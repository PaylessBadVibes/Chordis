/**
 * Ultimate Guitar Style Display
 * Displays chords above lyrics with instrument tabs, chord diagrams, and strumming patterns
 * Clean, professional layout like https://tabs.ultimate-guitar.com/
 */

class IntegratedSheetDisplay {
    constructor() {
        this.currentInstrument = 'guitar';
        this.diagramsVisible = true;
        this.strummingVisible = true;
        
        // Initialize chord data for multiple instruments
        this.chordData = {
            guitar: this.initGuitarChords(),
            ukulele: this.initUkuleleChords(),
            piano: this.initPianoChords()
        };
        
        // Common strumming patterns
        this.strummingPatterns = this.initStrummingPatterns();
    }

    /**
     * Guitar chord data: [E, A, D, G, B, e] strings, -1 = muted, 0 = open
     */
    initGuitarChords() {
        return {
            'C': { frets: [-1, 3, 2, 0, 1, 0], fingers: [0, 3, 2, 0, 1, 0] },
            'D': { frets: [-1, -1, 0, 2, 3, 2], fingers: [0, 0, 0, 1, 3, 2] },
            'Dm': { frets: [-1, -1, 0, 2, 3, 1], fingers: [0, 0, 0, 2, 3, 1] },
            'Dmaj7': { frets: [-1, -1, 0, 2, 2, 2], fingers: [0, 0, 0, 1, 1, 1] },
            'Dsus4': { frets: [-1, -1, 0, 2, 3, 3], fingers: [0, 0, 0, 1, 2, 3] },
            'Daug': { frets: [-1, -1, 0, 3, 3, 2], fingers: [0, 0, 0, 2, 3, 1] },
            'E': { frets: [0, 2, 2, 1, 0, 0], fingers: [0, 2, 3, 1, 0, 0] },
            'Em': { frets: [0, 2, 2, 0, 0, 0], fingers: [0, 2, 3, 0, 0, 0] },
            'F': { frets: [1, 3, 3, 2, 1, 1], fingers: [1, 3, 4, 2, 1, 1], barre: 1 },
            'G': { frets: [3, 2, 0, 0, 0, 3], fingers: [2, 1, 0, 0, 0, 3] },
            'Gm': { frets: [3, 5, 5, 3, 3, 3], fingers: [1, 3, 4, 1, 1, 1], barre: 3 },
            'Gmaj7': { frets: [3, 2, 0, 0, 0, 2], fingers: [3, 2, 0, 0, 0, 1] },
            'Gsus4': { frets: [3, 3, 0, 0, 1, 3], fingers: [2, 3, 0, 0, 1, 4] },
            'A': { frets: [-1, 0, 2, 2, 2, 0], fingers: [0, 0, 1, 2, 3, 0] },
            'Am': { frets: [-1, 0, 2, 2, 1, 0], fingers: [0, 0, 2, 3, 1, 0] },
            'A#': { frets: [-1, 1, 3, 3, 3, 1], fingers: [0, 1, 2, 3, 4, 1], barre: 1 },
            'B': { frets: [-1, 2, 4, 4, 4, 2], fingers: [0, 1, 2, 3, 4, 1], barre: 2 },
            'Bm': { frets: [-1, 2, 4, 4, 3, 2], fingers: [0, 1, 3, 4, 2, 1], barre: 2 },
            'Cm': { frets: [-1, 3, 5, 5, 4, 3], fingers: [0, 1, 3, 4, 2, 1], barre: 3 },
            'Cm7': { frets: [-1, 3, 5, 3, 4, 3], fingers: [0, 1, 3, 1, 2, 1], barre: 3 },
            'Cdim': { frets: [-1, 3, 4, 2, 4, 2], fingers: [0, 2, 3, 1, 4, 1] },
            'C7': { frets: [-1, 3, 2, 3, 1, 0], fingers: [0, 3, 2, 4, 1, 0] },
            'D7': { frets: [-1, -1, 0, 2, 1, 2], fingers: [0, 0, 0, 2, 1, 3] },
            'E7': { frets: [0, 2, 0, 1, 0, 0], fingers: [0, 2, 0, 1, 0, 0] },
            'G7': { frets: [3, 2, 0, 0, 0, 1], fingers: [3, 2, 0, 0, 0, 1] },
            'A7': { frets: [-1, 0, 2, 0, 2, 0], fingers: [0, 0, 1, 0, 2, 0] },
            'Am7': { frets: [-1, 0, 2, 0, 1, 0], fingers: [0, 0, 2, 0, 1, 0] },
            'F#m': { frets: [2, 4, 4, 2, 2, 2], fingers: [1, 3, 4, 1, 1, 1], barre: 2 },
            'C#m': { frets: [-1, 4, 6, 6, 5, 4], fingers: [0, 1, 3, 4, 2, 1], barre: 4 },
        };
    }

