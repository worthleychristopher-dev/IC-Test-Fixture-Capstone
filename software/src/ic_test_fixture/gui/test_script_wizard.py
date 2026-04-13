from yaml import safe_dump
from enum import IntEnum
from typing import Type
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
from ic_test_fixture.fileIO.parser import (
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

def dropdown(items: list) -> QComboBox:
    """Returns `QComboBox` widget with entries of `items`."""
    dropdown = QComboBox()
    dropdown.addItem("")
    for item in items:
        dropdown.addItem(str(item)) # items must be string
    return dropdown
    
def pinSpinbox() -> QSpinBox:
    """Returns `QSpinBox` widget with max range from 1 to `MAX_PINS`."""
    spinbox = QSpinBox()
    spinbox.setRange(1, MAX_PINS)
    return spinbox
    
def doubleSpinBox() -> QDoubleSpinBox:
    """Returns `QDoubleSpinBox` widget"""
    doublebox = QDoubleSpinBox()
    doublebox.setMinimum(0)
    doublebox.setDecimals(2)
    doublebox.setSingleStep(0.01)
    return doublebox

def get_value(widget: QWidget) -> str|int|float:
    """Returns value of `QWidget` object. Raises `NotImplementedError` if widget type is unknown."""
    if isinstance(widget, QLineEdit):
        return widget.text()
    elif isinstance(widget, QComboBox):
        return widget.currentText()
    elif isinstance(widget, QSpinBox):
        return widget.value()
    elif isinstance(widget, QDoubleSpinBox):
        return widget.value()
    else:
        raise NotImplementedError(
            f"Extraction for ({type(widget)}) has not been implemented."
        )

class PageNum(IntEnum):
    """Enumeration for page numbers QWizardPage
    
    Page numbers matters as sections of the test script are dependendent on other sections.

    Attributes:
        Select: SelectOptPage page number.
        ChipInfo: ChipInfoPage page numebr.
        GlobalParameters: GlobalParameters page number.
        PinMap: PinMap page number.
        TruthTable: TruthTablePage page number.
        Tests: TestsPage page number.
        End: End of QWizard, always -1.
    """
    Select = 0
    ChipInfo = 1
    GlobalParameters = 2
    PinMap = 3
    TruthTable = 4
    Tests = 5
    End = -1

class TestScriptWizard(QWizard):
    """High level test script generation for users.

    `TestScriptWizard` offers high level user-support for generating .yaml test scripts
    required to interface with the hardware test fixture. This is implemented by making
    entries mainly in the form of various dropdown menus offered by PySide6. These dropwdown
    menus are restricted to the defined macros of the parsing algortihm. Each page implements
    their own `validatePage` which calls their respective parser function from parser.py to
    verify that user inputs are valid before moving on to subsequent pages. The last page asks
    for the location to the save the generated .yaml test script.

    Attributes:
        data (dict): shared data between all pages via `self.wizard().data`.
    """
    def __init__(self):
        """Initialize TestScriptWizard instance."""
        super().__init__()
        self.setWindowTitle("Test Script Wizard")
        self.data = {} # shared dict for all QWizardPage

        self.setPage(PageNum.Select, SelectOptPage())
        self.setPage(PageNum.ChipInfo, ChipInfoPage())
        self.setPage(PageNum.GlobalParameters, GlobalParametersPage())
        self.setPage(PageNum.PinMap, PinMapPage())
        self.setPage(PageNum.TruthTable, TruthTablePage())
        self.setPage(PageNum.Tests, TestsPage())

class DynamicContainer(QWidget):
    """Dynamically creates table-like entries of various `QWidget` objects.

    Creates a grid array of specified `QWidget` types and methods to extract data from widgets.
    An add entry button is used for the user to add more rows of the specified widget types.
    By default, `DynamicContainer` starts with one row, and will not allow it to be deleted until
    more rows are added. A delete button is created with every row allowing users to delete entries 
    if they are no longer needed. Deleting will fail if there is only one row remaining.

    Attributes:
        widget_types (tuple[Type[QWidget], ...]): Types of widgets to create for each row.
        rows (list): References of each row, each element contains a tuple of widgets and delete button.
        grid (QGridLayout): Grid layout to place each widget by coordinates of the grid.

    Args:
        parent (QWidget): UI element responsible for `DynamicContainer` widget.
        widget_types (tuple[Type[QWidget], ...]): Types of widgets to create for each row.
        headers (tuple[str], ...): Names for each column of the table.
    """
    def __init__(self, parent: QWidget, widget_types: list[Type[QWidget]], headers: list[str]) -> None:
        """Initializes DynamicContainer instance."""
        super().__init__(parent)
        self.widget_types = widget_types
        self.rows = []

        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        if len(widget_types) != len(headers):
            raise ValueError("Length of header and length of column must be the same.")
        # create header row (row=0)
        for col, header in enumerate(headers):
            self.grid.addWidget(QLabel(header), 0, col)
        self.grid.addWidget(QLabel(""), 0, len(headers)) # no header over delete button

        self.add_row()

        add_button = QToolButton()
        add_button.setText("Add Entry")
        add_button.clicked.connect(self.add_row)

        main_layout = QVBoxLayout()
        main_layout.addLayout(self.grid)
        main_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def add_row(self) -> None:
        """Creates a new row with specified widgets and a delete button."""
        row_widget = []
        row_idx = len(self.rows) + 1
        # insert before the stretch
        delete_button = QToolButton()
        delete_button.setText("-")
        # need lamda because it wraps self.delete_row(btn) as a function object instead of executing
        delete_button.clicked.connect(lambda _, btn=delete_button: self.delete_row(btn))

        for col, widget_type in enumerate(self.widget_types):
            widget = widget_type()
            row_widget.append(widget)
            self.grid.addWidget(widget, row_idx, col)
        self.grid.addWidget(delete_button, row_idx, len(self.widget_types))
        # store references to later extract data from widgets and row deletion
        self.rows.append((row_widget, delete_button))
    
    def delete_row(self, button: QToolButton) -> None:
        """Removes row containing the button's reference and shifts remaining rows up."""
        # prevents deleting when there is only one row
        if len(self.rows) <= 1:
            return
        # search for row with button to be deleted
        row_idx = None
        for i, row in enumerate(self.rows):
            if button in row:
                row_idx = i
                break

        if row_idx is None:
            # failed to find row with that delete button reference
            # button should be connected to this function in add_row()
            return
        # delete all widgets and button
        widgets, btn = self.rows.pop(row_idx)
        for widget in widgets:
            self.grid.removeWidget(widget)
            widget.deleteLater()

        self.grid.removeWidget(btn)
        btn.deleteLater()
        # move all rows beneath it up 1, +1 for header row
        for i in range(row_idx, len(self.rows)):
            widgets, btn = self.rows[i]
            for col, widget in enumerate(widgets):
                # addWidget moves the widget if its already inside the layout
                # does not create a new instances
                self.grid.addWidget(widget, i+1, col)
            self.grid.addWidget(btn, i+1, len(widgets))

    def extract_data(self) -> list:
        """Extracts data from all of the widgets in each row and return as a list."""
        data = []
        for row in self.rows:
            values = []
            for widget in row[0]:
                values.append(get_value(widget))
            data.append(values)
        return data

class SelectOptPage(QWizardPage):
    """Selection Page for optional sections of the test script.
    
    Selected options in the form of `QCheckBox` widgets, will be used to display optional pages. 
    """
    def __init__(self) -> None:
        """Initializes SelectOptPage instance."""
        super().__init__()
        self.setTitle("Select Optional Sections to Include")

        self.inc_chip_info = QCheckBox("Chip Info")
        self.inc_pin_map = QCheckBox("Pin Map")
        self.inc_truth_table = QCheckBox("Truth Table")
        # registerField creates shared information between all pages QWizard
        # used for determining nextID implementation for all pages
        self.registerField("inc_chip_info", self.inc_chip_info)
        self.registerField("inc_pin_map", self.inc_pin_map)
        self.registerField("inc_truth_table", self.inc_truth_table)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.inc_chip_info)
        main_layout.addWidget(self.inc_pin_map)
        main_layout.addWidget(self.inc_truth_table)
        self.setLayout(main_layout)

    def nextId(self) -> int:
        """Next `QWizardPage` to go to."""
        if self.field("inc_chip_info"): return PageNum.ChipInfo
        return PageNum.GlobalParameters

