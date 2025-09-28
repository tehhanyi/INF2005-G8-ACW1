import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps
import io
import base64
import cv2
import os
from scipy import stats
import librosa
import soundfile as sf

def generate_difference_map(cover_path, stego_path):
    """Generate visual difference map between cover and stego images"""
    try:
        # Read images with EXIF orientation respected
        with Image.open(cover_path) as cim:
            cover_rgb = np.array(ImageOps.exif_transpose(cim).convert('RGB'))
        with Image.open(stego_path) as sim:
            stego_rgb = np.array(ImageOps.exif_transpose(sim).convert('RGB'))
        
        # Calculate absolute difference
        diff_img = np.abs(cover_rgb.astype(np.int16) - stego_rgb.astype(np.int16))
        
        # Create enhanced difference map (amplify small changes)
        enhanced_diff = np.clip(diff_img * 50, 0, 255).astype(np.uint8)
        
        # Create black-white filtering for LSB analysis (from lecture)
        # Even values = black (0), odd values = white (255)
        cover_bw = np.where(cover_rgb % 2 == 0, 0, 255).astype(np.uint8)
        stego_bw = np.where(stego_rgb % 2 == 0, 0, 255).astype(np.uint8)
        
        # Create subplot visualization
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # Original images
        axes[0,0].imshow(cover_rgb)
        axes[0,0].set_title('Cover Image')
        axes[0,0].axis('off')
        
        axes[0,1].imshow(stego_rgb)
        axes[0,1].set_title('Stego Image')
        axes[0,1].axis('off')
        
        axes[0,2].imshow(enhanced_diff)
        axes[0,2].set_title('Difference Map (Enhanced)')
        axes[0,2].axis('off')
        
        # LSB analysis (black-white filtering)
        axes[1,0].imshow(cover_bw, cmap='gray')
        axes[1,0].set_title('Cover LSB Plane (Even=Black, Odd=White)')
        axes[1,0].axis('off')
        
        axes[1,1].imshow(stego_bw, cmap='gray')
        axes[1,1].set_title('Stego LSB Plane')
        axes[1,1].axis('off')
        
        # LSB difference
        lsb_diff = np.abs(cover_bw.astype(np.int16) - stego_bw.astype(np.int16))
        axes[1,2].imshow(lsb_diff, cmap='hot')
        axes[1,2].set_title('LSB Changes (Hot = Modified)')
        axes[1,2].axis('off')
        
        plt.tight_layout()
        
        # Convert to base64 for web display
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        print(f"Error generating difference map: {str(e)}")
        return None


