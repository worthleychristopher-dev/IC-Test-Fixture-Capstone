import re
import yaml
import warnings
from ICTestFixture.core.testvector import TestVector, IOCommand, LogicMapping
from enum import Enum

# global macros for parser
INPUT_LOGIC = {"H", "L", "R", "F", "X"}
# Q_0 seems to serve same purpose as 'S'
OUTPUT_LOGIC = {"H", "L", "Z", "X", "S", "T", "Q_0"}
TRUTH_TABLE_LOGIC = INPUT_LOGIC | OUTPUT_LOGIC
SUPPORTED_VOLTAGES = {"0V", "1.8V", "2.5V", "3.3V", "4V", "4.5V", "5V"} # could remove V from test scripts
MAX_PINS = 20
# [digits] opt. decimal point [digits], space, [k or M]
NUM_WITH_UNIT = r"\d*\.?\d+\s[k|M]$"
class Clock(Enum): MAX = -1; MIN = -1
class VoltageUnit(Enum): k = 10e3; M = 10e6

# declare parser exceptions here
class ParseError(Exception):
    pass
class TableParseError(Exception):
    pass
class TestParseError(Exception):
    pass
class MissingKeys(Exception):
    pass

def checkType(val: any, expTypes: tuple, section: str, key: str) -> None:
    """
        helper function, checks if val is one of expTypes
    """
    if not isinstance(val, expTypes):
        errStr = f"Expected type "
        for expType in expTypes:
            errStr += f"\"{expType.__name__}\", " 
        errStr += f"got \"{type(val).__name__}\", in \"{section}[{key}]\""
        raise TypeError(errStr)
    return

def checkPin(pin: int|str, section: str, key: str) -> None:
    """
        helper function, check if pin is between 1 and MAX_PINS
    """
    if not (0 < pin <= MAX_PINS):
        raise ValueError(
            f"Pin number must be between 1 and {MAX_PINS}, got \"{pin}\" in \"{section}[{key}]\""
        )
    return

def checkVoltage(voltage: str, section: str, key: str) -> None:
    if voltage not in SUPPORTED_VOLTAGES:
        raise ValueError(
            f"Voltage must be one of supported voltages: {SUPPORTED_VOLTAGES}, "
            f"got \"{voltage}\" in \"{section}[{key}]\""
        )
    return

def checkKeys(expKeys: set, optKeys: set, gotKeys: set, section: str) -> None:
    """
        helper function, checks if gotKeys are in expKeys and optKeys
    """
    missingKeys = expKeys - gotKeys
    if missingKeys:
        raise MissingKeys(
            f"Missing required keys: {missingKeys}, in \"{section}\""
        )

    ignoredKeys = gotKeys - expKeys - optKeys if optKeys is not None else gotKeys-expKeys
    if ignoredKeys:
        warnings.warn(f"Ignoring unexpected keys: {ignoredKeys}, in \"{section}\"")
    return


def parse(filePath: str):
    """
        parses yaml test script for valid syntax, and valid names/values
    """
    with open(filePath, 'r') as file:
        data = yaml.safe_load(file)

        try:
            expKeys = {"Global Parameters", "Tests"}
            optKeys = {"Chip Info", "Pin Map", "Truth Table"}
            checkKeys(expKeys, optKeys, data.keys(), filePath)

            chipInfo = data.get("Chip Info", None)
            pinMap = data.get("Pin Map", None)
            truthTable = data.get("Truth Table", None)

            # if chipInfo: parseChipInfo(chipInfo)
            parseGlobalParams(data["Global Parameters"])

            vccPin = data["Global Parameters"]["VCC Pin"]
            gndPin = data["Global Parameters"]["GND Pin"]
            if pinMap is not None: parsePinMap(pinMap, vccPin, gndPin)

            tt = parseTruthTable(truthTable) if truthTable is not None else None

            testVecs = parseTests(data["Tests"], data["Global Parameters"], pinMap, tt)
        except Exception as e:
            raise ParseError(f"Failed to parse {filePath}") from e

        return chipInfo, testVecs
    
