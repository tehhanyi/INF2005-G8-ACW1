import wave
import numpy as np
import os
from .key_manager import generate_embedding_sequence, validate_key
from .utils import bytes_to_bits, bits_to_bytes


def _load_wav_as_array(path):
    with wave.open(path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        frames = wf.readframes(n_frames)

    if sampwidth == 1:
        dtype = np.uint8  # 8-bit PCM unsigned
    elif sampwidth == 2:
        dtype = np.int16  # 16-bit PCM signed little-endian
    else:
        raise ValueError('Unsupported WAV sample width: {} bytes'.format(sampwidth))

    samples = np.frombuffer(frames, dtype=dtype).copy()
    return samples, n_channels, sampwidth, framerate


def _write_wav_from_array(path, samples, n_channels, sampwidth, framerate):
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(samples.tobytes())


def _embed_bits_into_samples(samples: np.ndarray, bits, lsb_count: int, key: str, start_location: int, n_channels: int):
    if lsb_count < 1 or lsb_count > 8:
        raise ValueError('lsb_count must be between 1 and 8')

    # Total embedding slots = number of samples (including interleaved channels) * lsb_count
    total_slots = samples.size * lsb_count
    total_bits = len(bits)

    if start_location < 0:
        start_location = 0

    if start_location + total_bits > total_slots:
        raise ValueError('Payload too large for selected LSBs and start location')

    positions = generate_embedding_sequence(key, total_bits, total_slots, start_location=start_location)

    # Embed each bit into the specified bit position of the target sample
    for i, b in enumerate(bits):
        bit_val = 1 if b == '1' else 0
        slot = positions[i]
        sample_index = slot // lsb_count
        bit_index = slot % lsb_count  # 0 = LSB
        # Clear and set the bit_index bit
        samples[sample_index] = (samples[sample_index] & ~(1 << bit_index)) | (bit_val << bit_index)


def _extract_bits_from_samples(samples: np.ndarray, num_bits: int, lsb_count: int, key: str, start_location: int):
    if lsb_count < 1 or lsb_count > 8:
        raise ValueError('lsb_count must be between 1 and 8')

    total_slots = samples.size * lsb_count
    if start_location < 0:
        start_location = 0
    if start_location + num_bits > total_slots:
        raise ValueError('Requested extraction exceeds available capacity')

    positions = generate_embedding_sequence(key, num_bits, total_slots, start_location=start_location)
    out_bits = []
    for slot in positions:
        sample_index = slot // lsb_count
        bit_index = slot % lsb_count
        bit_val = (int(samples[sample_index]) >> bit_index) & 1
        out_bits.append('1' if bit_val else '0')
    return out_bits


def encode_audio(cover_path, payload_path, key, lsb_count, start_location):
    """Encode payload into a WAV audio file using LSB steganography.

    Header format (new):
      MAGIC(4)='STG1' | VER(1)=1 | NAME_LEN(2, big) | PAYLOAD_LEN(4, big) | NAME(bytes)
    Followed by raw payload bytes.

    Returns a dict with the stego file path and basic info.
    """
    if not validate_key(key):
        raise ValueError('Invalid key format; expecting numeric key')

    try:
        start_loc = int(start_location) if start_location is not None else 0
    except Exception:
        start_loc = 0

    samples, n_channels, sampwidth, framerate = _load_wav_as_array(cover_path)

    # Read payload and prepend header with filename metadata
    with open(payload_path, 'rb') as f:
        payload = f.read()
    payload_len = len(payload)
    if payload_len <= 0:
        raise ValueError('Payload is empty')

    name = os.path.basename(payload_path)
    name_bytes = name.encode('utf-8', errors='ignore')
    name_len = len(name_bytes)
    if name_len > 65535:
        # Clamp excessively long names
        name_bytes = name_bytes[:65535]
        name_len = len(name_bytes)

    header = b'STG1' + bytes([1]) + name_len.to_bytes(2, 'big') + payload_len.to_bytes(4, 'big') + name_bytes
    all_bytes = header + payload
    bits = bytes_to_bits(all_bytes)

    _embed_bits_into_samples(samples, bits, int(lsb_count), str(key), int(start_loc), n_channels)

    # Write out stego WAV next to cover file
    base, ext = os.path.splitext(cover_path)
    stego_path = f"{base}_stego.wav"
    _write_wav_from_array(stego_path, samples, n_channels, sampwidth, framerate)

    return {
        'stego_path': stego_path,
        'cover_channels': n_channels,
        'sample_width': sampwidth,
        'framerate': framerate,
        'payload_bytes': payload_len,
    }


def decode_audio(stego_path, key, lsb_count, start_location=0):
    """Decode payload from a WAV stego audio using the same key and LSBs.

    Assumes start_location = 0. If a non-zero start was used for encoding,
    the same must be provided and this function should be extended accordingly.
    """
    if not validate_key(key):
        raise ValueError('Invalid key format; expecting numeric key')

    samples, n_channels, sampwidth, framerate = _load_wav_as_array(stego_path)
    total_slots = samples.size * int(lsb_count)
    if start_location < 0:
        start_location = 0

    # Try new header first: need 11 bytes (88 bits) to parse magic, version, name_len, payload_len
    hdr_len_bytes_fixed = 11
    # If not enough capacity beyond start, fail early with a clear message
    if (hdr_len_bytes_fixed * 8) > (total_slots - int(start_location)):
        raise ValueError('Decoding failed: insufficient capacity at start position (check start_location)')

    hdr_bits = _extract_bits_from_samples(samples, hdr_len_bytes_fixed * 8, int(lsb_count), str(key), int(start_location))
    hdr = bits_to_bytes(hdr_bits)

    if len(hdr) >= 11 and hdr[:4] == b'STG1':
        ver = hdr[4]
        name_len = int.from_bytes(hdr[5:7], 'big')
        payload_len = int.from_bytes(hdr[7:11], 'big')
        if name_len < 0 or payload_len < 0 or name_len > 65535:
            raise ValueError('Decoding failed: invalid header (check key/lsb/start)')

        total_len_bytes = hdr_len_bytes_fixed + name_len + payload_len
        total_bits = total_len_bytes * 8
        # Validate against capacity beyond start_location
        if total_bits > (total_slots - int(start_location)):
            raise ValueError('Decoding failed: header implies size beyond capacity (check key/lsb/start)')
        all_bits = _extract_bits_from_samples(samples, total_bits, int(lsb_count), str(key), int(start_location))
        all_bytes = bits_to_bytes(all_bits)
        name_bytes = all_bytes[11:11 + name_len]
        payload_bytes = all_bytes[11 + name_len:11 + name_len + payload_len]
        try:
            decoded_name = name_bytes.decode('utf-8', errors='ignore') or 'extracted.bin'
        except Exception:
            decoded_name = 'extracted.bin'
        decoded_name = os.path.basename(decoded_name)
        if not decoded_name:
            decoded_name = 'extracted.bin'

        out_dir = os.path.dirname(stego_path)
        out_path = os.path.join(out_dir, decoded_name)
        with open(out_path, 'wb') as f:
            f.write(payload_bytes)

        return {
            'payload_path': out_path,
            'payload_filename': decoded_name,
            'payload_bytes': payload_len,
            'header_version': int(ver),
        }
    else:
        # Fallback to legacy format: first 4 bytes is payload length only
        # We already read 88 bits; however for legacy we need only first 32 bits.
        # Re-extract just the first 32 bits to avoid confusion.
        if 32 > (total_slots - int(start_location)):
            raise ValueError('Decoding failed: insufficient capacity at start position (check start_location)')
        header_bits_legacy = _extract_bits_from_samples(samples, 32, int(lsb_count), str(key), int(start_location))
        payload_len = int(''.join(header_bits_legacy), 2)
        if payload_len < 0:
            raise ValueError('Decoding failed: invalid payload length (check key/lsb/start)')

        total_bits = 32 + payload_len * 8
        if total_bits > (total_slots - int(start_location)):
            raise ValueError('Decoding failed: legacy length beyond capacity (check key/lsb/start)')
        bits = _extract_bits_from_samples(samples, total_bits, int(lsb_count), str(key), int(start_location))
        payload_bits = bits[32:]
        payload_bytes = bits_to_bytes(payload_bits)

        base, _ = os.path.splitext(stego_path)
        out_path = f"{base}_extracted.bin"
        with open(out_path, 'wb') as f:
            f.write(payload_bytes[:payload_len])

        return {
            'payload_path': out_path,
            'payload_filename': os.path.basename(out_path),
            'payload_bytes': payload_len,
            'header_version': 0,
        }


def calculate_audio_capacity(audio_file, lsb_count):
    """Calculate capacity (in bytes) for a WAV audio given LSB count.

    Accepts a Werkzeug FileStorage or a file path. Returns integer bytes.
    """
    if lsb_count < 1 or lsb_count > 8:
        raise ValueError('lsb_count must be between 1 and 8')

    try:
        # If a FileStorage-like object is passed
        if hasattr(audio_file, 'stream'):
            stream = audio_file.stream
            pos = stream.tell()
            try:
                with wave.open(stream, 'rb') as wf:
                    n_frames = wf.getnframes()
                    n_channels = wf.getnchannels()
            finally:
                # Reset stream for any subsequent reads by Flask
                try:
                    stream.seek(pos)
                except Exception:
                    pass
        else:
            # Assume it is a file path
            with wave.open(audio_file, 'rb') as wf:
                n_frames = wf.getnframes()
                n_channels = wf.getnchannels()
    except wave.Error as e:
        raise ValueError(f'Unsupported or invalid WAV file: {e}')

    total_samples = n_frames * n_channels
    total_bits = total_samples * int(lsb_count)
    return total_bits // 8
