/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "test_utils.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <stdarg.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */



/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

I2C_HandleTypeDef hi2c1;
I2C_HandleTypeDef hi2c2;

UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
static uint8_t rx_ch;
static char line_buf[LINE_BUF_SIZE];
static uint32_t line_len = 0;



static ParsedState g_state;
static volatile uint8_t g_run_connectivity_test = 0;


/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_I2C1_Init(void);
static void MX_I2C2_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART2_UART_Init(void);
/* USER CODE BEGIN PFP */
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
static void uart_print(const char *s)
{
  HAL_UART_Transmit(&huart1, (uint8_t*)s, (uint16_t)strlen(s), HAL_MAX_DELAY);
}

static void uart_printf(const char *fmt, ...)
{
  char out[256];
  va_list args;
  va_start(args, fmt);
  vsnprintf(out, sizeof(out), fmt, args);
  va_end(args);
  uart_print(out);
}

// Trim whitespace in-place (leading + trailing)
static void trim(char *s)
{
  // leading
  char *p = s;
  while (*p && isspace((unsigned char)*p)) p++;
  if (p != s) memmove(s, p, strlen(p) + 1);

  // trailing
  size_t n = strlen(s);
  while (n > 0 && isspace((unsigned char)s[n-1])) {
    s[n-1] = '\0';
    n--;
  }
}

static int parse_pin_list(const char *csv, uint8_t *arr, uint8_t *count_out)
{
  // csv like "1,2,3"
  char tmp[LINE_BUF_SIZE];
  strncpy(tmp, csv, sizeof(tmp)-1);
  tmp[sizeof(tmp)-1] = '\0';

  uint8_t count = 0;
  char *save = NULL;
  char *tok = strtok_r(tmp, ",", &save);

  while (tok)
  {
    trim(tok);
    if (*tok == '\0') return -2;

    char *endp = NULL;
    long v = strtol(tok, &endp, 10);
    if (endp == tok) return -2;          // not a number
    if (v < 1 || v > 20) return -3;      // out of allowed pin range
    if (count >= MAX_PINS) return -4;    // too many pins

    arr[count++] = (uint8_t)v;
    tok = strtok_r(NULL, ",", &save);
  }

  *count_out = count;
  return 0;
}

static int parse_vin_limits_mv(const char *csv, int32_t *low_mv, int32_t *high_mv)
{
  char tmp[LINE_BUF_SIZE];
  strncpy(tmp, csv, sizeof(tmp)-1);
  tmp[sizeof(tmp)-1] = '\0';

  char *save = NULL;
  char *a = strtok_r(tmp, ",", &save);
  char *b = strtok_r(NULL, ",", &save);
  if (!a || !b) return -2;

  trim(a); trim(b);
  if (*a == '\0' || *b == '\0') return -2;

  double lo = strtod(a, NULL);
  double hi = strtod(b, NULL);

  *low_mv  = (int32_t)(lo * 1000.0 + (lo >= 0 ? 0.5 : -0.5));
  *high_mv = (int32_t)(hi * 1000.0 + (hi >= 0 ? 0.5 : -0.5));
  return 0;
}

static int parse_prm(const char *csv,
                     uint8_t *vcc_pin_out,
                     uint8_t *gnd_pin_out,
                     int32_t *vcc_mv_out)
{
  // Expected format: "VCCpin,GNDpin,VCCvoltage"
  // Example: "14,7,3.30"
  char tmp[LINE_BUF_SIZE];
  strncpy(tmp, csv, sizeof(tmp)-1);
  tmp[sizeof(tmp)-1] = '\0';

  char *save = NULL;
  char *a = strtok_r(tmp, ",", &save);
  char *b = strtok_r(NULL, ",", &save);
  char *c = strtok_r(NULL, ",", &save);

  if (!a || !b || !c) return -2;

  trim(a); trim(b); trim(c);
  if (*a == '\0' || *b == '\0' || *c == '\0') return -2;

  char *endp1 = NULL;
  char *endp2 = NULL;
  long vcc = strtol(a, &endp1, 10);
  long gnd = strtol(b, &endp2, 10);
  if (endp1 == a || endp2 == b) return -2;

  // If you want PRM limited to DUT pins: use 1..20
  if (vcc < 1 || vcc > 20) return -3;
  if (gnd < 1 || gnd > 20) return -3;

  double v = strtod(c, NULL);
  int32_t mv = (int32_t)(v * 1000.0 + (v >= 0 ? 0.5 : -0.5));

  *vcc_pin_out = (uint8_t)vcc;
  *gnd_pin_out = (uint8_t)gnd;
  *vcc_mv_out  = mv;
  return 0;
}

