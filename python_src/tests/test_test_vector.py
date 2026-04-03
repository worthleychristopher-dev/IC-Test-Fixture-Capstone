import pytest

from ICTestFixture.device import test_vector

@pytest.fixture
def tv_fixture():
    # factory method to dynamically create a test fixture
    def _create(*, input_cmds, output_cmds):
        # input/output cmds must be passed by name
        global_params = {
            "VCC Pin": 8,
            "GND Pin": 7,
            "VCC Voltage": [3.3, 5],
            "Output Low": [0.23, 0.36],
            "Output High": [3.2, 4.9]
        }

        return test_vector.TestVector(
            global_params=global_params,
            pin_map={"A": 1, "B": 20},
            inputs=input_cmds,
            outputs=output_cmds,
            test_name="Test Value/Compare functions"
        )
    return _create

@pytest.fixture
def map_fixture():
    return [
        test_vector.IOCommand(
            pins=[9, "B"],
            pin_vals=["H", "L"],
            volt_type=3.3,
            cmd_type=test_vector.LogicMapping.Map
        ),
        test_vector.IOCommand(
            pins=[5, "A"],
            pin_vals=[0b01],
            volt_type=None,
            cmd_type=test_vector.LogicMapping.Map
        ),
        test_vector.IOCommand(
            pins=[7, 11],
            pin_vals=["X", "H"],
            volt_type=None,
            cmd_type=test_vector.LogicMapping.Map
        )
    ]

@pytest.fixture
def single_one_pin_fixture():
    return [
        test_vector.IOCommand(
            pins=[2],
            pin_vals=["H"],
            volt_type=2.5,
            cmd_type=test_vector.LogicMapping.Single
        ),
        test_vector.IOCommand(
            pins=["B"],
            pin_vals=["H"],
            volt_type=None,
            cmd_type=test_vector.LogicMapping.Single
        ),
        test_vector.IOCommand(
            pins=[18],
            pin_vals=["X"],
            volt_type=4.5,
            cmd_type=test_vector.LogicMapping.Single
        )
    ]

@pytest.fixture
def single_multi_pin_fixture():
    return [
        test_vector.IOCommand(
            pins=[2, 16],
            pin_vals=["H"],
            volt_type=2.5,
            cmd_type=test_vector.LogicMapping.Single
        ),
        test_vector.IOCommand(
            pins=["B", 12],
            pin_vals=["H"],
            volt_type=None,
            cmd_type=test_vector.LogicMapping.Single
        ),
        test_vector.IOCommand(
            pins=[18, "A"],
            pin_vals=["L"],
            volt_type=4.5,
            cmd_type=test_vector.LogicMapping.Single
        )
    ]

@pytest.fixture
def serial_one_pin_fixture():
    return [
        test_vector.IOCommand(
            pins=[2],
            pin_vals=["H", "L", "X", "R", "F"],
            volt_type=2.5,
            cmd_type=test_vector.LogicMapping.Serial
        ),
        test_vector.IOCommand(
            pins=["B"],
            pin_vals=["H", "L", "L"],
            volt_type=None,
            cmd_type=test_vector.LogicMapping.Serial
        )
    ]

@pytest.fixture
def serial_multi_pin_fixture():
    return [
        test_vector.IOCommand(
            pins=[2, "A"],
            pin_vals=["H", "L", "X", "R", "F"],
            volt_type=2.5,
            cmd_type=test_vector.LogicMapping.Serial
        ),
        test_vector.IOCommand(
            pins=["B", 12, 5],
            pin_vals=["H", "L", "L"],
            volt_type=None,
            cmd_type=test_vector.LogicMapping.Serial
        )
    ]

