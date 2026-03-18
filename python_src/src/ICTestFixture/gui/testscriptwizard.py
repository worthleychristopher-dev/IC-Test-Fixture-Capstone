from yaml import safe_dump
from enum import IntEnum
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QWidget,
    QWizard,
    QWizardPage,
    QVBoxLayout
)

from ICTestFixture.core.parser import (
    INPUT_LOGIC,
    OUTPUT_LOGIC,
    TRUTH_TABLE_LOGIC,
    SUPPORTED_VOLTAGES,
    MAX_PINS,
    parsePinMap,
    parseGlobalParams,
    parseTruthTable,
    parseTests
)

SORTED_VOLTAGES = sorted(SUPPORTED_VOLTAGES)
SORTED_INPUT = sorted(INPUT_LOGIC)
SORTED_OUTPUT = sorted(OUTPUT_LOGIC)
SORTED_LOGIC = sorted(TRUTH_TABLE_LOGIC)
PINS = [str(i) for i in range(1, MAX_PINS+1)]

class PageNum(IntEnum):
    Select = 0
    ChipInfo = 1
    GlobalParameters = 2
    PinMap = 3
    TruthTable = 4
    Tests = 5
    End = -1

class DynamicContainer(QWidget):
    def __init__(self, parent, widgetTypes, headers):
        super().__init__(parent)
        self.widgetTypes = widgetTypes
        self.rows = []

        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        for col, header in enumerate(headers):
            self.grid.addWidget(QLabel(header), 0, col)
        self.grid.addWidget(QLabel(""), 0, len(headers))

        self.addRow()

        addButton = QToolButton()
        addButton.setText("Add Entry")
        addButton.clicked.connect(self.addRow)

        layout = QVBoxLayout()
        layout.addLayout(self.grid)
        layout.addWidget(addButton, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def addRow(self):
        rowWidgets = []
        rowIdx = len(self.rows) + 1
        # insert before the stretch
        deleteButton = QToolButton()
        deleteButton.setText("-")
        deleteButton.clicked.connect(lambda _, btn=deleteButton: self.deleteRow(btn))

        for col, widgetType in enumerate(self.widgetTypes):
            widget = widgetType()
            rowWidgets.append(widget)
            self.grid.addWidget(widget, rowIdx, col)
        self.grid.addWidget(deleteButton, rowIdx, len(self.widgetTypes))

        self.rows.append((rowWidgets, deleteButton))
    
    def deleteRow(self, button):
        # prevents deleting when there is only one row
        if len(self.rows) <= 1:
            return
        
        rowIdx = None
        for i, row in enumerate(self.rows):
            if button in row:
                rowIdx = i
                break

        if rowIdx is None:
            return
        
        widgets, btn = self.rows.pop(rowIdx)
        for widget in widgets:
            self.grid.removeWidget(widget)
            widget.deleteLater()

        self.grid.removeWidget(btn)
        btn.deleteLater()

        for i in range(rowIdx, len(self.rows)):
            widgets, btn = self.rows[i]
            for col, widget in enumerate(widgets):
                self.grid.addWidget(widget, i+1, col)
            self.grid.addWidget(btn, i+1, len(widgets))

    def extractData(self):
        data = []
        for row in self.rows:
            values = []
            for widget in row[0]:
                values.append(self.getValue(widget))
            data.append(values)
        return data
    
    def __len__(self):
        return len(self.rows)
    
    @staticmethod
    def getValue(widget):
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        else:
            raise TypeError(
                f"Unknown Type ({type(widget)}) for Widget, unable to extract value"
            )

class SelectOptPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Select Optional Sections to Include")
        self.incChipInfo = QCheckBox("Chip Info")
        self.incPinMap = QCheckBox("Pin Map")
        self.incTruthTable = QCheckBox("Truth Table")

        self.registerField("incChipInfo", self.incChipInfo)
        self.registerField("incPinMap", self.incPinMap)
        self.registerField("incTruthTable", self.incTruthTable)

        layout = QVBoxLayout()
        layout.addWidget(self.incChipInfo)
        layout.addWidget(self.incPinMap)
        layout.addWidget(self.incTruthTable)
        self.setLayout(layout)

    def nextId(self):
        if self.field("incChipInfo"): return PageNum.ChipInfo
        return PageNum.GlobalParameters

class ChipInfoPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Chip Info")

        self.dataEntries = DynamicContainer(self, (QLineEdit, QLineEdit), ("Parameter", "Value"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.dataEntries)

        layout = QVBoxLayout()
        layout.addWidget(scroll, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)
    
    def validatePage(self):
        data = self.dataEntries.extractData()
        chipInfo = {}
        for d in data:
            chipInfo[d[0]] = d[1]

        self.wizard().data["Chip Info"] = chipInfo
        return True

    def nextId(self):
        return PageNum.GlobalParameters

class GlobalParametersPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Global Parameters")

        PARAMS = [
            ("VCC Pin", TestScriptWizard.pinSpinbox),
            ("GND Pin", TestScriptWizard.pinSpinbox),
            ("VCC Voltage", lambda: TestScriptWizard.dropdown(SORTED_VOLTAGES)),
            ("Output Low", TestScriptWizard.doubleSpinBox),
            ("Output High", TestScriptWizard.doubleSpinBox),
            ("Input Low (Opt.)", TestScriptWizard.doubleSpinBox),
            ("Input High (Opt.)", TestScriptWizard.doubleSpinBox)
        ]
        LABEL_WIDTH = 100
        WIDGET_WIDTH = 60

        self.globalParams = {}

        layout = QGridLayout()
        for row, (param, widgetFunc) in enumerate(PARAMS):
            label = QLabel(param)
            label.setFixedWidth(LABEL_WIDTH)

            widget = widgetFunc() if widgetFunc else QLineEdit()
            widget.setFixedWidth(WIDGET_WIDTH)

            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)
            if param.endswith("(Opt.)"):
                checkbox = QCheckBox()
                layout.addWidget(checkbox, row, 2)
                param = param.removesuffix(" (Opt.)")
                self.globalParams[param] = (widget, checkbox)
            else:
                self.globalParams[param] = widget

        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def validatePage(self):
        globalParams = {}
        for param, widget in self.globalParams.items():
            if param == "Input Low" or param == "Input High":
                if widget[1].isChecked():
                    globalParams[param] = DynamicContainer.getValue(widget[0])
            else:
                globalParams[param] = DynamicContainer.getValue(widget)

        try:
            parseGlobalParams(globalParams)
            self.wizard().data["Global Parameters"] = globalParams
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self):
        if self.field("incPinMap"): return PageNum.PinMap
        if self.field("incTruthTable"): return PageNum.TruthTable
        return PageNum.Tests

class PinMapPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Pin Map")

        self.dataEntries = DynamicContainer(self, (QLineEdit, TestScriptWizard.pinSpinbox), ("Pin Name", "Pin Number"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(250)
        scroll.setWidget(self.dataEntries)

        layout = QVBoxLayout()
        layout.addWidget(scroll, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

    def validatePage(self):
        data = self.dataEntries.extractData()
        pinMap = {}
        for d in data:
            pinMap[d[0]] = d[1]

        vccPin = self.wizard().data["Global Parameters"]["VCC Pin"]
        gndPin = self.wizard().data["Global Parameters"]["GND Pin"]

        try:
            parsePinMap(pinMap, vccPin, gndPin)
            self.wizard().data["Pin Map"] = pinMap
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self):
        if self.field("incTruthTable"): return PageNum.TruthTable
        return PageNum.Tests

class TruthTablePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Truth Table")

        self.dataEntries = None
        self.lineWidgets = []
        self.entryLayout = QVBoxLayout()

        editLayout = QVBoxLayout()
        self.editDialog = QDialog(self)
        self.editDialog.setWindowTitle("Edit Columns")

        spinbox = TestScriptWizard.pinSpinbox()
        spinbox.valueChanged.connect(self.updateEntryLayout)

        confirmButton = QPushButton("Confirm")
        cancelButton = QPushButton("Cancel")

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(confirmButton)
        buttonLayout.addWidget(cancelButton)

        confirmButton.clicked.connect(self.updateColNames)
        cancelButton.clicked.connect(self.editDialog.reject)

        editLayout.addWidget(spinbox)
        editLayout.addLayout(self.entryLayout)
        editLayout.addLayout(buttonLayout)
        self.editDialog.setLayout(editLayout)

        editButton = QToolButton()
        editButton.setText("Edit")
        editButton.clicked.connect(self.editDialog.exec)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(editButton, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.mainLayout)

    def updateEntryLayout(self, val):
        while len(self.lineWidgets) > val:
            widget = self.lineWidgets.pop()
            widget.deleteLater()

        while len(self.lineWidgets) < val:
            lineWidget = QLineEdit()
            self.lineWidgets.append(lineWidget)
            self.entryLayout.addWidget(lineWidget)

    def updateColNames(self):
        colNames = []
        dropdowns = []
        for lineWidget in self.lineWidgets:
            dropdowns.append(lambda: TestScriptWizard.dropdown(TRUTH_TABLE_LOGIC))
            colNames.append(lineWidget.text())

        if self.dataEntries:
            self.dataEntries.deleteLater()
        self.dataEntries = DynamicContainer(self, dropdowns, colNames)
        self.mainLayout.addWidget(self.dataEntries)
        self.editDialog.accept()

    def validatePage(self):
        truthTable = []
        for row in self.dataEntries.extractData():
            truthTable.append(self.valToDict(row))

        try:
            tt = parseTruthTable(truthTable)
            self.wizard().data["Truth Table"] = truthTable
            self.wizard().data["tt"] = tt
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False
        
    def valToDict(self, vals):
        d = {}
        for i in range(len(self.lineWidgets)):
            d[self.lineWidgets[i].text()] = vals[i]
        return d

    def nextId(self):
        return PageNum.Tests

class TestsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tests")

        self.testWidgets = {}

        self.tabs = QTabWidget()
        self.tabs.tabCloseRequested.connect(self.deleteTest)

        addTestButton = QToolButton()
        addTestButton.setText("Add Test")
        addTestButton.clicked.connect(self.getTestName)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(addTestButton, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def initializePage(self):
        pins = []
        pinMap = self.wizard().data.get("Pin Map")
        if pinMap:
            for pinName in pinMap:
                pins.append(pinName)
        pins.extend(PINS)
        
        inputWithTT = []
        outputWithTT = []
        truthTable = self.wizard().data.get("Truth Table")
        if truthTable:
            for colName in truthTable[0].keys():
                inputWithTT.append(colName)
                outputWithTT.append(colName)
        inputWithTT.extend(INPUT_LOGIC)
        outputWithTT.extend(OUTPUT_LOGIC)

        self.dropPin = lambda: TestScriptWizard.dropdown(pins)
        self.dropInput = lambda: TestScriptWizard.dropdown(inputWithTT)
        self.dropOutput = lambda: TestScriptWizard.dropdown(outputWithTT)

    def getTestName(self):
        testName, confirm = QInputDialog.getText(self, "Enter Test Name", "Test Name:")
        if testName and confirm:
            self.addTest(testName)

    def addTest(self, testName):
        testInput = DynamicContainer(self, (self.dropPin, self.dropInput), ("Pin(s)", "Value(s)"))
        testOutput = DynamicContainer(self, (self.dropPin, self.dropOutput), ("Pin(s)", "Value(s)"))

        testLayout = QVBoxLayout()
        testLayout.addWidget(QLabel("Input(s)"), alignment=Qt.AlignmentFlag.AlignCenter)
        testLayout.addWidget(testInput)
        testLayout.addWidget(QLabel("Output(s)", alignment=Qt.AlignmentFlag.AlignCenter))
        testLayout.addWidget(testOutput)

        testWidget = QWidget()
        testWidget.setLayout(testLayout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(testWidget)

        test = {"Inputs": testInput, "Outputs": testOutput}
        self.testWidgets[testName] = test
        self.tabs.addTab(scroll, testName)
        
    def deleteTest(self, i):
        reply = QMessageBox.question(
            self,
            "Deleting Test",
            "Are you sure you want to delete this test?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            testWidget = self.tabs.widget(i)
            testName = self.tabs.tabText(i)

            self.testWidgets.pop(testName)
            self.tabs.removeTab(i)
            testWidget.deleteLater()

    def validatePage(self):
        tests = {}
        for testName, testWidgets in self.testWidgets.items():
            inputData = self.valsToDict(testWidgets["Inputs"].extractData())
            outputData = self.valsToDict(testWidgets["Outputs"].extractData())
            tests[testName] = {"Inputs": inputData, "Outputs": outputData}

        globalParams = self.wizard().data.get("Global Parameters")
        pinMap = self.wizard().data.get("Pin Map")
        tt = self.wizard().data.get("tt")

        try:
            parseTests(tests, globalParams, pinMap, tt)
            self.wizard().data["Tests"] = tests
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False
        
        fileName = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save Test Script As",
            filter="Test Script Files (*.yaml *.yml)"
        )

        if not fileName[0]:
            return False  # user canceled, keep wizard open

        self.wizard().data.pop("tt", None)
        with open(fileName[0] + ".yaml", "w") as f:
            safe_dump(self.wizard().data, f, sort_keys=False)

        return True

    def valsToDict(self, vals):
        d = {}
        for val in vals:
            d[val[0]] = val[1]
        return d

    def nextId(self):
        return PageNum.End

class TestScriptWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Script Wizard")
        # self.resize()
        self.data = {}

        self.addPage(SelectOptPage())
        self.addPage(ChipInfoPage())
        self.addPage(GlobalParametersPage())
        self.addPage(PinMapPage())
        self.addPage(TruthTablePage())
        self.addPage(TestsPage())

    @staticmethod
    def dropdown(items):
        dropdown = QComboBox()
        dropdown.addItem("")
        dropdown.addItems(items)
        return dropdown
    
    @staticmethod
    def pinSpinbox():
        spinbox = QSpinBox()
        spinbox.setRange(1, MAX_PINS)
        return spinbox
    
    @staticmethod
    def doubleSpinBox():
        doublebox = QDoubleSpinBox()
        doublebox.setMinimum(0)
        doublebox.setDecimals(2)
        doublebox.setSingleStep(0.01)
        return doublebox
    