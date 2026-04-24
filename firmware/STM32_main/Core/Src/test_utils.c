/*
 * test_utils.c
 *
 * Includes stuff to control switch arrays and
 * main Test() function and other useful test utilities
 * that are called by main.c
 *
 * Session-cached version:
 * - ADC init / ADC calibration / fault preflight run only when the
 *   structural test configuration changes.
 * - Structural configuration = PRM + VIN + INS + OUT
 * - VIP changes alone do NOT retrigger preparation.
 * - This allows GUI scripts to call TEST many times without re-running
 *   expensive preflight work for every vector.
 */

#include "main.h"
#include "test_utils.h"
#include "mux_utils.h"
#include "nau7802.h"
#include "adg2128_router.h"
#include "fault_handling.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

/*
 * Assumptions:
 * - ParsedState is defined in main.h
 * - hi2c1 and huart1 are defined in main.c
 * - ADG chip 1 address = 0x70
 * - ADG chip 2 address = 0x71
 *
 * IMPORTANT:
 * - Adjust STM32_SRC_GPIO_Port / STM32_SRC_Pin if your routed STM32 source net
 *   is driven by a different GPIO pin.
 */

extern I2C_HandleTypeDef hi2c1;
extern UART_HandleTypeDef huart1;

/* Track currently-routed source for each DUT input pin so unchanged inputs
 * are not disconnected/reconnected every step.
 * Index by DUT pin number 1..20.
 */
static RouteSource last_input_source[21];
static uint8_t last_input_valid[21] = {0};
static int32_t g_adc_offset_mv = 0;

/*
 * Cached “prepared session” snapshot.
 * Only these fields determine whether calibration / preflight must rerun.
 * VIP is intentionally excluded so multiple TEST calls in the same script
 * can reuse the same prepared session.
 */
typedef struct
{
    uint8_t valid;

    uint8_t prm_set;
    uint8_t vin_set;

    uint8_t vcc_pin;
    uint8_t gnd_pin;
    int32_t vcc_mv;

    int32_t vin_low_mv;
    int32_t vin_high_mv;

    uint8_t ins[MAX_PINS];
    uint8_t n_ins;

    uint8_t outs[MAX_PINS];
    uint8_t n_outs;
} TestSessionSnapshot;

static uint8_t g_test_session_prepared = 0;
static TestSessionSnapshot g_prepared_snapshot = {0};

typedef enum
{
    INPUT_DRIVE_LOW = 0,
    INPUT_DRIVE_HIGH,
    INPUT_DRIVE_CLOCK,
    INPUT_DRIVE_PULSE
} InputDriveMode;

typedef enum
{
    VIP_STEP_LOW = 0,
    VIP_STEP_HIGH,
    VIP_STEP_RISE,
    VIP_STEP_FALL
} VipStepSymbol;

/* ---------- UART helpers ---------- */

static void test_uart_print(const char *s)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)s, (uint16_t)strlen(s), HAL_MAX_DELAY);
}

void test_uart_printf(const char *fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    test_uart_print(buf);
}

/* ---------- ADG constants ---------- */

#define ADG1_ADDR_7BIT   0x70
#define ADG2_ADDR_7BIT   0x71

#define ADG_Y_1V8        0
#define ADG_Y_2V5        1
#define ADG_Y_3V3        2
#define ADG_Y_4V0        3
#define ADG_Y_4V5        4
#define ADG_Y_5V0        5
#define ADG_Y_STM32      6
#define ADG_Y_GND        7

/* ADC calibration */
#define ADC_CAL_PIN                  20U
#define ADC_CAL_GND_MAX_ACCEPT_MV    300
#define ADC_CAL_EXTRA_SETTLE_MS      10U
#define ADC_CAL_THROWAWAY_READS      2U

/* ---------- STM32 source GPIO ---------- */
/* Change these if your routed STM32 source net is driven by a different pin. */
#define STM32_SRC_GPIO_Port GPIOA
#define STM32_SRC_Pin       GPIO_PIN_8

/* ---------- Clock-voltage mux select GPIOs ---------- */
/*
 * New 8:1 mux select pins:
 *   A0 = PB0
 *   A1 = PB1
 *   A2 = PB2
 *
 * Assumed channel mapping:
 *   000 -> S1 = 1.8V
 *   001 -> S2 = 2.5V
 *   010 -> S3 = 3.3V
 *   011 -> S4 = 4.0V
 *   100 -> S5 = 4.5V
 *   101 -> S6 = 5.0V
 *   110 -> S7 = GND
 *   111 -> S8 = GND
 */
#define CLK_VMUX_A0_GPIO_Port GPIOB
#define CLK_VMUX_A0_Pin       GPIO_PIN_0
#define CLK_VMUX_A1_GPIO_Port GPIOB
#define CLK_VMUX_A1_Pin       GPIO_PIN_1
#define CLK_VMUX_A2_GPIO_Port GPIOB
#define CLK_VMUX_A2_Pin       GPIO_PIN_2

/* Pulse timing in milliseconds */
#define STEP_EVENT_PULSE_LOW_MS     1U
#define STEP_EVENT_PULSE_HIGH_MS    1U
#define STEP_EVENT_PULSE_FINAL_MS   1U
#define STEP_PRE_PULSE_SETUP_MS     2U

/* Delay after step events before output readback */
#define STEP_SETTLE_DELAY_MS        10U

/* ADC read tuning */
#define ADC_OUTPUT_SWITCH_SETTLE_MS 15U
#define ADC_INITIAL_SETTLE_MS       20U
#define ADC_BETWEEN_SAMPLES_MS      4U
#define ADC_SAMPLE_COUNT            5U
#define ADC_OUTPUT_SWITCH_SETTLE_MS 10U
#define ADC_OUTPUT_THROWAWAY_READS  2U


