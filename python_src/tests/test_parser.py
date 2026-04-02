import pathlib # for cross-platform file paths
import pytest

from contextlib import nullcontext as does_not_raise # no exception raised

from ICTestFixture.fileIO import parser

def assert_msg(exc, *exp_parts):
    """Checks if error message contains important parts"""
    if hasattr(exc, "value"):  # normal exception
        msg = str(exc.value)
    elif hasattr(exc, "__iter__"):  # WarningsChecker or list of warnings
        # take all warnings messages
        msg = " ".join(str(w.message) for w in exc)
    else:
        raise TypeError(f"Unknown exc type: {type(exc)}")

    for part in exp_parts:
        if isinstance(part, (list, tuple, set)):
            for item in part:
                assert str(item) in msg
        else:
            assert str(part) in msg

@pytest.fixture
def base_check_type():
    return {
        "exp_keys": {"VCC Pin", "VCC Voltage"},
        "got_keys": {"VCC Pin", "VCC Voltage"},
        "section": "section"
    }

@pytest.fixture
def base_pin_map():
    return {
        "A": 2,
        "B": 9,
        "Y": 1
    }

@pytest.fixture
def base_truth_table():
    return [
        {"A": "L", "B": "L", "Y": "L"},
        {"A": "L", "B": "H", "Y": "L"},
        {"A": "H", "B": "L", "Y": "L"},
        {"A": "H", "B": "H", "Y": "H"}
    ]

@pytest.fixture
def base_global_params():
    return {
        "VCC Pin": 16,
        "GND Pin": 8,
        "VCC Voltage": 5,
        "Output Low": 0.2,
        "Output High": 3.81
    }

@pytest.fixture
def base_input_single():
    return {
        # without voltage
        1: "H",       # single int pin
        "A": "L",     # single pin ref
        "1,2,3": "H", # multiple int pins
        "A,B": "H",   # multiple pin refs
        # with voltage
        3: "H 5",
        "Y": "L 3.3",
        "1,2": "H 1.8",
        "Y,B": "L 2.5"
    }

@pytest.fixture
def base_output_single():
    return {
        # without voltage
        1: "L",
        "A": "T",
        "1,2,3": "Z",
        "A,B": "H",
        # with voltage
        2: "H 5",
        "Y": "X 1.8",
        "4,5": "L 2.5",
        "Y,B": "S 3.3"
    }

@pytest.fixture
def base_input_map():
    return {
        # without voltage
        "1,2": 0b11,   # int pins and binary value
        "3,4,5": "H,L,H", # int pins and logic value
        "A,B": "L,H",     # pin refs and logic value
        "B,A": 0b01,    # pin refs and binary value
        # with voltage
        "6,7,8": "0b101 2.5",
        "9,10,11": "H,L,H 4.5",
        "Y,B": "L,H 5",
        "A,Y": "0b01 3.3"
    }

@pytest.fixture
def base_output_map():
    return {
        # without voltage
        "15,20": 0b11,
        "5,8": "H,X",
        "Y,B": "Z,L",
        "A,19": 0b01,
        # with voltage
        "A,19": "0b10 5",
        "2,B": "H,X 3.3",
        "A,B": "H,H 2.5",
        "Y,A": "L,T 1.8"
    }

@pytest.fixture
def base_input_truthtable():
    return {
        1: "A",   # int pin
        "B": "B"  # pin ref
    }

@pytest.fixture
def base_output_truthtable():
    return {
        1: "Y",
        "Y": "Y"
    }

@pytest.fixture
def base_input_serial():
    return {
        1: ["H", "L", "H"],
        "2,3": ["L", "H"],
        "A": ["H", "H"],
        "B, A": ["L", "L"]
    }

@pytest.fixture
def base_output_serial():
    return {
        4: ["H", "L", "H"],
        "5,6": ["L", "H"],
        "B": ["H", "H"],
        "Y, A": ["L", "L"]
    }