# optional section, will be written into PDF report, likely nothing to check
# def parseChipInfo(chipInfo: dict):
#     """
#         parses chip info section of yaml test script
#     """
#     pass

# optional section, allows abstraction for Tests section
def parsePinMap(pinMap: dict, vccPin: int, gndPin: int) -> None:
    """
        parses pin map section of yaml test script
    """
    usedPins = set()
    for pin in pinMap:
        # pin name must be str to avoid conflicts
        # int reserved for direct mapping to socket
        checkType(pin, (str,), "Pin Map", pin)
        checkType(pinMap[pin], (int,), "Pin Map", pin)
        checkPin(pinMap[pin], "Pin Map", pin)
        
        if pinMap[pin] == vccPin:
            raise ValueError(
                f"Pin number must not be same as VCC Pin: {vccPin}, "
                f"got \"{pinMap[pin]}\" in \"Pin Map[{pin}]\""
            )
        
        if pinMap[pin] == gndPin:
            raise ValueError(
                f"Pin number must not be same as GND Pin: {gndPin}, "
                f"got \"{pinMap[pin]}\" in \"Pin Map[{pin}]\""
            )

        if pinMap[pin] in usedPins:
            raise ValueError(
                f"Multiple names map to same pin: \"{pinMap[pin]}\""
            )
        else:
            usedPins.add(pinMap[pin])
    return

# optional section, allows abstraction for Tests section
def parseTruthTable(truthTable: list[dict]) -> dict:
    """
        parses truth table section of yaml test script
    """
    colNum = len(truthTable[0])
    colNames = truthTable[0].keys()
    # col name must be str to avoid conflicts
    # int reserved for binary inputs with 0b and integers
    for colName in colNames: checkType(colName, (str,), "Truth Table", colName)
    # restructure truth table to use list for each column
    tt = {col: [None] * len(truthTable) for col in colNames}
    for i, row in enumerate(truthTable):
        # checks all rows have same number of columns as first row
        if len(row) != colNum:
            raise TableParseError(
                "Inconsistent number of columns in \"Truth Table\""
            )
        
        for key in row:
            # checks if all rows have same column names as first row
            if key not in colNames:
                raise TableParseError(
                    "Inconsistent column names in \"Truth Table\""
                )

            if row[key] not in TRUTH_TABLE_LOGIC:
                raise ValueError(
                    f"Invalid logic \"{row[key]}\" for column \"{key}\", "
                    f"expected one of {TRUTH_TABLE_LOGIC} in \"Truth Table\""
                )
            tt[key][i] = row[key]
    return tt