/* High-Z detection band */
#define ADC_HIGHZ_MIN_MV            1550
#define ADC_HIGHZ_MAX_MV            1660

/* ---------- Low-level helpers ---------- */

static HAL_StatusTypeDef adg_check_ready(uint8_t addr7)
{
    return HAL_I2C_IsDeviceReady(&hi2c1, (uint16_t)(addr7 << 1), 3, 100);
}

/*
 * ADG2128 X address encoding is NOT straight binary for X6-X11.
 *
 * Datasheet Table 7:
 * X0  = 0000
 * X1  = 0001
 * X2  = 0010
 * X3  = 0011
 * X4  = 0100
 * X5  = 0101
 * X6  = 1000
 * X7  = 1001
 * X8  = 1010
 * X9  = 1011
 * X10 = 1100
 * X11 = 1101
 */
static int adg_encode_x(uint8_t x, uint8_t *ax_out)
{
    if (ax_out == NULL) {
        return -1;
    }

    switch (x)
    {
        case 0:  *ax_out = 0x0; return 0;
        case 1:  *ax_out = 0x1; return 0;
        case 2:  *ax_out = 0x2; return 0;
        case 3:  *ax_out = 0x3; return 0;
        case 4:  *ax_out = 0x4; return 0;
        case 5:  *ax_out = 0x5; return 0;
        case 6:  *ax_out = 0x8; return 0;
        case 7:  *ax_out = 0x9; return 0;
        case 8:  *ax_out = 0xA; return 0;
        case 9:  *ax_out = 0xB; return 0;
        case 10: *ax_out = 0xC; return 0;
        case 11: *ax_out = 0xD; return 0;
        default: return -1;
    }
}

static HAL_StatusTypeDef adg_write_crosspoint(uint8_t addr7,
                                              uint8_t x,
                                              uint8_t y,
                                              uint8_t on)
{
    if (x > 11 || y > 7) {
        test_uart_print("ERR: invalid X/Y\r\n");
        return HAL_ERROR;
    }

    uint8_t ax;
    if (adg_encode_x(x, &ax) != 0) {
        test_uart_print("ERR: X encode failed\r\n");
        return HAL_ERROR;
    }

    uint8_t tx[2];

    tx[0] = ((on & 0x01U) << 7) |
            ((ax & 0x0FU) << 3) |
            ((y  & 0x07U) << 0);

    tx[1] = 0x01U;   /* LDSW = 1 */

    return HAL_I2C_Master_Transmit(&hi2c1,
                                   (uint16_t)(addr7 << 1),
                                   tx,
                                   2,
                                   100);
}

/* ---------- DUT pin mapping ---------- */

static int map_dut_pin(uint8_t dut_pin, uint8_t *addr7_out, uint8_t *x_out)
{
    if ((addr7_out == NULL) || (x_out == NULL)) {
        return -1;
    }

    switch (dut_pin)
    {
        /* ADG chip 1 */
        case 1:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 5; return 0;
        case 2:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 4; return 0;
        case 3:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 3; return 0;
        case 4:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 2; return 0;
        case 5:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 1; return 0;
        case 6:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 0; return 0;
        case 7:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 9; return 0;
        case 8:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 8; return 0;
        case 9:  *addr7_out = ADG1_ADDR_7BIT; *x_out = 7; return 0;
        case 10: *addr7_out = ADG1_ADDR_7BIT; *x_out = 6; return 0;

        /* ADG chip 2 */
        case 11: *addr7_out = ADG2_ADDR_7BIT; *x_out = 5; return 0;
        case 12: *addr7_out = ADG2_ADDR_7BIT; *x_out = 4; return 0;
        case 13: *addr7_out = ADG2_ADDR_7BIT; *x_out = 3; return 0;
        case 14: *addr7_out = ADG2_ADDR_7BIT; *x_out = 2; return 0;
        case 15: *addr7_out = ADG2_ADDR_7BIT; *x_out = 1; return 0;
        case 16: *addr7_out = ADG2_ADDR_7BIT; *x_out = 0; return 0;
        case 17: *addr7_out = ADG2_ADDR_7BIT; *x_out = 9; return 0;
        case 18: *addr7_out = ADG2_ADDR_7BIT; *x_out = 8; return 0;
        case 19: *addr7_out = ADG2_ADDR_7BIT; *x_out = 7; return 0;
        case 20: *addr7_out = ADG2_ADDR_7BIT; *x_out = 6; return 0;

        default:
            return -1;
    }
}

/* ---------- Route source mapping ---------- */

static int map_route_source_to_y(RouteSource source, uint8_t *y_out)
{
    if (y_out == NULL) {
        return -1;
    }

    switch (source)
    {
        case ROUTE_SRC_1V8:       *y_out = ADG_Y_1V8;   return 0;
        case ROUTE_SRC_2V5:       *y_out = ADG_Y_2V5;   return 0;
        case ROUTE_SRC_3V3:       *y_out = ADG_Y_3V3;   return 0;
        case ROUTE_SRC_4V0:       *y_out = ADG_Y_4V0;   return 0;
        case ROUTE_SRC_4V5:       *y_out = ADG_Y_4V5;   return 0;
        case ROUTE_SRC_5V0:       *y_out = ADG_Y_5V0;   return 0;
        case ROUTE_SRC_STM32_GPIO:*y_out = ADG_Y_STM32; return 0;
        case ROUTE_SRC_GND:       *y_out = ADG_Y_GND;   return 0;
        default:
            return -1;
    }
}