class TestParserHelpers:
    """Test helper functions used by parser.py."""
    @pytest.mark.parametrize(
        "val, exp_types, expectation", [ 
            (2.3, (float,), does_not_raise()),          # one type specified
            ("A", (str, int), does_not_raise()),        # multiple types specified
            ("B", (int,), pytest.raises(TypeError)),    # one type specified, error
            (2.3, (str, int), pytest.raises(TypeError)) # multiple types specified, error
        ]
    )
    def test_parser_check_type(self, val, exp_types, expectation):
        with expectation as exc:
            parser.check_type(val, exp_types, "section", "key")
        
        if exc is not None:
            # convert exp_types to string repr
            types_str = [exp_type.__name__ for exp_type in exp_types]
            # msg include section of error, expected type(s), and got type
            assert_msg(exc, "Expected type", "section", types_str, type(val).__name__)

    @pytest.mark.parametrize(
        "pin, expectation", [
            (parser.MAX_PINS-1, does_not_raise()),          # pin in range
            (1, does_not_raise()),                          # minimum pin value
            (parser.MAX_PINS, does_not_raise()),            # maximum pin value
            (0, pytest.raises(ValueError)),                 # < 1
            (parser.MAX_PINS+1, pytest.raises(ValueError))  # > MAXPINS
        ]
    )
    def test_parser_check_pin(self, pin, expectation):
        with expectation as exc:
            parser.check_pin(pin, "section", "key")

        if exc is not None:
            range_str = f"Pin number must be between 1 and {parser.MAX_PINS}"
            # msg includes rangeStr, section of error, and pin
            assert_msg(exc, range_str, "section[key]", pin)

    # all supported voltage references
    @pytest.mark.parametrize(
        "voltage, expectation", [
            (5.0, does_not_raise()),
            (2.3, pytest.raises(ValueError)) 
        ]
    )
    def test_parser_check_voltage(self, voltage, expectation):
        with expectation as exc:
            parser.check_voltage(voltage, "section", "key")

        if exc is not None:
            assert_msg(exc, "Voltage must be one of supported voltages", parser.SUPPORTED_VOLTAGES, voltage)

    @pytest.mark.parametrize(
        "opt_keys, add_key", [
            (None, None),               # explicit no opt keys 
            ({"CLK Freq"}, None),       # opt keys, but none used
            ({"CLK Freq"}, "CLK Freq")  # opt keys used
        ]
    )
    def test_valid_key_combos(self, base_check_type, opt_keys, add_key):
        base_check_type["opt_keys"] = opt_keys
        if add_key is not None:
            base_check_type["got_keys"].add(add_key)
        parser.check_keys(**base_check_type)

    @pytest.mark.parametrize(
        "pop_keys", [
            ("VCC Pin",),               # one key missing
            ("VCC Pin", "VCC Voltage")  # multiple keys missing
        ]
    )
    def test_missing_keys(self, base_check_type, pop_keys):
        base_check_type["got_keys"].difference_update(pop_keys) # removes keys from an iterable
        with pytest.raises(parser.MissingKeys) as exc:
            parser.check_keys(opt_keys=None, **base_check_type)
        # msg includes missing key(s) and section of error
        assert_msg(exc, "Missing required keys", pop_keys, base_check_type["section"])

    @pytest.mark.parametrize(
        "add_keys", [
            ("GND Pin",),               # one unknown key
            ("GND Pin", "GND Voltage")  # multiple unknown keys
        ]
    )
    def test_user_warning(self, base_check_type, add_keys):
        base_check_type["got_keys"].update(add_keys)
        with pytest.warns(UserWarning) as exc:
            parser.check_keys(opt_keys=None, **base_check_type)
        # msg includes unexpected key (GND Pin) and section of error
        assert_msg(exc, "Ignoring unexpected keys", add_keys, base_check_type["section"])

