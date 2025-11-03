"""
CNN Model for chord recognition
"""

import torch
import torch.nn as nn
import numpy as np
from .constants import NUM_CHORDS, CHORDS


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
        Simple rule-based chord prediction from chroma features
        (Fallback method when no trained model is available)
        
        Args:
            chroma_features: Chroma features (12-dimensional)
            
        Returns:
            Predicted chord index
        """
        # Major chord templates (simplified)
        major_templates = {
            'C': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],   # C, E, G
            'D': [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],   # D, F#, A
            'E': [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],   # E, G#, B
            'F': [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],   # F, A, C
            'G': [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],   # G, B, D
            'A': [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],   # A, C#, E
            'B': [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],   # B, D#, F#
        }
        
        # Minor chord templates
        minor_templates = {
            'Am': [1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],  # A, C, E
            'Em': [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],  # E, G, B
            'Dm': [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],  # D, F, A
        }
        
        # Combine all templates
        all_templates = {**major_templates, **minor_templates}
        
        # Find best matching chord
        best_chord = 'C'
        best_score = -float('inf')
        
        # Normalize chroma
        chroma_norm = chroma_features / (np.sum(chroma_features) + 1e-8)
        
        for chord_name, template in all_templates.items():
            template_array = np.array(template)
            # Compute correlation
            score = np.dot(chroma_norm, template_array)
            if score > best_score:
                best_score = score
                best_chord = chord_name
        
        # Get index in CHORDS list
        if best_chord in CHORDS:
            return CHORDS.index(best_chord)
        else:
            return 0  # Default to C major

