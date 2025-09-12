#!/usr/bin/env python3
"""
Simple debug test for LSB steganography
"""
from lsb_steganography import LSBSteganography
import traceback
import json
import struct

def debug_simple_test():
    """Simple debug test"""
    print("Debug: Testing simple LSB steganography...")
    
    key = "debug123"
    cover_data = b"This is a simple cover text that should be long enough for testing. " * 30  # Increased to 30
    payload_data = b"Secret"  # Shortened payload
    
    print(f"Cover data length: {len(cover_data)}")
    print(f"Payload data length: {len(payload_data)}")
    
    try:
        stego = LSBSteganography(key)
        print("✓ LSBSteganography initialized")
        
        # Debug key parameters
        start_pos = stego.key_manager.get_starting_position(len(cover_data))
        step_size = stego.key_manager.get_step_size(len(cover_data))
        bit_offset = stego.key_manager.bit_offset
        
        print(f"Key parameters: start_pos={start_pos}, step_size={step_size}, bit_offset={bit_offset}")
        
        # Calculate message size
        metadata = {
            'version': stego.VERSION,
            'payload_type': 'text',
            'payload_size': len(payload_data),
            'key_info': stego.key_manager.get_metadata()
        }
        
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        metadata_size = len(metadata_bytes)
        
        message = (stego.MAGIC_HEADER + 
                  struct.pack('>B', stego.VERSION) +
                  struct.pack('>H', metadata_size) +
                  metadata_bytes + 
                  payload_data)
        
        message_bits = stego._bytes_to_bits(message)
        message_bits.extend([1, 0, 1, 0, 1, 0, 1, 0])  # End marker
        
        print(f"Message length: {len(message)} bytes")
        print(f"Message bits length: {len(message_bits)} bits")
        print(f"Available positions: {len(cover_data)}")
        
        # Test encoding
        print("Starting encoding...")
        encoded_data = stego.encode(cover_data, payload_data, 'text')
        print(f"✓ Encoding complete. Encoded length: {len(encoded_data)}")
        
        # Test decoding
        print("Starting decoding...")
        decoded_payload, payload_type, metadata = stego.decode(encoded_data)
        print(f"✓ Decoding complete")
        print(f"Decoded payload length: {len(decoded_payload)}")
        print(f"Payload type: {payload_type}")
        print(f"Original payload: {payload_data}")
        print(f"Decoded payload:  {decoded_payload}")
        
        if payload_data == decoded_payload:
            print("✓ SUCCESS: Payload matches!")
            return True
        else:
            print("✗ FAILURE: Payload mismatch")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        traceback.print_exc()
        return False

def debug_message_structure():
    """Debug the message structure creation"""
    print("\nDebug: Testing message structure...")
    
    from lsb_steganography import LSBSteganography
    import json
    import struct
    
    key = "test"
    stego = LSBSteganography(key)
    payload_data = b"Hello"
    
    # Manually create the message structure like in encode()
    metadata = {
        'version': stego.VERSION,
        'payload_type': 'text',
        'payload_size': len(payload_data),
        'key_info': stego.key_manager.get_metadata()
    }
    
    metadata_bytes = json.dumps(metadata).encode('utf-8')
    metadata_size = len(metadata_bytes)
    
    message = (stego.MAGIC_HEADER + 
              struct.pack('>B', stego.VERSION) +
              struct.pack('>H', metadata_size) +
              metadata_bytes + 
              payload_data)
    
    print(f"Magic header: {stego.MAGIC_HEADER}")
    print(f"Version: {stego.VERSION}")
    print(f"Metadata size: {metadata_size}")
    print(f"Metadata: {metadata}")
    print(f"Message length: {len(message)}")
    print(f"Message start: {message[:20]}")
    
    # Test bit conversion
    bits = stego._bytes_to_bits(message)
    print(f"Message bits length: {len(bits)}")
    
    # Test round trip
    back_to_bytes = stego._bits_to_bytes(bits)
    print(f"Round trip successful: {back_to_bytes == message}")
    
if __name__ == '__main__':
    debug_simple_test()
    debug_message_structure()