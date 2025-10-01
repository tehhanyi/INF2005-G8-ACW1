# modules/image_stego.py
from PIL import Image, ImageOps
import os
import hashlib
import random
from .utils import iter_bits_lsb, pack_bits_lsb

def _safe_name(name: str) -> str:
    return os.path.basename(name).strip() or "payload.bin"

def _capacity_bytes_from_wh(width: int, height: int, k: int) -> int:
    return (width * height * 3 * k) // 8

def calculate_image_capacity(image_file, lsb_count: int) -> int:
    k = int(lsb_count)
    if not (1 <= k <= 8):
        raise ValueError("LSB count must be between 1 and 8")
    img = Image.open(image_file).convert("RGB")
    w, h = img.size
    return _capacity_bytes_from_wh(w, h, k)

def _parse_start_pixel_to_byte(start_input, w, h, total_carriers):
    """Treat user input as PIXEL index; support 'x,y' too; convert to byte offset (×3)."""
    if start_input is None or str(start_input).strip() == "":
        return 0
    s = str(start_input).strip()
    if "," in s:
        sx, sy = s.split(",", 1)
        x = max(0, min(w - 1, int(float(sx))))
        y = max(0, min(h - 1, int(float(sy))))
        pixel_index = y * w + x
    else:
        pixel_index = int(float(s))
        pixel_index = max(0, min(w * h - 1, pixel_index))
    return pixel_index * 3  # first channel of that pixel

def _parse_start_xy(start_input, w, h):
    """Parse start as strict (x,y) pixel coordinates. Values are clamped to bounds.
    Raises ValueError if input is not 'x,y'.
    """
    if start_input is None:
        return 0, 0
    s = str(start_input).strip()
    if "," not in s:
        raise ValueError("Start location must be in 'x,y' format for images.")
    sx, sy = s.split(",", 1)
    try:
        x = int(float(sx))
    except Exception:
        x = 0
    try:
        y = int(float(sy))
    except Exception:
        y = 0
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    return x, y

def parse_start_location(start_input, width: int, height: int) -> int:
    """Public helper that enforces (x,y) format for images.
    Returns the carrier-byte offset for the first channel of that pixel.
    Raises ValueError if the input is not in 'x,y' shape.
    """
    s = str(start_input).strip() if start_input is not None else ''
    if ',' not in s:
        raise ValueError("Start location must be in 'x,y' format for images.")
    x, y = _parse_start_xy(s, width, height)
    return (y * width + x) * 3

