#include "main.h"
#include <stdint.h>

/*
 * Assumptions:
 * - All three ADG708 8:1 muxes share address lines:
 *      A0 -> PA1
 *      A1 -> PA6
 *      A2 -> PA7
 *
 * - The ADG709 4:1 mux uses:
 *      A0 -> PA4
 *      A1 -> PA5
 *
 * - EN pins are hardwired/enabled elsewhere.
 * - All muxes are single-supply and logic-compatible with STM32 GPIO.
 */

/* ---------- GPIO pin definitions ---------- */

/* Shared ADG708 address lines */
#define MUX8_A0_GPIO_Port   GPIOA
#define MUX8_A0_Pin         GPIO_PIN_1

#define MUX8_A1_GPIO_Port   GPIOA
#define MUX8_A1_Pin         GPIO_PIN_6

#define MUX8_A2_GPIO_Port   GPIOA
#define MUX8_A2_Pin         GPIO_PIN_7

/* ADG709 address lines */
#define MUX4_A0_GPIO_Port   GPIOA
#define MUX4_A0_Pin         GPIO_PIN_4

#define MUX4_A1_GPIO_Port   GPIOA
#define MUX4_A1_Pin         GPIO_PIN_5


typedef struct
{
    uint8_t mux8_channel;   /* 1..8 */
    uint8_t mux4_channel;   /* 1..4 */
} OutputRoute;


/* ---------- Low-level helpers ---------- */

static void write_gpio_bit(GPIO_TypeDef *port, uint16_t pin, uint8_t bit_val)
{
    HAL_GPIO_WritePin(port, pin, bit_val ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/*
 * ADG708 truth table:
 * A2 A1 A0
 * 000 -> S1
 * 001 -> S2
 * 010 -> S3
 * 011 -> S4
 * 100 -> S5
 * 101 -> S6
 * 110 -> S7
 * 111 -> S8
 */
void mux708_set_channel(uint8_t channel)
{
    if ((channel < 1U) || (channel > 8U)) {
        return;
    }

    uint8_t sel = (uint8_t)(channel - 1U);

    write_gpio_bit(MUX8_A0_GPIO_Port, MUX8_A0_Pin, (uint8_t)((sel >> 0) & 0x01U));
    write_gpio_bit(MUX8_A1_GPIO_Port, MUX8_A1_Pin, (uint8_t)((sel >> 1) & 0x01U));
    write_gpio_bit(MUX8_A2_GPIO_Port, MUX8_A2_Pin, (uint8_t)((sel >> 2) & 0x01U));
}

/*
 * ADG709 truth table:
 * A1 A0
 * 00 -> S1
 * 01 -> S2
 * 10 -> S3
 * 11 -> S4
 */
void mux709_set_channel(uint8_t channel)
{
    if ((channel < 1U) || (channel > 4U)) {
        return;
    }

    uint8_t sel = (uint8_t)(channel - 1U);

    write_gpio_bit(MUX4_A0_GPIO_Port, MUX4_A0_Pin, (uint8_t)((sel >> 0) & 0x01U));
    write_gpio_bit(MUX4_A1_GPIO_Port, MUX4_A1_Pin, (uint8_t)((sel >> 1) & 0x01U));
}

/*
 * Maps a DUT output pin to:
 * - which channel on the relevant 8:1 mux
 * - which input on the 4:1 mux
 *
 * Mux tree:
 *
 * 8:1 mux 1:
 *   S1 pin8
 *   S2 pin7
 *   S3 pin6
 *   S4 pin5
 *   S5 pin1
 *   S6 pin2
 *   S7 pin3
 *   S8 pin4
 *
 * 8:1 mux 2:
 *   S1 pin16
 *   S2 pin15
 *   S3 pin14
 *   S4 pin13
 *   S5 pin9
 *   S6 pin10
 *   S7 pin11
 *   S8 pin12
 *
 * 8:1 mux 3:
 *   S1 pin20
 *   S2 pin19
 *   S3 pin18
 *   S4 pin17
 *   S5-S8 tied low
 *
 * 4:1 mux:
 *   S1A <- mux1 output
 *   S2A <- mux2 output
 *   S3A <- mux3 output
 */
int map_output_pin_to_mux(uint8_t dut_pin, OutputRoute *route)
{
    if (route == NULL) {
        return -1;
    }

    switch (dut_pin)
    {
        /* 8:1 mux 1 -> 4:1 channel 1 */
        case 8:  route->mux8_channel = 1; route->mux4_channel = 1; return 0;
        case 7:  route->mux8_channel = 2; route->mux4_channel = 1; return 0;
        case 6:  route->mux8_channel = 3; route->mux4_channel = 1; return 0;
        case 5:  route->mux8_channel = 4; route->mux4_channel = 1; return 0;
        case 1:  route->mux8_channel = 5; route->mux4_channel = 1; return 0;
        case 2:  route->mux8_channel = 6; route->mux4_channel = 1; return 0;
        case 3:  route->mux8_channel = 7; route->mux4_channel = 1; return 0;
        case 4:  route->mux8_channel = 8; route->mux4_channel = 1; return 0;

        /* 8:1 mux 2 -> 4:1 channel 2 */
        case 16: route->mux8_channel = 1; route->mux4_channel = 2; return 0;
        case 15: route->mux8_channel = 2; route->mux4_channel = 2; return 0;
        case 14: route->mux8_channel = 3; route->mux4_channel = 2; return 0;
        case 13: route->mux8_channel = 4; route->mux4_channel = 2; return 0;
        case 9:  route->mux8_channel = 5; route->mux4_channel = 2; return 0;
        case 10: route->mux8_channel = 6; route->mux4_channel = 2; return 0;
        case 11: route->mux8_channel = 7; route->mux4_channel = 2; return 0;
        case 12: route->mux8_channel = 8; route->mux4_channel = 2; return 0;

        /* 8:1 mux 3 -> 4:1 channel 3 */
        case 20: route->mux8_channel = 1; route->mux4_channel = 3; return 0;
        case 19: route->mux8_channel = 2; route->mux4_channel = 3; return 0;
        case 18: route->mux8_channel = 3; route->mux4_channel = 3; return 0;
        case 17: route->mux8_channel = 4; route->mux4_channel = 3; return 0;

        default:
            return -1;
    }
}

/*
 * Selects one DUT output pin through the mux tree so it reaches the ADC.
 */
int mux_select_dut_output_pin(uint8_t dut_pin)
{
    OutputRoute route;

    if (map_output_pin_to_mux(dut_pin, &route) != 0) {
        return -1;
    }

    mux708_set_channel(route.mux8_channel);
    mux709_set_channel(route.mux4_channel);
    HAL_Delay(2);

    return 0;
}