class ChipInfoPage(QWizardPage):
    """Chip Info Page for generating Chip Info section of the test script.

    Lets user include any information regarding the chip. This page is optional.

    Attributes:
        data_entries (DynamicContainer): Creates ("Parameter", QLineEdit), ("Value", QLineEdit).
    """
    def __init__(self) -> None:
        """Intializes ChipInfoPage instance."""
        super().__init__()
        self.setTitle("Chip Info")

        self.data_entries = DynamicContainer(self, (QLineEdit, QLineEdit), ("Parameter", "Value"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.data_entries)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(main_layout)
    
    def validatePage(self) -> bool:
        """Checks entries are valid and adds to shared dict before moving on."""
        data = self.data_entries.extract_data()
        chip_info = {}
        for d in data:
            chip_info[d[0]] = d[1]

        self.wizard().data["Chip Info"] = chip_info
        return True

    def nextId(self) -> int:
        """Next `QWizardPage` to go to."""
        return PageNum.GlobalParameters

class GlobalParametersPage(QWizardPage):
    """Global Parameters Page for generating Global Parameters section of the test script.
    
    Lets users enter information about chip that will be used all tests. All entry fields
    are created with respect to the defined macros of the parsing algorithm in parser.py.
    This page is required.

    Attributes:
        global_params (dict): Maps the parameter name to the widget.
    """
    def __init__(self) -> None:
        """Initializes GlobalParametersPage instance."""
        super().__init__()
        self.setTitle("Global Parameters")

        PARAMS = [
            ("VCC Pin", pinSpinbox),
            ("GND Pin", pinSpinbox),
            ("VCC Voltage", lambda: dropdown(SORTED_VOLTAGES)), # lambda for function object
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
                # keep self.global_params the expected format for parse_global_params()
                # expects "Input Low", and "Input High"
                checkbox = QCheckBox()
                main_layout.addWidget(checkbox, row, 2)
                param = param.removesuffix(" (Opt.)")
                self.global_params[param] = (widget, checkbox)
            else:
                self.global_params[param] = widget

        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def validatePage(self) -> bool:
        """Checks entries are valid and adds to shared dict before moving on."""
        global_params = {}
        for param, widget in self.global_params.items():
            if param == "Input Low" or param == "Input High":
                # optional, only add if checked
                if widget[1].isChecked():
                    global_params[param] = get_value(widget[0])
            else:
                # QComboBox value is a string, VCC voltage is needs to be float
                if param == "VCC Voltage": global_params[param] = float(get_value(widget))
                else: global_params[param] = get_value(widget)
        # parse the global_params for validity
        try:
            parse_global_params(global_params)
            self.wizard().data["Global Parameters"] = global_params
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self) -> int:
        """Next `QWizardPage` to go to."""
        if self.field("inc_pin_map"): return PageNum.PinMap
        if self.field("inc_truth_table"): return PageNum.TruthTable
        return PageNum.Tests

class PinMapPage(QWizardPage):
    """Pin Map Page for generating the Pin Map section of the test script.
    
    Lets user provide names for pins to provided abstraction for pins when generating the tests section
    of the test script. All entry fields are created with respect to the defined macros of the 
    parsing algorithm in parser.py. This page is optional.

    Attributes:
        data_entries (DynamicContainer): Creates ("Pin Name", QLineEdit), ("Pin Number", pinSpinbox).
    """
    def __init__(self) -> None:
        """Initializes PinMapPage instance."""
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

    def validatePage(self) -> bool:
        """Checks entries are valid and adds to shared dict before moving on."""
        pin_map = {}
        for row in self.data_entries.extract_data():
            pin_map[row[0]] = row[1]

        vcc_pin = self.wizard().data["Global Parameters"]["VCC Pin"]
        gnd_pin = self.wizard().data["Global Parameters"]["GND Pin"]
        # parse the pin_map for validity
        try:
            parse_pin_map(pin_map, vcc_pin, gnd_pin)
            self.wizard().data["Pin Map"] = pin_map
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self) -> int:
        """Next `QWizardPage` to go to."""
        if self.field("inc_truth_table"): return PageNum.TruthTable
        return PageNum.Tests