static void normalize_vip_bin_lengths(ParsedState *st)
{
  size_t max_len = 0;

  if (st == NULL) return;

  // Find longest binary payload length (excluding "0b")
  for (uint8_t i = 0; i < st->n_vip; i++)
  {
    if (st->vip_kind[i] == VIP_KIND_BIN)
    {
      size_t len = strlen(st->vip_bin[i]);
      if (len >= 2) {
        len -= 2; // exclude "0b"
        if (len > max_len) {
          max_len = len;
        }
      }
    }
  }

  if (max_len == 0) {
    return;
  }

  // Right-pad shorter binary strings with '0'
  for (uint8_t i = 0; i < st->n_vip; i++)
  {
    if (st->vip_kind[i] == VIP_KIND_BIN)
    {
      char padded[VIP_BIN_MAX];
      const char *src = st->vip_bin[i] + 2;  // skip "0b"
      size_t cur_len = strlen(src);

      if (cur_len >= max_len) {
        continue;
      }

      size_t out_idx = 0;
      padded[out_idx++] = '0';
      padded[out_idx++] = 'b';

      for (size_t j = 0; j < cur_len; j++) {
        padded[out_idx++] = src[j];
      }

      while ((out_idx - 2) < max_len) {
        padded[out_idx++] = '0';
      }

      padded[out_idx] = '\0';

      strncpy(st->vip_bin[i], padded, VIP_BIN_MAX - 1);
      st->vip_bin[i][VIP_BIN_MAX - 1] = '\0';
    }
  }
}

// Parse one VIP token into kind + value(s)
static int parse_vip_token(const char *tok_in,
                           VipKind *kind_out,
                           int32_t *mv_out,
                           uint32_t *clk_mhz_out,
                           char bin_out[VIP_BIN_MAX])
{
  char tok[VIP_BIN_MAX];
  strncpy(tok, tok_in, sizeof(tok) - 1);
  tok[sizeof(tok) - 1] = '\0';
  trim(tok);

  if (*tok == '\0') return -2;

  // CLKxx (MHz)
  if (strncmp(tok, "CLK", 3) == 0)
  {
    const char *p = tok + 3;
    if (*p == '\0') return -2;

    for (const char *q = p; *q; q++) {
      if (!isdigit((unsigned char)*q)) return -2;
    }

    long mhz = strtol(p, NULL, 10);
    if (mhz <= 0 || mhz > 1000) return -3;

    *kind_out = VIP_KIND_CLK;
    *clk_mhz_out = (uint32_t)mhz;
    return 0;
  }

  // 0bxxxx (serial/binary string, now allowing 0,1,R,F)
  if (strncmp(tok, "0b", 2) == 0)
  {
    const char *p = tok + 2;
    if (*p == '\0') return -2;

    size_t n = strlen(p);
    if (n > 32) return -4;

    for (const char *q = p; *q; q++) {
      if (*q != '0' && *q != '1' && *q != 'R' && *q != 'F') {
        return -2;
      }
    }

    *kind_out = VIP_KIND_BIN;
    strncpy(bin_out, tok, VIP_BIN_MAX - 1);
    bin_out[VIP_BIN_MAX - 1] = '\0';
    return 0;
  }

  // Otherwise treat as a voltage (volts -> mV)
  double v = strtod(tok, NULL);
  int32_t mv = (int32_t)(v * 1000.0 + (v >= 0 ? 0.5 : -0.5));

  *kind_out = VIP_KIND_VOLT;
  *mv_out = mv;
  return 0;
}

