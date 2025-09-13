from flask import Flask, request, render_template, send_from_directory, jsonify, url_for
from werkzeug.utils import secure_filename
import os

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
        payload_file = request.files['payload_file']
        key = request.form['key']
        lsb_count = int(request.form['lsb_count'])
        start_location = request.form.get('start_location', '0')
        
        # Validate inputs
        if not validate_key(key):
            return jsonify({'error': 'Invalid key format'}), 400
            
        # Save uploaded files
        cover_filename = secure_filename(cover_file.filename)
        payload_filename = secure_filename(payload_file.filename)
        
        cover_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
        payload_path = os.path.join(app.config['UPLOAD_FOLDER'], payload_filename)
        
        cover_file.save(cover_path)
        payload_file.save(payload_path)
        
        # Determine file type and call appropriate encoding function
        file_ext = cover_filename.lower().split('.')[-1]
        
        if file_ext in ['png', 'bmp', 'gif']:
            result = encode_image(cover_path, payload_path, key, lsb_count, start_location)
        elif file_ext in ['wav', 'pcm']:
            result = encode_audio(cover_path, payload_path, key, lsb_count, start_location)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        # Add download URL if stego file was generated
        if isinstance(result, dict) and result.get('stego_path'):
            stego_filename = os.path.basename(result['stego_path'])
            result['stego_url'] = url_for('download_upload_file', filename=stego_filename)

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
            payload_filename = os.path.basename(result['payload_path'])
            result['payload_url'] = url_for('download_upload_file', filename=payload_filename)

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
        
        # Calculate capacity based on file type
        file_ext = cover_file.filename.lower().split('.')[-1]
        
        if file_ext in ['png', 'bmp', 'gif']:
            capacity = calculate_image_capacity(cover_file, lsb_count)
        elif file_ext in ['wav', 'pcm']:
            capacity = calculate_audio_capacity(cover_file, lsb_count)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
            
        return jsonify({'capacity_bytes': capacity})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
