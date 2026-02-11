import os
import yaml
import warnings
import regex as re

from testvector import TestVector, IOCommand, LogicMapping
from enum import Enum

# global macros for parser
INPUT_LOGIC = {"H", "L", "R_CLK", "F_CLK", "X"}
# Q_0 seems to serve same purpose as 'S'
OUTPUT_LOGIC = {"H", "L", "Z", "X", "S", "T", "Q_0"}
TRUTH_TABLE_LOGIC = INPUT_LOGIC | OUTPUT_LOGIC
SUPPORTED_VOLTAGES = {"0V", "1.8V", "2.5V", "3.3V", "4V", "4.5V", "5V"} # could remove V from test scripts
MAX_PINS = 20
# [digits] opt. decimal point [digits], space, [k or M]
NUM_WITH_UNIT = r"\d*\.?\d+\s[k|M]$"
class Clock(Enum): MAX = -1; MIN = -1
class VoltageUnit(Enum): k = 10e3; M = 10e6

# declare parser exceptions here
class ParseError(Exception):
    pass
class TableParseError(Exception):
    pass
class TestParseError(Exception):
    pass
class MissingKeys(Exception):
    pass

def check_type(val: any, exp_types: tuple, section: str, key: str) -> None:
    """
        helper function, checks if val is one of exp_types
    """
    if not isinstance(val, exp_types):
        err_str = f"Expected type "
        for exp_type in exp_types:
            err_str += f"\"{exp_type.__name__}\", " 
        err_str += f"got \"{type(val).__name__}\", in \"{section}[{key}]\""
        raise TypeError(err_str)
    return

def check_pin(pin: int, section: str, key: str) -> None:
    """
        helper function, check if pin is between 1 and MAX_PINS
    """
    if not (0 < pin <= MAX_PINS):
        raise ValueError(
            f"Pin number must be between 1 and {MAX_PINS}, got \"{pin}\" in \"{section}[{key}]\""
        )
    return

def check_keys(exp_keys: set, opt_keys: set, got_keys: set, section: str) -> None:
    """
        helper function, checks if got_keys are in exp_keys and opt_keys
    """
    missing_keys = exp_keys - got_keys
    if missing_keys:
        raise MissingKeys(
            f"Missing required keys: {missing_keys}, in \"{section}\""
        )

    ignored_keys = got_keys-exp_keys-opt_keys if opt_keys else got_keys-exp_keys
    if ignored_keys:
        warnings.warn(f"Ignoring unexpected keys: {ignored_keys}, in \"{section}\"")
    return

def parse(file_path: str):
    """
        parses yaml test script for valid syntax, and valid names/values
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

        exp_keys = {"Global Parameters", "Tests"}
        opt_keys = {"Chip Info", "Pin Map", "Truth Table"}
        check_keys(exp_keys, opt_keys, data.keys(), file_path)

        chip_info = data.get("Chip Info", None)
        pin_map = data.get("Pin Map", None)
        truth_table = data.get("Truth Table", None)

        try:
            # if chip_info: parse_chip_info(chip_info)
            parse_global_params(data["Global Parameters"])

            vcc_pin = data["Global Parameters"]["VCC Pin"]
            gnd_pin = data["Global Parameters"]["GND Pin"]
            if pin_map is not None: parse_pin_map(pin_map, vcc_pin, gnd_pin)

            tt = parse_truth_table(truth_table) if truth_table is not None else None

            test_vecs = parse_tests(data["Tests"], pin_map, tt)
        except Exception as e:
            print(e)
            raise ParseError(
                f"Failed to parse {file_path}"
            )

        # update class attributes, affects all instances of TestVector
        TestVector.update_pin_map(pin_map)
        TestVector.update_global_params(data["Global Parameters"])

        return chip_info, test_vecs
    
# optional section, will be written into PDF report, likely nothing to check
# def parse_chip_info(chip_info: dict):
#     """
#         parses chip info section of yaml test script
#     """
#     pass

# optional section, allows abstraction for Tests section
def parse_pin_map(pin_map: dict, vcc_pin: int, gnd_pin: int) -> None:
    """
        parses pin map section of yaml test script
    """
    used_pins = set()
    for pin in pin_map:
        # pin name must be str to avoid conflicts
        # int reserved for direct mapping to socket
        check_type(pin, (str,), "Pin Map", pin)
        check_type(pin_map[pin], (int,), "Pin Map", pin)
        check_pin(pin_map[pin], "Pin Map", pin)
        
        if pin_map[pin] == vcc_pin:
            raise ValueError(
                f"Pin number must not be same as VCC Pin: {vcc_pin}, "
                f"got \"{pin_map[pin]}\" in \"Pin Map[{pin}]\""
            )
        
        if pin_map[pin] == gnd_pin:
            raise ValueError(
                f"Pin number must not be same as GND Pin: {gnd_pin}, "
                f"got \"{pin_map[pin]}\" in \"Pin Map[{pin}]\""
            )

        if pin_map[pin] in used_pins:
            warnings.warn(f"Multiple names map to same pin: \"{pin_map[pin]}\"")
        else:
            used_pins.add(pin_map[pin])
    return

