import serial
import random # used for dummy test
from enum import Enum, auto
from typing import NamedTuple

# useful for accessing tuple elements by variable name
# can implement class methods if needed
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
        self.passed = False

    def export_as_table(self):
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
                inp_str = self.to_bin_str(inp.pin_vals[i], len(inp.pins))
                inp_str += f" ({inp.volt_type})" if inp.volt_type else "" # only include voltage if specified
                input_data.append(inp_str)

            # compute output data entries
            # TODO: adjust this to work with individual output pin_cols
            output_data = []
            for out in self.outputs:
                for pin_idx in range(len(out.pins)):
                    if out.cmd_type == LogicMapping.single:
                        val_idx = 0
                    elif out.cmd_type == LogicMapping.map:
                        val_idx = pin_idx
                    elif out.cmd_type == LogicMapping.truth_table:
                        val_idx = i
                    output_data.append(self.to_bin_str(out.pin_vals[val_idx], 1))

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
                        out_data_idx = pin_idx if out.cmd_type == LogicMapping.truth_table else  out_idx*len(self.outputs) + pin_idx
                        row.append(output_data[out_data_idx] if vcc_idx == 0 else "")
                        res_idx = i if is_tt else pin_idx
                        row.append(self._append_results(res, res_idx))
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
    
    def to_bin_str(self, val, width):
        if isinstance(val, int):
            # convert int to binary string with leading 0b, +2 for padding
            return format(val, f"#0{width+2}b")
        elif isinstance(val, (list, tuple)):
            return ", ".join(val)
        else:
            return str(val)

    def _append_results(self, res: ResultTuple, i: int):
        return (
            f"{res.adc_vals[i]} "
            f"({self.to_bin_str(res.logic_vals[i], 1)})"
        )

    def test(self, ser: serial.Serial):
        # could use dict for test args, isInt, onCLK, singleIn, multiIn, mapIn, useTT
        for vcc_voltage in TestVector.global_params["VCC Voltage"]:
            # set power pins
            ser.write((
                f"PRM:{TestVector.global_params["VCC Pin"]},"
                f"{TestVector.global_params["GND Pin"]},"
                f"{vcc_voltage}\n"
            ).encode("utf-8"))

            # TODO: figure out clock inputs, specifically checking outputs on edges
            # Likely need separate test functions, truth tables
            if self.inputs[0].cmd_type == LogicMapping.truth_table:
                self._test_tt(self, ser)
            else:
                self._test(self, ser)
                
            # compare expected output with results
            passed = True
            for exp, res in zip(self.outputs, self.results):
                if exp.pin_vals != res.logic:
                    passed = False
                    break
            
            self.passed = passed
        return

    def _test(self, ser: serial.Serial):
        in_pins = [] # input pin list
        v_in = [] # input value list
        for inp in self.inputs:
            match inp.cmd_type:
                case LogicMapping.single:
                    self._single(inp, in_pins, v_in)
                case LogicMapping.map:
                    self._map(inp, in_pins, v_in, isinstance(inp.pin_vals[0], int))
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
        self._read_results(ser)
        return
    
    def _test_tt(self, ser: serial.Serial):
        for i in range(self.inputs[0].pin_vals): # iterate through length of truth table
            in_pins = []
            v_in = []
            for inp in self.inputs:
                for pin_ref in inp.pins:
                    pin = TestVector.get_pin(pin_ref)
                    logic = inp.pin_vals[i]
                    voltage = TestVector.get_voltage(logic, inp.volt_type)

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
            self._read_results(ser)
        return

    def _single(self, inp: IOCommand, in_pins: list[int], v_in: list[int|float]):
        for pin_ref in inp.pins:
            pin = TestVector.get_pin(pin_ref)
            logic = inp.pin_vals[0] # only one pin value for LogicMapping.single
            voltage = TestVector.get_voltage(logic, inp.volt_type)

            in_pins.append(pin)
            v_in.append(voltage)
        return
    
    def _map(self, inp: IOCommand, in_pins: list[int], v_in: list[int|float], isInt: bool):
        for i, pin_ref in enumerate(inp.pins):
            pin = TestVector.get_pin(pin_ref)
            if isInt: logic = (inp.pin_vals[0] >> (len(pin) - i - 1)) & 1 # bit shift to extract logic from int
            else: logic = inp.pin_vals[i]
            voltage = TestVector.get_voltage(logic, inp.volt_type)

            in_pins.append(pin)
            v_in.append(voltage)
        return

    def _list_to_command(self, command: str, args: list):
        return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")

    def _execute(self, ser: serial.Serial, in_pins: list[int], v_in: list[int|float], out_pins: list[int]):
        ser.write(self._list_to_command("INS", in_pins))
        ser.write(self._list_to_command("VIP", v_in))
        ser.write(self._list_to_command("OUT", out_pins))
        ser.write("TEST\n".encode("utf-8"))
        return

    def _read_results(self, ser: serial.Serial):
        response = ser.readline().decode("utf-8").strip()
        adc_vals_str = response.split(",")
        resp_idx = 0
        for i, out in enumerate(self.outputs):
            adc_vals = []
            logic_vals = []
            isInt = isinstance(out.pin_vals[i], int) # used to make results into int if output is formatted as int
            if isInt: logic_vals.append(0)
            for j in range(len(out.pins)):
                # extract value and logic
                val = adc_vals_str[resp_idx]
                float_val = float(val) / 100
                logic = TestVector.logic_from_thld(float_val, isInt)

                adc_vals.append(float_val)
                if isInt: logic_vals[0] |= (logic << (len(out.pins) - j - 1)) # bit shift and add logic bit to int
                else: logic_vals.append(logic)
                resp_idx += 1
            # set results
            self.results[i] = ResultTuple(adc_vals, logic_vals)
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
    def get_voltage(cls, logic: int|str, volt_type: str, param_idx: int = 0):
        if logic in {0, "L", "X"}: return 0 # dont care bits default to 0 volts
        else: return volt_type if volt_type is not None else  cls.global_params["VCC Voltage"][param_idx]

    @classmethod
    def logic_from_thld(cls, adc_val: float, isInt: bool, param_idx: int = 0):
        if adc_val >= cls.global_params["Output High"][param_idx]: return 1 if isInt else "H"
        elif adc_val <= cls.global_params["Output Low"][param_idx]: return 0 if isInt else "L"
        # not either logic low or high based on thresholds
        else: return "U"

    def dummy_test(self):
        # dummy test function to generate example data for report formatting
        for vcc_voltage in TestVector.global_params["VCC Voltage"]:
            for out in self.outputs:
                # create dummy adc values and logic results based on output pin values and VCC voltage
                adc_vals = []
                logic_list = []
                if out.cmd_type == LogicMapping.single or out.cmd_type == LogicMapping.map:
                    num_vals = len(out.pins)
                else:
                    num_vals = len(out.pin_vals)
                # TODO: when int, bitshift logic_vals to create int output
                for _ in range(num_vals):
                    adc_val = random.uniform(0, float(vcc_voltage[:-1]))
                    adc_vals.append(round(adc_val,3))
                    logic_list.append(TestVector.logic_from_thld(adc_val, False))
                self.results[vcc_voltage].append(ResultTuple(adc_vals, logic_list))
    