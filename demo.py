#!/usr/bin/env python3
"""
Demo script showing LSB Steganography capabilities
"""
from lsb_steganography import LSBSteganography, detect_file_type
import os

def demo_text_steganography():
    """Demonstrate basic text steganography"""
    print("🔤 TEXT STEGANOGRAPHY DEMO")
    print("=" * 50)
    
    # Create sample data
    cover_text = """
    This is a sample cover document that contains normal-looking text.
    It will be used to hide secret messages using LSB steganography.
    The content appears completely normal to anyone reading it.
    Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    """ * 10  # Make it large enough
    
    secret_message = "🔐 This is a secret message hidden in the text! 🔐"
    key = "MySecretKey123"
    
    print(f"📄 Cover text length: {len(cover_text)} characters")
    print(f"🤫 Secret message: {secret_message}")
    print(f"🔑 Key: {key}")
    print()
    
    # Encode
    stego = LSBSteganography(key)
    cover_data = cover_text.encode('utf-8')
    payload_data = secret_message.encode('utf-8')
    
    encoded_data = stego.encode(cover_data, payload_data, 'text')
    print(f"✅ Encoding successful!")
    print(f"📊 Original: {len(cover_data)} bytes → Encoded: {len(encoded_data)} bytes")
    
    # Save encoded file
    with open('demo_encoded.txt', 'wb') as f:
        f.write(encoded_data)
    print(f"💾 Saved to: demo_encoded.txt")
    print()
    
    # Decode
    decoded_payload, payload_type, metadata = stego.decode(encoded_data)
    decoded_message = decoded_payload.decode('utf-8')
    
    print(f"🔓 Decoding successful!")
    print(f"📋 Payload type: {payload_type}")
    print(f"📤 Decoded message: {decoded_message}")
    print(f"✔️  Match: {secret_message == decoded_message}")
    print()

def demo_key_security():
    """Demonstrate key-based security"""
    print("🛡️  KEY SECURITY DEMO")
    print("=" * 50)
    
    cover_data = b"A" * 5000  # Simple cover data
    secret = b"Top Secret Information!"
    correct_key = "CorrectPassword"
    wrong_key = "WrongPassword"
    
    # Encode with correct key
    stego_correct = LSBSteganography(correct_key)
    encoded_data = stego_correct.encode(cover_data, secret, 'text')
    print(f"✅ Encoded with key: '{correct_key}'")
    
    # Try to decode with correct key
    try:
        decoded, _, _ = stego_correct.decode(encoded_data)
        print(f"✅ Correct key decoding: SUCCESS")
        print(f"📤 Decoded: {decoded.decode('utf-8')}")
    except Exception as e:
        print(f"❌ Correct key decoding: FAILED - {e}")
    
    # Try to decode with wrong key
    stego_wrong = LSBSteganography(wrong_key)
    try:
        decoded, _, _ = stego_wrong.decode(encoded_data)
        print(f"❌ Wrong key decoding: SHOULD NOT SUCCEED")
    except Exception as e:
        print(f"✅ Wrong key decoding: CORRECTLY FAILED - {str(e)[:50]}...")
    
    print()

def demo_file_types():
    """Demonstrate different file type support"""
    print("📁 FILE TYPE DETECTION DEMO")  
    print("=" * 50)
    
    test_files = [
        (b"This is plain text content", "document.txt"),
        (b"%PDF-1.4\n%Sample PDF content", "document.pdf"),
        (b"MZ\x90\x00\x03Sample EXE", "program.exe"),
        (b"\xFF\xD8\xFF\xE0Sample JPEG", "image.jpg"),
        (b"Binary data \x00\x01\x02\x03", "data.bin"),
    ]
    
    for data, filename in test_files:
        detected_type = detect_file_type(data, filename)
        print(f"📄 {filename:15} → {detected_type}")
    
    print()

def demo_metadata():
    """Show metadata information"""
    print("🏷️  METADATA DEMO")
    print("=" * 50)
    
    key = "DemoKey456"
    stego = LSBSteganography(key)
    
    print(f"🔑 Key: {key}")
    metadata = stego.key_manager.get_metadata()
    
    for key_name, value in metadata.items():
        print(f"📊 {key_name}: {value}")
    
    print(f"🎲 Bit permutation: {stego.key_manager.bit_permutation}")
    print(f"📍 Sample starting position (for 1000 bytes): {stego.key_manager.get_starting_position(1000)}")
    print(f"👣 Step size: {stego.key_manager.get_step_size(1000)}")
    print()

def main():
    """Run all demos"""
    print("🎭 LSB STEGANOGRAPHY DEMONSTRATION")
    print("=" * 60)
    print("This demo shows the key features of our steganography tool")
    print()
    
    demo_text_steganography()
    demo_key_security()
    demo_file_types()
    demo_metadata()
    
    print("🎉 DEMO COMPLETE!")
    print("Run the web server with: python3 simple_server.py")
    print("Or run tests with: python3 test_steganography.py")

if __name__ == '__main__':
    main()