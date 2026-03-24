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
    parse_pin_map,
    parse_global_params,
    parse_truth_table,
    parse_tests
)

SORTED_VOLTAGES = sorted(SUPPORTED_VOLTAGES)
SORTED_INPUT = sorted(INPUT_LOGIC)
SORTED_OUTPUT = sorted(OUTPUT_LOGIC)
SORTED_LOGIC = sorted(TRUTH_TABLE_LOGIC)
PINS = [str(i) for i in range(1, MAX_PINS+1)]

def dropdown(items):
    dropdown = QComboBox()
    dropdown.addItem("")
    dropdown.addItems(items)
    return dropdown
    
def pinSpinbox():
    spinbox = QSpinBox()
    spinbox.setRange(1, MAX_PINS)
    return spinbox
    
def doubleSpinBox():
    doublebox = QDoubleSpinBox()
    doublebox.setMinimum(0)
    doublebox.setDecimals(2)
    doublebox.setSingleStep(0.01)
    return doublebox

def get_value(widget):
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

class PageNum(IntEnum):
    Select = 0
    ChipInfo = 1
    GlobalParameters = 2
    PinMap = 3
    TruthTable = 4
    Tests = 5
    End = -1

class DynamicContainer(QWidget):
    def __init__(self, parent, widget_types, headers):
        super().__init__(parent)
        self.widget_types = widget_types
        self.rows = []

        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        for col, header in enumerate(headers):
            self.grid.addWidget(QLabel(header), 0, col)
        self.grid.addWidget(QLabel(""), 0, len(headers))

        self.add_row()

        add_button = QToolButton()
        add_button.setText("Add Entry")
        add_button.clicked.connect(self.add_row)

        main_layout = QVBoxLayout()
        main_layout.addLayout(self.grid)
        main_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def add_row(self):
        row_widget = []
        row_idx = len(self.rows) + 1
        # insert before the stretch
        delete_button = QToolButton()
        delete_button.setText("-")
        delete_button.clicked.connect(lambda _, btn=delete_button: self.delete_row(btn))

        for col, widget_type in enumerate(self.widget_types):
            widget = widget_type()
            row_widget.append(widget)
            self.grid.addWidget(widget, row_idx, col)
        self.grid.addWidget(delete_button, row_idx, len(self.widget_types))

        self.rows.append((row_widget, delete_button))
    
    def delete_row(self, button):
        # prevents deleting when there is only one row
        if len(self.rows) <= 1:
            return
        
        row_idx = None
        for i, row in enumerate(self.rows):
            if button in row:
                row_idx = i
                break

        if row_idx is None:
            return
        
        widgets, btn = self.rows.pop(row_idx)
        for widget in widgets:
            self.grid.removeWidget(widget)
            widget.deleteLater()

        self.grid.removeWidget(btn)
        btn.deleteLater()

        for i in range(row_idx, len(self.rows)):
            widgets, btn = self.rows[i]
            for col, widget in enumerate(widgets):
                self.grid.addWidget(widget, i+1, col)
            self.grid.addWidget(btn, i+1, len(widgets))

    def extract_data(self):
        data = []
        for row in self.rows:
            values = []
            for widget in row[0]:
                values.append(get_value(widget))
            data.append(values)
        return data
        
    def __len__(self):
        return len(self.rows)

class SelectOptPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Select Optional Sections to Include")
        self.inc_chip_info = QCheckBox("Chip Info")
        self.inc_pin_map = QCheckBox("Pin Map")
        self.inc_truth_table = QCheckBox("Truth Table")

        self.registerField("inc_chip_info", self.inc_chip_info)
        self.registerField("inc_pin_map", self.inc_pin_map)
        self.registerField("inc_truth_table", self.inc_truth_table)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.inc_chip_info)
        main_layout.addWidget(self.inc_pin_map)
        main_layout.addWidget(self.inc_truth_table)
        self.setLayout(main_layout)

    def nextId(self):
        if self.field("inc_chip_info"): return PageNum.ChipInfo
        return PageNum.GlobalParameters

class ChipInfoPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Chip Info")

        self.data_entries = DynamicContainer(self, (QLineEdit, QLineEdit), ("Parameter", "Value"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.data_entries)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(main_layout)
    
    def validatePage(self):
        data = self.data_entries.extract_data()
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
            ("VCC Pin", pinSpinbox),
            ("GND Pin", pinSpinbox),
            ("VCC Voltage", lambda: dropdown(SORTED_VOLTAGES)),
            ("Output Low", doubleSpinBox),
            ("Output High", doubleSpinBox),
            ("Input Low (Opt.)", doubleSpinBox),
            ("Input High (Opt.)", doubleSpinBox)
        ]
        LABEL_WIDTH = 100
        WIDGET_WIDTH = 60

        self.global_params = {}

        main_layout = QGridLayout()
        for row, (param, widget_func) in enumerate(PARAMS):
            label = QLabel(param)
            label.setFixedWidth(LABEL_WIDTH)

            widget = widget_func() if widget_func else QLineEdit()
            widget.setFixedWidth(WIDGET_WIDTH)

            main_layout.addWidget(label, row, 0)
            main_layout.addWidget(widget, row, 1)
            if param.endswith("(Opt.)"):
                checkbox = QCheckBox()
                main_layout.addWidget(checkbox, row, 2)
                param = param.removesuffix(" (Opt.)")
                self.global_params[param] = (widget, checkbox)
            else:
                self.global_params[param] = widget

        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def validatePage(self):
        global_params = {}
        for param, widget in self.global_params.items():
            if param == "Input Low" or param == "Input High":
                if widget[1].isChecked():
                    global_params[param] = get_value(widget[0])
            else:
                global_params[param] = get_value(widget)

        try:
            parse_global_params(global_params)
            self.wizard().data["Global Parameters"] = global_params
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self):
        if self.field("inc_pin_map"): return PageNum.PinMap
        if self.field("inc_truth_table"): return PageNum.TruthTable
        return PageNum.Tests

class PinMapPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Pin Map")

        self.data_entries = DynamicContainer(self, (QLineEdit, pinSpinbox), ("Pin Name", "Pin Number"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(250)
        scroll.setWidget(self.data_entries)

        layout = QVBoxLayout()
        layout.addWidget(scroll, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

    def validatePage(self):
        data = self.data_entries.extract_data()
        pin_map = {}
        for d in data:
            pin_map[d[0]] = d[1]

        vcc_pin = self.wizard().data["Global Parameters"]["VCC Pin"]
        gnd_pin = self.wizard().data["Global Parameters"]["GND Pin"]

        try:
            parse_pin_map(pin_map, vcc_pin, gnd_pin)
            self.wizard().data["Pin Map"] = pin_map
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self):
        if self.field("inc_truth_table"): return PageNum.TruthTable
        return PageNum.Tests

class TruthTablePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Truth Table")

        self.data_entries = None
        self.line_widgets = []
        self.entry_layout = QVBoxLayout()

        self.edit_dialog = QDialog(self)
        self.edit_dialog.setWindowTitle("Edit Columns")

        spinbox = pinSpinbox()
        spinbox.valueChanged.connect(self.update_entry_layout)

        confirm_button = QPushButton("Confirm")
        cancel_button = QPushButton("Cancel")

        button_layout = QHBoxLayout()
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)

        confirm_button.clicked.connect(self.update_col_names)
        cancel_button.clicked.connect(self.edit_dialog.reject)

        edit_layout = QVBoxLayout()
        edit_layout.addWidget(spinbox)
        edit_layout.addLayout(self.entry_layout)
        edit_layout.addLayout(button_layout)
        self.edit_dialog.setLayout(edit_layout)

        edit_button = QToolButton()
        edit_button.setText("Edit")
        edit_button.clicked.connect(self.edit_dialog.exec)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(edit_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.main_layout)

    def update_entry_layout(self, val):
        while len(self.line_widgets) > val:
            widget = self.line_widgets.pop()
            widget.deleteLater()

        while len(self.line_widgets) < val:
            line_widget = QLineEdit()
            self.line_widgets.append(line_widget)
            self.entry_layout.addWidget(line_widget)

    def update_col_names(self):
        col_names = []
        dropdowns = []
        for line_widget in self.line_widgets:
            dropdowns.append(lambda: dropdown(TRUTH_TABLE_LOGIC))
            col_names.append(line_widget.text())

        if self.data_entries:
            self.data_entries.deleteLater()
        self.data_entries = DynamicContainer(self, dropdowns, col_names)
        self.main_layout.addWidget(self.data_entries)
        self.edit_dialog.accept()

    def validatePage(self):
        truth_table = []
        for row in self.data_entries.extract_data():
            truth_table.append(self.val_to_dict(row))

        try:
            tt = parse_truth_table(truth_table)
            self.wizard().data["Truth Table"] = truth_table
            self.wizard().data["tt"] = tt
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False
        
    def val_to_dict(self, vals):
        d = {}
        for i in range(len(self.line_widgets)):
            d[self.line_widgets[i].text()] = vals[i]
        return d

    def nextId(self):
        return PageNum.Tests

class TestsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tests")

        self.test_widgets = {}

        self.tabs = QTabWidget()
        self.tabs.tabCloseRequested.connect(self.delete_test)

        add_test_button = QToolButton()
        add_test_button.setText("Add Test")
        add_test_button.clicked.connect(self.get_test_name)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(add_test_button, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def initializePage(self):
        pins = []
        pin_map = self.wizard().data.get("Pin Map")
        if pin_map:
            for pin_name in pin_map:
                pins.append(pin_name)
        pins.extend(PINS)
        
        input_with_tt = []
        output_with_tt = []
        truth_table = self.wizard().data.get("Truth Table")
        if truth_table:
            for col_name in truth_table[0].keys():
                input_with_tt.append(col_name)
                output_with_tt.append(col_name)
        input_with_tt.extend(INPUT_LOGIC)
        output_with_tt.extend(OUTPUT_LOGIC)

        self.drop_pin = lambda: dropdown(pins)
        self.drop_input = lambda: dropdown(input_with_tt)
        self.drop_output = lambda: dropdown(output_with_tt)

    def get_test_name(self):
        test_name, confirm = QInputDialog.getText(self, "Enter Test Name", "Test Name:")
        if test_name and confirm:
            self.add_test(test_name)

    def add_test(self, test_name):
        test_input = DynamicContainer(self, (self.drop_pin, self.drop_input), ("Pin(s)", "Value(s)"))
        test_output = DynamicContainer(self, (self.drop_pin, self.drop_output), ("Pin(s)", "Value(s)"))

        test_layout = QVBoxLayout()
        test_layout.addWidget(QLabel("Input(s)"), alignment=Qt.AlignmentFlag.AlignCenter)
        test_layout.addWidget(test_input)
        test_layout.addWidget(QLabel("Output(s)", alignment=Qt.AlignmentFlag.AlignCenter))
        test_layout.addWidget(test_output)

        test_widget = QWidget()
        test_widget.setLayout(test_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(test_widget)

        test = {"Inputs": test_input, "Outputs": test_output}
        self.test_widgets[test_name] = test
        self.tabs.addTab(scroll, test_name)
        
    def delete_test(self, i):
        reply = QMessageBox.question(
            self,
            "Deleting Test",
            "Are you sure you want to delete this test?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            test_widget = self.tabs.widget(i)
            test_name = self.tabs.tabText(i)

            self.test_widgets.pop(test_name)
            self.tabs.removeTab(i)
            test_widget.deleteLater()

    def validatePage(self):
        tests = {}
        for test_name, test_widgets in self.test_widgets.items():
            input_data = self.vals_to_dict(test_widgets["Inputs"].extract_data())
            output_data = self.vals_to_dict(test_widgets["Outputs"].extract_data())
            tests[test_name] = {"Inputs": input_data, "Outputs": output_data}

        global_params = self.wizard().data.get("Global Parameters")
        pin_map = self.wizard().data.get("Pin Map")
        tt = self.wizard().data.get("tt")

        try:
            parse_tests(tests, global_params, pin_map, tt)
            self.wizard().data["Tests"] = tests
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False
        
        save_name, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save Test Script As",
            filter="Test Script Files (*.yaml *.yml)"
        )

        if not save_name[0]:
            return False  # user canceled, keep wizard open

        self.wizard().data.pop("tt", None)
        with open(f"{save_name}.yaml", "w") as f:
            safe_dump(self.wizard().data, f, sort_keys=False)

        return True

    def vals_to_dict(self, vals):
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
    