static HAL_StatusTypeDef disconnect_dut_pin(uint8_t dut_pin)
{
    uint8_t addr7, x;
    HAL_StatusTypeDef overall = HAL_OK;

    if (map_dut_pin(dut_pin, &addr7, &x) != 0) {
        return HAL_ERROR;
    }

    for (uint8_t y = 0; y <= 7; y++) {
        HAL_StatusTypeDef rc = adg_write_crosspoint(addr7, x, y, 0);
        if (rc != HAL_OK) {
            overall = rc;
        }
    }

    return overall;
}

/* ---------- Generic connect helper ---------- */

static HAL_StatusTypeDef connect_dut_pin_to_source(uint8_t dut_pin, RouteSource source)
{
    uint8_t addr7, x, y;

    if (map_dut_pin(dut_pin, &addr7, &x) != 0) {
        return HAL_ERROR;
    }

    if (map_route_source_to_y(source, &y) != 0) {
        return HAL_ERROR;
    }

    if (disconnect_dut_pin(dut_pin) != HAL_OK) {
        return HAL_ERROR;
    }

    return adg_write_crosspoint(addr7, x, y, 1);
}

/* ---------- Convenience wrappers for each route source ---------- */

static HAL_StatusTypeDef connect_dut_pin_to_1v8(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_1V8);
}

static HAL_StatusTypeDef connect_dut_pin_to_2v5(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_2V5);
}

static HAL_StatusTypeDef connect_dut_pin_to_3v3(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_3V3);
}

static HAL_StatusTypeDef connect_dut_pin_to_4v0(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_4V0);
}

static HAL_StatusTypeDef connect_dut_pin_to_4v5(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_4V5);
}

static HAL_StatusTypeDef connect_dut_pin_to_5v0(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_5V0);
}

static HAL_StatusTypeDef connect_dut_pin_to_stm32_gpio(uint8_t dut_pin)
{
    return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_STM32_GPIO);
}

static void disconnect_all_pins(void)
{
    for (uint8_t pin = 1; pin <= 20; pin++) {
        (void)disconnect_dut_pin(pin);
    }
}

static int adg_get_readback_addr(uint8_t x, uint8_t *rb_out)
{
    if (rb_out == NULL) {
        return -1;
    }

    switch (x)
    {
        case 0:  *rb_out = 0x34; return 0;
        case 1:  *rb_out = 0x3C; return 0;
        case 2:  *rb_out = 0x74; return 0;
        case 3:  *rb_out = 0x7C; return 0;
        case 4:  *rb_out = 0x35; return 0;
        case 5:  *rb_out = 0x3D; return 0;
        case 6:  *rb_out = 0x75; return 0;
        case 7:  *rb_out = 0x7D; return 0;
        case 8:  *rb_out = 0x36; return 0;
        case 9:  *rb_out = 0x3E; return 0;
        case 10: *rb_out = 0x76; return 0;
        case 11: *rb_out = 0x7E; return 0;
        default: return -1;
    }
}

static HAL_StatusTypeDef adg_read_x_status(uint8_t addr7, uint8_t x, uint8_t *y_status_out)
{
    uint8_t rb;
    if (y_status_out == NULL) {
        return HAL_ERROR;
    }

    if (adg_get_readback_addr(x, &rb) != 0) {
        return HAL_ERROR;
    }

    uint8_t tx[2] = { rb, 0x00 };
    HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c1,
                                                   (uint16_t)(addr7 << 1),
                                                   tx,
                                                   2,
                                                   100);
    if (rc != HAL_OK) {
        test_uart_printf("Readback setup failed addr=0x%02X X=%u rc=%d\r\n", addr7, x, rc);
        return rc;
    }

    uint8_t rx[2] = {0};
    rc = HAL_I2C_Master_Receive(&hi2c1,
                                (uint16_t)(addr7 << 1),
                                rx,
                                2,
                                100);
    if (rc != HAL_OK) {
        test_uart_printf("Readback receive failed addr=0x%02X X=%u rc=%d\r\n", addr7, x, rc);
        return rc;
    }

    *y_status_out = rx[1];
    test_uart_printf("Readback addr=0x%02X X=%u -> rx[0]=0x%02X rx[1]=0x%02X\r\n",
                     addr7, x, rx[0], rx[1]);

    return HAL_OK;
}

/* ---------- STM32 source GPIO helpers ---------- */

static void stm32_source_gpio_write(GPIO_PinState state)
{
    HAL_GPIO_WritePin(STM32_SRC_GPIO_Port, STM32_SRC_Pin, state);
}

static void stm32_source_gpio_idle_low(void)
{
    stm32_source_gpio_write(GPIO_PIN_RESET);
}

static HAL_StatusTypeDef pulse_stm32_source_gpio(uint32_t low_ms,
                                                 uint32_t high_ms,
                                                 uint32_t final_low_ms)
{
    stm32_source_gpio_write(GPIO_PIN_RESET);
    HAL_Delay(low_ms);

    stm32_source_gpio_write(GPIO_PIN_SET);
    HAL_Delay(high_ms);

    stm32_source_gpio_write(GPIO_PIN_RESET);
    HAL_Delay(final_low_ms);

    return HAL_OK;
}

/* ---------- Clock-voltage mux helpers ---------- */

