# 🎵 Chordis - AI Music Analysis

AI-powered music analysis tool that extracts chords and lyrics from any song using deep learning.

## Features

- 🔍 **Search Songs** - Find any song and get instant chords & lyrics
- 🎸 **AI Chord Detection** - Deep learning model detects chords with timing
- 📝 **Lyrics Transcription** - Genius API + Whisper AI for lyrics
- 🎵 **YouTube Analysis** - Analyze any YouTube video
- 📁 **File Upload** - Upload your own audio files
- 🎤 **Real-time Recognition** - Identify songs playing around you
- 💾 **Library** - Save analyzed songs for later
- 📚 **Tutorials** - Learn guitar with built-in video tutorials

## Quick Start (Local Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python api.py

# Access at http://localhost:5000/
```

## Deploy to Railway.app

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/YOUR_USERNAME/chordis)

### Manual Deployment

1. **Push to GitHub**
2. **Go to Railway.app** → "New Project" → "Deploy from GitHub"
3. **Select your repository**
4. **Add environment variables** (see `.env.example`)
5. **Deploy!**

Railway will automatically:
- Install Python dependencies
- Run database migrations
- Start the web server
- Give you a public URL

## Environment Variables for Railway

### Required:
- `GENIUS_ACCESS_TOKEN` - Get from https://genius.com/api-clients
- `SECRET_KEY` - Random string for Flask sessions

### Optional:
- `ACRCLOUD_ACCESS_KEY` - For song recognition
- `FLASK_ENV=production` - Production mode

## Tech Stack

- **Backend**: Python, Flask
- **AI Models**: PyTorch, Whisper, Custom CNN
- **Database**: SQLite (local) / PostgreSQL (production)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **APIs**: Genius, ACRCloud, AudD, YouTube (yt-dlp)

## License

MIT License - Feel free to use for your projects!

## Support

Found a bug? Please report it!
Want to contribute? Pull requests welcome!



