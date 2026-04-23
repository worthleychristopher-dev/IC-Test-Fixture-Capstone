#include "adg2128_router.h"
#include <stdint.h>

/*
 * CURRENTLY ANY FUNCTIONS IN THIS FILE ARE NOT USED AND FUNCTIONS ARE IMPLEMENTED
 * SLIGHTLY DIFFERENTLY IN test_utils.c
 *
 * ADG2128 router
 *
 * DUT pins 1..10  -> ADG chip 1 X lines
 * DUT pins 11..20 -> ADG chip 2 X lines
 *
 * Y mapping on both chips:
 *   Y0 = 1.8V
 *   Y1 = 2.5V
 *   Y2 = 3.3V
 *   Y3 = 4.0V
 *   Y4 = 4.5V
 *   Y5 = 5.0V
 *   Y6 = STM32 [5D]
 *   Y7 = unused
 *
 * NOTE:
 * SCL/SDA are only the I2C control interface and are NOT routed signals.
 */

extern I2C_HandleTypeDef hi2c1;

/* Set these to your two 7-bit I2C addresses */
static const uint8_t g_adg_addr7[ADG_DEV_COUNT] =
{
    0x70,   // ADG chip 1
    0x71    // ADG chip 2
};

/*
 * Shadow matrix:
 * g_shadow[device][x] is an 8-bit mask of enabled Y connections for that X.
 */
static uint8_t g_shadow[ADG_DEV_COUNT][12];

/* ---------------- Low-level ADG2128 crosspoint write ---------------- */

static HAL_StatusTypeDef ADG2128_WriteCrosspoint(AdgDevice dev,
                                                 uint8_t x,
                                                 uint8_t y,
                                                 uint8_t on,
                                                 uint8_t ldsw)
{
    if (dev >= ADG_DEV_COUNT) return HAL_ERROR;
    if (x > 11 || y > 7) return HAL_ERROR;

    uint8_t tx[2];

    /* Byte 0: DATA AX3 AX2 AX1 AX0 AY2 AY1 AY0 */
    tx[0] = ((on & 0x01U) << 7) |
            ((x  & 0x0FU) << 3) |
            ((y  & 0x07U) << 0);

    /* Byte 1: bit0 = LDSW */
    tx[1] = (ldsw & 0x01U);

    return HAL_I2C_Master_Transmit(&hi2c1,
                                   (uint16_t)(g_adg_addr7[dev] << 1),
                                   tx,
                                   2,
                                   HAL_MAX_DELAY);
}

static void Shadow_Set(AdgDevice dev, uint8_t x, uint8_t y, uint8_t on)
{
    if (dev >= ADG_DEV_COUNT || x > 11 || y > 7) return;

    if (on) {
        g_shadow[dev][x] |= (uint8_t)(1U << y);
    } else {
        g_shadow[dev][x] &= (uint8_t)~(1U << y);
    }
}

/* ---------------- DUT pin -> chip/X mapping ---------------- */

static int Router_MapDutPin(DutPin pin, AdgDevice *dev_out, uint8_t *x_out)
{
    switch (pin)
    {
        /* ADG chip 1 */
        case DUT_PIN_1:  *dev_out = ADG_DEV_1; *x_out = 5; return 0;
        case DUT_PIN_2:  *dev_out = ADG_DEV_1; *x_out = 4; return 0;
        case DUT_PIN_3:  *dev_out = ADG_DEV_1; *x_out = 3; return 0;
        case DUT_PIN_4:  *dev_out = ADG_DEV_1; *x_out = 2; return 0;
        case DUT_PIN_5:  *dev_out = ADG_DEV_1; *x_out = 1; return 0;
        case DUT_PIN_6:  *dev_out = ADG_DEV_1; *x_out = 0; return 0;
        case DUT_PIN_7:  *dev_out = ADG_DEV_1; *x_out = 9; return 0;
        case DUT_PIN_8:  *dev_out = ADG_DEV_1; *x_out = 8; return 0;
        case DUT_PIN_9:  *dev_out = ADG_DEV_1; *x_out = 7; return 0;
        case DUT_PIN_10: *dev_out = ADG_DEV_1; *x_out = 6; return 0;

        /* ADG chip 2 */
        case DUT_PIN_11: *dev_out = ADG_DEV_2; *x_out = 5; return 0;
        case DUT_PIN_12: *dev_out = ADG_DEV_2; *x_out = 4; return 0;
        case DUT_PIN_13: *dev_out = ADG_DEV_2; *x_out = 3; return 0;
        case DUT_PIN_14: *dev_out = ADG_DEV_2; *x_out = 2; return 0;
        case DUT_PIN_15: *dev_out = ADG_DEV_2; *x_out = 1; return 0;
        case DUT_PIN_16: *dev_out = ADG_DEV_2; *x_out = 0; return 0;
        case DUT_PIN_17: *dev_out = ADG_DEV_2; *x_out = 9; return 0;
        case DUT_PIN_18: *dev_out = ADG_DEV_2; *x_out = 8; return 0;
        case DUT_PIN_19: *dev_out = ADG_DEV_2; *x_out = 7; return 0;
        case DUT_PIN_20: *dev_out = ADG_DEV_2; *x_out = 6; return 0;

        default:
            return -1;
    }
}

