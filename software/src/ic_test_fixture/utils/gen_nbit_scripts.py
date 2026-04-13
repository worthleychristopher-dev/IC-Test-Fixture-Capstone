import yaml

def gen_adder_test(n, a_bits, b_bits, out_bits, a_val, b_val, **kwargs):
    for c in (0, 1):
        sum_val = a_val + b_val + c
        test = {
            "Inputs": {
                a_bits: a_val,
                b_bits: b_val,
                "CIN": c
                },
            "Outputs": {
                out_bits: sum_val & ((1 << n) - 1),
                "COUT": (sum_val >> n+1) & 1
            }
        }
        yield {f"A={a_val}, B={b_val}, CIN={c} -> S={sum_val}": test}

def gen_comparator_test(a_bits, b_bits, out_bits, a_val, b_val, **kwargs):
    en_bit = kwargs.pop("en_bit", None)
    active_low = kwargs.pop("active_low", False)
    invert = kwargs.pop("invert", False)

    result = int(a_val==b_val) ^ invert

    def make_test(en_val):
        return {
            "Inputs": {
                a_bits: a_val,
                b_bits: b_val,
                **({en_bit: en_val} if en_bit is not None else {})
            },
            "Outputs": {
                out_bits: result
            }
        }
    if en_bit:
        for en_val in (0, 1):
            if active_low and en_val == 1: result = 1
            yield {f"A={a_val}, B={b_val}, {en_bit}={en_val} -> Y={result}": make_test(en_val)}

    else:
        yield {f"A={a_val}, B={b_val} -> Y={result}": make_test(None)}

def gen_nbit_tests(logic, n, a_bits, b_bits, out_bits=None, **kwargs):
    max_val = 2 ** n
    for i in range(max_val):
        # reduces number of loops by doing both (i,j) and (j,i) in same loop
        for j in range(i, max_val):
            if logic == "adder":
                yield from gen_adder_test(n, a_bits, b_bits, out_bits, i, j, **kwargs)
                if i != j:
                    yield from gen_adder_test(n, a_bits, b_bits, out_bits, j, i, **kwargs)
            elif logic == "comparator":
                yield from gen_comparator_test(a_bits, b_bits, out_bits, i, j, **kwargs)
                if i != j:
                    yield from gen_comparator_test(a_bits, b_bits, out_bits, j, i, **kwargs)
            else:
                NotImplementedError("Logic is not implemented")
                
                
def gen_transciever(n, a_bits, b_bits):
    max_val = 2**n

    def make_test(en_val, dir_val, a_val, b_val):
        if en_val:
            return {
                "Inputs": { 
                    a_bits: a_val,
                    b_bits: b_val,
                    "OE": en_val,
                    "DIR": "X"
                },
                "Outputs": { 
                    a_bits: a_val,
                    b_bits: b_val 
                }
            }
        if dir_val:
            return {
                "Inputs": { a_bits: a, "DIR": dir_val, "OE": en_val },
                "Outputs": { b_bits: a }
            }
        else:
            return {
                "Inputs": { b_bits: b, "DIR": dir_val, "OE": en_val },
                "Outputs": { a_bits: b }
            }

    for a in range(max_val):
        yield {f"A={a}, OE=0, DIR=1 -> B={a}": make_test(0, 1, a, 0)}
    for b in range(max_val):
        yield {f"B={b}, OE=0, DIR=1 -> A={b}": make_test(0, 0, 0, b)}
    for a in range(max_val):
        for b in range(a, max_val):
            yield {f"A={a}, B={b}, OE=0, DIR=X -> A={a}, B={b}": make_test(1, None, a, b)}

                
if __name__ == "__main__":
    tests_dict = {"Tests": {}}
    for test in gen_nbit_tests("adder", 4, "A3,A2,A1,A0", "B3,B2,B1,B0", "S3,S2,S1,S0"):
            tests_dict["Tests"].update(test)
    with open("74hct283.yaml", "w") as f:
        yaml.dump(tests_dict, f, sort_keys=False)
    
    tests_dict["Tests"].clear()
    for test in gen_nbit_tests("comparator", 8, "17,15,13,11,8,6,4,2", 
            "18,16,14,12,9,7,5,3", "19", en_bit=1, active_low=True, invert=True):
        tests_dict["Tests"].update(test)
    with open("74hct688.yaml", "w") as f:
        yaml.dump(tests_dict, f, sort_keys=False)
            
    tests_dict["Tests"].clear()
    for test in gen_transciever(8, "9,8,7,6,5,4,3,2", "11,12,13,14,15,16,17,18"):
        tests_dict["Tests"].update(test)
    with open("74hct245.yaml", 'w') as f:
        yaml.dump(tests_dict, f, sort_keys=False)