class TruthTablePage(QWizardPage):
    """Truth Table Page for generating the Truth Table section of the test scripts.

    Let users define a truth table, abstracting pin values to into strings. These abstractions
    are used when generating the tests section of the test script. All entry fields are created
    with respect to the defined macros of the  parsing algorithm in parser.py. This page is optional.

    Attributes:
        data_entries (DynamicContainer): (`col_names`, dropdown(TRUTH_TABLE_LOGIC))
        line_widgets (List[QLineEdit]): Inputs for defining the column names of the truth table.
        edit_dialog (QDialog): Allows the user to edit the number of columns and their names.
    """
    def __init__(self) -> None:
        """Intializes TruthTablePage instance."""
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

    def update_entry_layout(self, val) -> None:
        """Adds `QLineEdit` instances to `self.edit_dialog` window to input column names."""
        while len(self.line_widgets) > val:
            widget = self.line_widgets.pop()
            widget.deleteLater()

        while len(self.line_widgets) < val:
            line_widget = QLineEdit()
            self.line_widgets.append(line_widget)
            self.entry_layout.addWidget(line_widget)

    def update_col_names(self) -> None:
        """Deletes old `data_entries` and create new `DynamicContainer` when number of columns are changed."""
        col_names = []
        dropdowns = []
        for line_widget in self.line_widgets:
            dropdowns.append(lambda: dropdown(TRUTH_TABLE_LOGIC)) # lambda to create function object
            col_names.append(line_widget.text())

        if self.data_entries:
            self.data_entries.deleteLater()

        self.data_entries = DynamicContainer(self, dropdowns, col_names)
        self.main_layout.addWidget(self.data_entries)
        self.edit_dialog.accept()

    def validatePage(self) -> bool:
        """Checks entries are valid and adds to shared dict before moving on."""
        truth_table = []
        for row in self.data_entries.extract_data():
            d = {}
            for i in range(len(self.line_widgets)):
                d[self.line_widgets[i].text()] = row[i]
            truth_table.append(d)
        # parses truth_table for validity
        try:
            tt = parse_truth_table(truth_table)
            self.wizard().data["Truth Table"] = truth_table
            self.wizard().data["tt"] = tt # parsed version of truth table needed for parse_tests()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")
            return False

    def nextId(self) -> int:
        """Next `QWizardPage` to go to."""
        return PageNum.Tests

