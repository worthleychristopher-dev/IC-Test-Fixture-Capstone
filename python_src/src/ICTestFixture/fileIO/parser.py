import yaml
import warnings

from typing import Tuple

from ICTestFixture.device.test_vector import TestVector, IOCommand, LogicMapping

# global macros for parser
INPUT_LOGIC = {"H", "L", "R", "F", "X"}
OUTPUT_LOGIC = {"H", "L", "Z", "X", "S", "T"}
TRUTH_TABLE_LOGIC = INPUT_LOGIC | OUTPUT_LOGIC
SUPPORTED_VOLTAGES = {0, 1.8, 2.5, 3.3, 4, 4.5, 5}
MAX_PINS = 20

# declare parser exceptions here
class ParseError(Exception):
    """Raised when any exception is raised."""
    pass
class TableParseError(Exception):
    """Raised when failed to parse Truth Table section."""
    pass
class TestParseError(Exception):
    """Raised when failed to parse Test section."""
    pass
class MissingKeys(Exception):
    """Raised when missing required keys for a section."""
    pass

def check_type(val: any, exp_types: tuple, section: str, key: str) -> None:
    """Checks if `val` type is in `exp_types`.

    Args:
        val (any): Data being parsed for correct type.
        exp_types (tuple): Tuple of valid types.
        section (str): Name of section `val` is from.
        key (str): Name of key `val` is from.

    Raises:
        TypeError: If `type(val)` not in `exp_types`.
    """
    if not isinstance(val, exp_types):
        err_str = f"Expected type "
        for exp_type in exp_types:
            err_str += f"\"{exp_type.__name__}\", " 
        err_str += f"got \"{type(val).__name__}\", in \"{section}[{key}]\""
        raise TypeError(err_str)
    return

def check_pin(pin: int, section: str, key: str) -> None:
    """Checks `pin` > 0 and < `MAX_PINS`.

    Args:
        pin (int): Pin number being parsed.
        section (str): Name of section `pin` is from.
        key (str): Name of key `pin` is from.

    Raises:
        ValueError: If `pin` is not within the valid range.
    """
    if not (0 < pin <= MAX_PINS):
        raise ValueError(
            f"Pin number must be between 1 and {MAX_PINS}, got \"{pin}\" in \"{section}[{key}]\""
        )
    return

def check_voltage(voltage: int|float, section: str, key: str) -> None:
    """Checks `voltage` is in `SUPPORTED_VOLTAGES`.
    
    Args:
        voltage (int|float): Voltage being parsed.
        sections (str): Name of section `voltage` is from.
        key (str): Name of the key `voltage` is from.

    Raises:
        ValueError: If `voltage` is not in `SUPPORTED_VOLTAGES`.
    """
    if voltage not in SUPPORTED_VOLTAGES:
        raise ValueError(
            f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
            f"got \"{voltage}\" in \"{section}[{key}]\""
        )
    return

def check_keys(exp_keys: set, opt_keys: set, got_keys: set, section: str) -> None:
    """Checks a section has all `exp_keys.`

    Args:
        exp_keys (set): Required keys for a section.
        opt_keys (set): Optional keys for a section.
        got_keys (set): Parsed keys got for a sections.
        section (str): Name of the section `got_keys` is from.
    
    Raises:
        MissingKeys: If `got_keys` does not have all `exp_keys`.
        UserWarning: If keys are not in `exp_keys` or `opt_keys`.
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


def parse(file_path: str) -> Tuple[dict, list[TestVector]]:
    """Parses a test script written in YAML format.

    Args:
        file_path (str): Path to the file to parse.

    Returns:
        chip_info (dict): Chip Info section of test script.
        test_vecs (list[TestVector]): List of parsed tests.
    
    Raises:
        ParseError: If file fails to meet defined test script format.
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

            parse_global_params(data["Global Parameters"])

            vcc_pin = data["Global Parameters"]["VCC Pin"]
            gnd_pin = data["Global Parameters"]["GND Pin"]
            if pin_map is not None: parse_pin_map(pin_map, vcc_pin, gnd_pin)

            tt = parse_truth_table(truth_table) if truth_table is not None else None

            test_vecs = parse_tests(data["Tests"], data["Global Parameters"], pin_map, tt)
        except Exception as e:
            raise ParseError(f"Failed to parse {file_path}") from e

        return chip_info, test_vecs

