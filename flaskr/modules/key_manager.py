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

# ---- Key+Start helpers ----
def _split_key_and_start(key: str):
    """Split a composite key of the form 'KEY@START'.
    Returns (key_main, start_str or None). Whitespace trimmed.
    """
    if key is None:
        return '', None
    s = str(key)
    if '@' in s:
        left, right = s.split('@', 1)
        return left.strip(), right.strip()
    return s.strip(), None

def extract_image_start_from_key(key: str, width: int, height: int):
    """If key contains '@x,y' or '@@x,y', return (key_main, 'x,y' clamped). Otherwise (key, None)."""
    key_main, start = _split_key_and_start(key)
    if not start:
        return key_main, None
    # Accept '@x,y' and '@@x,y' by stripping any leading '@'
    if start.startswith('@'):
        start = start.lstrip('@')
    if ',' not in start:
        return key_main, None
    try:
        sx, sy = start.split(',', 1)
        x = int(float(sx))
        y = int(float(sy))
    except Exception:
        return key_main, None
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    return key_main, f"{x},{y}"

def extract_audio_start_from_key(key: str):
    """If key contains '@N', return (key_main, int(N) >=0). Otherwise (key, None)."""
    key_main, start = _split_key_and_start(key)
    if not start:
        return key_main, None
    try:
        n = int(float(start))
        if n < 0:
            n = 0
        return key_main, n
    except Exception:
        return key_main, None
    
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
