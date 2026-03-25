import pytest
from ICTestFixture.core import testvector

@pytest.fixture
def resetTestvector():
    """
        set all class attributes of TestVector None before every and after every test
    """
    # clear before test
    testvector.TestVector.updateGlobalParams(None)
    testvector.TestVector.updatePinMap(None)
    yield
    # clear after test
    testvector.TestVector.updateGlobalParams(None)
    testvector.TestVector.updatePinMap(None)

# updates TestVector class attributes for tests when called
@pytest.fixture
def setTestvectorPinMap(resetTestvector):
    testvector.TestVector.updatePinMap({"A": 3, "Y": 8})

@pytest.fixture
def setTestvectorVoltage(resetTestvector):
    testvector.TestVector.updateGlobalParams({"VCC Voltage": ["5V"]})

@pytest.fixture
def setTestvectorThresholds(resetTestvector):
    testvector.TestVector.updateGlobalParams({"Output Low": [0.3], "Output High": [3.4]})


def testTestvectorIOCommand():
    ioCmd  = testvector.IOCommand([1,3,2], ["H"], "3.3V", testvector.LogicMapping.Map)
    # test by numeric index
    assert ioCmd[0] == [1,3,2]
    assert ioCmd[1] == ["H"]
    assert ioCmd[2] == "3.3V"
    assert ioCmd[3] == testvector.LogicMapping.Map

    # test by name index
    assert ioCmd.pins == [1,3,2]
    assert ioCmd.pinVals == ["H"]
    assert ioCmd.voltType == "3.3V"
    assert ioCmd.cmdType == testvector.LogicMapping.Map

def testTestvectorClassattr(resetTestvector):
    # initially None at first
    assert testvector.TestVector.globalParams == None
    assert testvector.TestVector.pinMap == None

    testvector.TestVector.updateGlobalParams({"VCC Voltage": "5V", "Output Low": 2.8})
    testvector.TestVector.updatePinMap({"A": 5, "CLK": 20})
    assert testvector.TestVector.globalParams == {"VCC Voltage": "5V", "Output Low": 2.8}
    assert testvector.TestVector.pinMap == {"A": 5, "CLK": 20}

    testvector.TestVector.updateGlobalParams({"Output High": 3.4, "VCC Pin": 6})
    testvector.TestVector.updatePinMap({"Q": 2, "QNot": 1})
    assert testvector.TestVector.globalParams == {"Output High": 3.4, "VCC Pin": 6}
    assert testvector.TestVector.pinMap == {"Q": 2, "QNot": 1}

@pytest.mark.parametrize(
    "pin, expected",
    [
        (9, 9), # int input
        ("A", 3), # pin id input
        ("Y", 8) # pin id input 2
    ]
)
def testTestvectorGetPin(setTestvectorPinMap, pin, expected):
    assert testvector.TestVector.getPin(pin) == expected

@pytest.mark.parametrize(
    "logic, voltType, expected",
    [
        (0, "2.5V", 0), # Logic 0
        ("L", "1.8V", 0), # Logic L
        ("X", "5V", 0), # X defaults to Logic L
        ("H", "3.3V", "3.3V"), # specified high voltage
        (1, None, "5V") # default to VCC Voltage
    ]
)
def testTestvectorGetVoltage(setTestvectorVoltage, logic, voltType, expected):
    assert testvector.TestVector.getVoltage(logic, voltType, paramIdx=0) == expected
    
@pytest.mark.parametrize(
    "adcVal, isInt, expected",
    [
        (0.21, False, "L"), # below low threshold, not int
        (0.21, True, 0), # below low threshold, int
        (2.5, False, "U"), # between thresholds, always U
        (2.5, True, "U"),
        (4.2, False, "H"), # above high threshold, not int
        (4.2, True, 1) # above high threshold, int
    ]
)
def testTestvectorLogicFromThld(setTestvectorThresholds, adcVal, isInt, expected):
    assert testvector.TestVector.logicFromThld(adcVal, isInt, paramIdx=0) == expected
