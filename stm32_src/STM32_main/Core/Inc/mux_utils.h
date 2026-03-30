#ifndef MUX_UTILS_H
#define MUX_UTILS_H

#include <stdint.h>

typedef struct
{
    uint8_t mux8_channel;
    uint8_t mux4_channel;
} OutputRoute;

void mux708_set_channel(uint8_t channel);
void mux709_set_channel(uint8_t channel);
int map_output_pin_to_mux(uint8_t dut_pin, OutputRoute *route);
int mux_select_dut_output_pin(uint8_t dut_pin);

#endif