static void clock_vmux_write_select_bits(uint8_t sel)
{
    HAL_GPIO_WritePin(CLK_VMUX_A0_GPIO_Port,
                      CLK_VMUX_A0_Pin,
                      (sel & 0x01U) ? GPIO_PIN_SET : GPIO_PIN_RESET);

    HAL_GPIO_WritePin(CLK_VMUX_A1_GPIO_Port,
                      CLK_VMUX_A1_Pin,
                      (sel & 0x02U) ? GPIO_PIN_SET : GPIO_PIN_RESET);

    HAL_GPIO_WritePin(CLK_VMUX_A2_GPIO_Port,
                      CLK_VMUX_A2_Pin,
                      (sel & 0x04U) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static HAL_StatusTypeDef select_clock_voltage_mux_for_vcc(RouteSource vcc_source)
{
    uint8_t sel;

    switch (vcc_source)
    {
        case ROUTE_SRC_1V8: sel = 0x0; break; /* S1 */
        case ROUTE_SRC_2V5: sel = 0x1; break; /* S2 */
        case ROUTE_SRC_3V3: sel = 0x2; break; /* S3 */
        case ROUTE_SRC_4V0: sel = 0x3; break; /* S4 */
        case ROUTE_SRC_4V5: sel = 0x4; break; /* S5 */
        case ROUTE_SRC_5V0: sel = 0x5; break; /* S6 */
        default:
            return HAL_ERROR;
    }

    clock_vmux_write_select_bits(sel);
    HAL_Delay(1);

    return HAL_OK;
}

static void clock_vmux_default_to_gnd(void)
{
    clock_vmux_write_select_bits(0x6); /* S7 = GND */
}

/* ---------- Session snapshot helpers ---------- */

static void snapshot_from_info(const ParsedState *info, TestSessionSnapshot *snap)
{
    if ((info == NULL) || (snap == NULL)) {
        return;
    }

    memset(snap, 0, sizeof(*snap));

    snap->valid = 1;
    snap->prm_set = info->prm_set;
    snap->vin_set = info->vin_set;

    /*
     * Cache only the physical/socket structural config.
     * Do NOT cache VCC magnitude or VIN thresholds as session-breaking values.
     */
    snap->vcc_pin = info->vcc_pin;
    snap->gnd_pin = info->gnd_pin;

    snap->n_ins = info->n_ins;
    snap->n_outs = info->n_outs;

    memcpy(snap->ins, info->ins, sizeof(snap->ins));
    memcpy(snap->outs, info->outs, sizeof(snap->outs));
}

static uint8_t info_matches_snapshot(const ParsedState *info, const TestSessionSnapshot *snap)
{
    if ((info == NULL) || (snap == NULL) || !snap->valid) {
        return 0U;
    }

    if (snap->prm_set != info->prm_set) return 0U;
    if (snap->vin_set != info->vin_set) return 0U;

    if (snap->vcc_pin != info->vcc_pin) return 0U;
    if (snap->gnd_pin != info->gnd_pin) return 0U;

    return 1U;
}

void Test_InvalidateSession(void)
{
    g_test_session_prepared = 0U;
    memset(&g_prepared_snapshot, 0, sizeof(g_prepared_snapshot));
}

/* ---------- Main test entry ---------- */

void Check_Connectivity(ParsedState *state)
{
    (void)state;  /* unused for this connectivity test */

    test_uart_print("\r\n=== ADG2128 Connectivity Test Start ===\r\n");

    if (adg_check_ready(ADG1_ADDR_7BIT) == HAL_OK) {
        test_uart_print("ADG chip 1 found at 0x70\r\n");
    } else {
        test_uart_print("ADG chip 1 NOT found at 0x70\r\n");
    }

    if (adg_check_ready(ADG2_ADDR_7BIT) == HAL_OK) {
        test_uart_print("ADG chip 2 found at 0x71\r\n");
    } else {
        test_uart_print("ADG chip 2 NOT found at 0x71\r\n");
    }

    test_uart_print("Clearing all DUT pin routes...\r\n");
    disconnect_all_pins();
    HAL_Delay(250);

    for (uint8_t pin = 1; pin <= 20; pin++)
    {
        HAL_StatusTypeDef rc;

        test_uart_printf("Driving DUT pin %u with 3.3V...\r\n", pin);

        rc = connect_dut_pin_to_3v3(pin);
        if (rc != HAL_OK) {
            test_uart_printf("ERR: failed to connect DUT pin %u\r\n", pin);
            continue;
        }

        uint8_t addr7, x, y_status;
        if (map_dut_pin(pin, &addr7, &x) == 0) {
            if (adg_read_x_status(addr7, x, &y_status) == HAL_OK) {
                test_uart_printf("Expected Y2 on, readback bits = 0x%02X\r\n", y_status);
            }
        }

        HAL_Delay(1500);

        rc = disconnect_dut_pin(pin);
        if (rc != HAL_OK) {
            test_uart_printf("ERR: failed to disconnect DUT pin %u\r\n", pin);
        } else {
            test_uart_printf("DUT pin %u disconnected\r\n", pin);
        }

        HAL_Delay(200);
    }

    test_uart_print("Final clear...\r\n");
    disconnect_all_pins();

    test_uart_print("=== ADG2128 Connectivity Test End ===\r\n\r\n");
}

static int vcc_mv_to_route_source(uint32_t vcc_mv, RouteSource *source_out)
{
    if (source_out == NULL) {
        return -1;
    }

    switch (vcc_mv)
    {
        case 1800: *source_out = ROUTE_SRC_1V8; return 0;
        case 2500: *source_out = ROUTE_SRC_2V5; return 0;
        case 3300: *source_out = ROUTE_SRC_3V3; return 0;
        case 4000: *source_out = ROUTE_SRC_4V0; return 0;
        case 4500: *source_out = ROUTE_SRC_4V5; return 0;
        case 5000: *source_out = ROUTE_SRC_5V0; return 0;
        default:
            return -1;
    }
}

static HAL_StatusTypeDef drive_dut_input_pin(uint8_t dut_pin,
                                             InputDriveMode mode,
                                             RouteSource high_source)
{
    switch (mode)
    {
        case INPUT_DRIVE_LOW:
            return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_GND);

        case INPUT_DRIVE_HIGH:
            return connect_dut_pin_to_source(dut_pin, high_source);

        case INPUT_DRIVE_CLOCK:
            return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_STM32_GPIO);

        case INPUT_DRIVE_PULSE:
            return connect_dut_pin_to_source(dut_pin, ROUTE_SRC_STM32_GPIO);

        default:
            return HAL_ERROR;
    }
}

