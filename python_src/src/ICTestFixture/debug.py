import os
from collections import deque
from ICTestFixture.fileIO import parser

def PRM(vcc_pin: int, gnd_pin: int, vcc_voltage: int|float):
    return f"PRM:{vcc_pin},{gnd_pin},{vcc_voltage}\n".encode("utf-8")

def VIN(output_low: float, output_high: float):
    return f"VIN:{output_low},{output_high}\n".encode("utf-8")
    
def list_to_command(command: str, args: list):
    return f"{command}:{','.join(map(str, args))}\n".encode("utf-8")

if __name__ == "__main__":
    # parsing all test scripts
    # folder_path = ["test_scripts/hc", "test_scripts/hct"]
    # num_scripts = sum(len(os.listdir(folder)) for folder in folder_path)
    # failed = 0
    # for folder in folder_path:
    #     for file in os.listdir(folder):
    #         try:
    #             print(f"Parsing {file}")
    #             parser.parse(os.path.join(folder, file))
    #         except Exception as e:
    #             print(e)
    #             print(e.__context__)
    #             failed += 1
    # print(f"{failed}/{num_scripts}")
    
    # checking pins, and commands being sent in correct format
    chip_info, test_vecs = parser.parse("test_scripts/hct/74hct74.yaml")

    for test_vec in test_vecs:
        print(test_vec.logic_to_int("X"))
        conditions = test_vec.test_conditions()
        cmds = deque()
        print(test_vec.power_pins())
        cmds.append(PRM(**test_vec.power_pins(), vcc_voltage=conditions[0][0]))
        cmds.append(VIN(conditions[0][1], conditions[0][2]))

        pins = test_vec.pin_lists(conditions[0][0])
        cmds.append(list_to_command("INS", pins["input_pins"]))
        cmds.append(list_to_command("OUT", pins["output_pins"]))
        cmds.append(list_to_command("VIP", pins["voltage_in"]))
        cmds.append("TEST")

        while cmds:
            print(cmds.popleft())
