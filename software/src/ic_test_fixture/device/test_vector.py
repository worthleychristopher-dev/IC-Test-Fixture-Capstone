import random # used for dummy test

from enum import auto, Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
from collections import defaultdict
# allows for accessing tuple elements by variable name
class LogicMapping(Enum):
    """Enumeration for type of IOCommands

    Attributes:
        Map: Multiple Pins map to sequence logic.
        Serial: Pin has a list of logic.
        Single: Only one logic.

    Examples:
        Map Examples:
            1,2,A: H,L,H
            1,2,A: 0b101
        
        Serial Examples:
            1: [H,L,H]
            1: A
            A: A

        Single Examples:
            1: H
            1,2,A: H
    """
    Map = auto()
    Serial = auto()
    Single = auto()

@dataclass
class IOCommand:
    """Command Information of pins, respective logic, and voltage to drive with.

    Attributes:
        pins (list[int, str]): List of pins.
        pin_vals (list[int, str]): List of logic values.
        volt_type (float): Voltage to drive logic HIGH.
        cmd_type: Type of Command based on `pins` and `pin_vals`.
    """
    pins: List[Union[int, str]]
    pin_vals: List[Union[int, str]]
    volt_type: float
    cmd_type: LogicMapping

@dataclass
class PinResult:
    """Stores ADC reading and associated logic value.

    Attributes:
        adc (float): Voltage measured from ADC in Volts.
        logic (int, str): Logic Value based on High and Low Thresholds.
    """
    adc: float
    logic: Union[int, str]

@dataclass
class Condition:
    """The associated VCC voltage, and high and low thresholds for a test
    
    Attributes:
        vcc (float): Voltage to supply to the IC.
        out_low (float): Threshold for a logic LOW.
        out_high (float): Threshold for a logic HIGH.
    """
    vcc: float
    out_low: float
    out_high: float