static int vip_voltage_to_route_source(int32_t mv, RouteSource *source_out)
{
    if (source_out == NULL) {
        return -1;
    }

    switch (mv)
    {
        case 0:    *source_out = ROUTE_SRC_GND; return 0;
        case 1800: *source_out = ROUTE_SRC_1V8; return 0;
        case 2500: *source_out = ROUTE_SRC_2V5; return 0;
        case 3300: *source_out = ROUTE_SRC_3V3; return 0;
        case 4000: *source_out = ROUTE_SRC_4V0; return 0;
        case 4500: *source_out = ROUTE_SRC_4V5; return 0;
        case 5000: *source_out = ROUTE_SRC_5V0; return 0;
        default:
            return -1;
    }
}

static int vip_bin_length_bits(const char *s)
{
    if (s == NULL) {
        return -1;
    }

    if ((s[0] != '0') || (s[1] != 'b')) {
        return -1;
    }

    int len = 0;
    for (int i = 2; s[i] != '\0'; i++) {
        if ((s[i] != '0') &&
            (s[i] != '1') &&
            (s[i] != 'R') &&
            (s[i] != 'F')) {
            return -1;
        }
        len++;
    }

    return (len > 0) ? len : -1;
}

static int vip_bin_get_symbol(const char *s,
                              uint8_t bit_index,
                              VipStepSymbol *sym_out)
{
    int len;
    char c;

    if ((s == NULL) || (sym_out == NULL)) {
        return -1;
    }

    len = vip_bin_length_bits(s);
    if (len <= 0) {
        return -1;
    }

    if (bit_index >= (uint8_t)len) {
        return -1;
    }

    c = s[2 + bit_index];

    switch (c)
    {
        case '0': *sym_out = VIP_STEP_LOW;  return 0;
        case '1': *sym_out = VIP_STEP_HIGH; return 0;
        case 'R': *sym_out = VIP_STEP_RISE; return 0;
        case 'F': *sym_out = VIP_STEP_FALL; return 0;
        default:
            return -1;
    }
}

static HAL_StatusTypeDef execute_vip_edge_on_pin(uint8_t dut_pin,
                                                 VipStepSymbol sym,
                                                 RouteSource high_source)
{
    if (sym == VIP_STEP_RISE)
    {
        if (connect_dut_pin_to_source(dut_pin, ROUTE_SRC_GND) != HAL_OK) {
            return HAL_ERROR;
        }

        HAL_Delay(STEP_EVENT_PULSE_LOW_MS);

        if (connect_dut_pin_to_source(dut_pin, high_source) != HAL_OK) {
            return HAL_ERROR;
        }

        HAL_Delay(STEP_EVENT_PULSE_HIGH_MS);

        last_input_source[dut_pin] = high_source;
        last_input_valid[dut_pin] = 1U;
        return HAL_OK;
    }

    if (sym == VIP_STEP_FALL)
    {
        if (connect_dut_pin_to_source(dut_pin, high_source) != HAL_OK) {
            return HAL_ERROR;
        }

        HAL_Delay(STEP_EVENT_PULSE_HIGH_MS);

        if (connect_dut_pin_to_source(dut_pin, ROUTE_SRC_GND) != HAL_OK) {
            return HAL_ERROR;
        }

        HAL_Delay(STEP_EVENT_PULSE_FINAL_MS);

        last_input_source[dut_pin] = ROUTE_SRC_GND;
        last_input_valid[dut_pin] = 1U;
        return HAL_OK;
    }

    return HAL_ERROR;
}

static void sort_int32_array(int32_t *arr, uint8_t count)
{
    for (uint8_t i = 0; i < count; i++)
    {
        for (uint8_t j = i + 1U; j < count; j++)
        {
            if (arr[j] < arr[i])
            {
                int32_t tmp = arr[i];
                arr[i] = arr[j];
                arr[j] = tmp;
            }
        }
    }
}

static int determine_serial_pattern_length(const ParsedState *info, uint8_t *steps_out)
{
    int serial_len = 0;

    if ((info == NULL) || (steps_out == NULL)) {
        return -1;
    }

    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        if (info->vip_kind[i] == VIP_KIND_BIN)
        {
            int len = vip_bin_length_bits(info->vip_bin[i]);
            if (len <= 0) {
                return -1;
            }

            if (serial_len == 0) {
                serial_len = len;
            } else if (serial_len != len) {
                return -1;
            }
        }
    }

    if (serial_len == 0) {
        *steps_out = 1;
    } else {
        *steps_out = (uint8_t)serial_len;
    }

    return 0;
}

