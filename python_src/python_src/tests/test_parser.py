import pytest
from ICTestFixture.core import parser
from ICTestFixture.core import testvector
import pathlib # for cross-platform file paths
from contextlib import nullcontext as doesNotRaise # no exception raised

def assertMsg(exc, *expParts):
    """
        helper function, assert exc msg contains expected parts
    """
    if hasattr(exc, "value"):  # normal exception
        msg = str(exc.value)
    elif hasattr(exc, "__iter__"):  # WarningsChecker or list of warnings
        # take all warnings messages
        msg = " ".join(str(w.message) for w in exc)
    else:
        raise TypeError(f"Unknown exc type: {type(exc)}")

    for part in expParts:
        if isinstance(part, (list, tuple, set)):
            for item in part:
                assert str(item) in msg
        else:
            assert str(part) in msg

@pytest.fixture
def baseCheckType():
    return {
        "expKeys": {"VCC Pin", "VCC Voltage"},
        "gotKeys": {"VCC Pin", "VCC Voltage"},
        "section": "section"
    }

@pytest.fixture
def basePinMap():
    return {
        "A": 2,
        "B": 9,
        "Y": 1
    }

@pytest.fixture
def baseTruthTable():
    return [
        {"A": "L", "B": "L", "Y": "L"},
        {"A": "L", "B": "H", "Y": "L"},
        {"A": "H", "B": "L", "Y": "L"},
        {"A": "H", "B": "H", "Y": "H"}
    ]

@pytest.fixture
def baseGlobalParams():
    return {
        "VCC Pin": 16,
        "GND Pin": 8,
        "VCC Voltage": "5V",
        "Output Low": 0.2,
        "Output High": 3.81
    }

@pytest.fixture
def baseInput_Single():
    return {
        # without voltage
        1: "H",       # single int pin
        "A": "L",     # single pin ref
        "1,2,3": "H", # multiple int pins
        "A,B": "H",   # multiple pin refs
        # with voltage
        3: "H 5V",
        "Y": "L 3.3V",
        "1,2": "H 1.8V",
        "Y,B": "L 2.5V"
    }

@pytest.fixture
def baseOutput_Single():
    return {
        # without voltage
        1: "L",
        "A": "T",
        "1,2,3": "Z",
        "A,B": "H",
        # with voltage
        2: "H 5V",
        "Y": "X 1.8V",
        "4,5": "L 2.5V",
        "Y,B": "S 3.3V"
    }

@pytest.fixture
def baseInput_Multi():
    return {
        # without voltage
        "1,2": 0b11,   # int pins and binary value
        "3,4,5": "H,L,H", # int pins and logic value
        "A,B": "L,H",     # pin refs and logic value
        "B,A": 0b01,    # pin refs and binary value
        # with voltage
        "6,7,8": "0b101 2.5V",
        "9,10,11": "H,L,H 4.5V",
        "Y,B": "L,H 5V",
        "A,Y": "0b01 3.3V"
    }

@pytest.fixture
def baseOutput_Multi():
    return {
        # without voltage
        "15,20": 0b11,
        "5,8": "H,X",
        "Y,B": "Z,L",
        "A,19": 0b01,
        # with voltage
        "A,19": "0b10 5V",
        "2,B": "H,X 3.3V",
        "A,B": "H,H 2.5V",
        "Y,A": "L,T 1.8V"
    }

@pytest.fixture
def baseInput_TruthTable():
    return {
        1: "A",   # int pin
        "B": "B"  # pin ref
    }

@pytest.fixture
def baseOutput_TruthTable():
    return {
        1: "Y",
        "Y": "Y"
    }

@pytest.mark.parametrize(
    "val, expTypes, expectation", [ 
        (2.3, (float,), doesNotRaise()),          # one type specified
        ("A", (str, int), doesNotRaise()),        # multiple types specified
        ("B", (int,), pytest.raises(TypeError)),    # one type specified, error
        (2.3, (str, int), pytest.raises(TypeError)) # multiple types specified, error
    ]
)
def testParserCheckType(val, expTypes, expectation):
    with expectation as exc:
        parser.checkType(val, expTypes, "section", "key")
    
    if exc is not None:
        # convert expTypes to string repr
        typesStr = [expType.__name__ for expType in expTypes]
        # msg include section of error, expected type(s), and got type
        assertMsg(exc, "Expected type", "section", typesStr, type(val).__name__)

