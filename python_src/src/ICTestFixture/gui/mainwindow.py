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
os.environ["QTAUTOSCREENSCALEFACTOR"] = "0" # Force Qt to NOT auto scale
os.environ["QTSCALEFACTOR"] = "1.0" # Force the scale factor
os.environ["QTSCREENSCALEFACTORS"] = "1.0"
os.environ["XCURSORSIZE"] = "12"

class ChoiceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New Test Script")

        layout = QVBoxLayout(self)
        self.choice1 = QRadioButton("Plain Text Editor")
        self.choice2 = QRadioButton("Test Script Maker")
        layout.addWidget(self.choice1)
        layout.addWidget(self.choice2)

        buttonLayout = QHBoxLayout()
        self.confirm = QPushButton("Confirm")
        self.confirm.clicked.connect(self.accept)

        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.reject)

        buttonLayout.addWidget(self.confirm)
        buttonLayout.addWidget(self.cancel)

        layout.addLayout(buttonLayout)
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

        self.choiceDialog = ChoiceDialog(self)
        self.testScriptMaker = TestScriptMaker(self)
        # default screen to show when no files are open
        self.default = QLabel(
            "Create a new Test Script with Ctrl+N\nOpen an existing Test Script with Ctrl+O",
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.tabbedEditor = TabbedEditor(self)
        self.tabbedEditor.hide()
        # shows and hide default screen and editor based on if a file is opened/created
        self.tabbedEditor.tabAdded.connect(self.showEditor)
        self.tabbedEditor.noTabs.connect(self.showDefault)

        self.errorDisp = QTextEdit(self)
        self.errorDisp.setTextColor(QColor("red"))
        self.errorDisp.setReadOnly(True)

        # creates layout of GUI
        central = QWidget()
        layout = QVBoxLayout(central)
        # stretch factors relative to other stretch factors of widgets
        # 80% textEditor || default screen, 20% error display
        layout.addWidget(self.default, 8)
        layout.addWidget(self.tabbedEditor, 8)
        layout.addWidget(self.errorDisp, 2)
        self.setCentralWidget(central)

        self.menu = self.menuBar()
        self.buildMenu()

    def runTest(self):
        if self.tabbedEditor.isEmpty() == "":
            self.errorDisp.setPlainText("No Test Script Selected")
            return
        # save changes made in text editor before parsing
        if self.tabbedEditor.isModified():
            self.tabbedEditor.saveFile()

        try:
            chipInfo, testVecs = parser.parse(self.tabbedEditor.editorPath())

            for testVec in testVecs:
                testVec.dummyTest()
            # TODO: ask for save file name, otherwise use Path(filePath).stem as default
            report.exportToPdf(chipInfo, testVecs, "Test.pdf")
        except Exception as e:
            errorMsg = ""
            current = e
            # show traceback of errors to user without Python debugging msgs
            while current:
                errorMsg += f"{str(current)}\n" 
                current = current.__cause__
            self.errorDisp.setPlainText(errorMsg)

    def closeEvent(self, event):
        if not self.tabbedEditor.isEmpty() and self.tabbedEditor.anyModified():
            reply = QMessageBox.question(
                self,
                "Unsaved Work",
                "Do you want to save before quitting?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.tabbedEditor.onClose()
                event.accept()  # Allow window to close

    def newFile(self):
        if self.choiceDialog.exec():
            choice = self.choiceDialog.select()
            if choice == "Plain Text Editor":
                self.tabbedEditor.newFile()
            if choice == "Test Script Maker":
                print("Test Script Maker")
                pass
                # self.testScriptMaker

    def showEditor(self):
        self.tabbedEditor.show()
        self.default.hide()

    def showDefault(self):
        self.tabbedEditor.hide()
        self.default.show()

    def buildMenu(self):
        self._buildFileMenu()
        self._buildEditMenu()
        self._buildRunMenu()

    def _buildFileMenu(self):
        newFile = QAction("New File", self)
        newFile.triggered.connect(self.newFile)
        newFile.setShortcut("Ctrl+N")

        openFile = QAction("Open File", self)
        openFile.triggered.connect(self.tabbedEditor.openFile)
        openFile.setShortcut("Ctrl+O")

        saveFile = QAction("Save File", self)
        saveFile.triggered.connect(self.tabbedEditor.saveFile)
        saveFile.setShortcut("Ctrl+S")

        saveAs = QAction("Save As...", self)
        saveAs.triggered.connect(self.tabbedEditor.saveAs)
        saveAs.setShortcut("Ctrl+Shift+S")

        fileMenu = self.menu.addMenu("File")
        fileMenu.addAction(newFile)
        fileMenu.addAction(openFile)
        fileMenu.addSeparator()
        fileMenu.addAction(saveFile)
        fileMenu.addAction(saveAs)

    def _buildEditMenu(self):
        editMenu = self.menu.addMenu("Edit")
        editMenu.addAction("Undo", self.tabbedEditor.undo, "Ctrl+Z")
        editMenu.addAction("Redo", self.tabbedEditor.redo, "Ctrl+Y")
        editMenu.addSeparator()
        editMenu.addAction("Cut", self.tabbedEditor.cut, "Ctrl+X")
        editMenu.addAction("Copy", self.tabbedEditor.copy, "Ctrl+C")
        editMenu.addAction("Paste", self.tabbedEditor.paste, "Ctrl+V")

    def _buildRunMenu(self):
        run = QAction("Run", self) # make a button instead of dropdown menu
        run.triggered.connect(self.runTest)
        self.menu.addAction(run)
