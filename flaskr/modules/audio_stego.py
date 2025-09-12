import wave
import numpy as np
import os
from .key_manager import generate_embedding_sequence, validate_key
from .utils import bytes_to_bits, bits_to_bytes, calculate_file_size

def encode_audio(cover_path, payload_path, key, lsb_count, start_location):
    """Encode payload into audio using LSB steganography"""
    return {}
def decode_audio(stego_path, key, lsb_count):
    """Decode payload from stego audio"""
    
    return {}

def calculate_audio_capacity(audio_file, lsb_count):
#idk if need this
    return 0