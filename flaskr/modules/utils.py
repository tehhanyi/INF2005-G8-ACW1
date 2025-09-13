import os
import struct
import hashlib
from PIL import Image
import wave

# =========================
# LSB-first bit utilities
# =========================

def iter_bits_lsb(data: bytes):
    """
    Yield bits LSB-first (ints 0/1) for each byte in 'data'.
    Streaming generator -> low memory for large payloads.
    """
    for b in data:
        for i in range(8):
            yield (b >> i) & 1

def pack_bits_lsb(bits_iter):
    """
    Pack bits (LSB-first) from an iterator/list into bytes.
    Accepts ints 0/1 OR '0'/'1' strings.
    """
    out = bytearray()
    val = 0
    count = 0
    for bit in bits_iter:
        bit_i = 1 if (bit == 1 or bit == '1') else 0
        val |= (bit_i & 1) << (count % 8)
        count += 1
        if count % 8 == 0:
            out.append(val)
            val = 0
    if count % 8 != 0:
        out.append(val)
    return bytes(out)

def bytes_to_bits(data: bytes):
    """
    Convert bytes -> list of bits (LSB-first), as INTs 0/1.
    """
    return [((b >> i) & 1) for b in data for i in range(8)]

def bits_to_bytes(bits):
    """
    Convert list/iter of bits (LSB-first) -> bytes.
    Accepts ints 0/1 OR '0'/'1' strings.
    """
    return pack_bits_lsb(bits)

def string_to_bits(text: str):
    """
    String -> list of LSB-first bits (ints), via UTF-8 encoding.
    """
    return bytes_to_bits(text.encode('utf-8'))

def bits_to_string(bits):
    """
    LSB-first bits -> string via UTF-8 (invalid bytes ignored).
    Accepts ints or '0'/'1' strings.
    """
    try:
        return bits_to_bytes(bits).decode('utf-8', errors='ignore')
    except Exception:
        return ""

# =========================
# File utilities
# =========================

def calculate_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def validate_file_exists(file_path):
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'File does not exist'}
    if not os.path.isfile(file_path):
        return {'valid': False, 'error': 'Path is not a file'}
    if not os.access(file_path, os.R_OK):
        return {'valid': False, 'error': 'File is not readable'}
    return {'valid': True}

def validate_image_file(file_path):
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'File does not exist'}
    try:
        with Image.open(file_path) as im:
            im.verify() 
        with Image.open(file_path) as im2:
            w, h = im2.size
            mode = im2.mode
        return {'valid': True, 'width': w, 'height': h, 'mode': mode}
    except Exception as e:
        return {'valid': False, 'error': f'Invalid image: {e}'}

def validate_file_size(file_path, max_size_mb=5):
    size_bytes = calculate_file_size(file_path)
    if size_bytes == 0:
        return {'valid': False, 'error': 'File does not exist or is empty'}
    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        return {'valid': False, 'error': f'File exceeds maximum size of {max_size_mb} MB'}
    
    return {'valid': True}

def get_file_info(file_path):
    if not os.path.exists(file_path):
        return {'error': 'File does not exist'}
    
    file_info = {}
    file_info['name'] = os.path.basename(file_path)
    file_info['size_bytes'] = calculate_file_size(file_path)
    file_info['extension'] = os.path.splitext(file_path)[1].lower()
    
    return file_info