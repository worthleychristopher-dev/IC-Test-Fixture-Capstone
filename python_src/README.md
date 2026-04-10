# IC Test Fixture Python Application

A standalone GUI application for controlling the reconfigurable IC test fixture. 
Users can write or upload YAML-based test scripts to execute tests, 
with results exported as PDF files.

Requires Python >= 3.10

## Installation

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

## Running Tests

```sh
pytest
```

## Documentation

TBA - links to documentation

## Package Structure

```
python_src/
├── README.md               # project overview, and instructions
├── pyproject.toml          # package metadata and dependencies
├── src/
│   └── ic_test_fixture/
│       ├── device/         # device-related modules
│       ├── fileIO/         # file parsing, and exporting data
│       ├── gui/            # graphical user interface code
│       ├── utils/          # misc. code / helper tools
│       ├── __init__.py
│       └── main.py         # application entry point
└── tests/
    ├── unittest_yaml/      # YAML-based test scripts for unit tests
    ├── test_parser.py      # tests for parser module
    └── test_test_vector.py # tests for test_vector module
```
