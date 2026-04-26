/*
 * fault_handling.c
 *
 * Best-effort fixture / insertion fault handling for the digital IC test fixture.
 */

#include "fault_handling.h"
#include "mux_utils.h"
#include "nau7802.h"

#include <stdio.h>
#include <string.h>
#include <stdarg.h>

extern I2C_HandleTypeDef hi2c1;
extern UART_HandleTypeDef huart1;

/* ---------- UART helpers ---------- */

static void fault_uart_print(const char *s)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)s, (uint16_t)strlen(s), HAL_MAX_DELAY);
}

static void fault_uart_printf(const char *fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    fault_uart_print(buf);
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

/* ---------- Timing / thresholds ---------- */

#define FAULT_ADC_OUTPUT_SWITCH_SETTLE_MS   8U
#define FAULT_ADC_INITIAL_SETTLE_MS         20U
#define FAULT_ADC_BETWEEN_SAMPLES_MS        4U
#define FAULT_ADC_SAMPLE_COUNT              5U
#define FAULT_PRECHECK_POWER_SETTLE_MS      25U
#define FAULT_PRECHECK_STIM_SETTLE_MS       10U

#define FAULT_FLOAT_MIN_MV                  1200
#define FAULT_FLOAT_MAX_MV                  2000

#define FAULT_BAD_INSERTION_MIN_COUNT       1

typedef enum
{
    FAULT_ROUTE_SRC_1V8 = 0,
    FAULT_ROUTE_SRC_2V5,
    FAULT_ROUTE_SRC_3V3,
    FAULT_ROUTE_SRC_4V0,
    FAULT_ROUTE_SRC_4V5,
    FAULT_ROUTE_SRC_5V0,
    FAULT_ROUTE_SRC_STM32_GPIO,
    FAULT_ROUTE_SRC_GND
} FaultRouteSource;

typedef enum
{
    PIN_STATE_LOW = 0,
    PIN_STATE_HIGH,
    PIN_STATE_HIGHZ,
    PIN_STATE_INVALID
} FaultPinState;

/* ---------- local helpers ---------- */

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

static int fault_vcc_mv_to_route_source(int32_t vcc_mv, FaultRouteSource *src_out)
{
    if (src_out == NULL) {
        return -1;
    }

    switch (vcc_mv)
    {
        case 1800: *src_out = FAULT_ROUTE_SRC_1V8; return 0;
        case 2500: *src_out = FAULT_ROUTE_SRC_2V5; return 0;
        case 3300: *src_out = FAULT_ROUTE_SRC_3V3; return 0;
        case 4000: *src_out = FAULT_ROUTE_SRC_4V0; return 0;
        case 4500: *src_out = FAULT_ROUTE_SRC_4V5; return 0;
        case 5000: *src_out = FAULT_ROUTE_SRC_5V0; return 0;
        default: return -1;
    }
}

static int fault_route_source_to_y(FaultRouteSource source, uint8_t *y_out)
{
    if (y_out == NULL) {
        return -1;
    }

    switch (source)
    {
        case FAULT_ROUTE_SRC_1V8:        *y_out = ADG_Y_1V8;   return 0;
        case FAULT_ROUTE_SRC_2V5:        *y_out = ADG_Y_2V5;   return 0;
        case FAULT_ROUTE_SRC_3V3:        *y_out = ADG_Y_3V3;   return 0;
        case FAULT_ROUTE_SRC_4V0:        *y_out = ADG_Y_4V0;   return 0;
        case FAULT_ROUTE_SRC_4V5:        *y_out = ADG_Y_4V5;   return 0;
        case FAULT_ROUTE_SRC_5V0:        *y_out = ADG_Y_5V0;   return 0;
        case FAULT_ROUTE_SRC_STM32_GPIO: *y_out = ADG_Y_STM32; return 0;
        case FAULT_ROUTE_SRC_GND:        *y_out = ADG_Y_GND;   return 0;
        default: return -1;
    }
}

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

    tx[1] = 0x01U;

    return HAL_I2C_Master_Transmit(&hi2c1,
                                   (uint16_t)(addr7 << 1),
                                   tx,
                                   2,
                                   100);
}

static HAL_StatusTypeDef disconnect_dut_pin(uint8_t dut_pin)
{
    uint8_t addr7, x;
    HAL_StatusTypeDef overall = HAL_OK;

    if (map_dut_pin(dut_pin, &addr7, &x) != 0) {
        return HAL_ERROR;
    }

    for (uint8_t y = 0; y <= 7; y++)
    {
        HAL_StatusTypeDef rc = adg_write_crosspoint(addr7, x, y, 0);
        if (rc != HAL_OK) {
            overall = rc;
        }
    }

    return overall;
}