def create_histogram_analysis(image_path, channels=['R', 'G', 'B'], stego_path=None):
    """Create histogram analysis like the lecture image"""
    try:
        # Read cover image
        cover_img = cv2.imread(image_path)
        if cover_img is None:
            return None
            
        cover_rgb = cv2.cvtColor(cover_img, cv2.COLOR_BGR2RGB)
        
        # Read stego image if provided
        stego_rgb = None
        if stego_path and os.path.exists(stego_path):
            stego_img = cv2.imread(stego_path)
            if stego_img is not None:
                stego_rgb = cv2.cvtColor(stego_img, cv2.COLOR_BGR2RGB)
        
        # Create figure with subplots (similar to lecture layout)
        if stego_rgb is not None:
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        else:
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            axes = [axes]  # Make it 2D for consistent indexing
        
        colors = ['red', 'green', 'blue']
        channel_names = ['Red', 'Green', 'Blue']
        
        # Analyze each channel
        for i, (color, channel_name) in enumerate(zip(colors, channel_names)):
            # Cover image histogram
            channel_data = cover_rgb[:, :, i].flatten()
            
            axes[0][i].hist(channel_data, bins=256, range=[0, 256], 
                           color=color, alpha=0.7, density=True)
            axes[0][i].set_title(f'Cover Image - {channel_name} Channel Histogram')
            axes[0][i].set_xlabel('Pixel Intensity')
            axes[0][i].set_ylabel('Normalized Frequency')
            axes[0][i].grid(True, alpha=0.3)
            
            # Add statistics text
            stats_text = f'Mean: {np.mean(channel_data):.1f}\nStd: {np.std(channel_data):.1f}\nPixels: {len(channel_data)}'
            axes[0][i].text(0.02, 0.98, stats_text, transform=axes[0][i].transAxes, 
                           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # Stego image histogram (if available)
            if stego_rgb is not None:
                stego_channel_data = stego_rgb[:, :, i].flatten()
                
                axes[1][i].hist(stego_channel_data, bins=256, range=[0, 256], 
                               color=color, alpha=0.7, density=True)
                axes[1][i].set_title(f'Stego Image - {channel_name} Channel Histogram')
                axes[1][i].set_xlabel('Pixel Intensity')
                axes[1][i].set_ylabel('Normalized Frequency')
                axes[1][i].grid(True, alpha=0.3)
                
                # Calculate and display statistical differences
                chi2_stat, p_value = stats.chisquare(
                    np.histogram(stego_channel_data, bins=256, range=[0, 256])[0],
                    np.histogram(channel_data, bins=256, range=[0, 256])[0]
                )
                
                diff_stats_text = f'Mean: {np.mean(stego_channel_data):.1f}\nChi²: {chi2_stat:.2e}\np-val: {p_value:.2e}'
                axes[1][i].text(0.02, 0.98, diff_stats_text, transform=axes[1][i].transAxes, 
                               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        print(f"Error creating histogram analysis: {str(e)}")
        return None


def extract_bit_planes(image_path):
    """Extract all 8 bit planes as shown in lecture"""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
            
        # Create figure for 8 bit planes (2x4 layout)
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        
        for bit in range(8):
            # Extract bit plane
            bit_plane = (img >> bit) & 1
            bit_plane = bit_plane * 255  # Scale to 0-255 for visibility
            
            row, col = divmod(bit, 4)
            axes[row, col].imshow(bit_plane, cmap='gray')
            
            if bit == 0:
                axes[row, col].set_title(f'Bit Plane {bit} (LSB)')
            elif bit == 7:
                axes[row, col].set_title(f'Bit Plane {bit} (MSB)')
            else:
                axes[row, col].set_title(f'Bit Plane {bit}')
            
            axes[row, col].axis('off')
        
        plt.suptitle('Bit Plane Analysis - Individual Bit Planes', fontsize=16)
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        print(f"Error extracting bit planes: {str(e)}")
        return None


def create_waveform_comparison(cover_audio_path, stego_audio_path):
    """Compare audio waveforms before and after embedding"""
    try:
        # Load audio files
        cover_audio, cover_sr = librosa.load(cover_audio_path, sr=None)
        stego_audio, stego_sr = librosa.load(stego_audio_path, sr=None)
        
        if cover_sr != stego_sr:
            return None
            
        # Create time arrays
        cover_time = np.linspace(0, len(cover_audio) / cover_sr, len(cover_audio))
        stego_time = np.linspace(0, len(stego_audio) / stego_sr, len(stego_audio))
        
        # Calculate difference
        min_len = min(len(cover_audio), len(stego_audio))
        audio_diff = stego_audio[:min_len] - cover_audio[:min_len]
        diff_time = np.linspace(0, min_len / cover_sr, min_len)
        
        # Create visualization
        fig, axes = plt.subplots(4, 1, figsize=(15, 12))
        
        # Cover waveform
        axes[0].plot(cover_time, cover_audio, color='blue', alpha=0.7)
        axes[0].set_title('Cover Audio Waveform')
        axes[0].set_ylabel('Amplitude')
        axes[0].grid(True, alpha=0.3)
        
        # Stego waveform
        axes[1].plot(stego_time, stego_audio, color='red', alpha=0.7)
        axes[1].set_title('Stego Audio Waveform')
        axes[1].set_ylabel('Amplitude')
        axes[1].grid(True, alpha=0.3)
        
        # Difference waveform
        axes[2].plot(diff_time, audio_diff, color='green', alpha=0.8)
        axes[2].set_title('Difference Waveform (Stego - Cover)')
        axes[2].set_ylabel('Amplitude Difference')
        axes[2].grid(True, alpha=0.3)
        
        # Spectrogram of difference
        D = librosa.stft(audio_diff)
        S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
        img = librosa.display.specshow(S_db, x_axis='time', y_axis='hz', ax=axes[3])
        axes[3].set_title('Difference Spectrogram')
        fig.colorbar(img, ax=axes[3], format='%+2.0f dB')
        
        axes[3].set_xlabel('Time (seconds)')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        print(f"Error creating waveform comparison: {str(e)}")
        return None


def calculate_capacity_info(file_path, file_type, lsb_count=1):
    """Calculate embedding capacity information using lecture formula"""
    try:
        capacity_info = {}
        
        if file_type.lower() in ['png', 'bmp', 'tiff', 'jpg', 'jpeg']:
            # Image capacity calculation (from lecture)
            img = cv2.imread(file_path)
            if img is None:
                return None
                
            height, width, channels = img.shape
            
            # Maximum bytes calculation from lecture: n_bytes = width * height * channels // 8
            total_pixels = width * height
            total_bits_available = total_pixels * channels * lsb_count
            max_bytes = total_bits_available // 8
            
            capacity_info = {
                'file_type': 'image',
                'dimensions': f'{width} x {height}',
                'channels': channels,
                'total_pixels': total_pixels,
                'lsb_bits_used': lsb_count,
                'total_bits_available': total_bits_available,
                'max_bytes_capacity': max_bytes,
                'max_kb_capacity': max_bytes / 1024,
                'max_mb_capacity': max_bytes / (1024 * 1024)
            }
            
        elif file_type.lower() in ['wav', 'pcm']:
            # Audio capacity calculation
            audio_data, sample_rate = librosa.load(file_path, sr=None)
            total_samples = len(audio_data)
            
            # For 16-bit audio, we can use LSB of each sample
            total_bits_available = total_samples * lsb_count
            max_bytes = total_bits_available // 8
            
            capacity_info = {
                'file_type': 'audio',
                'sample_rate': sample_rate,
                'duration_seconds': len(audio_data) / sample_rate,
                'total_samples': total_samples,
                'lsb_bits_used': lsb_count,
                'total_bits_available': total_bits_available,
                'max_bytes_capacity': max_bytes,
                'max_kb_capacity': max_bytes / 1024,
                'max_mb_capacity': max_bytes / (1024 * 1024)
            }
        
        return capacity_info
        
    except Exception as e:
        print(f"Error calculating capacity: {str(e)}")
        return None

def analyze_stego_detection(file_path, file_type):
    """Perform steganalysis detection algorithms from lecture"""
    try:
        analysis_results = {}
        
        if file_type.lower() in ['png', 'bmp', 'tiff', 'jpg', 'jpeg']:
            img = cv2.imread(file_path)
            if img is None:
                return None
                
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 1. LSB Analysis (from lecture)
            lsb_analysis = {}
            for channel in range(3):
                channel_data = img_rgb[:, :, channel]
                
                # Count even/odd pixels (LSB analysis from lecture)
                even_pixels = np.sum(channel_data % 2 == 0)
                odd_pixels = np.sum(channel_data % 2 == 1)
                total_pixels = channel_data.size
                
                # Chi-square test for randomness
                expected = total_pixels / 2
                chi2_stat = ((even_pixels - expected) ** 2 + (odd_pixels - expected) ** 2) / expected
                
                lsb_analysis[f'channel_{channel}'] = {
                    'even_pixels': even_pixels,
                    'odd_pixels': odd_pixels,
                    'ratio': even_pixels / odd_pixels if odd_pixels > 0 else 0,
                    'chi2_statistic': chi2_stat
                }
            
            # 2. Histogram Analysis (Pairs of Values from lecture)
            hist_analysis = {}
            for channel in range(3):
                channel_data = img_rgb[:, :, channel].flatten()
                hist, _ = np.histogram(channel_data, bins=256, range=[0, 256])
                
                # Look for pairs of values (PoV analysis from lecture)
                pov_score = 0
                for i in range(0, 256, 2):
                    if i + 1 < 256:
                        pov_score += abs(hist[i] - hist[i + 1])
                
                hist_analysis[f'channel_{channel}'] = {
                    'pov_score': pov_score,
                    'histogram_variance': np.var(hist),
                    'histogram_mean': np.mean(hist)
                }
            
            analysis_results = {
                'file_type': 'image',
                'lsb_analysis': lsb_analysis,
                'histogram_analysis': hist_analysis,
                'detection_confidence': 'low'  # Simple heuristic
            }
            
            # Detection heuristic based on chi-square values
            avg_chi2 = np.mean([lsb_analysis[f'channel_{i}']['chi2_statistic'] for i in range(3)])
            if avg_chi2 > 10:
                analysis_results['detection_confidence'] = 'high'
            elif avg_chi2 > 5:
                analysis_results['detection_confidence'] = 'medium'
        
        return analysis_results
        
    except Exception as e:
        print(f"Error in steganalysis detection: {str(e)}")
        return None

def analyze_complexity_segments(image_path, block_size=8, threshold=0.3):
    """Analyze BPCS complexity segments as described in lecture"""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
            
        height, width = img.shape
        complexity_data = []
        
        for i in range(0, height - block_size + 1, block_size):
            for j in range(0, width - block_size + 1, block_size):
                block = img[i:i+block_size, j:j+block_size]
                
                # Calculate complexity (from lecture: c = actual changes / 112)
                h_changes = np.sum(np.abs(np.diff(block, axis=1)) > 0)
                v_changes = np.sum(np.abs(np.diff(block, axis=0)) > 0)
                
                total_changes = h_changes + v_changes
                max_changes = 2 * block_size * (block_size - 1)  # 112 for 8x8 block
                
                complexity = total_changes / max_changes if max_changes > 0 else 0
                complexity_data.append({
                    'x': j, 'y': i,
                    'complexity': complexity,
                    'is_complex': complexity > threshold
                })
        
        return {
            'complexity_data': complexity_data,
            'threshold': threshold,
            'total_blocks': len(complexity_data),
            'complex_blocks': sum(1 for block in complexity_data if block['is_complex'])
        }
        
    except Exception as e:
        print(f"Error analyzing complexity: {str(e)}")
        return None
