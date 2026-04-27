import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from ic_test_fixture.utils import integrity
from ic_test_fixture.gui.main_window import MainWindow

def show_integrity_warning():
    reply = QMessageBox.question(
        None,
        "Warning: Checksum Failed",
        "Software checksum did not match expected value, continue anyways?",
        QMessageBox.Yes | QMessageBox.No
     )
    if reply == QMessageBox.No:
        sys.exit(1)
    return

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # app looks consistent across all OS

    # check if .exe has been modified, not used during development
    exe_path = sys.executable
    if getattr(sys, "frozen", False):
        if not integrity.verify_checksum(exe_path):
            QTimer.singleShot(0, show_integrity_warning)

    window = MainWindow()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
