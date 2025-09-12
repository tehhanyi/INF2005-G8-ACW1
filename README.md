# INF2005-G8-ACW1: LSB Steganography Tool

A comprehensive Flask-based application that implements Least Significant Bit (LSB) steganography with advanced key-based bit manipulation for secure data hiding.

## Features

### 🔐 Key-Based Security
- **Custom Key Format**: User-provided keys influence the entire steganography process
- **Multi-layer Security**: Key affects starting position, bit offset, byte permutation, and traversal patterns
- **Key Validation**: Both encoding and decoding require the same key
- **Metadata Protection**: Key information is embedded for validation during decoding

### 📁 File Type Support
- **Text Files**: Plain text, markdown, CSV files
- **Images**: PNG, JPEG, GIF, BMP, TIFF formats  
- **Documents**: PDF files
- **Executables**: EXE, DLL, binary files
- **Auto-detection**: Intelligent file type detection based on content and filename

### 🧠 Advanced LSB Algorithm
- **Key-influenced starting position** in cover data
- **Configurable bit offset** for LSB selection (0-7)
- **Byte-level bit permutation** based on key hash
- **Variable step size** for data traversal
- **Unique end markers** to prevent false positives

### 🌐 Web Interface
- Modern, responsive web interface
- Drag-and-drop file uploads
- Real-time encoding/decoding
- Download links for processed files
- Support for both text input and file uploads

## Installation

### Requirements
```bash
# Install dependencies (if available)
pip install -r requirements.txt

# Or use system Python with built-in modules
python3 --version  # Requires Python 3.6+
```

### Dependencies
- **Core**: Built using Python standard library (json, hashlib, struct, io, os)
- **Optional**: Flask, Pillow, numpy (for enhanced functionality)
- **Fallback**: Custom HTTP server implementation included

## Usage

### 1. Command Line Testing
```bash
# Run comprehensive test suite
python3 test_steganography.py

# Manual encoding/decoding test
python3 test_manual.py
```

### 2. Web Interface
```bash
# Start the server
python3 simple_server.py
# or specify port
python3 -c "from simple_server import run_server; run_server(8000)"

# Open browser to http://localhost:5000
```

### 3. HTTP API

#### Encode Data
```bash
curl -X POST \
  -F "key=your_secret_key" \
  -F "cover_file=@cover.txt" \
  -F "payload_text=Secret message" \
  http://localhost:5000/encode
```

#### Decode Data  
```bash
curl -X POST \
  -F "key=your_secret_key" \
  -F "encoded_file=@encoded_file.txt" \
  http://localhost:5000/decode
```

### 4. Python API
```python
from lsb_steganography import LSBSteganography

# Initialize with key
stego = LSBSteganography("your_secret_key")

# Encode data
with open('cover.txt', 'rb') as f:
    cover_data = f.read()

payload_data = b"Secret message"
encoded_data = stego.encode(cover_data, payload_data, 'text')

# Decode data
payload_data, payload_type, metadata = stego.decode(encoded_data)
print(f"Decoded: {payload_data.decode('utf-8')}")
```

## Key Format and Security

### Key Components
The user-provided key is processed through SHA-256 hashing to generate:

1. **Position Seed** (4 bytes): Determines starting location in cover data
2. **Permutation Seed** (4 bytes): Controls bit reordering within bytes
3. **Bit Offset** (1 byte): Sets which bit position (0-7) to use for LSB
4. **Step Seed** (4 bytes): Influences traversal step size through cover data

### Security Features
- **Steganographic Invisibility**: Wrong keys produce seemingly random data
- **Key Validation**: Embedded metadata prevents decoding with incorrect keys  
- **Bit Permutation**: Bytes are permuted based on key before bit extraction
- **Variable Positioning**: Key determines both start position and step size

## File Structure

```
├── lsb_steganography.py     # Core steganography implementation
├── key_manager.py           # Key processing and metadata handling  
├── simple_server.py         # HTTP server implementation
├── app.py                   # Flask application (if Flask available)
├── templates/
│   └── index.html          # Web interface
├── test_steganography.py    # Comprehensive test suite
├── test_manual.py          # Manual testing utility
└── requirements.txt        # Python dependencies
```

## Algorithm Details

### Encoding Process
1. **Key Processing**: Generate key components from user key
2. **Metadata Creation**: Build JSON metadata with file info and key validation data
3. **Message Assembly**: Combine magic header + version + metadata + payload
4. **Bit Extraction**: Convert message to individual bits with unique end marker
5. **LSB Embedding**: Embed bits using key-influenced positions and permutations

### Decoding Process
1. **Key Processing**: Generate same key components from user key
2. **Bit Extraction**: Extract bits using matching positions and permutations
3. **End Detection**: Find unique end marker to determine message boundary
4. **Message Parsing**: Separate header, metadata, and payload
5. **Validation**: Verify key matches and extract payload

### Key Influence Points
- **Starting Position**: `position_seed % (cover_length // 2)`
- **Bit Offset**: `key_hash[8] % 8`  
- **Step Size**: `(step_seed % 5) + 1`
- **Bit Permutation**: Custom shuffle based on permutation_seed

## Testing

The included test suite validates:
- ✅ Text steganography with various message sizes
- ✅ Key validation and security  
- ✅ File type detection accuracy
- ✅ Binary data handling
- ✅ Capacity limit enforcement
- ✅ HTTP API functionality

```bash
# Run all tests
python3 test_steganography.py

# Expected output: 5/5 tests passed 🎉
```

## Security Considerations

### Strengths
- **Key-dependent extraction**: Different keys produce different data streams
- **Multi-layer obfuscation**: Position, permutation, and bit selection all vary
- **No obvious patterns**: Embedded data appears random without correct key
- **Metadata validation**: Prevents partial decoding with wrong keys

### Recommendations  
- Use strong, unique keys for each encoding session
- Keep key secret and use secure communication for key sharing
- Choose cover files much larger than payloads (recommended 10:1 ratio)
- Consider additional encryption of payload before steganography

## License

This implementation is created for educational purposes as part of INF2005 coursework.

## Authors

- **Group 8** - INF2005 Assessment Coursework 1
- Developed using advanced LSB steganography techniques with cryptographic key management
