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
pins = [str(i) for i in range(1, MAX_PINS+1)]

class MultiComboBox(QComboBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        self.setModel(QStandardItemModel(self))
        self.model().dataChanged.connect(self.update_text)

    def addItem(self, text: str):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts: list[str]):
        for text in texts:
            self.addItem(text)

    def update_text(self):
        selected_items = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                selected_items.append(item.text())

        self.lineEdit().setText(",".join(selected_items))

class PinValRow(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        
        layout = QHBoxLayout()

        self.multi_box = MultiComboBox(self)
        self.multi_box.addItems(pins)

        self.value = QLineEdit(self)

        self.delete = QToolButton(self)
        self.delete.setText("-")
        self.delete.clicked.connect(self.delete_row)

        layout.addWidget(self.multi_box)
        layout.addWidget(self.value)
        layout.addWidget(self.delete)

        self.setLayout(layout)

    def delete_row(self):
        parent_layout = self.parent().layout()
        parent_layout.removeWidget(self)
        self.deleteLater()


class TestScriptMaker(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = {}

        self.setWindowTitle("Test Script Maker")

        self.add_test = QToolButton("Add Test")
        self.add_test.connect(self.create_test())

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.create_global_parameters())

        self.tests_layout = self.create_tests()
        main_layout.addLayout(self.tests_layout)

        self.setLayout(main_layout)

    def create_global_parameters(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Global Parameters"))

        layout.addLayout(self.sub_arg("VCC Pin", self.pin_spinbox()))
        layout.addLayout(self.sub_arg("GND Pin", self.pin_spinbox()))
        layout.addLayout(self.sub_arg("VCC Voltage", self.dropdown(SORTED_VOLTAGES)))
        layout.addLayout(self.sub_arg("Output Low"))
        layout.addLayout(self.sub_arg("Output High"))
        layout.addLayout(self.sub_arg("Input Low (Opt.)"))
        layout.addLayout(self.sub_arg("Input High (Opt.)"))

        return layout
    
    def create_tests(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Tests"))
        layout.addWidget(self.add_test)
        return layout
    
    def create_test(self):
        layout = QVBoxLayout()

        headers = QHBoxLayout()
        headers.addWidget(QLabel("Pin(s)"))
        headers.addWidget(QLabel("Logic"))

        layout.addWidget(QLabel("Inputs"))
        layout.addLayout(headers)

        layout.addWidget(QLabel("Outputs"))
        layout.addLayout(headers)

        # insert into Tests Layout
        layout.addLayout(self.sub_arg("Test Name"))
        layout.addLayout(headers)

    def dropdown(self, items):
        dropdown = QComboBox()
        dropdown.addItem("")
        dropdown.addItems(items)
        return dropdown
    
    def pin_spinbox(self):
        spinbox = QSpinBox()
        spinbox.setRange(1, MAX_PINS)
        return spinbox

    def sub_arg(self, title: str, selection_box: QWidget=None):
        hlayout = QHBoxLayout()

        label = QLabel(title)
        label.setIndent(30)

        hlayout.addWidget(label)
        widget = selection_box if selection_box else QLineEdit()
        hlayout.addWidget(widget)

        return hlayout