class TestParserPinMap:
    """Tests parse_pin_map function."""
    # private test fixtire for class
    @pytest.fixture(autouse=True)
    def pin_map_test_fixture(self, base_pin_map):
        self.pin_map_test_fixture = {
            "pin_map": base_pin_map,
            "vcc_pin": 16,
            "gnd_pin": 8
        }

    def test_valid_pin_map(self):
        parser.parse_pin_map(**self.pin_map_test_fixture)

    @pytest.mark.parametrize(
        "pin_ref, pin_val", [
            (2, 5),     # non-str pin id
            ("A", 2.4)  # non-int pin value
        ]
    )
    def test_invalid_pin_entry(self, pin_ref, pin_val):
        self.pin_map_test_fixture["pin_map"][pin_ref] = pin_val
        with pytest.raises(TypeError):
            parser.parse_pin_map(**self.pin_map_test_fixture)

    @pytest.mark.parametrize(
        "pin_val", [
            -1,                   # < 1 (minimum)
            parser.MAX_PINS + 1   # > MAXPINS
        ]
    )
    def test_pin_out_of_range(self, pin_val):
        self.pin_map_test_fixture["pin_map"]["A"] = pin_val
        with pytest.raises(ValueError):
            parser.parse_pin_map(**self.pin_map_test_fixture)

    @pytest.mark.parametrize(
        "pin_ref, err_msg", [
            ("gnd_pin", "Pin number must not be same as GND Pin"),    # pin is same as GND
            ("vcc_pin", "Pin number must not be same as VCC Pin"),    # pin is same as VCC
        ]
    )
    def test_power_pin_conflicts(self, pin_ref, err_msg):
        self.pin_map_test_fixture["pin_map"]["B"] = self.pin_map_test_fixture[pin_ref]
        with pytest.raises(ValueError) as exc:
            parser.parse_pin_map(**self.pin_map_test_fixture)
        # msg includes conflict type, conflicting pin, section of error
        assert_msg(exc, err_msg, self.pin_map_test_fixture["pin_map"]["B"], "Pin Map[B]")

    def test_same_pin_conflict(self):
        self.pin_map_test_fixture["pin_map"]["B"] = self.pin_map_test_fixture["pin_map"]["A"]
        with pytest.raises(ValueError) as exc:
            parser.parse_pin_map(**self.pin_map_test_fixture)
        # msg includes conflict type, conflicting pin
        assert_msg(exc, "Multiple names map to same pin", self.pin_map_test_fixture["pin_map"]["A"])

class TestParserTruthTable:
    """Tests parse_truth_table function."""
    def test_valid_truth_table(self, base_truth_table):
        tt = parser.parse_truth_table(base_truth_table)
        
        assert isinstance(tt, dict)
        assert len(tt) == 3
        assert tt["A"] == ["L", "L", "H", "H"]
        assert tt["B"] == ["L", "H", "L", "H"]
        assert tt["Y"] == ["L", "L", "L", "H"]

    def test_all_logic(self, base_truth_table):
        for logic in parser.TRUTH_TABLE_LOGIC:
            base_truth_table[0]["A"] = logic

            tt = parser.parse_truth_table(base_truth_table)
            assert len(tt) == 3
            assert tt["A"] == [logic ,"L", "H", "H"]
            assert tt["B"] == ["L", "H", "L", "H"]
            assert tt["Y"] == ["L", "L", "L", "H"]

    def test_non_str_col_name(self, base_truth_table):
        base_truth_table[0][5] = "L"
        with pytest.raises(TypeError):
            parser.parse_truth_table(base_truth_table)

    def test_inconsistent_num_cols(self, base_truth_table):
        base_truth_table[0]["C"] = "L"
        with pytest.raises(parser.TableParseError) as exc:
            parser.parse_truth_table(base_truth_table)
        # msg includes secion of error
        assert_msg(exc, "Inconsistent number of columns", "Truth Table")

    def test_inconsistent_col_names(self, base_truth_table):
        for i in range(len(base_truth_table)):
            if i == 0: base_truth_table[i]["C"] = "H"
            else: base_truth_table[i]["D"] = "L"
        with pytest.raises(parser.TableParseError) as exc:
            parser.parse_truth_table(base_truth_table)
        # msg includes section of error
        assert_msg(exc, "Inconsistent column names", "Truth Table")

    def test_invalid_logic(self, base_truth_table):
        base_truth_table[0]["A"] = "C"
        with pytest.raises(ValueError) as exc:
            parser.parse_truth_table(base_truth_table)
        # msg includes invalid logic (C), column name (A), expected logic, section of error
        assert_msg(exc, "Invalid logic", "C", "A", parser.TRUTH_TABLE_LOGIC, "Truth Table")