# optional section, allows abstraction for Tests section
def parse_truth_table(truth_table: list[dict]) -> dict:
    """
        parses truth table section of yaml test script
    """
    col_num = len(truth_table[0])
    col_names = truth_table[0].keys()
    # col name must be str to avoid conflicts
    # int reserved for binary inputs with 0b and integers
    for col_name in col_names: check_type(col_name, (str,), "Truth Table", col_name)
    # restructure truth table to use list for each column
    tt = {col: [None] * len(truth_table) for col in col_names}
    for i, row in enumerate(truth_table):
        # checks all rows have same number of columns as first row
        if len(row) != col_num:
            raise TableParseError(
                "Inconsistent number of columns in \"Truth Table\""
            )
        
        for key in row:
            # checks if all rows have same column names as first row
            if key not in col_names:
                raise TableParseError(
                    "Inconsistent column names in \"Truth Table\""
                )
            # identifier can't be one of reserved logic symbols
            if key in TRUTH_TABLE_LOGIC:
                raise ValueError(
                    f"Invalid identifier, can not use any of {TRUTH_TABLE_LOGIC}, "
                    f"got \"{key}\" in \"Truth Table\""
                )
            
            if row[key] not in TRUTH_TABLE_LOGIC:
                raise ValueError(
                    f"Invalid logic \"{row[key]}\" for column \"{key}\", "
                    f"expected one of {TRUTH_TABLE_LOGIC} in \"Truth Table\""
                )
            tt[key][i] = row[key]
    return tt

def parse_global_params(global_params: dict) -> None:
    """
        parses Global Parameters section of yaml test script
    """
    # maybe have structured test param section to remove match statements
    exp_keys = {"VCC Pin", "GND Pin", "VCC Voltage", "Output Low", "Output High"}
    opt_keys = {"CLK Freq", "Input Low", "Input High"}
    check_keys(exp_keys, opt_keys, global_params.keys(), "Global Parameters")
    
    # check VCC Pin and GND Pin are valid
    check_type(global_params["VCC Pin"], (int,), "Global Parameters", "VCC Pin")
    check_type(global_params["GND Pin"], (int,), "Test Parameters", "GND Pin")
    for param in ("VCC Pin", "GND Pin"):
        check_pin(global_params[param], "Global Parameters", param)

    if global_params["VCC Pin"] == global_params["GND Pin"]:
        raise ValueError(
            f"VCC Pin and GND Pin are the same, got \"{global_params["VCC Pin"]}\""
        )
    # check VCC Voltage is valid
    if global_params["VCC Voltage"] not in SUPPORTED_VOLTAGES:
        raise ValueError(
                f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
                f"got \"{global_params["VCC Voltage"]}\" in \"Global Parameters[VCC Voltage]\""
            )
    
    for key in ["Output Low", "Output High", "Input Low", "Input High"]:
        thld = global_params.get(key, None)
        if thld:
            check_type(thld, (int, float), "Global Parameters", key)
            if thld < 0:
                raise ValueError(
                    f"Expected voltage threshold greater than or equal to \"0\", "
                    f"got \"{thld}\", in \"Global Parameters[{key}]\""
                )

    # low threshold cannot be greater than high threshold
    if global_params["Output Low"] >= global_params["Output High"]:
        raise ValueError(
            f"Voltage Output Low is greater than or equal to Voltage Output High, "
            f"got {global_params["Output Low"]} >= {global_params["Output High"]}"
        )
    
    # optional arguments
    input_low = global_params.get("Input Low", None)
    input_high = global_params.get("Input High", None)
    if input_low and input_high:
        if input_low >= input_high:
            raise ValueError(
            f"Voltage Input Low is greater than or equal to Voltage Input High, "
            f"got {input_low} >= {input_low}"
        )

    # check CLK Freq is valid
    clk_freq = global_params.get("CLK Freq", None)
    if clk_freq:
        check_type(clk_freq, (str, int, float), "Test Parameters", "CLK_Freq")
        if isinstance(clk_freq, str):
            if re.match(NUM_WITH_UNIT, global_params[param]) is None:
                raise ValueError(
                    f"Invalid format for CLK Freq, got {clk_freq}\n"
                    "Syntax - CLK Freq: val [unit]"
                )
            parts = clk_freq.split()
            global_params["CLK Freq"] = float(parts[0]) * VoltageUnit[parts[1]].value
        if not (Clock.MIN.value <= global_params["CLK Freq"] <= Clock.MAX.value):
            raise ValueError(
                f"CLK Freq must be between or equal to "
                f"{Clock.MIN} and {Clock.MAX}, "
                f"got \"{global_params["CLK Freq"]}\" in \"Test Parameters[CLK Freq]\""
            )
        # TODO: check if its a feasible clock/round it
    return

