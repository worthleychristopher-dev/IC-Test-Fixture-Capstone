import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from ic_test_fixture.device.serial_manager import Checksum, SerialManager
from ic_test_fixture.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # app looks consistent across all OS

    window = None
    serial_manager = SerialManager()

    def checksum_success():
        serial_manager.done.disconnect(checksum_success)
        serial_manager.error.disconnect(checksum_fail)
        create_main_window()

    def checksum_fail():
        serial_manager.done.disconnect(checksum_success)
        serial_manager.error.disconnect(checksum_fail)
        reply = QMessageBox.question(
                None,
                "Warning: Checksum Failed",
                "Checksum did not match expected value, continue anyways?",
                QMessageBox.Yes | QMessageBox.No
            )
        
        if reply == QMessageBox.Yes:
            create_main_window()
        else:
            QApplication.quit()
            sys.exit(1)

    def create_main_window():
        nonlocal window
        #nonlocal serial_manager
        window = MainWindow(serial_manager)
        window.show()

    serial_manager.done.connect(checksum_success)
    serial_manager.error.connect(checksum_fail)
    serial_manager.set_protocol(Checksum)
    serial_manager.start_protocol()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
