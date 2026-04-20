#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "nau7802.h"
#include "test_utils.h"

/*
 * NAU7802 fixed 7-bit I2C address from datasheet = 0x2A
 * STM32 HAL expects left-shifted 8-bit address.
 */
#define NAU7802_ADDR_7BIT   0x2A
#define NAU7802_ADDR_HAL    (NAU7802_ADDR_7BIT << 1)

/*
 * IMPORTANT:
 * User clarified the NAU7802 is on I2C2:
 *   SDA = PB11
 *   SCL = PB10
 */
extern I2C_HandleTypeDef hi2c2;

/* ---------- Register addresses ---------- */
#define NAU7802_REG_PU_CTRL     0x00
#define NAU7802_REG_CTRL1       0x01
#define NAU7802_REG_CTRL2       0x02
#define NAU7802_REG_ADC_B2      0x12
#define NAU7802_REG_ADC_B1      0x13
#define NAU7802_REG_ADC_B0      0x14
#define NAU7802_REG_ADC_CTRL1   0x15
#define NAU7802_REG_ADC_CTRL3   0x1B
#define NAU7802_REG_PWR_CTRL    0x1C

/* ---------- PU_CTRL bits ---------- */
#define NAU7802_PU_CTRL_AVDDS   (1U << 7)
#define NAU7802_PU_CTRL_OSCS    (1U << 6)
#define NAU7802_PU_CTRL_CR      (1U << 5)
#define NAU7802_PU_CTRL_CS      (1U << 4)
#define NAU7802_PU_CTRL_PUR     (1U << 3)
#define NAU7802_PU_CTRL_PUA     (1U << 2)
#define NAU7802_PU_CTRL_PUD     (1U << 1)
#define NAU7802_PU_CTRL_RR      (1U << 0)

/* ---------- ADC_CTRL1 bits ---------- */
#define NAU7802_ADC_CTRL1_REG_CHPS_RECOMMENDED   (0x3U << 4)   /* bits 5:4 = 11 */

/* ---------- Local helpers ---------- */

extern UART_HandleTypeDef huart1;

static void nau_uart_print(const char *s)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)s, (uint16_t)strlen(s), HAL_MAX_DELAY);
}

static void nau_uart_printf(const char *fmt, ...)
{
    char buf[128];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    nau_uart_print(buf);
}


static HAL_StatusTypeDef nau7802_write_reg(uint8_t reg, uint8_t value)
{
    uint8_t tx[2] = { reg, value };
    return HAL_I2C_Master_Transmit(&hi2c2, NAU7802_ADDR_HAL, tx, 2, 100);
}

static HAL_StatusTypeDef nau7802_read_reg(uint8_t reg, uint8_t *value_out)
{
    if (value_out == NULL) {
        return HAL_ERROR;
    }

    HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c2, NAU7802_ADDR_HAL, &reg, 1, 100);
    if (rc != HAL_OK) {
        return rc;
    }

    return HAL_I2C_Master_Receive(&hi2c2, NAU7802_ADDR_HAL, value_out, 1, 100);
}

static HAL_StatusTypeDef nau7802_read_regs(uint8_t start_reg, uint8_t *buf, uint16_t len)
{
    if ((buf == NULL) || (len == 0U)) {
        return HAL_ERROR;
    }

    HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c2, NAU7802_ADDR_HAL, &start_reg, 1, 100);
    if (rc != HAL_OK) {
        return rc;
    }

    return HAL_I2C_Master_Receive(&hi2c2, NAU7802_ADDR_HAL, buf, len, 100);
}

static HAL_StatusTypeDef nau7802_update_bits(uint8_t reg, uint8_t mask, uint8_t value)
{
    uint8_t reg_val;
    HAL_StatusTypeDef rc = nau7802_read_reg(reg, &reg_val);
    if (rc != HAL_OK) {
        return rc;
    }

    reg_val = (uint8_t)((reg_val & (uint8_t)(~mask)) | (value & mask));
    return nau7802_write_reg(reg, reg_val);
}

/*
 * Convert signed 24-bit ADC code to mV.
 *
 * Datasheet full-scale differential input:
 *   +/- 0.5 * (VREF / PGA)
 *
 * Therefore:
 *   input_mv = raw * (0.5 * VREF / PGA) / 8388607
 */
static int32_t nau7802_raw_to_mv(int32_t raw)
{
    const int32_t vref_mv = NAU7802_VREF_MV_DEFAULT;
    const int32_t pga     = NAU7802_PGA_DEFAULT;
    const int32_t fs_code = 8388607L;
    const int32_t offset = 1650;
    const float scale_factor = 1.5; // from 10//20 resistor divider

    const int32_t fs_input_mv = (vref_mv / 2L) / pga;

    int64_t mv = ((int64_t)raw * (int64_t)fs_input_mv) / (int64_t)fs_code;
    int64_t scaled_mv = (mv + offset) * scale_factor;
    return (int32_t)scaled_mv;
}