static void disconnect_declared_pins(const ParsedState *info)
{
    if (info == NULL) {
        return;
    }

    fault_uart_print("Preflight: clearing declared pins\r\n");

    if (info->prm_set)
    {
        (void)disconnect_dut_pin(info->vcc_pin);
        (void)disconnect_dut_pin(info->gnd_pin);
    }

    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        (void)disconnect_dut_pin(info->ins[i]);
    }

    for (uint8_t i = 0; i < info->n_outs; i++)
    {
        (void)disconnect_dut_pin(info->outs[i]);
    }

    fault_uart_print("Preflight: declared pins cleared\r\n");
}

static HAL_StatusTypeDef connect_dut_pin_to_source(uint8_t dut_pin, FaultRouteSource source)
{
    uint8_t addr7, x, y;

    if (map_dut_pin(dut_pin, &addr7, &x) != 0) {
        return HAL_ERROR;
    }

    if (fault_route_source_to_y(source, &y) != 0) {
        return HAL_ERROR;
    }

    if (disconnect_dut_pin(dut_pin) != HAL_OK) {
        return HAL_ERROR;
    }

    return adg_write_crosspoint(addr7, x, y, 1);
}

static HAL_StatusTypeDef adc_settle_and_read_mv(int32_t *mv_out)
{
    HAL_StatusTypeDef rc;
    int32_t samples[FAULT_ADC_SAMPLE_COUNT];
    int32_t sorted[FAULT_ADC_SAMPLE_COUNT];

    if (mv_out == NULL) {
        return HAL_ERROR;
    }

    HAL_Delay(FAULT_ADC_INITIAL_SETTLE_MS);

    for (uint8_t i = 0; i < FAULT_ADC_SAMPLE_COUNT; i++)
    {
        rc = nau7802_read_mv(&samples[i]);
        if (rc != HAL_OK) {
            return rc;
        }

        sorted[i] = samples[i];

        if (i + 1U < FAULT_ADC_SAMPLE_COUNT) {
            HAL_Delay(FAULT_ADC_BETWEEN_SAMPLES_MS);
        }
    }

    sort_int32_array(sorted, FAULT_ADC_SAMPLE_COUNT);
    *mv_out = sorted[FAULT_ADC_SAMPLE_COUNT / 2U];
    return HAL_OK;
}

static HAL_StatusTypeDef read_dut_pin_mv(uint8_t dut_pin, int32_t *mv_out)
{
    if (mux_select_dut_output_pin(dut_pin) != 0) {
        return HAL_ERROR;
    }

    HAL_Delay(FAULT_ADC_OUTPUT_SWITCH_SETTLE_MS);

    return adc_settle_and_read_mv(mv_out);
}

static FaultPinState classify_pin_state(int32_t mv, int32_t vin_low_mv, int32_t vin_high_mv)
{
    if ((mv >= FAULT_FLOAT_MIN_MV) && (mv <= FAULT_FLOAT_MAX_MV)) {
        return PIN_STATE_HIGHZ;
    }

    if (mv <= vin_low_mv) {
        return PIN_STATE_LOW;
    }

    if (mv >= vin_high_mv) {
        return PIN_STATE_HIGH;
    }

    return PIN_STATE_INVALID;
}

static int count_nonpower_drivable_inputs(const ParsedState *info)
{
    int count = 0;

    if (info == NULL) {
        return 0;
    }

    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        uint8_t pin = info->ins[i];

        if ((pin == info->vcc_pin) || (pin == info->gnd_pin)) {
            continue;
        }

        if (info->vip_kind[i] == VIP_KIND_CLK) {
            continue;
        }

        count++;
    }

    return count;
}

static HAL_StatusTypeDef drive_all_nonpower_inputs(const ParsedState *info,
                                                   FaultRouteSource source)
{
    if (info == NULL) {
        return HAL_ERROR;
    }

    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        uint8_t pin = info->ins[i];

        if ((pin == info->vcc_pin) || (pin == info->gnd_pin)) {
            continue;
        }

        if (info->vip_kind[i] == VIP_KIND_CLK) {
            continue;
        }

        if (connect_dut_pin_to_source(pin, source) != HAL_OK) {
            return HAL_ERROR;
        }
    }

    return HAL_OK;
}

