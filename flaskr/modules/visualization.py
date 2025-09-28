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
    """Compare audio waveforms before and after embedding with correct time scaling"""
    try:
        # Load audio files (preserve original sample rate)
        cover_audio, cover_sr = librosa.load(cover_audio_path, sr=None)
        stego_audio, stego_sr = librosa.load(stego_audio_path, sr=None)
        
        # Ensure both files have the same sample rate
        if cover_sr != stego_sr:
            print(f"Sample rate mismatch: cover={cover_sr}, stego={stego_sr}")
            return None
            
        # Ensure both files have reasonable length
        if len(cover_audio) == 0 or len(stego_audio) == 0:
            print("One or both audio files are empty")
            return None
            
        # Create time arrays for waveforms
        cover_time = np.linspace(0, len(cover_audio) / cover_sr, len(cover_audio))
        stego_time = np.linspace(0, len(stego_audio) / stego_sr, len(stego_audio))
        
        # Calculate difference (truncate to shorter length)
        min_len = min(len(cover_audio), len(stego_audio))
        if min_len == 0:
            print("No overlapping audio data to compare")
            return None
            
        audio_diff = stego_audio[:min_len] - cover_audio[:min_len]
        diff_time = np.linspace(0, min_len / cover_sr, min_len)
        
        # STFT parameters for consistent time scaling
        n_fft = 2048
        hop_length = 512
        
        # Create visualization with better layout
        fig, axes = plt.subplots(4, 1, figsize=(16, 12))
        
        # Cover waveform
        axes[0].plot(cover_time, cover_audio, color='blue', alpha=0.7, linewidth=0.5)
        axes[0].set_title('Cover Audio Waveform', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Amplitude')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_xlim(0, max(cover_time[-1], stego_time[-1]) if len(cover_time) > 0 and len(stego_time) > 0 else 1)
        
        # Stego waveform
        axes[1].plot(stego_time, stego_audio, color='red', alpha=0.7, linewidth=0.5)
        axes[1].set_title('Stego Audio Waveform', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Amplitude')
        axes[1].grid(True, alpha=0.3)
        axes[1].set_xlim(0, max(cover_time[-1], stego_time[-1]) if len(cover_time) > 0 and len(stego_time) > 0 else 1)
        
        # Difference waveform with enhanced visibility
        axes[2].plot(diff_time, audio_diff, color='green', alpha=0.8, linewidth=0.6)
        axes[2].set_title('Difference Waveform (Stego - Cover)', fontsize=12, fontweight='bold')
        axes[2].set_ylabel('Amplitude Difference')
        axes[2].grid(True, alpha=0.3)
        axes[2].set_xlim(0, diff_time[-1] if len(diff_time) > 0 else 1)
        
        # Add zero line for reference
        axes[2].axhline(y=0, color='black', linestyle='--', alpha=0.5, linewidth=0.8)
        
        # Fixed spectrogram with correct time scaling
        if len(audio_diff) >= n_fft:  # Ensure we have enough samples for STFT
            D = librosa.stft(audio_diff, n_fft=n_fft, hop_length=hop_length, center=True)
            S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
            
            # CRITICAL FIX: Pass sr and hop_length to specshow for correct time axis
            img = librosa.display.specshow(
                S_db, 
                sr=cover_sr,           # Use actual sample rate
                hop_length=hop_length, # Use same hop_length as STFT
                x_axis='time', 
                y_axis='hz', 
                ax=axes[3],
                cmap='viridis'         # Better colormap for visibility
            )
            axes[3].set_title('Difference Spectrogram', fontsize=12, fontweight='bold')
            
            # Add colorbar with proper formatting
            cbar = fig.colorbar(img, ax=axes[3], format='%+2.0f dB', shrink=0.8)
            cbar.set_label('Magnitude (dB)', rotation=270, labelpad=15)
            
        else:
            # Fallback for very short audio
            axes[3].text(0.5, 0.5, 'Audio too short for spectrogram analysis', 
                        ha='center', va='center', transform=axes[3].transAxes,
                        fontsize=12, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            axes[3].set_title('Difference Spectrogram (Insufficient Data)', fontsize=12)
            axes[3].set_xlabel('Time (seconds)')
            axes[3].set_ylabel('Frequency (Hz)')
        
        # Set consistent x-axis label
        axes[3].set_xlabel('Time (seconds)', fontsize=11)
        
        # Add file info as subtitle
        duration_text = f"Duration: {len(cover_audio)/cover_sr:.2f}s | Sample Rate: {cover_sr} Hz | Samples: {min_len:,}"
        fig.suptitle(f'Audio Waveform Comparison\n{duration_text}', fontsize=14, y=0.98)
        
        # Improve layout
        plt.tight_layout(rect=[0, 0, 1, 0.95])  # Leave space for suptitle
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        print(f"Error creating waveform comparison: {str(e)}")
        import traceback
        traceback.print_exc()  # For debugging
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
    """Simple, effective steganalysis detection"""
    try:
        ft = (file_type or '').lower()
        analysis_results = {'detection_confidence': 'unknown'}

        if ft in ['wav', 'pcm', 'mp3']:
            try:
                audio, sr = sf.read(file_path, dtype='int16', always_2d=False)
                if audio.ndim > 1:
                    audio = audio.mean(axis=1).astype(np.int16)
                samples = audio.astype(np.int32)
            except Exception:
                y, sr = librosa.load(file_path, sr=None, mono=True)
                samples = (np.clip(y, -1, 1) * 32767.0).astype(np.int32)

            if samples.size == 0:
                return analysis_results

            # Simple but effective approach
            lsb = samples & 1
            ones = int(lsb.sum())
            zeros = int(lsb.size - ones)
            
            # Key insight: Check LSB distribution in segments
            win = 8192  # Larger window for stability
            step = win
            
            segment_biases = []
            for start in range(0, lsb.size - win + 1, step):
                seg = lsb[start:start+win]
                seg_ones = int(seg.sum())
                seg_bias = abs((seg_ones / len(seg)) - 0.5)
                segment_biases.append(seg_bias)
            
            if not segment_biases:
                return analysis_results
            
            # Simple decision metrics
            avg_bias = float(np.mean(segment_biases))
            min_bias = float(np.min(segment_biases))
            max_bias = float(np.max(segment_biases))
            std_bias = float(np.std(segment_biases))
            
            # Count segments that are "too balanced" (suspicious for embedding)
            very_balanced_segments = sum(1 for b in segment_biases if b < 0.01)
            balanced_ratio = very_balanced_segments / len(segment_biases)
            
            # Simple scoring logic
            stego_indicators = 0
            
            # Indicator 1: Too many perfectly balanced segments
            if balanced_ratio > 0.6:  # More than 60% of segments perfectly balanced
                stego_indicators += 2
            elif balanced_ratio > 0.4:  # More than 40% perfectly balanced
                stego_indicators += 1
                
            # Indicator 2: Very low average bias (overall too balanced)
            if avg_bias < 0.005:
                stego_indicators += 2
            elif avg_bias < 0.01:
                stego_indicators += 1
                
            # Indicator 3: Low variance in bias (too consistent = suspicious)
            if std_bias < 0.005:
                stego_indicators += 1
                
            # Indicator 4: Minimum bias too low (at least one segment perfectly balanced)
            if min_bias < 0.002:
                stego_indicators += 1
            
            # CRITICAL: Natural audio penalty
            # Natural audio typically has some segments with higher bias
            if max_bias > 0.05 and balanced_ratio < 0.3:
                # Has natural variation and not too many balanced segments
                stego_indicators = max(0, stego_indicators - 2)  # Strong penalty
            elif max_bias > 0.03 and balanced_ratio < 0.4:
                stego_indicators = max(0, stego_indicators - 1)  # Moderate penalty
            
            # Final confidence mapping (simplified)
            conf = 'unknown'
            if stego_indicators >= 4:
                conf = 'high'
            elif stego_indicators >= 3:
                conf = 'medium'
            elif stego_indicators >= 2:
                conf = 'low'
            # 0-1 stays 'unknown'
            
            analysis_results.update({
                'file_type': 'audio',
                'sample_rate': int(sr) if sr else None,
                'audio_metrics': {
                    'segments_analyzed': len(segment_biases),
                    'avg_bias': avg_bias,
                    'min_bias': min_bias,
                    'max_bias': max_bias,
                    'std_bias': std_bias,
                    'balanced_segments': int(very_balanced_segments),
                    'balanced_ratio': float(balanced_ratio),
                    'stego_indicators': int(stego_indicators)
                },
                'detection_confidence': conf
            })
            return analysis_results

        analysis_results.update({'file_type': ft or 'unknown'})
        return analysis_results

    except Exception as e:
        print(f"Error in steganalysis detection: {str(e)}")
        return {'detection_confidence': 'unknown'}

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