    /**
     * Ukulele chord data: [G, C, E, A] strings
     */
    initUkuleleChords() {
        return {
            'C': { frets: [0, 0, 0, 3] },
            'D': { frets: [2, 2, 2, 0] },
            'Dm': { frets: [2, 2, 1, 0] },
            'E': { frets: [1, 4, 0, 2] },
            'Em': { frets: [0, 4, 3, 2] },
            'F': { frets: [2, 0, 1, 0] },
            'G': { frets: [0, 2, 3, 2] },
            'Gm': { frets: [0, 2, 3, 1] },
            'A': { frets: [2, 1, 0, 0] },
            'Am': { frets: [2, 0, 0, 0] },
            'B': { frets: [4, 3, 2, 2] },
            'Bm': { frets: [4, 2, 2, 2] },
        };
    }

    /**
     * Piano chord notes
     */
    initPianoChords() {
        return {
            'C': ['C', 'E', 'G'],
            'Cm': ['C', 'Eb', 'G'],
            'D': ['D', 'F#', 'A'],
            'Dm': ['D', 'F', 'A'],
            'E': ['E', 'G#', 'B'],
            'Em': ['E', 'G', 'B'],
            'F': ['F', 'A', 'C'],
            'G': ['G', 'B', 'D'],
            'Gm': ['G', 'Bb', 'D'],
            'A': ['A', 'C#', 'E'],
            'Am': ['A', 'C', 'E'],
            'B': ['B', 'D#', 'F#'],
            'Bm': ['B', 'D', 'F#'],
        };
    }

    initStrummingPatterns() {
        return {
            'basic': { name: 'Basic', pattern: ['D', 'D', 'D', 'D'], bpm: 120 },
            'folk': { name: 'Folk', pattern: ['D', '-', 'D', 'U', '-', 'U', 'D', 'U'], bpm: 100 },
            'pop': { name: 'Pop', pattern: ['D', '-', 'U', '-', 'D', 'U', '-', 'U'], bpm: 120 },
            'ballad': { name: 'Ballad', pattern: ['D', '-', '-', 'U', 'D', 'U', '-', 'U'], bpm: 80 },
        };
    }

    detectStrummingPattern(tempo) {
        if (!tempo) tempo = 120;
        if (tempo < 80) return 'ballad';
        if (tempo > 140) return 'basic';
        return tempo < 110 ? 'folk' : 'pop';
    }

    /**
     * Main generate function
     */
    generate(songData) {
        const { title, artist, chords, lyrics, key, tempo, duration, tuning, capo } = songData;
        const uniqueChords = this.getUniqueChords(chords);
        const strumPattern = this.detectStrummingPattern(tempo);
        const mergedLines = this.mergeChordsWithLyrics(chords, lyrics);
        
        return `
            <div class="ug-container">
                ${this.generateHeader(title, artist, key, tempo, duration, uniqueChords.length, tuning, capo)}
                ${this.generateInstrumentTabs()}
                ${this.generateChordDiagrams(uniqueChords)}
                ${this.generateStrummingPattern(strumPattern, tempo)}
                <div class="ug-content">
                    ${this.generateLyricsWithChords(mergedLines)}
                </div>
            </div>
        `;
    }