def parseGlobalParams(globalParams: dict) -> None:
    """
        parses Global Parameters section of yaml test script
    """
    # maybe have structured test param section to remove match statements
    expKeys = {"VCC Pin", "GND Pin", "VCC Voltage", "Output Low", "Output High"}
    optKeys = {"CLK Freq", "Input Low", "Input High"}
    checkKeys(expKeys, optKeys, globalParams.keys(), "Global Parameters")
    # checkVoltage(globalParams["VCC Voltage"], "Global Parameters", "VCC Voltage") # check VCC Voltage is valid
    # check VCC Pin and GND Pin are valid
    checkType(globalParams["VCC Pin"], (int,), "Global Parameters", "VCC Pin")
    checkType(globalParams["GND Pin"], (int,), "Global Parameters", "GND Pin")
    for param in ("VCC Pin", "GND Pin"):
        checkPin(globalParams[param], "Global Parameters", param)

    if globalParams["VCC Pin"] == globalParams["GND Pin"]:
        raise ValueError(
            f"VCC Pin and GND Pin are the same, got \"{globalParams["VCC Pin"]}\""
        )
    
    # wrap everything into list for consistency when only 1 value is provided
    # make testing loop at various VCC Voltages easier
    length = set()
    for param in ["VCC Voltage", "Output Low", "Output High", "Input Low", "Input High"]:
        if param in globalParams:
            if not isinstance(globalParams[param], list):
                globalParams[param] = [globalParams[param]]
            length.add(len(globalParams[param]))
    
    if len(length) > 1:
        raise ValueError(
            f"Inconsistent number of values for VCC Voltage and voltage thresholds, "
            f"got {length} values in \"Global Parameters\""
        )
    
    for param in ["Output Low", "Output High", "Input Low", "Input High"]:
        thlds = globalParams.get(param, None)
        if thlds is not None:
            for thld in thlds:
                checkType(thld, (int, float), "Global Parameters", param)
                if thld < 0:
                    raise ValueError(
                        f"Expected voltage threshold greater than or equal to \"0\", "
                        f"got \"{thld}\", in \"Global Parameters[{param}]\""
                    )

    paramLength = next(iter(length))
    for i in range(paramLength):
        checkVoltage(globalParams["VCC Voltage"][i], "Global Parameters", f"VCC Voltage") # check VCC Voltage is valid
        # low threshold cannot be greater than high threshold
        # output thresholds
        if globalParams["Output Low"][i] >= globalParams["Output High"][i]:
            raise ValueError(
                f"Voltage Output Low is greater than or equal to Voltage Output High, "
                f"got {globalParams['Output Low'][i]} >= {globalParams['Output High'][i]}"
            )
        # input thresholds
        if "Input Low" in globalParams and "Input High" in globalParams:
            if globalParams["Input Low"][i] >= globalParams["Input High"][i]:
                raise ValueError(
                    f"Voltage Input Low is greater than or equal to Voltage Input High, "
                    f"got {globalParams['Input Low'][i]} >= {globalParams['Input High'][i]}"
                )

    # check CLK Freq is valid
    clkFreq = globalParams.get("CLK Freq", None)
    if clkFreq:
        checkType(clkFreq, (str, int, float), "Test Parameters", "CLKFreq")
        if isinstance(clkFreq, str):
            if re.match(NUM_WITH_UNIT, globalParams["CLK Freq"]) is None:
                raise ValueError(
                    f"Invalid format for CLK Freq, got {clkFreq}\n"
                    "Syntax - CLK Freq: val [unit]"
                )
            parts = clkFreq.split()
            globalParams["CLK Freq"] = float(parts[0]) * VoltageUnit[parts[1]].value
        if not (Clock.MIN.value <= globalParams["CLK Freq"] <= Clock.MAX.value):
            raise ValueError(
                f"CLK Freq must be between or equal to "
                f"{Clock.MIN} and {Clock.MAX}, "
                f"got \"{globalParams["CLK Freq"]}\" in \"Test Parameters[CLK Freq]\""
            )
        # TODO: check if its a feasible clock/round it
    return

def parseTests(tests: dict, globalParams: dict, pinMap: dict, truthTable: dict) -> list[TestVector]:
    """
        parses Tests section of yaml test script
    """
    expKeys = {"Inputs", "Outputs"}
    testVecs = [None for _ in range(len(tests))]
    for i, (testName, test) in enumerate(tests.items()):
        checkKeys(expKeys, None, test.keys(), f"Tests[{testName}]")
        inputCmds = parseTestIO(test["Inputs"], pinMap, truthTable, INPUT_LOGIC, testName)
        outputCmds = parseTestIO(test["Outputs"], pinMap, truthTable, OUTPUT_LOGIC, testName)
        testVecs[i] = TestVector(inputCmds, outputCmds, globalParams, pinMap, testName)
    return testVecs

