/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
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

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32c0xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */
typedef enum {
  VIP_KIND_NONE = 0,
  VIP_KIND_VOLT,   // token is a voltage (e.g. 3.3) stored as millivolts
  VIP_KIND_CLK,    // token is a clock (e.g. CLK50) stored as MHz
  VIP_KIND_BIN     // token is a serial pattern (e.g. 0b0101) stored as string
} VipKind;

#define MAX_PINS        20
#define LINE_BUF_SIZE   512
#define VIP_BIN_MAX     64   // supports up to 32 bits + "0b" + null

//struct that holds all data required to run a test on an IC
typedef struct {
  uint8_t ins[MAX_PINS];
  uint8_t n_ins;

  uint8_t outs[MAX_PINS];
  uint8_t n_outs;

  int32_t vin_low_mv;
  int32_t vin_high_mv;
  uint8_t vin_set;

  // ---------------- PRM ----------------
  uint8_t vcc_pin;
  uint8_t gnd_pin;
  int32_t vcc_mv;   // VCC voltage in millivolts
  uint8_t prm_set;

  // ---------------- VIP ----------------
  // One token per INS pin, mapped in INS order.
  VipKind  vip_kind[MAX_PINS];
  int32_t  vip_mv[MAX_PINS];             // valid if kind == VIP_KIND_VOLT
  uint32_t vip_clk_mhz[MAX_PINS];        // valid if kind == VIP_KIND_CLK
  char     vip_bin[MAX_PINS][VIP_BIN_MAX]; // valid if kind == VIP_KIND_BIN
  uint8_t  n_vip;




} ParsedState;
/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
