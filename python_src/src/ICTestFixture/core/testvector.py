import serial
import random # used for dummy test
from enum import Enum, auto
from typing import NamedTuple

# useful for accessing tuple elements by variable name
# TODO: add serial type
class LogicMapping(Enum):
    single = auto()
    map = auto()
    truth_table = auto()

class IOCommand(NamedTuple):
    pins: list[int|str]
    pin_vals: list[list|int|str]
    volt_type: str
    cmd_type: LogicMapping

class ResultTuple(NamedTuple):
    adc_vals: list[float]
    logic_vals: list[str|int]

class TestVector:
    # class attributes shared by all instances
    pin_map = None
    global_params = None

    def __init__(self, inputs: list[IOCommand], outputs: list[IOCommand], test_name: str):
        self.inputs = inputs
        self.outputs = outputs
        # results will be a dict of lists of ResultTuples
        self.results = {vcc_voltage: [] for vcc_voltage in TestVector.global_params["VCC Voltage"]}
        self.test_name = test_name
        self.passed = None

    def test(self, ser: serial.Serial):
        # could use dict for test args, isInt, onCLK, singleIn, multiIn, mapIn, useTT
        for param_idx, vcc_voltage in enumerate(TestVector.global_params["VCC Voltage"]):
            # set power pins
            ser.write((
                f"PRM:{TestVector.global_params["VCC Pin"]},"
                f"{TestVector.global_params["GND Pin"]},"
                f"{vcc_voltage}\n"
            ).encode("utf-8"))

            # TODO: figure out clock inputs, specifically checking outputs on edges
            # Likely need separate test functions, truth tables
            if self.inputs[0].cmd_type == LogicMapping.truth_table:
                self._test_tt(self, ser, param_idx)
            else:
                self._test(self, ser, param_idx)
                
            # compare expected output with results
            passed = True
            if self.passed is not False:
                for exp, res in zip(self.outputs, self.results[vcc_voltage]):
                    passed = self._compare_results(exp, res)
                    if passed == False:
                        break
                self.passed = passed
        return

    def export_as_table(self):
        def to_bin_str(val, width):
            if isinstance(val, int):
                # convert int to binary string with leading 0b, +2 for padding
                return format(val, f"#0{width+2}b")
            elif isinstance(val, (list, tuple)):
                return ", ".join(val)
            else:
                return str(val)
        # empty strings are used for spanning
        num_vcc = len(TestVector.global_params["VCC Voltage"])
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

        data = []
        is_tt = True if self.inputs[0].cmd_type == LogicMapping.truth_table else False 
        num_rows = len(self.inputs[0].pin_vals) if is_tt else 1

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
                    if out.cmd_type == LogicMapping.single:
                        val_idx = 0
                    elif out.cmd_type == LogicMapping.map:
                        val_idx = 0 if isinstance(out.pin_vals[0], int) else pin_idx
                    elif out.cmd_type == LogicMapping.truth_table:
                        val_idx = i

                    if isinstance(out.pin_vals[val_idx], int):
                        out_val = (out.pin_vals[0] >> (len(out.pins) - pin_idx - 1)) & 1
                    else:
                        out_val = out.pin_vals[val_idx]
                    output_data.append(out_val)

            for vcc_idx, vcc_voltage in enumerate(TestVector.global_params["VCC Voltage"]):
                row = []
                # Inputs and VCC
                if include_vcc:
                    # print input data if first vcc_row, else print empty strings, vcc column at end
                    row.extend((input_data if vcc_idx == 0 else [""] * len(input_data)) + [vcc_voltage])
                else:
                    # print input data, no vcc column
                    row.extend(input_data)
                # Output/Results
                for out_idx, out in enumerate(self.outputs):
                    res = self.results[vcc_voltage][out_idx] # corresponding result based on voltage and output pin group
                    for pin_idx in range(len(out.pins)):
                        # calculate index postions of outputs and results
                        out_data_idx = pin_idx if is_tt else  out_idx*len(self.outputs) + pin_idx
                        res_idx = i if is_tt else pin_idx
                        
                        row.append(output_data[out_data_idx] if vcc_idx == 0 else "")
                        row.append(f"{res.adc_vals[res_idx]} ({res.logic_vals[res_idx]})")
                data.append(row)

        table = [header] + [pin_cols] + data
        metadata = {
            "input span" : len(self.inputs),
            "output span" : total_out_pins,
            "num rows" : num_rows,
            "include vcc" : include_vcc,
            "num vcc" : num_vcc
        }
        return table, metadata
    
    def _list_to_command(self, command: str, args: list):
        return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")

    def _execute(self, ser: serial.Serial, in_pins: list[int], v_in: list[int|float], out_pins: list[int]):
        ser.write(self._list_to_command("INS", in_pins))
        ser.write(self._list_to_command("VIP", v_in))
        ser.write(self._list_to_command("OUT", out_pins))
        ser.write("TEST\n".encode("utf-8"))
        return

    def _compare_results(self, exp: IOCommand, res: ResultTuple):
        # check bit by bit because ResultTuple does not store as int
        # U prevents bit shifting results
        if isinstance(exp.pin_vals[0], int):
            for i in range(len(exp.pins)):
                bit = exp.pin_vals[0] >> (len(exp.pins) - i - 1) & 1
                if bit != res.logic_vals[i]:
                    return False
        # compares two lists
        elif exp.pin_vals != res.logic_vals:
            return False
        return True

    def _test(self, ser: serial.Serial, param_idx: int):
        in_pins = [] # input pin list
        v_in = [] # input value list
        for inp in self.inputs:
            match inp.cmd_type:
                case LogicMapping.single:
                    self._single(inp, in_pins, v_in, param_idx)
                case LogicMapping.map:
                    self._map(inp, in_pins, v_in, param_idx, isinstance(inp.pin_vals[0], int))
                case _:
                    raise ValueError(
                        f"No such LogicMapping command type \"{inp.cmd_type}\""
                    )
        # extract all output pins into one list  
        out_pins = []
        for out in self.outputs:
            for pin_ref in out.pins:
                pin = TestVector.get_pin(pin_ref)
                out_pins.append(pin)

        self._execute(ser, in_pins, v_in, out_pins)
        self._read_results(ser, param_idx)
        return

    def _single(self, inp: IOCommand, in_pins: list[int], v_in: list[int|float], param_idx: int):
        for pin_ref in inp.pins:
            pin = TestVector.get_pin(pin_ref)
            logic = inp.pin_vals[0] # only one pin value for LogicMapping.single
            voltage = TestVector.get_voltage(logic, inp.volt_type, param_idx)

            in_pins.append(pin)
            v_in.append(voltage)
        return
    
    def _map(self, inp: IOCommand, in_pins: list[int], v_in: list[int|float], param_idx: int, isInt: bool):
        for i, pin_ref in enumerate(inp.pins):
            pin = TestVector.get_pin(pin_ref)
            if isInt: logic = (inp.pin_vals[0] >> (len(pin) - i - 1)) & 1 # bit shift to extract logic from int
            else: logic = inp.pin_vals[i]
            voltage = TestVector.get_voltage(logic, inp.volt_type, param_idx)

            in_pins.append(pin)
            v_in.append(voltage)
        return
    
    def _test_tt(self, ser: serial.Serial, param_idx: int):
        for i in range(self.inputs[0].pin_vals): # iterate through length of truth table
            in_pins = []
            v_in = []
            for inp in self.inputs:
                for pin_ref in inp.pins:
                    pin = TestVector.get_pin(pin_ref)
                    logic = inp.pin_vals[i]
                    voltage = TestVector.get_voltage(logic, inp.volt_type, param_idx)

                    in_pins.append(pin)
                    v_in.append(voltage)
            
            out_pins = []
            for out in self.outputs:
                for pin_ref in out.pins:
                    pin = TestVector.get_pin(pin_ref)
                    out_pins.append(pin)

            # write commands to serial
            self._execute(ser, in_pins, v_in, out_pins)

            # TODO: read results and place into ResultTuple Object
            self._read_results_tt(ser, i, param_idx)
        return

    def _read_results(self, ser: serial.Serial, param_idx: int):
        response = ser.readline().decode("utf-8").strip()
        adc_vals_str = response.split(",")
        resp_idx = 0
        for i, out in enumerate(self.outputs):
            isInt = isinstance(out.pin_vals[i], int) # used to make results into int if output is formatted as int

            adc_vals = []
            logic_vals = []

            for _ in range(len(out.pins)):
                # extract value and logic
                val = adc_vals_str[resp_idx]
                float_val = float(val) / 100
                logic = TestVector.logic_from_thld(float_val, isInt, param_idx)

                adc_vals.append(float_val)
                logic_vals.append(logic)
                resp_idx += 1
            # set results
            self.results[TestVector.global_params["VCC Voltage"][param_idx]].append(ResultTuple(adc_vals, logic_vals))
        return

    def _read_results_tt(self, ser: serial.Serial, row_idx: int, param_idx: int):
        response = ser.readline().decode("utf-8").strip()
        adc_vals_str = response.split(",")
        resp_idx = 0
        for i in range(len(self.outputs)):
            # extract value and logic
            val = adc_vals_str[resp_idx]
            float_val = float(val) / 100
            logic = TestVector.logic_from_thld(float_val, False, param_idx)

            if row_idx == 0:
                self.results[TestVector.global_params["VCC Voltage"][param_idx]].append([logic])
            else:
                self.results[TestVector.global_params["VCC Voltage"][param_idx]][i].append(logic)
            resp_idx += 1
        return
    
    @classmethod
    def update_pin_map(cls, pin_map: dict):
        cls.pin_map = pin_map

    @classmethod
    def update_global_params(cls, global_params: dict):
        cls.global_params = global_params
    
    @classmethod
    def get_pin(cls, pin_ref: int|str):
        if isinstance(pin_ref, int): return pin_ref
        else: return cls.pin_map[pin_ref] 

    @classmethod
    def get_voltage(cls, logic: int|str, volt_type: str, param_idx: int):
        if logic in {0, "L", "X"}: return 0 # dont care bits default to 0 volts
        else: return volt_type if volt_type is not None else  cls.global_params["VCC Voltage"][param_idx]

    @classmethod
    def logic_from_thld(cls, adc_val: float, isInt: bool, param_idx: int):
        if adc_val >= cls.global_params["Output High"][param_idx]: return 1 if isInt else "H"
        elif adc_val <= cls.global_params["Output Low"][param_idx]: return 0 if isInt else "L"
        # not either logic low or high based on thresholds
        else: return "U"

    def dummy_test(self):
        def random_voltage(low, high, percent=0.05):
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
        # dummy test function to generate example data for report formatting
        for param_idx, vcc_voltage in enumerate(TestVector.global_params["VCC Voltage"]):
            low = TestVector.global_params["Output Low"][param_idx]
            high = TestVector.global_params["Output High"][param_idx]
            for out in self.outputs:
                isInt = isinstance(out.pin_vals[0], int)
                # create dummy adc values and logic results based on output pin values and VCC voltage
                adc_vals = []
                logic_vals = []

                if out.cmd_type == LogicMapping.single or out.cmd_type == LogicMapping.map:
                    num_vals = len(out.pins)
                else:
                    num_vals = len(out.pin_vals)

                for _ in range(num_vals):
                    adc_val = random_voltage(low, high, 0.05)
                    adc_vals.append(round(adc_val,3))
                    logic_vals.append(TestVector.logic_from_thld(adc_val, isInt, param_idx))
                self.results[vcc_voltage].append(ResultTuple(adc_vals, logic_vals))

        passed = True
        for vcc_voltage in TestVector.global_params["VCC Voltage"]:       
            for exp, res in zip(self.outputs, self.results[vcc_voltage]):
                passed = self._compare_results(exp, res)
                if passed == False:
                    break
        self.passed = passed
        return
    