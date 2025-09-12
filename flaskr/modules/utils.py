import os
import struct
import hashlib
from PIL import Image
import wave

def bytes_to_bits(data):
    """
    Convert bytes to a list of bit strings
    
    Args:
        data (bytes): Input byte data
        
    Returns:
        list: List of bit strings ('0' or '1')
    """
    bits = []
    for byte in data:
        # Convert each byte to 8-bit binary string and split into individual bits
        byte_bits = format(byte, '08b')
        bits.extend(list(byte_bits))
    return bits

def bits_to_bytes(bits):
    """
    Convert list of bit strings back to bytes
    
    Args:
        bits (list): List of bit strings ('0' or '1')
        
    Returns:
        bytes: Reconstructed byte data
    """
    # Pad bits to make length divisible by 8
    while len(bits) % 8 != 0:
        bits.append('0')
    
    byte_data = bytearray()
    # Process 8 bits at a time to form bytes
    for i in range(0, len(bits), 8):
        byte_bits = ''.join(bits[i:i+8])
        byte_value = int(byte_bits, 2)
        byte_data.append(byte_value)
    
    return bytes(byte_data)

def string_to_bits(text):
    """
    Convert string to bits using UTF-8 encoding
    
    Args:
        text (str): Input text string
        
    Returns:
        list: List of bit strings
    """
    return bytes_to_bits(text.encode('utf-8'))

def bits_to_string(bits):
    """
    Convert bits back to string using UTF-8 decoding
    
    Args:
        bits (list): List of bit strings
        
    Returns:
        str: Decoded string
    """
    try:
        byte_data = bits_to_bytes(bits)
        return byte_data.decode('utf-8', errors='ignore')
    except:
        return ""

def calculate_file_size(file_path):
    """
    Get file size in bytes
    
    Args:
        file_path (str): Path to file
        
    Returns:
        int: File size in bytes, 0 if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def validate_file_exists(file_path):
    """
    Validate if file exists and is readable
    
    Args:
        file_path (str): Path to file
        
    Returns:
        dict: Validation result with success status and error message
    """
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'File does not exist'}
    
    if not os.path.isfile(file_path):
        return {'valid': False, 'error': 'Path is not a file'}
    
    if not os.access(file_path, os.R_OK):
        return {'valid': False, 'error': 'File is not readable'}
    
    return {'valid': True}

def validate_image_file(file_path):
    """
    Validate image file format and get basic info
    
    Args:
        file_path (str): Path to image file
        
    Returns:
        dict: Validation result with image properties
    """

def validate_file_size(file_path, max_size_mb=5):
    """
    Validate file size against maximum allowed size
    
    Args:
        file_path (str): Path to file
        max_size_mb (int): Maximum allowed size in megabytes
        
    Returns:
        dict: Validation result with success status and error message
    """
    size_bytes = calculate_file_size(file_path)
    if size_bytes == 0:
        return {'valid': False, 'error': 'File does not exist or is empty'}
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        return {'valid': False, 'error': f'File exceeds maximum size of {max_size_mb} MB'}
    
    return {'valid': True}

def get_file_info(file_path):
    """
    Get basic file information
    
    Args:
        file_path (str): Path to file
        
    Returns:
        dict: File information including name, size, and type
    """
    if not os.path.exists(file_path):
        return {'error': 'File does not exist'}
    
    file_info = {}
    file_info['name'] = os.path.basename(file_path)
    file_info['size_bytes'] = calculate_file_size(file_path)
    file_info['extension'] = os.path.splitext(file_path)[1].lower()
    
    return file_info