# Reconfigurable Integrated Circuit Test Fixture – Firmware

This firmware drives the **Reconfigurable Digital Integrated Circuit Test Fixture**, enabling configurable testing of common digital ICs through a command-based interface.

## Overview

The system is designed to operate in two primary modes:
- **GUI-controlled operation** (normal use case)
- **Standalone command-driven operation** (development, debugging, automation)

The firmware runs on an STM32 microcontroller and interfaces with:
- Analog switch matrices (2x ADG2128)
- Analog multiplexers (4x ADG708, 1x ADG709)
- Voltage rail selection circuitry
- GPIO-based digital I/O
- ADC (NAU7802) for measurement
- UART interface for command communication

## Firmware Architecture

### Core Responsibilities
- Parse and execute incoming commands (SCPI-style)
- Configure routing through analog switch arrays
- Apply voltage rails to DUT pins
- Drive digital inputs and read outputs
- Execute test sequences
- Return structured responses over UART

### Key Modules
- `main.c`  
  Handles system initialization (HAL, peripherals), UART communication, and command dispatch
  Parses incoming ASCII commands and routes them to execution handlers

- `test_utils.c`  
  Contains core test execution logic and validation
  Contains functions for switch array routing

- `nau7802.c`
  Handles ADC reads, calibration, and measurement routines

- `mux_utils.c`  
  Controls analog switch matrices (ADG2128) and pin routing

- `bist.c`   
  Code for executing a built-in self test for the fixture

- `fault_handling.c`
  Functions and subroutines for hardware fault handling

- `adg2128_router.c` *functions not used*
  Contains legacy functions for routing the switch arrays
  Functions improved upon and implemented in test_utils.c. 
  Header file includes variable definitions that ARE used

- `firmware_crc.c`
  Contains functions for running the firmware checksum

## Command Interface

The firmware uses a text-based command protocol.

### Format
```
CMD:arg1,arg2,arg3
```

### Example
```
PRM:20,7,5
VIN:0.33,3.84
INS:1,2,3
OUT:4,5
VIP:0b0101,0b1010
TEST
```

### Full Command Reference
See:
```
/docs/STM32 Command Programming Guide.txt
```

This file contains:
- All supported commands
- Argument formats
- Command use cases

## Development Setup

### Requirements
- STM32CubeIDE
- ST-Link debugger/programmer
- USB connection to STM32 board
- (Optional) Python (for executor script)

## Building the Firmware

1. Open STM32CubeIDE
2. Go to:
   ```
   File → Open Projects from File System
   ```
3. Import the firmware project folder
4. Build the project:
   ```
   Project → Build Project
   ```

## Flashing the Firmware (ST-Link)

1. Connect ST-Link to the board
2. Power the board via USB
3. In STM32CubeIDE:
   ```
   Run → Debug (or Run)
   ```
4. The firmware will compile (if needed) and flash automatically

## UART Communication

Typical UART settings:
- Baud Rate: 115200
- Data Bits: 8
- Stop Bits: 1
- Parity: None

## Using the System with the GUI

### Steps
1. Plug in the fixture via USB
2. Ensure firmware is running on the STM32
3. Open the GUI application
4. The GUI will automatically connect 
5. System now ready to run test scripts from the GUI application

### Notes
- No manual setup is required if firmware is running
- GUI handles all command formatting and communication

## Standalone Usage (Without GUI)

### Option 1: Serial Terminal

You can manually send commands using a serial terminal.

#### Recommended Tools
- STM32CubeIDE Serial Terminal
- Terminal or Windows Powershell

#### Steps
1. Open a serial terminal
2. Set directory to the one that includes stm32_terminal.py
   ex. 'cd C:\IC-Test-Fixture-Capstone\firmware\utils'
3. Run the python file, 'python stm32_terminal.py'
4. Send commands manually:
   ```
   PRM:20,7,5
   TEST
   ```

#### Example Output
```
OK PRM
OK TEST
RESULT: PASS
```

---

### Option 2: Script Execution (executor.py)

The `executor.py` script allows automated execution of command sequences.

#### Usage
```
python executor.py 
```

#### Example `script.txt`
```
PRM:20,7,5
VIN:0.33,3.84
INS:1,2,3
OUT:4
VIP:0b0101
TEST
```

#### Features
- Sequential command execution
- Response logging
- Useful for automated testing and debugging

## Typical Workflow

### Development Workflow
1. Modify firmware source code
2. Build in STM32CubeIDE
3. Flash using ST-Link
4. Test using terminal or executor.py

### Normal Operation
1. Power on fixture
2. Open GUI
3. Run test scripts

## Error Handling

Common responses:
- `OK <CMD>` → Command executed successfully
- `ERR <reason>` → Command failed

### Examples
```
ERR no_colon
ERR invalid_args
```

## Troubleshooting

### No UART Output
- Check COM port selection
- Verify baud rate
- Ensure firmware is running

### Flashing Issues
- Verify ST-Link connection
- Confirm correct target device in CubeIDE
- Power cycle the board

### Command Errors
- Ensure correct format (`CMD:args`)
- Refer to Command Programming Guide

## Future Improvements
- Expanded command set
- Improved error reporting
- Multi-fixture GUI support
- Enhanced logging and diagnostics

## Notes
- Designed for production-like testing environments
- Emphasizes modularity and scalability
- Command-based interface enables easy automation

## License

The firmware portion of the **Reconfigurable Digital Integrated Circuit Test Fixture** is under a MIT license. The firmware contains third-party software provided by STMicroelectronic and are subject to their own licenses and agreement policies. See firmware/LICENSE, and firmware/THIRD_PARTY_NOTICES for full details.
