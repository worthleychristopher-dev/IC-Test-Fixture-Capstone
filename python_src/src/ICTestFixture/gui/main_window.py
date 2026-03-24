import html

from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QIODevice
from PySide6.QtGui import QAction
from PySide6.QtSerialPort import QSerialPort
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget
)

from ICTestFixture.fileIO import parser, report
from ICTestFixture.device.test_runner import TestRunner
from ICTestFixture.gui.test_script_wizard import TestScriptWizard
from ICTestFixture.gui.tabbed_editor import TabbedEditor

BAUDRATE = QSerialPort.BaudRate.Baud115200
PORT_NAME = ""

class ChoiceDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("New Test Script")
        self.setMinimumSize(250, 150) # prevents window title from being clipped

        self.op_button1 = QRadioButton("Plain Text Editor")
        self.op_button2 = QRadioButton("Test Script Wizard")

        confirm_button = QPushButton("Confirm")
        cancel_button = QPushButton("Cancel")

        confirm_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.op_button1)
        layout.addWidget(self.op_button2)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def select(self):
        if self.op_button1.isChecked():
            return "Plain Text Editor"
        if self.op_button2.isChecked():
            return "Test Script Wizard"
        return "No Choice"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # window properties
        self.setWindowTitle("IC Test Fixture")
        self.resize(600, 400)

        self.chip_info = None
        self.test_vecs = None

        self.serial = None
        QTimer.singleShot(0, self.init_serial) # runs after construction of main_window

        # default screen to show when no files are open
        self.default = QLabel(
            "Create a new Test Script with Ctrl+N\nOpen an existing Test Script with Ctrl+O",
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.tabbed_editor = TabbedEditor(self)
        self.tabbed_editor.hide()
        # shows and hide default screen and editor based on if a file is opened/created
        self.tabbed_editor.tab_added.connect(self.show_editor)
        self.tabbed_editor.no_tabs.connect(self.show_default)

        self.status_disp = QTextEdit(self)
        self.status_disp.setReadOnly(True)

        self._buildMenu() # build last as its depedendent on tabbed_editor

        # creates layout of GUI
        central = QWidget()
        main_layout = QVBoxLayout(central)
        # stretch factors relative to other stretch factors of widgets
        # 80% textEditor || default screen, 20% error display
        main_layout.addWidget(self.default, 8)
        main_layout.addWidget(self.tabbed_editor, 8)
        main_layout.addWidget(self.status_disp, 2)
        self.setCentralWidget(central)

    def init_serial(self):
        self.serial = QSerialPort()
        self.serial.setBaudRate(BAUDRATE)
        self.serial.setPortName(PORT_NAME)

        if self.serial.open(QIODevice.ReadWrite):
            self.add_status_msg("Serial port opened successfully")
        else:
            self.add_status_msg(f"ERR: Failed to open serial port, {self.serial.errorString()}")

    def run_test(self):
        if self.tabbed_editor.is_empty() == "":
            self.status_disp.setPlainText("No Test Script Selected")
            return
        # save changes made in text editor before parsing
        if self.tabbed_editor.is_modified():
            self.tabbed_editor.save_file()

        try:
            self.chip_info, self.test_vecs = parser.parse(self.tabbed_editor.editor_path())

            self.test_runner = TestRunner(self.serial, self.test_vecs)
            self.test_runner.status_msg.connect(self.add_status_msg)
            # self.test_runner.done.connect(self.export_results)
            self.test_runner.start_test()
            # for testVec in test_vecs:
            #     testVec.dummy_test()
        except Exception as e:
            err_msg = ""
            current = e
            # show traceback of errors to user without Python debugging msgs
            while current:
                err_msg += f"{type(current).__name__}: {current}\n"
                current = current.__cause__
            self.add_status_msg(err_msg)
        return

    # def export_results(self):
    #     save_name, _ = QFileDialog.getSaveFileName(
    #             parent=self,
    #             caption="Save File",
    #             dir=Path(self.tabbed_editor.editor_path()).stem,
    #             filter="PDF Files (*.pdf)"
    #         )
    #     report.export_to_pdf(self.chip_info, self.test_vecs, f"{save_name}.pdf")
    #     return

    def closeEvent(self, event):
        if not self.tabbed_editor.is_empty() and self.tabbed_editor.any_modified():
            reply = QMessageBox.question(
                self,
                "Unsaved Work",
                "Do you want to save before quitting?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.tabbed_editor.on_close()
                event.accept()  # Allow window to close

    def new_file(self):
        choice_dialog = ChoiceDialog()
        if choice_dialog.exec():
            choice = choice_dialog.select()
            if choice == "Plain Text Editor":
                self.tabbed_editor.new_file()
            if choice == "Test Script Wizard":
                wizard = TestScriptWizard()
                wizard.exec()
        return

    def show_editor(self):
        self.tabbed_editor.show()
        self.default.hide()

    def show_default(self):
        self.tabbed_editor.hide()
        self.default.show()

    def add_status_msg(self, msg: str):
        if msg.startswith("ERR") or "error" in msg.lower():
            color = "red"
        elif msg.startswith("SENT"):
            color = "blue"
        else:
            color = "green"
        # html.escape makes msg safe if it contains <>, or other formatting characters
        disp_msg = f"<span style=\"color:{color};\">{html.escape(msg)}</span>"

        self.status_disp.append(disp_msg)

    def _buildMenu(self):
        self.menu = self.menuBar()
        self._buildFileMenu()
        self._buildEditMenu()
        self._buildRunMenu()

    def _buildFileMenu(self):
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

    def _buildEditMenu(self):
        edit_menu = self.menu.addMenu("Edit")
        edit_menu.addAction("Undo", self.tabbed_editor.undo, "Ctrl+Z")
        edit_menu.addAction("Redo", self.tabbed_editor.redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("Cut", self.tabbed_editor.cut, "Ctrl+X")
        edit_menu.addAction("Copy", self.tabbed_editor.copy, "Ctrl+C")
        edit_menu.addAction("Paste", self.tabbed_editor.paste, "Ctrl+V")

    def _buildRunMenu(self):
        run = QAction("Run", self) # make a button instead of dropdown menu
        run.triggered.connect(self.run_test)
        self.menu.addAction(run)