def _scattered_positions(total_carriers: int, start: int, key, w: int, h: int):
    """Key-seeded pseudo-random order over the SUFFIX starting at 'start'.

    - Restricts embedding to pixels at or after the selected start pixel.
    - No wrap-around: nothing before 'start' is touched.
    - Shuffles eligible pixels using a deterministic seed from (key,w,h).
    - Expands each pixel to its three channel-byte indices in R,G,B order.
    """
    if total_carriers <= 0:
        return []
    n_pixels = max(0, w * h)
    if n_pixels == 0:
        return []
    # Compute starting pixel index from byte offset
    start_pixel = (start // 3)
    if start_pixel < 0:
        start_pixel = 0
    if start_pixel >= n_pixels:
        return []

    # Eligible pixels are only those at or after the start pixel
    eligible_pixels = list(range(start_pixel, n_pixels))
    seed_bytes = (f"ACW1|IMG|{w}x{h}|{key}").encode("utf-8", "ignore")
    seed = int.from_bytes(hashlib.sha256(seed_bytes).digest()[:8], "little")
    rng = random.Random(seed)
    rng.shuffle(eligible_pixels)

    # Expand to byte indices in channel order (R,G,B), clipped to available carriers
    out = []
    out_extend = out.extend
    max_needed = total_carriers - (start_pixel * 3)
    for p in eligible_pixels:
        base = p * 3
        out_extend((base, base + 1, base + 2))
        if len(out) >= max_needed:
            break
    return out[:max_needed]

def encode_image(cover_path, payload_path, key, lsb_count, start_location):
    k = int(lsb_count)
    if not (1 <= k <= 8):
        raise ValueError("LSB count must be between 1 and 8")

    cover_img = ImageOps.exif_transpose(Image.open(cover_path)).convert("RGB")
    w, h = cover_img.size
    carrier = bytearray(cover_img.tobytes())
    total_carriers = len(carrier)

    # Compute precise (x,y) start and corresponding byte offset
    start_x, start_y = _parse_start_xy(start_location, w, h)
    start = (start_y * w + start_x) * 3

    with open(payload_path, "rb") as f:
        payload = f.read()

    MAGIC = b"ACW1"
    key_bytes = str(key).encode("utf-8", "ignore")
    key_sig = hashlib.sha256(key_bytes).digest()[:4]
    name_bytes = _safe_name(payload_path).encode("utf-8", "ignore")[:65535]
    name_len = len(name_bytes)
    # Header: MAGIC(4) | KEY_SIG(4) | NAME_LEN(2) | PAYLOAD_LEN(4) | NAME
    header = MAGIC + key_sig + name_len.to_bytes(2, "little") + len(payload).to_bytes(4, "little") + name_bytes
    blob = header + payload

    total_bits = len(blob) * 8
    carriers_needed = (total_bits + k - 1) // k
    capacity_bytes = (w * h * 3 * k) // 8
    # Scattered embedding over suffix only
    positions_full = _scattered_positions(total_carriers, start, key, w, h)
    available_from_start = (len(positions_full) * k) // 8
    if carriers_needed > len(positions_full):
        raise ValueError(
            f"Payload too large for starting location: needs {len(blob)} bytes, "
            f"available from start {available_from_start} bytes at k={k}"
        )
    positions = positions_full[:carriers_needed]

    bits = iter_bits_lsb(blob)
    mask = (1 << k) - 1
    for idx in positions:
        try:
            val = 0
            for _ in range(k):
                val = (val << 1) | next(bits)
            carrier[idx] = (carrier[idx] & ~mask) | val
        except StopIteration:
            break

    cover_ext = os.path.splitext(cover_path)[1].lower().lstrip('.')
    supported_formats = {
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'gif': 'GIF',
        'png': 'PNG',
        'bmp': 'BMP'
    }
    out_fmt = supported_formats.get(cover_ext, 'PNG')
    out_ext = cover_ext if cover_ext in supported_formats else 'png'
    # out_fmt, out_ext = ('PNG', 'png') if cover_ext != 'bmp' else ('BMP', 'bmp')
    stego_name = f"stego_{os.path.splitext(os.path.basename(cover_path))[0]}.{out_ext}"
    stego_path = os.path.join(os.path.dirname(cover_path), stego_name)
    Image.frombytes("RGB", (w, h), bytes(carrier)).save(stego_path, format=out_fmt)

    return {
        "ok": True,
        "stego_path": stego_path,
        "embedded_bytes": len(payload),
        "capacity_bytes": capacity_bytes,
        "k": k,
        "start": start,
        "start_xy": [start_x, start_y],
        "stego_format": out_fmt,
    }

def decode_image(stego_path, key, lsb_count, start_location=0):
    k = int(lsb_count)
    if not (1 <= k <= 8):
        raise ValueError("LSB count must be between 1 and 8")

    stego_img = ImageOps.exif_transpose(Image.open(stego_path)).convert("RGB")
    w, h = stego_img.size
    data = stego_img.tobytes()
    total_carriers = len(data)
  
    # Enforce (x,y) for images during decode as well
    start_x, start_y = _parse_start_xy(start_location, w, h)
    start = (start_y * w + start_x) * 3
    
    # Scattered extraction: reproduce key-seeded rotation from the same 'start'
    positions = _scattered_positions(total_carriers, start, key, w, h)
    
    mask = (1 << k) - 1
    
    def bit_stream():
        for idx in positions:
            v = data[idx] & mask
            for j in reversed(range(k)):
                yield (v >> j) & 1
    
    MAGIC = b"ACW1"
    bits = bit_stream()
    
    magic = pack_bits_lsb((next(bits) for _ in range(32)))
    if magic[:4] != MAGIC:
        raise ValueError("Not a valid stego image for these parameters (MAGIC mismatch).")
    
    # Verify key signature (next 4 bytes)
    key_sig_emb = pack_bits_lsb((next(bits) for _ in range(32)))
    exp_sig = hashlib.sha256(str(key).encode("utf-8", "ignore")).digest()[:4]
    if key_sig_emb[:4] != exp_sig:
        raise ValueError("Wrong key for this stego image.")
    
    # Read name_len(2) + payload_len(4)
    hdr = pack_bits_lsb((next(bits) for _ in range((2 + 4) * 8)))
    name_len = int.from_bytes(hdr[:2], "little")
    length   = int.from_bytes(hdr[2:6], "little")
    if not (0 <= name_len <= 65535):
        raise ValueError("Corrupted header (filename length).")
    # Read filename
    name_bytes = pack_bits_lsb((next(bits) for _ in range(name_len * 8)))[:name_len]
    try:
        fname = os.path.basename(name_bytes.decode("utf-8", "ignore")).strip() or "payload.bin"
    except Exception:
        fname = "payload.bin"
    
    payload = pack_bits_lsb((next(bits) for _ in range(length * 8)))[:length]

    out_path = os.path.join(os.path.dirname(stego_path), fname)
    with open(out_path, "wb") as f:
        f.write(payload)

    return {"ok": True, "payload_path": out_path, "extracted_bytes": len(payload), "k": k, "start": start}
