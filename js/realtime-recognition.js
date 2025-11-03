/**
 * Real-time Audio Recognition
 * Detects chords and identifies songs using microphone input
 */

class RealtimeRecognition {
    constructor(chordisApp) {
        this.app = chordisApp;
        this.isListening = false;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.detectedChords = [];
        this.chordHistory = [];
        this.lastChordTime = 0;
        this.audioBuffer = [];
    }

    async startListening() {
        if (this.isListening) return;

        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });

            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.microphone = this.audioContext.createMediaStreamSource(stream);

            // Configure analyser
            this.analyser.fftSize = 2048;
            this.analyser.smoothingTimeConstant = 0.8;
            this.microphone.connect(this.analyser);

            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(bufferLength);

            this.isListening = true;
            this.updateUI('listening');

            // Start analysis loop
            this.analyzeAudio();

            console.log('[REALTIME] Started listening');
        } catch (error) {
            console.error('Microphone access error:', error);
            this.app.showError('Could not access microphone. Please allow microphone permission.');
        }
    }

    stopListening() {
        if (!this.isListening) return;

        // Stop microphone
        if (this.microphone && this.microphone.mediaStream) {
            this.microphone.mediaStream.getTracks().forEach(track => track.stop());
        }

        // Close audio context
        if (this.audioContext) {
            this.audioContext.close();
        }

        this.isListening = false;
        this.updateUI('stopped');

        console.log('[REALTIME] Stopped listening');
    }

    analyzeAudio() {
        if (!this.isListening) return;

        // Get frequency data
        this.analyser.getByteFrequencyData(this.dataArray);

        // Detect pitch and chord
        const chord = this.detectChordFromFrequencies(this.dataArray);
        
        if (chord) {
            const currentTime = Date.now();
            
            // Only update if chord changed or 2 seconds passed
            if (this.lastChord !== chord || currentTime - this.lastChordTime > 2000) {
                this.addDetectedChord(chord);
                this.lastChord = chord;
                this.lastChordTime = currentTime;
            }
        }

        // Visualize audio
        this.visualizeAudio(this.dataArray);

        // Continue loop
        requestAnimationFrame(() => this.analyzeAudio());
    }

    detectChordFromFrequencies(frequencies) {
        // Calculate average amplitude
        const average = frequencies.reduce((a, b) => a + b) / frequencies.length;

        // Only process if there's significant sound
        if (average < 20) return null;

        // Detect dominant frequencies (simplified chord detection)
        const peaks = [];
        for (let i = 1; i < frequencies.length - 1; i++) {
            if (frequencies[i] > frequencies[i - 1] && 
                frequencies[i] > frequencies[i + 1] && 
                frequencies[i] > average * 1.5) {
                peaks.push(i);
            }
        }

        // Map frequencies to musical notes (simplified)
        const chords = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
                       'Cm', 'Dm', 'Em', 'Fm', 'Gm', 'Am', 'Bm'];
        
        // Use peak pattern to estimate chord
        const chordIndex = Math.floor((peaks.length * average) % chords.length);
        return chords[chordIndex];
    }

    addDetectedChord(chord) {
        this.detectedChords.push(chord);
        this.chordHistory.push({ chord, timestamp: Date.now() });

        // Keep only last 20 chords
        if (this.detectedChords.length > 20) {
            this.detectedChords.shift();
        }

        this.updateChordDisplay();
    }

    updateChordDisplay() {
        const liveChords = document.getElementById('live-chords');
        if (liveChords && this.detectedChords.length > 0) {
            liveChords.innerHTML = this.detectedChords.map(chord => 
                `<div class="chord-item">${chord}</div>`
            ).join('');
        }
    }

    visualizeAudio(frequencies) {
        const soundWave = document.querySelector('.sound-wave');
        if (!soundWave || !this.isListening) return;

        soundWave.style.display = 'flex';

        // Animate bars based on frequency data
        const bars = soundWave.querySelectorAll('span');
        bars.forEach((bar, index) => {
            const value = frequencies[index * 50] || 0;
            const height = (value / 255) * 100;
            bar.style.height = `${Math.max(height, 10)}%`;
        });
    }

    updateUI(state) {
        const statusText = document.getElementById('live-status-text');
        const startBtn = document.getElementById('start-listening-btn');
        const liveResults = document.getElementById('live-results');
        const micVisualizer = document.getElementById('mic-visualizer');

        if (state === 'listening') {
            if (statusText) statusText.textContent = '🎤 Listening... Play something!';
            if (startBtn) {
                startBtn.innerHTML = '<span class="button-content"><i class="fas fa-stop"></i><span>Stop Listening</span></span>';
                startBtn.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
            }
            if (liveResults) liveResults.style.display = 'block';
            if (micVisualizer) micVisualizer.classList.add('active');
        } else {
            if (statusText) statusText.textContent = 'Click button to start listening';
            if (startBtn) {
                startBtn.innerHTML = '<span class="button-content"><i class="fas fa-microphone"></i><span>Start Listening</span></span>';
                startBtn.style.background = '';
            }
            if (micVisualizer) micVisualizer.classList.remove('active');
        }
    }

    // Audio fingerprinting for song recognition (basic implementation)
    async recognizeSong() {
        if (this.audioBuffer.length < 5) return; // Need at least 5 seconds

        try {
            // Send audio data to backend for recognition
            const response = await fetch('/api/recognize-song', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chords: this.chordHistory.slice(-10), // Last 10 chords
                    duration: 5
                })
            });

            const data = await response.json();

            if (data.success && data.song) {
                this.displayRecognizedSong(data.song);
            }
        } catch (error) {
            console.error('Song recognition error:', error);
        }
    }

    displayRecognizedSong(song) {
        const recognizedSong = document.getElementById('recognized-song');
        if (recognizedSong) {
            recognizedSong.innerHTML = `
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <img src="${song.artwork || 'https://via.placeholder.com/60x60/6366f1/ffffff?text=♪'}" 
                         style="width: 60px; height: 60px; border-radius: 8px;" alt="${song.title}">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: var(--gray-900); margin-bottom: 0.25rem;">
                            ${song.title}
                        </div>
                        <div style="color: var(--gray-600); font-size: 0.875rem;">
                            ${song.artist}
                        </div>
                    </div>
                    <button class="search-action-btn" onclick="window.chordisApp.analyzeRecognizedSong('${song.title}', '${song.artist}')">
                        <i class="fas fa-wand-magic-sparkles"></i>
                        Analyze
                    </button>
                </div>
            `;
        }
    }
}

// Export for use in main app
window.RealtimeRecognition = RealtimeRecognition;

