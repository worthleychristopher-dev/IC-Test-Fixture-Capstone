from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtSerialPort import QSerialPort  # type hint only
    from ICTestFixture.device.test_vector import TestVector

from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer

#TODO: add support to export data when done executing all in test vecs
class TestRunner(QObject):
    done = Signal()
    status_msg = Signal(str)

    def __init__(self, serial: QSerialPort, test_vecs: list[TestVector]):
        super().__init__()
        
        self.serial = serial
        self.test_vecs = test_vecs
        self.buffer = ""
        self.conditions = None
        self.cmds = deque()
        self.test_idx = 0
        self.condition_idx = 0
        self.stop = False

        self.serial.readyRead.connect(self.handle_ready_read)

    def start_test(self):
        self.conditions = None
        self.cmds.clear()

        self.test_idx = 0
        self.condition_idx = 0

        self.stop = False

        self.test_loop()
        return

    def test_loop(self):
        if self.test_idx >= len(self.test_vecs):
            self.status_msg.emit("All tests finished")
            self.done.emit()
            return
        
        test_vec = self.test_vecs[self.test_idx]

        if self.conditions is None:
            self.conditions = test_vec.test_conditions()
            self.condition_idx = 0

        # Finished all conditions → move to next test
        if self.condition_idx >= len(self.conditions):
            self.status_msg.emit(f"Completed: {test_vec.test_name}")
            self.test_idx += 1
            self.conditions = None
            # lets GUI figure out when to run function, reduces recursion depth
            QTimer.singleShot(0, self.test_loop)
            # self.test_loop()
            return
        
        condition = self.conditions[self.condition_idx]
        self.cmds.append(self.PRM(**test_vec.power_pins(), vcc_voltage=condition[0]))
        self.cmds.append(self.VIN(condition[1], condition[2]))

        pins = test_vec.pin_lists(condition[0])
        self.cmds.append(self.list_to_command("INS", pins["input_pins"]))
        self.cmds.append(self.list_to_command("OUT", pins["output_pins"]))
        self.cmds.append(self.list_to_command("VIP", pins["voltage_in"]))
        self.cmds.append("TEST")
        
        self.send_next_command()
        return

    def send_next_command(self):
        if self.stop:
            # error, stop sending commands
            return
        
        if self.cmds:
            cmd = self.cmds.popleft()
            self.serial.write(cmd)
            self.status_msg.emit(f"SENT: {cmd}")
        else:
            # all commands sent, waiting for DONE to move on
            pass

    def handle_ready_read(self):
        self.buffer += bytes(self.serial.readAll()).decode("utf-8")

        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            self.process_line(line)

    def process_line(self, line: str):
        self.status_msg.emit(f"Received: {line}")

        if self.stop:
            return
        
        if line.startswith("ERR"):
            self.status_msg.emit(line)
            self.stop = True
            return

        if line == "DONE":
            self.condition_idx += 1
            # lets GUI figure out when to run function, reduces recursion depth
            QTimer.singleShot(self.test_loop)
            # self.test_loop()
        elif line.startswith("STEP"):
            # decode pin, and output, write to current test_vec
            tokens = line.split(" ")
            step_num = int(tokens[1])
            pin = int(tokens[4])
            logic = int(tokens[6])
            adc = round(float(tokens[7][1:]) / 100, 2)
            vcc = self.conditions[self.condition_idx]
            self.test_vecs[self.test_idx].add_result(step_num, pin, logic, adc, vcc)
        else:
            self.status_msg.emit(line)

        self.send_next_command()
        return

    def PRM(self, vcc_pin: int, gnd_pin: int, vcc_voltage: int|float):
        # remove V at the end of vcc_voltage str
        return f"PRM:{vcc_pin},{gnd_pin},{float(vcc_voltage[:-1])}\n".encode("utf-8")

    def VIN(self, output_low: float, output_high: float):
        return f"VIN:{output_low},{output_high}\n".encode("utf-8")
    
    def list_to_command(self, command: str, args: list):
        return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")
