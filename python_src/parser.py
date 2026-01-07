import yaml
from test_vector import TestVector
import regex as re
import os

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
class UnknownKeyWordError(Exception):
    pass
class TableParseError(Exception):
    pass
class MissingThresholds(Exception):
    pass
class MissingTestParameters(Exception):
    pass

def type_error_msg(val: any, exp_types: tuple, section: str, key: str):
    """"
        type error message helper function
    """
    err_str = f"Expected type "
    for exp_type in exp_types:
        err_str += f"\"{exp_type.__name__}\", " 
    err_str += f"got \"{type(val).__name__}\", in \"{section}[{key}]\""
    return err_str

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
    for pin in pin_map.keys():
        # pin name must be str to avoind conflicts
        # int reserved for direct mapping to socket
        if not isinstance(pin, str):
            raise TypeError(
                type_error_msg(pin, (str,), "Pin Map", pin)
            )
        
        if not isinstance(pin_map[pin], int):
            raise TypeError(
                type_error_msg(pin_map[pin], (int,), "Pin Map", pin)
            )
        
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
    # restructure truth table to use list for each column
    tt = {col: [None] * len(truth_table) for col in col_names}
    for i, row in enumerate(truth_table):
        # checks all rows have same number of columns as first row
        if len(row) != col_num:
            raise TableParseError(
                "Inconsistent number of columns in \"Truth Table\""
            )
        for key in row.keys():
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
            # col name must be str to avoid conflicts
            # int reserved for binary inputs with 0b and integers
            if not isinstance(key, str):
                raise TypeError(
                    type_error_msg(key, (str,), "Truth Table", key)
                )
            tt[key][i] = row[key]
    return tt

def parse_tests(tests: dict, pin_map: dict, truth_table: dict):
    """
        parses tests section of yaml test script
    """
    # maybe have structured tests section to remove match statements
    test_vecs = TestVector(tests.keys())
    for test_name in tests.keys():
        for test_param in tests[test_name].keys():
            test = tests[test_name]
            match test_param:
                case "Inputs":
                    test_vecs.add_input_vector(test_name, 
                        parse_test_io(test[test_param], pin_map, truth_table, INPUT_LOGIC, test_name))
                case "Outputs":
                    test_vecs.add_output_vector(test_name, 
                        parse_test_io(test[test_param], pin_map, truth_table, OUTPUT_LOGIC, test_name))
                case _:
                    raise UnknownKeyWordError(
                    f"Keyword \"{test_param}\" in \"Tests[{test_name}]\" is unknown"
                )
    return test_vecs

def parse_test_io(io: dict, pin_map: dict, truth_table: dict, valid_logic: set, test_name: str):
    """
        helper function to parse_tests, parses Inputs/Outputs sections of each test
    """
    vec = [None] * len(io.keys())
    for i, pins in enumerate(io.keys()):
        # verify pin is either valid pin number or name from pin map
        pin_names = None
        if isinstance(pins, int):
            pin_names = [str(pins)]
        elif isinstance(pins, str):
            pin_names = pins.split(",")
        else:
            raise TypeError(
                type_error_msg(pins, (int, str), f"Tests[{test_name}]", "I/O")
            )
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

        # verify pin value is valid character or identifier from truth table
        pin_vals = None
        # int case
        if isinstance(io[pins], int):
            if not (io[pins] <= 2**len(pin_names) - 1):
                raise ValueError(
                    f"Integer value \"{io[pins]}\" exceeds maximum value: {2**len(pin_names) - 1} "
                    f"for {len(pin_names)} pin(s), got \"{io[pins]}\" in \"Tests[{test_name}][{pins}]\""
                )
            pin_vals = io[pins]
        # str case
        elif isinstance(io[pins], str):
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
        else:
            raise TypeError(
                type_error_msg(io[pins], (str, int), f"Tests[{test_name}]", pins)
            )
        vec[i] = (pin_names, pin_vals)
    return vec