@pytest.mark.parametrize(
    "pin, expectation", [
        (parser.MAX_PINS-1, doesNotRaise()),          # pin in range
        (1, doesNotRaise()),                          # minimum pin value
        (parser.MAX_PINS, doesNotRaise()),            # maximum pin value
        (0, pytest.raises(ValueError)),                 # < 1
        (parser.MAX_PINS+1, pytest.raises(ValueError))  # > MAXPINS
    ]
)
def testParserCheckPin(pin, expectation):
    with expectation as exc:
        parser.checkPin(pin, "section", "key")

    if exc is not None:
        rangeStr = f"Pin number must be between 1 and {parser.MAX_PINS}"
        # msg includes rangeStr, section of error, and pin
        assertMsg(exc, rangeStr, "section[key]", pin)

# all supported voltage references
@pytest.mark.parametrize(
    "voltage, expectation", [
        ("5V", doesNotRaise()),
        ("2.3V", pytest.raises(ValueError)) 
    ]
)
def testParserCheckVoltage(voltage, expectation):
    with expectation as exc:
        parser.checkVoltage(voltage, "section", "key")

    if exc is not None:
        assertMsg(exc, "Voltage must be one of supported voltages", parser.SUPPORTED_VOLTAGES, voltage)

class TestParserCheckKeys:
    @pytest.mark.parametrize(
        "optKeys, addKey", [
            (None, None),               # explicit no opt keys 
            ({"CLK Freq"}, None),       # opt keys, but none used
            ({"CLK Freq"}, "CLK Freq")  # opt keys used
        ]
    )
    def testValidKeyCombos(self, baseCheckType, optKeys, addKey):
        baseCheckType["optKeys"] = optKeys
        if addKey is not None:
            baseCheckType["gotKeys"].add(addKey)
        parser.checkKeys(**baseCheckType)

    @pytest.mark.parametrize(
        "popKeys", [
            ("VCC Pin",),               # one key missing
            ("VCC Pin", "VCC Voltage")  # multiple keys missing
        ]
    )
    def testMissingKeys(self, baseCheckType, popKeys):
        baseCheckType["gotKeys"].difference_update(popKeys) # removes keys from an iterable
        with pytest.raises(parser.MissingKeys) as exc:
            parser.checkKeys(optKeys=None, **baseCheckType)
        # msg includes missing key(s) and section of error
        assertMsg(exc, "Missing required keys", popKeys, baseCheckType["section"])

    @pytest.mark.parametrize(
        "addKeys", [
            ("GND Pin",),               # one unknown key
            ("GND Pin", "GND Voltage")  # multiple unknown keys
        ]
    )
    def testUserWarning(self, baseCheckType, addKeys):
        baseCheckType["gotKeys"].update(addKeys)
        with pytest.warns(UserWarning) as exc:
            parser.checkKeys(optKeys=None, **baseCheckType)
        # msg includes unexpected key (GND Pin) and section of error
        assertMsg(exc, "Ignoring unexpected keys", addKeys, baseCheckType["section"])

