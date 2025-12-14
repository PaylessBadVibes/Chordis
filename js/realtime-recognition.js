/**
 * Real-time Audio Recognition
 * Detects chords from live instrument input using microphone
 * Uses FFT analysis to identify musical notes and determine chords
 */

class RealtimeChordRecognition {
    constructor() {
        this.isListening = false;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.detectedChords = [];
        this.chordHistory = [];
        this.lastChordTime = 0;
        this.lastChord = null;
        this.onChordDetected = null; // Callback for chord detection
        this.onVolumeChange = null; // Callback for volume visualization
        
        // Musical note frequencies (A4 = 440Hz standard tuning)
        this.NOTE_FREQUENCIES = {
            'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'E2': 82.41, 'F2': 87.31,
            'F#2': 92.50, 'G2': 98.00, 'G#2': 103.83, 'A2': 110.00, 'A#2': 116.54, 'B2': 123.47,
            'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81, 'F3': 174.61,
            'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08, 'B3': 246.94,
            'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63, 'F4': 349.23,
            'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
            'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'E5': 659.25, 'F5': 698.46,
            'F#5': 739.99, 'G5': 783.99, 'G#5': 830.61, 'A5': 880.00, 'A#5': 932.33, 'B5': 987.77,
            'C6': 1046.50
        };
        
        // Note names for chord building
        this.NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        
        // Chord templates (intervals in semitones from root)
        this.CHORD_TEMPLATES = {
            'maj': [0, 4, 7],           // Major triad
            'm': [0, 3, 7],             // Minor triad
            '7': [0, 4, 7, 10],         // Dominant 7th
            'maj7': [0, 4, 7, 11],      // Major 7th
            'm7': [0, 3, 7, 10],        // Minor 7th
            'dim': [0, 3, 6],           // Diminished
            'aug': [0, 4, 8],           // Augmented
            'sus4': [0, 5, 7],          // Suspended 4th
            'sus2': [0, 2, 7],          // Suspended 2nd
            'add9': [0, 4, 7, 14],      // Add 9
            '6': [0, 4, 7, 9],          // Major 6th
            'm6': [0, 3, 7, 9],         // Minor 6th
        };
    }

