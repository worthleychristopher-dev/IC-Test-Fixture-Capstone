
import serial
import time

PORT = "COM9"
BAUD = 115200
TIMEOUT_S = 1.0


def read_line(ser: serial.Serial) -> str:
    """Read one newline-terminated line from the STM32 (returns '' on timeout)."""
    try:
        return ser.readline().decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def send_and_print(ser: serial.Serial, cmd: str, expected_lines: int = 2) -> None:
    """
    Send one command line and print the STM32's response lines.

    expected_lines:
      - 2 for INS/OUT/VTI/VTO (OK line + echo line)
      - 2 for VIN in the C code I gave (OK VIN + VIN:low,high)
      - If you later add more lines, change this.
    """
    ser.write((cmd + "\n").encode("utf-8"))

    print(f"> {cmd}")
    for _ in range(expected_lines):
        resp = read_line(ser)
        print(f"< {resp if resp else '(timeout/no response)'}")
    print()


def main():
    # Open COM port
    with serial.Serial(PORT, BAUD, timeout=TIMEOUT_S) as ser:
        # Many STM32 boards reset or reboot when the serial port opens.
        time.sleep(0.3)
        ser.reset_input_buffer()

        # Try to read a READY banner if it arrives after open
        banner = read_line(ser)
        if banner:
            print(f"< {banner}\n")

        # ---- Test messages ----
        send_and_print(ser, "INS:1,3,5,7", expected_lines=2)
        send_and_print(ser, "OUT:2,4,6", expected_lines=2)
        send_and_print(ser, "VIN:0.80,2.00", expected_lines=2)
        #should get back VIN: 800, 2000 as STM32 does not use floats

        send_and_print(ser, "VTI:TTL,TTL,TTL,CMOS", expected_lines=2)
        send_and_print(ser, "VTO:CMOS,CMOS,CMOS", expected_lines=2)

        # ---- Extra quick error tests (optional) ----
        # Bad pin range (should error on STM32)
        # send_and_print(ser, "INS:0,13", expected_lines=1)
        #
        # Missing colon
        # send_and_print(ser, "INS 1,2,3", expected_lines=1)

        print("Done.")


if __name__ == "__main__":
    main()
