from math import gcd
import random

def validate_key(key) -> bool:
    """
    Accepts numeric strings (e.g., '123', '-7') or ints.
    Returns True if convertible to int; else False.
    """
    try:
        int(key)
        return True
    except Exception:
        return False
    
# ---- Position generator (preferred: start + stride) ----
def _stride_for(total: int, key_int: int) -> int:
    """
    Derive a stride from the key that is coprime with 'total'.
    Ensures we traverse the space evenly in a pseudo-random but deterministic way.
    """
    if total <= 1:
        return 1
    stride = 1 + (abs(int(key_int)) % max(1, total - 1))
    # make stride coprime with total
    while gcd(stride, total) != 1:
        stride += 1
        if stride >= total:
            stride = 1
    return stride

def get_embedding_positions(key, data_length, cover_size, lsb_count, start_location=0):
    """
    Return EXACTLY 'data_length' carrier-byte indices (0..cover_size-1) to use for embedding,
    derived deterministically from (key, start_location).
    - key: numeric (string or int)
    - data_length: number of CARRIER BYTES you need to touch (not payload bytes)
    - cover_size: total number of carrier bytes (e.g., w*h*3 for RGB)
    - lsb_count: included for signature parity (not used by this algorithm)
    - start_location: starting index offset
    """
    total = int(cover_size)
    count = int(data_length)
    start = int(start_location) % max(1, total)
    key_int = int(key)

    if count > total:
        count = total

    stride = _stride_for(total, key_int)
    idx = start
    out = []
    for _ in range(count):
        out.append(idx)
        idx = (idx + stride) % total
    return out

def generate_embedding_sequence(key, data_length, cover_size, start_location=0):
    """Generate a pseudo-random embedding sequence based on the key"""
    random.seed(int(key))
    positions = list(range(start_location, cover_size))
    random.shuffle(positions)
    return positions[:data_length]
def validate_key(key):
    try:
        int(key)
        return True
    except ValueError:
        return False