static HAL_StatusTypeDef configure_clock_inputs_once(const ParsedState *info,
                                                     RouteSource vcc_source)
{
    if (info == NULL) {
        return HAL_ERROR;
    }

    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        uint8_t dut_pin = info->ins[i];

        if (info->vip_kind[i] != VIP_KIND_CLK) {
            continue;
        }

        if ((dut_pin == info->vcc_pin) || (dut_pin == info->gnd_pin))
        {
            test_uart_printf("ERR: DUT pin %u cannot be both power and clock input\r\n", dut_pin);
            return HAL_ERROR;
        }

        if (drive_dut_input_pin(dut_pin, INPUT_DRIVE_CLOCK, vcc_source) != HAL_OK)
        {
            test_uart_printf("ERR: failed to configure CLOCK on DUT pin %u\r\n", dut_pin);
            return HAL_ERROR;
        }

        last_input_source[dut_pin] = ROUTE_SRC_STM32_GPIO;
        last_input_valid[dut_pin] = 1U;
    }

    return HAL_OK;
}

static HAL_StatusTypeDef adc_settle_and_read_mv(int32_t *mv_out)
{
    HAL_StatusTypeDef rc;
    int32_t samples[ADC_SAMPLE_COUNT];
    int32_t sorted[ADC_SAMPLE_COUNT];

    if (mv_out == NULL) {
        return HAL_ERROR;
    }

    HAL_Delay(ADC_INITIAL_SETTLE_MS);

    for (uint8_t i = 0; i < ADC_SAMPLE_COUNT; i++)
    {
        samples[i] = 0;
        sorted[i] = 0;
    }

    for (uint8_t i = 0; i < ADC_SAMPLE_COUNT; i++)
    {
        rc = nau7802_read_mv(&samples[i]);
        if (rc != HAL_OK) {
            return rc;
        }

        if (i + 1U < ADC_SAMPLE_COUNT) {
            HAL_Delay(ADC_BETWEEN_SAMPLES_MS);
        }
    }

    for (uint8_t i = 0; i < ADC_SAMPLE_COUNT; i++) {
        sorted[i] = samples[i];
    }

    sort_int32_array(sorted, ADC_SAMPLE_COUNT);

    *mv_out = sorted[ADC_SAMPLE_COUNT / 2U];
    return HAL_OK;
}

static HAL_StatusTypeDef apply_inputs_for_step(const ParsedState *info,
                                               RouteSource vcc_source,
                                               uint8_t step_index)
{
    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        uint8_t dut_pin = info->ins[i];
        RouteSource desired_source;

        if ((dut_pin == info->vcc_pin) || (dut_pin == info->gnd_pin))
        {
            test_uart_printf("ERR: DUT pin %u cannot be both power and input\r\n", dut_pin);
            return HAL_ERROR;
        }

        switch (info->vip_kind[i])
        {
            case VIP_KIND_VOLT:
            {
                if (vip_voltage_to_route_source(info->vip_mv[i], &desired_source) != 0)
                {
                    test_uart_printf("ERR: unsupported VIP voltage %ld mV on DUT pin %u\r\n",
                                     (long)info->vip_mv[i], dut_pin);
                    return HAL_ERROR;
                }
                break;
            }

            case VIP_KIND_CLK:
            {
                continue;
            }

            case VIP_KIND_BIN:
            {
                VipStepSymbol sym;

                if (vip_bin_get_symbol(info->vip_bin[i], step_index, &sym) != 0)
                {
                    test_uart_printf("ERR: failed to get serial symbol for DUT pin %u at step %u\r\n",
                                     dut_pin, step_index);
                    return HAL_ERROR;
                }

                if (sym == VIP_STEP_RISE || sym == VIP_STEP_FALL)
                {
                    if (execute_vip_edge_on_pin(dut_pin, sym, vcc_source) != HAL_OK)
                    {
                        test_uart_printf("ERR: failed to execute edge on DUT pin %u at step %u\r\n",
                                         dut_pin, step_index);
                        return HAL_ERROR;
                    }

                    continue;
                }

                desired_source = (sym == VIP_STEP_HIGH) ? vcc_source : ROUTE_SRC_GND;
                break;
            }

            default:
                test_uart_printf("ERR: unknown VIP kind on DUT pin %u\r\n", dut_pin);
                return HAL_ERROR;
        }

        if ((!last_input_valid[dut_pin]) || (last_input_source[dut_pin] != desired_source))
        {
            if (connect_dut_pin_to_source(dut_pin, desired_source) != HAL_OK)
            {
                test_uart_printf("ERR: failed to configure DUT input pin %u\r\n", dut_pin);
                return HAL_ERROR;
            }

            last_input_source[dut_pin] = desired_source;
            last_input_valid[dut_pin] = 1U;
        }
    }

    return HAL_OK;
}



static HAL_StatusTypeDef adc_read_calibrated_mv(int32_t *mv_out)
{
    int32_t raw_mv = 0;

    if (mv_out == NULL) {
        return HAL_ERROR;
    }

    if (adc_settle_and_read_mv(&raw_mv) != HAL_OK) {
        return HAL_ERROR;
    }

    *mv_out = raw_mv - g_adc_offset_mv;
    return HAL_OK;
}

static HAL_StatusTypeDef read_output_pin_calibrated_mv(uint8_t dut_pin, int32_t *mv_out)
{
    int32_t dummy_mv = 0;

    if (mv_out == NULL) {
        return HAL_ERROR;
    }

    if (mux_select_dut_output_pin(dut_pin) != 0)
    {
        return HAL_ERROR;
    }

    HAL_Delay(ADC_OUTPUT_SWITCH_SETTLE_MS);

    /* Throw away first couple reads after mux channel switch */
    for (uint8_t i = 0; i < ADC_OUTPUT_THROWAWAY_READS; i++)
    {
        if (nau7802_read_mv(&dummy_mv) != HAL_OK) {
            return HAL_ERROR;
        }
        HAL_Delay(ADC_BETWEEN_SAMPLES_MS);
    }

    return adc_read_calibrated_mv(mv_out);
}





