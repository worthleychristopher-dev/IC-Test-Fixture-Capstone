from test_vector import TestVector
import yaml
import warnings
import regex as re

# global macros for parser
INPUT_LOGIC = {0, 1, "H", "L", "R_CLK", "F_CLK", "X"}
OUTPUT_LOGIC = {0, 1, "H", "L", "Z", "X", "S", "T", "Q_0"}
TRUTH_TABLE_LOGIC = INPUT_LOGIC | OUTPUT_LOGIC
SUPPORTED_VOLTAGES = {0, 1.8, 2.5, 3.3, 4, 4.5, 5}
MAX_PINS = 20
CLK_RANGE = {"MIN" : -1, "MAX" : -1} # TODO: set proper clk range
UNIT_CONV = {"k" : 10e3, "M" : 10e6}
# [digits] opt. decimal point [digits], space, [k or M]
NUM_WITH_UNIT = r"\d*\.?\d+\s[k|M]$"

# declare parser exceptions here
class ParseError(Exception):
    pass
class TableParseError(Exception):
    pass
class MissingKeys(Exception):
    pass

def check_type(val: any, exp_types: tuple, section: str, key: str):
    """"
        type error message helper function
    """
    if not isinstance(val, exp_types):
        err_str = f"Expected type "
        for exp_type in exp_types:
            err_str += f"\"{exp_type.__name__}\", " 
        err_str += f"got \"{type(val).__name__}\", in \"{section}[{key}]\""
        raise TypeError(err_str)
    return

def check_keys(exp_keys: set, opt_keys: set, got_keys: set, section: str):
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

        chip_info = data.get("Chip Info", None)
        pin_map = data.get("Pin Map", None)
        truth_table = data.get("Truth Table", None)
        try:
            # if chip_info: parse_chip_info(chip_info)
            if pin_map: parse_pin_map(pin_map)
            tt = parse_truth_table(truth_table) if truth_table else None
            test_vecs = parse_tests(data["Tests"], pin_map, tt)
            parse_voltage_thresholds(data["Voltage Thresholds"])
            parse_test_params(data["Test Parameters"])
        except Exception as e:
            print(e)
            raise ParseError(
                f"Failed to parse {file_path}"
            )

        return chip_info, test_vecs, data["Voltage Thresholds"], data["Test Parameters"]
    
# optional section, will be written into PDF report, likely nothing to check
# def parse_chip_info(chip_info: dict):
#     """
#         parses chip info section of yaml test script
#     """
#     pass

# optional section, allows abstraction for Tests section
def parse_pin_map(pin_map: dict):
    """
        parses pin map section of yaml test script
    """
    for pin in pin_map:
        # pin name must be str to avoind conflicts
        # int reserved for direct mapping to socket
        check_type(pin, (str,), "Pin Map", pin)
        check_type(pin_map[pin], (int,), "Pin Map", pin)
        
        if not (0 < pin_map[pin] <= MAX_PINS):
            raise ValueError(
                f"Pin number must be between 1 and {MAX_PINS}, "
                f"got \"{pin_map[pin]}\" in \"Pin Map[{pin}]\""
            )
        # check pin configuration for I/O?
    return

# optional section, allows abstraction for Tests section
def parse_truth_table(truth_table: dict):
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

def parse_tests(tests: dict, pin_map: dict, truth_table: dict):
    """
        parses tests section of yaml test script
    """
    exp_keys = {"Inputs", "Outputs"}
    test_vecs = {test_name: TestVector() for test_name in tests}
    for test_name in tests:
        check_keys(exp_keys, None, tests[test_name].keys(), f"Tests[{test_name}]")

        inputs = tests[test_name].get("Inputs", None)
        outputs = tests[test_name].get("Outputs", None)
        
        test_vecs[test_name].add_input_vector(
            parse_test_io(inputs, pin_map, truth_table, INPUT_LOGIC, test_name))
        test_vecs[test_name].add_output_vector(
            parse_test_io(outputs, pin_map, truth_table, OUTPUT_LOGIC, test_name))
        
    return test_vecs