class TestParserPinMap:
    # private test fixtire for class
    @pytest.fixture(autouse=True)
    def pinMapTestFixture(self, basePinMap):
        self.pinMapTestFixture = {
            "pinMap": basePinMap,
            "vccPin": 16,
            "gndPin": 8
        }

    def testValidPinMap(self):
        parser.parsePinMap(**self.pinMapTestFixture)

    @pytest.mark.parametrize(
        "pinRef, pinVal", [
            (2, 5),     # non-str pin id
            ("A", 2.4)  # non-int pin value
        ]
    )
    def testInvalidPinEntry(self, pinRef, pinVal):
        self.pinMapTestFixture["pinMap"][pinRef] = pinVal
        with pytest.raises(TypeError):
            parser.parsePinMap(**self.pinMapTestFixture)

    @pytest.mark.parametrize(
        "pinVal", [
            -1,                   # < 1 (minimum)
            parser.MAX_PINS + 1   # > MAXPINS
        ]
    )
    def testPinOutOfRange(self, pinVal):
        self.pinMapTestFixture["pinMap"]["A"] = pinVal
        with pytest.raises(ValueError):
            parser.parsePinMap(**self.pinMapTestFixture)

    @pytest.mark.parametrize(
        "pinRef, errMsg", [
            ("gndPin", "Pin number must not be same as GND Pin"),    # pin is same as GND
            ("vccPin", "Pin number must not be same as VCC Pin"),    # pin is same as VCC
        ]
    )
    def testPowerPinConflicts(self, pinRef, errMsg):
        self.pinMapTestFixture["pinMap"]["B"] = self.pinMapTestFixture[pinRef]
        with pytest.raises(ValueError) as exc:
            parser.parsePinMap(**self.pinMapTestFixture)
        # msg includes conflict type, conflicting pin, section of error
        assertMsg(exc, errMsg, self.pinMapTestFixture["pinMap"]["B"], "Pin Map[B]")

    def testSamePinConflict(self):
        self.pinMapTestFixture["pinMap"]["B"] = self.pinMapTestFixture["pinMap"]["A"]
        with pytest.raises(ValueError) as exc:
            parser.parsePinMap(**self.pinMapTestFixture)
        # msg includes conflict type, conflicting pin
        assertMsg(exc, "Multiple names map to same pin", self.pinMapTestFixture["pinMap"]["A"])

class TestParserTruthTable:
    def testValidTruthTable(self, baseTruthTable):
        tt = parser.parseTruthTable(baseTruthTable)
        
        assert isinstance(tt, dict)
        assert len(tt) == 3
        assert tt["A"] == ["L", "L", "H", "H"]
        assert tt["B"] == ["L", "H", "L", "H"]
        assert tt["Y"] == ["L", "L", "L", "H"]

    def testAllLogic(self, baseTruthTable):
        for logic in parser.TRUTH_TABLE_LOGIC:
            baseTruthTable[0]["A"] = logic

            tt = parser.parseTruthTable(baseTruthTable)
            assert len(tt) == 3
            assert tt["A"] == [logic ,"L", "H", "H"]
            assert tt["B"] == ["L", "H", "L", "H"]
            assert tt["Y"] == ["L", "L", "L", "H"]

    def testNonStrColName(self, baseTruthTable):
        baseTruthTable[0][5] = "L"
        with pytest.raises(TypeError):
            parser.parseTruthTable(baseTruthTable)

    def testInconsistentNumCols(self, baseTruthTable):
        baseTruthTable[0]["C"] = "L"
        with pytest.raises(parser.TableParseError) as exc:
            parser.parseTruthTable(baseTruthTable)
        # msg includes secion of error
        assertMsg(exc, "Inconsistent number of columns", "Truth Table")

    def testInconsistentColNames(self, baseTruthTable):
        for i in range(len(baseTruthTable)):
            if i == 0: baseTruthTable[i]["C"] = "H"
            else: baseTruthTable[i]["D"] = "L"
        with pytest.raises(parser.TableParseError) as exc:
            parser.parseTruthTable(baseTruthTable)
        # msg includes section of error
        assertMsg(exc, "Inconsistent column names", "Truth Table")

    def testInvalidLogic(self, baseTruthTable):
        baseTruthTable[0]["A"] = "C"
        with pytest.raises(ValueError) as exc:
            parser.parseTruthTable(baseTruthTable)
        # msg includes invalid logic (C), column name (A), expected logic, section of error
        assertMsg(exc, "Invalid logic", "C", "A", parser.TRUTH_TABLE_LOGIC, "Truth Table")