def parse_tests(tests: dict, pin_map: dict, truth_table: dict) -> dict[str, TestVector]:
    """
        parses Tests section of yaml test script
    """
    exp_keys = {"Inputs", "Outputs"}
    # test_vecs = {test_name: TestVector() for test_name in tests}
    test_vecs = [None] * len(tests) 
    for i, (test_name, test) in enumerate(tests.items()):
        check_keys(exp_keys, None, test.keys(), f"Tests[{test_name}]")
        input_cmds = parse_test_io(test["Inputs"], pin_map, truth_table, INPUT_LOGIC, test_name)
        output_cmds = parse_test_io(test["Outputs"], pin_map, truth_table, OUTPUT_LOGIC, test_name)
        test_vecs[i] = TestVector(input_cmds, output_cmds, test_name)
    return test_vecs

def parse_test_io(io: dict, pin_map: dict, truth_table: dict, valid_logic: set[str], test_name: str) -> list[tuple]:
    """
        helper function to parse_tests, parses Inputs/Outputs sections of each test
    """
    # TODO: figure out how to make work with shift registers
    # TODO: check voltage is within input thresholds, otherwise raise a warning, maybe easier in TestVector class
    # returning data structure: list of tuples, each tuple is (list of pin numbers, list of pin values, voltage)
    vec = [None for _ in range(len(io))]
    for i, pins in enumerate(io):
        # check pin is either valid pin number or name from pin map
        check_type(pins, (int, str), f"Tests[{test_name}]", "I/O")
        pin_names = [pins] if isinstance(pins, int) else pins.split(",")
        for pin_name in pin_names:
            if isinstance(pin_name, int): 
                val = pin_name
            elif pin_name.isdigit(): 
                val = int(pin_name) # convert digits to int representation
            # check if identifer is in pin map
            elif pin_map is not None and pin_name in pin_map:
                val = pin_map[pin_name]
            else:
                raise ValueError(
                    f"Unknown pin name \"{pin_name}\" in \"Tests[{test_name}]\"\n"
                    "Either provide valid pin number or define pin name in Pin Map"
                )

            check_pin(val, "Tests", test_name)

        # check pin value is valid character or identifier from truth table
        check_type(io[pins], (str, int), f"Tests[{test_name}]", pins)
        if not isinstance(io[pins], str): io[pins] = str(io[pins]) # normalize command as str
        # could add output pin explicitly state clock dependency on certain pins
        cmd = io[pins].split(" ")
        pin_vals = cmd[0].split(",")
        voltage = cmd[-1] if len(cmd) >= 2 else None

        if voltage is not None and voltage not in SUPPORTED_VOLTAGES:
            raise ValueError(
                f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
                f"got \"{voltage}\" in \"Tests[{test_name}]\""
            )
        
        parsed_pin_vals = []
        cmd_type = None
        for pin_val in pin_vals:
            # converts binary to ints
            if pin_val.startswith("0b") or pin_val.isdigit():
                # for now only support lone integers, not 0b10,0b11
                if len(pin_vals) != 1:
                    # only one integer input allowed per line
                    raise TestParseError(
                        f"Only 1 integer input allowed for input mapping, "
                        f"got {pin_vals} in \"Test[{test_name}]\""
                    )
                val = int(pin_val, 0) # base=0 autodetects from string
                # check if int possible
                if not (val <= 2**len(pin_names) - 1):
                    raise ValueError(
                        f"Integer value \"{val}\" exceeds maximum value: {2**len(pin_names) - 1} "
                        f"for {len(pin_names)} pin(s), got \"{val}\" in \"Tests[{test_name}][{pins}]\""
                    )
                parsed_pin_vals.append(val)
                new_cmd_type = LogicMapping.map
            # replace identifier with value from truth table
            # maybe don't, to make testing truth tables easier in test_vector.py?
            elif truth_table and pin_val in truth_table:
                parsed_pin_vals.extend(truth_table[pin_val])
                new_cmd_type = LogicMapping.truth_table
            # no truth table, using logic set
            else:
                if pin_val not in valid_logic:
                    raise ValueError(
                        f"Invalid char/identifier \"{pin_val}\" for pin \"{pins}\", "
                        f"expected one of {valid_logic}, or identifier in \"Truth Table\" in \"Tests[{test_name}]\""
                    )
                parsed_pin_vals.append(pin_val)
                new_cmd_type = None

            if cmd_type is None:
                cmd_type = new_cmd_type
            # cannot not mix truth_table with any other type
            elif LogicMapping.truth_table in (cmd_type, new_cmd_type) and cmd_type != new_cmd_type:
                raise TestParseError(
                    f"Cannot mix truth table mapping with any other pin mapping "
                    f"in \"Tests[{test_name}]\""
                )

        # was not integer or truth table
        if cmd_type is None:
            if len(pin_names) == len(pin_vals):
                cmd_type = LogicMapping.map
            elif len(pin_vals) == 1:
                cmd_type = LogicMapping.single
            else:
                # cannot map inputs to pins
                raise TestParseError(
                    f"Incompatible lengths of I/O pins ({len(pin_names)}) and values ({len(pin_vals)}), " 
                    f"both must be same length, or values has length of 1 in \"Tests[{test_name}]\""
                )
        vec[i] = IOCommand(pin_names, parsed_pin_vals, voltage, cmd_type)
    return vec
