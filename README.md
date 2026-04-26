# Reconfigurable Digital Integrated Circuit Test Fixture

A flexible test setup designed to quickly verify the functionality of various digital integrated circuits, ranging from simple logic gates to timing-dependent shift registers. It supplies standard logic-level voltages and measures output voltages to ensure they are within specification. A PC application enables users to control the system and execute test scripts. Test results are stored and exported as a PDF report describing the outcome of each test.

## Project Background

The core challenge lies in testing and servicing digital integrated circuit (IC) assemblies used in NUWC Division Newport’s ship test equipment. The large number of ICs in these systems makes troubleshooting and verification time-consuming, impacting operational efficiency, system reliability, and maintenance costs.

Since these assemblies are expected to remain functionally reliable for 25–30 years, diagnosing failures without efficient tools increases labor time, risks using faulty components, and threatens overall system readiness.

### Proposed Solution

To address this, our project proposes a **Reconfigurable Digital Integrated Circuit Test Fixture** that enables NUWC technicians to quickly verify IC functionality and assist in debugging failed circuit assemblies.

### System Components

- **Hardware Fixture**  
  Adapts to various IC packages and pinouts, applies logic-level signals, and measures outputs via analog-to-digital converters.

- **Software Interface**  
  Communicates with the hardware over USB, runs user-defined test scripts, and automatically generates detailed PDF reports.

### Key Benefits

- **Improved Maintenance Efficiency**  
  Reduces time spent on board-level diagnostics and repairs.

- **Inventory Verification**  
  Confirms IC functionality before installation.

- **Cost and Labor Savings**  
  Minimizes dependence on expensive test equipment and manual checks.

## Getting Started

### Prerequisites

#### Hardware

Altium Designer or KiCad (may need to manually fix PCB)

SolidWorks

CP2102 USB to UART Driver (https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers)

AN721: CP210x/CP211x Device Customization Guide (https://www.silabs.com/interface/usb-bridges/classic/device.cp2102?tab=softwareandtools)

USB-C 2.0 Cable

#### Software

Requires Python >= 3.10

Third Party Libraries used in this project are:

  - PySide6
  - PyYAML
  - ReportLab

See /software/pyproject.toml for compatible versions.

#### Firmware

STM32CubeIDE

ST-Link debugger/programmer

### Installation

TBA

### Usage

TBA

## Documentation

All documentation can be found in the directory docs. The directory includes PDF files of user manuals
and technical documentation. Additionally, /docs/editable/ includes a DOCX variant to allow
additions to the documentation as this project is expanded on. README markdown file are included with most parts
of the project to assist in navigation and summarize their purpose.

## License

The Reconfigurable Integrated Test Fixture project contains multiple components with different licenses:

- **Hardware (Altium, SolidWorks)**: CERN-OHL-P-2.0 (see /hardware/LICENSE)
- **Software (Python)**: MIT License (see /software/LICENSE)
- **Firmware (STM32)**: MIT License (see /firmware/LICENSE)

Refer to each subdirectory for full details regarding license of each component.

## Project Structure

```
IC-Test-Fixture-Capstone/
├── README.md               # project overview, and instructions
├── LICENSE                 # top-level license
├── docs/                   # images, user manuals, and technical documentation
├── hardware/               # altium source files and chassis files
├── software/               # Python application
├── firmware/               # firmware for STM32C071RB
├── test_scripts/           # HC/HCT test scripts for select 7400-series ICs
└── test_results/           # generated PDF reports from testing on 7400-series ICs
```

## UML Capstone Team 2025 - 2026

Qingping Diep (EE/CS) - [LinkedIn](https://www.linkedin.com/in/qdiep/)

Chris Worthley (CE) - [LinkedIn](https://www.linkedin.com/in/christopher-worthley-98b83a29a/)

Theodore Skafidas (EE) - [LinkedIn](https://www.linkedin.com/in/theodore-skafidas/)

Will Mensah (EE) - [LinkedIn](https://www.linkedin.com/in/will-s-mensah/)

Zacharie Fluet (EE) - [LinkedIn](https://www.linkedin.com/in/zacharie-fluet-6625728b/)

## Acknowledgements

### Advisors

Zachary Murtishi (NUWC)

Paul Robinette (Dept. of Electrical and Computer Engineering UML) - [LinkedIn](https://www.linkedin.com/in/paul-robinette-24857b/)

### UConn Capstone Team 2024 - 2025

Steven Chen (CSE) - [LinkedIn](https://www.linkedin.com/in/steven848/)

William Dunnett (CSE) - [LinkedIn](https://www.linkedin.com/in/william-dunnett-61431b260/)

Joshua Bardinelli (CSE) - [LinkedIn](https://www.linkedin.com/in/joshua-bardinelli/)

Sarah Millien (CSE) - [LinkedIn](https://www.linkedin.com/in/sarah-millien/)

Brennen Ravenberg (CSE)

Gabriel Zambrano (ECE) - [LinkedIn](https://www.linkedin.com/in/gabrielzambrano1111/)

Quincy Tejada (ECE)

Amir Herzberg (Dept. of Computer Science and Engineering UConn)

This project was sponsored by Naval Undersea Warfare Center Division Newport.
