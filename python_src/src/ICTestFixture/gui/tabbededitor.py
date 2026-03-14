from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QPlainTextEdit, QFileDialog

class TabbedEditor(QTabWidget):
    tabAdded = Signal()
    noTabs = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.editorPaths = {}
        self.newFileCount = 0

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.removeTab)

    def newTab(self, editor, filePath: str=None):
        if filePath:
            tabText = Path(filePath).stem
        else:
            tabText = f"Untitled {self.newFileCount}"
            self.newFileCount += 1

        self.editorPaths[editor] = filePath
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(self.modifiedTitle)
        self.addTab(editor, tabText)
        self.setCurrentWidget(editor)

        if self.count() == 1:
            self.tabAdded.emit()

    def newFile(self):
        editor = QPlainTextEdit()
        self.newTab(editor)

    def openFile(self):
        filePath = QFileDialog.getOpenFileName(
            parent=self,
            caption="Select Test Script",
            filter="Test Script Files (*.yaml *.yml)"
        )

        if filePath[0]:
            editor = QPlainTextEdit(self)
            with open(filePath[0], "r") as f:
                editor.setPlainText(f.read())
            self.newTab(editor, filePath[0])

    def saveFile(self):
        filePath = self.editorPaths[self.currentWidget()]
        if filePath:
            with open(filePath, "w") as f:
                f.write(self.currentWidget().toPlainText())
            self.currentWidget().document().setModified(False)
        else:
            self.saveAs()

    def saveAs(self):
        filePath = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save Test Script As",
            filter="Test Script Files (*.yaml *.yml)"
        )

        if filePath[0]:
            with open(filePath[0] + ".yaml", "w") as f:
                f.write(self.currentWidget().toPlainText())
            self.currentWidget().document().setModified(False)
            self.setTabText(self.currentIndex(), Path(filePath[0]).stem)
            self.editorPaths[self.currentWidget()] = filePath[0] + ".yaml"

    def removeTab(self, i):
        tabText = self.tabText(i)
        editor = self.widget(i)

        if editor.toPlainText().strip() == "":
            pass
        elif tabText.endswith("*") or tabText.startswith("Untitled"):
            self.saveFile(editor)

        self.editorPaths.pop(editor)
        self.removeTab(i)

        if self.count() == 0:
            self.noTabs.emit()

    def modifiedTitle(self):
        # adds asterisk to title, signals unsaved changes
        idx = self.currentIndex()
        title = self.tabText(idx)
        if not title.endswith("*"):
            self.setTabText(idx, self.tabText(idx) + "*")

    def onClose(self):
        for i in range(self.count()):
            self.setCurrentIndex(i)
            self.saveFile()

    def editorPath(self):
        return self.editorPaths[self.currentWidget()]

    def isEmpty(self):
        return self.count() == 0 or self.currentWidget().toPlainText().strip() == ""
    
    def isModified(self):
        return self.count() != 0 and self.currentWidget().document().isModified()
    
    def anyModified(self):
        if self.count() == 0:
            return False
        
        for i in range(self.count()):
            editor = self.widget(i)
            if editor.document().isModified():
                return True

    def undo(self):
        return self.currentWidget().undo()

    def redo(self):
        return self.currentWidget().redo()

    def cut(self):
        return self.currentWidget().cut()

    def copy(self):
        return self.currentWidget().copy()

    def paste(self):
        return self.setCurrentWidget().paste()
