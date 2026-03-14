from PySide6.QtWidgets import QComboBox
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

class MultiComboBox(QComboBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        self.setModel(QStandardItemModel(self))
        self.model().dataChanged.connect(self.update_text)

    def addItem(self, text: str):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts: list[str]):
        for text in texts:
            self.addItem(text)

    def update_text(self):
        selected_items = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                selected_items.append(item.text())

        self.lineEdit().setText(",".join(selected_items))