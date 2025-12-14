"""
CNN Model for chord recognition
"""

import torch
import torch.nn as nn
import numpy as np
import os
import requests
from .constants import NUM_CHORDS, CHORDS

# Hooktheory API configuration
HOOKTHEORY_API_KEY = os.getenv('HOOKTHEORY_API_KEY', None)
HOOKTHEORY_API_URL = 'https://api.hooktheory.com/v1'


class CNNModel(nn.Module):
    """
    Convolutional Neural Network for chord recognition
    """
    
    def __init__(self, input_size=600, num_classes=NUM_CHORDS):
        """
        Initialize the CNN model
        
        Args:
            input_size: Input feature dimension (default: 12 * 50 = 600 for chroma features)
            num_classes: Number of chord classes
        """
        super(CNNModel, self).__init__()
        
        self.input_size = input_size
        self.num_classes = num_classes
        
        # Simple CNN architecture
        self.conv1 = nn.Conv1d(1, 16, kernel_size=3, padding=1)
        self.pool = nn.MaxPool1d(2)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=3, padding=1)
        self.dropout = nn.Dropout(0.3)
        
        # Calculate the size after convolutions
        conv_output_size = (input_size // 2 // 2) * 32
        
        self.fc1 = nn.Linear(conv_output_size, 128)
        self.fc2 = nn.Linear(128, num_classes)
        
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch_size, 1, input_size)
            
        Returns:
            Output tensor of shape (batch_size, num_classes)
        """
        # Ensure input has correct shape
        if len(x.shape) == 2:
            x = x.unsqueeze(1)  # Add channel dimension
            
        x = torch.relu(self.conv1(x))
        x = self.pool(x)
        x = torch.relu(self.conv2(x))
        x = self.pool(x)
        x = self.dropout(x)
        
        # Flatten
        x = x.view(x.size(0), -1)
        
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x
    
    def predict_from_chroma(self, chroma_features):
        """
        Enhanced rule-based chord prediction from chroma features
        (Fallback method when no trained model is available)
        
        Uses comprehensive chord templates for all 12 keys with various chord types:
        - Major, Minor
        - Dominant 7th, Major 7th, Minor 7th
        - Diminished, Augmented
        - Suspended (sus4)
        
        Args:
            chroma_features: Chroma features (12-dimensional)
            
        Returns:
            Predicted chord index
        """
        # Build comprehensive chord templates
        # Chroma order: C, C#, D, D#, E, F, F#, G, G#, A, A#, B (indices 0-11)
        
        def shift_template(template, semitones):
            """Shift a template by semitones (for transposing to different keys)"""
            return np.roll(template, semitones)
        
        # Base templates for C (root at index 0)
        # Chroma indices: C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11
        base_templates = {
            'major': np.array([1.0, 0, 0, 0, 0.8, 0, 0, 0.9, 0, 0, 0, 0]),      # Root, Major 3rd, Perfect 5th (C, E, G)
            'minor': np.array([1.0, 0, 0, 0.8, 0, 0, 0, 0.9, 0, 0, 0, 0]),      # Root, Minor 3rd, Perfect 5th (C, Eb, G)
            'dom7': np.array([1.0, 0, 0, 0, 0.7, 0, 0, 0.8, 0, 0, 0.6, 0]),     # Root, Maj 3rd, P5, Min 7th (C, E, G, Bb)
            'maj7': np.array([1.0, 0, 0, 0, 0.7, 0, 0, 0.8, 0, 0, 0, 0.6]),     # Root, Maj 3rd, P5, Maj 7th (C, E, G, B)
            'min7': np.array([1.0, 0, 0, 0.7, 0, 0, 0, 0.8, 0, 0, 0.6, 0]),     # Root, Min 3rd, P5, Min 7th (C, Eb, G, Bb)
            'dim': np.array([1.0, 0, 0, 0.8, 0, 0, 0.8, 0, 0, 0, 0, 0]),        # Root, Min 3rd, Dim 5th (C, Eb, Gb)
            'aug': np.array([1.0, 0, 0, 0, 0.8, 0, 0, 0, 0.8, 0, 0, 0]),        # Root, Maj 3rd, Aug 5th (C, E, G#)
            'sus4': np.array([1.0, 0, 0, 0, 0, 0.8, 0, 0.9, 0, 0, 0, 0]),       # Root, Perfect 4th, P5 (C, F, G)
            # NEW CHORD TYPES
            'sus2': np.array([1.0, 0, 0.8, 0, 0, 0, 0, 0.9, 0, 0, 0, 0]),       # Root, Major 2nd, P5 (C, D, G)
            'dim7': np.array([1.0, 0, 0, 0.7, 0, 0, 0.7, 0, 0, 0.6, 0, 0]),     # Root, Min 3rd, Dim 5th, Dim 7th (C, Eb, Gb, Bbb/A)
            'min7b5': np.array([1.0, 0, 0, 0.7, 0, 0, 0.7, 0, 0, 0, 0.6, 0]),   # Half-dim: Root, Min 3rd, Dim 5th, Min 7th (C, Eb, Gb, Bb)
            'add9': np.array([1.0, 0, 0.5, 0, 0.7, 0, 0, 0.8, 0, 0, 0, 0]),     # Root, Maj 2nd(9th), Maj 3rd, P5 (C, D, E, G)
        }
        
        # Note names for each semitone
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Generate all chord templates for ALL 12 KEYS (including sharps)
        all_templates = {}
        
        # Major chords (all 12 keys)
        for i, note in enumerate(note_names):
            all_templates[note] = shift_template(base_templates['major'], i)
        
        # Minor chords (all 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}m'] = shift_template(base_templates['minor'], i)
        
        # Dominant 7th chords (ALL 12 keys - including C#7, D#7, F#7, G#7, A#7)
        for i, note in enumerate(note_names):
            all_templates[f'{note}7'] = shift_template(base_templates['dom7'], i)
        
        # Major 7th chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}maj7'] = shift_template(base_templates['maj7'], i)
        
        # Minor 7th chords (ALL 12 keys - including C#m7, D#m7, F#m7, G#m7, A#m7)
        for i, note in enumerate(note_names):
            all_templates[f'{note}m7'] = shift_template(base_templates['min7'], i)
        
        # Diminished chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}dim'] = shift_template(base_templates['dim'], i)
        
        # Augmented chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}aug'] = shift_template(base_templates['aug'], i)
        
        # Suspended 4th chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}sus4'] = shift_template(base_templates['sus4'], i)
        
        # NEW: Suspended 2nd chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}sus2'] = shift_template(base_templates['sus2'], i)
        
        # NEW: Diminished 7th chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}dim7'] = shift_template(base_templates['dim7'], i)
        
        # NEW: Half-diminished / Minor 7 flat 5 chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}m7b5'] = shift_template(base_templates['min7b5'], i)
        
        # NEW: Add9 chords (ALL 12 keys)
        for i, note in enumerate(note_names):
            all_templates[f'{note}add9'] = shift_template(base_templates['add9'], i)
        
        # Normalize chroma features
        chroma_norm = chroma_features / (np.sum(chroma_features) + 1e-8)
        
        # Find best matching chord using weighted correlation
        best_chord = 'C'
        best_score = -float('inf')
        
        for chord_name, template in all_templates.items():
            # Normalize template
            template_norm = template / (np.sum(template) + 1e-8)
            
            # Compute weighted correlation (emphasizes root note)
            score = np.dot(chroma_norm, template_norm)
            
            # Bonus for strong root note match
            # Extract root note by removing all chord suffixes
            root_note = chord_name
            for suffix in ['m7b5', 'maj7', 'dim7', 'add9', 'sus4', 'sus2', 'm7', 'dim', 'aug', 'm', '7']:
                root_note = root_note.replace(suffix, '')
            try:
                root_index = note_names.index(root_note)
                if chroma_norm[root_index] > 0.5:
                    score *= 1.2
            except ValueError:
                pass  # If root note not found, skip bonus
            
            if score > best_score:
                best_score = score
                best_chord = chord_name
        
        # Confidence thresholding - if score is too low, return 'N' (no chord)
        if best_score < 0.15:  # Empirical threshold
            if 'N' in CHORDS:
                return CHORDS.index('N')
        
        # Get index in CHORDS list
        if best_chord in CHORDS:
            return CHORDS.index(best_chord)
        else:
            # Fallback to C major if chord not in list
            return 0


def get_chords_from_hooktheory(song_title, artist):
    """
    Try to get chord progression from Hooktheory API
    
    Args:
        song_title: Title of the song
        artist: Artist name
        
    Returns:
        List of chord names if found, None if not found or API unavailable
    """
    if not HOOKTHEORY_API_KEY:
        print("[HOOKTHEORY] API key not configured, skipping external lookup")
        return None
    
    try:
        print(f"[HOOKTHEORY] Searching for '{song_title}' by '{artist}'")
        
        # Search for the song
        headers = {
            'Authorization': f'Bearer {HOOKTHEORY_API_KEY}',
            'Accept': 'application/json'
        }
        
        # Clean up search terms
        clean_title = song_title.lower().strip()
        clean_artist = artist.lower().strip()
        
        # Try to search for the song
        search_url = f"{HOOKTHEORY_API_URL}/trends/songs"
        params = {
            'q': f"{clean_artist} {clean_title}"
        }
        
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data and len(data) > 0:
                # Found matching songs
                song = data[0]  # Take first match
                
                # Extract chord progression if available
                if 'chords' in song:
                    chords = song['chords']
                    print(f"[HOOKTHEORY] Found chords: {chords}")
                    return chords
                    
                # Try to get song details
                if 'id' in song:
                    detail_url = f"{HOOKTHEORY_API_URL}/trends/songs/{song['id']}"
                    detail_response = requests.get(detail_url, headers=headers, timeout=10)
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        if 'chords' in detail_data:
                            print(f"[HOOKTHEORY] Found chords from details: {detail_data['chords']}")
                            return detail_data['chords']
                
                print(f"[HOOKTHEORY] Song found but no chord data available")
                return None
            else:
                print(f"[HOOKTHEORY] No results found for '{song_title}' by '{artist}'")
                return None
        elif response.status_code == 401:
            print("[HOOKTHEORY] API key invalid or expired")
            return None
        elif response.status_code == 429:
            print("[HOOKTHEORY] Rate limit exceeded")
            return None
        else:
            print(f"[HOOKTHEORY] API error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("[HOOKTHEORY] API timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[HOOKTHEORY] Request error: {e}")
        return None
    except Exception as e:
        print(f"[HOOKTHEORY] Unexpected error: {e}")
        return None