class TestsPage(QWizardPage):
    """Tests Page to generate the Tests section of the test script.

    Lets users create tests they want to be executed. The dropwdown menus include all abstracted
    variables from Pin Map and Truth Table pages if they were added. All entry fields are created
    with respect to the defined macros of the parsing algorithm in parser.py. This page is required.
    
    Attributes:
        tests_widgets (dict): Stores reference of created test QWidgets using the name of the test as they key.
        tabs (QTabWidget): Allows the user to switch between multiple tests they are creating.
    """
    def __init__(self) -> None:
        """Initializes TestsPage instance."""
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

    def initializePage(self) -> None:
        """Adds abstracted variables to entries. Called automatically after `__init__`"""
        # add abstracted pins to pin options
        pins = []
        pin_map = self.wizard().data.get("Pin Map")
        if pin_map:
            for pin_name in pin_map:
                pins.append(pin_name)
        pins.extend(PINS)
        
        # add abstracted pin values to pin value options
        input_with_tt = []
        output_with_tt = []
        truth_table = self.wizard().data.get("Truth Table")
        if truth_table:
            for col_name in truth_table[0].keys():
                input_with_tt.append(col_name)
                output_with_tt.append(col_name)
        input_with_tt.extend(INPUT_LOGIC)
        output_with_tt.extend(OUTPUT_LOGIC)
        # lambda to create function object
        self.drop_pin = lambda: dropdown(pins)
        self.drop_input = lambda: dropdown(input_with_tt)
        self.drop_output = lambda: dropdown(output_with_tt)

    def get_test_name(self) -> None:
        """Dialog asking user to enter the name of test to create."""
        test_name, confirm = QInputDialog.getText(self, "Enter Test Name", "Test Name:")
        if test_name and confirm:
            self.add_test(test_name)

    def add_test(self, test_name) -> None:
        # TODO: add QWidget for voltage input
        """Creates a `QWidget` that allows the inputs of pin and their values and adds it to the layout.
        
        The widget is created by using two separate `DynamicContainer` objects, one for the Inputs subsection,
        the other for the Outputs subsection of the test script. References to each object is stored in a dict
        which is then added to the main dict `self.test_widgets`. This does not support serial inputs.
        """
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
        
    def delete_test(self, i) -> None:
        """Delete the test if requested to close the tab."""
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

    def validatePage(self) -> bool:
        """Checks entries are valid and adds to shared dict before moving on."""
        tests = {}
        for test_name, test_widgets in self.test_widgets.items():
            input_data = self.vals_to_dict(test_widgets["Inputs"].extract_data())
            output_data = self.vals_to_dict(test_widgets["Outputs"].extract_data())
            tests[test_name] = {"Inputs": input_data, "Outputs": output_data}

        global_params = self.wizard().data.get("Global Parameters")
        pin_map = self.wizard().data.get("Pin Map")
        tt = self.wizard().data.get("tt")
        # parses test for validity
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

    def vals_to_dict(self, vals: list[list]) -> dict:
        """Converts the nested list into a dict."""
        d = {}
        for val in vals:
            d[val[0]] = val[1]
        return d

    def nextId(self) -> int:
        """Next `QWizardPage` to go to."""
        return PageNum.End
    