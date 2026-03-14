import serial
import random # used for dummy test
from enum import Enum, auto
from typing import NamedTuple

# useful for accessing tuple elements by variable name
# TODO: add serial type
class LogicMapping(Enum):
    Single = auto()
    Map = auto()
    TruthTable = auto()

class IOCommand(NamedTuple):
    pins: list[int|str]
    pinVals: list[list|int|str]
    voltType: str
    cmdType: LogicMapping

class ResultTuple(NamedTuple):
    adcVals: list[float]
    logicVals: list[str|int]

class TestVector:
    # class attributes shared by all instances
    pinMap = None
    globalParams = None

    def __init__(self, inputs: list[IOCommand], outputs: list[IOCommand], testName: str):
        self.inputs = inputs
        self.outputs = outputs
        # results will be a dict of lists of ResultTuples
        self.results = {vccVoltage: [] for vccVoltage in TestVector.globalParams["VCC Voltage"]}
        self.testName = testName
        self.passed = None

    def test(self, ser: serial.Serial):
        # could use dict for test args, isInt, onCLK, singleIn, multiIn, mapIn, useTT
        for paramIdx, vccVoltage in enumerate(TestVector.globalParams["VCC Voltage"]):
            # set power pins
            ser.write((
                f"PRM:{TestVector.globalParams["VCC Pin"]},"
                f"{TestVector.globalParams["GND Pin"]},"
                f"{vccVoltage}\n"
            ).encode("utf-8"))

            # TODO: figure out clock inputs, specifically checking outputs on edges
            # Likely need separate test functions, truth tables
            if self.inputs[0].cmdType == LogicMapping.TruthTable:
                self._testTruthTable(self, ser, paramIdx)
            else:
                self._test(self, ser, paramIdx)
                
            # compare expected output with results
            passed = True
            if self.passed is not False:
                for exp, res in zip(self.outputs, self.results[vccVoltage]):
                    passed = self._compareResults(exp, res)
                    if passed == False:
                        break
                self.passed = passed
        return

    def exportAsTable(self):
        def toBinStr(val, width):
            if isinstance(val, int):
                # convert int to binary string with leading 0b, +2 for padding
                return format(val, f"#0{width+2}b")
            elif isinstance(val, (list, tuple)):
                return ", ".join(val)
            else:
                return str(val)
        # empty strings are used for spanning
        numVcc = len(TestVector.globalParams["VCC Voltage"])
        includeVcc = numVcc > 1
        totalOutPins = sum(len(out.pins) for out in self.outputs)
        # build header
        # VCC Voltage is always default High/1 value if not specified
        header = (
            ["Inputs"] + ([""] * (len(self.inputs) - 1)) +
            (["VCC"] if includeVcc else []) +
            ["Outputs/Results"] + [""] * (2*totalOutPins - 1)
        )
        # build columns
        # unwraps output pin list into its own column
        pinCols = (
            [", ".join(str(pin) for pin in inp.pins) for inp in self.inputs] +
            ([""] if includeVcc else []) +
            [col for out in self.outputs for pin in out.pins for col in (pin, "")] # empty string after each output pin
        )

        data = []
        isTruthTable = True if self.inputs[0].cmdType == LogicMapping.TruthTable else False 
        numRows = len(self.inputs[0].pinVals) if isTruthTable else 1

        # create rows for data
        for i in range(numRows):
            # compute input data entries
            inputData = []
            for inp in self.inputs:
                inpStr = toBinStr(inp.pinVals[i], len(inp.pins))
                inpStr += f" ({inp.voltType})" if inp.voltType else "" # only include voltage if specified
                inputData.append(inpStr)

            # compute output data entries
            outputData = []
            for out in self.outputs:
                for pinIdx in range(len(out.pins)):
                    if out.cmdType == LogicMapping.Single:
                        valIdx = 0
                    elif out.cmdType == LogicMapping.Map:
                        valIdx = 0 if isinstance(out.pinVals[0], int) else pinIdx
                    elif out.cmdType == LogicMapping.TruthTable:
                        valIdx = i

                    if isinstance(out.pinVals[valIdx], int):
                        outVal = (out.pinVals[0] >> (len(out.pins) - pinIdx - 1)) & 1
                    else:
                        outVal = out.pinVals[valIdx]
                    outputData.append(outVal)

            for vccIdx, vccVoltage in enumerate(TestVector.globalParams["VCC Voltage"]):
                row = []
                # Inputs and VCC
                if includeVcc:
                    # print input data if first vccRow, else print empty strings, vcc column at end
                    row.extend((inputData if vccIdx == 0 else [""] * len(inputData)) + [vccVoltage])
                else:
                    # print input data, no vcc column
                    row.extend(inputData)
                # Output/Results
                for outIdx, out in enumerate(self.outputs):
                    res = self.results[vccVoltage][outIdx] # corresponding result based on voltage and output pin group
                    for pinIdx in range(len(out.pins)):
                        # calculate index postions of outputs and results
                        outDataIdx = pinIdx if isTruthTable else  outIdx*len(self.outputs) + pinIdx
                        resIdx = i if isTruthTable else pinIdx
                        
                        row.append(outputData[outDataIdx] if vccIdx == 0 else "")
                        row.append(f"{res.adcVals[resIdx]} ({res.logicVals[resIdx]})")
                data.append(row)

        table = [header] + [pinCols] + data
        metadata = {
            "inputSpan" : len(self.inputs),
            "outputSpan" : totalOutPins,
            "numRows" : numRows,
            "includeVcc" : includeVcc,
            "numVcc" : numVcc
        }
        return table, metadata
    
    def _listToCommand(self, command: str, args: list):
        return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")

    def _execute(self, ser: serial.Serial, inPins: list[int], vIn: list[int|float], outPins: list[int]):
        ser.write(self.ListToCommand("INS", inPins))
        ser.write(self.ListToCommand("VIP", vIn))
        ser.write(self.ListToCommand("OUT", outPins))
        ser.write("TEST\n".encode("utf-8"))
        return

    def _compareResults(self, exp: IOCommand, res: ResultTuple):
        # check bit by bit because ResultTuple does not store as int
        # U prevents bit shifting results
        if isinstance(exp.pinVals[0], int):
            for i in range(len(exp.pins)):
                bit = exp.pinVals[0] >> (len(exp.pins) - i - 1) & 1
                if bit != res.logicVals[i]:
                    return False
        # compares two lists
        elif exp.pinVals != res.logicVals:
            return False
        return True

    def _test(self, ser: serial.Serial, paramIdx: int):
        inPins = [] # input pin list
        vIn = [] # input value list
        for inp in self.inputs:
            match inp.cmdType:
                case LogicMapping.Single:
                    self._single(inp, inPins, vIn, paramIdx)
                case LogicMapping.Map:
                    self._map(inp, inPins, vIn, paramIdx, isinstance(inp.pinVals[0], int))
                case _:
                    raise ValueError(
                        f"No such LogicMapping command type \"{inp.cmdType}\""
                    )
        # extract all output pins into one list  
        outPins = []
        for out in self.outputs:
            for pinRef in out.pins:
                pin = TestVector.getPin(pinRef)
                outPins.append(pin)

        self._execute(ser, inPins, vIn, outPins)
        self._readResults(ser, paramIdx)
        return

    def _single(self, inp: IOCommand, inPins: list[int], vIn: list[int|float], paramIdx: int):
        for pinRef in inp.pins:
            pin = TestVector.getPin(pinRef)
            logic = inp.pinVals[0] # only one pin value for LogicMapping.single
            voltage = TestVector.getVoltage(logic, inp.voltType, paramIdx)

            inPins.append(pin)
            vIn.append(voltage)
        return
    
    def _map(self, inp: IOCommand, inPins: list[int], vIn: list[int|float], paramIdx: int, isInt: bool):
        for i, pinRef in enumerate(inp.pins):
            pin = TestVector.getPin(pinRef)
            if isInt: logic = (inp.pinVals[0] >> (len(pin) - i - 1)) & 1 # bit shift to extract logic from int
            else: logic = inp.pinVals[i]
            voltage = TestVector.getVoltage(logic, inp.voltType, paramIdx)

            inPins.append(pin)
            vIn.append(voltage)
        return
    
    def _testTruthTable(self, ser: serial.Serial, paramIdx: int):
        for i in range(self.inputs[0].pinVals): # iterate through length of truth table
            inPins = []
            vIn = []
            for inp in self.inputs:
                for pinRef in inp.pins:
                    pin = TestVector.getPin(pinRef)
                    logic = inp.pinVals[i]
                    voltage = TestVector.getVoltage(logic, inp.voltType, paramIdx)

                    inPins.append(pin)
                    vIn.append(voltage)
            
            outPins = []
            for out in self.outputs:
                for pinRef in out.pins:
                    pin = TestVector.getPin(pinRef)
                    outPins.append(pin)

            # write commands to serial
            self._execute(ser, inPins, vIn, outPins)

            # TODO: read results and place into ResultTuple Object
            self._readResultsTruthTable(ser, i, paramIdx)
        return

    def _readResults(self, ser: serial.Serial, paramIdx: int):
        response = ser.readline().decode("utf-8").strip()
        adcValsStr = response.split(",")
        respIdx = 0
        for i, out in enumerate(self.outputs):
            isInt = isinstance(out.pinVals[i], int) # used to make results into int if output is formatted as int

            adcVals = []
            logicVals = []

            for _ in range(len(out.pins)):
                # extract value and logic
                val = adcValsStr[respIdx]
                floatVal = float(val) / 100
                logic = TestVector.logicFromThld(floatVal, isInt, paramIdx)

                adcVals.append(floatVal)
                logicVals.append(logic)
                respIdx += 1
            # set results
            self.results[TestVector.globalParams["VCC Voltage"][paramIdx]].append(ResultTuple(adcVals, logicVals))
        return

    def _readResultsTruthTable(self, ser: serial.Serial, rowIdx: int, paramIdx: int):
        response = ser.readline().decode("utf-8").strip()
        adcValsStr = response.split(",")
        respIdx = 0
        for i in range(len(self.outputs)):
            # extract value and logic
            val = adcValsStr[respIdx]
            floatVal = float(val) / 100
            logic = TestVector.logicFromThld(floatVal, False, paramIdx)

            if rowIdx == 0:
                self.results[TestVector.globalParams["VCC Voltage"][paramIdx]].append([logic])
            else:
                self.results[TestVector.globalParams["VCC Voltage"][paramIdx]][i].append(logic)
            respIdx += 1
        return
    
    @classmethod
    def updatePinMap(cls, pinMap: dict):
        cls.pinMap = pinMap

    @classmethod
    def updateGlobalParams(cls, globalParams: dict):
        cls.globalParams = globalParams
    
    @classmethod
    def getPin(cls, pinRef: int|str):
        if isinstance(pinRef, int): return pinRef
        else: return cls.pinMap[pinRef] 

    @classmethod
    def getVoltage(cls, logic: int|str, voltType: str, paramIdx: int):
        if logic in {0, "L", "X"}: return 0 # dont care bits default to 0 volts
        else: return voltType if voltType is not None else  cls.globalParams["VCC Voltage"][paramIdx]

    @classmethod
    def logicFromThld(cls, adcVal: float, isInt: bool, paramIdx: int):
        if adcVal >= cls.globalParams["Output High"][paramIdx]: return 1 if isInt else "H"
        elif adcVal <= cls.globalParams["Output Low"][paramIdx]: return 0 if isInt else "L"
        # not either logic low or high based on thresholds
        else: return "U"

    def dummyTest(self):
        def randomVoltage(low, high, percent=0.05):
            # Compute bands
            lowMin  = low  * (1 - percent)
            lowMax  = low  * (1 + percent)
            highMin = high * (1 - percent)
            highMax = high * (1 + percent)

            # Randomly choose which band to sample from
            if random.random() < 0.5:
                return random.uniform(lowMin, lowMax)
            else:
                return random.uniform(highMin, highMax)
        # dummy test function to generate example data for report formatting
        for paramIdx, vccVoltage in enumerate(TestVector.globalParams["VCC Voltage"]):
            low = TestVector.globalParams["Output Low"][paramIdx]
            high = TestVector.globalParams["Output High"][paramIdx]
            for out in self.outputs:
                isInt = isinstance(out.pinVals[0], int)
                # create dummy adc values and logic results based on output pin values and VCC voltage
                adcVals = []
                logicVals = []

                if out.cmdType == LogicMapping.Single or out.cmdType == LogicMapping.Map:
                    numVals = len(out.pins)
                else:
                    numVals = len(out.pinVals)

                for _ in range(numVals):
                    adcVal = randomVoltage(low, high, 0.05)
                    adcVals.append(round(adcVal,3))
                    logicVals.append(TestVector.logicFromThld(adcVal, isInt, paramIdx))
                self.results[vccVoltage].append(ResultTuple(adcVals, logicVals))

        passed = True
        for vccVoltage in TestVector.globalParams["VCC Voltage"]:       
            for exp, res in zip(self.outputs, self.results[vccVoltage]):
                passed = self._compareResults(exp, res)
                if passed == False:
                    break
        self.passed = passed
        return
    