class TestParserGlobalParams:
    def testValidGlobalParams(self, baseGlobalParams):
        parser.parseGlobalParams(baseGlobalParams)

    def testValidGlobalParamsWithList(self, baseGlobalParams):
        baseGlobalParams["VCC Voltage"] = ["5V", "2.5V"]
        baseGlobalParams["Output Low"] = [0.33, 0.2]
        baseGlobalParams["Output High"] = [3.84, 4.5]
        parser.parseGlobalParams(baseGlobalParams)

    def testValidGlobalParamsWithOptKeys(self, baseGlobalParams):
        baseGlobalParams["CLK Freq"] = -1
        baseGlobalParams["Input Low"] = 0.2
        baseGlobalParams["Input High"] = 4
        parser.parseGlobalParams(baseGlobalParams)

    def testValidWithOneThreshold(self, baseGlobalParams):
        baseGlobalParams["Input High"] = 3
        parser.parseGlobalParams(baseGlobalParams)

    def testMissingKeysGlobalParams(self, baseGlobalParams):
        baseGlobalParams.pop("VCC Pin")
        with pytest.raises(parser.MissingKeys):
            parser.parseGlobalParams(baseGlobalParams)

    @pytest.mark.parametrize(
        "param, val", [
            ("VCC Pin", 16.0),      # non int VCC Pin
            ("GND Pin", "8"),       # non int GND Pin
            ("Output Low", "0.3"),  # non int/float threshold
            ("CLK Freq", [1.2])     # non int/float/str clk
        ]
    )
    def testInvalidTypesForParams(self, baseGlobalParams, param, val):
        baseGlobalParams[param] = val
        with pytest.raises(TypeError):
            parser.parseGlobalParams(baseGlobalParams)

    @pytest.mark.parametrize(
        "key, val", [
            ("VCC Pin", 0),                     # VCC Pin < 1 (min)
            ("GND Pin", -2),                    # GND Pin < 1 (min)
            ("VCC Pin", parser.MAX_PINS + 1),   # VCC Pin > MAXPINS
            ("GND Pin", parser.MAX_PINS + 2)    # GND Pin > MAXPINS
        ]
    )
    def testPowerPinsOutOfRange(self, baseGlobalParams, key, val):
        baseGlobalParams[key] = val
        with pytest.raises(ValueError):
            parser.parseGlobalParams(baseGlobalParams)

    def testVccPinEqualGndPin(self, baseGlobalParams):
        baseGlobalParams["VCC Pin"] = baseGlobalParams["GND Pin"]
        with pytest.raises(ValueError) as exc:
            parser.parseGlobalParams(baseGlobalParams)
        # msg includes VCC/GND conflict pin
        assertMsg(exc, "VCC Pin and GND Pin are the same", baseGlobalParams["VCC Pin"])

    def testUnsupportedVccVoltage(self, baseGlobalParams):
        baseGlobalParams["VCC Voltage"] = "2.2V"
        with pytest.raises(ValueError):
            parser.parseGlobalParams(baseGlobalParams)

    def testInconsistentNumVoltageAndThresholds(self, baseGlobalParams):
        baseGlobalParams["VCC Voltage"] = ["5V", "3.3V"]
        with pytest.raises(ValueError) as exc:
            parser.parseGlobalParams(baseGlobalParams)
        # msg includes the got lengths of VCC Voltage and thresholds, and section of error
        assertMsg(exc, "Inconsistent number of values for VCC Voltage and voltage thresholds", {1, 2}, "Global Parameters")

    @pytest.mark.parametrize(
        "param1, val1, param2, val2", [
            ("Output Low", 3.4, "Output High", 3.3),                    # output low >= high
            ("Input Low", 4.5, "Input High", 4.5)                      # input low >= high
        ]
    )
    def testLowGreaterThanHighThreshold(self, baseGlobalParams, param1, val1, param2, val2):
        baseGlobalParams[param1] = val1
        baseGlobalParams[param2] = val2
        io = param1.split(" ")[0]
        with pytest.raises(ValueError) as exc:
            parser.parseGlobalParams(baseGlobalParams)
        # msg includes io type (Input/Output), and values
        assertMsg(exc, f"Voltage {io} Low is greater than or equal to Voltage {io} High", val1, val2)

    def testLowGreaterThanHighThresholdList(self, baseGlobalParams):
        baseGlobalParams["VCC Voltage"] = ["5V", "3.3V"] # need to set VCC Voltage to have same length as thresholds
        baseGlobalParams["Output Low"] = [0.3, 5.6]
        baseGlobalParams["Output High"] = [1.9, 4.5]
        with pytest.raises(ValueError) as exc:
            parser.parseGlobalParams(baseGlobalParams)
        # msg includes io type (Output), and values
        assertMsg(exc, f"Voltage Output Low is greater than or equal to Voltage Output High", 5.6, 4.5)

    @pytest.mark.skip(reason="To be determined CLK Range")
    @pytest.mark.parametrize(
        "inputClk", [
            -1,       # int clk input
            -1.0,     # float clk input
            "1 k",    # str clk input
            "1.1 M"   # str clk input 2
        ]
    )
    def testClkFreq(self, baseGlobalParams, inputClk):
        baseGlobalParams["CLK Freq"] = inputClk
        parser.parseGlobalParams(baseGlobalParams)

    @pytest.mark.skip(reason="To be determined CLK Range")
    @pytest.mark.parametrize(
        "inputClk", [
            (),
            ()
        ]
    )
    def testClkFreqInvalidStr(self, baseGlobalParams, inputClk):
        baseGlobalParams["CLK Freq"] = inputClk
        with pytest.raises(ValueError) as exc:
            parser.parseGlobalParams(baseGlobalParams)
        # msg includes inputClk val
        assertMsg(exc, "Invalid format for CLK Freq", inputClk)

    @pytest.mark.skip(reason="To be determined CLK Range")
    @pytest.mark.parametrize(
        "inputClk", [
            (),
            (),
            (),
            ()
        ]
    )
    def testClkFreqOutOfRange(self, baseGlobalParams, inputClk):
        baseGlobalParams["CLK Freq"] = inputClk
        with pytest.raises(ValueError) as exc:
            parser.parseGlobalParams(baseGlobalParams)

        assertMsg(exc, 
            f"CLK Freq must be between or equal to {parser.Clock.MIN} and {parser.Clock.MAX}",
            inputClk,
           "\"Test Parameters[CLK Freq]\""
        )

