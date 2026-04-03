import pytest

from ICTestFixture.device import test_vector

@pytest.fixture
def tv_fixture():
    # factory method to dynamically create a test fixture
    def _create(*, input_cmds, output_cmds):
        # input/output cmds must be passed by name
        return test_vector.TestVector(
            global_params=None,
            pin_map={"A": 1, "B": 20},
            inputs=input_cmds,
            outputs=output_cmds,
            test_name="Test Value/Compare functions"
        )
    return _create

@pytest.fixture
def map_one_pin_fixture():
    pass

@pytest.fixture
def map_multi_pin_fixture():
    pass

@pytest.fixture
def single_one_pin_fixture():
    pass

@pytest.fixture
def single_multi_pin_fixture():
    pass

@pytest.fixture
def serial_one_pin_fixture():
    pass

@pytest.fixture
def serial_multi_pin_fixture():
    pass

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
    def test_map(self, tv_fixture, map_one_pin_fixture, map_multi_pin_fixture):
        in_pins_one = []
        v_in_one = []

        map_one_fixture = tv_fixture(input_cmds=list(map_one_pin_fixture))
        map_one_fixture._map(
            map_one_pin_fixture,
            in_pins_one,
            v_in_one,
            5.0    
        )

        assert in_pins_one == 
        assert v_in_one ==

        in_pins_multi = []
        v_in_multi = []

        map_multi_fixture = tv_fixture(input_cmds=list(map_multi_pin_fixture))
        map_multi_fixture._map(
            map_multi_pin_fixture,
            in_pins_multi,
            v_in_multi,
            5.0    
        )

        assert in_pins_multi ==
        assert v_in_multi ==

    def test_single(self, tv_fixture, single_one_pin_fixture, single_multi_pin_fixture):
        in_pins_one = []
        v_in_one = []

        single_one_fixture = tv_fixture(input_cmds=list(single_one_pin_fixture))
        single_one_fixture._single(
            single_one_pin_fixture,
            in_pins_one,
            v_in_one,
            5.0    
        )

        assert in_pins_one ==
        assert v_in_one ==

        in_pins_multi = []
        v_in_multi = []

        single_multi_fixture = tv_fixture(input_cmds=list(single_multi_pin_fixture))
        single_multi_fixture._single(
            single_multi_pin_fixture,
            in_pins_multi,
            v_in_multi,
            5.0    
        )

        assert in_pins_multi ==
        assert v_in_multi ==

    def test_serial(self, tv_fixture, serial_one_pin_fixture, serial_multi_pin_fixture):
        in_pins_one = []
        v_in_one = []

        serial_one_fixture = tv_fixture(input_cmds=list(serial_one_pin_fixture))
        serial_one_fixture._serial(
            serial_one_pin_fixture,
            in_pins_multi,
            v_in_multi,
            5.0    
        )

        assert in_pins_one ==
        assert v_in_one ==

        in_pins_multi = []
        v_in_multi = []

        serial_multi_fixture = tv_fixture(input_cmds=list(serial_multi_pin_fixture))
        serial_multi_fixture._serial(
            serial_multi_pin_fixture,
            in_pins_multi,
            v_in_multi,
            5.0    
        )

        assert in_pins_multi ==
        assert v_in_multi ==

    def test_pin_lists(self, tv_fixture):
        pass

class TestTestVectorComparisons:
    """Tests functions that compare results to expected values."""
    def test_compare_map(self, tv_fixture, map_one_pin_fixture, map_multi_pin_fixture):
        pass

    def test_compare_single(self, tv_fixture, single_one_pin_fixture, single_multi_pin_fixture):
        pass

    def test_compare_serial(self, tv_fixture, serial_one_pin_fixture, serial_multi_pin_fixture):
        pass

    def test_compare_results(self):
        pass
