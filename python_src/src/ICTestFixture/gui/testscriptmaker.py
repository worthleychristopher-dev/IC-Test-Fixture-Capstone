from ICTestFixture.core.parser import INPUT_LOGIC, OUTPUT_LOGIC, TRUTH_TABLE_LOGIC, SUPPORTED_VOLTAGES, MAX_PINS
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget
)

SORTED_VOLTAGES = sorted(SUPPORTED_VOLTAGES)
SORTED_INPUT = sorted(INPUT_LOGIC)
SORTED_OUTPUT = sorted(OUTPUT_LOGIC)
SORTED_LOGIC = sorted(TRUTH_TABLE_LOGIC)
PINS = [str(i) for i in range(1, MAX_PINS+1)]

class MultiComboBox(QComboBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        self.setModel(QStandardItemModel(self))
        self.model().dataChanged.connect(self.updateText)

    def addItem(self, text: str):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts: list[str]):
        for text in texts:
            self.addItem(text)

    def updateText(self):
        selectedItems = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                selectedItems.append(item.text())

        self.lineEdit().setText(",".join(selectedItems))

class PinValRow(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        
        layout = QHBoxLayout()

        self.multiBox = MultiComboBox(self)
        self.multiBox.addItems(PINS)

        self.value = QLineEdit(self)

        self.delete = QToolButton(self)
        self.delete.setText("-")
        self.delete.clicked.connect(self.deleteRow)

        layout.addWidget(self.multiBox)
        layout.addWidget(self.value)
        layout.addWidget(self.delete)

        self.setLayout(layout)

    def deleteRow(self):
        parentLayout = self.parent().layout()
        parentLayout.removeWidget(self)
        self.deleteLater()


class TestScriptMaker(QDialog):
    def _Init__(self, parent):
        super()._Init__(parent)
        self.data = {}

        self.setWindowTitle("Test Script Maker")

        self.addTest = QToolButton("Add Test")
        self.addTest.connect(self.createTest())

        mainLayout = QVBoxLayout(self)
        mainLayout.addLayout(self.createGlobalParameters())

        self.testsLayout = self.createTests()
        mainLayout.addLayout(self.testsLayout)

        self.setLayout(mainLayout)

    def createGlobalParameters(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Global Parameters"))

        layout.addLayout(self.subArg("VCC Pin", self.pinSpinbox()))
        layout.addLayout(self.subArg("GND Pin", self.pinSpinbox()))
        layout.addLayout(self.subArg("VCC Voltage", self.dropdown(SORTED_VOLTAGES)))
        layout.addLayout(self.subArg("Output Low"))
        layout.addLayout(self.subArg("Output High"))
        layout.addLayout(self.subArg("Input Low (Opt.)"))
        layout.addLayout(self.subArg("Input High (Opt.)"))

        return layout
    
    def createTests(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Tests"))
        layout.addWidget(self.addTest)
        return layout
    
    def createTest(self):
        layout = QVBoxLayout()

        headers = QHBoxLayout()
        headers.addWidget(QLabel("Pin(s)"))
        headers.addWidget(QLabel("Logic"))

        layout.addWidget(QLabel("Inputs"))
        layout.addLayout(headers)

        layout.addWidget(QLabel("Outputs"))
        layout.addLayout(headers)

        # insert into Tests Layout
        layout.addLayout(self.subArg("Test Name"))
        layout.addLayout(headers)

    def dropdown(self, items):
        dropdown = QComboBox()
        dropdown.addItem("")
        dropdown.addItems(items)
        return dropdown
    
    def pinSpinbox(self):
        spinbox = QSpinBox()
        spinbox.setRange(1, MAX_PINS)
        return spinbox

    def subArg(self, title: str, selectionBox: QWidget=None):
        hlayout = QHBoxLayout()

        label = QLabel(title)
        label.setIndent(30)

        hlayout.addWidget(label)
        widget = selectionBox if selectionBox else QLineEdit()
        hlayout.addWidget(widget)

        return hlayout