class TestParserTests:
    @pytest.fixture(autouse=True)
    def testsTestFixture(self, basePinMap, baseTruthTable):
        self.testsTestFixture = {
            "pinMap": basePinMap,
            "truthTable": parser.parseTruthTable(baseTruthTable)
        }
    
    @pytest.fixture(autouse=True)
    def testvectorAttr(self, baseGlobalParams, basePinMap):
        # set TestVector class attributes for tests
        # need to wrap vcc voltage, and thresholds into list because parseGlobalParams does that
        baseGlobalParams["VCC Voltage"] = ['5V']
        baseGlobalParams["Output Low"] = [0.3]
        baseGlobalParams["Output High"] = [3.4]
        testvector.TestVector.updateGlobalParams(baseGlobalParams)
        testvector.TestVector.updatePinMap(basePinMap)

    @pytest.mark.parametrize(
        "inputFixture, outputFixture, testName", [
            ("baseInput_Single", "baseOutput_Single", "Single"),
            ("baseInput_Multi", "baseOutput_Multi", "Map"),
            ("baseInput_TruthTable", "baseOutput_TruthTable", "Truth Table")
        ]
    )
    def testValidTests(self, request, inputFixture, outputFixture, testName):
        testInput = request.getfixturevalue(inputFixture)
        testOutput = request.getfixturevalue(outputFixture)
        test = {testName: {"Inputs": testInput, "Outputs": testOutput}}
        testVec = parser.parseTests(test, **self.testsTestFixture)
        
        assert len(testVec) == 1
        assert isinstance(testVec[0], parser.TestVector)
        assert len(testVec[0].inputs) == len(testInput)
        assert len(testVec[0].outputs) == len(testOutput)
        assert testVec[0].testName == testName

    def testMissingKeysTests(self):
        with pytest.raises(parser.MissingKeys):
            parser.parseTests(tests={"MissingKey Test": {"Inputs": {1: "H"}}}, **self.testsTestFixture)