def parseTestIO(io: dict, pinMap: dict, truthTable: dict, validLogic: set[str], testName: str) -> list[IOCommand]:
    """
        helper function to parseTests, parses Inputs/Outputs sections of each test
    """
    # TODO: figure out how to make work with shift registers
    # TODO: check voltage is within input thresholds, otherwise raise a warning, maybe easier in TestVector class
    # returning data structure: list of tuples, each tuple is (list of pin numbers, list of pin values, voltage)
    vec = [None for _ in range(len(io))]
    for i, pins in enumerate(io):
        # check pin is either valid pin number or name from pin map
        checkType(pins, (int, str), f"Tests[{testName}]", "I/O")
        pinNames = [pins] if isinstance(pins, int) else pins.split(",")
        for j, pinName in enumerate(pinNames):
            if isinstance(pinName, int): 
                pin = pinName
                store = pin
            elif pinName.isdigit(): 
                pin = int(pinName) # convert digits to int representation
                store = pin
            # check if identifer is in pin map
            elif pinMap is not None and pinName in pinMap:
                pin = pinMap[pinName]
                store = pinName
            else:
                raise ValueError(
                    f"Unknown pin name \"{pinName}\" in \"Tests[{testName}]\"\n"
                    "Either provide valid pin number or define pin name in Pin Map"
                )

            checkPin(pin, "Tests", testName)
            pinNames[j] = store

        # check pin value is valid character or identifier from truth table
        checkType(io[pins], (str, int), f"Tests[{testName}]", pins)
        if not isinstance(io[pins], str): io[pins] = str(io[pins]) # normalize command as str
        # could add output pin explicitly state clock dependency on certain pins
        cmd = io[pins].split(" ")
        pinVals = cmd[0].split(",")
        voltage = cmd[-1] if len(cmd) >= 2 else None

        if voltage is not None:
            checkVoltage(voltage, "Tests", testName)
        
        parsedPinVals = []
        cmdType = None
        for pinVal in pinVals:
            # converts binary to ints
            if pinVal.startswith("0b") or pinVal.isdigit():
                # for now only support lone integers, not 0b10,0b11
                if len(pinVals) != 1:
                    # only one integer input allowed per line
                    raise TestParseError(
                        f"Only 1 integer input allowed for input mapping, "
                        f"got {pinVals} in \"Test[{testName}]\""
                    )
                val = int(pinVal, 0) # autodetects base from string
                # check if int possible
                if not (val <= 2**len(pinNames) - 1):
                    raise ValueError(
                        f"Integer value \"{val}\" exceeds maximum value: {2**len(pinNames) - 1} "
                        f"for {len(pinNames)} pin(s), got \"{val}\" in \"Tests[{testName}][{pins}]\""
                    )
                parsedPinVals.append(val)
                cmdType = LogicMapping.Map
            # replace reference with value from truth table
            # maybe don't, to make testing truth tables easier in testVector.py?
            elif truthTable is not None and pinVal in truthTable:
                if len(pinVals) > 1:
                    raise TestParseError(
                        f"Cannot have multiple outpins in same line when using truth table value"
                    )
                parsedPinVals.extend(truthTable[pinVal])
                cmdType = LogicMapping.TruthTable
            # no truth table, using logic set
            else:
                if pinVal not in validLogic:
                    raise ValueError(
                        f"Invalid logic/reference \"{pinVal}\" for pin \"{pins}\", "
                        f"expected one of {validLogic}, or reference in \"Truth Table\" in \"Tests[{testName}]\""
                    )
                parsedPinVals.append(pinVal)
                if len(pinVals) == 1:
                    cmdType = LogicMapping.Single
                elif len(pinNames) == len(pinVals):
                    cmdType = LogicMapping.Map
                else:
                    # cannot map inputs to pins
                    raise TestParseError(
                        f"Incompatible lengths of I/O pins ({len(pinNames)}) and values ({len(pinVals)}), " 
                        f"both must be same length, or values has length of 1 in \"Tests[{testName}]\""
                    )
        
        vec[i] = IOCommand(pinNames, parsedPinVals, voltage, cmdType)

    # Global mapping consistency check
    allCmdTypes = {entry.cmdType for entry in vec if entry is not None}

    if (
        LogicMapping.TruthTable in allCmdTypes
        and any(cmd != LogicMapping.TruthTable for cmd in allCmdTypes)
    ):
        raise TestParseError(
            f"Cannot mix truth table mapping with any other pin mapping "
            f'in "Tests[{testName}]"'
        )

    return vec
