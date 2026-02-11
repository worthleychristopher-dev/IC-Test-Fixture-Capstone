import pytest
import testvector
from testvector import LogicMapping

@pytest.fixture
def reset_testvector():
    """
        set all class attributes of TestVector None before every and after every test
    """
    # clear before test
    testvector.TestVector.update_global_params(None)
    testvector.TestVector.update_pin_map(None)
    yield
    # clear after test
    testvector.TestVector.update_global_params(None)
    testvector.TestVector.update_pin_map(None)

# updates TestVector class attributes for tests when called
@pytest.fixture
def set_testvector_pin_map(reset_testvector):
    testvector.TestVector.update_pin_map({"A": 3, "Y": 8})

@pytest.fixture
def set_testvector_voltage(reset_testvector):
    testvector.TestVector.update_global_params({"VCC Voltage": "5V"})

@pytest.fixture
def set_testvector_thresholds(reset_testvector):
    testvector.TestVector.update_global_params({"Output Low": 0.3, "Output High": 3.4})


def test_testvector_IOCommand():
    io_cmd  = testvector.IOCommand([1,3,2], ["H"], "3.3V", LogicMapping.map)
    # test by numeric index
    assert io_cmd[0] == [1,3,2]
    assert io_cmd[1] == ["H"]
    assert io_cmd[2] == "3.3V"
    assert io_cmd[3] == LogicMapping.map

    # test by name index
    assert io_cmd.pins == [1,3,2]
    assert io_cmd.pin_vals == ["H"]
    assert io_cmd.volt_type == "3.3V"
    assert io_cmd.cmd_type == LogicMapping.map

def test_testvector_classattr(reset_testvector):
    # initially None at first
    assert testvector.TestVector.global_params == None
    assert testvector.TestVector.pin_map == None

    testvector.TestVector.update_global_params({"VCC Voltage": "5V", "Output Low": 2.8})
    testvector.TestVector.update_pin_map({"A": 5, "CLK": 20})
    assert testvector.TestVector.global_params == {"VCC Voltage": "5V", "Output Low": 2.8}
    assert testvector.TestVector.pin_map == {"A": 5, "CLK": 20}

    testvector.TestVector.update_global_params({"Output High": 3.4, "VCC Pin": 6})
    testvector.TestVector.update_pin_map({"Q": 2, "QNot": 1})
    assert testvector.TestVector.global_params == {"Output High": 3.4, "VCC Pin": 6}
    assert testvector.TestVector.pin_map == {"Q": 2, "QNot": 1}

@pytest.mark.parametrize(
    "pin, expected",
    [
        (9, 9),
        ("A", 3),
        ("Y", 8)
    ]
)
def test_testvector_get_pin(set_testvector_pin_map, pin, expected):
    assert testvector.TestVector.get_pin(pin) == expected

@pytest.mark.parametrize(
    "logic, volt_type, expected",
    [
        (0, "2.5V", 0),
        ("L", "1.8V", 0),
        ("X", "5V", 0),
        ("H", "3.3V", "3.3V"),
        (1, None, "5V")
    ]
)
def test_testvector_get_voltage(set_testvector_voltage, logic, volt_type, expected):
    assert testvector.TestVector.get_voltage(logic, volt_type) == expected
    
@pytest.mark.parametrize(
    "adc_val, isInt, expected",
    [
        (0.21, False, "L"),
        (0.21, True, 0),
        (2.5, False, "U"),
        (2.5, True, "U"),
        (4.2, False, "H"),
        (4.2, True, 1)
    ]
)
def test_testvector_logic_from_thld(set_testvector_thresholds, adc_val, isInt, expected):
    assert testvector.TestVector.logic_from_thld(adc_val, isInt) == expected
