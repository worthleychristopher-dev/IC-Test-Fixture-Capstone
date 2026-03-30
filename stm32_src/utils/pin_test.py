import serial
import time
from dataclasses import dataclass


# =========================
# USER SETTINGS
# =========================

PORT = "COM8"          # Change this to your STM32 COM port
BAUDRATE = 115200
TIMEOUT = 1.0

POST_SEND_DELAY = 0.3
PROBE_SECONDS = 100
AUTO_CLEAR_NOTE = False   # STM32 format you gave does not include a CLEAR command


# =========================
# TEST DATA STRUCTURE
# =========================

@dataclass
class PowerTest:
    name: str
    vcc_pin: int
    gnd_pin: int
    vcc_voltage: float   # volts, e.g. 3.3


# =========================
# SERIAL HELPERS
# =========================

def open_serial():
    ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    time.sleep(2.0)  # allow STM32 reset after serial open
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser


def send_command(ser, cmd: str):
    print(f">>> {cmd.strip()}")
    ser.write(cmd.encode("ascii"))
    ser.flush()


def read_available(ser, duration=1.0):
    end_time = time.time() + duration

    while time.time() < end_time:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            text = data.decode("utf-8", errors="replace")
            print(text, end="")
        time.sleep(0.05)

    print()


# =========================
# COMMAND BUILDERS
# =========================

def build_prm_command(test: PowerTest) -> str:
    """
    STM32 expects:
    PRM:VCCpin,GNDpin,VCCvoltage

    Example:
    PRM:14,7,3.3
    """
    return f"PRM:{test.vcc_pin},{test.gnd_pin},{test.vcc_voltage:.2f}\r\n"


def build_test_command() -> str:
    """
    STM32 expects:
    TEST
    """
    return "TEST\r\n"


# =========================
# TEST EXECUTION
# =========================

def run_power_test(ser, test: PowerTest):
    print("\n" + "=" * 60)
    print(f"Running test: {test.name}")
    print(f"Expected results:")
    print(f"  DUT pin {test.vcc_pin} -> about {test.vcc_voltage:.2f} V")
    print(f"  DUT pin {test.gnd_pin} -> GND / 0 V")
    print("=" * 60)

    prm_cmd = build_prm_command(test)
    test_cmd = build_test_command()

    # Send PRM first
    send_command(ser, prm_cmd)
    time.sleep(POST_SEND_DELAY)
    read_available(ser, duration=0.75)

    # Then send TEST
    send_command(ser, test_cmd)
    time.sleep(POST_SEND_DELAY)
    read_available(ser, duration=1.5)

    print("Probe now with your DMM:")
    print(f"  1. Measure DUT pin {test.vcc_pin} to DUT pin {test.gnd_pin}")
    print(f"     Expected: about {test.vcc_voltage:.2f} V")
    print(f"  2. Measure DUT pin {test.gnd_pin} to board ground")
    print("     Expected: about 0 V")
    print(f"  3. Measure DUT pin {test.vcc_pin} to board ground")
    print(f"     Expected: about {test.vcc_voltage:.2f} V")
    print()

    for remaining in range(PROBE_SECONDS, 0, -1):
        print(f"Time left to probe: {remaining:2d} s", end="\r")
        time.sleep(1.0)

    print(" " * 40, end="\r")
    print("Test window done.")

    if not AUTO_CLEAR_NOTE:
        print("Note: no CLEAR command was provided, so routing may remain active until the next test/reset.")


def interactive_mode(ser):
    while True:
        print("\nEnter VCC/GND test values:")
        print("format: <vcc_pin> <gnd_pin> <vcc_voltage>")
        print("example: 14 7 3.3")
        print("type q to quit")

        user = input("> ").strip()
        if user.lower() == "q":
            break

        parts = user.split()
        if len(parts) != 3:
            print("Invalid input. Need exactly 3 values.")
            continue

        try:
            vcc_pin = int(parts[0])
            gnd_pin = int(parts[1])
            vcc_voltage = float(parts[2])
        except ValueError:
            print("Invalid numeric input.")
            continue

        test = PowerTest(
            name=f"VCC pin {vcc_pin}, GND pin {gnd_pin}, {vcc_voltage:.2f}V",
            vcc_pin=vcc_pin,
            gnd_pin=gnd_pin,
            vcc_voltage=vcc_voltage
        )

        run_power_test(ser, test)


def preset_mode(ser):
    tests = [
        PowerTest("3.3V check", 14, 7, 3.3),
        PowerTest("5.0V check", 14, 7, 5.0),
        PowerTest("1.8V check", 14, 7, 1.8),
    ]

    for test in tests:
        run_power_test(ser, test)

    print("\nAll preset tests complete.")


def main():
    ser = None
    try:
        ser = open_serial()
        print(f"Connected to {PORT} @ {BAUDRATE}")

        while True:
            print("\nChoose mode:")
            print("1) Interactive mode")
            print("2) Preset tests")
            print("q) Quit")

            choice = input("> ").strip().lower()

            if choice == "1":
                interactive_mode(ser)
            elif choice == "2":
                preset_mode(ser)
            elif choice == "q":
                break
            else:
                print("Invalid choice.")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    finally:
        if ser is not None and ser.is_open:
            ser.close()
            print("Serial port closed.")


if __name__ == "__main__":
    main()