static HAL_StatusTypeDef calibrate_adc_offset(void)
{
    int32_t throwaway_mv = 0;
    int32_t cal_mv = 0;

    test_uart_print("ADC calibration start\r\n");

    disconnect_all_pins();
    HAL_Delay(ADC_CAL_EXTRA_SETTLE_MS);

    if (connect_dut_pin_to_source(ADC_CAL_PIN, ROUTE_SRC_GND) != HAL_OK)
    {
        test_uart_printf("ERR: ADC cal failed to route GND to DUT pin %u\r\n", ADC_CAL_PIN);
        return HAL_ERROR;
    }

    if (mux_select_dut_output_pin(ADC_CAL_PIN) != 0)
    {
        test_uart_printf("ERR: ADC cal failed to mux DUT pin %u\r\n", ADC_CAL_PIN);
        disconnect_all_pins();
        return HAL_ERROR;
    }

    HAL_Delay(ADC_OUTPUT_SWITCH_SETTLE_MS + ADC_CAL_EXTRA_SETTLE_MS);

    for (uint8_t i = 0; i < ADC_CAL_THROWAWAY_READS; i++)
    {
        if (nau7802_read_mv(&throwaway_mv) != HAL_OK)
        {
            test_uart_print("ERR: ADC cal throwaway read failed\r\n");
            disconnect_all_pins();
            return HAL_ERROR;
        }
        HAL_Delay(ADC_BETWEEN_SAMPLES_MS);
    }

    if (adc_settle_and_read_mv(&cal_mv) != HAL_OK)
    {
        test_uart_print("ERR: ADC calibration read failed\r\n");
        disconnect_all_pins();
        return HAL_ERROR;
    }

    g_adc_offset_mv = cal_mv;

    test_uart_printf("ADC calibration raw=%ld mV, offset=%ld mV\r\n",
                     (long)cal_mv,
                     (long)g_adc_offset_mv);

    if (cal_mv < -ADC_CAL_GND_MAX_ACCEPT_MV || cal_mv > ADC_CAL_GND_MAX_ACCEPT_MV)
    {
        test_uart_printf("ERR: ADC calibration out of expected range (%ld mV)\r\n",
                         (long)cal_mv);
        disconnect_all_pins();
        return HAL_ERROR;
    }

    disconnect_all_pins();
    HAL_Delay(ADC_CAL_EXTRA_SETTLE_MS);

    test_uart_print("ADC calibration complete\r\n");
    return HAL_OK;
}

static HAL_StatusTypeDef read_outputs_for_step(const ParsedState *info, uint8_t step_index)
{

    if (info->n_outs > 0)
    {
        int32_t dummy_mv = 0;
        (void)read_output_pin_calibrated_mv(info->outs[0], &dummy_mv);
    }

	for (uint8_t i = 0; i < info->n_outs; i++)
    {
        uint8_t dut_pin = info->outs[i];

        int32_t adc_mv = 0;
        if (read_output_pin_calibrated_mv(dut_pin, &adc_mv) != HAL_OK)
        {
            test_uart_printf("ERR: failed to read calibrated ADC for DUT output pin %u at step %u\r\n",
                             dut_pin, step_index);
            continue;
        }

        if ((adc_mv >= ADC_HIGHZ_MIN_MV) && (adc_mv <= ADC_HIGHZ_MAX_MV))
        {
            test_uart_printf("STEP %u OUT pin %u -> -2 (%ld mV)\r\n",
                             step_index, dut_pin, (long)adc_mv);
            continue;
        }

        uint8_t logic_value;
        if (adc_mv <= info->vin_low_mv) {
            logic_value = 0;
        }
        else if (adc_mv >= info->vin_high_mv) {
            logic_value = 1;
        }
        else {
            test_uart_printf("STEP %u OUT pin %u -> -1 (%ld mV)\r\n",
                             step_index, dut_pin, (long)adc_mv);
            continue;
        }

        test_uart_printf("STEP %u OUT pin %u -> %u (%ld mV)\r\n",
                         step_index,
                         dut_pin,
                         logic_value,
                         (long)adc_mv);
    }

    return HAL_OK;
}

/*
 * Returns 1 if any input pin for this test step is declared as VIP_KIND_CLK,
 * 0 if none are, and -1 on bad args.
 */
static int step_has_clock_event(const ParsedState *info)
{
    if (info == NULL) {
        return -1;
    }

    for (uint8_t i = 0; i < info->n_ins; i++) {
        if (info->vip_kind[i] == VIP_KIND_CLK) {
            return 1;
        }
    }

    return 0;
}

static HAL_StatusTypeDef execute_step_events(const ParsedState *info)
{
    int has_clk = step_has_clock_event(info);

    if (has_clk < 0) {
        return HAL_ERROR;
    }

    if (has_clk == 1)
    {
        if (pulse_stm32_source_gpio(STEP_EVENT_PULSE_LOW_MS,
                                    STEP_EVENT_PULSE_HIGH_MS,
                                    STEP_EVENT_PULSE_FINAL_MS) != HAL_OK)
        {
            test_uart_print("ERR: failed to generate STM32 clock pulse\r\n");
            return HAL_ERROR;
        }
    }

    return HAL_OK;
}

static void reset_parsed_state(ParsedState *info)
{
    if (info == NULL) {
        return;
    }

    memset(info, 0, sizeof(*info));
}

