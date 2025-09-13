from PIL import Image
import os
from .key_manager import get_embedding_positions
from .utils import iter_bits_lsb, pack_bits_lsb

# --------- small helpers we still need here ---------
def _write_k_bits(byte_val: int, bits_val: int, k: int) -> int:
    mask = (1 << k) - 1
    return (byte_val & ~mask) | (bits_val & mask)

def _read_k_bits(byte_val: int, k: int) -> int:
    return byte_val & ((1 << k) - 1)

def _capacity_bytes_from_wh(width: int, height: int, k: int) -> int:
    # RGB → 3 carrier bytes per pixel; each carries k bits.
    return (width * height * 3 * k) // 8

# ----------------- public API used by app.py -----------------

def calculate_image_capacity(image_file, lsb_count: int) -> int:
    k = int(lsb_count)
    if not (1 <= k <= 8):
        raise ValueError("LSB count must be between 1 and 8")
    img = Image.open(image_file).convert("RGB")
    w, h = img.size
    return _capacity_bytes_from_wh(w, h, k)

def _safe_name(name: str) -> str:
    # keep only basename, strip weird separators
    return os.path.basename(name).strip() or "payload.bin"

def encode_image(cover_path, payload_path, key, lsb_count, start_location):
    """
    Embed payload file's raw bytes into cover image using k LSBs and key+start to choose positions.
    Returns dict with 'stego_path' and metadata (used by app.py to build download URL).
    """
    k = int(lsb_count)
    if not (1 <= k <= 8):
        raise ValueError("LSB count must be 1..8")
    start = int(start_location) if start_location is not None else 0
    # key is now alphanumeric; pass through for internal hashing

    # Load cover (RGB carrier bytes)
    cover_img = Image.open(cover_path).convert("RGB")
    w, h = cover_img.size
    carrier = bytearray(cover_img.tobytes())
    total_carriers = len(carrier)

    # Load payload bytes (any file)
    with open(payload_path, "rb") as f:
        payload = f.read()

    # --- NEW: filename in header ---
    name_bytes = _safe_name(payload_path).encode("utf-8", "ignore")[:65535]
    name_len = len(name_bytes)

    MAGIC = b"ACW1"
    header = MAGIC + name_len.to_bytes(2, "little") + len(payload).to_bytes(4, "little") + name_bytes
    blob = header + payload

    # Capacity & carriers needed
    total_bits = len(blob) * 8
    carriers_needed = (total_bits + k - 1) // k
    capacity_bytes = (w * h * 3 * k) // 8
    if carriers_needed > total_carriers:
        raise ValueError(f"Payload too large: needs {len(blob)} bytes, capacity {capacity_bytes} bytes at k={k}")

    # Get carrier indices from key+start
    positions = get_embedding_positions(key, carriers_needed, total_carriers, k, start)
    if len(positions) < carriers_needed:
        raise ValueError("key_manager.get_embedding_positions returned too few positions.")

    bits = iter_bits_lsb(blob)  # from utils
    for idx in positions:
        v = 0
        for j in range(k):
            try:
                v |= (next(bits) & 1) << j
            except StopIteration:
                pass
        mask = (1 << k) - 1
        carrier[idx] = (carrier[idx] & ~mask) | (v & mask)

    # Choose output format/extension based on cover type
    cover_ext = os.path.splitext(cover_path)[1].lower().lstrip('.')
    out_fmt = 'PNG'
    out_ext = 'png'
    note = None
    if cover_ext == 'bmp':
        out_fmt, out_ext = 'BMP', 'bmp'
    elif cover_ext == 'png':
        out_fmt, out_ext = 'PNG', 'png'
    elif cover_ext == 'gif':
        # GIF is palette-based; to preserve embedded LSBs we save as PNG
        # Also reject animated GIFs silently by converting single frame
        out_fmt, out_ext = 'PNG', 'png'
        note = 'gif_converted_to_png_for_lossless_lsb'

    stego_name = f"stego_{os.path.splitext(os.path.basename(cover_path))[0]}.{out_ext}"
    stego_path = os.path.join(os.path.dirname(cover_path), stego_name)
    Image.frombytes("RGB", (w, h), bytes(carrier)).save(stego_path, format=out_fmt)

    result = {"ok": True, "stego_path": stego_path, "embedded_bytes": len(payload),
              "capacity_bytes": capacity_bytes, "k": k, "start": start, "stego_format": out_fmt}
    if note:
        result['note'] = note
    return result


def decode_image(stego_path, key, lsb_count, start_location=0):
    """
    Decode payload from a stego image created by encode_image using the NEW header:
      [MAGIC 'ACW1'(4)][name_len:2][payload_len:4][name_bytes][payload_bytes]

    Requires the same (k, key, start_location) used for encoding.
    """
    k = int(lsb_count)
    if not (1 <= k <= 8):
        raise ValueError("LSB count must be 1..8")
    start = int(start_location) if start_location is not None else 0
    # key is now alphanumeric; pass through for internal hashing

    stego_img = Image.open(stego_path).convert("RGB")
    w, h = stego_img.size
    data = stego_img.tobytes()
    total_carriers = len(data)

    # Visiting order must match encode
    positions = get_embedding_positions(key, total_carriers, total_carriers, k, start)

    mask = (1 << k) - 1

    # Continuous LSB-first bit stream across carriers (fixes k>1 misalignment)
    def bit_stream():
        for idx in positions:
            v = data[idx] & mask
            for j in range(k):           # LSB-first within each carrier byte
                yield (v >> j) & 1

    bits = bit_stream()

    # Helper: take exactly n bits from the stream (raises ValueError if not enough)
    def take(n):
        try:
            for _ in range(n):
                yield next(bits)
        except StopIteration:
            raise ValueError("Invalid/corrupted stego image or wrong parameters (key/k/start).")

    # ---- Parse NEW header ----
    MAGIC = b"ACW1"

    # MAGIC (4 bytes)
    magic = pack_bits_lsb(take(32))
    if magic[:4] != MAGIC:
        raise ValueError("Not a valid stego image for these parameters (MAGIC mismatch).")

    # name_len (2) + payload_len (4)
    hdr = pack_bits_lsb(take((2 + 4) * 8))
    name_len = int.from_bytes(hdr[:2], "little")
    length   = int.from_bytes(hdr[2:6], "little")
    if not (0 <= name_len <= 65535):
        raise ValueError("Corrupted header (filename length).")

    # filename bytes
    name_bytes = pack_bits_lsb(take(name_len * 8))[:name_len]
    try:
        fname = os.path.basename(name_bytes.decode("utf-8", "ignore")).strip() or "payload.bin"
    except Exception:
        fname = "payload.bin"

    # Bit-level capacity check (precise)
    capacity_bits = total_carriers * k
    header_bits   = (4 + 2 + 4 + name_len) * 8
    if length < 0 or (length * 8) > max(0, capacity_bits - header_bits):
        raise ValueError("Invalid/corrupted stego image or wrong parameters (key/k/start).")

    # Payload
    payload = pack_bits_lsb(take(length * 8))[:length]

    out_path = os.path.join(os.path.dirname(stego_path), fname)
    with open(out_path, "wb") as f:
        f.write(payload)

    return {
        "ok": True,
        "payload_path": out_path,
        "extracted_bytes": len(payload),
        "k": k,
        "start": start
    }