class TestParserIO:
    # private test fixture for class
    @pytest.fixture(autouse=True)
    def ioTestFixture(self, basePinMap, baseTruthTable):
        self.ioTestFixture = {
            "pinMap": basePinMap,
            "truthTable": parser.parseTruthTable(baseTruthTable),
            "validLogic": parser.INPUT_LOGIC,
            "testName": "testIo"
        }

    @pytest.mark.parametrize(
        "fixtureName", [
            "baseInput_Single",
            "baseInput_Multi",
            "baseInput_TruthTable",
            "baseOutput_Single",
            "baseOutput_Multi",
            "baseOutput_TruthTable"
        ]
    )
    def testValidIo(self, request, fixtureName):
        # request is from PyTest library, get test fixtures by name
        io = request.getfixturevalue(fixtureName)
        # change validLogic to OUTPUTLOGIC from the default INPUTLOGIC
        self.ioTestFixture["validLogic"] = parser.INPUT_LOGIC if "input" in fixtureName else parser.OUTPUT_LOGIC
        ioCmds = parser.parseTestIo(io=io, **self.ioTestFixture)
        assert len(ioCmds) == len(io)

        # verify commands are written correctly by looping each entry separetly
        for pins, pinVals in io.items():
            tokens = pinVals.split(" ")
            # make int if a digit, otherwise get from pin map
            expPins = [
                int(pin) if pin.isdigit() else pin
                for pin in str(pins).split(",")
            ]
            # convert ints, otherwise remain as str
            expVals = [
                int(val, 0) if val.startswith("0b") or val.isdigit() else val
                for val in str(tokens[0]).split(",")
            ]
            expVolt = tokens[-1] if len(tokens) > 1 else None
            expCmd = None

            logicMapType = fixtureName.split("_")[-1]
            if logicMapType == "Single":
                expCmd = parser.LogicMapping.Single
            elif logicMapType == "Multi":
                expCmd = parser.LogicMapping.Map
            elif logicMapType == "TruthTable":
                expCmd = parser.LogicMapping.TruthTable
            else:
                raise NotImplementedError(
                    f"No such logic mapping implemented: {logicMapType}"
                )
            
            # replace reference with value from truth table
            if expCmd == parser.LogicMapping.TruthTable:
                expVals = self.ioTestFixture["truthTable"][expVals[0]] # take out list wrapper for expVals

            ret = parser.parseTestIo(io={pins: pinVals}, **self.ioTestFixture)
            assert len(ret) == 1
            assert ret[0].pins == expPins
            assert ret[0].pinVals == expVals
            assert ret[0].voltType == expVolt
            assert ret[0].cmdType == expCmd

    def testAllValidLogic(self):
        for logic in parser.INPUT_LOGIC:
            parser.parseTestIo({1: logic}, None, None, parser.INPUT_LOGIC, f"Input: {logic}")

        for logic in parser.OUTPUT_LOGIC:
            parser.parseTestIo({1: logic}, None, None, parser.OUTPUT_LOGIC, f"Output: {logic}")
    
    def testInvalidLogic(self):
        with pytest.raises(ValueError) as exc1:
            parser.parseTestIo({1: "LOW"}, None, None, parser.INPUT_LOGIC, "Test LOW")
        # msg includes pin, value, expected logic, and section of error
        assertMsg(exc1, "Invalid logic/reference", 1, "LOW", parser.INPUT_LOGIC, "\"Tests[Test LOW]\"")

        with pytest.raises(ValueError) as exc2:
            parser.parseTestIo({1: "HIGH"}, None, None, parser.OUTPUT_LOGIC, "Test HIGH")
        # msg includes pin, value, expected logic, and section of error
        assertMsg(exc2, "Invalid logic/reference", 1, "HIGH", parser.OUTPUT_LOGIC, "\"Tests[Test HIGH]\"")
        
    @pytest.mark.parametrize(
        "io,", [
            {2.6: "L 3.3V"},    # pin not int or str
            {1: 2.74}           # pin val not int or str
        ]
    )
    def testInvalidTypesTests(self, io):
        with pytest.raises(TypeError):
            parser.parseTestIo(io=io, **self.ioTestFixture)

    @pytest.mark.parametrize(
        "io", [
            {0: "L"},                 # pin < 1
            {parser.MAX_PINS+1: 0b1}, # pin > MAXPINS
            {"C": "H, 5V"},           # pinRef < 1
            {"D": "0b11, 3.3V"}       # pinRef > MAXPINS
        ]
    )
    def testPinOutOfRange(self, io):
        self.ioTestFixture["pinMap"]["C"] = -3
        self.ioTestFixture["pinMap"]["D"] = parser.MAX_PINS+1
        with pytest.raises(ValueError):
            parser.parseTestIo(io=io, **self.ioTestFixture)

    def testMultipleIntValues(self):
        with pytest.raises(parser.TestParseError) as exc:
            parser.parseTestIo(io={1: "0b1,0b0"}, **self.ioTestFixture)
        # msg includes pinVals, and section of error
        assertMsg(exc, "Only 1 integer input allowed for input mapping", "0b1", "0b0", self.ioTestFixture["testName"])

    def testPinValueGreaterThanMax(self):
        with pytest.raises(ValueError) as exc:
            parser.parseTestIo(io={"1,2,3": 0b1011}, **self.ioTestFixture)
        # msg includes length of pins, maxixmum possible value, pins, and section of error
        assertMsg(exc, 3, 7, 0b1011, self.ioTestFixture["testName"])

    def testLogicMappingCombinations(self, baseInput_Single, baseInput_TruthTable):
        inputIo = baseInput_Single | baseInput_TruthTable
        with pytest.raises(parser.TestParseError) as exc:
            parser.parseTestIo(io=inputIo, **self.ioTestFixture)
        # msg includes section of error
        assertMsg(exc, "Cannot mix truth table mapping with any other pin mapping", self.ioTestFixture["testName"])

