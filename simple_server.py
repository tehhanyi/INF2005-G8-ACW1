# Minimal Flask replacement for testing
import http.server
import socketserver
import urllib.parse
import json
import io
import os
import cgi
import tempfile
from lsb_steganography import LSBSteganography, detect_file_type
import traceback

class SteganoHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('templates/index.html', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path.startswith('/download/'):
            filename = self.path[10:]  # Remove '/download/'
            filepath = os.path.join('uploads', filename)
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'healthy', 'message': 'LSB Steganography API is running'}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        try:
            if self.path == '/encode':
                self.handle_encode()
            elif self.path == '/decode':
                self.handle_decode()
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            self.send_json_response({'error': f'Server error: {str(e)}'}, 500)
    
    def handle_encode(self):
        # Parse multipart form data
        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self.send_json_response({'error': 'Content-Type must be multipart/form-data'}, 400)
            return
        
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_json_response({'error': 'No data received'}, 400)
            return
        
        # Read and parse the multipart data
        post_data = self.rfile.read(content_length)
        
        # Parse multipart data using cgi.FieldStorage
        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': str(content_length)
        }
        
        fp = io.BytesIO(post_data)
        form = cgi.FieldStorage(fp=fp, environ=env)
        
        # Extract form fields
        key = form.getvalue('key')
        if not key:
            self.send_json_response({'error': 'Key is required'}, 400)
            return
        
        cover_file = form['cover_file'] if 'cover_file' in form else None
        if cover_file is None or not hasattr(cover_file, 'file') or not cover_file.file:
            self.send_json_response({'error': 'Cover file is required'}, 400)
            return
        
        payload_text = form.getvalue('payload_text', '').strip()
        payload_file = form['payload_file'] if 'payload_file' in form else None
        
        if not payload_text and (payload_file is None or not hasattr(payload_file, 'file') or not payload_file.file):
            self.send_json_response({'error': 'Either payload text or payload file is required'}, 400)
            return
        
        # Read cover data
        cover_data = cover_file.file.read()
        if len(cover_data) == 0:
            self.send_json_response({'error': 'Cover file is empty'}, 400)
            return
        
        # Prepare payload data
        if payload_text:
            payload_data = payload_text.encode('utf-8')
            payload_type = 'text'
        else:
            payload_data = payload_file.file.read()
            payload_type = detect_file_type(payload_data, payload_file.filename)
        
        # Initialize steganography
        stego = LSBSteganography(key)
        
        # Encode the data
        encoded_data = stego.encode(cover_data, payload_data, payload_type)
        
        # Generate output filename
        cover_filename = cover_file.filename or 'cover_file'
        name, ext = os.path.splitext(cover_filename)
        output_filename = f"{name}_encoded{ext}"
        
        # Save encoded file
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        output_path = os.path.join('uploads', output_filename)
        with open(output_path, 'wb') as f:
            f.write(encoded_data)
        
        response = {
            'success': True,
            'message': f'Data successfully encoded into {cover_filename}',
            'download_url': f'/download/{output_filename}',
            'payload_type': payload_type,
            'payload_size': len(payload_data),
            'cover_size': len(cover_data),
            'encoded_size': len(encoded_data)
        }
        self.send_json_response(response)
    
    def handle_decode(self):
        # Parse multipart form data (same as encode)
        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self.send_json_response({'error': 'Content-Type must be multipart/form-data'}, 400)
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_json_response({'error': 'No data received'}, 400)
            return
        
        post_data = self.rfile.read(content_length)
        
        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': str(content_length)
        }
        
        fp = io.BytesIO(post_data)
        form = cgi.FieldStorage(fp=fp, environ=env)
        
        # Extract form fields
        key = form.getvalue('key')
        if not key:
            self.send_json_response({'error': 'Key is required for decoding'}, 400)
            return
        
        encoded_file = form['encoded_file'] if 'encoded_file' in form else None
        if encoded_file is None or not hasattr(encoded_file, 'file') or not encoded_file.file:
            self.send_json_response({'error': 'Encoded file is required'}, 400)
            return
        
        # Read encoded data
        encoded_data = encoded_file.file.read()
        if len(encoded_data) == 0:
            self.send_json_response({'error': 'Encoded file is empty'}, 400)
            return
        
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
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        output_path = os.path.join('uploads', output_filename)
        with open(output_path, 'wb') as f:
            f.write(payload_data)
        
        # If it's text, also return the text content
        text_content = None
        if payload_type == 'text':
            try:
                text_content = payload_data.decode('utf-8')
            except:
                text_content = "Could not decode as UTF-8 text"
        
        response = {
            'success': True,
            'message': f'Data successfully decoded from {encoded_file.filename}',
            'download_url': f'/download/{output_filename}',
            'payload_type': payload_type,
            'payload_size': len(payload_data),
            'metadata': metadata,
            'text_content': text_content
        }
        self.send_json_response(response)
    
    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def run_server(port=5000):
    handler = SteganoHandler
    httpd = socketserver.TCPServer(("", port), handler)
    print(f"LSB Steganography server starting at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()