// VIP list: token,token,token... (each token can be VOLT, CLKxx, or 0bxxxx)
static int parse_vip_list(const char *csv,
                          VipKind *kinds,
                          int32_t *mv_arr,
                          uint32_t *clk_arr,
                          char bin_arr[MAX_PINS][VIP_BIN_MAX],
                          uint8_t *count_out)
{
  char tmp[LINE_BUF_SIZE];
  strncpy(tmp, csv, sizeof(tmp)-1);
  tmp[sizeof(tmp)-1] = '\0';

  uint8_t count = 0;
  char *save = NULL;
  char *tok = strtok_r(tmp, ",", &save);

  while (tok)
  {
    if (count >= MAX_PINS) return -4;
    trim(tok);
    if (*tok == '\0') return -2;

    kinds[count] = VIP_KIND_NONE;
    mv_arr[count] = 0;
    clk_arr[count] = 0;
    bin_arr[count][0] = '\0';

    int rc = parse_vip_token(tok,
                             &kinds[count],
                             &mv_arr[count],
                             &clk_arr[count],
                             bin_arr[count]);
    if (rc != 0) return rc;

    count++;
    tok = strtok_r(NULL, ",", &save);
  }

  *count_out = count;
  return 0;
}

static void send_u8_array(const char *name, const uint8_t *arr, uint8_t n)
{
  uart_printf("%s:", name);
  for (uint8_t i = 0; i < n; i++) {
    uart_printf("%u%s", arr[i], (i + 1 < n) ? "," : "");
  }
  uart_print("\r\n");
}

// Echo VIP back in a normalized format:
// - voltages as millivolts integers
// - clocks as CLK<MHz>
// - binaries as 0b...
static void send_vip_array(const ParsedState *st)
{
  uart_printf("VIP:");
  for (uint8_t i = 0; i < st->n_vip; i++)
  {
    if (st->vip_kind[i] == VIP_KIND_VOLT) {
      uart_printf("%ld", (long)st->vip_mv[i]);
    } else if (st->vip_kind[i] == VIP_KIND_CLK) {
      uart_printf("CLK%lu", (unsigned long)st->vip_clk_mhz[i]);
    } else if (st->vip_kind[i] == VIP_KIND_BIN) {
      uart_printf("%s", st->vip_bin[i]);
    } else {
      uart_printf("?");
    }

    if (i + 1 < st->n_vip) uart_print(",");
  }
  uart_print("\r\n");
}