class TestParserGlobalParams:
    """Test parse_global_params function."""
    def test_valid_global_params(self, base_global_params):
        parser.parse_global_params(base_global_params)

    def test_valid_global_params_with_list(self, base_global_params):
        base_global_params["VCC Voltage"] = [5, 2.5]
        base_global_params["Output Low"] = [0.33, 0.2]
        base_global_params["Output High"] = [3.84, 4.5]
        parser.parse_global_params(base_global_params)

    def test_valid_global_params_with_opt_keys(self, base_global_params):
        base_global_params["Input Low"] = 0.2
        base_global_params["Input High"] = 4
        parser.parse_global_params(base_global_params)

    def test_valid_global_params_with_one_threshold(self, base_global_params):
        base_global_params["Input High"] = 3
        parser.parse_global_params(base_global_params)

    def test_missing_keys_global_params(self, base_global_params):
        base_global_params.pop("VCC Pin")
        with pytest.raises(parser.MissingKeys):
            parser.parse_global_params(base_global_params)

    @pytest.mark.parametrize(
        "param, val", [
            ("VCC Pin", 16.0),      # non int VCC Pin
            ("GND Pin", "8"),       # non int GND Pin
            ("Output Low", "0.3"),  # non int/float threshold
        ]
    )
    def test_invalid_types_for_params(self, base_global_params, param, val):
        base_global_params[param] = val
        with pytest.raises(TypeError):
            parser.parse_global_params(base_global_params)

    @pytest.mark.parametrize(
        "key, val", [
            ("VCC Pin", 0),                     # VCC Pin < 1 (min)
            ("GND Pin", -2),                    # GND Pin < 1 (min)
            ("VCC Pin", parser.MAX_PINS + 1),   # VCC Pin > MAXPINS
            ("GND Pin", parser.MAX_PINS + 2)    # GND Pin > MAXPINS
        ]
    )
    def test_power_pins_out_of_range(self, base_global_params, key, val):
        base_global_params[key] = val
        with pytest.raises(ValueError):
            parser.parse_global_params(base_global_params)

    def test_vcc_pin_equal_gnd_pin(self, base_global_params):
        base_global_params["VCC Pin"] = base_global_params["GND Pin"]
        with pytest.raises(ValueError) as exc:
            parser.parse_global_params(base_global_params)
        # msg includes VCC/GND conflict pin
        assert_msg(exc, "VCC Pin and GND Pin are the same", base_global_params["VCC Pin"])

    def test_unsupported_vcc_voltage(self, base_global_params):
        base_global_params["VCC Voltage"] = 2.2
        with pytest.raises(ValueError):
            parser.parse_global_params(base_global_params)

    def test_inconsistent_num_voltage_and_thresholds(self, base_global_params):
        base_global_params["VCC Voltage"] = [5, 3.3]
        with pytest.raises(ValueError) as exc:
            parser.parse_global_params(base_global_params)
        # msg includes the got lengths of VCC Voltage and thresholds, and section of error
        assert_msg(exc, "Inconsistent number of values for VCC Voltage and voltage thresholds", {1, 2}, "Global Parameters")

    @pytest.mark.parametrize(
        "param1, val1, param2, val2", [
            ("Output Low", 3.4, "Output High", 3.3),                    # output low >= high
            ("Input Low", 4.5, "Input High", 4.5)                      # input low >= high
        ]
    )
    def test_low_greater_than_high_threshold(self, base_global_params, param1, val1, param2, val2):
        base_global_params[param1] = val1
        base_global_params[param2] = val2
        io = param1.split(" ")[0]
        with pytest.raises(ValueError) as exc:
            parser.parse_global_params(base_global_params)
        # msg includes io type (Input/Output), and values
        assert_msg(exc, f"Voltage {io} Low is greater than or equal to Voltage {io} High", val1, val2)

    def test_low_greater_than_high_threshold_list(self, base_global_params):
        base_global_params["VCC Voltage"] = [5, 3.3] # need to set VCC Voltage to have same length as thresholds
        base_global_params["Output Low"] = [0.3, 5.6]
        base_global_params["Output High"] = [1.9, 4.5]
        with pytest.raises(ValueError) as exc:
            parser.parse_global_params(base_global_params)
        # msg includes io type (Output), and values
        assert_msg(exc, f"Voltage Output Low is greater than or equal to Voltage Output High", 5.6, 4.5)

