# modules/image_stego.py
from PIL import Image, ImageOps
import os
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
    """Parse start as (x,y) pixel coordinates. If a single integer is given,
    treat it as a pixel index and convert to (x,y). Values are clamped to bounds.
    """
    if start_input is None or str(start_input).strip() == "":
        return 0, 0
    s = str(start_input).strip()
    if "," in s:
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
    try:
        pixel_index = int(float(s))
    except Exception:
        pixel_index = 0
    pixel_index = max(0, min(w * h - 1, pixel_index))
    y, x = divmod(pixel_index, w)
    return x, y

def parse_start_location(start_input, width: int, height: int) -> int:
    """Public helper to convert start input into carrier-byte offset for given image size."""
    total_carriers = width * height * 3
    return _parse_start_pixel_to_byte(start_input, width, height, total_carriers)

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
    name_bytes = _safe_name(payload_path).encode("utf-8", "ignore")[:65535]
    name_len = len(name_bytes)
    header = MAGIC + name_len.to_bytes(2, "little") + len(payload).to_bytes(4, "little") + name_bytes
    blob = header + payload

    total_bits = len(blob) * 8
    carriers_needed = (total_bits + k - 1) // k
    capacity_bytes = (w * h * 3 * k) // 8
    if carriers_needed > total_carriers:
        raise ValueError(f"Payload too large: needs {len(blob)} bytes, capacity {capacity_bytes} bytes at k={k}")

    # Capped embedding (no wrap-around) and explicit pixel-ordered traversal
    end = start + carriers_needed
    if end > total_carriers:
        raise ValueError(f"Payload too large for starting location")

    def positions_iter():
        remaining = carriers_needed
        for yy in range(start_y, h):
            xx0 = start_x if yy == start_y else 0
            for xx in range(xx0, w):
                base = ((yy * w) + xx) * 3
                for ch in range(3):
                    if remaining <= 0:
                        return
                    yield base + ch
                    remaining -= 1

    positions = positions_iter()

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
    out_fmt, out_ext = ('PNG', 'png') if cover_ext != 'bmp' else ('BMP', 'bmp')
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

    start = _parse_start_pixel_to_byte(start_location, w, h, total_carriers)

    # Wrap-around extraction (read all bytes starting from start)
    positions = [(start + i) % total_carriers for i in range(total_carriers)]

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

    hdr = pack_bits_lsb((next(bits) for _ in range((2 + 4) * 8)))
    name_len = int.from_bytes(hdr[:2], "little")
    length   = int.from_bytes(hdr[2:6], "little")
    if not (0 <= name_len <= 65535):
        raise ValueError("Corrupted header (filename length).")

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