static void clear_vip_state(ParsedState *info)
{
    if (info == NULL) {
        return;
    }

    info->n_vip = 0;
    memset(info->vip_kind, 0, sizeof(info->vip_kind));
    memset(info->vip_mv, 0, sizeof(info->vip_mv));
    memset(info->vip_clk_mhz, 0, sizeof(info->vip_clk_mhz));
    memset(info->vip_bin, 0, sizeof(info->vip_bin));
}

/* ---------- One-time prepare for a structural test session ---------- */

HAL_StatusTypeDef Test_PrepareIfNeeded(ParsedState *info)
{
    if (info == NULL) {
        test_uart_print("ERR: info is NULL\r\n");
        return HAL_ERROR;
    }

    if (g_test_session_prepared && info_matches_snapshot(info, &g_prepared_snapshot))
    {
        return HAL_OK;
    }

    if (nau7802_init() != HAL_OK)
    {
        test_uart_print("ERR: failed to initialize NAU7802\r\n");
        g_test_session_prepared = 0U;
        return HAL_ERROR;
    }

    stm32_source_gpio_idle_low();
    clock_vmux_default_to_gnd();

    g_adc_offset_mv = 0;

    int32_t dummy_mv = 0;
    HAL_Delay(100);
    (void)nau7802_read_mv(&dummy_mv);
    HAL_Delay(10);
    (void)nau7802_read_mv(&dummy_mv);

    test_uart_print("NAU7802 dummy reads done\r\n");

    if (calibrate_adc_offset() != HAL_OK)
    {
        test_uart_print("ERR: ADC calibration failed\r\n");
        g_test_session_prepared = 0U;
        return HAL_ERROR;
    }

    FaultResult fault_result = Fault_RunPreflight(info, info->vcc_mv);
    if (fault_result != FAULT_RESULT_OK)
    {
        test_uart_printf("ERR: Test aborted, %s\r\n", Fault_ResultString(fault_result));
        g_test_session_prepared = 0U;
        return HAL_ERROR;
    }

    snapshot_from_info(info, &g_prepared_snapshot);
    g_test_session_prepared = 1U;
    return HAL_OK;
}

/* ---------- Actual per-TEST execution ---------- */

void Test(ParsedState *info)
{
	if (info == NULL) {
	        test_uart_print("ERR: info is NULL\r\n");
	        return;
	    }

    disconnect_all_pins();

    for (uint8_t pin = 0; pin <= 20; pin++)
    {
        last_input_valid[pin] = 0U;
    }

    HAL_Delay(500);

    RouteSource vcc_source;

    if (vcc_mv_to_route_source((uint32_t)info->vcc_mv, &vcc_source) != 0)
    {
        test_uart_printf("ERR: unsupported VCC = %ld mV\r\n", (long)info->vcc_mv);
        Test_InvalidateSession();
        goto cleanup;
    }

    test_uart_printf("Using VCC source for %ld mV\r\n", (long)info->vcc_mv);

    if (select_clock_voltage_mux_for_vcc(vcc_source) != HAL_OK)
    {
        test_uart_print("ERR: failed to set clock-voltage mux for current VCC\r\n");
        Test_InvalidateSession();
        goto cleanup;
    }

    if (connect_dut_pin_to_source(info->vcc_pin, vcc_source) != HAL_OK)
    {
        test_uart_printf("ERR: failed to connect DUT pin %u to VCC source\r\n", info->vcc_pin);
        Test_InvalidateSession();
        goto cleanup;
    }

    if (connect_dut_pin_to_source(info->gnd_pin, ROUTE_SRC_GND) != HAL_OK)
    {
        test_uart_printf("ERR: failed to connect DUT pin %u to GND\r\n", info->gnd_pin);
        Test_InvalidateSession();
        goto cleanup;
    }

    if (info->n_vip != info->n_ins)
    {
        test_uart_printf("ERR: INS count (%u) does not match VIP count (%u)\r\n",
                         info->n_ins, info->n_vip);
        goto cleanup;
    }

    uint8_t serial_steps = 1;
    if (determine_serial_pattern_length(info, &serial_steps) != 0)
    {
        test_uart_print("ERR: invalid VIP binary pattern(s) or mismatched lengths\r\n");
        goto cleanup;
    }

    test_uart_printf("Running %u test step(s)\r\n", serial_steps);

    if (configure_clock_inputs_once(info, vcc_source) != HAL_OK)
    {
        goto cleanup;
    }

    for (uint8_t step = 0; step < serial_steps; step++)
    {
        test_uart_printf("---- STEP %u ----\r\n", step);

        if (apply_inputs_for_step(info, vcc_source, step) != HAL_OK)
        {
            goto cleanup;
        }

        HAL_Delay(STEP_PRE_PULSE_SETUP_MS);

        if (execute_step_events(info) != HAL_OK)
        {
            goto cleanup;
        }

        HAL_Delay(STEP_SETTLE_DELAY_MS);

        if (read_outputs_for_step(info, step) != HAL_OK)
        {
            goto cleanup;
        }
    }

cleanup:
    stm32_source_gpio_idle_low();
    clock_vmux_default_to_gnd();
    disconnect_all_pins();

    for (uint8_t pin = 0; pin <= 20; pin++)
    {
        last_input_valid[pin] = 0U;
    }

    /*
     * Keep PRM / VIN / INS / OUT so the next TEST in the same script
     * can reuse the prepared session.
     * Only clear VIP so the GUI can load the next vector.
     */
    clear_vip_state(info);

    test_uart_printf("DONE\r\n");
}