static void handle_command_line(char *line)
{
  trim(line);
  if (*line == '\0') return;

  // TEST has no ":" parameters
  if (strcmp(line, "TEST") == 0)
  {
    uart_print("OK TEST\r\n");
    g_run_connectivity_test = 1;
    return;
  }

  // All other commands are CMD:params
  char *colon = strchr(line, ':');
  if (!colon) {
    uart_print("ERR no_colon\r\n");
    return;
  }

  *colon = '\0';
  char *cmd = line;
  char *params = colon + 1;
  trim(cmd);
  trim(params);

  if (strcmp(cmd, "INS") == 0)
  {
    int rc = parse_pin_list(params, g_state.ins, &g_state.n_ins);
    if (rc == 0) {
      uart_printf("OK INS n=%u\r\n", g_state.n_ins);
     // send_u8_array("INS", g_state.ins, g_state.n_ins);
    } else {
      uart_printf("ERR INS rc=%d\r\n", rc);
    }
    return;
  }

  if (strcmp(cmd, "OUT") == 0)
  {
    int rc = parse_pin_list(params, g_state.outs, &g_state.n_outs);
    if (rc == 0) {
      uart_printf("OK OUT n=%u\r\n", g_state.n_outs);
      //send_u8_array("OUT", g_state.outs, g_state.n_outs);
    } else {
      uart_printf("ERR OUT rc=%d\r\n", rc);
    }
    return;
  }

  if (strcmp(cmd, "VIN") == 0)
  {
    int32_t lo_mv = 0, hi_mv = 0;
    int rc = parse_vin_limits_mv(params, &lo_mv, &hi_mv);
    if (rc == 0) {
      g_state.vin_low_mv  = lo_mv;
      g_state.vin_high_mv = hi_mv;
      g_state.vin_set     = 1;

      uart_print("OK VIN\r\n");
      //uart_printf("VIN:%ld,%ld\r\n", (long)g_state.vin_low_mv, (long)g_state.vin_high_mv);
    } else {
      uart_printf("ERR VIN rc=%d\r\n", rc);
    }
    return;
  }

  if (strcmp(cmd, "PRM") == 0)
  {
    uint8_t vcc = 0, gnd = 0;
    int32_t vcc_mv = 0;

    int rc = parse_prm(params, &vcc, &gnd, &vcc_mv);
    if (rc == 0) {
      g_state.vcc_pin = vcc;
      g_state.gnd_pin = gnd;
      g_state.vcc_mv  = vcc_mv;
      g_state.prm_set = 1;

      uart_print("OK PRM\r\n");
      //uart_printf("PRM:%u,%u,%ld\r\n", g_state.vcc_pin, g_state.gnd_pin, (long)g_state.vcc_mv);
    } else {
      uart_printf("ERR PRM rc=%d\r\n", rc);
    }
    return;
  }

  if (strcmp(cmd, "VIP") == 0)
  {
    int rc = parse_vip_list(params,
                            g_state.vip_kind,
                            g_state.vip_mv,
                            g_state.vip_clk_mhz,
                            g_state.vip_bin,
                            &g_state.n_vip);
    if (rc == 0) {
      uart_printf("OK VIP n=%u\r\n", g_state.n_vip);
      normalize_vip_bin_lengths(&g_state);
      //send_vip_array(&g_state);
    } else {
      uart_printf("ERR VIP rc=%d\r\n", rc);
    }
    return;
  }

  uart_print("ERR unknown_cmd\r\n");
}
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_I2C1_Init();
  MX_I2C2_Init();
  MX_USART1_UART_Init();
  MX_USART2_UART_Init();
  /* USER CODE BEGIN 2 */
  memset(&g_state, 0, sizeof(g_state));
  uart_print("READY\r\n");

  // Start 1-byte interrupt receive
  HAL_UART_Receive_IT(&huart1, &rx_ch, 1);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
	  if (g_run_connectivity_test)
	      {
	          g_run_connectivity_test = 0;
	          Test(&g_state);
	      }


    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  __HAL_FLASH_SET_LATENCY(FLASH_LATENCY_0);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSIDiv = RCC_HSI_DIV4;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.Timing = 0x00402D41;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Analogue filter
  */
  if (HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Digital filter
  */
  if (HAL_I2CEx_ConfigDigitalFilter(&hi2c1, 0) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief I2C2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C2_Init(void)
{

  /* USER CODE BEGIN I2C2_Init 0 */

  /* USER CODE END I2C2_Init 0 */

  /* USER CODE BEGIN I2C2_Init 1 */

  /* USER CODE END I2C2_Init 1 */
  hi2c2.Instance = I2C2;
  hi2c2.Init.Timing = 0x00402D41;
  hi2c2.Init.OwnAddress1 = 0;
  hi2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c2.Init.OwnAddress2 = 0;
  hi2c2.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c2) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Analogue filter
  */
  if (HAL_I2CEx_ConfigAnalogFilter(&hi2c2, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Digital filter
  */
  if (HAL_I2CEx_ConfigDigitalFilter(&hi2c2, 0) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C2_Init 2 */

  /* USER CODE END I2C2_Init 2 */

}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart1.Init.ClockPrescaler = UART_PRESCALER_DIV1;
  huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_SetTxFifoThreshold(&huart1, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_SetRxFifoThreshold(&huart1, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_DisableFifoMode(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart2.Init.ClockPrescaler = UART_PRESCALER_DIV1;
  huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1|GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6
                          |GPIO_PIN_7|GPIO_PIN_8, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_10, GPIO_PIN_SET);

  /*Configure GPIO pins : PF0 PF1 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_1;
  GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);

  /*Configure GPIO pins : PA1 PA4 PA5 PA6
                           PA7 PA8 */
  GPIO_InitStruct.Pin = GPIO_PIN_1|GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6
                          |GPIO_PIN_7|GPIO_PIN_8;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pin : PC10 */
  GPIO_InitStruct.Pin = GPIO_PIN_10;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART1)
  {
    char c = (char)rx_ch;

    if (c == '\r') {
      // ignore CR
    }
    else if (c == '\n')
    {
      line_buf[line_len] = '\0';

      // Work on a copy because handle_command_line modifies the string
      char work[LINE_BUF_SIZE];
      strncpy(work, line_buf, sizeof(work)-1);
      work[sizeof(work)-1] = '\0';

      handle_command_line(work);
      line_len = 0;
    }
    else
    {
      if (line_len < (LINE_BUF_SIZE - 1)) {
        line_buf[line_len++] = c;
      } else {
        line_len = 0;
        uart_print("ERR line_overflow\r\n");
      }
    }

    // Re-arm the interrupt for next byte
    HAL_UART_Receive_IT(&huart1, &rx_ch, 1);
  }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
