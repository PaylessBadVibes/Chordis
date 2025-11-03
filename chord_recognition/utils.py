"""
Utility functions for audio preprocessing
"""

import numpy as np
import librosa
from .constants import SAMPLE_RATE, HOP_LENGTH, N_FFT, N_MELS


def preprocess_audio(y, sr=SAMPLE_RATE):
    """
    Preprocess audio signal for chord recognition
    
    Args:
        y: Audio time series (numpy array)
        sr: Sample rate
        
    Returns:
        Processed features as numpy array (spectral features)
    """
    # Compute mel-spectrogram
    mel_spec = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS
    )
    
    # Convert to log scale (dB)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Normalize
    mel_spec_db = (mel_spec_db - mel_spec_db.mean()) / (mel_spec_db.std() + 1e-8)
    
    # Compute chroma features (useful for chord recognition)
    chroma = librosa.feature.chroma_cqt(
        y=y,
        sr=sr,
        hop_length=HOP_LENGTH
    )
    
    # Combine features
    # For simplicity, we'll use chroma features which are directly related to chords
    # Shape: (12, time_frames) where 12 represents the 12 pitch classes
    
    # Segment into fixed-length windows
    window_size = 50  # Number of frames per segment
    num_windows = chroma.shape[1] // window_size
    
    if num_windows == 0:
        # If audio is too short, pad it
        num_windows = 1
        chroma_padded = np.pad(chroma, ((0, 0), (0, window_size - chroma.shape[1])), mode='constant')
        features = chroma_padded.T[:window_size].reshape(1, -1)
    else:
        # Take only complete windows
        chroma_truncated = chroma[:, :num_windows * window_size]
        # Reshape to (num_windows, 12 * window_size)
        features = chroma_truncated.T.reshape(num_windows, -1)
    
    return features


def extract_chroma_features(y, sr=SAMPLE_RATE):
    """
    Extract chroma features from audio
    
    Args:
        y: Audio time series
        sr: Sample rate
        
    Returns:
        Chroma features
    """
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)
    return chroma


def segment_audio(features, segment_length=50):
    """
    Segment audio features into fixed-length chunks
    
    Args:
        features: Audio features (2D array)
        segment_length: Length of each segment
        
    Returns:
        Segmented features
    """
    num_segments = features.shape[1] // segment_length
    if num_segments == 0:
        return features.T[:segment_length].reshape(1, -1)
    
    truncated = features[:, :num_segments * segment_length]
    return truncated.T.reshape(num_segments, -1)

