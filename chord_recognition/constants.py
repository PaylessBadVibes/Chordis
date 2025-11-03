"""
Constants for chord recognition
"""

# Common chord labels used in music
CHORDS = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',  # Major
    'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm',  # Minor
    'C7', 'D7', 'E7', 'F7', 'G7', 'A7', 'B7',  # Dominant 7th
    'Cmaj7', 'Dmaj7', 'Emaj7', 'Fmaj7', 'Gmaj7', 'Amaj7', 'Bmaj7',  # Major 7th
    'Cm7', 'Dm7', 'Em7', 'Fm7', 'Gm7', 'Am7', 'Bm7',  # Minor 7th
    'Cdim', 'Ddim', 'Edim', 'Fdim', 'Gdim', 'Adim', 'Bdim',  # Diminished
    'Caug', 'Daug', 'Eaug', 'Faug', 'Gaug', 'Aaug', 'Baug',  # Augmented
    'Csus4', 'Dsus4', 'Esus4', 'Fsus4', 'Gsus4', 'Asus4', 'Bsus4',  # Suspended
    'N',  # No chord
]

# Number of chords
NUM_CHORDS = len(CHORDS)

# Audio processing parameters
SAMPLE_RATE = 16000
HOP_LENGTH = 512
N_FFT = 2048
N_MELS = 128

