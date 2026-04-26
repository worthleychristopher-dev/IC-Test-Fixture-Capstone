from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QPlainTextEdit, QFileDialog

class TabbedEditor(QTabWidget):
    """Allows user to open, edit, and switch between multiple test scripts.

    Attributes:
        tab_added (Signal): Emitted when a new tab is added when `TabbedEditor` was empty.
        no_tabs (Singal): Emitted when `TabbedEditor` is empty.
        editor_paths (dict[QPlainTextEdit | str]): Storage of file paths with `QPlainTextEdit` widget as the key.
        new_file_count (int): Used for giving unique names tabs with blank `QPlainTextEdit` instances.
    """
    tab_added = Signal()
    no_tabs = Signal()

    def __init__(self, parent):
        """Initializes TabbedEditor instance."""
        super().__init__(parent)
        self.editor_paths = {}
        self.new_file_count = 0

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.remove_tab)

    def new_tab(self, editor: QPlainTextEdit, file_path: str=None):
        """Creates new tab for `QPlainTextEdit` widget and adds it to class attributes.
        
        Args:
            editor (QPlainTextEdit): Instance of QPlainTextEdit to add.
            file_path (str): File path the editor is opened from/saves to.
        """
        if file_path:
            tab_text = Path(file_path).stem
        else:
            tab_text = f"Untitled {self.new_file_count}"
            self.new_file_count += 1

        self.editor_paths[editor] = file_path
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(self.modify_title)
        self.addTab(editor, tab_text)
        self.setCurrentWidget(editor)

        if self.count() == 1:
            self.tab_added.emit()

    def new_file(self) -> None:
        """Creates new instance of `QPlainTextEdit`, and calls `new_tab`."""
        editor = QPlainTextEdit()
        self.new_tab(editor)

    def open_file(self) -> None:
        """Opens test script file (.yaml), and adds it to class attributes."""
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

    def save_file(self) -> None:
        """Saves contents of current `QPlainTextEdit` widget to location of file. Calls `save_as()` if no path exists."""
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

    def save_as(self) -> None:
        """Saves contents of current `QPlainTextEdit` widget to user-chosen location."""
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
            self.setTabText(self.currentIndex(), Path(save_name).stem) # display save_name as title of tab
            self.editor_paths[self.currentWidget()] = save_with_ext # store location of file for parsing/saving
            

    def remove_tab(self, i: int) -> None:
        """Removes tab from class attributes when user request to close tab."""
        tab_text = self.tabText(i)
        editor = self.widget(i)

        if editor.toPlainText().strip() == "":
            pass
        elif tab_text.endswith("*") or tab_text.startswith("Untitled"):
            # save work before closing
            self.save_file()

        self.editor_paths.pop(editor, None)
        self.removeTab(i)
        editor.deleteLater()

        if self.count() == 0:
            self.no_tabs.emit()

    def modify_title(self) -> None:
        """Adds asterisk to title of current tab if edits were made and are not yet saved."""
        # adds asterisk to title, signals unsaved changes
        idx = self.currentIndex()
        title = self.tabText(idx)
        if not title.endswith("*"):
            self.setTabText(idx,  f"{title}*")

    def on_close(self) -> None:
        """Executes if user chooses to save work on close of application."""
        for i in range(self.count()):
            self.setCurrentIndex(i)
            self.save_file()

    def editor_path(self) -> str:
        """Returns file_path of current `QPlainTextEdit` widget."""
        return self.editor_paths[self.currentWidget()]

    def is_empty(self) -> bool:
        """Returns if any tabs are open or current `QPlainTextEdit` widget is empty."""
        return self.count() == 0 or self.currentWidget().toPlainText().strip() == ""
    
    def is_modified(self) -> bool:
        """Returns if current `QPlainTextEdit` widget is modified."""
        return self.count() != 0 and self.currentWidget().document().isModified()
    
    def any_modified(self) -> bool:
        """Returns if any `QPlainTextEdit` widgets have been modified."""
        if self.count() == 0:
            return False
        
        for i in range(self.count()):
            editor = self.widget(i)
            if editor.document().isModified():
                return True

    def undo(self) -> None:
        """Returns `undo()` of current `QPlainTextEdit` widget."""
        return self.currentWidget().undo()

    def redo(self) -> None:
        """Returns `redo()` of current `QPlainTextEdit` widget."""
        return self.currentWidget().redo()

    def cut(self) -> None:
        """Returns `cut()` of current `QPlainTextEdit` widget."""
        return self.currentWidget().cut()

    def copy(self) -> None:
        """Returns `copy()` of current `QPlainTextEdit` widget."""
        return self.currentWidget().copy()

    def paste(self) -> None:
        """Returns `paste()` of current `QPlainTextEdit` widget."""
        return self.currentWidget().paste()
