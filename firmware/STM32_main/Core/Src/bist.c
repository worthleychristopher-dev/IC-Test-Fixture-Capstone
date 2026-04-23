/*
 * bist.c
 *
 * Exhaustive Built-In Self Test (BIST) for the digital IC test fixture.
 *
 * This version:
 * - tests every DUT pin 1..20
 * - tests every fixture voltage source on every pin
 * - routes each source through the ADG switch arrays
 * - routes that DUT pin through the output mux
 * - reads voltage with the ADC
 * - checks against expected thresholds
 *
 * Assumptions:
 * - NO IC is inserted in the socket during BIST
 * - selecting a DUT pin through mux_select_dut_output_pin() allows the ADC
 *   to measure that socket pin voltage directly
 */

#include "main.h"
#include "bist.h"
#include "mux_utils.h"
#include "nau7802.h"

#include <stdio.h>
#include <string.h>
#include <stdarg.h>

/* extern peripherals from main.c */
extern I2C_HandleTypeDef hi2c1;
extern UART_HandleTypeDef huart1;

/* ---------- UART helpers ---------- */

static void bist_uart_print(const char *s)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)s, (uint16_t)strlen(s), HAL_MAX_DELAY);
}

static void bist_uart_printf(const char *fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    bist_uart_print(buf);
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

/* ---------- ADC timing ---------- */

#define BIST_ADC_INITIAL_SETTLE_MS      30U
#define BIST_ADC_BETWEEN_SAMPLES_MS     6U
#define BIST_ADC_SAMPLE_COUNT           5U
#define BIST_OUTPUT_SWITCH_SETTLE_MS    12U
#define BIST_POST_ROUTE_SETTLE_MS       20U
#define BIST_ADC_THROWAWAY_READS        2U

/* ---------- tolerance values ---------- */

#define BIST_GND_MAX_MV                 150
#define BIST_VOLTAGE_TOL_MV             250

typedef enum
{
    BIST_SRC_1V8 = 0,
    BIST_SRC_2V5,
    BIST_SRC_3V3,
    BIST_SRC_4V0,
    BIST_SRC_4V5,
    BIST_SRC_5V0,
    BIST_SRC_GND
} BistSource;

/* ---------- stats ---------- */

static uint32_t g_bist_total_checks = 0;
static uint32_t g_bist_failed_checks = 0;

/* ---------- small utils ---------- */

static int32_t abs32(int32_t x)
{
    return (x < 0) ? -x : x;
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

static void bist_mark_simple(const char *label, uint8_t pass)
{
    g_bist_total_checks++;

    if (pass) {
        bist_uart_printf("PASS %s\r\n", label);
    } else {
        g_bist_failed_checks++;
        bist_uart_printf("FAIL %s\r\n", label);
    }
}

static void bist_mark_voltage_result(uint8_t pin,
                                     const char *src_name,
                                     int32_t expected_mv,
                                     int32_t measured_mv,
                                     uint8_t pass)
{
    g_bist_total_checks++;

    if (pass) {
        bist_uart_printf("PASS pin=%u src=%s expected=%ldmV measured=%ldmV\r\n",
                         pin,
                         src_name,
                         (long)expected_mv,
                         (long)measured_mv);
    } else {
        g_bist_failed_checks++;
        bist_uart_printf("FAIL pin=%u src=%s expected=%ldmV measured=%ldmV\r\n",
                         pin,
                         src_name,
                         (long)expected_mv,
                         (long)measured_mv);
    }
}

/* ---------- ADG helpers ---------- */

static HAL_StatusTypeDef adg_check_ready(uint8_t addr7)
{
    return HAL_I2C_IsDeviceReady(&hi2c1, (uint16_t)(addr7 << 1), 3, 100);
}

/*
 * ADG2128 X encoding is not straight binary for X6..X11.
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
        return HAL_ERROR;
    }

    uint8_t ax;
    if (adg_encode_x(x, &ax) != 0) {
        return HAL_ERROR;
    }

    uint8_t tx[2];

    tx[0] = ((on & 0x01U) << 7) |
            ((ax & 0x0FU) << 3) |
            ((y  & 0x07U) << 0);

    tx[1] = 0x01U; /* LDSW = 1 */

    return HAL_I2C_Master_Transmit(&hi2c1,
                                   (uint16_t)(addr7 << 1),
                                   tx,
                                   2,
                                   100);
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
        return rc;
    }

    uint8_t rx[2] = {0};
    rc = HAL_I2C_Master_Receive(&hi2c1,
                                (uint16_t)(addr7 << 1),
                                rx,
                                2,
                                100);
    if (rc != HAL_OK) {
        return rc;
    }

    *y_status_out = rx[1];
    return HAL_OK;
}

