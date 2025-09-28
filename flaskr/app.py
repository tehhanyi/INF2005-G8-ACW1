from flask import Flask, request, render_template, send_from_directory, jsonify, url_for
from werkzeug.utils import secure_filename
import os
import uuid
import shutil
import uuid
import numpy as np
from PIL import Image, ImageOps
import wave

# Import your custom modules using absolute imports
from modules.image_stego import encode_image, decode_image, parse_start_location
from modules.audio_stego import encode_audio, decode_audio, _coerce_start_seconds, _seconds_to_bit_offset
#from modules.key_manager import validate_key, generate_lsb_positions
from modules.key_manager import validate_key, extract_image_start_from_key, extract_audio_start_from_key
from modules.utils import validate_file_size, get_file_info
from modules.visualization import (
    generate_difference_map, 
    create_histogram_analysis,
    calculate_capacity_info,
    analyze_stego_detection,
    create_waveform_comparison,
    extract_bit_planes,
    analyze_complexity_segments
)

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
        start_location_raw = request.form.get('start_location', '0')
        start_location = start_location_raw.strip() if isinstance(start_location_raw, str) else str(start_location_raw)
        if start_location == '':
            start_location = '0'
        
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
        
        if file_ext in ['png', 'bmp', 'gif', 'jpg', 'jpeg']:
            # If key encodes a start (KEY@x,y) and no explicit image start was provided, use it.
            try:
                with Image.open(cover_path) as tmp:
                    w, h = tmp.size
            except Exception:
                w = h = None
            key_main, key_start = extract_image_start_from_key(key, w or 0, h or 0)
            if (not start_location or start_location.strip() in ('0', '0,0')) and key_start:
                start_location = key_start
            key = key_main
            result = encode_image(cover_path, payload_path, key, lsb_count, start_location)
        elif file_ext in ['wav', 'pcm']:
            try:
                audio_start = int(float(start_location))
            except Exception:
                return jsonify({'error': 'Start location must be a whole number for audio files.'}), 400
            if audio_start < 0:
                audio_start = 0
            # If key encodes a start (KEY@N) and no explicit start provided, use it.
            key_main, key_start = extract_audio_start_from_key(key)
            if (start_location.strip() == '0' or start_location.strip() == '') and key_start is not None:
                audio_start = int(key_start)
            key = key_main
            result = encode_audio(cover_path, payload_path, key, lsb_count, audio_start)
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

@app.route('/visualize', methods=['GET'])
def visualize():
    """Render the visualization/analysis page"""
    return render_template('visualize.html')

