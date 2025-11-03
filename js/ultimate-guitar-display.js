/**
 * Ultimate Guitar Style Display
 * Positions chords above lyrics like Ultimate Guitar tabs
 */

class UltimateGuitarDisplay {
    constructor() {
        this.chordDiagrams = this.initChordDiagrams();
    }

    /**
     * Initialize chord diagram finger positions
     * Format: [string1, string2, string3, string4, string5, string6]
     * x = muted, 0 = open, 1-4 = fret number
     */
    initChordDiagrams() {
        return {
            'C': ['x', '3', '2', '0', '1', '0'],
            'D': ['x', 'x', '0', '2', '3', '2'],
            'E': ['0', '2', '2', '1', '0', '0'],
            'F': ['1', '3', '3', '2', '1', '1'],
            'G': ['3', '2', '0', '0', '0', '3'],
            'A': ['x', '0', '2', '2', '2', '0'],
            'B': ['x', '2', '4', '4', '4', '2'],
            'Am': ['x', '0', '2', '2', '1', '0'],
            'Bm': ['x', '2', '4', '4', '3', '2'],
            'Cm': ['x', '3', '5', '5', '4', '3'],
            'Dm': ['x', 'x', '0', '2', '3', '1'],
            'Em': ['0', '2', '2', '0', '0', '0'],
            'Fm': ['1', '3', '3', '1', '1', '1'],
            'Gm': ['3', '5', '5', '3', '3', '3'],
            'C7': ['x', '3', '2', '3', '1', '0'],
            'D7': ['x', 'x', '0', '2', '1', '2'],
            'E7': ['0', '2', '0', '1', '0', '0'],
            'F7': ['1', '3', '1', '2', '1', '1'],
            'G7': ['3', '2', '0', '0', '0', '1'],
            'A7': ['x', '0', '2', '0', '2', '0'],
            'B7': ['x', '2', '1', '2', '0', '2'],
            'Cmaj7': ['x', '3', '2', '0', '0', '0'],
            'Dmaj7': ['x', 'x', '0', '2', '2', '2'],
            'Emaj7': ['0', '2', '1', '1', '0', '0'],
            'Fmaj7': ['1', '3', '2', '2', '1', '1'],
            'Gmaj7': ['3', '2', '0', '0', '0', '2'],
            'Amaj7': ['x', '0', '2', '1', '2', '0'],
            'Bmaj7': ['x', '2', '4', '3', '4', '2'],
        };
    }

    /**
     * Generate Ultimate Guitar style display
     */
    generate(songData) {
        const { title, artist, chords, lyrics, key, tempo, duration } = songData;
        
        // Get unique chords for diagrams
        const uniqueChords = this.getUniqueChords(chords);
        
        // Merge chords with lyrics
        const mergedLines = this.mergeChordsWithLyrics(chords, lyrics);
        
        return `
            <div class="view-toggle">
                <button class="view-toggle-btn" data-view="timeline">
                    <i class="fas fa-stream"></i>
                    <span>Timeline View</span>
                </button>
                <button class="view-toggle-btn active" data-view="ultimate-guitar">
                    <i class="fas fa-guitar"></i>
                    <span>Guitar Tab View</span>
                </button>
            </div>
            
            <div class="ultimate-guitar-view">
                ${this.generateHeader(title, artist, key, tempo, duration, uniqueChords.length)}
                ${this.generateChordDiagrams(uniqueChords)}
                ${this.generateLyricsWithChords(mergedLines)}
            </div>
        `;
    }

