#include "main.h"
#include <stdint.h>
#include <stddef.h>

#define FLASH_START_ADDR  0x08000000UL

// This symbol usually exists in STM32CubeIDE linker scripts.
// It marks the end of the firmware image in flash.
extern uint32_t _etext;

static uint32_t crc32_update(uint32_t crc, uint8_t data)
{
    crc ^= data;

    for (uint8_t i = 0; i < 8; i++)
    {
        if (crc & 1)
        {
            crc = (crc >> 1) ^ 0xEDB88320UL;
        }
        else
        {
            crc >>= 1;
        }
    }

    return crc;
}

uint32_t firmware_crc32(void)
{
    uint32_t crc = 0xFFFFFFFFUL;

    uint8_t *start = (uint8_t *)FLASH_START_ADDR;
    uint8_t *end = (uint8_t *)&_etext;

    while (start < end)
    {
        crc = crc32_update(crc, *start);
        start++;
    }

    return crc ^ 0xFFFFFFFFUL;
}
