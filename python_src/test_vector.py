import serial

class TestVector:
    # class attributes shared by all instances
    _pin_map = None
    _global_params = None

    def __init__(self):
        self._inputs = None
        self._outputs = None
        self._results = None
        self._passed = False

    @classmethod
    def update_pin_map(cls, pin_map: dict):
        cls._pin_map = pin_map

    @classmethod
    def update_global_params(cls, global_params: dict):
        cls._global_params = global_params
        
    @property
    def inputs(self) -> list[tuple]:
        return self._inputs

    @property
    def outputs(self) -> list[tuple]:
        return self._outputs
    
    @property
    def results(self) -> list:
        return self._results
    
    @property
    def passed(self) -> bool:
        return self._passed

    @inputs.setter
    def inputs(self, input_vector: list[tuple]) -> None:
        self._inputs = input_vector

    @outputs.setter
    def outputs(self, output_vector: list[tuple]) -> None:
        self._outputs = output_vector
        # results list is same length as output vector
        self._results = [None for _ in range(len(output_vector))]

    def test(self, ser: serial.Serial):
        pass
