#!/usr/bin/env python3
"""
Simple debug test for step-by-step LSB steganography
"""
from lsb_steganography import LSBSteganography
import traceback
import json
import struct

def debug_decoding():
    """Debug decoding step by step"""
    print("Debug: Step-by-step decoding test...")
    
    key = "test123"
    cover_data = b"A" * 3000  # Simple repeating pattern
    payload_data = b"Hi"  # Very short payload
    
    print(f"Cover data length: {len(cover_data)} bytes")
    print(f"Payload data: {payload_data}")
    
    stego = LSBSteganography(key)
    
    # Encode
    encoded_data = stego.encode(cover_data, payload_data, 'text')
    print(f"✓ Encoded successfully")
    
    # Manual decode to debug
    start_pos = stego.key_manager.get_starting_position(len(encoded_data))
    bit_offset = stego.key_manager.bit_offset
    target_bit = bit_offset % 8
    
    print(f"Decode parameters: start_pos={start_pos}, bit_offset={bit_offset}, target_bit={target_bit}")
    
    # Extract first 50 bits to see what we get
    extracted_bits = []
    for i in range(50):
        pos = (start_pos + i) % len(encoded_data)
        bit = (encoded_data[pos] >> target_bit) & 1
        extracted_bits.append(bit)
        if i < 20:
            print(f"Pos {pos}: byte={encoded_data[pos]:08b} -> bit {target_bit} = {bit}")
    
    print(f"First 50 extracted bits: {extracted_bits}")
    
    # Try to find our magic header in bits
    magic_bits = stego._bytes_to_bits(stego.MAGIC_HEADER)
    print(f"Magic header bits: {magic_bits}")
    
    # Check if magic header matches
    if extracted_bits[:len(magic_bits)] == magic_bits:
        print("✓ Magic header found at start!")
    else:
        print("✗ Magic header NOT found at start")
        print(f"Expected: {magic_bits}")
        print(f"Got:      {extracted_bits[:len(magic_bits)]}")

if __name__ == '__main__':
    debug_decoding()