from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os

# Import your custom modules using absolute imports
from modules.image_stego import encode_image, decode_image, calculate_image_capacity
from modules.audio_stego import encode_audio, decode_audio, calculate_audio_capacity
from modules.key_manager import validate_key, generate_lsb_positions
from modules.utils import validate_file_size, get_file_info

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
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
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/decode', methods=['POST'])
def decode():
    try:
        stego_file = request.files['stego_file']
        key = request.form['key']
        lsb_count = int(request.form['lsb_count'])
        
        # Validate and process similar to encode
        # Call appropriate decode function based on file type
        
        return jsonify({'success': 'File decoded successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