# NEW: Comprehensive comparison route for visualization tab
@app.route('/analyze/comprehensive_comparison', methods=['POST'])
def comprehensive_comparison():
    """Comprehensive side-by-side analysis of cover vs stego files"""
    try:
        cover_file = request.files.get('cover_file')
        stego_file = request.files.get('stego_file')
        
        if not cover_file and not stego_file:
            return jsonify({'error': 'At least one file must be provided'}), 400
            
        results = {
            'analysis_type': None,
            'cover_analysis': {},
            'stego_analysis': {},
            'comparison_analysis': {}
        }
        
        # Save files and determine type
        cover_path = None
        stego_path = None
        file_type = None
        
        if cover_file:
            cover_filename = secure_filename(cover_file.filename)
            cover_path = os.path.join(app.config['UPLOAD_FOLDER'], f"viz_cover_{uuid.uuid4().hex}_{cover_filename}")
            cover_file.save(cover_path)
            file_type = cover_filename.lower().split('.')[-1]
            
        if stego_file:
            stego_filename = secure_filename(stego_file.filename)
            stego_path = os.path.join(app.config['UPLOAD_FOLDER'], f"viz_stego_{uuid.uuid4().hex}_{stego_filename}")
            stego_file.save(stego_path)
            if not file_type:
                file_type = stego_filename.lower().split('.')[-1]
        
        # Determine analysis type
        if file_type in ['png', 'bmp', 'gif', 'jpg', 'jpeg']:
            results['analysis_type'] = 'image'
            
            # Individual file analyses
            if cover_path:
                results['cover_analysis'] = {
                    'histogram': create_histogram_analysis(cover_path),
                    'bit_planes': extract_bit_planes(cover_path),
                    'steganalysis': analyze_stego_detection(cover_path, file_type),
                    'filename': cover_filename if cover_file else None
                }
                
            if stego_path:
                results['stego_analysis'] = {
                    'histogram': create_histogram_analysis(stego_path),
                    'bit_planes': extract_bit_planes(stego_path),
                    'steganalysis': analyze_stego_detection(stego_path, file_type),
                    'filename': stego_filename if stego_file else None
                }
            
            # Comparison analyses (require both files)
            if cover_path and stego_path:
                results['comparison_analysis'] = {
                    'difference_map': generate_difference_map(cover_path, stego_path),
                    'histogram_comparison': create_histogram_analysis(cover_path, stego_path=stego_path)
                }
                
        elif file_type in ['wav', 'mp3', 'pcm']:
            results['analysis_type'] = 'audio'
            
            # Individual file analyses
            if cover_path:
                results['cover_analysis'] = {
                    'steganalysis': analyze_stego_detection(cover_path, file_type),
                    'filename': cover_filename if cover_file else None
                }
                
            if stego_path:
                results['stego_analysis'] = {
                    'steganalysis': analyze_stego_detection(stego_path, file_type),
                    'filename': stego_filename if stego_file else None
                }
            
            # Audio comparison
            if cover_path and stego_path:
                results['comparison_analysis'] = {
                    'waveform_comparison': create_waveform_comparison(cover_path, stego_path)
                }
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Convert numpy types for JSON serialization
        results = convert_numpy_types(results)
        
        return jsonify({
            'success': True,
            'visualization_results': results,
            'message': f'Comprehensive {results["analysis_type"]} analysis completed'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
    
# @app.route('/analyze/difference_map', methods=['POST'])
# def difference_map():
#     """Generate visual difference map between cover and stego images"""
#     try:
#         cover_file = request.files['cover_file']
#         stego_file = request.files['stego_file']
        
#         # Save uploaded files
#         cover_filename = secure_filename(cover_file.filename)
#         cover_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cover_{uuid.uuid4().hex}_{cover_filename}")
#         cover_file.save(cover_path)
        
#         stego_filename = secure_filename(stego_file.filename)
#         stego_path = os.path.join(app.config['UPLOAD_FOLDER'], f"stego_{uuid.uuid4().hex}_{stego_filename}")
#         stego_file.save(stego_path)
        
#         # Generate difference map visualization
#         difference_img = generate_difference_map(cover_path, stego_path)
        
#         if difference_img:
#             return jsonify({
#                 'success': True,
#                 'difference_map': difference_img,
#                 'message': 'Difference map generated successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to generate difference map'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/histogram', methods=['POST']) 
# def histogram_analysis():
#     """Create multi-channel histogram analysis"""
#     try:
#         cover_file = request.files['cover_file']
#         stego_file = request.files.get('stego_file')  # Optional
        
#         # Save cover file
#         cover_filename = secure_filename(cover_file.filename)
#         cover_path = os.path.join(app.config['UPLOAD_FOLDER'], f"hist_cover_{uuid.uuid4().hex}_{cover_filename}")
#         cover_file.save(cover_path)
        
#         stego_path = None
#         if stego_file:
#             stego_filename = secure_filename(stego_file.filename)
#             stego_path = os.path.join(app.config['UPLOAD_FOLDER'], f"hist_stego_{uuid.uuid4().hex}_{stego_filename}")
#             stego_file.save(stego_path)
        
#         # Generate histogram analysis
#         histogram_img = create_histogram_analysis(cover_path, stego_path=stego_path)
        
#         if histogram_img:
#             return jsonify({
#                 'success': True,
#                 'histogram_analysis': histogram_img,
#                 'message': 'Histogram analysis completed successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to generate histogram analysis'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/bit_planes', methods=['POST'])
# def bit_plane_analysis():
#     """Extract and display all 8 bit planes"""
#     try:
#         image_file = request.files['image_file']
        
#         # Save uploaded file
#         filename = secure_filename(image_file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"bitplane_{uuid.uuid4().hex}_{filename}")
#         image_file.save(file_path)
        
#         # Extract bit planes
#         bit_planes_img = extract_bit_planes(file_path)
        
#         if bit_planes_img:
#             return jsonify({
#                 'success': True,
#                 'bit_planes': bit_planes_img,
#                 'message': 'Bit plane extraction completed successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to extract bit planes'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/complexity', methods=['POST'])
# def complexity_analysis():
#     """Perform BPCS complexity analysis"""
#     try:
#         image_file = request.files['image_file']
#         threshold = float(request.form.get('threshold', 0.3))
#         block_size = int(request.form.get('block_size', 8))
        
#         # Save uploaded file
#         filename = secure_filename(image_file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"complex_{uuid.uuid4().hex}_{filename}")
#         image_file.save(file_path)
        
#         # Analyze complexity
#         complexity_results = analyze_complexity_segments(file_path, block_size, threshold)
        
#         if complexity_results:
#             return jsonify({
#                 'success': True,
#                 'complexity_analysis': complexity_results,
#                 'message': 'Complexity analysis completed successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to analyze complexity'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/capacity', methods=['POST'])
# def capacity_analysis():
#     """Calculate detailed capacity information"""
#     try:
#         file = request.files['file']
#         lsb_count = int(request.form.get('lsb_count', 1))
        
#         # Save uploaded file
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"capacity_{uuid.uuid4().hex}_{filename}")
#         file.save(file_path)
        
#         # Determine file type
#         file_ext = filename.lower().split('.')[-1]
        
#         # Calculate capacity using visualization module
#         capacity_info = calculate_capacity_info(file_path, file_ext, lsb_count)
        
#         if capacity_info:
#             return jsonify({
#                 'success': True,
#                 'capacity_info': capacity_info,
#                 'message': 'Capacity analysis completed successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to calculate capacity'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/steganalysis', methods=['POST'])
# def steganalysis_detection():
#     """Perform comprehensive steganalysis detection"""
#     try:
#         file = request.files['file']
        
#         # Save uploaded file
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"steg_{uuid.uuid4().hex}_{filename}")
#         file.save(file_path)
        
