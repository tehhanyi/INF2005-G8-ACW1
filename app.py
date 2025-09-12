from flask import Flask, request, render_template, jsonify, send_file, flash, redirect, url_for
import os
import io
import tempfile
from werkzeug.utils import secure_filename
from lsb_steganography import LSBSteganography, detect_file_type
import traceback

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'exe', 'bin', 'dll', 'md', 'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode_data():
    try:
        # Get the key
        key = request.form.get('key')
        if not key:
            return jsonify({'error': 'Key is required'}), 400
        
        # Get cover file
        cover_file = request.files.get('cover_file')
        if not cover_file or cover_file.filename == '':
            return jsonify({'error': 'Cover file is required'}), 400
        
        # Get payload data
        payload_text = request.form.get('payload_text', '').strip()
        payload_file = request.files.get('payload_file')
        
        if not payload_text and (not payload_file or payload_file.filename == ''):
            return jsonify({'error': 'Either payload text or payload file is required'}), 400
        
        # Read cover data
        cover_data = cover_file.read()
        if len(cover_data) == 0:
            return jsonify({'error': 'Cover file is empty'}), 400
        
        # Prepare payload data
        if payload_text:
            payload_data = payload_text.encode('utf-8')
            payload_type = 'text'
            payload_filename = 'text_payload.txt'
        else:
            payload_data = payload_file.read()
            payload_type = detect_file_type(payload_data, payload_file.filename)
            payload_filename = secure_filename(payload_file.filename)
        
        # Initialize steganography
        stego = LSBSteganography(key)
        
        # Encode the data
        encoded_data = stego.encode(cover_data, payload_data, payload_type)
        
        # Generate output filename
        cover_filename = secure_filename(cover_file.filename)
        name, ext = os.path.splitext(cover_filename)
        output_filename = f"{name}_encoded{ext}"
        
        # Save encoded file
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        with open(output_path, 'wb') as f:
            f.write(encoded_data)
        
        return jsonify({
            'success': True,
            'message': f'Data successfully encoded into {cover_filename}',
            'download_url': f'/download/{output_filename}',
            'payload_type': payload_type,
            'payload_size': len(payload_data),
            'cover_size': len(cover_data),
            'encoded_size': len(encoded_data)
        })
        
    except Exception as e:
        app.logger.error(f"Encoding error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Encoding failed: {str(e)}'}), 500

@app.route('/decode', methods=['POST'])
def decode_data():
    try:
        # Get the key
        key = request.form.get('key')
        if not key:
            return jsonify({'error': 'Key is required for decoding'}), 400
        
        # Get encoded file
        encoded_file = request.files.get('encoded_file')
        if not encoded_file or encoded_file.filename == '':
            return jsonify({'error': 'Encoded file is required'}), 400
        
        # Read encoded data
        encoded_data = encoded_file.read()
        if len(encoded_data) == 0:
            return jsonify({'error': 'Encoded file is empty'}), 400
        
        # Initialize steganography with the key
        stego = LSBSteganography(key)
        
        # Decode the data
        payload_data, payload_type, metadata = stego.decode(encoded_data)
        
        # Generate output filename based on payload type
        if payload_type == 'text':
            output_filename = 'decoded_text.txt'
        elif payload_type == 'image':
            output_filename = 'decoded_image.png'
        elif payload_type == 'pdf':
            output_filename = 'decoded_document.pdf'
        elif payload_type == 'exe':
            output_filename = 'decoded_executable.exe'
        else:
            output_filename = 'decoded_file.bin'
        
        # Save decoded file
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        with open(output_path, 'wb') as f:
            f.write(payload_data)
        
        # If it's text, also return the text content
        text_content = None
        if payload_type == 'text':
            try:
                text_content = payload_data.decode('utf-8')
            except:
                text_content = "Could not decode as UTF-8 text"
        
        return jsonify({
            'success': True,
            'message': f'Data successfully decoded from {encoded_file.filename}',
            'download_url': f'/download/{output_filename}',
            'payload_type': payload_type,
            'payload_size': len(payload_data),
            'metadata': metadata,
            'text_content': text_content
        })
        
    except Exception as e:
        app.logger.error(f"Decoding error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Decoding failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=safe_filename)
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'LSB Steganography API is running'})

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)