static HAL_StatusTypeDef read_output_state_vector(const ParsedState *info,
                                                  FaultPinState *states_out,
                                                  uint8_t *highz_count_out,
                                                  uint8_t *invalid_count_out)
{
    uint8_t highz_count = 0;
    uint8_t invalid_count = 0;

    if ((info == NULL) || (states_out == NULL) ||
        (highz_count_out == NULL) || (invalid_count_out == NULL))
    {
        return HAL_ERROR;
    }

    for (uint8_t i = 0; i < info->n_outs; i++)
    {
        int32_t mv = 0;
        uint8_t pin = info->outs[i];

        if (read_dut_pin_mv(pin, &mv) != HAL_OK) {
            return HAL_ERROR;
        }

        states_out[i] = classify_pin_state(mv,
                                            info->vin_low_mv,
                                            info->vin_high_mv);

        if (states_out[i] == PIN_STATE_HIGHZ) {
            highz_count++;
        }
        else if (states_out[i] == PIN_STATE_INVALID) {
            invalid_count++;
        }
    }

    *highz_count_out = highz_count;
    *invalid_count_out = invalid_count;

    return HAL_OK;
}

static uint8_t state_vectors_have_any_change(const FaultPinState *a,
                                             const FaultPinState *b,
                                             uint8_t n)
{
    for (uint8_t i = 0; i < n; i++)
    {
        if (a[i] != b[i]) {
            return 1U;
        }
    }

    return 0U;
}

/*
 * Generic LOW/HIGH preflight is only safe for simple combinational-style ICs.
 * Clocked / serial / sequential parts need ordered pin behavior.
 * Bus transceivers like HC245 also need special handling because direction/OE
 * pins can disable or reverse the pins being measured.
 */
static uint8_t preflight_is_special_controlled_ic(const ParsedState *info)
{
    if (info == NULL) {
        return 1U;
    }

    if ((info->n_ins >= 9U) && (info->n_outs >= 8U)) {
        return 1U;
    }

    for (uint8_t i = 0; i < info->n_ins; i++)
    {
        if (info->vip_kind[i] == VIP_KIND_CLK) {
            return 1U;
        }

        if (info->vip_kind[i] == VIP_KIND_BIN)
        {
            const char *s = info->vip_bin[i];

            if (s != NULL)
            {
                for (uint8_t j = 0; s[j] != '\0'; j++)
                {
                    if ((s[j] == 'R') || (s[j] == 'F')) {
                        return 1U;
                    }
                }
            }
        }
    }

    return 0U;
}

const char *Fault_ResultString(FaultResult result)
{
    switch (result)
    {
        case FAULT_RESULT_OK:
            return "OK";
        case FAULT_RESULT_CONFIG_ERROR:
            return "CONFIG_ERROR";
        case FAULT_RESULT_HARDWARE_FAULT:
            return "HARDWARE_FAULT";
        case FAULT_RESULT_NO_IC_DETECTED:
            return "NO_IC_DETECTED";
        case FAULT_RESULT_BAD_INSERTION:
            return "BAD_INSERTION";
        default:
            return "UNKNOWN";
    }
}

