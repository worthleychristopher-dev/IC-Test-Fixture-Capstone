import yaml
import warnings
import os

from enum import Enum

from ICTestFixture.device.test_vector import TestVector, IOCommand, LogicMapping

# global macros for parser
INPUT_LOGIC = {"H", "L", "R", "F", "X"}
# Q_0 seems to serve same purpose as 'S'
OUTPUT_LOGIC = {"H", "L", "Z", "X", "S", "T"}
TRUTH_TABLE_LOGIC = INPUT_LOGIC | OUTPUT_LOGIC
SUPPORTED_VOLTAGES = {0, 1.8, 2.5, 3.3, 4, 4.5, 5}
MAX_PINS = 20

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

def check_pin(pin: int|str, section: str, key: str) -> None:
    """
        helper function, check if pin is between 1 and MAX_PINS
    """
    if not (0 < pin <= MAX_PINS):
        raise ValueError(
            f"Pin number must be between 1 and {MAX_PINS}, got \"{pin}\" in \"{section}[{key}]\""
        )
    return

def check_voltage(voltage: str, section: str, key: str) -> None:
    if voltage not in SUPPORTED_VOLTAGES:
        raise ValueError(
            f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
            f"got \"{voltage}\" in \"{section}[{key}]\""
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

    ignored_keys = got_keys - exp_keys - opt_keys if opt_keys is not None else got_keys-exp_keys
    if ignored_keys:
        warnings.warn(f"Ignoring unexpected keys: {ignored_keys}, in \"{section}\"")
    return


def parse(file_path: str):
    """
        parses yaml test script for valid syntax, and valid names/values
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

        try:
            exp_keys = {"Global Parameters", "Tests"}
            opt_keys = {"Chip Info", "Pin Map", "Truth Table"}
            check_keys(exp_keys, opt_keys, data.keys(), file_path)

            chip_info = data.get("Chip Info", None)
            pin_map = data.get("Pin Map", None)
            truth_table = data.get("Truth Table", None)

            # if chip_info: parsechip_info(chip_info)
            parse_global_params(data["Global Parameters"])

            vcc_pin = data["Global Parameters"]["VCC Pin"]
            gnd_pin = data["Global Parameters"]["GND Pin"]
            if pin_map is not None: parse_pin_map(pin_map, vcc_pin, gnd_pin)

            tt = parse_truth_table(truth_table) if truth_table is not None else None

            test_vecs = parse_tests(data["Tests"], data["Global Parameters"], pin_map, tt)
        except Exception as e:
            raise ParseError(f"Failed to parse {file_path}") from e

        return chip_info, test_vecs
    
# optional section, will be written into PDF report, likely nothing to check
# def parsechip_info(chip_info: dict):
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
            raise ValueError(
                f"Multiple names map to same pin: \"{pin_map[pin]}\""
            )
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

            if row[key] not in TRUTH_TABLE_LOGIC:
                raise ValueError(
                    f"Invalid logic \"{row[key]}\" for column \"{key}\", "
                    f"expected one of {TRUTH_TABLE_LOGIC} in \"Truth Table\""
                )
            tt[key][i] = row[key]
    return tt

def parse_global_params(global_param: dict) -> None:
    """
        parses Global Parameters section of yaml test script
    """
    # maybe have structured test param section to remove match statements
    exp_keys = {"VCC Pin", "GND Pin", "VCC Voltage", "Output Low", "Output High"}
    opt_keys = {"CLK Freq", "Input Low", "Input High"}
    check_keys(exp_keys, opt_keys, global_param.keys(), "Global Parameters")
    # check_voltage(global_param["VCC Voltage"], "Global Parameters", "VCC Voltage") # check VCC Voltage is valid
    # check VCC Pin and GND Pin are valid
    check_type(global_param["VCC Pin"], (int,), "Global Parameters", "VCC Pin")
    check_type(global_param["GND Pin"], (int,), "Global Parameters", "GND Pin")
    for param in ("VCC Pin", "GND Pin"):
        check_pin(global_param[param], "Global Parameters", param)

    if global_param["VCC Pin"] == global_param["GND Pin"]:
        raise ValueError(
            f"VCC Pin and GND Pin are the same, got \"{global_param["VCC Pin"]}\""
        )
    
    # wrap everything into list for consistency when only 1 value is provided
    # make testing loop at various VCC Voltages easier
    length = set()
    for param in ["VCC Voltage", "Output Low", "Output High", "Input Low", "Input High"]:
        if param in global_param:
            if not isinstance(global_param[param], list):
                global_param[param] = [global_param[param]]
            length.add(len(global_param[param]))
    
    if len(length) > 1:
        raise ValueError(
            f"Inconsistent number of values for VCC Voltage and voltage thresholds, "
            f"got {length} values in \"Global Parameters\""
        )
    
    for param in ["Output Low", "Output High", "Input Low", "Input High"]:
        thlds = global_param.get(param, None)
        if thlds is not None:
            for thld in thlds:
                check_type(thld, (int, float), "Global Parameters", param)
                if thld < 0:
                    raise ValueError(
                        f"Expected voltage threshold greater than or equal to \"0\", "
                        f"got \"{thld}\", in \"Global Parameters[{param}]\""
                    )

    param_length = next(iter(length))
    for i in range(param_length):
        check_voltage(global_param["VCC Voltage"][i], "Global Parameters", f"VCC Voltage") # check VCC Voltage is valid
        # low threshold cannot be greater than high threshold
        # output thresholds
        if global_param["Output Low"][i] >= global_param["Output High"][i]:
            raise ValueError(
                f"Voltage Output Low is greater than or equal to Voltage Output High, "
                f"got {global_param['Output Low'][i]} >= {global_param['Output High'][i]}"
            )
        # input thresholds
        if "Input Low" in global_param and "Input High" in global_param:
            if global_param["Input Low"][i] >= global_param["Input High"][i]:
                raise ValueError(
                    f"Voltage Input Low is greater than or equal to Voltage Input High, "
                    f"got {global_param['Input Low'][i]} >= {global_param['Input High'][i]}"
                )

    # # check CLK Freq is valid
    # clkFreq = global_param.get("CLK Freq", None)
    # if clkFreq:
    #     check_type(clkFreq, (str, int, float), "Test Parameters", "CLKFreq")
    #     if isinstance(clkFreq, str):
    #         if re.match(NUM_WITH_UNIT, global_param["CLK Freq"]) is None:
    #             raise ValueError(
    #                 f"Invalid format for CLK Freq, got {clkFreq}\n"
    #                 "Syntax - CLK Freq: val [unit]"
    #             )
    #         parts = clkFreq.split()
    #         global_param["CLK Freq"] = float(parts[0]) * VoltageUnit[parts[1]].value
    #     if not (Clock.MIN.value <= global_param["CLK Freq"] <= Clock.MAX.value):
    #         raise ValueError(
    #             f"CLK Freq must be between or equal to "
    #             f"{Clock.MIN} and {Clock.MAX}, "
    #             f"got \"{global_param["CLK Freq"]}\" in \"Test Parameters[CLK Freq]\""
    #         )
    #     # TODO: check if its a feasible clock/round it
    return

def parse_tests(tests: dict, global_param: dict, pin_map: dict, truth_table: dict) -> list[TestVector]:
    """
        parses Tests section of yaml test script
    """
    exp_keys = {"Inputs", "Outputs"}
    test_vecs = [None for _ in range(len(tests))]
    for i, (test_name, test) in enumerate(tests.items()):
        check_keys(exp_keys, None, test.keys(), f"Tests[{test_name}]")
        input_cmd = parse_test_IO(test["Inputs"], pin_map, truth_table, INPUT_LOGIC, test_name)
        output_cmds = parse_test_IO(test["Outputs"], pin_map, truth_table, OUTPUT_LOGIC, test_name)
        test_vecs[i] = TestVector(input_cmd, output_cmds, global_param, pin_map, test_name)
    return test_vecs

def parse_test_IO(io: dict, pin_map: dict, truth_table: dict, valid_logic: set[str], test_name: str) -> list[IOCommand]:
    """
        helper function to parse_tests, parses Inputs/Outputs sections of each test
    """
    # TODO: check voltage is within input thresholds, otherwise raise a warning, maybe easier in TestVector class
    # returning data structure: list of tuples, each tuple is (list of pin numbers, list of pin values, voltage)
    vec = [None for _ in range(len(io))]
    for i, pins in enumerate(io):
        # check pin is either valid pin number or name from pin map
        check_type(pins, (int, str), f"Tests[{test_name}]", "I/O")
        pin_names = [pins] if isinstance(pins, int) else [p.strip() for p in pins.split(",")]
        for j, pin_name in enumerate(pin_names):
            if isinstance(pin_name, int): 
                pin = pin_name
                store = pin
            elif pin_name.isdigit(): 
                pin = int(pin_name) # convert digits to int representation
                store = pin
            # check if identifer is in pin map
            elif pin_map is not None and pin_name in pin_map:
                pin = pin_map[pin_name]
                store = pin_name
            else:
                raise ValueError(
                    f"Unknown pin name \"{pin_name}\" in \"Tests[{test_name}]\"\n"
                    "Either provide valid pin number or define pin name in Pin Map"
                )

            check_pin(pin, "Tests", test_name)
            pin_names[j] = store

        # check pin value is valid character or identifier from truth table
        cmd_type = None
        voltage = None
        if isinstance(io[pins], list):
            cmd_type = LogicMapping.Serial
            pin_vals = io[pins]
            voltage = None
        elif isinstance(io[pins], (str, int)):
            if not isinstance(io[pins], str): io[pins] = str(io[pins])
            cmd = io[pins].strip().split(" ")
            pin_vals = [p.strip() for p in cmd[0].split(",")]
            voltage = cmd.strip() if len(cmd) >= 2 else None
        else:
            # this will raise an error
            check_type(io[pins], (str, int, list), f"Tests[{test_name}]", pins)

        if voltage is not None:
            check_voltage(voltage, "Tests", test_name)
        
        parsed_pin_vals = []
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
                val = int(pin_val, 0) # autodetects base from string
                # check if int possible
                if not (val <= 2**len(pin_names) - 1):
                    raise ValueError(
                        f"Integer value \"{val}\" exceeds maximum value: {2**len(pin_names) - 1} "
                        f"for {len(pin_names)} pin(s), got \"{val}\" in \"Tests[{test_name}][{pins}]\""
                    )
                parsed_pin_vals.append(val)
                cmd_type = LogicMapping.Map
            # replace reference with value from truth table
            # maybe don't, to make testing truth tables easier in testVector.py?
            elif truth_table is not None and pin_val in truth_table:
                if len(pin_vals) > 1:
                    raise TestParseError(
                        f"Cannot have multiple outpins in same line when using truth table value"
                    )
                parsed_pin_vals.extend(truth_table[pin_val])
                cmd_type = LogicMapping.TruthTable
            # no truth table, using logic set
            else:
                if pin_val not in valid_logic:
                    raise ValueError(
                        f"Invalid logic/reference \"{pin_val}\" for pin \"{pins}\", "
                        f"expected one of {valid_logic}, or reference in \"Truth Table\" in \"Tests[{test_name}]\""
                    )
                parsed_pin_vals.append(pin_val)
                if cmd_type is None:
                    if len(pin_vals) == 1:
                        cmd_type = LogicMapping.Single
                    elif len(pin_names) == len(pin_vals):
                        cmd_type = LogicMapping.Map
                    else:
                        # cannot map inputs to pins
                        raise TestParseError(
                            f"Incompatible lengths of I/O pins ({len(pin_names)}) and values ({len(pin_vals)}), " 
                            f"both must be same length, or values has length of 1 in \"Tests[{test_name}]\""
                        )
        
        vec[i] = IOCommand(pins, parsed_pin_vals, voltage, cmd_type)

    # Global mapping consistency check
    all_cmd_types = {entry.cmd_type for entry in vec if entry is not None}

    if (
        LogicMapping.TruthTable in all_cmd_types
        and any(cmd != LogicMapping.TruthTable for cmd in all_cmd_types)
    ):
        raise TestParseError(
            f"Cannot mix truth table mapping with any other pin mapping "
            f'in "Tests[{test_name}]"'
        )

    return vec

if __name__ == "__main__":
    folder_path = ["test_scripts/hc", "test_scripts/hct"]
    num_scripts = sum(len(os.listdir(folder)) for folder in folder_path)
    failed = 0
    for folder in folder_path:
        for file in os.listdir(folder):
            try:
                print(f"Parsing {file}")
                parse(os.path.join(folder, file))
            except Exception as e:
                print(e)
                print(e.__context__)
                failed += 1
    print(f"{failed}/{num_scripts}")
