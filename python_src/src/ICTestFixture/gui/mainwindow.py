import os
from ICTestFixture.core import parser, report
from ICTestFixture.gui.testscriptmaker import TestScriptMaker
from ICTestFixture.gui.tabbededitor import TabbedEditor
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QDialog,
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
# fixes DPI issues on high resolution displays
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0" # Force Qt to NOT auto scale
os.environ["QT_SCALE_FACTOR"] = "1.0" # Force the scale factor
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1.0"
os.environ["XCURSOR_SIZE"] = "12"

class ChoiceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New Test Script")

        layout = QVBoxLayout(self)
        self.choice1 = QRadioButton("Plain Text Editor")
        self.choice2 = QRadioButton("Test Script Maker")
        layout.addWidget(self.choice1)
        layout.addWidget(self.choice2)

        button_layout = QHBoxLayout()
        self.confirm = QPushButton("Confirm")
        self.confirm.clicked.connect(self.accept)

        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.reject)

        button_layout.addWidget(self.confirm)
        button_layout.addWidget(self.cancel)

        layout.addLayout(button_layout)
        self.setMinimumSize(250, 150) # orevents window title from being clipped

    def select(self):
        if self.choice1.isChecked():
            return "Plain Text Editor"
        if self.choice2.isChecked():
            return "Test Script Maker"
        return "No Choice"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # window properties
        self.setWindowTitle("IC Test Fixture")
        self.resize(600, 400)

        self.choice_dialog = ChoiceDialog(self)
        self.test_script_maker = TestScriptMaker(self)
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

        self.error_disp = QTextEdit(self)
        self.error_disp.setTextColor(QColor("red"))
        self.error_disp.setReadOnly(True)

        # creates layout of GUI
        central = QWidget()
        layout = QVBoxLayout(central)
        # stretch factors relative to other stretch factors of widgets
        # 80% text_editor || default screen, 20% error display
        layout.addWidget(self.default, 8)
        layout.addWidget(self.tabbed_editor, 8)
        layout.addWidget(self.error_disp, 2)
        self.setCentralWidget(central)

        self.menu = self.menuBar()
        self.build_menu()

    def run_test(self):
        if self.tabbed_editor.is_empty() == "":
            self.error_disp.setPlainText("No Test Script Selected")
            return
        # save changes made in text editor before parsing
        if self.tabbed_editor.is_modified():
            self.tabbed_editor.save_file()

        try:
            chip_info, test_vecs = parser.parse(self.tabbed_editor.editor_path())

            for test_vec in test_vecs:
                test_vec.dummy_test()
            # TODO: ask for save file name, otherwise use Path(file_path).stem as default
            report.export_to_pdf(chip_info, test_vecs, "Test.pdf")
        except Exception as e:
            error_msg = ""
            current = e
            # show traceback of errors to user without Python debugging msgs
            while current:
                error_msg += f"{str(current)}\n" 
                current = current.__cause__
            self.error_disp.setPlainText(error_msg)

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
        if self.choice_dialog.exec():
            choice = self.choice_dialog.select()
            if choice == "Plain Text Editor":
                self.tabbed_editor.new_file()
            if choice == "Test Script Maker":
                print("Test Script Maker")
                pass
                # self.test_script_maker

    def show_editor(self):
        self.tabbed_editor.show()
        self.default.hide()

    def show_default(self):
        self.tabbed_editor.hide()
        self.default.show()

    def build_menu(self):
        self._build_file_menu()
        self._build_edit_menu()
        self._build_run_menu()

    def _build_file_menu(self):
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

    def _build_edit_menu(self):
        edit_menu = self.menu.addMenu("Edit")
        edit_menu.addAction("Undo", self.tabbed_editor.undo, "Ctrl+Z")
        edit_menu.addAction("Redo", self.tabbed_editor.redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("Cut", self.tabbed_editor.cut, "Ctrl+X")
        edit_menu.addAction("Copy", self.tabbed_editor.copy, "Ctrl+C")
        edit_menu.addAction("Paste", self.tabbed_editor.paste, "Ctrl+V")

    def _build_run_menu(self):
        run = QAction("Run", self) # make a button instead of dropdown menu
        run.triggered.connect(self.run_test)
        self.menu.addAction(run)
