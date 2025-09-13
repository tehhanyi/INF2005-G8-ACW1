from flask import Flask, request, render_template, send_from_directory, jsonify, url_for
from werkzeug.utils import secure_filename
import os
import uuid
import shutil
import uuid

# Import your custom modules using absolute imports
from modules.image_stego import encode_image, decode_image, calculate_image_capacity
from modules.audio_stego import encode_audio, decode_audio, calculate_audio_capacity
#from modules.key_manager import validate_key, generate_lsb_positions
from modules.key_manager import validate_key
from modules.utils import validate_file_size, get_file_info

app = Flask(__name__)
app.config['UPLOAD_FOLDER']   = os.path.join(app.root_path, 'uploads')
app.config['DOWNLOAD_FOLDER'] = os.path.join(app.root_path, 'downloads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode():
    try:
        # Get form data
        cover_file = request.files['cover_file']
        payload_file = request.files.get('payload_file')
        payload_text = request.form.get('payload_text', '')
        key = request.form['key']
        lsb_count = int(request.form['lsb_count'])
        start_location = request.form.get('start_location', '0')
        
        # Validate inputs
        if not validate_key(key):
            return jsonify({'error': 'Invalid key format'}), 400
            
        # Save uploaded files
        cover_filename = secure_filename(cover_file.filename)
        cover_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
        cover_file.save(cover_path)

        # Determine payload source (file or inline text)
        if payload_file and getattr(payload_file, 'filename', ''):
            payload_filename = secure_filename(payload_file.filename)
            payload_path = os.path.join(app.config['UPLOAD_FOLDER'], payload_filename)
            payload_file.save(payload_path)
        elif payload_text:
            payload_filename = f"payload_text_{uuid.uuid4().hex}.txt"
            payload_path = os.path.join(app.config['UPLOAD_FOLDER'], payload_filename)
            with open(payload_path, 'w', encoding='utf-8') as f:
                f.write(payload_text)
        else:
            return jsonify({'error': 'No payload provided. Upload a file or enter text.'}), 400
        
        # Determine file type and call appropriate encoding function
        file_ext = cover_filename.lower().split('.')[-1]
        
        if file_ext in ['png', 'bmp', 'gif']:
            result = encode_image(cover_path, payload_path, key, lsb_count, start_location)
        elif file_ext in ['wav', 'pcm']:
            result = encode_audio(cover_path, payload_path, key, lsb_count, start_location)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        # Move stego output into downloads and add download URL
        if isinstance(result, dict) and result.get('stego_path'):
            src_path = result['stego_path']
            stego_filename = os.path.basename(src_path)
            dst_path = os.path.join(app.config['DOWNLOAD_FOLDER'], stego_filename)
            try:
                if os.path.abspath(src_path) != os.path.abspath(dst_path):
                    shutil.move(src_path, dst_path)
                result['stego_path'] = dst_path
            except Exception:
                # If move fails, keep original path
                dst_path = src_path
            result['stego_url'] = url_for('download_download_file', filename=os.path.basename(dst_path))

        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/decode', methods=['POST'])
def decode():
    try:
        stego_file = request.files['stego_file']
        key = request.form['key']
        lsb_count = int(request.form['lsb_count'])
        start_location = int(request.form.get('start_location', '0'))

        if not validate_key(key):
            return jsonify({'error': 'Invalid key format'}), 400

        # Save the uploaded stego file
        stego_filename = secure_filename(stego_file.filename)
        stego_path = os.path.join(app.config['UPLOAD_FOLDER'], stego_filename)
        stego_file.save(stego_path)

        # Determine file type and call appropriate decoding function
        file_ext = stego_filename.lower().split('.')[-1]

        if file_ext in ['png', 'bmp', 'gif']:
            result = decode_image(stego_path, key, lsb_count, start_location)
        elif file_ext in ['wav']:
            result = decode_audio(stego_path, key, lsb_count, start_location)
        elif file_ext in ['pcm']:
            return jsonify({'error': 'Raw PCM decode not supported yet'}), 501
        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        # Add download URL for extracted payload
        if isinstance(result, dict) and result.get('payload_path'):
            src_path = result['payload_path']
            payload_filename = os.path.basename(src_path)
            dst_path = os.path.join(app.config['DOWNLOAD_FOLDER'], payload_filename)
            try:
                if os.path.abspath(src_path) != os.path.abspath(dst_path):
                    shutil.move(src_path, dst_path)
                result['payload_path'] = dst_path
            except Exception:
                dst_path = src_path
            result['payload_url'] = url_for('download_download_file', filename=os.path.basename(dst_path))

        return jsonify(result)
    except Exception as e:
        # Provide clearer 400s for common decode errors (e.g., wrong key/lsb/start)
        if isinstance(e, ValueError):
            return jsonify({'error': str(e)}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/download/uploads/<path:filename>')
def download_upload_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/download/downloads/<path:filename>')
def download_download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/calculate_capacity', methods=['POST'])
def calculate_capacity():
    try:
        cover_file = request.files['cover_file']
        lsb_count = int(request.form['lsb_count'])
        start_location = int(request.form.get('start_location', '0')) if 'start_location' in request.form else 0
        
        # Calculate capacity based on file type
        file_ext = cover_file.filename.lower().split('.')[-1]
        
        if file_ext in ['png', 'bmp', 'gif']:
            total_bytes = calculate_image_capacity(cover_file, lsb_count)
        elif file_ext in ['wav', 'pcm']:
            total_bytes = calculate_audio_capacity(cover_file, lsb_count)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        # Adjust for start_location in bit slots
        total_bits = max(0, int(total_bytes) * 8)
        adjusted_bits = max(0, total_bits - max(0, int(start_location)))
        capacity = adjusted_bits // 8
        return jsonify({'capacity_bytes': capacity, 'start_location': start_location})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
