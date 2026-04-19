import serial
import time
import sys
import os

PORT = "COM9"
BAUD = 115200
COMMAND_FILE = r"C:\Users\worthc2\STM32CubeIDE\workspace_2.0.0\STM32_main\test_commands.txt"

# How long to wait after sending each command before deciding STM32 is done responding
RESPONSE_TIMEOUT = 1.0

# Small pause after opening serial so STM32 has time to settle
STARTUP_DELAY = 2.0


def read_response(ser, timeout=1.0):
    """
    Read all available STM32 output until no new data arrives for 'timeout' seconds.
    Returns the collected response as a string.
    """
    response_lines = []
    last_data_time = time.time()

    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode(errors="ignore")
                if line:
                    response_lines.append(line)
                    last_data_time = time.time()
            except Exception as e:
                response_lines.append(f"[Read error: {e}]\n")
                break
        else:
            if time.time() - last_data_time > timeout:
                break
            time.sleep(0.01)

    return "".join(response_lines)


def main():
    if not os.path.exists(COMMAND_FILE):
        print(f"Command file not found:\n{COMMAND_FILE}")
        sys.exit(1)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        print(f"Connected to {PORT} at {BAUD} baud")
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        sys.exit(1)

    try:
        time.sleep(STARTUP_DELAY)

        # Clear any junk already sitting in the buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        with open(COMMAND_FILE, "r") as f:
            commands = f.readlines()

        for line_num, raw_line in enumerate(commands, start=1):
            cmd = raw_line.strip()

            # Skip blank lines and comments
            if not cmd or cmd.startswith("#"):
                continue

            print(f"\n>>> Sending line {line_num}: {cmd}")

            # STM32 parser expects CRLF based on your terminal script
            ser.write((cmd + "\r\n").encode())
            ser.flush()

            response = read_response(ser, timeout=RESPONSE_TIMEOUT)

            if response.strip():
                print("<<< STM32 response:")
                print(response, end="" if response.endswith("\n") else "\n")
            else:
                print("<<< No response")

        print("\nFinished sending all commands.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError during execution: {e}")
    finally:
        ser.close()
        print("Serial port closed.")


if __name__ == "__main__":
    main()