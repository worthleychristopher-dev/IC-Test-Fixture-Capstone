import serial
import threading
import sys

PORT = "COM9"
BAUD = 115200


def read_serial(ser):
    """
    Continuously read from STM32 and print to terminal
    """
    while True:
        try:
            data = ser.readline()
            if data:
                print(data.decode(errors="ignore"), end="")
        except:
            break


def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Connected to {PORT} at {BAUD} baud")
        print("Type commands to send to STM32. Ctrl+C to exit.\n")

    except Exception as e:
        print("Failed to open serial port:", e)
        return

    # Start background reader
    thread = threading.Thread(target=read_serial, args=(ser,), daemon=True)
    thread.start()

    try:
        while True:
            cmd = input("> ")

            # Send command with newline (STM32 parser expects newline)
            #ser.write((cmd + "\n").encode())
            ser.write((cmd + "\r\n").encode())

    except KeyboardInterrupt:
        print("\nClosing connection.")
        ser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()