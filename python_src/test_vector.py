# TODO: make iterable
class TestVector:
    def __init__(self, test_names: list):
        # 0 for input, 1 for output
        self.test_vec = {test_names: [None]*2 for test_names in test_names}

    def add_input_vector(self, test_name: str, input_vector: tuple):
        self.test_vec[test_name][0] = input_vector

    def add_output_vector(self, test_name: str, output_vector: tuple):
        self.test_vec[test_name][1] = output_vector

    def get_test_vector(self, test_name: str):
        return self.test_vec[test_name]

