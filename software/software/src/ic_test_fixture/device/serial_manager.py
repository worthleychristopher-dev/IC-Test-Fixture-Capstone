from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..device.test_vector import TestVector

from collections import deque
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtCore import QIODevice, QObject, Signal, QTimer

BAUDRATE = QSerialPort.BaudRate.Baud115200
VID = 0x10C4
PID = 0xEA60
SERIAL_STRING = "UML Capstone 25-304 NUWC 2026"

class SerialManager(QObject):
    """Manages all serial communication the STM32.

    Attributes:
        done (Signal): Emitted when all tests have finished.
        error (Signal): Emitted if error has occuured during execution.
        line_received (Signal[str]): Emitted to report commands sent and received as a string.
        status_msg (Signal[str]): Emitted to report the status of serial communicaition.
        serial (QSerialPort): Serial port used for communication.
        active_protocol (type[SerialProtocol]): Current active protocol in use.
        buffer (str): Buffer to store incoming data until a full line is received.
    """
    done = Signal()
    error = Signal()
    line_received = Signal(str)
    status_msg = Signal(str)

    def __init__(self) -> None:
        """Initialize a SerialManager instance."""
        super().__init__()
        self.serial = QSerialPort()
        self.active_protocol = None
        self.buffer = ""

        self.serial.setBaudRate(BAUDRATE)
        for port_info in QSerialPortInfo.availablePorts():
            # based on CP2102 - GM from Silicon Labs for USB to UART bridge
            # Datasheet: https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf
            decoded_serial = bytes.fromhex(port_info.serialNumber()).decode("utf-8")
            # print(f"Serial Number: {port_info.serialNumber()}")
            # print(f"Decoded Serial Number: {decoded_serial}")

            if (port_info.vendorIdentifier() == VID and
                port_info.productIdentifier() == PID and
                decoded_serial == SERIAL_STRING):

                #print(port_info.portName())
                self.serial.setPortName(port_info.portName())

        if self.serial.open(QIODevice.ReadWrite):
            self.status_msg.emit("Serial port opened successfully")
        else:
            self.status_msg.emit(f"ERR: Failed to open serial port, {self.serial.errorString()}")

        #print(port_info.portName())
        self.serial.readyRead.connect(self._handle_ready_read)

    def set_protocol(self, protocol_cls: type[SerialProtocol], *args, **kwargs) -> None:
        """Sets the serial protocol to use for communication.

        Disconnects any previous `SerialProtocol` and creates an instance of `protocol_cls`.

        Args:
            protocol_cls (type[SerialProtocol]): The SerialProtocol subclass to use for communication.
        """
        if self.active_protocol:
            try:
                self.line_received.disconnect(self.active_protocol.process_line)
                self.active_protocol.deleteLater() # safely delete previous protocol instance
            except (TypeError, RuntimeError):
                # line_received not connected to active_protocol.process_line, pass
                pass

        self.active_protocol = protocol_cls(self, *args, **kwargs)
        self.line_received.connect(self.active_protocol.process_line)
        return
    
    def start_protocol(self) -> None:
        """Starts the active serial protocol."""
        if self.active_protocol:
            self.active_protocol.start()
        else:
            self.status_msg.emit("ERR: No active protocol set")
        return

    def write(self, data: str|bytes) -> None:
        """Writes data to the serial port.

        Args:
            data (str|bytes): Data to be written to the serial port.
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.serial.write(data)
        self.status_msg.emit(f"SENT: {data}")
        return

    def is_open(self) -> bool:
        """Checks if the serial port is open."""
        return self.serial.isOpen()

    def _handle_ready_read(self) -> None:
        """Handles readyRead signal emitted from `self.serial`."""
        self.buffer += bytes(self.serial.readAll()).decode("utf-8", errors="ignore") # convert QBytesArra to Python Bytes
        #print(self.buffer)
        # each command is spaced by '\n'
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            self.line_received.emit(line)
        return
    
class SerialProtocol(QObject):
    """Interface for serial communication.
    
    Subclasses should be implemented as if they were Finite State Machines. 
    """
    def __init__(self, manager: SerialManager) -> None:
        """Initialize a SerialProtocol instance.

        Args:
            manager (SerialManager): SerialManager instance to use for serial communication.
        """
        super().__init__()
        self.manager = manager

    def start(self) -> None:
        """Start the serial communication process. Should be implemented by subclasses.
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        print(self.buffer)
        raise NotImplementedError
    
    def process_line(self, line: str) -> None:
        """Processes a line based on starting phrase. Should be implemented by subclasses.
        
        Raises: NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

class Checksum(SerialProtocol):
    """Serial communication for sending and handling checksum feature."""
    EXPECTED_CHECKSUM = "0x9F0717A7"

    def __init__(self, manager: SerialManager) -> None:
        """Initialize a Checksum instance.
        
        Args:
            manager (SerialManager): SerialManager instance to use for serial communication.
        """
        super().__init__(manager)

    def start(self) -> None:
        """Start the checksum process by sending FWCRC command to the STM32."""
        if not self.manager.is_open():
            self.manager.status_msg.emit("ERR: Serial port not open")
            self.manager.error.emit()
            return
        self.manager.write("FWCRC\n".encode("utf-8"))
        return

    def process_line(self, line: str) -> None:
        """Processes a line based on starting phrase."""
        if line.startswith("FW CRC32"):
            # safely check message format is correct before accessing index
            parts = line.split("=")
            if len(parts) < 2:
                self.manager.error.emit()
                return
            checksum_value = parts[1].strip()

            if checksum_value == self.EXPECTED_CHECKSUM:
                self.manager.status_msg.emit(f"Checksum value received: {checksum_value}, matches expected value")
                #print(checksum_value)
                self.manager.done.emit()
            else:
                self.manager.status_msg.emit(f"ERR: Checksum value received: {checksum_value}, does not match expected value")
                self.manager.error.emit()
        elif line.startswith("ERR"):
            self.manager.error.emit()
        return

class BIST(SerialProtocol):
    """Serial communication for sending and handling BIST feature."""
    def __init__(self, manager: SerialManager) -> None:
        """Initialize a BIST instance.
        
        Args:
            manager (SerialManager): SerialManager instance to use for serial communication."""
        super().__init__(manager)

    def start(self) -> None:
        """Start the BIST process by sending the BIST command to the STM32."""
        if not self.manager.is_open():
            self.manager.status_msg.emit("ERR: Serial port not open")
            self.manager.error.emit()
            return
        self.manager.write("BIST\n".encode("utf-8"))
        return

    def process_line(self, line: str) -> None:
        """Processes a line based on starting phrase."""
        if line.startswith("DONE"):
            self.manager.done.emit()
        elif line.startswith("ERR"):
            self.manager.error.emit()
        return

class TestRunner(SerialProtocol):
    """Testing Loop to communicate with the STM32 asynchronously.

    Iterates over a list of TestVector objects, generating commands
    for each and sending them over serial communication. Results are stored
    inside the same TestVector.

    Attributes:
        test_vecs (list[TestVector]): List of tests to execute.
        cmds (deque[bytes]): Queue of UTF-8 encoded commands to send to the STM32.
        conditions (list[Condition]): All test conditions.
        test_idx (int): Index of the current test in `test_vecs`.
        cond_idx (int): Index of the current condition in `conditions`.
        stop (bool): Flag to stop the test loop if an error is received.
    """
    def __init__(self, manager: SerialManager, test_vecs: list[TestVector]) -> None:
        """Initialize a TestRunner instance.
        
        Args:
            manager (SerialManager): Serial manager instance.
            test_vecs (list[TestVector]): List of tests to run.
        """
        super().__init__(manager)

        self.test_vecs = test_vecs
        self.cmds = deque()
        # current state of TestRunner
        self.conditions = None
        self.test_idx = 0
        self.cond_idx = 0
        self.stop = False # stops test loop if ERR is received

    def start(self) -> None:
        """Starts test loop."""
        if not self.manager.is_open():
            self.manager.status_msg.emit("ERR: Serial port not open")
            self.manager.error.emit()
            return
        self.cmds.append("START\n".encode("utf-8"))
        self.test_loop()
        return

    def test_loop(self) -> None:
        """Main test loop of TestRunner

        Generates UTF-8 encoded commands for the current active test at
        `self.test_vecs[self.test_idx]` with the condition at
        `self.conditions[self.cond_idx]`. Moves to next test upon completion, emits
        done signal when all tests have been executed.
        """
        if self.test_idx >= len(self.test_vecs):
            self.manager.status_msg.emit("All tests finished")
            self.manager.done.emit()
            return
        
        test_vec = self.test_vecs[self.test_idx]
        # no condition, get conditions of current test
        if self.conditions is None:
            self.conditions = test_vec.test_conditions()
            self.cond_idx = 0

        # Finished all conditions -> compare results -> move to next test
        if self.cond_idx >= len(self.conditions):
            self.manager.status_msg.emit(f"Completed: {test_vec.test_name}")
            self.test_idx += 1
            self.conditions = None
            # lets GUI figure out when to run function, reduces recursion depth
            QTimer.singleShot(0, self.test_loop)
            return
        
        # add UTF-8 encoded commands to deque
        curr_cond = self.conditions[self.cond_idx]
        self.cmds.append(self.PRM(**test_vec.power_pins(), vcc=curr_cond.vcc))
        self.cmds.append(self.VIN(curr_cond.out_low, curr_cond.out_high))

        pins = test_vec.pin_lists(curr_cond.vcc)
        self.cmds.append(self.list_to_command("INS", pins["input_pins"]))
        self.cmds.append(self.list_to_command("OUT", pins["output_pins"]))
        self.cmds.append(self.list_to_command("VIP", pins["voltage_in"]))
        self.cmds.append("TEST\n".encode("utf-8"))
        
        self.send_next_command()
        return

    def send_next_command(self) ->  None:
        """Send next UTF-8 encoded command from queue to the serial port.
        
        Pops the next command from `self.cmds`, and writes it to `self.serial`.
        Emits a status message after sending the command.
        """
        if self.stop:
            # error occured, stop sending
            return

        if self.cmds:
            # deque not empty, keep sending
            cmd = self.cmds.popleft()
            self.manager.write(cmd)
        else:
            # all commands sent, waiting for DONE to move on
            pass
        return

    def process_line(self, line: str) -> None:
        """Processes a line based on starting phrase.

        Calls `self.send_next_command()` if line is processed without any errors.
        """
        if self.stop:
            # error occured, stop processing
            return

        if line.startswith("ERR"):
            self.manager.error.emit()
            self.stop = True
            return

        if line.startswith("DONE"):
            self.test_vecs[self.test_idx].compare_results(self.conditions[self.cond_idx].vcc)
            self.cond_idx += 1
            # lets GUI figure out when to run function, reduces recursion depth
            QTimer.singleShot(0, self.test_loop)
        elif line.startswith("STEP"):
            # decode pin, and output, write to current test_vec
            # formatted as: STEP X OUT pin Y -> logic (adc_val mV)
            tokens = line.split(" ")
            step_num = int(tokens[1])
            pin = int(tokens[4])
            logic = int(tokens[6])
            adc = round(float(tokens[7][1:]) / 1000, 2)
            vcc = self.conditions[self.cond_idx].vcc
            self.test_vecs[self.test_idx].add_result(step_num, pin, logic, adc, vcc)

        self.send_next_command()
        return

    def PRM(self, vcc_pin: int, gnd_pin: int, vcc: float) -> bytes:
        """Generate a PRM command as a UTF-8 encoded byte string.
        
        The command is formatted as:
            PRM:vcc_pin,gnd_pin,vcc\\n

        Args:
            vcc_pin (int): Voltage Supply Pin of the IC.
            gnd_pin (int): Ground Pin of the IC.
            vcc (float): Voltage to drive `vcc_pin`

        Returns:
            bytes: The full PRM command encoded in UTF-8
        """
        return f"PRM:{vcc_pin},{gnd_pin},{vcc}\n".encode("utf-8")

    def VIN(self, output_low: float, output_high: float) -> bytes:
        """Generate a VIN command as a UTF-8 encoded byte string.

        The command is formatted as:
            VIN:output_low,output_high\\n

        Args:
            output_low (float): Output Low Threshold of the IC.
            output_high (float): Output High Threshold of the IC.

        Returns:
            bytes: The full VIN command encoded in UTF-8
        """
        return f"VIN:{output_low},{output_high}\n".encode("utf-8")
    
    def list_to_command(self, command: str, args: list) -> bytes:
        """Generate a command as a UTF-8 encoded byte string.

        The command is formatted as:
            command:arg1,arg2,arg3\\n

        Args:
            command (str): The name of the command.
            args (list): A list of arguments to include in the command

        Returns:
            bytes: The full command encoded in UTF-8
        """
        return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")
