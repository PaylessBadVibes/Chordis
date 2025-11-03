"""
Chord Recognition Module
Simple chord recognition for music analysis
"""

from .constants import CHORDS
from .model import CNNModel
from .utils import preprocess_audio

__all__ = ['CHORDS', 'CNNModel', 'preprocess_audio']