static int Router_MapSource(RouteSource src, uint8_t *y_out)
{
    switch (src)
    {
        case ROUTE_SRC_1V8:       *y_out = 0; return 0;
        case ROUTE_SRC_2V5:       *y_out = 1; return 0;
        case ROUTE_SRC_3V3:       *y_out = 2; return 0;
        case ROUTE_SRC_4V0:       *y_out = 3; return 0;
        case ROUTE_SRC_4V5:       *y_out = 4; return 0;
        case ROUTE_SRC_5V0:       *y_out = 5; return 0;
        case ROUTE_SRC_STM32_GPIO:*y_out = 6; return 0;
        case ROUTE_SRC_GND:       *y_out = 7; return 0;
        default:
            return -1;
    }
}

/* ---------------- Public API ---------------- */

void Router_Init(void)
{
    uint8_t dev, x;
    for (dev = 0; dev < ADG_DEV_COUNT; dev++) {
        for (x = 0; x < 12; x++) {
            g_shadow[dev][x] = 0;
        }
    }
}

/*
 * Direct helper: on/off one specific DUT pin to one specific source.
 */
HAL_StatusTypeDef Router_SetPinSource(DutPin pin, RouteSource src, uint8_t on)
{
    AdgDevice dev;
    uint8_t x, y;

    if (Router_MapDutPin(pin, &dev, &x) != 0) return HAL_ERROR;
    if (Router_MapSource(src, &y) != 0) return HAL_ERROR;

    HAL_StatusTypeDef rc = ADG2128_WriteCrosspoint(dev, x, y, on, 1);
    if (rc == HAL_OK) {
        Shadow_Set(dev, x, y, on);
    }

    return rc;
}

/*
 * Connect one source to one DUT pin.
 */
HAL_StatusTypeDef Router_ConnectSupplyToPin(DutPin pin, RouteSource src)
{
    return Router_SetPinSource(pin, src, 1);
}

/*
 * Disconnect all routed sources from one DUT pin.
 * This is useful if you want one DUT pin to only ever have one active source.
 */
HAL_StatusTypeDef Router_DisconnectPin(DutPin pin)
{
    AdgDevice dev;
    uint8_t x;
    uint8_t y;
    HAL_StatusTypeDef overall = HAL_OK;

    if (Router_MapDutPin(pin, &dev, &x) != 0) return HAL_ERROR;

    for (y = 0; y <= 6; y++)
    {
        if (g_shadow[dev][x] & (1U << y))
        {
            HAL_StatusTypeDef rc = ADG2128_WriteCrosspoint(dev, x, y, 0, 1);
            if (rc == HAL_OK) {
                Shadow_Set(dev, x, y, 0);
            } else {
                overall = rc;
            }
        }
    }

    return overall;
}

/*
 * Clear all known routes on both chips.
 */
HAL_StatusTypeDef Router_ClearAll(void)
{
    HAL_StatusTypeDef overall = HAL_OK;
    uint8_t dev, x, y;

    for (dev = 0; dev < ADG_DEV_COUNT; dev++)
    {
        for (x = 0; x < 12; x++)
        {
            for (y = 0; y < 8; y++)
            {
                if (g_shadow[dev][x] & (1U << y))
                {
                    HAL_StatusTypeDef rc =
                        ADG2128_WriteCrosspoint((AdgDevice)dev, x, y, 0, 1);

                    if (rc == HAL_OK) {
                        Shadow_Set((AdgDevice)dev, x, y, 0);
                    } else {
                        overall = rc;
                    }
                }
            }
        }
    }

    return overall;
}

const char *Router_SourceName(RouteSource src)
{
    switch (src)
    {
        case ROUTE_SRC_1V8:        return "1.8V";
        case ROUTE_SRC_2V5:        return "2.5V";
        case ROUTE_SRC_3V3:        return "3.3V";
        case ROUTE_SRC_4V0:        return "4.0V";
        case ROUTE_SRC_4V5:        return "4.5V";
        case ROUTE_SRC_5V0:        return "5.0V";
        case ROUTE_SRC_STM32_GPIO: return "STM32_GPIO";
        case ROUTE_SRC_GND:        return "GND";
        default:                   return "UNKNOWN";
    }
}

uint8_t Router_IsPinConnectedToSource(DutPin pin, RouteSource src)
{
    AdgDevice dev;
    uint8_t x, y;

    if (Router_MapDutPin(pin, &dev, &x) != 0) return 0;
    if (Router_MapSource(src, &y) != 0) return 0;

    return (g_shadow[dev][x] & (1U << y)) ? 1U : 0U;
}
