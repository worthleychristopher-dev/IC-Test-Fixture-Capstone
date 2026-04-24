import os
from collections import deque
from ic_test_fixture.file_io import parser, report

def PRM(vcc_pin: int, gnd_pin: int, vcc_voltage: int|float):
    return f"PRM:{vcc_pin},{gnd_pin},{vcc_voltage}\n".encode("utf-8")

def VIN(output_low: float, output_high: float):
    return f"VIN:{output_low},{output_high}\n".encode("utf-8")
    
def list_to_command(command: str, args: list):
    return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")

def parsing_all_test_scripts():
    folder_path = ["test_scripts/hc", "test_scripts/hct"]
    num_scripts = sum(len(os.listdir(folder)) for folder in folder_path)
    failed = 0
    for folder in folder_path:
        for file in os.listdir(folder):
            try:
                print(f"Parsing {file}")
                parser.parse(os.path.join(folder, file))
            except Exception as e:
                print(e)
                print(e.__context__)
                failed += 1
    print(f"{failed}/{num_scripts}")

def uart_commands(file_path: str):
    # checking pins, and commands being sent in correct format
    _, test_vecs = parser.parse(file_path)

    for test_vec in test_vecs:
        conditions = test_vec.test_conditions()
        cmds = deque()
        cmds.append(PRM(**test_vec.power_pins(), vcc_voltage=conditions[0].vcc))
        cmds.append(VIN(conditions[0].out_low, conditions[0].out_high))

        pins = test_vec.pin_lists(conditions[0].vcc)
        cmds.append(list_to_command("INS", pins["input_pins"]))
        cmds.append(list_to_command("OUT", pins["output_pins"]))
        cmds.append(list_to_command("VIP", pins["voltage_in"]))
        cmds.append("TEST\n".encode("utf-8"))

        while cmds:
            print(cmds.popleft())

def simulated_test(file_path: str):
    _, test_vecs = parser.parse(file_path)
    for test_vec in test_vecs:
        test_vec.simulated_test(None, True)
    report.export_to_pdf(_, test_vecs, "testing.pdf")
        

if __name__ == "__main__":
    # parsing_all_test_scripts()
    # uart_commands("/home/chefshouse/IC-Test-Fixture-Capstone/test_scripts/hct/74hct73.yaml")
    simulated_test("/home/chefshouse/IC-Test-Fixture-Capstone/test_scripts/hct/74hct74.yaml")