class TestTestVectorHelpers:
    """Tests Helper functions used by TestVector"""
    @pytest.fixture
    def helper_tv_fixture(self):
        pin_map = {
            "A": 3,
            "B": 4
        }

        return test_vector.TestVector(
            global_params=None,
            pin_map=pin_map,
            inputs=None,
            outputs=None,
            test_name="Test Helper Functions"
        )

    @pytest.mark.parametrize(
        "pin, exp_pin",[
            (8, 8),     # int pin
            ("A", 3),   # reference to pin A
            ("B", 4)    # reference to pin B
        ]
    )
    def test_test_vector_get_pin(self, pin, exp_pin, helper_tv_fixture):
        assert helper_tv_fixture._get_pin(pin) == exp_pin

    @pytest.mark.parametrize(
        "logic, volt_type, vcc, exp_volt",[
            ("H", 3.3, 5, 3.3),     # HIGH with volt_type
            ("H", None, 5, 5),      # HIGH without volt_type
            (1, 2.5, 3.3, 2.5),     # 1 with volt_type
            (1, None, 3.3, 3.3),    # 1 without volt_type
            ("L", 1.8, 5, 0),       # LOW with volt_type
            ("L", None, 5, 0),      # LOW without volt_type
            ("X", 3.3, 4, 0),       # Don't care with volt_type
            ("X", None, 4, 0),      # Don't care without volt_type
            (0, 2.5, 2.5, 0),       # 0 with volt_type
            (0, None, 2.5, 0)       # 0 without volt_type
        ]
    )
    def test_test_vector_get_voltage(self, logic, volt_type, vcc, exp_volt, helper_tv_fixture):
        assert helper_tv_fixture._get_voltage(logic, volt_type, vcc) == exp_volt
    
    @pytest.mark.parametrize(
        "logic, exp_int",[
            ("H", 1),
            (1, 1),
            ("L", 0),
            (0, 0),
            ("X", 0),   # don't care defaults to LOW
            ("R", "R"), # clock pulse, rising edge
            ("F", "F")  # clock pulse, falling edge
        ]
    )
    def test_test_vector_logic_to_int(self, logic, exp_int, helper_tv_fixture):
        assert helper_tv_fixture._logic_to_int(logic) == exp_int

    @pytest.mark.parametrize(
        "logic, exp_str",[
            (1, "H"),
            (0, "L"),
            (-1, "U")
        ]
    )
    def test_test_vector_int_to_logic(self, logic, exp_str, helper_tv_fixture):
        assert helper_tv_fixture._int_to_logic(logic) == exp_str

class TestTestVectorParameters:
    """Tests functions that regarding conitions/test metadata."""
    @pytest.fixture
    def parameter_tv_fixture(self):
        global_params = {
            "VCC Pin": 1,
            "GND Pin": 2,
            "VCC Voltage": [1.8, 2.5, 3.3, 4, 4.5, 5],
            "Output Low": [0.12, 0.24, 0.5, 0.71, 0.36, 0.42],
            "Output High": [1.7, 2.4, 3.2, 3.9, 4.4, 4.9]
        }

        return test_vector.TestVector(
            global_params=global_params,
            pin_map=None,
            inputs=None,
            outputs=None,
            test_name="Test Parameter Functions"
        )

    def test_test_vector_test_conditions(self, parameter_tv_fixture):
        EXP_VCC = [1.8, 2.5, 3.3, 4, 4.5, 5]
        EXP_LOW = [0.12, 0.24, 0.5, 0.71, 0.36, 0.42]
        EXP_HIGH = [1.7, 2.4, 3.2, 3.9, 4.4, 4.9]

        for i, condition in enumerate(parameter_tv_fixture.test_conditions()):
            assert condition.vcc == EXP_VCC[i]
            assert condition.out_high == EXP_HIGH[i]
            assert condition.out_low == EXP_LOW[i]

    def test_test_vector_power_pins(self, parameter_tv_fixture):
        assert parameter_tv_fixture.power_pins() == {"vcc_pin": 1, "gnd_pin": 2}

