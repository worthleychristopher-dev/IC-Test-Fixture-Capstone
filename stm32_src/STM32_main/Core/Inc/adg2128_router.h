#ifndef ADG2128_ROUTER_H
#define ADG2128_ROUTER_H

#include "main.h"
#include <stdint.h>

typedef enum
{
    ADG_DEV_1 = 0,
    ADG_DEV_2 = 1,
    ADG_DEV_COUNT
} AdgDevice;

typedef enum
{
    ROUTE_SRC_1V8 = 0,
    ROUTE_SRC_2V5,
    ROUTE_SRC_3V3,
    ROUTE_SRC_4V0,
    ROUTE_SRC_4V5,
    ROUTE_SRC_5V0,
    ROUTE_SRC_STM32_GPIO,   // Y6
    ROUTE_SRC_GND
} RouteSource;

typedef enum
{
    DUT_PIN_1 = 1,
    DUT_PIN_2,
    DUT_PIN_3,
    DUT_PIN_4,
    DUT_PIN_5,
    DUT_PIN_6,
    DUT_PIN_7,
    DUT_PIN_8,
    DUT_PIN_9,
    DUT_PIN_10,
    DUT_PIN_11,
    DUT_PIN_12,
    DUT_PIN_13,
    DUT_PIN_14,
    DUT_PIN_15,
    DUT_PIN_16,
    DUT_PIN_17,
    DUT_PIN_18,
    DUT_PIN_19,
    DUT_PIN_20
} DutPin;

void Router_Init(void);

HAL_StatusTypeDef Router_ConnectSupplyToPin(DutPin pin, RouteSource src);
HAL_StatusTypeDef Router_DisconnectPin(DutPin pin);

HAL_StatusTypeDef Router_SetPinSource(DutPin pin, RouteSource src, uint8_t on);
HAL_StatusTypeDef Router_ClearAll(void);

const char *Router_SourceName(RouteSource src);
uint8_t Router_IsPinConnectedToSource(DutPin pin, RouteSource src);

#endif
