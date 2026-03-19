from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QPlainTextEdit, QFileDialog

class TabbedEditor(QTabWidget):
    tab_added = Signal()
    no_tabs = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.editor_paths = {}
        self.new_file_count = 0

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.remove_tab)

    def new_tab(self, editor, file_path: str=None):
        if file_path:
            tab_text = Path(file_path).stem
        else:
            tab_text = f"Untitled {self.new_file_count}"
            self.new_file_count += 1

        self.editor_paths[editor] = file_path
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(self.modified_title)
        self.addTab(editor, tab_text)
        self.setCurrentWidget(editor)

        if self.count() == 1:
            self.tab_added.emit()

    def new_file(self):
        editor = QPlainTextEdit()
        self.new_tab(editor)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Select Test Script",
            filter="Test Script Files (*.yaml *.yml)"
        )

        if file_path:
            editor = QPlainTextEdit(self)
            with open(file_path, "r") as f:
                editor.setPlainText(f.read())
            self.new_tab(editor, file_path)

    def save_file(self):
        if self.count() <= 0:
            return
        
        file_path = self.editor_paths[self.currentWidget()]
        if file_path:
            with open(file_path, "w") as f:
                f.write(self.currentWidget().toPlainText())
            self.currentWidget().document().setModified(False)
            tab_text = self.tabText(self.currentIndex())
            if tab_text.endswith("*"):
                self.setTabText(self.currentIndex(), tab_text[:-1])
        else:
            self.save_as()

    def save_as(self):
        if self.count() <= 0:
            return
        
        save_name, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save Test Script As",
            filter="Test Script Files (*.yaml *.yml)"
        )

        if save_name:
            save_with_ext = f"{save_name}.yaml"
            with open(save_with_ext, "w") as f:
                f.write(self.currentWidget().toPlainText())
            self.currentWidget().document().setModified(False)
            self.setTabText(self.currentIndex(), Path(save_name).stem)
            self.editor_paths[self.currentWidget()] = save_with_ext
            

    def remove_tab(self, i):
        tab_text = self.tabText(i)
        editor = self.widget(i)

        if editor.toPlainText().strip() == "":
            pass
        elif tab_text.endswith("*") or tab_text.startswith("Untitled"):
            self.save_file()

        self.editor_paths.pop(editor, None)
        self.removeTab(i)
        editor.deleteLater()

        if self.count() == 0:
            self.no_tabs.emit()

    def modified_title(self):
        # adds asterisk to title, signals unsaved changes
        idx = self.currentIndex()
        title = self.tabText(idx)
        if not title.endswith("*"):
            self.setTabText(idx,  f"{title}*")

    def on_close(self):
        for i in range(self.count()):
            self.setCurrentIndex(i)
            self.save_file()

    def editor_path(self):
        return self.editor_paths[self.currentWidget()]

    def is_empty(self):
        return self.count() == 0 or self.currentWidget().toPlainText().strip() == ""
    
    def is_modified(self):
        return self.count() != 0 and self.currentWidget().document().isModified()
    
    def any_modified(self):
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
        return self.currentWidget().paste()
