#!/usr/bin/env python3
"""
Test script for LSB Steganography functionality
"""
import os
import tempfile
from lsb_steganography import LSBSteganography, detect_file_type

def test_text_steganography():
    """Test basic text steganography"""
    print("Testing text steganography...")
    
    # Test data
    key = "test123"
    cover_text = "This is a cover text file that will be used to hide secret data. " * 50
    secret_message = "This is the secret message that should be hidden!"
    
    cover_data = cover_text.encode('utf-8')
    payload_data = secret_message.encode('utf-8')
    
    # Initialize steganography
    stego = LSBSteganography(key)
    
    try:
        # Encode
        encoded_data = stego.encode(cover_data, payload_data, 'text')
        print(f"✓ Encoding successful. Cover: {len(cover_data)} bytes -> Encoded: {len(encoded_data)} bytes")
        
        # Decode
        decoded_payload, payload_type, metadata = stego.decode(encoded_data)
        decoded_message = decoded_payload.decode('utf-8')
        
        print(f"✓ Decoding successful. Payload type: {payload_type}")
        print(f"✓ Original message: {secret_message}")
        print(f"✓ Decoded message:  {decoded_message}")
        
        if secret_message == decoded_message:
            print("✓ Text steganography test PASSED")
            return True
        else:
            print("✗ Text steganography test FAILED - messages don't match")
            return False
            
    except Exception as e:
        print(f"✗ Text steganography test FAILED: {e}")
        return False

def test_key_validation():
    """Test key validation functionality"""
    print("\nTesting key validation...")
    
    key1 = "correct_key"
    key2 = "wrong_key"
    
    cover_data = b"This is cover data that needs to be long enough for the test." * 50  # Increased size
    payload_data = b"Secret payload data"
    
    # Encode with key1
    stego1 = LSBSteganography(key1)
    encoded_data = stego1.encode(cover_data, payload_data, 'text')
    print("✓ Encoded with key1")
    
    # Try to decode with key1 (should work)
    try:
        decoded_payload, _, _ = stego1.decode(encoded_data)
        if decoded_payload == payload_data:
            print("✓ Decoding with correct key PASSED")
        else:
            print("✗ Decoding with correct key FAILED - data mismatch")
            return False
    except Exception as e:
        print(f"✗ Decoding with correct key FAILED: {e}")
        return False
    
    # Try to decode with key2 (should fail)
    stego2 = LSBSteganography(key2)
    try:
        decoded_payload, _, _ = stego2.decode(encoded_data)
        print("✗ Key validation test FAILED - wrong key was accepted")
        return False
    except ValueError as e:
        if "Invalid key" in str(e):
            print("✓ Key validation test PASSED - wrong key rejected")
            return True
        else:
            print(f"✗ Key validation test FAILED - unexpected error: {e}")
            return False
    except Exception as e:
        print(f"✗ Key validation test FAILED - unexpected error: {e}")
        return False

def test_different_file_types():
    """Test detection of different file types"""
    print("\nTesting file type detection...")
    
    test_cases = [
        (b"Just plain text content", "test.txt", "text"),
        (b"%PDF-1.4\n%Fake PDF content", "document.pdf", "pdf"),
        (b"MZ\x90\x00Fake EXE content", "program.exe", "exe"),
        (b"\xFF\xD8\xFF\xE0Fake JPEG", "image.jpg", "image"),
        (b"Random binary data \x00\x01\x02", "unknown.bin", "other"),
    ]
    
    all_passed = True
    for data, filename, expected_type in test_cases:
        detected_type = detect_file_type(data, filename)
        if detected_type == expected_type:
            print(f"✓ {filename} -> {detected_type} (correct)")
        else:
            print(f"✗ {filename} -> {detected_type} (expected {expected_type})")
            all_passed = False
    
    return all_passed

def test_binary_data():
    """Test with binary data"""
    print("\nTesting binary data steganography...")
    
    key = "binary_test_key"
    
    # Create binary cover data (simulate an image or binary file)
    cover_data = bytes(range(256)) * 10  # 2560 bytes of varied binary data
    
    # Create binary payload (simulate a small file)
    payload_data = b"\x89PNG\r\n\x1a\n" + bytes([i % 256 for i in range(100)])
    
    stego = LSBSteganography(key)
    
    try:
        # Encode
        encoded_data = stego.encode(cover_data, payload_data, 'image')
        print(f"✓ Binary encoding successful. Cover: {len(cover_data)} bytes -> Encoded: {len(encoded_data)} bytes")
        
        # Decode
        decoded_payload, payload_type, metadata = stego.decode(encoded_data)
        
        print(f"✓ Binary decoding successful. Payload type: {payload_type}")
        print(f"✓ Original payload size: {len(payload_data)}")
        print(f"✓ Decoded payload size: {len(decoded_payload)}")
        
        if payload_data == decoded_payload:
            print("✓ Binary data steganography test PASSED")
            return True
        else:
            print("✗ Binary data steganography test FAILED - data mismatch")
            return False
            
    except Exception as e:
        print(f"✗ Binary data steganography test FAILED: {e}")
        return False

def test_capacity_limits():
    """Test capacity limits"""
    print("\nTesting capacity limits...")
    
    key = "capacity_test"
    stego = LSBSteganography(key)
    
    # Small cover data
    small_cover = b"Small cover data"
    large_payload = b"This payload is much larger than the cover data" * 100
    
    try:
        encoded_data = stego.encode(small_cover, large_payload, 'text')
        print("✗ Capacity test FAILED - should have rejected large payload")
        return False
    except ValueError as e:
        if "too small" in str(e):
            print("✓ Capacity test PASSED - correctly rejected oversized payload")
            return True
        else:
            print(f"✗ Capacity test FAILED - unexpected error: {e}")
            return False
    except Exception as e:
        print(f"✗ Capacity test FAILED - unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print("LSB Steganography Test Suite")
    print("=" * 40)
    
    tests = [
        test_text_steganography,
        test_key_validation,
        test_different_file_types,
        test_binary_data,
        test_capacity_limits
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED!")
        return True
    else:
        print(f"❌ {total - passed} tests FAILED")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)