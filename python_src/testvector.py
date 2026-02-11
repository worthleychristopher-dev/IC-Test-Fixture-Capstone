import serial
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
    logic: list[int|str]

class TestVector:
    # class attributes shared by all instances
    pin_map = None
    global_params = None

    def __init__(self, inputs: list[IOCommand], outputs: list[IOCommand], test_name: str):
        self.inputs = inputs
        self.outputs = outputs
        self.results = [output.pin_vals for output in outputs] # [None for _ in range(len(outputs))]
        self.test_name = test_name
        self.passed = False

    def export_as_table(self):
        # convert integers to binary string, else return string
        def to_bin_str(val, width):
            return format(val, f"#0{width+2}b") if isinstance(val, int) else ", ".join(val)

        # build header
        # VCC Voltage is always default High/1 value if not specified
        header = (
            [f"Inputs ({TestVector.global_params["VCC Voltage"]})"] + ([""] * (len(self.inputs) - 1)) +
            ["Outputs/Results"] + [""] * (2 * len(self.outputs) - 1)
        )
        # build columns
        pin_cols = (
            [", ".join(inp.pins) for inp in self.inputs] +
            [", ".join(out.pins) for out in self.outputs]
        )

        pin_vals = []
        is_tt = True if self.inputs[0].cmd_type == LogicMapping.truth_table else False 
        num_rows = len(self.inputs[0].pin_vals) if is_tt else 1

        # create rows for pin_vals
        for i in range(num_rows):
            row = []
            for inp in self.inputs:
                inp_str = to_bin_str(inp.pin_vals[i], len(inp.pins))
                inp_str += f" ({inp.volt_type})" if inp.volt_type else "" # only include voltage if specified
                row.append(inp_str)

            for out, res in zip(self.outputs, self.results):
                row.extend([
                    to_bin_str(out.pin_vals[i], len(out.pins)),
                    (to_bin_str(res[i], len(out.pins))) # change to result voltage from ADC
                ])
            pin_vals.append(row)
        return [header] + [pin_cols] + pin_vals

    def test(self, ser: serial.Serial):
        # could use dict for test args, isInt, onCLK, singleIn, multiIn, mapIn, useTT
        # set power pins
        ser.write((
            f"PRM:{TestVector.global_params["VCC Pin"]},"
            f"{TestVector.global_params["GND Pin"]},"
            f"{TestVector.global_params["VCC Voltage"]}\n"
        ).encode("utf-8"))

        # TODO: implement testing loop
        # TODO: write inputs based on LogicMapping

        # TODO: compare expected output with results
        return

    def _test_single(self, inp: IOCommand, ins: list[int], vip: list[int|float]):
        pass
    
    def _test_map(self, inp: IOCommand, ins: list[int], vip: list[int|float], isInt: bool):
        pass
    
    def _test_tt(self, inp: IOCommand, ins: list[int], vip: list[int|float]):
        pass

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
    def get_voltage(cls, logic: int|str, volt_type: str):
        if logic in {0, "L", "X"}: return 0 # dont care bits default to 0 volts
        else: return volt_type if volt_type is not None else  cls.global_params["VCC Voltage"]

    @classmethod
    def logic_from_thld(cls, adc_val: float, isInt: bool):
        if adc_val >= cls.global_params["Output High"]: return 1 if isInt else "H"
        elif adc_val <= cls.global_params["Output Low"]: return 0 if isInt else "L"
        # not either logic low or high based on thresholds
        else: return "U"
