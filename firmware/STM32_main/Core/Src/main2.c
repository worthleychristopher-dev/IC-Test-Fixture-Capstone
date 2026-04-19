///* USER CODE BEGIN Header */
///**
//  ******************************************************************************
//  * @file           : main.c
//  * @brief          : Main program body
//  ******************************************************************************
//  * @attention
//  *
//  * Copyright (c) 2026 STMicroelectronics.
//  * All rights reserved.
//  *
//  * This software is licensed under terms that can be found in the LICENSE file
//  * in the root directory of this software component.
//  * If no LICENSE file comes with this software, it is provided AS-IS.
//  *
//  ******************************************************************************
//  */
///* USER CODE END Header */
///* Includes ------------------------------------------------------------------*/
//
///* Private includes ----------------------------------------------------------*/
///* USER CODE BEGIN Includes */
//#include "main.h"
//#include "test_utils.c"
//#include <string.h>
//#include <stdio.h>
//#include <stdlib.h>
//#include <ctype.h>
//#include <stdarg.h>
///* USER CODE END Includes */
//
///* Private typedef -----------------------------------------------------------*/
///* USER CODE BEGIN PTD */
//typedef enum {
//  VIP_KIND_NONE = 0,
//  VIP_KIND_VOLT,   // token is a voltage (e.g. 3.3) stored as millivolts
//  VIP_KIND_CLK,    // token is a clock (e.g. CLK50) stored as MHz
//  VIP_KIND_BIN     // token is a serial pattern (e.g. 0b0101) stored as string
//} VipKind;
//
////struct that holds all data required to run a test on an IC
//typedef struct {
//  uint8_t ins[MAX_PINS];
//  uint8_t n_ins;
//
//  uint8_t outs[MAX_PINS];
//  uint8_t n_outs;
//
//  int32_t vin_low_mv;
//  int32_t vin_high_mv;
//  uint8_t vin_set;
//
//  // ---------------- PRM ----------------
//  uint8_t vcc_pin;
//  uint8_t gnd_pin;
//  int32_t vcc_mv;   // VCC voltage in millivolts
//  uint8_t prm_set;
//
//  // ---------------- VIP ----------------
//  // One token per INS pin, mapped in INS order.
//  VipKind  vip_kind[MAX_PINS];
//  int32_t  vip_mv[MAX_PINS];             // valid if kind == VIP_KIND_VOLT
//  uint32_t vip_clk_mhz[MAX_PINS];        // valid if kind == VIP_KIND_CLK
//  char     vip_bin[MAX_PINS][VIP_BIN_MAX]; // valid if kind == VIP_KIND_BIN
//  uint8_t  n_vip;
//
//} ParsedState;
//
//
///* USER CODE END PTD */
//
///* Private define ------------------------------------------------------------*/
///* USER CODE BEGIN PD */
///* USER CODE END PD */
//
///* Private macro -------------------------------------------------------------*/
///* USER CODE BEGIN PM */
//#define MAX_PINS        20
//#define LINE_BUF_SIZE   128
//#define VIP_BIN_MAX     34   // supports up to 32 bits + "0b" + null
///* USER CODE END PM */
//
///* Private variables ---------------------------------------------------------*/
//
//UART_HandleTypeDef huart2;
//
///* USER CODE BEGIN PV */
//static uint8_t rx_ch;
//static char line_buf[LINE_BUF_SIZE];
//static uint32_t line_len = 0;
//
//
//
//static ParsedState g_state;
//
//
///* USER CODE END PV */
//
///* Private function prototypes -----------------------------------------------*/
//void SystemClock_Config(void);
//static void MX_GPIO_Init(void);
//static void MX_USART2_UART_Init(void);
///* USER CODE BEGIN PFP */
///* USER CODE END PFP */
//
///* Private user code ---------------------------------------------------------*/
///* USER CODE BEGIN 0 */
//static void uart_print(const char *s)
//{
//  HAL_UART_Transmit(&huart2, (uint8_t*)s, (uint16_t)strlen(s), HAL_MAX_DELAY);
//}
//
//static void uart_printf(const char *fmt, ...)
//{
//  char out[256];
//  va_list args;
//  va_start(args, fmt);
//  vsnprintf(out, sizeof(out), fmt, args);
//  va_end(args);
//  uart_print(out);
//}
//
//// Trim whitespace in-place (leading + trailing)
//static void trim(char *s)
//{
//  // leading
//  char *p = s;
//  while (*p && isspace((unsigned char)*p)) p++;
//  if (p != s) memmove(s, p, strlen(p) + 1);
//
//  // trailing
//  size_t n = strlen(s);
//  while (n > 0 && isspace((unsigned char)s[n-1])) {
//    s[n-1] = '\0';
//    n--;
//  }
//}
//
//static int parse_pin_list(const char *csv, uint8_t *arr, uint8_t *count_out)
//{
//  // csv like "1,2,3"
//  char tmp[LINE_BUF_SIZE];
//  strncpy(tmp, csv, sizeof(tmp)-1);
//  tmp[sizeof(tmp)-1] = '\0';
//
//  uint8_t count = 0;
//  char *save = NULL;
//  char *tok = strtok_r(tmp, ",", &save);
//
//  while (tok)
//  {
//    trim(tok);
//    if (*tok == '\0') return -2;
//
//    char *endp = NULL;
//    long v = strtol(tok, &endp, 10);
//    if (endp == tok) return -2;          // not a number
//    if (v < 1 || v > 20) return -3;      // out of allowed pin range
//    if (count >= MAX_PINS) return -4;    // too many pins
//
//    arr[count++] = (uint8_t)v;
//    tok = strtok_r(NULL, ",", &save);
//  }
//
//  *count_out = count;
//  return 0;
//}
//
//static int parse_vin_limits_mv(const char *csv, int32_t *low_mv, int32_t *high_mv)
//{
//  char tmp[LINE_BUF_SIZE];
//  strncpy(tmp, csv, sizeof(tmp)-1);
//  tmp[sizeof(tmp)-1] = '\0';
//
//  char *save = NULL;
//  char *a = strtok_r(tmp, ",", &save);
//  char *b = strtok_r(NULL, ",", &save);
//  if (!a || !b) return -2;
//
//  trim(a); trim(b);
//  if (*a == '\0' || *b == '\0') return -2;
//
//  double lo = strtod(a, NULL);
//  double hi = strtod(b, NULL);
//
//  *low_mv  = (int32_t)(lo * 1000.0 + (lo >= 0 ? 0.5 : -0.5));
//  *high_mv = (int32_t)(hi * 1000.0 + (hi >= 0 ? 0.5 : -0.5));
//  return 0;
//}
//
//static int parse_prm(const char *csv,
//                     uint8_t *vcc_pin_out,
//                     uint8_t *gnd_pin_out,
//                     int32_t *vcc_mv_out)
//{
//  // Expected format: "VCCpin,GNDpin,VCCvoltage"
//  // Example: "14,7,3.30"
//  char tmp[LINE_BUF_SIZE];
//  strncpy(tmp, csv, sizeof(tmp)-1);
//  tmp[sizeof(tmp)-1] = '\0';
//
//  char *save = NULL;
//  char *a = strtok_r(tmp, ",", &save);
//  char *b = strtok_r(NULL, ",", &save);
//  char *c = strtok_r(NULL, ",", &save);
//
//  if (!a || !b || !c) return -2;
//
//  trim(a); trim(b); trim(c);
//  if (*a == '\0' || *b == '\0' || *c == '\0') return -2;
//
//  char *endp1 = NULL;
//  char *endp2 = NULL;
//  long vcc = strtol(a, &endp1, 10);
//  long gnd = strtol(b, &endp2, 10);
//  if (endp1 == a || endp2 == b) return -2;
//
//  // If you want PRM limited to DUT pins: use 1..20
//  if (vcc < 1 || vcc > 20) return -3;
//  if (gnd < 1 || gnd > 20) return -3;
//
//  double v = strtod(c, NULL);
//  int32_t mv = (int32_t)(v * 1000.0 + (v >= 0 ? 0.5 : -0.5));
//
//  *vcc_pin_out = (uint8_t)vcc;
//  *gnd_pin_out = (uint8_t)gnd;
//  *vcc_mv_out  = mv;
//  return 0;
//}
//
//// Parse one VIP token into kind + value(s)
//static int parse_vip_token(const char *tok_in,
//                           VipKind *kind_out,
//                           int32_t *mv_out,
//                           uint32_t *clk_mhz_out,
//                           char bin_out[VIP_BIN_MAX])
//{
//  char tok[VIP_BIN_MAX];
//  strncpy(tok, tok_in, sizeof(tok)-1);
//  tok[sizeof(tok)-1] = '\0';
//  trim(tok);
//
//  if (*tok == '\0') return -2;
//
//  // CLKxx (MHz)
//  if (strncmp(tok, "CLK", 3) == 0)
//  {
//    const char *p = tok + 3;
//    if (*p == '\0') return -2;
//
//    // ensure digits
//    for (const char *q = p; *q; q++) {
//      if (!isdigit((unsigned char)*q)) return -2;
//    }
//
//    long mhz = strtol(p, NULL, 10);
//    if (mhz <= 0 || mhz > 1000) return -3; // arbitrary sanity cap
//    *kind_out = VIP_KIND_CLK;
//    *clk_mhz_out = (uint32_t)mhz;
//    return 0;
//  }
//
//  // 0bxxxx (binary string)
//  if (strncmp(tok, "0b", 2) == 0)
//  {
//    const char *p = tok + 2;
//    if (*p == '\0') return -2;
//
//    size_t n = strlen(p);
//    if (n > 32) return -4; // limit to 32 bits for now
//
//    for (const char *q = p; *q; q++) {
//      if (*q != '0' && *q != '1') return -2;
//    }
//
//    *kind_out = VIP_KIND_BIN;
//    strncpy(bin_out, tok, VIP_BIN_MAX-1);
//    bin_out[VIP_BIN_MAX-1] = '\0';
//    return 0;
//  }
//
//  // Otherwise treat as a voltage (volts -> mV)
//  double v = strtod(tok, NULL);
//  int32_t mv = (int32_t)(v * 1000.0 + (v >= 0 ? 0.5 : -0.5));
//
//  *kind_out = VIP_KIND_VOLT;
//  *mv_out = mv;
//  return 0;
//}
//
//// VIP list: token,token,token... (each token can be VOLT, CLKxx, or 0bxxxx)
//static int parse_vip_list(const char *csv,
//                          VipKind *kinds,
//                          int32_t *mv_arr,
//                          uint32_t *clk_arr,
//                          char bin_arr[MAX_PINS][VIP_BIN_MAX],
//                          uint8_t *count_out)
//{
//  char tmp[LINE_BUF_SIZE];
//  strncpy(tmp, csv, sizeof(tmp)-1);
//  tmp[sizeof(tmp)-1] = '\0';
//
//  uint8_t count = 0;
//  char *save = NULL;
//  char *tok = strtok_r(tmp, ",", &save);
//
//  while (tok)
//  {
//    if (count >= MAX_PINS) return -4;
//    trim(tok);
//    if (*tok == '\0') return -2;
//
//    kinds[count] = VIP_KIND_NONE;
//    mv_arr[count] = 0;
//    clk_arr[count] = 0;
//    bin_arr[count][0] = '\0';
//
//    int rc = parse_vip_token(tok,
//                             &kinds[count],
//                             &mv_arr[count],
//                             &clk_arr[count],
//                             bin_arr[count]);
//    if (rc != 0) return rc;
//
//    count++;
//    tok = strtok_r(NULL, ",", &save);
//  }
//
//  *count_out = count;
//  return 0;
//}
//
//static void send_u8_array(const char *name, const uint8_t *arr, uint8_t n)
//{
//  uart_printf("%s:", name);
//  for (uint8_t i = 0; i < n; i++) {
//    uart_printf("%u%s", arr[i], (i + 1 < n) ? "," : "");
//  }
//  uart_print("\r\n");
//}
//
//// Echo VIP back in a normalized format:
//// - voltages as millivolts integers
//// - clocks as CLK<MHz>
//// - binaries as 0b...
//static void send_vip_array(const ParsedState *st)
//{
//  uart_printf("VIP:");
//  for (uint8_t i = 0; i < st->n_vip; i++)
//  {
//    if (st->vip_kind[i] == VIP_KIND_VOLT) {
//      uart_printf("%ld", (long)st->vip_mv[i]);
//    } else if (st->vip_kind[i] == VIP_KIND_CLK) {
//      uart_printf("CLK%lu", (unsigned long)st->vip_clk_mhz[i]);
//    } else if (st->vip_kind[i] == VIP_KIND_BIN) {
//      uart_printf("%s", st->vip_bin[i]);
//    } else {
//      uart_printf("?");
//    }
//
//    if (i + 1 < st->n_vip) uart_print(",");
//  }
//  uart_print("\r\n");
//}
//
//static void handle_command_line(char *line)
//{
//  trim(line);
//  if (*line == '\0') return;
//
//  // TEST has no ":" parameters
//  if (strcmp(line, "TEST") == 0)
//  {
//    uart_print("OK TEST\r\n");
//    return;
//  }
//
//  // All other commands are CMD:params
//  char *colon = strchr(line, ':');
//  if (!colon) {
//    uart_print("ERR no_colon\r\n");
//    return;
//  }
//
//  *colon = '\0';
//  char *cmd = line;
//  char *params = colon + 1;
//  trim(cmd);
//  trim(params);
//
//  if (strcmp(cmd, "INS") == 0)
//  {
//    int rc = parse_pin_list(params, g_state.ins, &g_state.n_ins);
//    if (rc == 0) {
//      uart_printf("OK INS n=%u\r\n", g_state.n_ins);
//      send_u8_array("INS", g_state.ins, g_state.n_ins);
//    } else {
//      uart_printf("ERR INS rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//  if (strcmp(cmd, "OUT") == 0)
//  {
//    int rc = parse_pin_list(params, g_state.outs, &g_state.n_outs);
//    if (rc == 0) {
//      uart_printf("OK OUT n=%u\r\n", g_state.n_outs);
//      send_u8_array("OUT", g_state.outs, g_state.n_outs);
//    } else {
//      uart_printf("ERR OUT rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//  if (strcmp(cmd, "VIN") == 0)
//  {
//    int32_t lo_mv = 0, hi_mv = 0;
//    int rc = parse_vin_limits_mv(params, &lo_mv, &hi_mv);
//    if (rc == 0) {
//      g_state.vin_low_mv  = lo_mv;
//      g_state.vin_high_mv = hi_mv;
//      g_state.vin_set     = 1;
//
//      uart_print("OK VIN\r\n");
//      uart_printf("VIN:%ld,%ld\r\n", (long)g_state.vin_low_mv, (long)g_state.vin_high_mv);
//    } else {
//      uart_printf("ERR VIN rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//  if (strcmp(cmd, "PRM") == 0)
//  {
//    uint8_t vcc = 0, gnd = 0;
//    int32_t vcc_mv = 0;
//
//    int rc = parse_prm(params, &vcc, &gnd, &vcc_mv);
//    if (rc == 0) {
//      g_state.vcc_pin = vcc;
//      g_state.gnd_pin = gnd;
//      g_state.vcc_mv  = vcc_mv;
//      g_state.prm_set = 1;
//
//      uart_print("OK PRM\r\n");
//      uart_printf("PRM:%u,%u,%ld\r\n", g_state.vcc_pin, g_state.gnd_pin, (long)g_state.vcc_mv);
//    } else {
//      uart_printf("ERR PRM rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//  if (strcmp(cmd, "VIP") == 0)
//  {
//    int rc = parse_vip_list(params,
//                            g_state.vip_kind,
//                            g_state.vip_mv,
//                            g_state.vip_clk_mhz,
//                            g_state.vip_bin,
//                            &g_state.n_vip);
//    if (rc == 0) {
//      uart_printf("OK VIP n=%u\r\n", g_state.n_vip);
//      send_vip_array(&g_state);
//    } else {
//      uart_printf("ERR VIP rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//  uart_print("ERR unknown_cmd\r\n");
//}
///* USER CODE END 0 */
//
///**
//  * @brief  The application entry point.
//  * @retval int
//  */
//int main(void)
//{
//  HAL_Init();
//  SystemClock_Config();
//
//  MX_GPIO_Init();
//  MX_USART2_UART_Init();
//
//  /* USER CODE BEGIN 2 */
//  memset(&g_state, 0, sizeof(g_state));
//  uart_print("READY\r\n");
//
//  // Start 1-byte interrupt receive
//  HAL_UART_Receive_IT(&huart2, &rx_ch, 1);
//  /* USER CODE END 2 */
//
//  while (1)
//  {
//  }
//}
//
///**
//  * @brief System Clock Configuration
//  * @retval None
//  */
//void SystemClock_Config(void)
//{
//  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
//  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
//
//  __HAL_FLASH_SET_LATENCY(FLASH_LATENCY_0);
//
//  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
//  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
//  RCC_OscInitStruct.HSIDiv = RCC_HSI_DIV4;
//  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
//  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
//  {
//    Error_Handler();
//  }
//
//  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
//                              |RCC_CLOCKTYPE_PCLK1;
//  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
//  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
//  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV1;
//  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV1;
//
//  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
//  {
//    Error_Handler();
//  }
//}
//
///**
//  * @brief USART2 Initialization Function
//  * @param None
//  * @retval None
//  */
//static void MX_USART2_UART_Init(void)
//{
//  huart2.Instance = USART2;
//  huart2.Init.BaudRate = 115200;
//  huart2.Init.WordLength = UART_WORDLENGTH_8B;
//  huart2.Init.StopBits = UART_STOPBITS_1;
//  huart2.Init.Parity = UART_PARITY_NONE;
//  huart2.Init.Mode = UART_MODE_TX_RX;
//  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
//  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
//  huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
//  huart2.Init.ClockPrescaler = UART_PRESCALER_DIV1;
//  huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
//  if (HAL_UART_Init(&huart2) != HAL_OK)
//  {
//    Error_Handler();
//  }
//}
//
///**
//  * @brief GPIO Initialization Function
//  * @param None
//  * @retval None
//  */
//static void MX_GPIO_Init(void)
//{
//  __HAL_RCC_GPIOA_CLK_ENABLE();
//}
//
///* USER CODE BEGIN 4 */
//void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
//{
//  if (huart->Instance == USART2)
//  {
//    char c = (char)rx_ch;
//
//    if (c == '\r') {
//      // ignore CR
//    }
//    else if (c == '\n')
//    {
//      line_buf[line_len] = '\0';
//
//      // Work on a copy because handle_command_line modifies the string
//      char work[LINE_BUF_SIZE];
//      strncpy(work, line_buf, sizeof(work)-1);
//      work[sizeof(work)-1] = '\0';
//
//      handle_command_line(work);
//      line_len = 0;
//    }
//    else
//    {
//      if (line_len < (LINE_BUF_SIZE - 1)) {
//        line_buf[line_len++] = c;
//      } else {
//        line_len = 0;
//        uart_print("ERR line_overflow\r\n");
//      }
//    }
//
//    // Re-arm the interrupt for next byte
//    HAL_UART_Receive_IT(&huart2, &rx_ch, 1);
//  }
//}
///* USER CODE END 4 */
//
///**
//  * @brief  This function is executed in case of error occurrence.
//  * @retval None
//  */
//void Error_Handler(void)
//{
//  __disable_irq();
//  while (1)
//  {
//  }
//}