class TestParserTests:
    """Tests parse_tests function."""
    @pytest.fixture(autouse=True)
    def tests_test_fixture(self, base_global_params, base_pin_map, base_truth_table):
        self.tests_test_fixture = {
            "global_params": base_global_params,
            "pin_map": base_pin_map,
            "truth_table": parser.parse_truth_table(base_truth_table)
        }

    @pytest.mark.parametrize(
        "input_fixture, output_fixture, test_name", [
            ("base_input_single", "base_output_single", "Single"),
            ("base_input_map", "base_output_map", "Map"),
            ("base_input_truthtable", "base_output_truthtable", "Truth Table"),
            ("base_input_serial", "base_output_serial", "Serial")
        ]
    )
    def test_valid_tests(self, request, input_fixture, output_fixture, test_name):
        test_input = request.getfixturevalue(input_fixture)
        test_output = request.getfixturevalue(output_fixture)
        test = {test_name: {"Inputs": test_input, "Outputs": test_output}}
        test_vec = parser.parse_tests(test, **self.tests_test_fixture)
        
        assert len(test_vec) == 1
        assert len(test_vec[0].inputs) == len(test_input)
        assert len(test_vec[0].outputs) == len(test_output)
        assert test_vec[0].global_params == self.tests_test_fixture["global_params"]
        assert test_vec[0].pin_map == self.tests_test_fixture["pin_map"]
        assert test_vec[0].test_name == test_name

    def test_missing_keys_tests(self):
        with pytest.raises(parser.MissingKeys):
            parser.parse_tests(tests={"MissingKey Test": {"Inputs": {1: "H"}}}, **self.tests_test_fixture)