    generateHeader(title, artist, key, tempo, duration, chordCount, tuning, capo) {
        // Store song data for PDF export
        this.currentSongData = { title, artist, key, tempo, duration, tuning, capo };
        
        return `
            <div class="ug-header">
                <div class="ug-header-top">
                    <div>
                        <h1 class="ug-title">${title || 'Unknown Song'} Chords</h1>
                        <p class="ug-artist">by ${artist || 'Unknown Artist'}</p>
                    </div>
                    <button class="ug-download-btn" onclick="window.sheetDisplay?.downloadPDF()">
                        📥 Download PDF
                    </button>
                </div>
                <div class="ug-meta">
                    <span><strong>Tuning:</strong> ${tuning || 'E A D G B E'}</span>
                    <span><strong>Key:</strong> ${key || 'C Major'}</span>
                    <span><strong>Capo:</strong> ${capo || 'no capo'}</span>
                </div>
                <div class="ug-stats">
                    <span>🎵 ${chordCount} chords</span>
                    <span>🥁 ${tempo || 120} BPM</span>
                    <span>⏱️ ${this.formatDuration(duration)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Download chord sheet as PDF
     */
    downloadPDF() {
        const container = document.querySelector('.ug-container');
        if (container && window.ChordPDFExport) {
            window.ChordPDFExport.downloadPDF(this.currentSongData, container);
        } else {
            // Fallback: use browser print
            window.print();
        }
    }

    generateInstrumentTabs() {
        return `
            <div class="ug-tabs">
                <span class="ug-tabs-label">Chords ↔</span>
                <div class="ug-tabs-buttons">
                    <button class="ug-tab ${this.currentInstrument === 'guitar' ? 'active' : ''}" 
                            onclick="window.sheetDisplay?.setInstrument('guitar')">🎸 Guitar</button>
                    <button class="ug-tab ${this.currentInstrument === 'ukulele' ? 'active' : ''}" 
                            onclick="window.sheetDisplay?.setInstrument('ukulele')">🪕 Ukulele</button>
                    <button class="ug-tab ${this.currentInstrument === 'piano' ? 'active' : ''}" 
                            onclick="window.sheetDisplay?.setInstrument('piano')">🎹 Piano</button>
                </div>
            </div>
        `;
    }

    setInstrument(instrument) {
        this.currentInstrument = instrument;
        document.querySelectorAll('.ug-tab').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`.ug-tab:nth-child(${instrument === 'guitar' ? 1 : instrument === 'ukulele' ? 2 : 3})`)?.classList.add('active');
        
        const container = document.getElementById('ug-diagrams');
        if (container) {
            const chords = Array.from(container.querySelectorAll('.ug-chord-box')).map(el => el.dataset.chord);
            container.innerHTML = chords.map(chord => this.generateChordDiagram(chord)).join('');
        }
    }

    generateChordDiagrams(chords) {
        if (!chords || chords.length === 0) return '';
        
        return `
            <div class="ug-diagrams" id="ug-diagrams">
                ${chords.map(chord => this.generateChordDiagram(chord)).join('')}
            </div>
        `;
    }

    generateChordDiagram(chordName) {
        if (this.currentInstrument === 'piano') {
            return this.generatePianoDiagram(chordName);
        }
        return this.generateFretboardDiagram(chordName);
    }

    /**
     * Generate SVG fretboard diagram for guitar/ukulele
     */
    generateFretboardDiagram(chordName) {
        const isUkulele = this.currentInstrument === 'ukulele';
        const chordData = this.chordData[this.currentInstrument]?.[chordName];
        const stringCount = isUkulele ? 4 : 6;
        const fretCount = 4;
        
        const width = isUkulele ? 60 : 80;
        const height = 90;
        const stringSpacing = (width - 20) / (stringCount - 1);
        const fretSpacing = 18;
        const topPadding = 20;
        const leftPadding = 10;
        
        let svg = `<svg class="chord-svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">`;
        
        // Draw nut (top bar)
        svg += `<rect x="${leftPadding}" y="${topPadding}" width="${(stringCount-1) * stringSpacing}" height="3" fill="#333"/>`;
        
        // Draw frets (horizontal lines)
        for (let i = 1; i <= fretCount; i++) {
            svg += `<line x1="${leftPadding}" y1="${topPadding + i * fretSpacing}" 
                         x2="${leftPadding + (stringCount-1) * stringSpacing}" y2="${topPadding + i * fretSpacing}" 
                         stroke="#666" stroke-width="1"/>`;
        }
        
        // Draw strings (vertical lines)
        for (let i = 0; i < stringCount; i++) {
            svg += `<line x1="${leftPadding + i * stringSpacing}" y1="${topPadding}" 
                         x2="${leftPadding + i * stringSpacing}" y2="${topPadding + fretCount * fretSpacing}" 
                         stroke="#999" stroke-width="1"/>`;
        }
        
        // Draw finger positions
        if (chordData && chordData.frets) {
            chordData.frets.forEach((fret, stringIndex) => {
                const x = leftPadding + stringIndex * stringSpacing;
                
                if (fret === -1) {
                    // Muted string (X)
                    svg += `<text x="${x}" y="${topPadding - 5}" text-anchor="middle" font-size="10" fill="#e53935">×</text>`;
                } else if (fret === 0) {
                    // Open string (O)
                    svg += `<text x="${x}" y="${topPadding - 5}" text-anchor="middle" font-size="10" fill="#43a047">○</text>`;
                } else {
                    // Fretted note (filled circle)
                    const y = topPadding + (fret - 0.5) * fretSpacing;
                    svg += `<circle cx="${x}" cy="${y}" r="6" fill="#1976d2"/>`;
                    
                    // Finger number if available
                    if (chordData.fingers && chordData.fingers[stringIndex] > 0) {
                        svg += `<text x="${x}" y="${y + 3}" text-anchor="middle" font-size="8" fill="white" font-weight="bold">
                                    ${chordData.fingers[stringIndex]}</text>`;
                    }
                }
            });
            
            // Draw barre if present
            if (chordData.barre) {
                const barreY = topPadding + (chordData.barre - 0.5) * fretSpacing;
                const startX = leftPadding;
                const endX = leftPadding + (stringCount - 1) * stringSpacing;
                svg += `<line x1="${startX}" y1="${barreY}" x2="${endX}" y2="${barreY}" 
                             stroke="#1976d2" stroke-width="10" stroke-linecap="round" opacity="0.8"/>`;
            }
        } else {
            // Unknown chord - show question mark
            svg += `<text x="${width/2}" y="${topPadding + 35}" text-anchor="middle" font-size="16" fill="#999">?</text>`;
        }
        
        svg += '</svg>';
        
        return `
            <div class="ug-chord-box" data-chord="${chordName}">
                <div class="ug-chord-name">${chordName}</div>
                ${svg}
            </div>
        `;
    }

    /**
     * Generate piano diagram
     */
    generatePianoDiagram(chordName) {
        const notes = this.chordData.piano[chordName] || [];
        const allNotes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const whiteNotes = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
        const blackNotes = ['C#', 'D#', 'F#', 'G#', 'A#'];
        
        const isActive = (note) => notes.some(n => 
            n === note || n.replace('b', '#') === note || 
            (n === 'Eb' && note === 'D#') || (n === 'Bb' && note === 'A#') ||
            (n === 'Ab' && note === 'G#') || (n === 'Db' && note === 'C#') ||
            (n === 'Gb' && note === 'F#')
        );
        
        let html = `
            <div class="ug-chord-box piano" data-chord="${chordName}">
                <div class="ug-chord-name">${chordName}</div>
                <div class="piano-keyboard">
        `;
        
        // White keys
        whiteNotes.forEach((note, i) => {
            html += `<div class="piano-white ${isActive(note) ? 'active' : ''}">${isActive(note) ? '●' : ''}</div>`;
        });
        
        // Black keys (positioned absolutely)
        const blackPositions = [0, 1, 3, 4, 5]; // C#, D#, F#, G#, A#
        blackNotes.forEach((note, i) => {
            const left = blackPositions[i] * 16 + 11;
            html += `<div class="piano-black ${isActive(note) ? 'active' : ''}" style="left:${left}px">${isActive(note) ? '●' : ''}</div>`;
        });
        
        html += `
                </div>
                <div class="piano-notes">${notes.join(' ')}</div>
            </div>
        `;
        
        return html;
    }

    generateStrummingPattern(patternKey, tempo) {
        const pattern = this.strummingPatterns[patternKey] || this.strummingPatterns['folk'];
        
        return `
            <div class="ug-strumming">
                <div class="ug-strumming-header">
                    <span>Strumming pattern</span>
                    <span class="ug-strumming-bpm">${tempo || pattern.bpm} bpm</span>
                </div>
                <div class="ug-strumming-visual">
                    ${pattern.pattern.map(s => 
                        `<span class="strum ${s === 'D' ? 'down' : s === 'U' ? 'up' : 'rest'}">${s === 'D' ? '↓' : s === 'U' ? '↑' : '·'}</span>`
                    ).join('')}
                </div>
                <div class="ug-strumming-counts">
                    ${['1', '&', '2', '&', '3', '&', '4', '&'].slice(0, pattern.pattern.length).map(c => 
                        `<span>${c}</span>`
                    ).join('')}
                </div>
            </div>
        `;
    }

    generateLyricsWithChords(lines) {
        return lines.map((line, i) => this.generateLine(line, i)).join('');
    }

    generateLine(line, index) {
        if (line.type === 'section') {
            return `<div class="ug-section">[${line.text}]</div>`;
        }

        const { chordsRow, lyricsRow } = this.alignChordsWithLyrics(line);
        
        if (!chordsRow && !lyricsRow.trim()) {
            return '<div class="ug-line-empty"></div>';
        }
        
        return `
            <div class="ug-line">
                ${chordsRow ? `<div class="ug-chords">${chordsRow}</div>` : ''}
                <div class="ug-lyrics">${lyricsRow || ''}</div>
            </div>
        `;
    }

    alignChordsWithLyrics(line) {
        if (!line.chords || line.chords.length === 0) {
            return { chordsRow: '', lyricsRow: line.text || '' };
        }

        const lyrics = line.text || '';
        const chords = line.chords.sort((a, b) => (a.position || 0) - (b.position || 0));
        
        let chordsHTML = '';
        let lastPos = 0;
        
        chords.forEach((chord) => {
            const pos = chord.position || 0;
            const spacing = Math.max(0, pos - lastPos);
            if (spacing > 0) {
                chordsHTML += ' '.repeat(spacing);
            }
            // Use ug-chord class for Ultimate Guitar style (plain text, not pills)
            chordsHTML += `<span class="ug-chord">${chord.name}</span>`;
            lastPos = pos + chord.name.length;
        });
        
        return { chordsRow: chordsHTML, lyricsRow: lyrics };
    }

    mergeChordsWithLyrics(chords, lyrics) {
        const lines = [];
        let lyricsLines = [];
        
        if (typeof lyrics === 'string') {
            lyricsLines = lyrics.split('\n');
        } else if (Array.isArray(lyrics)) {
            lyricsLines = lyrics.map(l => l.text || l);
        }

        if (lyricsLines.length === 0) lyricsLines = [''];

        if (Array.isArray(chords) && chords.length > 0) {
            const maxTimestamp = Math.max(...chords.map(c => c.start_time || c.timestamp || c.time || 0));
            const lineDuration = maxTimestamp === 0 ? 4 : maxTimestamp / Math.max(lyricsLines.length, 1);
            
            const lineChordMap = new Map();
            lyricsLines.forEach((_, i) => lineChordMap.set(i, []));

            chords.forEach((chord, idx) => {
                const chordName = chord.chord || chord.name || chord;
                let timestamp = chord.start_time || chord.timestamp || chord.time || (maxTimestamp === 0 ? idx * lineDuration : 0);
                
                let lineIndex = Math.floor(timestamp / lineDuration);
                lineIndex = Math.min(Math.max(0, lineIndex), lyricsLines.length - 1);
                
                const lineText = lyricsLines[lineIndex] || '';
                const percentIntoLine = lineDuration > 0 ? ((timestamp % lineDuration) / lineDuration) : 0;
                const charPosition = Math.floor(percentIntoLine * Math.max(lineText.length, 40));
                
                lineChordMap.get(lineIndex)?.push({ name: chordName, position: charPosition, timestamp });
            });

            lyricsLines.forEach((text, index) => {
                lines.push({ type: 'lyric', text, chords: lineChordMap.get(index) || [], timestamp: index * lineDuration });
            });
        } else {
            lyricsLines.forEach((line, index) => {
                lines.push({ type: 'lyric', text: line, chords: [], timestamp: index * 5 });
            });
        }

        return this.detectSections(lines);
    }

    detectSections(lines) {
        const result = [];
        const sectionPatterns = [
            /^\s*\[(verse|chorus|bridge|intro|outro|pre-chorus|hook|interlude|solo|note|chords?)(\s*\d*)?\]\s*$/i,
            /^\s*(verse|chorus|bridge|intro|outro|hook)(\s*\d*)?\s*:?\s*$/i,
        ];

        lines.forEach((line) => {
            const text = (line.text || '').trim();
            let isSection = false;
            let sectionName = '';
            
            for (const pattern of sectionPatterns) {
                const match = text.match(pattern);
                if (match) {
                    isSection = true;
                    sectionName = (match[1] + (match[2] || '')).trim();
                    sectionName = sectionName.charAt(0).toUpperCase() + sectionName.slice(1).toLowerCase();
                    break;
                }
            }
            
            if (isSection) {
                result.push({ type: 'section', text: sectionName });
            } else {
                result.push(line);
            }
        });

        return result;
    }

    getUniqueChords(chords) {
        if (!Array.isArray(chords)) return [];
        const unique = new Set();
        chords.forEach(chord => {
            const name = chord.chord || chord.name || chord;
            if (name && typeof name === 'string') unique.add(name);
        });
        return Array.from(unique).sort();
    }

    formatDuration(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    highlightChord(timestamp) {
        document.querySelectorAll('.ug-line.active, .ug-chord.active').forEach(el => el.classList.remove('active'));
        
        document.querySelectorAll('.ug-line').forEach(line => {
            const chords = line.querySelectorAll('.ug-chord');
            chords.forEach(chord => {
                const chordTime = parseFloat(chord.dataset.timestamp || 0);
                if (Math.abs(chordTime - timestamp) < 2) {
                    chord.classList.add('active');
                    line.classList.add('active');
                }
            });
        });
    }
}

// Export
window.IntegratedSheetDisplay = IntegratedSheetDisplay;
window.UltimateGuitarDisplay = IntegratedSheetDisplay;
window.sheetDisplay = new IntegratedSheetDisplay();