#         # Determine file type
#         file_ext = filename.lower().split('.')[-1]
        
#         # Perform steganalysis
#         analysis_results = analyze_stego_detection(file_path, file_ext)
        
#         if analysis_results:
#             return jsonify({
#                 'success': True,
#                 'steganalysis_results': analysis_results,
#                 'message': 'Steganalysis detection completed successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to perform steganalysis'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/audio_comparison', methods=['POST'])
# def audio_waveform_analysis():
#     """Compare audio waveforms before and after embedding"""
#     try:
#         cover_audio = request.files['cover_audio']
#         stego_audio = request.files['stego_audio']
        
#         # Save uploaded files
#         cover_filename = secure_filename(cover_audio.filename)
#         cover_path = os.path.join(app.config['UPLOAD_FOLDER'], f"audio_cover_{uuid.uuid4().hex}_{cover_filename}")
#         cover_audio.save(cover_path)
        
#         stego_filename = secure_filename(stego_audio.filename)
#         stego_path = os.path.join(app.config['UPLOAD_FOLDER'], f"audio_stego_{uuid.uuid4().hex}_{stego_filename}")
#         stego_audio.save(stego_path)
        
#         # Generate waveform comparison
#         waveform_img = create_waveform_comparison(cover_path, stego_path)
        
#         if waveform_img:
#             return jsonify({
#                 'success': True,
#                 'waveform_comparison': waveform_img,
#                 'message': 'Audio waveform comparison completed successfully'
#             })
#         else:
#             return jsonify({'error': 'Failed to generate waveform comparison'}), 500
            
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/analyze/comprehensive', methods=['POST'])
# def comprehensive_analysis():
#     """Perform comprehensive analysis with all available tools"""
#     try:
#         cover_file = request.files['cover_file']
#         stego_file = request.files.get('stego_file')
#         analysis_type = request.form.get('analysis_type', 'image')
        
#         # Save cover file
#         cover_filename = secure_filename(cover_file.filename)
#         cover_path = os.path.join(app.config['UPLOAD_FOLDER'], f"comp_cover_{uuid.uuid4().hex}_{cover_filename}")
#         cover_file.save(cover_path)
        
#         stego_path = None
#         if stego_file:
#             stego_filename = secure_filename(stego_file.filename)
#             stego_path = os.path.join(app.config['UPLOAD_FOLDER'], f"comp_stego_{uuid.uuid4().hex}_{stego_filename}")
#             stego_file.save(stego_path)
        
#         # Perform comprehensive analysis
#         results = {}
        
#         if analysis_type == 'image':
#             # Image-specific analyses
#             results['histogram_analysis'] = create_histogram_analysis(cover_path, stego_path=stego_path)
#             results['bit_planes'] = extract_bit_planes(cover_path)
#             results['capacity_info'] = calculate_capacity_info(cover_path, 'png')
#             results['steganalysis'] = analyze_stego_detection(cover_path, 'png')
#             results['complexity_analysis'] = analyze_complexity_segments(cover_path)
            
#             if stego_path:
#                 results['difference_map'] = generate_difference_map(cover_path, stego_path)
                
#         elif analysis_type == 'audio':
#             # Audio-specific analyses
#             results['capacity_info'] = calculate_capacity_info(cover_path, 'wav')
#             results['steganalysis'] = analyze_stego_detection(cover_path, 'wav')
            
#             if stego_path:
#                 results['waveform_comparison'] = create_waveform_comparison(cover_path, stego_path)
        
