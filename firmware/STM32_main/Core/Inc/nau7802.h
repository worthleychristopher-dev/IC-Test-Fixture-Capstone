#ifndef NAU7802_H
#define NAU7802_H

#include "main.h"
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * NAU7802 conversion assumptions.
 *
 * Full-scale differential input = +/- 0.5 * (VREF / PGA)
 *
 * Default assumptions below:
 *   VREF = 5000 mV
 *   PGA  = 1
 *
 *
 */
#define NAU7802_VREF_MV_DEFAULT   3300L
#define NAU7802_PGA_DEFAULT       1L

HAL_StatusTypeDef nau7802_init(void);
HAL_StatusTypeDef nau7802_reset(void);
HAL_StatusTypeDef nau7802_wait_powerup(uint32_t timeout_ms);
HAL_StatusTypeDef nau7802_wait_conversion_ready(uint32_t timeout_ms);

HAL_StatusTypeDef nau7802_read_raw(int32_t *raw_out);
HAL_StatusTypeDef nau7802_read_mv(int32_t *mv_out);

#ifdef __cplusplus
}
#endif

#endif /* NAU7802_H */
