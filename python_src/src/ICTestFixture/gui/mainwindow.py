from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
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

from ICTestFixture.core import parser, report
from ICTestFixture.gui.testscriptwizard import TestScriptWizard
from ICTestFixture.gui.tabbededitor import TabbedEditor

class ChoiceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New Test Script")
        self.setMinimumSize(250, 150) # orevents window title from being clipped

        self.opButton1 = QRadioButton("Plain Text Editor")
        self.opButton2 = QRadioButton("Test Script Wizard")

        confirmButton = QPushButton("Confirm")
        cancelButton = QPushButton("Cancel")

        confirmButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(confirmButton)
        buttonLayout.addWidget(cancelButton)

        layout = QVBoxLayout()
        layout.addWidget(self.opButton1)
        layout.addWidget(self.opButton2)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)

    def select(self):
        if self.opButton1.isChecked():
            return "Plain Text Editor"
        if self.opButton2.isChecked():
            return "Test Script Wizard"
        return "No Choice"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # window properties
        self.setWindowTitle("IC Test Fixture")
        self.resize(600, 400)

        self.choiceDialog = ChoiceDialog(self)
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

        self._buildMenu() # build last as its depedendent on tabbedEditor

        # creates layout of GUI
        central = QWidget()
        layout = QVBoxLayout(central)
        # stretch factors relative to other stretch factors of widgets
        # 80% textEditor || default screen, 20% error display
        layout.addWidget(self.default, 8)
        layout.addWidget(self.tabbedEditor, 8)
        layout.addWidget(self.errorDisp, 2)
        self.setCentralWidget(central)

    def runTest(self):
        if self.tabbedEditor.isEmpty() == "":
            self.errorDisp.setPlainText("No Test Script Selected")
            return
        # save changes made in text editor before parsing
        if self.tabbedEditor.isModified():
            self.tabbedEditor.saveFile()

        try:
            filePath = self.tabbedEditor.editorPath()
            chipInfo, testVecs = parser.parse(self.tabbedEditor.editorPath())

            for testVec in testVecs:
                testVec.dummyTest()
            # TODO: let user pick path to save to
            saveName = QFileDialog.getSaveFileName(
                parent=self,
                caption="Save File",
                dir=Path(filePath).stem,
                filter="PDF Files (*.pdf)"
            )
            
            report.exportToPdf(chipInfo, testVecs, f"{saveName[0]}.pdf")
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
            if choice == "Test Script Wizard":
                wizard = TestScriptWizard()
                wizard.exec()
                # self.testScriptMaker

    def showEditor(self):
        self.tabbedEditor.show()
        self.default.hide()

    def showDefault(self):
        self.tabbedEditor.hide()
        self.default.show()

    def _buildMenu(self):
        self.menu = self.menuBar()
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
