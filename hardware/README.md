# Reconfigurable Digital Integrated Circuit Test Fixture - Hardware

The hardware encompasses circuit simulations, schematics, chassis and any other physical component of the **Reconfigurable Digital Integerated Circuit Test Fixture**. The design emphasizes reconfigurability, measurement accuracy, and system protection, enabling reliable testing of digital ICs across a range of operating conditions.

## Overview

The hardware utilizes a USB-C interface for power and communication. The power and data lines are isolated, reducing the noise of the system and protecting the host PC from potential electrical faults. The test fixture accomodates common logic voltage levels from 1.8V to 5V.

Input signal routing is handled using a pair of analog switch arrays, allowing flexible operation of input voltages to pins of the device under test. For measuring output pins, the output signal path is multiplexed and fed first into a high-impedance (Hi-Z) detection circuit, and then into a high-resolution ADC system.

## Core Components

Control of the circuit is handled by the STM32C071RB microcontroller from STMicroelectronics. Communication with the host PC is achieved through a CP2102 USB-to-UART bridge. To ensure signal integrity and safety, USB data lines are isolated using the ADuM4160, while power isolation is provided by the UCC33420 module.

Logic-level voltage references are generated using TLV431 shunt regulators in combination with high-precision resistors, ensuring stable and accurate voltage levels.

Dynamic analog signal routing is implemented using the ADG2128 switch array and ADG708 multiplexers. Output voltages are measured by the NAU7802 ADC, providing high-resolution data.

## Validation

The hardware was validated through a series of test, ensuring analog components performed with high-precison and stability. The power rails and TLV431 circuits were verified for correctness. Signal routing was tested for all ppossible combinations. The ADC performance was evaluated to confirm accuracy of responses and compatability with 1.8 to 5V signals.

All system components performed within expected specifications.

## Chassis

All files included are of the SolidWorks CAD of the IC test fixture chassis design.

This includes raw pre-fab chassis consisting of a top, front, rear, and bottom chassis, modified chassis with cutouts for the PCB on the top, front, and bottom chassis, and the CAD files for hardware used to fully assemble the IC test fixture, including screws, standoffs, and rubber feet.

Drawings are present showing each chassis parts individually, along with their measurements and cutouts. The Chassis is made of ABS plastic.

The pre-fabricated chassis is a JB-65 Desktop Electronics Enclosure, by Polycase and can be orderd from https://www.polycase.com/jb-65

Physical assembly of the chassis can be done with the chassis screws provided with the chassis by Polycase, 8x #4-40 Pan screws, 4x #4-40 1" hex standoffs, and 4x 0.5" cylindrical bumper rubber feet along with the IC test fixture PCB.

## Spice Simulations

Voltage reference (VREF) circuits consist of a TLV431 shunt regulator component with a $1.24\ V$ reference voltage, a voltage divider resistor circuit to set the VREF voltage, and a current limiting resistor to restrict the amount of current that can flow through the circuit.

For all VREF circuits within the IC test fixture, $V_{in} = 5\ V$, $V_{ref} = 1.24\ V$.

The formula for all the VREF circuits is:

$$V_{out} = V_{ref} \left(1 + \frac{R_1}{R_2}\right)$$

where $R_2 = 2490\ \Omega$ for consistency.

$V_{out}$ is set to $1.8\ V$, $2.5\ V$, $3.3\ V$, $4.0\ V$, or $4.5\ V$ for the VREF circuit, which is used to find each circuit's $R_1$ value, which is then chosen from the closest available 0.1% tolerance value.

The current limiting resistor ($R_3$) is equal to: 
$$R_3 = \frac{\left(V_{in} - V_{out}\right)}{\left(I_{out} + I_{cathode}\right)}$$

### TLV431 Simulation Results

| Target Voltage | Simulated Voltage |
| -------------- | ----------------- |
| 1.8 V | 1.803 V |
| 2.5 V | 2.509 V |
| 3.3 V | 3.314 V |
| 4.0 V | 4.001 V |
| 4.5 V | 4.506 V |

5V is not present as the USB interface outputs at max 5V. Instead, the 5V is provided by the isolated 5V rail from UCC33420.

## Documentation

Refer to Hardware Documentation in docs/. The documentation details the system architecture, circuit design, component selection, and PCB implementation used to support flexible, multi-voltage logic testing.

The hardware documentation includes:

| Section | Description |
| ------- | ----------- |
| System Overview | High-level description of functionality and purpose |
| System Architecture | Block-level breakdown of subsystems |
| Design Decisions | Justification of key engineering choices |
| Signal Flow | End-to-end operation from input to measurement |
| Circuit Descriptions | Detailed explanation of each schematic block |
| PCB Layout | Board design, routing, and layer stack considerations |
| Electrical Specifications | Voltage ranges, thresholds, and performance |
| Interfaces | USB, UART, I²C, and ZIF socket definitions |
| Testing & Validation | Verification of system functionality |
| Safety & Protection | ESD, isolation, and overcurrent protection |

Refer to Reconfigurable Test Fixture BOM in docs/. The file includes the name of the part, part number, manufacturer number, designator, and quantity.

## License

The hardware portion of the **Reconfigurable Digital Integrated Circuit Test Fixture** is under a CERN-OHL-P-2.0 license.
