from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtSerialPort import QSerialPort
    from ..device.test_vector import TestVector

from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer

class SerialCommunication(QObject):
    done = Signal()
    error = Signal()
    status_msg = Signal(str)

    def __init__(self, serial: QSerialPort) -> None:
        super().__init__()
        self.serial = serial
        self.buffer = ""

        self.serial.readyRead.connect(self.handle_ready_read)

    def start(self) -> None:
        if not self._port_is_open():
            self.statis_msg.emit("ERR: serial port not open")
            return
        raise NotImplementedError

    def _port_is_open(self) -> bool:
        if not self.serial.isOpen():
            self.error.emit()
            return False
        return True

    def handle_ready_read(self) -> None:
        self.buffer += bytes(self.serial.readAll()).decode("utf-8") # convert QBytesArra to Python Bytes
        # each command is spaced by '\n'
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            self.status_msg.emit(line)
            self.process_line(line)
        return
    
    def process_line(self, line: str) -> None:
        raise NotImplementedError

class BIST(SerialCommunication):
    def __init__(self, serial: QSerialPort) -> None:
        super().__init__(serial)

    def start(self) -> None:
        if not self._port_is_open():
            self.status_msg.emit("ERR: serial port not open")
            return
        self.serial.write("BIST\n".encode("utf-8"))
        return

    def process_line(self, line: str) -> None:
        if line.startswith("DONE"):
            self.done.emit()
        return

class TestRunner(SerialCommunication):
    """Testing Loop to communicate with the STM32 asynchronously.

    Iterates over a list of TestVector objects, generating commands
    for each and sending them over serial communication. Results are stored
    inside the same TestVector.

    Attributes:
        done (Signal): Emitted when all tests have finished.
        error (Signal): Emiited if error has occuured during execution.
        status_msg (Signal[str]): Emitted to report commands sent and received as a string.
        serial (QSerialPort): Serial port used for communication.
        test_vecs (list[TestVector]): List of tests to execute.
        conditions (list[Condition]): All test conditions.
        test_idx (int): Index of the current test in `test_vecs`.
        cond_idx (int): Index of the current condition in `conditions`.
    """
    done = Signal()
    error = Signal()
    status_msg = Signal(str)

    def __init__(self, serial: QSerialPort, test_vecs: list[TestVector]) -> None:
        """Initialize a TestRunner instance.
        
        Args:
            serial (QSerialPort): Serial port to write to and read from.
            test_vecs (list[TestVector]): List of tests to run.
        """
        super().__init__(serial)

        self.test_vecs = test_vecs
        self.cmds = deque()
        # current state of TestRunner
        self.conditions = None
        self.test_idx = 0
        self.cond_idx = 0
        self.stop = False # stops test loop if ERR is received

    def start(self) -> None:
        """Reset all attributes and starts test loop."""
        if not self._port_is_open():
            self.status_msg.emit("ERR: serial port not open")
            return
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
            self.status_msg.emit("All tests finished")
            self.done.emit()
            return
        
        test_vec = self.test_vecs[self.test_idx]
        # no condition, get conditions of current test
        if self.conditions is None:
            self.conditions = test_vec.test_conditions()
            self.cond_idx = 0

        # Finished all conditions -> compare results -> move to next test
        if self.cond_idx >= len(self.conditions):
            self.status_msg.emit(f"Completed: {test_vec.test_name}")
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
            self.serial.write(cmd)
            self.status_msg.emit(f"SENT: {cmd}")
        else:
            # all commands sent, waiting for DONE to move on
            pass

    # def handle_ready_read(self) -> None:
    #     """Handles readyRead signal emitted from `self.serial`.
        
    #     Decodes all UTF-8 encoded responses into strings and add its to the `self.buffer`.
    #     Calls `self.proccess_line()` to process each line in the buffer.
    #     """
    #     self.buffer += bytes(self.serial.readAll()).decode("utf-8") # convert QBytesArra to Python Bytes
    #     # each command is spaced by '\n'
    #     while "\n" in self.buffer:
    #         line, self.buffer = self.buffer.split("\n", 1)
    #         line = line.strip()
    #         self.process_line(line)
    #     return

    def process_line(self, line: str) -> None:
        """Processes a line based on starting phrase.

        Emits a status message of the received command.
        Calls `self.send_next_command()` if line is processed without any errors.
        """
        if self.stop:
            # error occured, stop processing
            return

        if line.startswith("ERR"):
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
