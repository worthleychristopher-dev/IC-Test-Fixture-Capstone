################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Core/Src/adg2128_router.c \
../Core/Src/main.c \
../Core/Src/main2.c \
../Core/Src/main_backup.c \
../Core/Src/mux_utils.c \
../Core/Src/nau7802.c \
../Core/Src/stm32c0xx_hal_msp.c \
../Core/Src/stm32c0xx_it.c \
../Core/Src/syscalls.c \
../Core/Src/sysmem.c \
../Core/Src/system_stm32c0xx.c \
../Core/Src/test_utils.c \
../Core/Src/test_utils_backup.c 

OBJS += \
./Core/Src/adg2128_router.o \
./Core/Src/main.o \
./Core/Src/main2.o \
./Core/Src/main_backup.o \
./Core/Src/mux_utils.o \
./Core/Src/nau7802.o \
./Core/Src/stm32c0xx_hal_msp.o \
./Core/Src/stm32c0xx_it.o \
./Core/Src/syscalls.o \
./Core/Src/sysmem.o \
./Core/Src/system_stm32c0xx.o \
./Core/Src/test_utils.o \
./Core/Src/test_utils_backup.o 

C_DEPS += \
./Core/Src/adg2128_router.d \
./Core/Src/main.d \
./Core/Src/main2.d \
./Core/Src/main_backup.d \
./Core/Src/mux_utils.d \
./Core/Src/nau7802.d \
./Core/Src/stm32c0xx_hal_msp.d \
./Core/Src/stm32c0xx_it.d \
./Core/Src/syscalls.d \
./Core/Src/sysmem.d \
./Core/Src/system_stm32c0xx.d \
./Core/Src/test_utils.d \
./Core/Src/test_utils_backup.d 


# Each subdirectory must supply rules for building sources it contributes
Core/Src/%.o Core/Src/%.su Core/Src/%.cyclo: ../Core/Src/%.c Core/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m0plus -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32C071xx -c -I../Core/Inc -I../Drivers/STM32C0xx_HAL_Driver/Inc -I../Drivers/STM32C0xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32C0xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Core-2f-Src

clean-Core-2f-Src:
	-$(RM) ./Core/Src/adg2128_router.cyclo ./Core/Src/adg2128_router.d ./Core/Src/adg2128_router.o ./Core/Src/adg2128_router.su ./Core/Src/main.cyclo ./Core/Src/main.d ./Core/Src/main.o ./Core/Src/main.su ./Core/Src/main2.cyclo ./Core/Src/main2.d ./Core/Src/main2.o ./Core/Src/main2.su ./Core/Src/main_backup.cyclo ./Core/Src/main_backup.d ./Core/Src/main_backup.o ./Core/Src/main_backup.su ./Core/Src/mux_utils.cyclo ./Core/Src/mux_utils.d ./Core/Src/mux_utils.o ./Core/Src/mux_utils.su ./Core/Src/nau7802.cyclo ./Core/Src/nau7802.d ./Core/Src/nau7802.o ./Core/Src/nau7802.su ./Core/Src/stm32c0xx_hal_msp.cyclo ./Core/Src/stm32c0xx_hal_msp.d ./Core/Src/stm32c0xx_hal_msp.o ./Core/Src/stm32c0xx_hal_msp.su ./Core/Src/stm32c0xx_it.cyclo ./Core/Src/stm32c0xx_it.d ./Core/Src/stm32c0xx_it.o ./Core/Src/stm32c0xx_it.su ./Core/Src/syscalls.cyclo ./Core/Src/syscalls.d ./Core/Src/syscalls.o ./Core/Src/syscalls.su ./Core/Src/sysmem.cyclo ./Core/Src/sysmem.d ./Core/Src/sysmem.o ./Core/Src/sysmem.su ./Core/Src/system_stm32c0xx.cyclo ./Core/Src/system_stm32c0xx.d ./Core/Src/system_stm32c0xx.o ./Core/Src/system_stm32c0xx.su ./Core/Src/test_utils.cyclo ./Core/Src/test_utils.d ./Core/Src/test_utils.o ./Core/Src/test_utils.su ./Core/Src/test_utils_backup.cyclo ./Core/Src/test_utils_backup.d ./Core/Src/test_utils_backup.o ./Core/Src/test_utils_backup.su

.PHONY: clean-Core-2f-Src