class TestParserIO:
    """Tests parse_test_IO function."""
    # private test fixture for class
    @pytest.fixture(autouse=True)
    def io_test_fixture(self, base_pin_map, base_truth_table):
        self.io_test_fixture = {
            "pin_map": base_pin_map,
            "truth_table": parser.parse_truth_table(base_truth_table),
            "valid_logic": parser.INPUT_LOGIC,
            "test_name": "test_io"
        }

    @pytest.mark.parametrize(
        "fixture_name", [
            "base_input_single",
            "base_input_map",
            "base_input_truthtable",
            "base_input_serial",
            "base_output_single",
            "base_output_map",
            "base_output_truthtable",
            "base_output_serial"
        ]
    )
    def test_valid_io(self, request, fixture_name):
        # request is from PyTest library, get test fixtures by name
        io = request.getfixturevalue(fixture_name)
        # change valid_logic to OUTPUT_LOGIC from the default INPUT_LOGIC
        self.io_test_fixture["valid_logic"] = parser.INPUT_LOGIC if "input" in fixture_name else parser.OUTPUT_LOGIC
        
        io_cmds = parser.parse_test_IO(io=io, **self.io_test_fixture)
        assert len(io_cmds) == len(io)

        # verify commands are written correctly by looping each entry separetly
        for pins, pin_vals in io.items():
            # call before modifying pins and pin_vals
            ret = parser.parse_test_IO(io={pins: pin_vals}, **self.io_test_fixture)

            if isinstance(pin_vals, list):
                pin_vals = ",".join(pin_vals)
            tokens = pin_vals.split(" ")
            # make int if a digit, otherwise get from pin map
            exp_pins = [
                int(pin) if pin.isdigit() else pin.strip()
                for pin in str(pins).split(",")
            ]
            # convert ints, otherwise remain as str
            exp_vals = [
                int(val, 0) if val.startswith("0b") or val.isdigit() else val.strip()
                for val in str(tokens[0]).split(",")
            ]
            exp_volt = float(tokens[-1]) if len(tokens) > 1 else None
            exp_cmd = None

            logic_map_type = fixture_name.split("_")[-1]
            if logic_map_type == "single":
                exp_cmd = parser.LogicMapping.Single
            elif logic_map_type == "map":
                exp_cmd = parser.LogicMapping.Map
            elif logic_map_type == "truthtable":
                exp_cmd = parser.LogicMapping.TruthTable
            elif logic_map_type == "serial":
                exp_cmd = parser.LogicMapping.Serial
            else:
                raise NotImplementedError(
                    f"No such logic mapping implemented: {logic_map_type}"
                )
            
            # replace reference with value from truth table
            if exp_cmd == parser.LogicMapping.TruthTable:
                exp_vals = self.io_test_fixture["truth_table"][exp_vals[0]] # take out list wrapper for exp_vals

            assert len(ret) == 1
            assert ret[0].pins == exp_pins
            assert ret[0].pin_vals == exp_vals
            assert ret[0].volt_type == exp_volt
            assert ret[0].cmd_type == exp_cmd

    def test_all_valid_logic(self):
        for logic in parser.INPUT_LOGIC:
            parser.parse_test_IO({1: logic}, None, None, parser.INPUT_LOGIC, f"Input: {logic}")

        for logic in parser.OUTPUT_LOGIC:
            parser.parse_test_IO({1: logic}, None, None, parser.OUTPUT_LOGIC, f"Output: {logic}")
    
    def test_invalid_logic(self):
        with pytest.raises(ValueError) as exc1:
            parser.parse_test_IO({1: "LOW"}, None, None, parser.INPUT_LOGIC, "Test LOW")
        # msg includes pin, value, expected logic, and section of error
        assert_msg(exc1, "Invalid logic/reference", 1, "LOW", parser.INPUT_LOGIC, "\"Tests[Test LOW]\"")

        with pytest.raises(ValueError) as exc2:
            parser.parse_test_IO({1: "HIGH"}, None, None, parser.OUTPUT_LOGIC, "Test HIGH")
        # msg includes pin, value, expected logic, and section of error
        assert_msg(exc2, "Invalid logic/reference", 1, "HIGH", parser.OUTPUT_LOGIC, "\"Tests[Test HIGH]\"")
        
    @pytest.mark.parametrize(
        "io,", [
            {2.6: "L 3.3"},    # pin not int or str
            {1: 2.74}           # pin val not int or str
        ]
    )
    def test_invalid_types_tests(self, io):
        with pytest.raises(TypeError):
            parser.parse_test_IO(io=io, **self.io_test_fixture)

    @pytest.mark.parametrize(
        "io", [
            {0: "L"},                 # pin < 1
            {parser.MAX_PINS+1: 0b1}, # pin > MAXPINS
            {"C": "H, 5"},           # pin_ref < 1
            {"D": "0b11, 3.3"}       # pin_ref > MAXPINS
        ]
    )
    def test_pin_out_of_range(self, io):
        self.io_test_fixture["pin_map"]["C"] = -3
        self.io_test_fixture["pin_map"]["D"] = parser.MAX_PINS+1
        with pytest.raises(ValueError):
            parser.parse_test_IO(io=io, **self.io_test_fixture)

    def test_multiple_int_values(self):
        with pytest.raises(parser.TestParseError) as exc:
            parser.parse_test_IO(io={1: "0b1,0b0"}, **self.io_test_fixture)
        # msg includes pin_vals, and section of error
        assert_msg(exc, "Only 1 integer input allowed for input mapping", "0b1", "0b0", self.io_test_fixture["test_name"])

    def test_pin_value_greater_than_max(self):
        with pytest.raises(ValueError) as exc:
            parser.parse_test_IO(io={"1,2,3": 0b1011}, **self.io_test_fixture)
        # msg includes length of pins, maxixmum possible value, pins, and section of error
        assert_msg(exc, 3, 7, 0b1011, self.io_test_fixture["test_name"])

    def test_logic_mapping_combinations(self, base_input_single, base_input_truthtable):
        input_io = base_input_single | base_input_truthtable
        with pytest.raises(parser.TestParseError) as exc:
            parser.parse_test_IO(io=input_io, **self.io_test_fixture)
        # msg includes section of error
        assert_msg(exc, "Cannot mix truth table mapping with any other pin mapping", self.io_test_fixture["test_name"])

