import serial
from typing import NamedTuple

# useful for accessing tuple elements by variable name
# can implement class methods if needed
class IOCommand(NamedTuple):
    pins: list[int|str]
    pin_vals: list[list|int|str]
    volt_type: str

class TestVector:
    # class attributes shared by all instances
    pin_map = None
    global_params = None

    def __init__(self, inputs: list[IOCommand], outputs: list[IOCommand], test_name: str):
        #TODO: check length of inputs and output values match
        self.inputs = inputs
        self.outputs = outputs
        self.results = [output.pin_vals for output in outputs] # [None for _ in range(len(outputs))]
        self.test_name = test_name
        self.passed = False

    @classmethod
    def update_pin_map(cls, pin_map: dict):
        cls.pin_map = pin_map

    @classmethod
    def update_global_params(cls, global_params: dict):
        cls.global_params = global_params
        
    def export_as_table(self):
        # convert integers to binary string, else return string
        def to_bin_str(val, width):
            return format(val, f"#0{width+2}b") if isinstance(val, int) else ", ".join(val)

        # build header
        header = (
            ["Inputs"] + ([""] * (len(self.inputs) - 1)) +
            ["Outputs/Results"] + [""] * (2 * len(self.outputs) - 1)
        )
        # build columns
        pin_cols = (
            [", ".join(input.pins) for input in self.inputs] +
            [", ".join(output.pins) for output in self.outputs]
        )

        pin_vals = []
        is_tt = isinstance(self.inputs[0].pin_vals[0], list) # truth table will have [[]] structure
        num_rows = len(self.inputs[0].pin_vals[0]) if is_tt else 1
        #TODO: add voltage reference to table

        # create rows for pin_vals
        for i in range(num_rows):
            row = []
            for input in self.inputs:
                input_vals = input.pin_vals[0] if is_tt else input.pin_vals
                row.append(to_bin_str(input_vals[i], len(input.pins)))

            for output, result in zip(self.outputs, self.results):
                output_vals = output.pin_vals[0] if is_tt else output.pin_vals
                result_vals = result[0] if is_tt else result
                row.extend([
                    to_bin_str(output_vals[i], len(output.pins)),
                    to_bin_str(result_vals[i], len(output.pins))
                ])
            pin_vals.append(row)
        return [header] + [pin_cols] + pin_vals

    def test(self, ser: serial.Serial):
        pass
 