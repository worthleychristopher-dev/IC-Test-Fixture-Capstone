/*
 * fault_handling.h
 *
 *  Created on: Apr 23, 2026
 *      Author: worthc2
 */

#ifndef FAULT_HANDLING_H
#define FAULT_HANDLING_H

#include "main.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum
{
    FAULT_RESULT_OK = 0,
    FAULT_RESULT_CONFIG_ERROR,
    FAULT_RESULT_HARDWARE_FAULT,
    FAULT_RESULT_NO_IC_DETECTED,
    FAULT_RESULT_BAD_INSERTION
} FaultResult;

/*
 * Runs a best-effort preflight before the actual DUT test.
 *
 * What it checks:
 * - fixture can route declared VCC/GND pins correctly
 * - powered DUT outputs are not all floating
 * - simple low/high stimulus produces at least some believable response
 *
 * Returns:
 * - FAULT_RESULT_OK if preflight looks good
 * - otherwise a specific fault classification
 */
FaultResult Fault_RunPreflight(const ParsedState *info, int32_t vcc_mv);

/* Returns a short printable string for the result */
const char *Fault_ResultString(FaultResult result);

#ifdef __cplusplus
}
#endif

#endif /* FAULT_HANDLING_H */
