import hashlib

def verify_checksum(file_path):
    """Checks .exe checksum using SHA-256, assumes last 32 bytes are expected checksum"""
    with open(file_path, "rb") as f:
        data = f.read()

    if len(data) < 32:
        return False  # file too small or corrupted

    original = data[:-32]
    stored = data[-32:] 

    computed = hashlib.sha256(original).digest()

    return computed == stored
