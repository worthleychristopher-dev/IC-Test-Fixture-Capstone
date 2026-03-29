import sys
from PySide6.QtWidgets import QApplication
from ICTestFixture.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # app looks consistent across all OS

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