def parse_global_params(global_param: dict) -> None:
    """Parses Global Parameters section of the test script.

    Args:
        global_params (dict): Global Parameters section of the test script.

    Raises:
        ValueError: If the VCC Pin and GND Pin are the same pin.
        ValueError: If the length of thresholds and VCC voltages are differet.
        ValueError: If the threshold is less than 0.
        ValueError: If Output Low is greater than or equal to Output High.
        ValueError: If Input Low is greater than or equal to Input High.
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
    return

def parse_pin_map(pin_map: dict, vcc_pin: int, gnd_pin: int) -> None:
    """Parses Pin Map section of the test script.

    Args:
        pin_map (dict): Pin Map section of test script.
        vcc_pin (int): VCC Pin from Global Parameters section of the test script.
        gnd_pin (int): GND Pin from Global Parameters section of the test script.

    Raises:
        ValueError: If a pin maps to the same pin as `vcc_pin`.
        ValueError: If a pin maps to the same pin as `gnd_pin`.
        ValueError: If multiples pins map to the same pin.
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
    """Parses truth table section of the test script.

    Args:
        truth_table (dict): Truth Table section of the test script.

    Returns:
        tt (dict): conversion of `truth_table` to dict[list].

    Raises:
        TableParseError: If the number of columns per row is inconsistent.
        TableParseError: If the names of columns per row is inconsistent.
        ValueError: If the logic inside `truth_table` is in `TRUTH_TABLE_LOGIC`.
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

def parse_tests(tests: dict, global_param: dict, pin_map: dict, truth_table: dict) -> list[TestVector]:
    """Parses Tests section of the test script.

    Args:
        tests (dict): Tests section of the test script.
        global_params (dict): Global Parameters of the test script.
        pin_map (dict): Pin Map section of the test script.
        truth_table (dict): Parsed Truth Table section of the test script.

    Returns:
        test_vecs (list[TestVector]): List of `TestVector` objects based on parsed I/O and test metadata.
    """
    exp_keys = {"Inputs", "Outputs"}
    test_vecs = [None for _ in range(len(tests))]
    for i, (test_name, test) in enumerate(tests.items()):
        check_keys(exp_keys, None, test.keys(), f"Tests[{test_name}]")

        input_cmd = parse_test_IO(test["Inputs"], pin_map, truth_table, INPUT_LOGIC, test_name)
        output_cmds = parse_test_IO(test["Outputs"], pin_map, truth_table, OUTPUT_LOGIC, test_name)

        test_vecs[i] = TestVector(global_param, pin_map, input_cmd, output_cmds, test_name)
    return test_vecs

def parse_test_IO(io: dict, pin_map: dict, truth_table: dict, valid_logic: set[str], test_name: str) -> list[IOCommand]:
    """Parses Inputs and Outputs of a Test in Tests section.

    Args:
        io (dict): Inputs/Outputs section of Test being parsed.
        pin_map (dict): Pin Map section of the test script.
        truth_table (dict): Parsed Truth Table section of the test script.
        valid_logic (set(str)): Valid set of logic for I/O.
        test_name (str): Name of test being parsed.

    Returns:
        vec (list[IOCommand]): List of `IOCommand` dataclasses based on the Inputs/Outputs of the test.

    Raises:
        ValueError: If pin name is not found in Pin Map.
        ValueError: If integer value exceeds maximum number based on number of provided pins.
        ValueError: If pin value is not in `valid_logic`.
        TestParseError: If multiple integers are used `LogicMapping.Map` commands.
        TestParseError: If it is not possible to map pins to a value from the I/O command.
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
                # Ex: 1
                pin = pin_name
                store = pin
            elif pin_name.isdigit(): 
                # Ex: '1' or 1,2
                pin = int(pin_name)
                store = pin
            elif pin_map is not None and pin_name in pin_map:
                # Ex: A where A: 1 in Pin Map
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
            # Ex: [H, L, H]
            cmd_type = LogicMapping.Serial
            pin_vals = io[pins]
            voltage = None
        elif isinstance(io[pins], (str, int)):
            if not isinstance(io[pins], str): io[pins] = str(io[pins])
            # Ex: H [voltage], or 1 [voltage]
            cmd = io[pins].strip().split(" ")
            pin_vals = [p.strip() for p in cmd[0].split(",")]
            voltage = float(cmd.strip()) if len(cmd) >= 2 else None
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
            elif truth_table is not None and pin_val in truth_table:
                # replace reference with value from truth table
                parsed_pin_vals.extend(truth_table[pin_val])
                cmd_type = LogicMapping.TruthTable

            else:
                # no truth table, using logic set
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
        
        vec[i] = IOCommand(pin_names, parsed_pin_vals, voltage, cmd_type)

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