    /**
     * Generate header section
     */
    generateHeader(title, artist, key, tempo, duration, chordCount) {
        return `
            <div class="ug-header">
                <h2 class="ug-song-title">${title || 'Unknown Song'}</h2>
                <p class="ug-artist">${artist || 'Unknown Artist'}</p>
                <div class="ug-meta">
                    <div class="ug-meta-item">
                        <i class="fas fa-key"></i>
                        <span>Key: ${key || 'C Major'}</span>
                    </div>
                    <div class="ug-meta-item">
                        <i class="fas fa-drum"></i>
                        <span>Tempo: ${tempo || 120} BPM</span>
                    </div>
                    <div class="ug-meta-item">
                        <i class="fas fa-clock"></i>
                        <span>Duration: ${this.formatDuration(duration)}</span>
                    </div>
                    <div class="ug-meta-item">
                        <i class="fas fa-guitar"></i>
                        <span>${chordCount} Chords</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate chord diagrams
     */
    generateChordDiagrams(chords) {
        return `
            <div class="ug-chord-diagrams">
                ${chords.map(chord => this.generateChordDiagram(chord)).join('')}
            </div>
        `;
    }

    /**
     * Generate individual chord diagram
     */
    generateChordDiagram(chordName) {
        const diagram = this.chordDiagrams[chordName] || ['x', 'x', 'x', 'x', 'x', 'x'];
        
        return `
            <div class="chord-diagram">
                <div class="chord-diagram-name">${chordName}</div>
                <div class="chord-diagram-grid">
                    ${diagram.map((fret, string) => {
                        if (fret === 'x' || fret === '0') return '';
                        const row = parseInt(fret);
                        return `<div class="chord-diagram-dot" style="grid-column: ${string + 1}; grid-row: ${row};"></div>`;
                    }).join('')}
                </div>
                <div style="font-size: 10px; color: var(--gray-500); font-family: monospace;">
                    ${diagram.join(' ')}
                </div>
            </div>
        `;
    }

    /**
     * Generate lyrics with chords positioned above
     */
    generateLyricsWithChords(lines) {
        return `
            <div class="ug-lyrics">
                ${lines.map((line, index) => this.generateLine(line, index)).join('')}
            </div>
        `;
    }

    /**
     * Generate a single line with chords above
     */
    generateLine(line, index) {
        if (line.type === 'section') {
            return `<div class="ug-section">${line.text}</div>`;
        }

        const { chordsRow, lyricsRow } = this.alignChordsWithLyrics(line);
        
        return `
            <div class="ug-line" data-line="${index}">
                ${chordsRow ? `<div class="ug-chords-row">${chordsRow}</div>` : ''}
                <div class="ug-lyrics-row">${lyricsRow || '&nbsp;'}</div>
            </div>
        `;
    }

    /**
     * Align chords with lyrics text
     */
    alignChordsWithLyrics(line) {
        if (!line.chords || line.chords.length === 0) {
            return {
                chordsRow: '',
                lyricsRow: line.text || ''
            };
        }

        const lyrics = line.text || '';
        const chords = line.chords.sort((a, b) => a.position - b.position);
        
        let chordsRow = '';
        let lastPos = 0;
        
        // Build chords row with proper spacing
        chords.forEach(chord => {
            const pos = chord.position || 0;
            // Add spaces to align chord
            chordsRow += ' '.repeat(Math.max(0, pos - lastPos));
            chordsRow += chord.name;
            lastPos = pos + chord.name.length;
        });
        
        return {
            chordsRow,
            lyricsRow: lyrics
        };
    }

    /**
     * Merge chords with lyrics based on timestamps
     */
    mergeChordsWithLyrics(chords, lyrics) {
        const lines = [];
        
        // Split lyrics into lines
        let lyricsLines = [];
        if (typeof lyrics === 'string') {
            lyricsLines = lyrics.split('\n');
        } else if (Array.isArray(lyrics)) {
            lyricsLines = lyrics.map(l => l.text || l);
        }

        // If we have chords array with timestamps
        if (Array.isArray(chords)) {
            let currentLineChords = [];
            let currentLineIndex = 0;
            const lineDuration = chords.length > 0 && lyricsLines.length > 0 
                ? (chords[chords.length - 1].start_time || 180) / lyricsLines.length 
                : 10;

            chords.forEach(chord => {
                const chordName = chord.chord || chord.name || chord;
                const timestamp = chord.start_time || chord.timestamp || 0;
                const lineIndex = Math.floor(timestamp / lineDuration);
                
                if (lineIndex !== currentLineIndex) {
                    // Push previous line
                    if (currentLineIndex < lyricsLines.length) {
                        lines.push({
                            type: 'lyric',
                            text: lyricsLines[currentLineIndex],
                            chords: [...currentLineChords]
                        });
                    }
                    currentLineChords = [];
                    currentLineIndex = lineIndex;
                }
                
                // Estimate position in line (rough approximation)
                const posInLine = Math.floor((timestamp % lineDuration) / lineDuration * 40);
                currentLineChords.push({
                    name: chordName,
                    position: posInLine,
                    timestamp: timestamp
                });
            });

            // Push remaining lyrics lines
            for (let i = currentLineIndex; i < lyricsLines.length; i++) {
                lines.push({
                    type: 'lyric',
                    text: lyricsLines[i],
                    chords: i === currentLineIndex ? currentLineChords : []
                });
            }
        } else {
            // No chords, just lyrics
            lyricsLines.forEach(line => {
                lines.push({
                    type: 'lyric',
                    text: line,
                    chords: []
                });
            });
        }

        // Detect sections (Verse, Chorus, etc.)
        return this.detectSections(lines);
    }

    /**
     * Detect and add section markers
     */
    detectSections(lines) {
        const result = [];
        let inSection = false;

        lines.forEach((line, index) => {
            const text = (line.text || '').trim().toLowerCase();
            
            // Check if line is a section marker
            if (text.match(/^\[(verse|chorus|bridge|intro|outro|pre-chorus|hook)\]/i)) {
                result.push({
                    type: 'section',
                    text: text.replace(/^\[|\]$/g, '')
                });
                inSection = true;
            } else {
                result.push(line);
            }
        });

        return result;
    }

    /**
     * Get unique chords from chord progression
     */
    getUniqueChords(chords) {
        if (!Array.isArray(chords)) return [];
        
        const unique = new Set();
        chords.forEach(chord => {
            const name = chord.chord || chord.name || chord;
            if (name && typeof name === 'string') {
                unique.add(name);
            }
        });
        
        return Array.from(unique).sort();
    }

    /**
     * Format duration
     */
    formatDuration(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Highlight active chord during playback
     */
    highlightChord(timestamp) {
        // Remove previous highlights
        document.querySelectorAll('.ug-line.active, .ug-chord-inline.active').forEach(el => {
            el.classList.remove('active');
        });

        // Find and highlight current chord
        const lines = document.querySelectorAll('.ug-line');
        lines.forEach(line => {
            const chords = line.querySelectorAll('.ug-chord-inline');
            chords.forEach(chord => {
                const chordTime = parseFloat(chord.dataset.timestamp || 0);
                if (Math.abs(chordTime - timestamp) < 1) {
                    chord.classList.add('active');
                    line.classList.add('active');
                }
            });
        });
    }
}

// Export for use in main app
window.UltimateGuitarDisplay = UltimateGuitarDisplay;