FaultResult Fault_RunPreflight(const ParsedState *info, int32_t vcc_mv)
{
    FaultRouteSource vcc_source;

    FaultPinState low_states[MAX_PINS];
    FaultPinState high_states[MAX_PINS];

    uint8_t low_highz = 0;
    uint8_t low_invalid = 0;
    uint8_t high_highz = 0;
    uint8_t high_invalid = 0;

    if (info == NULL)
    {
        fault_uart_print("ERR: info is NULL\r\n");
        return FAULT_RESULT_CONFIG_ERROR;
    }

    if (!info->prm_set || !info->vin_set)
    {
        fault_uart_print("ERR: PRM and VIN must be configured before TEST\r\n");
        return FAULT_RESULT_CONFIG_ERROR;
    }

    if (fault_vcc_mv_to_route_source(vcc_mv, &vcc_source) != 0)
    {
        fault_uart_printf("ERR: unsupported VCC = %ld mV\r\n", (long)vcc_mv);
        return FAULT_RESULT_CONFIG_ERROR;
    }

    fault_uart_print("Preflight fault check start\r\n");

    disconnect_declared_pins(info);

    fault_uart_printf("Preflight: routing VCC pin %u to %ld mV\r\n",
                      info->vcc_pin, (long)vcc_mv);

    if (connect_dut_pin_to_source(info->vcc_pin, vcc_source) != HAL_OK)
    {
        fault_uart_printf("ERR: failed to route VCC pin %u\r\n", info->vcc_pin);
        disconnect_declared_pins(info);
        return FAULT_RESULT_HARDWARE_FAULT;
    }

    fault_uart_printf("Preflight: routing GND pin %u to GND\r\n", info->gnd_pin);

    if (connect_dut_pin_to_source(info->gnd_pin, FAULT_ROUTE_SRC_GND) != HAL_OK)
    {
        fault_uart_printf("ERR: failed to route GND pin %u\r\n", info->gnd_pin);
        disconnect_declared_pins(info);
        return FAULT_RESULT_HARDWARE_FAULT;
    }

    fault_uart_print("Preflight: power pins routed\r\n");

    HAL_Delay(FAULT_PRECHECK_POWER_SETTLE_MS);

    if (info->n_outs == 0)
    {
        fault_uart_print("Preflight: no OUT pins declared, skipping insertion detection\r\n");
        disconnect_declared_pins(info);
        return FAULT_RESULT_OK;
    }

    /*
     * For controlled/bidirectional/sequential ICs, passive outputs may all be
     * high-Z before the actual functional test configures OE/DIR/LOAD/CLK.
     * Therefore, this path never rejects the IC based only on passive high-Z.
     */
    if (preflight_is_special_controlled_ic(info))
    {
        fault_uart_print("Preflight: controlled/serial IC detected, passive scan only\r\n");

        if (read_output_state_vector(info,
                                     low_states,
                                     &low_highz,
                                     &low_invalid) != HAL_OK)
        {
            fault_uart_print("ERR: failed passive output scan\r\n");
            disconnect_declared_pins(info);
            return FAULT_RESULT_HARDWARE_FAULT;
        }

        fault_uart_printf("Preflight passive counts: highz=%u invalid=%u n_outs=%u\r\n",
                          low_highz,
                          low_invalid,
                          info->n_outs);

        disconnect_declared_pins(info);

        if ((low_highz + low_invalid) == info->n_outs)
        {
            fault_uart_print("Preflight warning: all outputs passive/high-Z; continuing for controlled IC\r\n");
        }

        fault_uart_print("Preflight fault check passed\r\n");
        return FAULT_RESULT_OK;
    }

    if (count_nonpower_drivable_inputs(info) > 0)
    {
        fault_uart_print("Preflight: driving all non-power inputs LOW\r\n");

        if (drive_all_nonpower_inputs(info, FAULT_ROUTE_SRC_GND) != HAL_OK)
        {
            fault_uart_print("ERR: failed to drive preflight LOW stimulus\r\n");
            disconnect_declared_pins(info);
            return FAULT_RESULT_HARDWARE_FAULT;
        }
    }

    HAL_Delay(FAULT_PRECHECK_STIM_SETTLE_MS);

    fault_uart_print("Preflight: reading LOW-state outputs\r\n");

    if (read_output_state_vector(info,
                                 low_states,
                                 &low_highz,
                                 &low_invalid) != HAL_OK)
    {
        fault_uart_print("ERR: failed to read LOW-state outputs\r\n");
        disconnect_declared_pins(info);
        return FAULT_RESULT_HARDWARE_FAULT;
    }

    if (count_nonpower_drivable_inputs(info) > 0)
    {
        fault_uart_print("Preflight: driving all non-power inputs HIGH\r\n");

        if (drive_all_nonpower_inputs(info, vcc_source) != HAL_OK)
        {
            fault_uart_print("ERR: failed to drive preflight HIGH stimulus\r\n");
            disconnect_declared_pins(info);
            return FAULT_RESULT_HARDWARE_FAULT;
        }
    }

    HAL_Delay(FAULT_PRECHECK_STIM_SETTLE_MS);

    fault_uart_print("Preflight: reading HIGH-state outputs\r\n");

    if (read_output_state_vector(info,
                                 high_states,
                                 &high_highz,
                                 &high_invalid) != HAL_OK)
    {
        fault_uart_print("ERR: failed to read HIGH-state outputs\r\n");
        disconnect_declared_pins(info);
        return FAULT_RESULT_HARDWARE_FAULT;
    }

    disconnect_declared_pins(info);

    fault_uart_printf("Preflight counts: LOW highz=%u invalid=%u, HIGH highz=%u invalid=%u, n_outs=%u\r\n",
                      low_highz,
                      low_invalid,
                      high_highz,
                      high_invalid,
                      info->n_outs);

    fault_uart_printf("Preflight changed=%u\r\n",
                      state_vectors_have_any_change(low_states, high_states, info->n_outs));

    if (((low_highz + low_invalid) == info->n_outs) &&
        ((high_highz + high_invalid) == info->n_outs))
    {
        fault_uart_print("ERR: no IC detected. Insert the IC at the TOP of the ZIF socket and retry.\r\n");
        return FAULT_RESULT_NO_IC_DETECTED;
    }

    if (((low_highz + low_invalid) >= FAULT_BAD_INSERTION_MIN_COUNT) &&
        ((high_highz + high_invalid) >= FAULT_BAD_INSERTION_MIN_COUNT) &&
        !state_vectors_have_any_change(low_states, high_states, info->n_outs))
    {
        fault_uart_print("ERR: IC may be inserted incorrectly or not fully seated.\r\n");
        fault_uart_print("ERR: Place the IC at the TOP of the ZIF socket and retry.\r\n");
        return FAULT_RESULT_BAD_INSERTION;
    }

    fault_uart_print("Preflight fault check passed\r\n");
    return FAULT_RESULT_OK;
}
