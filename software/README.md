# Reconfigurable Digital Integrated Circuit Test Fixture - Software

A standalone GUI application for controlling the **Reconfigurable Digital Integrated Circuit Test Fixture**. 
Users can write or upload YAML-based test scripts to execute tests, with results exported as PDF files.

Requires Python >= 3.10

Recommended Python >= 3.14.3 (latest as of April 2026)

## Installation

Create virtual Python environment
```sh
cd software/

python -m venv .venv

# linux/mac
source .venv/bin/activate

# windows
.venv\scripts\Activate.ps1
```

Install with only required dependencies
```sh
# run in same directory as pyproject.toml
pip install -e .
```

Install with additional optional dependencies
```sh
pip install -e .[dev]
```

## Usage

```sh
# run directly from src
python src/ic_test_fixture/main.py

# or if installed in editable mode
python -m ic_test_fixture.main
```

To compile an executable
```sh
pyinstaller --onefile --noconsole --name ICTestFixture src/ic_test_fixture/main.py
```

## GUI Usage

### **Warning**

If there is an issue regarding the checksum

### From Existing Test Script
    1. Go to **File -> Open File** (Ctrl+O)
    2. Verify test script is correct
    3. Press **Run -> Run** (F5)
    4. Save results to desired location as PDF file
    
### Create a New Test Script

1. Go to **File → New File** (Ctrl+N)
2. Choose one of the following:
   - **Text Editor** (manual script creation)
   - **Test Script Wizard** (guided setup)

---

Refer to User Guide in docs/ for full usage

#### Option A: Text Editor
3. Write your test script manually  
4. Save the test script as a YAML file  

---

#### Option B: Test Script Wizard
3. Select the desired optional sections  
4. Use the dropdown menus to configure parameters  
5. Save the test script as a YAML file  

## Running Tests

```sh
# to run all unit tests
pytest tests/

# :: operator can be used to run specific tests
pytest tests/test_parser.py::TestParserHelpers
```

## Troubleshooting

### Checksum failed

Verify CP2102 driver has been installed and serial number has been reprogrammed. See the repository's main README.md for the associated download links.

Verify the test fixture is connected via USB-C 2.0.

Ensure firmware has not been tampered with. If developing, change EXPECTED_CHECKSUM in device/serial_manager.py::CheckSum to the the new expected checksum. 

## Documentation

See docs/ for all documentation

Python Technical Documentation - explaination of source code, architecture, and data structures

YAML Test Script Documentation - expected syntax of test scripts

User Manual - system and application usage

## License

The software portion of the **Reconfigurable Digital Integrated Circuit Test Fixture** is under a MIT license. The software contains third-party packages that are subject to their own licenses provided by their authors. See software/LICENSE, and software/THIRD_PARTY_NOTICES for full details.

## Package Structure

```
software/
├── README.md               # project overview, and instructions
├── LICENSE                 # license for Python source code
├── THIRD PARTY NOTICES     # licenses for Python packages used
├── pyproject.toml          # package metadata and dependencies
├── src/
│   └── ic_test_fixture/
│       ├── device/         # device-related modules
│       ├── file_io/        # file parsing, and exporting data
│       ├── gui/            # graphical user interface code
│       ├── utils/          # misc. code / helper tools
│       ├── __init__.py
│       └── main.py         # application entry point
└── tests/
    ├── unittest_yaml/      # YAML-based test scripts for unit tests
    ├── test_parser.py      # tests for parser module
    └── test_test_vector.py # tests for test_vector module
```
