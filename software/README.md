# IC Test Fixture Python Application

A standalone GUI application for controlling the reconfigurable IC test fixture. 
Users can write or upload YAML-based test scripts to execute tests, 
with results exported as PDF files.

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

## Running Tests

```sh
# to run all unit tests
pytest tests/

# :: operator can be used to run specific tests
pytest tests/test_parser.py::TestParserHelpers
```

## Documentation

See docs/ for all documentation

Python Technical Documentation - explaination of source code, architecture, and data structures

YAML Test Script Documentation - expected syntax of test scripts

User Manual - application usage

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
