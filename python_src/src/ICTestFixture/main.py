import sys
from PySide6.QtWidgets import QApplication
from ICTestFixture.gui.mainwindow import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
if __name__ == "__main__":
    main()