#         return jsonify({
#             'success': True,
#             'comprehensive_results': results,
#             'message': 'Comprehensive analysis completed successfully'
#         })
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    
@app.route('/decode', methods=['POST'])
def decode():
    try:
        stego_file = request.files['stego_file']
        key = request.form['key']
        lsb_count = int(request.form['lsb_count'])
        start_raw = request.form.get('start_location', '0')
        start_location = start_raw.strip() if isinstance(start_raw, str) else str(start_raw)
        if start_location == '':
            start_location = '0'

        if not validate_key(key):
            return jsonify({'error': 'Invalid key format'}), 400

        # Save the uploaded stego file
        stego_filename = secure_filename(stego_file.filename)
        stego_path = os.path.join(app.config['UPLOAD_FOLDER'], stego_filename)
        stego_file.save(stego_path)

        # Determine file type and call appropriate decoding function
        file_ext = stego_filename.lower().split('.')[-1]

        if file_ext in ['png', 'bmp', 'gif', 'jpg', 'jpeg']:
            try:
                with Image.open(stego_path) as tmp:
                    w, h = tmp.size
            except Exception:
                w = h = None
            key_main, key_start = extract_image_start_from_key(key, w or 0, h or 0)
            if (not start_location or start_location.strip() in ('', '0', '0,0')) and key_start:
                start_location = key_start
            key = key_main
            result = decode_image(stego_path, key, lsb_count, start_location)
        elif file_ext in ['wav']:
            try:
                key_main, key_start = extract_audio_start_from_key(key)
                if (not start_location or start_location.strip() == '0') and key_start is not None:
                    start_location = str(int(key_start))
                audio_start = int(float(start_location))
            except Exception:
                return jsonify({'error': 'Start location must be a whole number for audio files.'}), 400
            if audio_start < 0:
                audio_start = 0
            result = decode_audio(stego_path, key_main if 'key_main' in locals() else key, lsb_count, audio_start)
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
        start_raw = request.form.get('start_location', '0,0')
        start_input = start_raw.strip() if isinstance(start_raw, str) else str(start_raw)
        if start_input == '':
            start_input = '0,0'

        file_ext = cover_file.filename.lower().split('.')[-1]
        image_exts = ['png', 'bmp', 'gif', 'jpg', 'jpeg']

        if file_ext in image_exts:
            try:
                # Ensure stream is at beginning for PIL
                try:
                    cover_file.stream.seek(0)
                except Exception:
                    pass
                with Image.open(cover_file) as img:
                    img2 = ImageOps.exif_transpose(img)
                    w, h = img2.size
                total_carriers = w * h * 3
                try:
                    start_offset = parse_start_location(start_input, w, h)
                except ValueError:
                    return jsonify({'error': "Invalid start location format. Use 'x,y' for images."}), 400
                start_offset = max(0, min(total_carriers, start_offset))
                remaining_carriers = max(0, total_carriers - start_offset)
                capacity = (remaining_carriers * lsb_count) // 8
            finally:
                try:
                    cover_file.stream.seek(0)
                except Exception:
                    pass
            return jsonify({
                'capacity_bytes': capacity,
                'start_location': start_input,
                'start_offset_bytes': start_offset,
                'dimensions': f'{w}x{h}'
            })
        elif file_ext in ['wav', 'pcm']:
            try:
                stream = getattr(cover_file, 'stream', None)
                pos = None
                if stream is not None:
                    try:
                        pos = stream.tell()
                    except Exception:
                        pos = None
                    try:
                        stream.seek(0)
                    except Exception:
                        pass
                    with wave.open(stream, 'rb') as wf:
                        n_frames = wf.getnframes()
                        n_channels = wf.getnchannels()
                        framerate = wf.getframerate()
                    if pos is not None:
                        try:
                            stream.seek(pos)
                        except Exception:
                            pass
                else:
                    with wave.open(cover_file, 'rb') as wf:
                        n_frames = wf.getnframes()
                        n_channels = wf.getnchannels()
                        framerate = wf.getframerate()

                lsb = int(lsb_count)
                total_samples = n_frames * n_channels
                total_bits = total_samples * lsb
                bits_per_second = lsb * n_channels * framerate

                start_seconds_requested = _coerce_start_seconds(start_input)
                start_offset_bits = _seconds_to_bit_offset(start_seconds_requested, framerate, n_channels, lsb)
                if start_offset_bits > total_bits:
                    start_offset_bits = total_bits
                remaining_bits = max(0, total_bits - start_offset_bits)
                capacity = remaining_bits // 8
                start_offset_seconds = round(float(start_offset_bits) / bits_per_second, 6) if bits_per_second else 0.0
                audio_duration_seconds = round(float(total_bits) / bits_per_second, 6) if bits_per_second else 0.0

                return jsonify({
                    'capacity_bytes': capacity,
                    'start_location': start_input,
                    'start_offset_bits': int(start_offset_bits),
                    'start_offset_seconds': start_offset_seconds,
                    'start_seconds_requested': start_seconds_requested,
                    'audio_duration_seconds': audio_duration_seconds
                })
            except wave.Error as exc:
                return jsonify({'error': f'Unsupported or invalid WAV file: {exc}'}), 400
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