class TestParserParse:
    @pytest.fixture
    def expGlobalParams(self):
        return {
            "VCC Pin": 14,
            "GND Pin": 7,
            "VCC Voltage": ["5V"],
            "Output Low": [0.33],
            "Output High": [3.84]
        }

    @pytest.fixture
    def expPinMap(self):
        return {
            "A1": 1,
            "A2": 4,
            "A3": 9,
            "A4": 12,
            "B1": 2,
            "B2": 5,
            "B3": 10,
            "B4": 13,
            "Y1": 3,
            "Y2": 6,
            "Y3": 8,
            "Y4": 11
        }
    
    @pytest.fixture
    def expChipInfo(self):
        return {
            "Name": "74HCT00",
            "Manufacturer": "Texas Instruments",
            "Logic": "NAND"
        }

    @pytest.mark.parametrize(
        "fileName, hasChipInfo, hasPinMap",[
            ("nand_bare.yaml", False, False),
            ("nand_pm.yaml", False, True), 
            ("nand_full.yaml", True, True)
        ]
    )
    def testValidParse(self, fileName, hasChipInfo, hasPinMap, expChipInfo, expPinMap, expGlobalParams):
        # make sure TestVector attributes start as None for test
        testvector.TestVector.updateGlobalParams(None)
        testvector.TestVector.updatePinMap(None)
        filePath = pathlib.Path.cwd() / "tests" / "unittest_yaml" / fileName # / will create file path based on os
        chipInfo, testVecs = parser.parse(filePath)

        assert len(testVecs) == 4
        assert testvector.TestVector.globalParams == expGlobalParams
        if hasChipInfo: assert chipInfo == expChipInfo
        if hasPinMap: assert testvector.TestVector.pinMap == expPinMap

    @pytest.mark.parametrize(
        "fileName, excCause", [
            ("MissingKeys.yaml", parser.MissingKeys),
            ("MissingKeys_gp.yaml", parser.MissingKeys),
            ("MissingKeys_tests.yaml", parser.MissingKeys),
            ("bad_tt1.yaml", parser.TableParseError),
            ("bad_tt2.yaml", parser.TableParseError),
            ("bad_tests1.yaml", parser.TestParseError),
            ("bad_tests2.yaml", parser.TestParseError),
            ("bad_tests3.yaml", parser.TestParseError),
            ("TypeError_pm1.yaml", TypeError),
            ("TypeError_pm2.yaml", TypeError),
            ("TypeError_gp1.yaml", TypeError),
            ("TypeError_gp2.yaml", TypeError),
            ("TypeError_gp3.yaml", TypeError),
            ("TypeError_tests1.yaml", TypeError),
            ("TypeError_tests2.yaml", TypeError),
            ("ValueError_pm1.yaml", ValueError),
            ("ValueError_pm2.yaml", ValueError),
            ("ValueError_tt.yaml", ValueError),
            ("ValueError_gp1.yaml", ValueError),
            ("ValueError_gp2.yaml", ValueError),
            ("ValueError_gp3.yaml", ValueError),
            ("ValueError_gp4.yaml", ValueError),
            ("ValueError_tests1.yaml", ValueError),
            ("ValueError_tests2.yaml", ValueError)
        ]    
    )
    def testParseError(self, fileName, excCause):
        filePath = pathlib.Path.cwd() / "tests" / "unittest_yaml" / fileName
        with pytest.raises(parser.ParseError) as exc:
            parser.parse(filePath)
        # msg includes filePath
        assertMsg(exc, filePath)
        assert isinstance(exc.value.__cause__, excCause)