    async startListening() {
        if (this.isListening) return;

        try {
            // Request microphone access with optimized settings for instruments
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: false,  // Disable for cleaner instrument sound
                    noiseSuppression: false,  // Disable for better frequency detection
                    autoGainControl: false,   // Disable for consistent levels
                    sampleRate: 44100         // Standard audio sample rate
                } 
            });

            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 44100
            });
            
            this.analyser = this.audioContext.createAnalyser();
            this.microphone = this.audioContext.createMediaStreamSource(stream);

            // Configure analyser for better frequency resolution
            this.analyser.fftSize = 8192;  // Higher = better frequency resolution
            this.analyser.smoothingTimeConstant = 0.8;
            this.analyser.minDecibels = -90;
            this.analyser.maxDecibels = -10;
            
            this.microphone.connect(this.analyser);

            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Float32Array(bufferLength);

            this.isListening = true;
            
            // Start analysis loop
            this.analyzeAudio();

            console.log('[REALTIME] Started listening for instrument input');
            return true;
        } catch (error) {
            console.error('Microphone access error:', error);
            throw error;
        }
    }

    stopListening() {
        if (!this.isListening) return;

        // Stop microphone
        if (this.microphone && this.microphone.mediaStream) {
            this.microphone.mediaStream.getTracks().forEach(track => track.stop());
        }

        // Close audio context
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }

        this.isListening = false;
        this.detectedChords = [];
        this.lastChord = null;

        console.log('[REALTIME] Stopped listening');
    }

    analyzeAudio() {
        if (!this.isListening) return;

        // Get frequency data in decibels
        this.analyser.getFloatFrequencyData(this.dataArray);

        // Calculate volume for visualization
        const volume = this.calculateVolume();
        if (this.onVolumeChange) {
            this.onVolumeChange(volume);
        }

        // Only detect chords if there's significant sound (lowered threshold for better sensitivity)
        if (volume > 0.01) {  // Much more sensitive - works with quiet instruments
            const detectedNotes = this.detectNotes();
            
            // Can detect with just 1 note for single-note instruments
            if (detectedNotes.length >= 1) {
                const chord = this.identifyChord(detectedNotes);
                
                if (chord) {
                    const currentTime = Date.now();
                    
                    // Only update if chord changed or 500ms passed
                    if (this.lastChord !== chord || currentTime - this.lastChordTime > 500) {
                        this.addDetectedChord(chord);
                        this.lastChord = chord;
                        this.lastChordTime = currentTime;
                        
                        if (this.onChordDetected) {
                            this.onChordDetected(chord, detectedNotes);
                        }
                    }
                }
            }
        }

        // Continue loop
        requestAnimationFrame(() => this.analyzeAudio());
    }

    calculateVolume() {
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
            // Convert from dB to linear scale
            const amplitude = Math.pow(10, this.dataArray[i] / 20);
            sum += amplitude * amplitude;
        }
        return Math.sqrt(sum / this.dataArray.length);
    }

    detectNotes() {
        const sampleRate = this.audioContext.sampleRate;
        const binSize = sampleRate / this.analyser.fftSize;
        const detectedNotes = [];
        const noteScores = {};
        
        // Initialize scores for all notes
        this.NOTE_NAMES.forEach(note => {
            noteScores[note] = 0;
        });

        // Find peaks in the frequency spectrum
        const peaks = this.findPeaks();
        
        // Map each peak to the nearest musical note
        for (const peak of peaks) {
            const frequency = peak.bin * binSize;
            
            // Expanded frequency range for all instruments:
            // Bass: 40Hz+, Guitar: 80Hz+, Piano: 27Hz-4200Hz, Vocals: 80Hz-1100Hz
            if (frequency < 40 || frequency > 4200) continue;
            
            const noteInfo = this.frequencyToNote(frequency);
            if (noteInfo) {
                // Add to note score based on amplitude
                noteScores[noteInfo.note] += peak.amplitude;
            }
        }
        
        // Get notes with significant scores (lowered thresholds for better sensitivity)
        const maxScore = Math.max(...Object.values(noteScores));
        const threshold = maxScore * 0.2; // Lower threshold (was 0.3)
        
        for (const [note, score] of Object.entries(noteScores)) {
            if (score > threshold && score > 0.01) {  // Lower minimum (was 0.1)
                detectedNotes.push({
                    note: note,
                    score: score
                });
            }
        }
        
        // Sort by score (highest first)
        detectedNotes.sort((a, b) => b.score - a.score);
        
        return detectedNotes.slice(0, 6); // Return top 6 notes
    }

    findPeaks() {
        const peaks = [];
        const threshold = -70; // Lower dB threshold for better sensitivity (was -60)
        
        for (let i = 2; i < this.dataArray.length - 2; i++) {
            const current = this.dataArray[i];
            
            // Check if this is a local maximum
            if (current > threshold &&
                current > this.dataArray[i - 1] &&
                current > this.dataArray[i + 1] &&
                current > this.dataArray[i - 2] &&
                current > this.dataArray[i + 2]) {
                
                // Convert dB to linear amplitude
                const amplitude = Math.pow(10, current / 20);
                
                peaks.push({
                    bin: i,
                    amplitude: amplitude
                });
            }
        }
        
        // Sort by amplitude and return top peaks (increased from 20 to 30)
        peaks.sort((a, b) => b.amplitude - a.amplitude);
        return peaks.slice(0, 30);
    }

    frequencyToNote(frequency) {
        // Calculate the note number relative to A4 (440Hz)
        const noteNum = 12 * Math.log2(frequency / 440);
        const noteIndex = Math.round(noteNum) + 9; // A is index 9 in NOTE_NAMES
        
        // Normalize to 0-11 range
        const normalizedIndex = ((noteIndex % 12) + 12) % 12;
        const noteName = this.NOTE_NAMES[normalizedIndex];
        
        // Calculate how close we are to the exact note (cents)
        const exactNoteNum = 12 * Math.log2(frequency / 440) + 9;
        const cents = Math.abs((exactNoteNum - Math.round(exactNoteNum)) * 100);
        
        // Only accept if within 30 cents of the note
        if (cents < 30) {
            return {
                note: noteName,
                frequency: frequency,
                cents: cents
            };
        }
        
        return null;
    }

    identifyChord(detectedNotes) {
        if (detectedNotes.length < 1) return null;
        
        // Get unique note names
        const noteNames = [...new Set(detectedNotes.map(n => n.note))];
        
        // If only 1 note detected, return it as a single note (not a chord)
        if (noteNames.length === 1) {
            return noteNames[0]; // Return single note like "C" or "G"
        }
        
        // Convert notes to pitch classes (0-11)
        const pitchClasses = noteNames.map(note => this.NOTE_NAMES.indexOf(note));
        
        let bestMatch = null;
        let bestScore = 0;
        
        // Try each note as potential root
        for (let rootIndex = 0; rootIndex < 12; rootIndex++) {
            const rootNote = this.NOTE_NAMES[rootIndex];
            
            // Check if this root note is in our detected notes
            if (!noteNames.includes(rootNote)) continue;
            
            // Calculate intervals from this root
            const intervals = pitchClasses.map(pc => ((pc - rootIndex) + 12) % 12);
            
            // Try to match with chord templates
            for (const [chordType, template] of Object.entries(this.CHORD_TEMPLATES)) {
                const score = this.matchChordTemplate(intervals, template);
                
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = {
                        root: rootNote,
                        type: chordType,
                        score: score
                    };
                }
            }
        }
        
        // Only return if we have a good match (at least 70% of template matched)
        if (bestMatch && bestMatch.score >= 0.7) {
            const chordName = bestMatch.type === 'maj' 
                ? bestMatch.root 
                : bestMatch.root + bestMatch.type;
            return chordName;
        }
        
        // If no chord matched, return the root note as a single note
        if (noteNames.length > 0) {
            return noteNames[0] + ' (note)';
        }
        
        return null;
    }

    matchChordTemplate(intervals, template) {
        let matched = 0;
        
        for (const templateInterval of template) {
            if (intervals.includes(templateInterval)) {
                matched++;
            }
        }
        
        return matched / template.length;
    }

    addDetectedChord(chord) {
        this.detectedChords.push(chord);
        this.chordHistory.push({ 
            chord: chord, 
            timestamp: Date.now() 
        });

        // Keep only last 20 chords
        if (this.detectedChords.length > 20) {
            this.detectedChords.shift();
        }
    }

    getDetectedChords() {
        return [...this.detectedChords];
    }

    getLastChord() {
        return this.lastChord;
    }

    clearHistory() {
        this.detectedChords = [];
        this.chordHistory = [];
        this.lastChord = null;
    }
}

// Export for use in main app
window.RealtimeChordRecognition = RealtimeChordRecognition;