def parse_test_io(io: dict, pin_map: dict, truth_table: dict, valid_logic: set, test_name: str):
    """
        helper function to parse_tests, parses Inputs/Outputs sections of each test
    """
    vec = [None] * len(io)
    for i, pins in enumerate(io):
        # check pin is either valid pin number or name from pin map
        check_type(pins, (int, str), f"Tests[{test_name}]", "I/O")
        pin_names = [str(pins)] if isinstance(pins, int) else pins.split(",")
        for j, pin_name in enumerate(pin_names):
            # convert digits to int representation
            if pin_name.isdigit():
                if not (0 < int(pin_name) <= MAX_PINS):
                    raise ValueError(
                        f"Pin number must be between equal to or between 1 and {MAX_PINS}, "
                        f"got \"{pin_name}\" in \"Tests[{test_name}]\""
                    )
                pin_names[j] = int(pin_name)
            # convert pin name to int representation using pin map
            elif pin_map is not None:
                if pin_name not in pin_map:
                    raise ValueError(
                        f"Pin name \"{pin_name}\" not found in Pin Map"
                    )
                pin_names[j] = pin_map[pin_name]
            else:
                raise ValueError(
                    f"Unknown pin name \"{pin_name}\" in \"Tests[{test_name}]\"\n"
                    "Either provide valid pin number or define pin name in Pin Map"
                )
        # check if pin conflicts with I/O configuration?

        # check pin value is valid character or identifier from truth table
        pin_vals = None
        check_type(io[pins], (str, int), f"Tests[{test_name}]", pins)
        # int case
        if isinstance(io[pins], int):
            if not (io[pins] <= 2**len(pin_names) - 1):
                raise ValueError(
                    f"Integer value \"{io[pins]}\" exceeds maximum value: {2**len(pin_names) - 1} "
                    f"for {len(pin_names)} pin(s), got \"{io[pins]}\" in \"Tests[{test_name}][{pins}]\""
                )
            pin_vals = io[pins]
        # str case
        else:
            pin_vals = io[pins].split(",")
            for k, pin_val in enumerate(pin_vals):
                # replace identifier with value from truth table
                if truth_table and pin_val in truth_table:
                    pin_vals[k] = truth_table[pin_val]
                    continue
                # no truth table, using logic set
                if pin_val not in valid_logic:
                    raise ValueError(
                        f"Invalid char/identifier \"{io[pins]}\" for pin \"{pins}\", "
                        f"expected one of {valid_logic}, or identifier in \"Truth Table\" in \"Tests[{test_name}]\""
                    )
        vec[i] = (pin_names, pin_vals)
    return vec

def parse_voltage_thresholds(thresholds: dict):
    """
        parses voltage thresholds section of yaml test script
    """
    # TODO: add HC chip support, thresholds vary with different VCC
    exp_keys = {"Vil", "Vih", "Vol", "Voh"}
    check_keys({"Vil", "Vih", "Vol", "Voh"}, None, thresholds.keys(), "Voltage Thresholds")
    # check type and value of each threshold
    for key, volt_thld in thresholds.items():
        # ignore unknwon keys
        if key not in exp_keys:
            continue

        check_type(volt_thld, (int, float), "Voltage Thresholds", key)
        
        if volt_thld < 0:
            raise ValueError(
                f"Expected voltage threshold greater than or equal to \"0\", "
                f"got \"{volt_thld}\", in \"Voltage Thresholds[{key}]\""
            )
    # possibly remove vil and vih?
    # make sure logic High is greater than logic Low
    if thresholds["Vil"] >= thresholds["Vih"]:
        raise ValueError(
            f"Vil is greater than or equal to Vih, got {thresholds["Vil"]} >= {thresholds["Vih"]}"
        )
    elif thresholds["Vol"] >= thresholds["Voh"]:
        raise ValueError(
            f"Vol is greater than or equal to Voh, got {thresholds["Vol"]} >= {thresholds["Voh"]}"
        )
    return

def parse_test_params(test_params: dict):
    """
        parses test parameters section of yaml test script
    """
    # maybe have structured test param section to remove match statements
    exp_keys = {"Vref", "VCC Pin", "GND Pin"}
    opt_keys = {"CLK Freq"}
    check_keys(exp_keys, opt_keys, test_params.keys(), "Test Parameters")
    
    # check Vref is valid
    if not isinstance(test_params["Vref"], (list)):
        # make single Vref to match list of multiple Vref
        test_params["Vref"] = [test_params["Vref"]] 
    for voltage in test_params["Vref"]: 
        check_type(voltage, (int, float), "Test Parameters", "Vref")
        
        if voltage not in SUPPORTED_VOLTAGES:
            raise ValueError(
                f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
                f"got \"{voltage}\" in \"Test Parameters[Vref]\""
            )
    # check VCC Pin and GND Pin are valid
    check_type(test_params["VCC Pin"], (int,), "Test Parameters", "VCC Pin")
    check_type(test_params["GND Pin"], (int,), "Test Parameters", "GND Pin")
    for param in ("VCC Pin", "GND Pin"):
        if not (0 < test_params[param] <= MAX_PINS):
            raise ValueError(
                f"Pin number must be between or equal to 1 and {MAX_PINS}, "
                f"got \"{test_params[param]}\" in \"Test Parameters[{param}]\""
            )
    if test_params["VCC Pin"] == test_params["GND Pin"]:
        raise ValueError(
            f"VCC Pin and GND Pin are the same, got \"{test_params["VCC Pin"]}\""
        )
    
    # check CLK Freq is valid
    clk_freq = test_params.get("CLK Freq", None)
    if clk_freq:
        check_type(clk_freq, (str, int, float), "Test Parameters", "CLK_Freq")
        if isinstance(clk_freq, str):
            if re.match(NUM_WITH_UNIT, test_params[param]) is None:
                raise ValueError(
                    f"Invalid format for CLK Freq, got {clk_freq}\n"
                    "Syntax - CLK Freq: val [unit]"
                )
            parts = clk_freq.split()
            test_params["CLK Freq"] = float(parts[0]) * UNIT_CONV[parts[1]]
        if not (CLK_RANGE["MIN"] <= test_params["CLK Freq"] <= CLK_RANGE["MAX"]):
            raise ValueError(
                f"CLK Freq must be between or equal to "
                f"{CLK_RANGE["MIN"]} and {CLK_RANGE["MAX"]}, "
                f"got \"{test_params["CLK Freq"]}\" in \"Test Parameters[CLK Freq]\""
            )
        # TODO: check if its a feasible clock/round it
    return