class TestParserParse:
    """Tests parse function."""
    @pytest.fixture
    def exp_global_params(self):
        return {
            "VCC Pin": 14,
            "GND Pin": 7,
            "VCC Voltage": [5],
            "Output Low": [0.33],
            "Output High": [3.84]
        }

    @pytest.fixture
    def exp_pin_map(self):
        return {
            "A1": 1,
            "A2": 4,
            "A3": 9,
            "A4": 12,
            "B1": 2,
            "B2": 5,
            "B3": 10,
            "B4": 13,
            "Y1": 3,
            "Y2": 6,
            "Y3": 8,
            "Y4": 11
        }
    
    @pytest.fixture
    def exp_chip_info(self):
        return {
            "Name": "74HCT00",
            "Manufacturer": "Texas Instruments",
            "Logic": "NAND"
        }

    @pytest.mark.parametrize(
        "file_name, has_chip_info, has_pin_map",[
            ("nand_bare.yaml", False, False),
            ("nand_pm.yaml", False, True), 
            ("nand_full.yaml", True, True)
        ]
    )
    def testValidParse(self, file_name, has_chip_info, has_pin_map, exp_chip_info, exp_pin_map, exp_global_params):
        file_path = pathlib.Path.cwd() / "tests" / "unittest_yaml" / file_name # / will create file path based on os
        chip_info, test_vecs = parser.parse(file_path)

        assert len(test_vecs) == 4
        if has_chip_info: assert chip_info == exp_chip_info
        
        for test_vec in test_vecs:
            assert test_vec.global_params == exp_global_params
            if has_pin_map:
                assert test_vec.pin_map == exp_pin_map
            else:
                assert test_vec.pin_map is None

    @pytest.mark.parametrize(
        "file_name, exc_cause", [
            ("MissingKeys.yaml", parser.MissingKeys),
            ("MissingKeys_gp.yaml", parser.MissingKeys),
            ("MissingKeys_tests.yaml", parser.MissingKeys),
            ("bad_tt1.yaml", parser.TableParseError),
            ("bad_tt2.yaml", parser.TableParseError),
            ("bad_tests1.yaml", parser.TestParseError),
            ("bad_tests2.yaml", parser.TestParseError),
            ("bad_tests3.yaml", parser.TestParseError),
            ("TypeError_pm1.yaml", TypeError),
            ("TypeError_pm2.yaml", TypeError),
            ("TypeError_gp1.yaml", TypeError),
            ("TypeError_gp2.yaml", TypeError),
            ("TypeError_gp3.yaml", TypeError),
            ("TypeError_tests1.yaml", TypeError),
            ("TypeError_tests2.yaml", TypeError),
            ("ValueError_pm1.yaml", ValueError),
            ("ValueError_pm2.yaml", ValueError),
            ("ValueError_tt.yaml", ValueError),
            ("ValueError_gp1.yaml", ValueError),
            ("ValueError_gp2.yaml", ValueError),
            ("ValueError_gp3.yaml", ValueError),
            ("ValueError_gp4.yaml", ValueError),
            ("ValueError_tests1.yaml", ValueError),
            ("ValueError_tests2.yaml", ValueError)
        ]    
    )
    def test_parse_error(self, file_name, exc_cause):
        file_path = pathlib.Path.cwd() / "tests" / "unittest_yaml" / file_name
        with pytest.raises(parser.ParseError) as exc:
            parser.parse(file_path)
        # msg includes file_path
        assert_msg(exc, file_path)
        assert isinstance(exc.value.__cause__, exc_cause)
