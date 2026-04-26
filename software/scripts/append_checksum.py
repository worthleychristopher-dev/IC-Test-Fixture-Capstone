import sys
import hashlib

def calculate_checksum(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(block)

    return sha256_hash.digest()  # raw 32 bytes

def append_checksum(file_path, checksum):
    with open(file_path, "ab") as f:
        f.write(checksum)

if __name__ == "__main__":
    file_path = sys.argv[1]

    checksum = calculate_checksum(file_path)
    print(f"Checksum calculated: {checksum}")
    append_checksum(file_path, checksum)
    print("Checksum appended (32 bytes).")
