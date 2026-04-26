import serial
import threading
import sys
import time

PORT = "COM5"
BAUD = 115200


def read_serial(ser):
    while ser.is_open:
        try:
            data = ser.readline()
            if data:
                print("\r" + data.decode(errors="ignore"), end="")
                print("> ", end="", flush=True)
        except Exception as e:
            print(f"\nReader error: {e}")
            break


def main():
    try:
        ser = serial.Serial(
            PORT,
            BAUD,
            timeout=0.1,
            write_timeout=1,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )

        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print(f"Connected to {PORT} at {BAUD} baud")
        print("Type commands to send to STM32. Ctrl+C to exit.")
        print("Try: PRM:20,8,5 or FWCRC\n")

    except Exception as e:
        print("Failed to open serial port:", e)
        return

    thread = threading.Thread(target=read_serial, args=(ser,), daemon=True)
    thread.start()

    try:
        while ser.is_open:
            cmd = input("> ").strip()

            if not cmd:
                continue

            msg = (cmd + "\n").encode("ascii", errors="ignore")
            ser.write(msg)
            ser.flush()

            print(f"SENT: {msg!r}")

    except KeyboardInterrupt:
        print("\nClosing connection.")
    finally:
        ser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()