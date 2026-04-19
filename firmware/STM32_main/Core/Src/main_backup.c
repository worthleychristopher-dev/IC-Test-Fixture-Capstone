///*/* USER CODE BEGIN Header */
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
//
//
//#include <string.h>
//#include <stdio.h>
//#include <stdlib.h>
//#include <ctype.h>
//#include <stdarg.h>
///* USER CODE END Includes */
//
///* Private typedef -----------------------------------------------------------*/
///* USER CODE BEGIN PTD */
//
///* USER CODE END PTD */
//
///* Private define ------------------------------------------------------------*/
///* USER CODE BEGIN PD */
//
///* USER CODE END PD */
//
///* Private macro -------------------------------------------------------------*/
///* USER CODE BEGIN PM */
//#define MAX_PINS        12
//#define LINE_BUF_SIZE   128
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
//  // Voltage “type” tokens (store raw tokens, e.g. "TTL", "CMOS", "L", "H")
//  char vti[MAX_PINS][8];
//  uint8_t n_vti;
//
//  char vto[MAX_PINS][8];
//  uint8_t n_vto;
//} ParsedState;
//
//static ParsedState g_state;
///* USER CODE END PV */
//
///* Private function prototypes -----------------------------------------------*/
//void SystemClock_Config(void);
//static void MX_GPIO_Init(void);
//static void MX_USART2_UART_Init(void);
///* USER CODE BEGIN PFP */
//
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
//    if (v < 1 || v > 12) return -3;      // out of allowed pin range
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
//static int parse_token_list(const char *csv, char tokens[MAX_PINS][8], uint8_t *count_out)
//{
//  // csv like "TTL,TTL,CMOS" or "L,H,L"
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
//    if (count >= MAX_PINS) return -4;
//
//    strncpy(tokens[count], tok, 7);
//    tokens[count][7] = '\0';
//    count++;
//
//    tok = strtok_r(NULL, ",", &save);
//  }
//
//  *count_out = count;
//  return 0;
//}
//
//static int parse_vin_limits_mv(const char *csv, int32_t *low_mv, int32_t *high_mv)
//{
//  // Accepts formats like "0.80,2.00" or "1,3.3" or "5.0,5.5"
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
//  // Use strtod (double) for parsing, then convert to mV. No printf-float needed.
//  double lo = strtod(a, NULL);
//  double hi = strtod(b, NULL);
//
//  *low_mv  = (int32_t)(lo * 1000.0 + (lo >= 0 ? 0.5 : -0.5));  // rounded
//  *high_mv = (int32_t)(hi * 1000.0 + (hi >= 0 ? 0.5 : -0.5));
//
//  return 0;
//}
//
//
//static void send_u8_array(const char *name, const uint8_t *arr, uint8_t n) //Eventually this function will get removed and replaced with setting stuff to the right pins
//{
//  uart_printf("%s:", name);
//  for (uint8_t i = 0; i < n; i++) {
//    uart_printf("%u%s", arr[i], (i + 1 < n) ? "," : "");
//  }
//  uart_print("\r\n");
//}
//
//static void send_str_array(const char *name, char arr[MAX_PINS][8], uint8_t n)
//{
//  uart_printf("%s:", name);
//  for (uint8_t i = 0; i < n; i++) {
//    uart_printf("%s%s", arr[i], (i + 1 < n) ? "," : "");
//  }
//  uart_print("\r\n");
//}
//
//static void handle_command_line(char *line)
//{
//  // Expected: CMD:params
//  // Examples:
//  //   INS:1,3,5,7
//  //   OUT:2,4,6
//  //   VIN:0.80,2.00
//  //   VTI:TTL,TTL,TTL,CMOS
//  //   VTO:CMOS,CMOS,CMOS
//  trim(line);
//  if (*line == '\0') return;
//
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
//      // Example output: VIN:800,2000   (meaning mV)
//    } else {
//      uart_printf("ERR VIN rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//
//  if (strcmp(cmd, "VTI") == 0)
//  {
//    int rc = parse_token_list(params, g_state.vti, &g_state.n_vti);
//    if (rc == 0) {
//      uart_printf("OK VTI n=%u\r\n", g_state.n_vti);
//      send_str_array("VTI", g_state.vti, g_state.n_vti);
//    } else {
//      uart_printf("ERR VTI rc=%d\r\n", rc);
//    }
//    return;
//  }
//
//  if (strcmp(cmd, "VTO") == 0)
//  {
//    int rc = parse_token_list(params, g_state.vto, &g_state.n_vto);
//    if (rc == 0) {
//      uart_printf("OK VTO n=%u\r\n", g_state.n_vto);
//      send_str_array("VTO", g_state.vto, g_state.n_vto);
//    } else {
//      uart_printf("ERR VTO rc=%d\r\n", rc);
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
//
//  /* USER CODE BEGIN 1 */
//
//  /* USER CODE END 1 */
//
//  /* MCU Configuration--------------------------------------------------------*/
//
//  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
//  HAL_Init();
//
//  /* USER CODE BEGIN Init */
//
//  /* USER CODE END Init */
//
//  /* Configure the system clock */
//  SystemClock_Config();
//
//  /* USER CODE BEGIN SysInit */
//
//  /* USER CODE END SysInit */
//
//  /* Initialize all configured peripherals */
//  MX_GPIO_Init();
//  MX_USART2_UART_Init();
//  /* USER CODE BEGIN 2 */
//  memset(&g_state, 0, sizeof(g_state));
//  uart_print("READY\r\n");
//
//  // Start 1-byte interrupt receive
//  HAL_UART_Receive_IT(&huart2, &rx_ch, 1);
//  /* USER CODE END 2 */
//
//  /* Infinite loop */
//  /* USER CODE BEGIN WHILE */
//  while (1)
//  {
//    /* USER CODE END WHILE */
//
//    /* USER CODE BEGIN 3 */
//  }
//  /* USER CODE END 3 */
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
//  /** Initializes the RCC Oscillators according to the specified parameters
//  * in the RCC_OscInitTypeDef structure.
//  */
//  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
//  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
//  RCC_OscInitStruct.HSIDiv = RCC_HSI_DIV4;
//  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
//  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
//  {
//    Error_Handler();
//  }
//
//  /** Initializes the CPU, AHB and APB buses clocks
//  */
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
//
//  /* USER CODE BEGIN USART2_Init 0 */
//
//  /* USER CODE END USART2_Init 0 */
//
//  /* USER CODE BEGIN USART2_Init 1 */
//
//  /* USER CODE END USART2_Init 1 */
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
//  /* USER CODE BEGIN USART2_Init 2 */
//
//  /* USER CODE END USART2_Init 2 */
//
//}
//
///**
//  * @brief GPIO Initialization Function
//  * @param None
//  * @retval None
//  */
//static void MX_GPIO_Init(void)
//{
//  /* USER CODE BEGIN MX_GPIO_Init_1 */
//
//  /* USER CODE END MX_GPIO_Init_1 */
//
//  /* GPIO Ports Clock Enable */
//  __HAL_RCC_GPIOA_CLK_ENABLE();
//
//  /* USER CODE BEGIN MX_GPIO_Init_2 */
//
//  /* USER CODE END MX_GPIO_Init_2 */
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
//  /* USER CODE BEGIN Error_Handler_Debug */
//  /* User can add his own implementation to report the HAL error return state */
//  __disable_irq();
//  while (1)
//  {
//  }
//  /* USER CODE END Error_Handler_Debug */
//}
//#ifdef USE_FULL_ASSERT
///**
//  * @brief  Reports the name of the source file and the source line number
//  *         where the assert_param error has occurred.
//  * @param  file: pointer to the source file name
//  * @param  line: assert_param error line source number
//  * @retval None
//  */
//void assert_failed(uint8_t *file, uint32_t line)
//{
//  /* USER CODE BEGIN 6 */
//  /* User can add his own implementation to report the file name and line number,
//     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
//  /* USER CODE END 6 */
//}
//#endif /* USE_FULL_ASSERT */
///*
// *
// *
// *
// *
// * */