class TestTestVectorValueLists:
    """Tests functions that create the argument lists."""
    def test_map(self, tv_fixture, map_fixture):
        in_pins = []
        v_in = []

        map_tv_fixture = tv_fixture(input_cmds=None, output_cmds=None) # ._map is not a static function, instance of TestVector
        for cmd in map_fixture:
            is_int = True if isinstance(cmd.pin_vals[0], int) else False
            map_tv_fixture._map(cmd, in_pins, v_in, 5.0, is_int)

        assert in_pins == [9, 20, 5, 1, 7, 11]
        assert v_in == [3.3, 0, 0, 5.0, 0, 5.0]

    def test_single(self, tv_fixture, single_one_pin_fixture, single_multi_pin_fixture):
        in_pins_one = []
        v_in_one = []

        single_fixture = tv_fixture(input_cmds=None, output_cmds=None)
        for cmd in single_one_pin_fixture:
            single_fixture._single(cmd, in_pins_one, v_in_one, 5.0)

        assert in_pins_one == [2, 20, 18]
        assert v_in_one == [2.5, 5.0, 0]

        in_pins_multi = []
        v_in_multi = []

        for cmd in single_multi_pin_fixture:
            single_fixture._single(cmd, in_pins_multi, v_in_multi, 5.0)

        assert in_pins_multi == [2, 16, 20, 12, 18, 1]
        assert v_in_multi == [2.5, 2.5, 5.0, 5.0, 0, 0]

    def test_serial(self, tv_fixture, serial_one_pin_fixture, serial_multi_pin_fixture):
        in_pins_one = []
        v_in_one = []

        serial_fixture = tv_fixture(input_cmds=None, output_cmds=None)
        for cmd in serial_one_pin_fixture:
            serial_fixture._serial(cmd, in_pins_one, v_in_one)

        assert in_pins_one == [2, 20]
        assert v_in_one == ["0b100RF", "0b100"]

        in_pins_multi = []
        v_in_multi = []

        for cmd in serial_multi_pin_fixture:
            serial_fixture._serial(cmd, in_pins_multi, v_in_multi)

        assert in_pins_multi == [2, 1, 20, 12, 5]
        assert v_in_multi == ["0b100RF", "0b100RF", "0b100", "0b100", "0b100"]

    def test_pin_lists_map(self, tv_fixture, map_fixture):
        map_tv_fixture = tv_fixture(input_cmds=map_fixture, output_cmds=map_fixture)
        ret = map_tv_fixture.pin_lists(5.0)
        
        assert isinstance(ret, dict)
        assert ret["input_pins"] == [9, 20, 5, 1, 7, 11]
        assert ret["output_pins"] == [9, 20, 5, 1, 7, 11]
        assert ret["voltage_in"] == [3.3, 0, 0, 5.0, 0, 5.0]

    def test_pin_lists_single(self, tv_fixture, single_one_pin_fixture, single_multi_pin_fixture):
        single_tv_fixture = tv_fixture(input_cmds=single_one_pin_fixture, output_cmds=single_multi_pin_fixture)
        ret = single_tv_fixture.pin_lists(5.0)
        
        assert isinstance(ret, dict)
        assert ret["input_pins"] == [2, 20, 18]
        assert ret["output_pins"] == [2, 16, 20, 12, 18, 1]
        assert ret["voltage_in"] == [2.5, 5.0, 0]


    def test_pin_lists_serial(self, tv_fixture, serial_one_pin_fixture, serial_multi_pin_fixture):
        serial_tv_fixture = tv_fixture(input_cmds=serial_one_pin_fixture, output_cmds=serial_multi_pin_fixture)
        ret = serial_tv_fixture.pin_lists(5.0)
        
        assert isinstance(ret, dict)
        assert ret["input_pins"] == [2, 20]
        assert ret["output_pins"] == [2, 1, 20, 12, 5]
        assert ret["voltage_in"] == ["0b100RF", "0b100"]

class TestTestVectorComparisons:
    """Tests functions that compare results to expected values."""
    def test_compare_map(self, tv_fixture, map_fixture):
        map_true_tv_fixture = tv_fixture(input_cmds=map_fixture, output_cmds=map_fixture)
        map_true_tv_fixture.simulated_test(None, True)

        for vcc in map_true_tv_fixture.global_params["VCC Voltage"]:
            for cmd in map_fixture:
                assert map_true_tv_fixture._compare_map(cmd, vcc) == True

        map_rand_tv_fixture = tv_fixture(input_cmds=map_fixture, output_cmds=map_fixture)
        map_rand_tv_fixture.simulated_test(42, False)

        for vcc in map_rand_tv_fixture.global_params["VCC Voltage"]:
            for cmd in map_fixture:
                assert map_rand_tv_fixture._compare_map(cmd, vcc) == False

    def test_compare_single(self, tv_fixture, single_one_pin_fixture, single_multi_pin_fixture):
        single_true_tv_fixture = tv_fixture(input_cmds=single_one_pin_fixture, output_cmds=single_multi_pin_fixture)
        single_true_tv_fixture.simulated_test(None, True)

        for vcc in single_true_tv_fixture.global_params["VCC Voltage"]:
            for cmd in single_multi_pin_fixture:
                assert single_true_tv_fixture._compare_single(cmd, vcc) == True

        single_rand_tv_fixture = tv_fixture(input_cmds=single_one_pin_fixture, output_cmds=single_multi_pin_fixture)
        single_rand_tv_fixture.simulated_test(42, False)

        for vcc in single_rand_tv_fixture.global_params["VCC Voltage"]:
            for cmd in single_multi_pin_fixture:
                assert single_rand_tv_fixture._compare_single(cmd, vcc) == False

    def test_compare_serial(self, tv_fixture, serial_one_pin_fixture, serial_multi_pin_fixture):
        pass
    
    def test_compare_results(self):
        pass
