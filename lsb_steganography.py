import io
import json
import struct
from typing import Union, Tuple, BinaryIO
from key_manager import KeyManager

class LSBSteganography:
    """
    LSB Steganography implementation with key-based bit manipulation.
    Supports text, images, and binary files as cover media.
    """
    
    MAGIC_HEADER = b'LSBS'  # LSB Steganography header
    VERSION = 1
    
    def __init__(self, key: str):
        """
        Initialize steganography engine with user key.
        
        Args:
            key: User-provided key for encoding/decoding
        """
        self.key_manager = KeyManager(key)
    
    def encode(self, cover_data: bytes, payload_data: bytes, 
               payload_type: str = 'text') -> bytes:
        """
        Encode payload data into cover data using LSB steganography.
        
        Args:
            cover_data: Cover medium (image, text, or binary data)
            payload_data: Data to hide
            payload_type: Type of payload ('text', 'image', 'pdf', 'exe', 'other')
            
        Returns:
            Encoded data with hidden payload
        """
        if len(cover_data) * 8 < len(payload_data) * 8 + 1024:  # Need space for metadata
            raise ValueError("Cover data too small for payload")
        
        # Create metadata
        metadata = {
            'version': self.VERSION,
            'payload_type': payload_type,
            'payload_size': len(payload_data),
            'key_info': self.key_manager.get_metadata()
        }
        
        # Serialize metadata and combine with payload
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        metadata_size = len(metadata_bytes)
        
        # Create complete message: MAGIC + VERSION + METADATA_SIZE + METADATA + PAYLOAD
        message = (self.MAGIC_HEADER + 
                  struct.pack('>B', self.VERSION) +
                  struct.pack('>H', metadata_size) +
                  metadata_bytes + 
                  payload_data)
        
        # Encode message into cover data
        return self._encode_message(cover_data, message)
    
    def decode(self, encoded_data: bytes) -> Tuple[bytes, str, dict]:
        """
        Decode hidden payload from encoded data.
        
        Args:
            encoded_data: Data containing hidden payload
            
        Returns:
            Tuple of (payload_data, payload_type, metadata)
        """
        # Extract message from cover data
        message = self._decode_message(encoded_data)
        
        # Parse message structure
        if len(message) < 7 or message[:4] != self.MAGIC_HEADER:
            raise ValueError("Invalid or corrupted steganography data")
        
        version = struct.unpack('>B', message[4:5])[0]
        if version != self.VERSION:
            raise ValueError(f"Unsupported version: {version}")
        
        metadata_size = struct.unpack('>H', message[5:7])[0]
        if len(message) < 7 + metadata_size:
            raise ValueError("Corrupted metadata")
        
        # Extract and parse metadata
        metadata_bytes = message[7:7 + metadata_size]
        try:
            metadata = json.loads(metadata_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Invalid metadata format")
        
        # Validate key
        if not self.key_manager.validate_key(metadata.get('key_info', {})):
            raise ValueError("Invalid key - cannot decode with this key")
        
        # Extract payload
        payload_start = 7 + metadata_size
        expected_payload_size = metadata.get('payload_size', 0)
        payload_data = message[payload_start:payload_start + expected_payload_size]
        
        if len(payload_data) != expected_payload_size:
            raise ValueError("Payload size mismatch")
        
        return payload_data, metadata.get('payload_type', 'unknown'), metadata
    
    def _encode_message(self, cover_data: bytes, message: bytes) -> bytes:
        """Encode message bits into cover data using key-based LSB."""
        cover_array = bytearray(cover_data)
        message_bits = self._bytes_to_bits(message)
        
        # Add end marker (8 bits of alternating pattern)
        message_bits.extend([1, 0, 1, 0, 1, 0, 1, 0])
        
        # Get key-based parameters
        start_pos = self.key_manager.get_starting_position(len(cover_array))
        step_size = self.key_manager.get_step_size(len(cover_array))
        bit_offset = self.key_manager.bit_offset
        
        # Check if we have enough capacity (simple check - each bit needs one byte)
        if len(message_bits) > len(cover_array):
            raise ValueError("Cover data too small for message")
        
        # Simple sequential encoding with key-based starting position and bit offset
        for i, bit in enumerate(message_bits):
            if i >= len(cover_array):
                raise ValueError("Cover data too small for message")
                
            pos = (start_pos + i) % len(cover_array)
            target_bit = bit_offset % 8
            
            # Clear and set the target bit
            cover_array[pos] = (cover_array[pos] & ~(1 << target_bit)) | (bit << target_bit)
        
        return bytes(cover_array)
    
    def _decode_message(self, encoded_data: bytes) -> bytes:
        """Decode message bits from encoded data using key-based LSB."""
        # Get key-based parameters
        start_pos = self.key_manager.get_starting_position(len(encoded_data))
        bit_offset = self.key_manager.bit_offset
        
        message_bits = []
        end_pattern = [1, 0, 1, 0, 1, 0, 1, 0]
        target_bit = bit_offset % 8
        
        # Extract bits using the same pattern as encoding
        for i in range(len(encoded_data)):
            pos = (start_pos + i) % len(encoded_data)
            
            # Extract bit from the target position
            bit = (encoded_data[pos] >> target_bit) & 1
            message_bits.append(bit)
            
            # Check for end pattern
            if len(message_bits) >= 8 and message_bits[-8:] == end_pattern:
                message_bits = message_bits[:-8]  # Remove end pattern
                break
        
        # Convert bits back to bytes
        return self._bits_to_bytes(message_bits)
    
    def _bytes_to_bits(self, data: bytes) -> list:
        """Convert bytes to list of bits."""
        bits = []
        for byte in data:
            for i in range(8):
                bits.append((byte >> i) & 1)
        return bits
    
    def _bits_to_bytes(self, bits: list) -> bytes:
        """Convert list of bits to bytes."""
        # Pad to multiple of 8
        while len(bits) % 8 != 0:
            bits.append(0)
        
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_value = 0
            for j in range(8):
                if i + j < len(bits) and bits[i + j]:
                    byte_value |= (1 << j)
            result.append(byte_value)
        
        return bytes(result)

def is_image_file(data: bytes) -> bool:
    """Check if data represents a valid image file based on magic bytes."""
    # Common image file signatures
    image_signatures = [
        b'\xFF\xD8\xFF',        # JPEG
        b'\x89PNG\r\n\x1a\n',   # PNG
        b'GIF87a',              # GIF 87a
        b'GIF89a',              # GIF 89a
        b'BM',                  # BMP
        b'II*\x00',             # TIFF (little endian)
        b'MM\x00*',             # TIFF (big endian)
    ]
    
    for sig in image_signatures:
        if data.startswith(sig):
            return True
    return False

def detect_file_type(data: bytes, filename: str = None) -> str:
    """Detect file type from data and filename."""
    # Prioritize filename extension if available
    if filename:
        filename = filename.lower()
        if filename.endswith(('.txt', '.md', '.csv')):
            return 'text'
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
            return 'image'
        elif filename.endswith(('.pdf',)):
            return 'pdf'
        elif filename.endswith(('.exe', '.dll')):
            return 'exe'
        elif filename.endswith(('.bin',)):
            # .bin files are ambiguous - check content first
            pass
    
    # Check magic bytes for common formats
    if data.startswith(b'%PDF'):
        return 'pdf'
    elif data.startswith(b'MZ'):  # Windows executable
        return 'exe'
    elif is_image_file(data):
        return 'image'
    else:
        # Try to decode as text
        try:
            # Check if it's mostly printable ASCII/UTF-8 text
            decoded = data.decode('utf-8')
            # Count printable characters
            printable_chars = sum(1 for c in decoded if c.isprintable() or c.isspace())
            if printable_chars >= len(decoded) * 0.8:  # At least 80% printable
                return 'text'
        except:
            pass
        
        return 'other'