def parse_voltage_thresholds(thresholds: dict):
    """
        parses voltage thresholds section of yaml test script
    """
    # TODO: add HC chip support, thresholds vary with different VCC
    # maybe have structured voltage thresholds section to remove match statements
    # variables to read voltage thresholds into
    vil = vih = vol = voh = None

    for volt_thld in thresholds.keys():
        if not isinstance(thresholds[volt_thld], (int, float)):
            raise TypeError(
                type_error_msg(thresholds[volt_thld], (int, float), "Voltage Thresholds", volt_thld)
            )
        if thresholds[volt_thld] < 0:
            raise ValueError(
                f"Expected voltage threshold greater than or equal to \"0\", "
                f"got \"{thresholds[volt_thld]}\", in \"Voltage Thresholds[{volt_thld}]\""
            )
        match volt_thld:
            case "Vil":
                vil = thresholds[volt_thld]
            case "Vih":
                vih = thresholds[volt_thld]
            case "Vol":
                vol = thresholds[volt_thld]
            case "Voh":
                voh = thresholds[volt_thld]
            case _:
                raise UnknownKeyWordError(
                    f"Keyword \"{volt_thld}\" in \"Voltage Thresholds\" is unknown"
                )

    # all voltage thresholds must be in test script, no None
    # possibly remove vil and vih?
    if any(threshold is None for threshold in (vil, vih, vol, voh)):
        raise MissingThresholds(
            "Missing voltage threshold for one or more thresholds, "
            "must have \"Vil\", \"Vih\", \"Vol\", and \"Voh\""
        )
    elif vil >= vih:
        raise ValueError(
            f"Vil is greater than or equal to Vih, got {vil} >= {vih}"
        )
    elif vol >= voh:
        raise ValueError(
            f"Vol is greater than or equal to Voh, got {vol} >= {voh}"
        )
    return

def parse_test_params(test_params: dict):
    """
        parses test parameters section of yaml test script
    """
    # maybe have structured test param section to remove match statements
    vcc_pin = gnd_pin = vref = None
    for param in test_params.keys():
        match param:
            case "Vref":
                if not isinstance(test_params[param], (list)):
                    test_params[param] = [test_params[param]]

                for voltage in test_params[param]:
                    if not isinstance(voltage, (int, float)):
                        raise TypeError(
                        type_error_msg(voltage, (int, float), "Test Parameters", param)
                        )
                
                    if voltage not in SUPPORTED_VOLTAGES:
                        raise ValueError(
                            f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
                            f"got \"{voltage}\" in \"Test Parameters[{param}]\""
                        )
                vref = test_params
            case "VCC Pin" | "GND Pin":
                if not isinstance(test_params[param], int):
                    raise TypeError(
                        type_error_msg(test_params[param], (int,), "Test Parameters", param)
                    )
                if not (0 < test_params[param] <= MAX_PINS):
                    raise ValueError(
                        f"Pin number must be between or equal to 1 and {MAX_PINS}, "
                        f"got \"{test_params[param]}\" in \"Test Parameters[{param}]\""
                    )
                if param == "VCC Pin":
                    vcc_pin = test_params[param]
                else:
                    gnd_pin = test_params[param]
            # could add support for list of clk freq
            case "CLK Freq":
                if isinstance(test_params[param], str):
                    if re.match(NUM_WITH_UNIT, test_params[param]) is None:
                        raise ValueError(
                                f"Invalid format for CLK Freq, got {test_params[param]}\n"
                                "Syntax - CLK Freq: val [unit]"
                        )
                    parts = test_params[param].split()
                    test_params[param] = float(parts[0]) * UNIT_CONV[parts[1]]
                # int and float are valid clk freq
                # TODO: check if its a feasible clk freq/round number
                elif not isinstance(test_params[param], (int, float)):
                    raise TypeError(
                        type_error_msg(test_params[param], (str, int, float), "Test Parameters", param)
                    )
                
                if not (CLK_RANGE["MIN"] <= test_params[param] <= CLK_RANGE["MAX"]):
                    raise ValueError(
                        f"CLK Freq must be between or equal to "
                        f"{CLK_RANGE["MIN"]} and {CLK_RANGE["MAX"]}, "
                        f"got \"{test_params[param]}\" in \"Test Parameters[{param}]\""
                    )
            case _:
                raise UnknownKeyWordError(
                    f"Keyword \"{param}\" in \"Test Parameters\" is unknown"
                )
    # required to power IC, and which voltages to use during testing
    if any(test_param is None for test_param in (vcc_pin, gnd_pin, vref)):
        raise MissingTestParameters(
            "Missing test parameter for one or more parameters, "
            "must have \"VCC Pin\", \"GND Pin\", and \"Vref\""
        )
    
    if vcc_pin == gnd_pin:
        raise ValueError(
            f"VCC Pin and GND Pin are the same, got \"{vcc_pin}\""
        )
    return

if __name__ == "__main__":
    folder_path = "/home/chefshouse/Capstone/test_scripts/hct"
    failed = 0
    for file in os.listdir(folder_path):
        try:
            parse(os.path.join(folder_path, file))
        except Exception as e:
            print(e)
            failed += 1
    print(f"{failed}/{len(os.listdir(folder_path))}")