/* ---------- DUT pin mapping ---------- */

static int map_dut_pin(uint8_t dut_pin, uint8_t *addr7_out, uint8_t *x_out)
{
    if ((addr7_out == NULL) || (x_out == NULL)) {
        return -1;
    }

    switch (dut_pin)
    {
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

static int source_to_y(BistSource src, uint8_t *y_out)
{
    if (y_out == NULL) {
        return -1;
    }

    switch (src)
    {
        case BIST_SRC_1V8: *y_out = ADG_Y_1V8; return 0;
        case BIST_SRC_2V5: *y_out = ADG_Y_2V5; return 0;
        case BIST_SRC_3V3: *y_out = ADG_Y_3V3; return 0;
        case BIST_SRC_4V0: *y_out = ADG_Y_4V0; return 0;
        case BIST_SRC_4V5: *y_out = ADG_Y_4V5; return 0;
        case BIST_SRC_5V0: *y_out = ADG_Y_5V0; return 0;
        case BIST_SRC_GND: *y_out = ADG_Y_GND; return 0;
        default: return -1;
    }
}

static const char *source_name(BistSource src)
{
    switch (src)
    {
        case BIST_SRC_1V8: return "1.8V";
        case BIST_SRC_2V5: return "2.5V";
        case BIST_SRC_3V3: return "3.3V";
        case BIST_SRC_4V0: return "4.0V";
        case BIST_SRC_4V5: return "4.5V";
        case BIST_SRC_5V0: return "5.0V";
        case BIST_SRC_GND: return "GND";
        default:           return "?";
    }
}

static int32_t source_expected_mv(BistSource src)
{
    switch (src)
    {
        case BIST_SRC_1V8: return 1800;
        case BIST_SRC_2V5: return 2500;
        case BIST_SRC_3V3: return 3300;
        case BIST_SRC_4V0: return 4000;
        case BIST_SRC_4V5: return 4500;
        case BIST_SRC_5V0: return 5000;
        case BIST_SRC_GND: return 0;
        default:           return -1;
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

static HAL_StatusTypeDef disconnect_all_pins(void)
{
    HAL_StatusTypeDef overall = HAL_OK;

    for (uint8_t pin = 1; pin <= 20; pin++) {
        HAL_StatusTypeDef rc = disconnect_dut_pin(pin);
        if (rc != HAL_OK) {
            overall = rc;
        }
    }

    return overall;
}

static HAL_StatusTypeDef connect_pin_to_source(uint8_t dut_pin, BistSource src)
{
    uint8_t addr7, x, y;

    if (map_dut_pin(dut_pin, &addr7, &x) != 0) {
        return HAL_ERROR;
    }

    if (source_to_y(src, &y) != 0) {
        return HAL_ERROR;
    }

    if (disconnect_dut_pin(dut_pin) != HAL_OK) {
        return HAL_ERROR;
    }

    return adg_write_crosspoint(addr7, x, y, 1);
}

static uint8_t verify_adg_readback(uint8_t dut_pin, BistSource src)
{
    uint8_t addr7, x, y_expected, y_status;

    if (map_dut_pin(dut_pin, &addr7, &x) != 0) {
        return 0;
    }

    if (source_to_y(src, &y_expected) != 0) {
        return 0;
    }

    if (adg_read_x_status(addr7, x, &y_status) != HAL_OK) {
        return 0;
    }

    return (y_status == (uint8_t)(1U << y_expected)) ? 1U : 0U;
}

/* ---------- ADC helpers ---------- */

static HAL_StatusTypeDef adc_settle_and_read_mv(int32_t *mv_out)
{
    HAL_StatusTypeDef rc;
    int32_t samples[BIST_ADC_SAMPLE_COUNT];
    int32_t sorted[BIST_ADC_SAMPLE_COUNT];

    if (mv_out == NULL) {
        return HAL_ERROR;
    }

    HAL_Delay(BIST_ADC_INITIAL_SETTLE_MS);

    for (uint8_t i = 0; i < BIST_ADC_SAMPLE_COUNT; i++)
    {
        samples[i] = 0;
        sorted[i] = 0;
    }

    for (uint8_t i = 0; i < BIST_ADC_SAMPLE_COUNT; i++)
    {
        rc = nau7802_read_mv(&samples[i]);
        if (rc != HAL_OK) {
            return rc;
        }

        if (i + 1U < BIST_ADC_SAMPLE_COUNT) {
            HAL_Delay(BIST_ADC_BETWEEN_SAMPLES_MS);
        }
    }

    for (uint8_t i = 0; i < BIST_ADC_SAMPLE_COUNT; i++) {
        sorted[i] = samples[i];
    }

    sort_int32_array(sorted, BIST_ADC_SAMPLE_COUNT);

    *mv_out = sorted[BIST_ADC_SAMPLE_COUNT / 2U];
    return HAL_OK;
}

static HAL_StatusTypeDef read_pin_voltage_mv(uint8_t dut_pin, int32_t *mv_out)
{
    int32_t dummy_mv = 0;

    if (mux_select_dut_output_pin(dut_pin) != 0) {
        return HAL_ERROR;
    }

    HAL_Delay(BIST_OUTPUT_SWITCH_SETTLE_MS);

    for (uint8_t i = 0; i < BIST_ADC_THROWAWAY_READS; i++)
    {
        if (nau7802_read_mv(&dummy_mv) != HAL_OK) {
            return HAL_ERROR;
        }
        HAL_Delay(BIST_ADC_BETWEEN_SAMPLES_MS);
    }

    return adc_settle_and_read_mv(mv_out);
}

static uint8_t voltage_within_threshold(BistSource src, int32_t measured_mv)
{
    int32_t expected_mv = source_expected_mv(src);

    if (src == BIST_SRC_GND) {
        return (measured_mv <= BIST_GND_MAX_MV) ? 1U : 0U;
    }

    return (abs32(measured_mv - expected_mv) <= BIST_VOLTAGE_TOL_MV) ? 1U : 0U;
}

static uint8_t read_and_validate_with_retry(uint8_t dut_pin,
                                            BistSource src,
                                            int32_t *measured_mv_out)
{
    int32_t mv1 = 0;
    int32_t mv2 = 0;

    if (read_pin_voltage_mv(dut_pin, &mv1) != HAL_OK) {
        return 0;
    }

    if (voltage_within_threshold(src, mv1))
    {
        *measured_mv_out = mv1;
        return 1;
    }

    HAL_Delay(15);

    if (read_pin_voltage_mv(dut_pin, &mv2) != HAL_OK) {
        *measured_mv_out = mv1;
        return 0;
    }

    *measured_mv_out = mv2;
    return voltage_within_threshold(src, mv2);
}

/* ---------- one full routing test ---------- */

static void run_single_route_test(uint8_t dut_pin, BistSource src)
{
    int32_t measured_mv = 0;
    int32_t expected_mv = source_expected_mv(src);
    const char *src_str = source_name(src);
    uint8_t pass;

    if (disconnect_all_pins() != HAL_OK)
    {
        bist_mark_simple("disconnect_all_pins", 0);
        return;
    }

    if (connect_pin_to_source(dut_pin, src) != HAL_OK)
    {
        bist_mark_simple("connect_pin_to_source", 0);
        return;
    }

    HAL_Delay(BIST_POST_ROUTE_SETTLE_MS);

    if (mux_select_dut_output_pin(dut_pin) != 0)
    {
        bist_uart_printf("FAIL pin=%u src=%s mux preselect failed\r\n", dut_pin, src_str);
        g_bist_total_checks++;
        g_bist_failed_checks++;
        return;
    }

    HAL_Delay(BIST_OUTPUT_SWITCH_SETTLE_MS);

    if (!verify_adg_readback(dut_pin, src))
    {
        bist_uart_printf("FAIL pin=%u src=%s ADG readback mismatch\r\n", dut_pin, src_str);
        g_bist_total_checks++;
        g_bist_failed_checks++;
        return;
    }
    else
    {
        g_bist_total_checks++;
        bist_uart_printf("PASS pin=%u src=%s ADG readback\r\n", dut_pin, src_str);
    }

    pass = read_and_validate_with_retry(dut_pin, src, &measured_mv);

    bist_mark_voltage_result(dut_pin,
                             src_str,
                             expected_mv,
                             measured_mv,
                             pass);
}

/* ---------- full exhaustive sweep ---------- */

static void run_exhaustive_switch_array_test(void)
{
    static const BistSource sources[] =
    {
        BIST_SRC_GND,
        BIST_SRC_1V8,
        BIST_SRC_2V5,
        BIST_SRC_3V3,
        BIST_SRC_4V0,
        BIST_SRC_4V5,
        BIST_SRC_5V0
    };

    bist_uart_print("---- Exhaustive switch-array / mux / ADC sweep start ----\r\n");

    for (uint8_t s = 0; s < (sizeof(sources) / sizeof(sources[0])); s++)
    {
        bist_uart_printf("Testing source %s across all 20 DUT pins...\r\n", source_name(sources[s]));

        for (uint8_t pin = 1; pin <= 20; pin++)
        {
            run_single_route_test(pin, sources[s]);
        }
    }

    bist_uart_print("---- Exhaustive switch-array / mux / ADC sweep end ----\r\n");
}

/* ---------- public entry ---------- */

void Run_BIST(void)
{
    int32_t dummy_mv = 0;

    g_bist_total_checks = 0;
    g_bist_failed_checks = 0;

    bist_uart_print("\r\n========================================\r\n");
    bist_uart_print("BIST START\r\n");
    bist_uart_print("Ensure NO IC is inserted in the fixture\r\n");
    bist_uart_print("========================================\r\n");

    bist_mark_simple("ADG chip 1 @0x70 present",
                     (adg_check_ready(ADG1_ADDR_7BIT) == HAL_OK) ? 1U : 0U);

    bist_mark_simple("ADG chip 2 @0x71 present",
                     (adg_check_ready(ADG2_ADDR_7BIT) == HAL_OK) ? 1U : 0U);

    if (nau7802_init() != HAL_OK)
    {
        bist_mark_simple("NAU7802 init", 0);
        goto cleanup;
    }
    bist_mark_simple("NAU7802 init", 1);

    HAL_Delay(100);
    if (nau7802_read_mv(&dummy_mv) != HAL_OK) {
        bist_mark_simple("NAU7802 dummy read #1", 0);
        goto cleanup;
    }
    bist_mark_simple("NAU7802 dummy read #1", 1);

    HAL_Delay(10);
    if (nau7802_read_mv(&dummy_mv) != HAL_OK) {
        bist_mark_simple("NAU7802 dummy read #2", 0);
        goto cleanup;
    }
    bist_mark_simple("NAU7802 dummy read #2", 1);

    run_exhaustive_switch_array_test();

cleanup:
    (void)disconnect_all_pins();

    bist_uart_print("----------------------------------------\r\n");
    bist_uart_printf("BIST COMPLETE: %lu total checks, %lu failed\r\n",
                     (unsigned long)g_bist_total_checks,
                     (unsigned long)g_bist_failed_checks);

    if (g_bist_failed_checks == 0) {
        bist_uart_print("BIST RESULT: PASS\r\n");
    } else {
        bist_uart_print("BIST RESULT: FAIL\r\n");
    }

    bist_uart_print("DONE\r\n\r\n");
}
