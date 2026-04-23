#ifndef TEST_UTILS_H
#define TEST_UTILS_H

#include "main.h"

HAL_StatusTypeDef Test_Prepare(ParsedState *state);
void Test(ParsedState *state);
void Check_Connectivity(ParsedState *state);
void test_uart_printf(const char *fmt, ...);

#endif
