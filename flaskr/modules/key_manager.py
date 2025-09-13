from math import gcd
import random
import hashlib

def _normalize_key_str(key) -> str:
    return str(key).strip().lower()

def key_to_int(key) -> int:
    """
    Case-insensitive alphanumeric key derivation.
    Deterministically hash the key to a 64-bit integer seed.
    """
    s = _normalize_key_str(key)
    # empty becomes 0
    if not s:
        return 0
    # Preserve legacy behavior for pure numeric keys
    if s.lstrip('-').isdigit():
        try:
            return int(s)
        except Exception:
            pass
    h = hashlib.sha256(s.encode('utf-8')).digest()
    return int.from_bytes(h[:8], 'big', signed=False)

def validate_key(key) -> bool:
    """
    Accept any non-empty string (case-insensitive). Numbers also valid.
    """
    return _normalize_key_str(key) != ''
    
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
    key_int = key_to_int(key)

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
    random.seed(key_to_int(key))
    positions = list(range(start_location, cover_size))
    random.shuffle(positions)
    return positions[:data_length]