class TestVector:
    """Encapsulation of pin I/O commands for testing.

    Contains all the necessary metadata to execute the test at different conditions
    and store the results. Results are exported by calling `export_as_table()`. The
    function `simulated_tests()` simulates the hardware test fixture responses for
    debugging purposes.

    Attributes:
        global_params (dict): Parameters that are for all test regardless of conditions.
        pin_map (dict): Maps pin name to an integer representation of the pin.
        inputs (list[IOCommands]): List of input commands to drive the ICTestFixture
        outputs (list[IOCommands]): List of output commands containing expected results.
        test_name (str): Name of the Test.
        passed (bool): State of whether test has passed or not.
        results (defaultdict): Nested dictionary with 3 layers.

            Structure:
                results[vcc][step_num][pin] returns PinResult

            `vcc` is the vcc condition of the test, `step_num` is from serial, and
            `pin`, as an integer representation is the pin that was measured.
    """
    def __init__(
        self,
        global_params: dict,
        pin_map:dict,
        inputs: list[IOCommand],
        outputs: list[IOCommand],
        test_name: str
    ) -> None:
        """Initializes a TestVector instance.
        
        Args:
            global_params (dict): Parameters that are for all test regardless of conditions.
            pin_map (dict): Maps pin name to an integer representation of the pin.
            inputs (list[IOCommands]): List of input commands to drive the ICTestFixture
            outputs (list[IOCommands]): List of output commands containing expected results.
            test_name (str): Name of the Test.
        """
        self.global_params = global_params
        self.pin_map = pin_map
        self.inputs = inputs
        self.outputs = outputs
        self.results = defaultdict(lambda: defaultdict(dict)) # 3 layer dictionary
        self.test_name = test_name
        self.passed = None # prevents use of export_as_table if test not executed
        # prevents errors when executing unit tests on TestVector without inputs and outputs
        if self.inputs is not None and self.outputs is not None:
            self._pad_inputs()

    def export_as_table(self) -> Tuple[list, dict]:
        """Exports all of the data and results into a tabular format.

        Constructs a table using `self.inputs`, `self.outputs`, and
        `self.results`. This includes constructing the header rows,
        and displaying all data from `PinResult` dataclasses.

        Returns:
            table (list): Data of I/O and results in a tabular format.
            metadata (dict): Information about properties of the table.
        """
        def to_bin_str(val, width) -> str:
            """Returns string representation of val depending on type."""
            if isinstance(val, int):
                # convert int to binary string with leading 0b, +2 for padding
                return format(val, f"#0{width+2}b")
            elif isinstance(val, (list, tuple)):
                # formats: [H, L, H] -> H, L, H
                return ", ".join(val)
            else:
                # catch all for anything else
                return str(val)
            
        if self.passed is None:
            # did not execute test, so self.results is empty
            return
        
        # empty strings are used for spanning
        num_vcc = len(self.global_params["VCC Voltage"])
        include_vcc = num_vcc > 1
        total_out_pins = sum(len(out.pins) for out in self.outputs)
        # build header
        # VCC Voltage is always default High/1 value if not specified
        header = (
            ["Inputs"] + ([""] * (len(self.inputs) - 1)) +
            (["VCC"] if include_vcc else []) +
            ["Outputs/Results"] + [""] * (2*total_out_pins - 1)
        )
        # build columns
        # unwraps output pin list into its own column
        pin_cols = (
            [", ".join(str(pin) for pin in inp.pins) for inp in self.inputs] +
            ([""] if include_vcc else []) +
            [col for out in self.outputs for pin in out.pins for col in (pin, "")] # empty string after each output pin
        )

        data = [] # main table
        is_serial = True if self.inputs[0].cmd_type == LogicMapping.Serial else False 
        num_rows = len(self.inputs[0].pin_vals) if is_serial else 1

        # create rows for data
        for i in range(num_rows):
            # compute input data entries
            input_data = []
            for inp in self.inputs:
                inp_str = to_bin_str(inp.pin_vals[i], len(inp.pins))
                inp_str += f" ({inp.volt_type})" if inp.volt_type else "" # only include voltage if specified
                input_data.append(inp_str)

            # compute output data entries
            output_data = []
            for out in self.outputs:
                for pin_idx in range(len(out.pins)):
                    # get val_idx of the pin_val
                    if out.cmd_type == LogicMapping.Single:
                        val_idx = 0
                    elif out.cmd_type == LogicMapping.Map:
                        val_idx = 0 if isinstance(out.pin_vals[0], int) else pin_idx
                    elif out.cmd_type == LogicMapping.Serial:
                        val_idx = i

                    # extract out_val at val_idx of pin_val
                    if isinstance(out.pin_vals[val_idx], int):
                        out_val = (out.pin_vals[0] >> (len(out.pins) - pin_idx - 1)) & 1
                    else:
                        out_val = out.pin_vals[val_idx]
                    # sequentially add to output_data
                    # 1,2,3: H,L,H -> [H,L,H] in output_data
                    output_data.append(out_val)

            for vcc_idx, vcc in enumerate(self.global_params["VCC Voltage"]):
                row = []
                # Inputs and VCC
                if include_vcc:
                    # print input data if first vcc row, else print empty strings, vcc column at end
                    row.extend((input_data if vcc_idx == 0 else [""] * len(input_data)) + [vcc])
                else:
                    # print input data, no vcc column
                    row.extend(input_data)
                # Output/Results
                out_ptr = 0
                for out in self.outputs:
                    for pin in out.pins:
                        pin_int = self._get_pin(pin)
                        res = self.results[vcc][i][pin_int]

                        row.append(output_data[out_ptr] if vcc_idx == 0 else "")
                        row.append(f"{res.adc}\n({res.logic})") # PinResult(3.3, H) -> "3.3 (H)"
                        out_ptr += 1 # can increment since output_data is sequential
                data.append(row)

        table = [header] + [pin_cols] + data
        metadata = {
            "input_span" : len(self.inputs),
            "output_span" : total_out_pins,
            "num_rows" : num_rows,
            "include_vcc" : include_vcc,
            "num_vcc" : num_vcc
        }
        return table, metadata
    
    def add_result(self, step_num: int, pin: int, logic: int, adc: float, vcc: float) -> None:
        """Creates `PinResult` dataclass from `adc`, and `logic` and adds to `self.results`.

        Args:
            step_num (int): Step number of the test.
            pin (int): Pin number on the socket of the test fixture.
            logic (int): Logic in an int reprsentation, 1=H, 0=L, -1=U.
            adc (float): Measured voltage value.
            vcc (float): VCC voltage of the test condition.
        """
        self.results[vcc][step_num][pin] = PinResult(adc, logic) 

    def compare_results(self, vcc: float) -> None:
        """Compares `self.results` to `self.outputs` at `vcc`.

        Args:
            vcc (float): VCC voltage of the test conditon.

        Raises:
            ValueError: If `cmd_type` of `IOCommand` is unknown.
        """
        for out in self.outputs:
            match out.cmd_type:
                case LogicMapping.Map:
                    passed = self._compare_map(out, vcc)
                case LogicMapping.Single:
                    passed = self._compare_single(out, vcc)
                case LogicMapping.Serial:
                    passed = self._compare_serial(out, vcc)
                case _:
                    raise ValueError(
                        f"No such LogicMapping command type \"{out.cmd_type}\""
                    )
            if self.passed is None or self.passed is not False:
                # only modifies if it hasn't already
                # if already false, test remains false
                self.passed = passed
        return

    def test_conditions(self) -> list[Condition]:
        """Returns a list of `Condition` dataclasses."""
        conditions = []
        for param_idx in range(len(self.global_params["VCC Voltage"])):
            conditions.append(Condition(
                self.global_params["VCC Voltage"][param_idx],
                self.global_params["Output Low"][param_idx],
                self.global_params["Output High"][param_idx]
            ))
        return conditions
    
    def power_pins(self) -> dict:
        """Returns power pins of TestVector."""
        return {
            "vcc_pin": self.global_params["VCC Pin"],
            "gnd_pin": self.global_params["GND Pin"],
        }
    
    def pin_lists(self, vcc: float) -> dict:
        """Creates list of input pins, output pins, and voltages to drive the input pins.

        `input_pins` and `voltage_in` are matched by the order they are in the list.

        Args:
            vcc (float): VCC voltage of the test condition.

        Returns:
            dict[str,Any]: Dictionary containing test pin configuration:
                - input_pins (list[int]): List of input pin names.
                - output_pins (list[float]): List of output pin names.
                - voltage_in (float): Input voltage value.
        """
        in_pins = [] # input pin list
        v_in = [] # input value list
        for inp in self.inputs:
            match inp.cmd_type:
                case LogicMapping.Map:
                    self._map(inp, in_pins, v_in, vcc, isinstance(inp.pin_vals[0], int))
                case LogicMapping.Single:
                    self._single(inp, in_pins, v_in, vcc)
                case LogicMapping.Serial:
                    self._serial(inp, in_pins, v_in)
                case _:
                    raise ValueError(
                        f"No such LogicMapping command type \"{inp.cmd_type}\""
                    )
        # reorder inputs to have clk pin last
        end = len(v_in) - 1
        i = 0
        while i <= end:
            if isinstance(v_in[i], str) and any(c in v_in[i] for c in "RF"):
                v_in[i], v_in[end] = v_in[end], v_in[i]
                in_pins[i], in_pins[end] = in_pins[end], in_pins[i]
                end -= 1
            else:
                i += 1
        # extract all output pins into one list  
        out_pins = []
        for out in self.outputs:
            for pin_ref in out.pins:
                pin = self._get_pin(pin_ref)
                out_pins.append(pin)

        return {
            "input_pins": in_pins,
            "output_pins": out_pins,
            "voltage_in": v_in,
        }
    
    def _get_pin(self, pin: int|str) -> int:
        """Returns integer representation of `pin`."""
        if isinstance(pin, int): return pin
        else: return self.pin_map[pin] 

    def _get_voltage(self, logic: int|str, volt_type: float, vcc: float) -> float:
        """Returns voltages based on `logic` and `volt_type`."""
        if logic in {0, "L", "X"}: return 0 # dont care bits default to 0 volts
        else: return volt_type if volt_type is not None else vcc

    def _logic_to_int(self, logic: int|str) -> int|str:
        """Returns logic as an integer if possible. "X" defaults to 0."""
        if logic == "H": return 1
        elif logic in ("L", "X"): return 0
        else: return logic # already an integer or R/F

    def _int_to_logic(self, logic: int|str) -> str:
        """Returns logic in string representation."""
        if logic == 1: return "H"
        elif logic == 0: return "L"
        elif logic == -1: return "U"
        elif logic == -2: return "Z"
        else: return logic # already a string

    def _pad_inputs(self):
        """If a serial input exists, pads all commands to be the same length as the longest serial input."""
        all_cmds = self.inputs + self.outputs
        if any(cmd.cmd_type == LogicMapping.Serial for cmd in all_cmds):
            max_len = max(len(cmd.pin_vals) for cmd in all_cmds)

            for cmd in all_cmds:
                if cmd.cmd_type == LogicMapping.Map:
                    if isinstance(cmd.pin_vals[0], int):
                        raise ValueError(
                            f"Unable to pad input {cmd.pin_vals[0]} that are integers, use logic symbols instead."
                        )
                cmd.pin_vals += cmd.pin_vals[-1] * (max_len - len(cmd.pin_vals)) # pad with the last element
                cmd.cmd_type = LogicMapping.Serial # need to change so serial functions are used instead
        return

    def _map(self, inp: IOCommand, in_pins: list[int], v_in: list[float], vcc: int|float, is_int: bool) -> None:
        """Appends data to `in_pins`, and `v_in` for `LogicMapping.Map` type `IOCommand`.
        
        Args:
            inp (IOCommand): Input command with `LogicMapping.Map` type.
            in_pins (list[int]): List of input pins.
            v_in (list[float]): List of voltages to drive input pins.
            vcc (float): VCC voltage of the test condition.
            is_int (float): `pin_vals` of `IOCommand` is an integer.
        """
        for i, pin_ref in enumerate(inp.pins):
            pin = self._get_pin(pin_ref)
            if is_int: logic = (inp.pin_vals[0] >> (len(inp.pins) - i - 1)) & 1 # bit shift to extract logic from int
            else: logic = self._logic_to_int(inp.pin_vals[i])
            voltage = self._get_voltage(logic, inp.volt_type, vcc)

            in_pins.append(pin)
            v_in.append(voltage)
        return

    def _single(self, inp: IOCommand, in_pins: list[int], v_in: list[float], vcc: float) -> None:
        """Appends data to `in_pins`, and `v_in` for `LogicMapping.Single` type `IOCommand`.
        
        Args:
            inp (IOCommand): Input command with `LogicMapping.Single` type.
            in_pins (list[int]): List of input pins.
            v_in (list[float]): List of voltages to drive input pins.
            vcc (float): VCC voltage of the test condition.
        """
        for pin_ref in inp.pins:
            pin = self._get_pin(pin_ref)
            logic = self._logic_to_int(inp.pin_vals[0]) # only one pin value for LogicMapping.Single
            voltage = self._get_voltage(logic, inp.volt_type, vcc)

            in_pins.append(pin)
            v_in.append(voltage)
        return
    
    def _serial(self, inp: IOCommand, in_pins: list[int], v_in: list[float]) -> None:
        """Appends data to `in_pins`, and `v_in` for `LogicMapping.Serial` and `LogicMapping.TruthTable` type `IOCommand`.
        
        Args:
            inp (IOCommand): Input command with `LogicMapping.Serial` and `LogicMapping.TruthTable` type.
            in_pins (list[int]): List of input pins.
            v_in (list[float]): List of voltages to drive input pins.
            vcc (float): VCC voltage of the test condition.
        """
        for pin_ref in inp.pins:
            pin = self._get_pin(pin_ref)
            logic_str = "0b" + "".join("1" if c == "H" else "0" if c in ("L", "X") else c for c in inp.pin_vals)

            in_pins.append(pin)
            v_in.append(logic_str)
        return
    
    def _compare_map(self, out: IOCommand, vcc: float) -> bool:
        """Compares `self.results` to expected output of `IOCommand` of type `LogicMapping.Map`.

        Args:
            out (IOCommand): Output command with `LogicMapping.Map` type.
            vcc (float): VCC voltage of the test condition.

        Returns:
            bool: If the results matches the expect output.
        """
        is_int_map = isinstance(out.pin_vals[0], int)
        passed = True
        for i, pin in enumerate(out.pins):
            pin_int = self._get_pin(pin)
            if is_int_map: exp_logic = (out.pin_vals[0] >> (len(out.pins) - i - 1)) & 1 # bit shift to extract logic from int
            else: exp_logic = out.pin_vals[i]
            is_int = isinstance(exp_logic, int)

            got_logic = self.results[vcc][0][pin_int].logic
            if not is_int:
                # converts logic to string representation if exp_logic is in string
                got_logic = self._int_to_logic(got_logic)
                # replaces result.logic with matching str|int representation
                self.results[vcc][0][pin_int].logic = got_logic

            if passed:
                if exp_logic == "X":
                    pass
                elif got_logic != exp_logic:
                    passed = False
        return passed

    def _compare_single(self, out: IOCommand, vcc: float) -> bool:
        """Compares `self.results` to expected output of `IOCommand` of type `LogicMapping.Single`.

        Args:
            out (IOCommand): Output command with `LogicMapping.Single` type.
            vcc (float): VCC voltage of the test condition.

        Returns:
            bool: If the results matches the expect output.
        """
        exp_logic = out.pin_vals[0]
        is_int = isinstance(exp_logic, int)
        passed = True
        for pin in out.pins:
            pin_int = self._get_pin(pin)
            got_logic = self.results[vcc][0][pin_int].logic

            if not is_int:
                # converts logic to string representation if exp_logic is in string
                got_logic = self._int_to_logic(got_logic)
                # replaces result.logic with matching str|int representation
                self.results[vcc][0][pin_int].logic = got_logic

            if passed:
                if exp_logic == "X":
                    pass
                elif got_logic != exp_logic:
                    passed = False   
        return passed
    
    # fix test scripts, does amount of steps based on longest input length
    def _compare_serial(self, out: IOCommand, vcc: float) -> bool:
        """Compares `self.results` to expected output of `IOCommand` of type `LogicMapping.Serial`, or `LogicMapping.TruthTable`.

        Args:
            out (IOCommand): Output command with `LogicMapping.Serial` or `LogicMapping.TruthTable` type.
            vcc (float): VCC voltage of the test condition.

        Returns:
            bool: If the results matches the expect output.
        """
        passed = True
        for pin in out.pins:
            pin_int = self._get_pin(pin)
            for i, exp_logic in enumerate(out.pin_vals):
                is_int = isinstance(exp_logic, int)
                got_logic = self.results[vcc][i][pin_int].logic

                if not is_int:
                    # converts logic to string representation if exp_logic is in string
                    got_logic = self._int_to_logic(got_logic)
                    # replaces result.logic with matching str|int representation
                    self.results[vcc][i][pin_int].logic = got_logic
                if passed:
                    if exp_logic == "X":
                        pass
                    elif got_logic != exp_logic:
                        passed = False   
        return passed

    def simulated_test(self, seed: Optional[int]=None, all_true: bool=False) -> None:
        """Mock test setup simulating output responses of hardware.
        
        Args:
            seed (int): Seed for random voltage generation. If None, voltage is randomly generated.
            all_true (bool): If true, all results are set to the expected value with adc value at VCC or 0. 
        """
        HI_Z = 1.65
        def random_voltage(low: float, high: float, percent: float=0.05) -> float:
            """Returns random floating point based on low and high thresholds with percentage variance."""
            if seed:
                random.seed(seed)
            # Compute bands
            low_min  = low  * (1 - percent)
            low_max  = low  * (1 + percent)
            high_min = high * (1 - percent)
            high_max = high * (1 + percent)

            # Randomly choose which band to sample from
            if random.random() < 0.5:
                return random.uniform(low_min, low_max)
            else:
                return random.uniform(high_min, high_max)
            
        def calculate_test_steps() -> int:
            """Returns number of steps test fixture conducts. Based on maximum input length."""
            num_steps = 0
            for inp in self.inputs:
                if inp.cmd_type == LogicMapping.Single or inp.cmd_type == LogicMapping.Map:
                    length = 1
                else:
                    length = len(inp.pin_vals)
                
                if length > num_steps:
                    num_steps = length
            return num_steps

        # simulates testing loop
        # used for checking _compare_results function implementation and export_table
        for param_idx, vcc in enumerate(self.global_params["VCC Voltage"]):
            low = self.global_params["Output Low"][param_idx]
            high = self.global_params["Output High"][param_idx]
            
            num_steps = calculate_test_steps()

            for step in range(num_steps):
                for out in self.outputs:
                    for i, pin in enumerate(out.pins):
                        pin_int = self._get_pin(pin)
                        if all_true:
                            adc_val = self._get_exp_val(
                                out.pin_vals,
                                out.cmd_type,
                                vcc,
                                len(out.pins),
                                i,
                                step)
                        else:
                            adc_val = round(random_voltage(low, high, 0.05), 2)

                        if adc_val <= low:
                            logic = 0
                        elif adc_val >= high:
                            logic = 1
                        elif adc_val == HI_Z:
                            logic = -2
                        else:
                            logic = -1

                        self.add_result(step, pin_int, logic, adc_val, vcc)
            self.compare_results(vcc)
        return

    def _get_exp_val(
            self,
            pin_vals: list[int|str],
            cmd_type: LogicMapping,
            vcc: float,
            num_pins: int,
            i: int,
            step: int) -> float:
        """Returns `vcc` or `0.0` depending on the expected logic value of the pin at `step`."""

        match cmd_type:
            case LogicMapping.Map:
                if isinstance(pin_vals[0], int):
                    val = (pin_vals[0] >> (num_pins - i - 1)) & 1
                    logic = "H" if val == 1 else "L"
                else:
                    logic = pin_vals[i]
            case LogicMapping.Single:
                logic = pin_vals[0]
            case LogicMapping.Serial:
                logic =  pin_vals[step]

        if logic == "H":
            return vcc
        elif logic == "Z":
            return 1.65
        else:
            return 0.0
