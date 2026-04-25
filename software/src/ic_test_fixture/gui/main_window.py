import html

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QRadioButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget
)
from ic_test_fixture.file_io import parser, report
from ic_test_fixture.device.serial_manager import BIST, SerialManager, TestRunner
from ..gui.test_script_wizard import TestScriptWizard
from ..gui.tabbed_editor import TabbedEditor

class ChoiceDialog(QDialog):
    """Dialog for creating a new test script.

    Offers selection choice of Plain Text Editor, and Test Script Wizard
    to the user to create a new test script. Layout of the dialog is
    `QRadioButton` (choices), `QPushButtons` (confirm/cancel).
    """
    def __init__(self) -> None:
        """Initializes a ChoiceDialog instance."""
        super().__init__()
        self.setWindowTitle("New Test Script")
        # choices
        self.op_button1 = QRadioButton("Plain Text Editor")
        self.op_button2 = QRadioButton("Test Script Wizard")
        # confirmation buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        # set layout
        layout = QVBoxLayout()
        layout.addWidget(self.op_button1)
        layout.addWidget(self.op_button2)
        layout.addWidget(self.buttons, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def select(self) -> str:
        """Returns choice made by the user."""
        if self.op_button1.isChecked():
            return "Plain Text Editor"
        if self.op_button2.isChecked():
            return "Test Script Wizard"
        return "No Choice"

class BISTDialog(QDialog):
    """Dialog for running BIST on the test fixture.
    
    Alerts user to remove IC from test fixture before running BIST.
    """
    run_bist_requested = Signal()
    def __init__(self) -> None:
        """Initializes a BISTDialog instance."""
        super().__init__()
        self.setWindowTitle("Built-In Self Test")
        # confirmation buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.run_bist)
        self.buttons.rejected.connect(self.reject)
        # set layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Remove IC from test fixture, and click OK to run BIST"))
        layout.addWidget(self.buttons, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def run_bist(self) -> None:
        """Emits signal to run BIST on test fixture."""
        self.run_bist_requested.emit()
        self.accept()
        return

class MainWindow(QMainWindow):
    """Main window of the GUI application.

    The ic_test_fixture application is a simple interface allowing users to either create or open
    an existing test script, and running it via the Run button in menu bar. Other features include
    standard text editor support, similar to NotePad, VSCode, etc. A status display is provided at
    the bottom of the window, displaying information of tasks handled in the background of the
    application. Any `QObject` with the attribute of `Signal(str)` can add messages to the status display
    by connecting it to the function `self.add_status_msg`. 

    `MainWindow` serves as connection point between all parts of this Python project.

    Attributes:
        chip_info (dict): Chip information of the current chip under test.
        test_vecs (list[TestVector]): List of tests of the current chip under test.
        serial (QSerialPort): Port for asynchronous communication with the test fixture.
        tabbed_editor (TabbedEditor): Text Editor widgets for opening and editing test scripts.
        status_disp (QTextEdit): Display for all status messages throughout the application.
    """
    def __init__(self, serial_manager: SerialManager) -> None:
        """Initializes MainWindow instance."""
        super().__init__()
        # window properties
        self.setWindowTitle("IC Test Fixture")
        self.resize(600, 400)

        self.serial_manager = serial_manager
        self.chip_info = None
        self.test_vecs = None
        # default screen to show when no files are open
        self.default = QLabel(
            "Create a new Test Script with Ctrl+N\nOpen an existing Test Script with Ctrl+O",
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.tabbed_editor = TabbedEditor(self)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.default)
        self.stack.addWidget(self.tabbed_editor)
        self.stack.setCurrentWidget(self.default)
        self.stack.setCurrentWidget(self.default)
        # shows and hide default screen and editor based on if a file is opened/created
        self.tabbed_editor.tab_added.connect(self.show_editor)
        self.tabbed_editor.no_tabs.connect(self.show_default)
        # displays all status msgs from serial communications, and errors raised from Python code
        self.status_disp = QTextEdit(self)
        self.status_disp.setReadOnly(True)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.stack)
        splitter.addWidget(self.status_disp)
        splitter.setSizes([800, 200]) # stretch factors relative to each other, 80% text editor, 20% status display

        self._build_menu() # build last as its depedendent on tabbed_editor

        # creates layout of GUI
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.addWidget(splitter)
        self.setCentralWidget(central)

    def run_test(self) -> None:
        """Parse and run test script currently in focus on `self.tabbed_editor` widget.
        
        Parses the test script that is on screen and creates a `TestRunner` object to execute all of
        the tests using `self.serial` for serial communication with the hardware test fixture. Signals
        of the `TestRunner` instance are connected to GUI elements to prevent the GUI thread from being
        completely frozen as tests are being executed.
        """
        if self.tabbed_editor.is_empty() == "":
            self.status_disp.setPlainText("No Test Script Selected")
            return
        # save changes made in text editor before parsing
        if self.tabbed_editor.is_modified():
            self.tabbed_editor.save_file()

        try:
            self.chip_info, self.test_vecs = parser.parse(self.tabbed_editor.editor_path())

            self.serial_manager.set_protocol(TestRunner, self.test_vecs)
            # connect signals to GUI elements
            self.serial_manager.status_msg.connect(self.add_status_msg)
            self.serial_manager.error.connect(self.enable_run)
            self.serial_manager.done.connect(self.enable_run)
            self.serial_manager.done.connect(self.export_results)
            # disable run button to prevent multiple test runs at the same time, re-enable when done or error
            self.run_menu.setEnabled(False)
            self.serial_manager.start_protocol()
        except Exception as e:
            err_msg = ""
            current = e
            # show traceback of errors to user without Python debugging msgs
            while current:
                err_msg += f"{type(current).__name__}: {current}"
                current = current.__cause__
            self.add_status_msg(err_msg)
        return

    def export_results(self) -> None:
        """Exports results after `TestRunner` executed all tests in `self.test_vecs` as a PDF document."""
        save_name, _ = QFileDialog.getSaveFileName(
                parent=self,
                caption="Save File",
                dir=Path(self.tabbed_editor.editor_path()).stem,
                filter="PDF Files (*.pdf)"
            )
        report.export_to_pdf(self.chip_info, self.test_vecs, f"{save_name}")
        return
    
    def new_file(self) -> None:
        """Executes `ChoiceDialog` to create a new file"""
        choice_dialog = ChoiceDialog()
        if choice_dialog.exec():
            choice = choice_dialog.select()
            if choice == "Plain Text Editor":
                self.tabbed_editor.new_file()
            if choice == "Test Script Wizard":
                wizard = TestScriptWizard()
                wizard.exec()
        return
    
    def open_bist_dialog(self) -> None:
        """Executes `BISTDialog`"""
        bist_dialog = BISTDialog()
        bist_dialog.run_bist_requested.connect(self.bist)
        bist_dialog.exec()
        return
    
    def bist(self) -> None:
        """Runs BIST on test fixture"""
        self.run_menu.setEnabled(False)
        self.serial_manager.set_protocol(BIST)
        # connect signals to GUI elements
        self.serial_manager.status_msg.connect(self.add_status_msg)
        self.serial_manager.error.connect(self.enable_run)
        self.serial_manager.done.connect(self.enable_run)
        self.serial_manager.start_protocol()
    
    def add_status_msg(self, msg: str) -> None:
        """Displays color coded messages from application to `self.status_disp`.
        
        Args:
            msg (str): Message to be displayed.
        """
        if msg.startswith("ERR") or "error" in msg.lower():
            color = "red"
        elif msg.startswith("SENT"):
            color = "blue"
        elif msg.startswith("STEP"):
            color = "purple"
        else:
            color = "green"
        # html.escape makes msg safe if it contains <>, or other formatting characters
        # html can't render "\n", so replace with <br> for newlines in status display
        disp_msg = f"<span style=\"color:{color};\">{html.escape(msg).replace('\n', '<br>')}</span>"

        self.status_disp.append(disp_msg)

    def closeEvent(self, event) -> None:
        """Actions to perform when user closes the main window."""
        if not self.tabbed_editor.is_empty() and self.tabbed_editor.any_modified():
            # ask to save all unsaved work before closing
            reply = QMessageBox.question(
                self,
                "Unsaved Work",
                "Do you want to save before quitting?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.tabbed_editor.on_close()
                event.accept()  # Allow window to close

    def show_editor(self) -> None:
        """Displays `self.tabbed_editor` when a file is open."""
        self.stack.setCurrentWidget(self.tabbed_editor)

    def show_default(self) -> None:
        """Displays text on how to open a file if no file is open."""
        self.stack.setCurrentWidget(self.default)

    def enable_run(self) -> None:
        """Enables run button"""
        self.run_menu.setEnabled(True)

    def _build_menu(self) -> None:
        """Builds menuBar widget of the main window"""
        self.menu = self.menuBar()
        self._build_file_menu()
        self._build_edit_menu()
        self._build_run_menu()

    def _build_file_menu(self) -> None:
        """Builds File menu."""
        new_file = QAction("New File", self)
        new_file.triggered.connect(self.new_file)
        new_file.setShortcut("Ctrl+N")

        open_file = QAction("Open File", self)
        open_file.triggered.connect(self.tabbed_editor.open_file)
        open_file.setShortcut("Ctrl+O")

        save_file = QAction("Save File", self)
        save_file.triggered.connect(self.tabbed_editor.save_file)
        save_file.setShortcut("Ctrl+S")

        save_as = QAction("Save As...", self)
        save_as.triggered.connect(self.tabbed_editor.save_as)
        save_as.setShortcut("Ctrl+Shift+S")

        file_menu = self.menu.addMenu("File")
        file_menu.addAction(new_file)
        file_menu.addAction(open_file)
        file_menu.addSeparator()
        file_menu.addAction(save_file)
        file_menu.addAction(save_as)

    def _build_edit_menu(self) -> None:
        """Builds Edit menu."""
        edit_menu = self.menu.addMenu("Edit")
        edit_menu.addAction("Undo", self.tabbed_editor.undo, "Ctrl+Z")
        edit_menu.addAction("Redo", self.tabbed_editor.redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("Cut", self.tabbed_editor.cut, "Ctrl+X")
        edit_menu.addAction("Copy", self.tabbed_editor.copy, "Ctrl+C")
        edit_menu.addAction("Paste", self.tabbed_editor.paste, "Ctrl+V")

    def _build_run_menu(self) -> None:
        """Builds Run menu."""
        run = QAction("Run", self) # make a button instead of dropdown menu
        run.triggered.connect(self.run_test)

        bist = QAction("BIST", self)
        bist.triggered.connect(self.open_bist_dialog)

        self.run_menu = self.menu.addMenu("Run")
        self.run_menu.addAction(run)
        self.run_menu.addSeparator()
        self.run_menu.addAction(bist)
