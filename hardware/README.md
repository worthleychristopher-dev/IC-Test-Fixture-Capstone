# Reconfigurable Digital Integrated Circuit Test Fixture - Hardware

The hardware encompasses circuit simulations, schematics, chassis and any other physical component of the **Reconfigurable Digital Integerated Circuit Test Fixture**.

## Some altium/circuit stuff

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

## Documentation

This repository contains the hardware design documentation for a reconfigurable test fixture used to evaluate 7400-series digital integrated circuits (ICs). The documentation details the system architecture, circuit design, component selection, and PCB implementation used to support flexible, multi-voltage logic testing.

The design emphasizes reconfigurability, measurement accuracy, and system protection, enabling reliable testing of digital ICs across a range of operating conditions.

# The hardware documentation includes:
 - System Overview – High-level description of functionality and purpose
 - System Architecture – Block-level breakdown of subsystems
 - Design Decisions – Justification of key engineering choices
 - Signal Flow – End-to-end operation from input to measurement
 - Circuit Descriptions – Detailed explanation of each schematic block
 - PCB Layout – Board design, routing, and layer stack considerations
 - Electrical Specifications – Voltage ranges, thresholds, and performance
 - Interfaces – USB, UART, I²C, and ZIF socket definitions
 - Testing & Validation – Verification of system functionality
 - Safety & Protection – ESD, isolation, and overcurrent protection

# Key Hardware Features
 - USB-C interface for power and communication
 - Full USB isolation for noise reduction and safety
 - Multi-voltage support (1.8V – 5V logic levels)
 - Configurable analog switch matrix and multiplexers
 - High-resolution ADC measurement system
 - High-impedance (Hi-Z) detection capability
 - STM32-based control architecture

# Major Components
 - STM32 Microcontroller
 - CP2102 USB-to-UART Bridge
 - ADuM4160 USB Isolator
 - UCC33420 Isolated Power Module
 - ADG2128 Analog Switch Array
 - ADG708 Multiplexers
 - NAU7802 ADC
 - TLV431 Voltage References

Design Highlights
Modular and scalable architecture
Isolation between host and measurement domains
Flexible signal routing for multi-pin IC testing
Accurate voltage measurement using external ADC
Robust protection against ESD and overcurrent

# Validation Summary
The hardware was validated through:
- Power rail verification
- Signal routing tests
- ADC accuracy checks
- Logic-level testing across multiple voltages

All system components performed within expected specifications.

# Purpose
This documentation is intended to:
- Describe the complete hardware design
- Provide sufficient detail for system understanding or replication
- Support analysis, debugging, and further development

## License

The hardware portion of the **Reconfigurable Digital Integrated Circuit Test Fixture** is under a CERN-OHL-P-2.0 license.
