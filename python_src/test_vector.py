class TestVector:
    def __init__(self):
        # 0 for input, 1 for output
        self.test_vec = [None] * 2
    def add_input_vector(self, input_vector: tuple):
        self.test_vec[0] = input_vector
    def add_output_vector(self, output_vector: tuple):
        self.test_vec[1] = output_vector
