#!/usr/bin/env python3
"""
Test the encoding/decoding manually
"""
from lsb_steganography import LSBSteganography

def test_manual():
    # Read the test cover file
    with open('test_cover.txt', 'rb') as f:
        cover_data = f.read()
    
    key = "test123"
    payload_text = "Secret!"
    payload_data = payload_text.encode('utf-8')
    
    print(f"Cover size: {len(cover_data)} bytes")
    print(f"Payload: {payload_text} ({len(payload_data)} bytes)")
    
    # Test encoding
    stego = LSBSteganography(key)
    try:
        encoded_data = stego.encode(cover_data, payload_data, 'text')
        print(f"✓ Encoded successfully: {len(encoded_data)} bytes")
        
        # Save encoded file
        with open('manual_encoded.txt', 'wb') as f:
            f.write(encoded_data)
        
        # Test decoding
        decoded_payload, payload_type, metadata = stego.decode(encoded_data)
        decoded_text = decoded_payload.decode('utf-8')
        
        print(f"✓ Decoded successfully")
        print(f"Payload type: {payload_type}")
        print(f"Original: {payload_text}")
        print(f"Decoded:  {decoded_text}")
        print(f"Match: {payload_text == decoded_text}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_manual()