/* ---------- Public API ---------- */

HAL_StatusTypeDef nau7802_reset(void)
{
    HAL_StatusTypeDef rc;

    rc = nau7802_write_reg(NAU7802_REG_PU_CTRL, NAU7802_PU_CTRL_RR);
    if (rc != HAL_OK) {
        return rc;
    }

    HAL_Delay(1);

    rc = nau7802_write_reg(NAU7802_REG_PU_CTRL, 0x00);
    if (rc != HAL_OK) {
        return rc;
    }

    HAL_Delay(1);
    return HAL_OK;
}

HAL_StatusTypeDef nau7802_wait_powerup(uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();
    uint8_t reg_val = 0;

    while ((HAL_GetTick() - start) < timeout_ms)
    {
        if (nau7802_read_reg(NAU7802_REG_PU_CTRL, &reg_val) != HAL_OK) {
            return HAL_ERROR;
        }

        if (reg_val & NAU7802_PU_CTRL_PUR) {
            return HAL_OK;
        }

        HAL_Delay(1);
    }

    return HAL_TIMEOUT;
}

HAL_StatusTypeDef nau7802_init(void)
{
    HAL_StatusTypeDef rc;

    nau_uart_print("NAU: init start\r\n");

    rc = HAL_I2C_IsDeviceReady(&hi2c2, NAU7802_ADDR_HAL, 3, 100);
    nau_uart_printf("NAU: IsDeviceReady rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_reset();
    nau_uart_printf("NAU: reset rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_write_reg(NAU7802_REG_PU_CTRL,
                           (uint8_t)(NAU7802_PU_CTRL_PUD | NAU7802_PU_CTRL_PUA));
    nau_uart_printf("NAU: write PU_CTRL rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_wait_powerup(100);
    nau_uart_printf("NAU: wait powerup rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_write_reg(NAU7802_REG_CTRL1, 0x00);
    nau_uart_printf("NAU: write CTRL1 rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_write_reg(NAU7802_REG_CTRL2, 0x00);
    nau_uart_printf("NAU: write CTRL2 rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_write_reg(NAU7802_REG_ADC_CTRL1, NAU7802_ADC_CTRL1_REG_CHPS_RECOMMENDED);
    nau_uart_printf("NAU: write ADC_CTRL1 rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_write_reg(NAU7802_REG_ADC_CTRL3, 0x00);
    nau_uart_printf("NAU: write ADC_CTRL3 rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_write_reg(NAU7802_REG_PWR_CTRL, 0x00);
    nau_uart_printf("NAU: write PWR_CTRL rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_update_bits(NAU7802_REG_PU_CTRL, NAU7802_PU_CTRL_CS, 0x00);
    nau_uart_printf("NAU: clear CS rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    rc = nau7802_update_bits(NAU7802_REG_PU_CTRL, NAU7802_PU_CTRL_CS, NAU7802_PU_CTRL_CS);
    nau_uart_printf("NAU: set CS rc=%d\r\n", rc);
    if (rc != HAL_OK) {
        return rc;
    }

    nau_uart_print("NAU: init OK\r\n");
    return HAL_OK;
}

HAL_StatusTypeDef nau7802_wait_conversion_ready(uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();
    uint8_t reg_val = 0;

    while ((HAL_GetTick() - start) < timeout_ms)
    {
        if (nau7802_read_reg(NAU7802_REG_PU_CTRL, &reg_val) != HAL_OK) {
            return HAL_ERROR;
        }

        if (reg_val & NAU7802_PU_CTRL_CR) {
            return HAL_OK;
        }

        HAL_Delay(1);
    }

    return HAL_TIMEOUT;
}

HAL_StatusTypeDef nau7802_read_raw(int32_t *raw_out)
{
    if (raw_out == NULL) {
        return HAL_ERROR;
    }

    HAL_StatusTypeDef rc = nau7802_wait_conversion_ready(500);
    if (rc != HAL_OK) {
        return rc;
    }

    uint8_t buf[3] = {0};
    rc = nau7802_read_regs(NAU7802_REG_ADC_B2, buf, 3);
    if (rc != HAL_OK) {
        return rc;
    }

    int32_t raw = ((int32_t)buf[0] << 16) |
                  ((int32_t)buf[1] << 8)  |
                  ((int32_t)buf[2] << 0);

    if (raw & 0x00800000L) {
        raw |= 0xFF000000L;
    }

    *raw_out = raw;
    return HAL_OK;
}

HAL_StatusTypeDef nau7802_read_mv(int32_t *mv_out)
{
    if (mv_out == NULL) {
        return HAL_ERROR;
    }

    int32_t raw;
    HAL_StatusTypeDef rc = nau7802_read_raw(&raw);
    if (rc != HAL_OK) {
        return rc;
    }
//    test_uart_printf("ADC raw bits read: %d",raw);  //print raw bits
    *mv_out = nau7802_raw_to_mv(raw);
    return HAL_OK;
}
