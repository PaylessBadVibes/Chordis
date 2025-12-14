from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, Response, stream_with_context
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from functools import wraps
import os
import tempfile
import torch
import librosa
import soundfile as sf
import yt_dlp
import whisper
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import requests
import hashlib
import hmac
import base64
import time
import json

# Try to import lyricsgenius (optional)
try:
    import lyricsgenius
    GENIUS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import lyricsgenius: {e}")
    GENIUS_AVAILABLE = False
    lyricsgenius = None

# Try to import pydub for audio format conversion (optional)
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import pydub: {e}")
    print("Install with: pip install pydub")
    print("Note: pydub requires FFmpeg to be installed on your system")
    PYDUB_AVAILABLE = False
    AudioSegment = None

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Database models
from models import db, User, SavedAnalysis, Tutorial, SearchLog, SongRecognitionLog, AnalysisActivityLog

# Assuming the core prediction logic is here
from chord_recognition.utils import preprocess_audio
from chord_recognition.model import CNNModel
from chord_recognition.constants import CHORDS

# ============================================
# AUDIO CACHE CONFIGURATION
# ============================================
AUDIO_CACHE_DIR = Path('temp/audio_cache')
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DURATION_HOURS = 2  # Cache audio files for 2 hours

# ============================================
# CHORDMINIAPP CONFIGURATION
# ============================================
# ChordMiniApp provides ML-based chord detection with 301 chord types
# GitHub: https://github.com/ptnghia-j/ChordMiniApp
# Use 127.0.0.1 for same-container communication (Railway)
CHORDMINI_API_URL = os.getenv('CHORDMINI_API_URL', 'http://127.0.0.1:5001')
CHORDMINI_TIMEOUT = int(os.getenv('CHORDMINI_TIMEOUT', '120'))  # seconds
# Disable ChordMini by default in production (Railway) - use rule-based detection
IS_RAILWAY = bool(os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_SERVICE_NAME'))
CHORDMINI_ENABLED = os.getenv('CHORDMINI_ENABLED', 'false' if IS_RAILWAY else 'true').lower() == 'true'

# Circuit breaker state for ChordMiniApp
chordmini_circuit_breaker = {
    'failures': 0,
    'last_failure': None,
    'open': False,
    'cooldown_seconds': 60
}

def is_chordmini_available():
    """Check if ChordMiniApp service is available with circuit breaker pattern"""
    global chordmini_circuit_breaker
    
    if not CHORDMINI_ENABLED:
        return False
    
    # Check circuit breaker
    if chordmini_circuit_breaker['open']:
        if chordmini_circuit_breaker['last_failure']:
            elapsed = (datetime.now() - chordmini_circuit_breaker['last_failure']).total_seconds()
            if elapsed < chordmini_circuit_breaker['cooldown_seconds']:
                print(f"[CHORDMINI] Circuit breaker open, {chordmini_circuit_breaker['cooldown_seconds'] - elapsed:.0f}s until retry")
                return False
            else:
                # Reset circuit breaker for retry
                chordmini_circuit_breaker['open'] = False
                chordmini_circuit_breaker['failures'] = 0
    
    try:
        response = requests.get(f"{CHORDMINI_API_URL}/health", timeout=5)
        if response.status_code == 200:
            chordmini_circuit_breaker['failures'] = 0
            chordmini_circuit_breaker['open'] = False
            return True
    except requests.exceptions.RequestException:
        pass
    
    # Try root endpoint as fallback health check
    try:
        response = requests.get(f"{CHORDMINI_API_URL}/", timeout=5)
        if response.status_code in [200, 404]:  # Server is responding
            chordmini_circuit_breaker['failures'] = 0
            chordmini_circuit_breaker['open'] = False
            return True
    except requests.exceptions.RequestException:
        pass
    
    return False


def record_chordmini_failure():
    """Record a ChordMiniApp failure for circuit breaker"""
    global chordmini_circuit_breaker
    chordmini_circuit_breaker['failures'] += 1
    chordmini_circuit_breaker['last_failure'] = datetime.now()
    
    if chordmini_circuit_breaker['failures'] >= 3:
        chordmini_circuit_breaker['open'] = True
        print(f"[CHORDMINI] Circuit breaker OPEN after {chordmini_circuit_breaker['failures']} failures")


def normalize_chord_name(chord_name):
    """
    Normalize chord notation from ChordMiniApp format to standard format
    
    ChordMiniApp uses notation like:
    - "C:maj" -> "C"
    - "C:min" -> "Cm"
    - "C:maj7" -> "Cmaj7"
    - "C:min7" -> "Cm7"
    - "N" -> "N" (no chord)
    """
    if not chord_name or chord_name == 'N':
        return 'N'
    
    # Handle colon notation (C:min -> Cm)
    if ':' in chord_name:
        parts = chord_name.split(':')
        root = parts[0]
        quality = parts[1] if len(parts) > 1 else ''
        
        # Map quality names to standard notation
        quality_map = {
            'maj': '',
            'min': 'm',
            'minor': 'm',
            'major': '',
            'dim': 'dim',
            'aug': 'aug',
            'sus4': 'sus4',
            'sus2': 'sus2',
            'maj7': 'maj7',
            'min7': 'm7',
            '7': '7',
            'dim7': 'dim7',
            'hdim7': 'm7b5',
            'minmaj7': 'mMaj7',
            '9': '9',
            'maj9': 'maj9',
            'min9': 'm9',
            'add9': 'add9',
            '11': '11',
            '13': '13',
        }
        
        normalized_quality = quality_map.get(quality.lower(), quality)
        return f"{root}{normalized_quality}"
    
    return chord_name


def transform_chordmini_response(response_data):
    """
    Transform ChordMiniApp response to our chord format
    
    ChordMiniApp format may vary, this handles common formats:
    - List of {chord, start, end} objects
    - Dict with 'chords' key containing list
    """
    chords = []
    
    # Handle different response formats
    if isinstance(response_data, list):
        chord_list = response_data
    elif isinstance(response_data, dict):
        chord_list = response_data.get('chords', response_data.get('progression', []))
    else:
        print(f"[CHORDMINI] Unknown response format: {type(response_data)}")
        return []
    
    for i, item in enumerate(chord_list):
        if isinstance(item, dict):
            # Extract chord name (handle different key names)
            chord_name = item.get('chord', item.get('name', item.get('label', 'N')))
            
            # Clean up chord notation (ChordMiniApp may use "C:min" format)
            chord_name = normalize_chord_name(chord_name)
            
            # Skip "no chord" entries
            if chord_name == 'N':
                continue
            
            # Extract timing
            start_time = float(item.get('start', item.get('start_time', item.get('timestamp', i * 2))))
            end_time = float(item.get('end', item.get('end_time', start_time + 2)))
            
            chords.append({
                'chord': chord_name,
                'name': chord_name,
                'start_time': round(start_time, 2),
                'end_time': round(end_time, 2),
                'timestamp': round(start_time, 2),
                'source': 'chordmini'
            })
        elif isinstance(item, str):
            # Simple string chord names
            chord_name = normalize_chord_name(item)
            if chord_name != 'N':
                chords.append({
                    'chord': chord_name,
                    'name': chord_name,
                    'start_time': i * 2,
                    'end_time': (i + 1) * 2,
                    'timestamp': i * 2,
                    'source': 'chordmini'
                })
    
    print(f"[CHORDMINI] Transformed {len(chords)} chords")
    return chords


def get_chords_from_chordmini(audio_path, model='chord-cnn-lstm'):
    """
    Get chord recognition from ChordMiniApp service
    
    Args:
        audio_path: Path to the audio file
        model: Model to use ('chord-cnn-lstm' or 'btc')
    
    Returns:
        List of chord dictionaries or None if failed
    """
    if not is_chordmini_available():
        print("[CHORDMINI] Service not available, skipping")
        return None
    
    try:
        print(f"[CHORDMINI] Sending audio for chord recognition: {audio_path}")
        print(f"[CHORDMINI] Using model: {model}")
        
        with open(audio_path, 'rb') as audio_file:
            files = {'file': (os.path.basename(audio_path), audio_file, 'audio/mpeg')}
            data = {'model': model}
            
            response = requests.post(
                f"{CHORDMINI_API_URL}/api/recognize-chords",
                files=files,
                data=data,
                timeout=CHORDMINI_TIMEOUT
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[CHORDMINI] Successfully received chord data")
            
            # Transform ChordMiniApp format to our format
            chords = transform_chordmini_response(result)
            return chords
        else:
            print(f"[CHORDMINI] Error response: {response.status_code} - {response.text[:200]}")
            record_chordmini_failure()
            return None
            
    except requests.exceptions.Timeout:
        print(f"[CHORDMINI] Request timed out after {CHORDMINI_TIMEOUT}s")
        record_chordmini_failure()
        return None
    except requests.exceptions.RequestException as e:
        print(f"[CHORDMINI] Request failed: {e}")
        record_chordmini_failure()
        return None
    except Exception as e:
        print(f"[CHORDMINI] Unexpected error: {e}")
        record_chordmini_failure()
        return None


def get_cache_filename(identifier):
    """Generate a unique cache filename from an identifier (YouTube URL or search query)"""
    file_hash = hashlib.md5(identifier.encode()).hexdigest()
    return file_hash

def is_cache_valid(cache_path):
    """Check if a cached file exists and is not expired"""
    if not os.path.exists(cache_path):
        return False
    
    file_age_hours = (time.time() - os.path.getmtime(cache_path)) / 3600
    return file_age_hours < CACHE_DURATION_HOURS

def cleanup_old_cache():
    """Delete cache files older than CACHE_DURATION_HOURS"""
    try:
        current_time = time.time()
        deleted_count = 0
        for cache_file in AUDIO_CACHE_DIR.glob('*'):
            if cache_file.is_file():
                file_age_hours = (current_time - os.path.getmtime(cache_file)) / 3600
                if file_age_hours > CACHE_DURATION_HOURS:
                    cache_file.unlink()
                    deleted_count += 1
        if deleted_count > 0:
            print(f"[CACHE] Cleaned up {deleted_count} expired cache files")
    except Exception as e:
        print(f"[CACHE] Cleanup error: {e}")

def cache_youtube_audio(youtube_url_or_query, is_search=False):
    """
    Download and cache YouTube audio
    
    Args:
        youtube_url_or_query: YouTube URL or search query
        is_search: If True, treat as search query instead of URL
        
    Returns:
        tuple: (cache_path, youtube_webpage_url) or (None, None) on failure
    """
    # Generate cache filename
    file_hash = get_cache_filename(youtube_url_or_query)
    
    # Check if already cached
    for ext in ['.m4a', '.webm', '.opus', '.mp4', '.mp3', '.wav']:
        cache_path = AUDIO_CACHE_DIR / f"{file_hash}{ext}"
        if is_cache_valid(cache_path):
            print(f"[CACHE] Using cached audio: {cache_path}")
            return str(cache_path), None  # TODO: Store webpage URL in metadata
    
    # Not cached, download
    print(f"[CACHE] Downloading audio for caching...")
    
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'outtmpl': str(AUDIO_CACHE_DIR / f"{file_hash}.%(ext)s"),
        }
        
        if is_search:
            ydl_opts['default_search'] = 'ytsearch1:'
            search_query = youtube_url_or_query
        else:
            search_query = youtube_url_or_query
        
        youtube_webpage_url = None
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_search:
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
                if info and 'entries' in info and len(info['entries']) > 0:
                    youtube_webpage_url = info['entries'][0].get('webpage_url')
            else:
                info = ydl.extract_info(search_query, download=True)
                youtube_webpage_url = info.get('webpage_url') if info else None
        
        # Find the downloaded file
        for ext in ['.m4a', '.webm', '.opus', '.mp4', '.mp3']:
            cache_path = AUDIO_CACHE_DIR / f"{file_hash}{ext}"
            if cache_path.exists():
                print(f"[CACHE] Cached audio at: {cache_path}")
                return str(cache_path), youtube_webpage_url
        
        print(f"[CACHE] Download completed but file not found")
        return None, None
        
    except Exception as e:
        print(f"[CACHE] Download error: {e}")
        return None, None


def convert_to_wav(input_path, output_path=None):
    """
    Convert any audio format to WAV for consistent processing
    
    Args:
        input_path: Path to input audio file (MP3, M4A, FLAC, OGG, etc.)
        output_path: Optional output path. If None, uses same name with .wav extension
        
    Returns:
        Path to WAV file, or None if conversion failed
    """
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + '.wav'
    
    # Check if already WAV
    if input_path.lower().endswith('.wav'):
        print(f"[CONVERT] File is already WAV: {input_path}")
        return input_path
    
    # Try pydub first (most reliable)
    if PYDUB_AVAILABLE:
        try:
            print(f"[CONVERT] Converting {input_path} to WAV using pydub...")
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format='wav')
            print(f"[CONVERT] Successfully converted to: {output_path}")
            return output_path
        except Exception as e:
            print(f"[CONVERT] pydub conversion failed: {e}")
    
    # Try librosa as fallback
    try:
        print(f"[CONVERT] Trying librosa for conversion...")
        audio_data, sr = librosa.load(input_path, sr=22050)
        sf.write(output_path, audio_data, sr)
        print(f"[CONVERT] Successfully converted to: {output_path}")
        return output_path
    except Exception as e:
        print(f"[CONVERT] librosa conversion failed: {e}")
    
    print(f"[CONVERT] All conversion methods failed for: {input_path}")
    return None


def check_ffmpeg_available():
    """Check if FFmpeg is available on the system"""
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "unknown version"
            print(f"[FFMPEG] ✓ Available: {version_line}")
            return True
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[FFMPEG] Check error: {e}")
    
    print("[FFMPEG] ✗ Not found on system")
    print("[FFMPEG] Some audio formats (M4A, AAC) may not be supported")
    print("[FFMPEG] Install FFmpeg: https://ffmpeg.org/download.html")
    return False

# Check FFmpeg at startup
FFMPEG_AVAILABLE = check_ffmpeg_available()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_analyzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session cookie configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

# CORS configuration - Allow credentials
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

# Email configuration (using Gmail - users should set up their own)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@chordis.com')

# Initialize extensions
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create database tables (runs on import, needed for gunicorn)
with app.app_context():
    db.create_all()
    print("[DB] Database tables created/verified")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Custom login required decorator that returns JSON
from functools import wraps

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required", "success": False}), 401
        if not current_user.is_admin:
            return jsonify({"error": "Admin privileges required", "success": False}), 403
        return f(*args, **kwargs)
    return decorated_function


def send_verification_email(user, token):
    """Send verification email to user"""
    verification_url = f"http://localhost:5000/verify-email?token={token}"
    
    msg = Message(
        subject="Verify Your Chordis Account",
        recipients=[user.email],
        html=f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; text-align: center;">
                <h1 style="color: white; margin: 0;">🎵 Welcome to Chordis!</h1>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa; border-radius: 10px; margin-top: 20px;">
                <h2 style="color: #333;">Hi {user.username}!</h2>
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Thank you for registering with Chordis. To complete your registration and start analyzing music, 
                    please verify your email address by clicking the button below:
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              font-weight: bold;
                              display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    Or copy and paste this link into your browser:
                    <br>
                    <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 1 hour. If you didn't create an account with Chordis, 
                    you can safely ignore this email.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>© 2025 Chordis - AI-Powered Music Analysis</p>
            </div>
        </body>
        </html>
        """
    )
    
    try:
        mail.send(msg)
        print(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        # For development, print the verification URL
        print(f"Verification URL: {verification_url}")
        return False

# Load models once at startup
print("Loading chord recognition model...")
chord_model = CNNModel()
model_path = "models/cnn_model.pth"

# Check if trained model exists
if os.path.exists(model_path):
    print(f"Loading trained model from {model_path}")
    chord_model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
    chord_model.eval()
    use_trained_model = True
else:
    print("[INFO] No trained model found. Using rule-based chord detection.")
    print("   To use a trained model, place it at: models/cnn_model.pth")
    use_trained_model = False

print("Loading Whisper model for lyrics extraction...")
print("   (This may take a moment on first run...)")
# Use 'tiny' model for faster processing - can be changed to 'base', 'small', etc.
whisper_model = whisper.load_model("tiny")  # Faster! Use "base" or "small" for better quality

# Initialize Genius API (optional - add your token for better results)
# Get free token at: https://genius.com/api-clients
GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN', None)
if GENIUS_AVAILABLE and GENIUS_ACCESS_TOKEN:
    try:
        genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, verbose=False, remove_section_headers=True)
        genius.timeout = 10
        
        # Validate API token by testing with a popular song
        print("[GENIUS] Initializing and validating API token...")
        try:
            test_song = genius.search_song("Bohemian Rhapsody", "Queen")
            if test_song and test_song.lyrics:
                print("[GENIUS] ✓ API token validated successfully!")
                print(f"[GENIUS] ✓ Test search successful: '{test_song.title}' by '{test_song.artist}'")
                print(f"[GENIUS] ✓ Ready to fetch lyrics from Genius database")
            else:
                print("[GENIUS] ⚠ API token works but test search returned no results")
                print("[GENIUS] This might indicate rate limiting or API issues")
        except Exception as test_err:
            print(f"[GENIUS] ⚠ API validation test failed: {test_err}")
            print(f"[GENIUS] API may still work, but there might be issues")
            
    except Exception as e:
        print(f"[GENIUS] ✗ Could not initialize Genius API: {e}")
        genius = None
        print("[GENIUS] Will use Whisper for lyrics as fallback")
else:
    genius = None
    if not GENIUS_AVAILABLE:
        print("[GENIUS] ✗ lyricsgenius library not installed")
        print("[GENIUS] Install with: pip install lyricsgenius")
        print("[GENIUS] Will use Whisper for lyrics")
    elif not GENIUS_ACCESS_TOKEN:
        print("[GENIUS] ✗ GENIUS_ACCESS_TOKEN not configured in .env file")
        print("[GENIUS] Get your free token at: https://genius.com/api-clients")
        print("[GENIUS] Add to .env file: GENIUS_ACCESS_TOKEN=your_token_here")
        print("[GENIUS] Will use Whisper for lyrics as fallback")
    else:
        print("[GENIUS] Genius API not configured (will use Whisper for lyrics)")

# Initialize ChordMiniApp status (ML-based chord detection)
print("\nChordMiniApp Status:")
if CHORDMINI_ENABLED:
    if is_chordmini_available():
        print(f"[CHORDMINI] ✓ Service available at {CHORDMINI_API_URL}")
        print("[CHORDMINI] Using ML-based chord detection (301 chord types)")
    else:
        print(f"[CHORDMINI] ✗ Service not available at {CHORDMINI_API_URL}")
        print("[CHORDMINI] Will use rule-based detection as fallback (~48 chord types)")
        print("[CHORDMINI] To enable: run start_servers.bat or manually start ChordMiniApp:")
        print("[CHORDMINI]   cd chordmini/python_backend && python app.py")
else:
    print("[CHORDMINI] ✗ Disabled (CHORDMINI_ENABLED=false in .env)")
    print("[CHORDMINI] Using rule-based chord detection")

# Check Music Recognition APIs
print("\nMusic Recognition Status:")
if os.getenv('ACRCLOUD_ACCESS_KEY') and os.getenv('ACRCLOUD_ACCESS_SECRET'):
    print("[OK] ACRCloud configured (2,000 requests/day)")
else:
    print("[WARN] ACRCloud not configured")

if os.getenv('AUDD_API_TOKEN'):
    print("[OK] AudD configured (300 requests/month)")
else:
    print("[WARN] AudD not configured")

if not os.getenv('ACRCLOUD_ACCESS_KEY') and not os.getenv('AUDD_API_TOKEN'):
    print("\n[INFO] Music recognition requires API configuration:")
    print("   See MUSIC_RECOGNITION_SETUP.md for setup instructions")
    print("   You can still use the app by entering song info manually")

print("\n[OK] All models loaded successfully!")

def download_youtube_audio(url, output_path):
    """Get YouTube audio info and download if possible"""
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,  # Only download single video, not playlist
        'extract_flat': False,
    }
    
    try:
        # Remove playlist parameter from URL if present
        if '&list=' in url:
            url = url.split('&list=')[0]
            print(f"[YOUTUBE] Removed playlist parameter from URL")
        
        print(f"[YOUTUBE] Getting info from: {url}")
        
        # First, just get info without downloading to see if it works
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                print(f"[YOUTUBE ERROR] Could not extract video info")
                return False, None
            
            # Extract metadata
            video_title = info.get('title', '')
            uploader = info.get('uploader', '')
            thumbnail = info.get('thumbnail', '')
            stream_url = info.get('url')  # Direct stream URL
            
            print(f"[YOUTUBE] [OK] Got info: {video_title}")
            print(f"[YOUTUBE] Stream URL available: {stream_url is not None}")
            
            # Try to extract artist and song from title
            artist, song_title = extract_song_info_from_title(video_title)
            
            # If no artist found, use uploader
            if not artist or artist == 'Unknown':
                artist = uploader or 'Unknown Artist'
            
            metadata = {
                'title': song_title or video_title,
                'artist': artist,
                'thumbnail': thumbnail,
                'stream_url': stream_url,  # Direct streaming URL
                'youtube_url': url  # Original YouTube URL
            }
            
            return True, metadata
    except Exception as e:
        error_msg = str(e)
        print(f"[YOUTUBE ERROR] Failed to download: {error_msg}")
        
        if '403' in error_msg or 'Forbidden' in error_msg:
            print("[YOUTUBE ERROR] YouTube is blocking the download (403 Forbidden)")
            print("[FIX] Try updating yt-dlp: pip install --upgrade yt-dlp")
            print("[FIX] Or use a different video URL")
        
        import traceback
        traceback.print_exc()
        return False, None


def extract_song_info_from_title(title):
    """Extract artist and song name from video title"""
    # Common patterns: "Artist - Song", "Song - Artist", "Artist: Song"
    patterns = [
        r'^(.+?)\s*-\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',  # Artist - Song
        r'^(.+?)\s*:\s*(.+?)(?:\s*\(.*\))?(?:\s*\[.*\])?$',  # Artist: Song
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            part1, part2 = match.groups()
            # Try to determine which is artist and which is song
            # Usually artist comes first
            return part1.strip(), part2.strip()
    
    # If no pattern matches, return title as song name
    return None, title.strip()


def download_from_url(url, output_path=None):
    """
    Download audio from various platforms (YouTube, TikTok, Facebook, Instagram, SoundCloud, etc.)
    using yt-dlp which supports 1000+ sites
    
    Args:
        url: URL to download from (video or audio)
        output_path: Optional output path for the audio file
    
    Returns:
        Tuple of (success: bool, audio_path: str or None, metadata: dict or None)
    """
    if not output_path:
        output_path = tempfile.mktemp(suffix='.m4a')
    
    # Detect platform for better logging
    platform = 'Unknown'
    if 'youtube.com' in url or 'youtu.be' in url:
        platform = 'YouTube'
    elif 'tiktok.com' in url:
        platform = 'TikTok'
    elif 'facebook.com' in url or 'fb.watch' in url:
        platform = 'Facebook'
    elif 'instagram.com' in url:
        platform = 'Instagram'
    elif 'soundcloud.com' in url:
        platform = 'SoundCloud'
    elif 'twitter.com' in url or 'x.com' in url:
        platform = 'Twitter/X'
    elif 'vimeo.com' in url:
        platform = 'Vimeo'
    
    print(f"[DOWNLOAD] Detected platform: {platform}")
    print(f"[DOWNLOAD] URL: {url}")
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Prefer m4a, fallback to best audio
        'outtmpl': output_path.replace('.m4a', '.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,  # Only download single item, not playlist
        'extract_flat': False,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
    }
    
    try:
        # Clean up playlist parameters from URL if present
        if '&list=' in url:
            url = url.split('&list=')[0]
            print(f"[DOWNLOAD] Removed playlist parameter from URL")
        
        print(f"[DOWNLOAD] Extracting info...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract metadata first
            info = ydl.extract_info(url, download=False)
            
            if not info:
                print(f"[DOWNLOAD] ERROR: Could not extract video/audio info")
                return False, None, None
            
            # Extract useful metadata
            title = info.get('title', 'Unknown')
            artist = info.get('uploader', '') or info.get('channel', '') or info.get('creator', '')
            duration = info.get('duration', 0)
            
            print(f"[DOWNLOAD] Found: '{title}' by '{artist}' ({duration}s)")
            print(f"[DOWNLOAD] Downloading audio...")
            
            # Download audio
            ydl.download([url])
            
            # Find the downloaded file
            # yt-dlp might change the extension based on what's available
            possible_extensions = ['.m4a', '.mp3', '.webm', '.opus', '.wav']
            base_path = output_path.replace('.m4a', '')
            
            actual_file = None
            for ext in possible_extensions:
                test_path = base_path + ext
                if os.path.exists(test_path):
                    actual_file = test_path
                    break
            
            if not actual_file:
                print(f"[DOWNLOAD] ERROR: Downloaded file not found")
                return False, None, None
            
            print(f"[DOWNLOAD] ✓ SUCCESS! Downloaded to: {actual_file}")
            
            metadata = {
                'title': title,
                'artist': artist,
                'duration': duration,
                'platform': platform,
                'url': url
            }
            
            return True, actual_file, metadata
            
    except Exception as e:
        print(f"[DOWNLOAD] ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Provide helpful error messages
        if 'Unsupported URL' in str(e):
            print(f"[DOWNLOAD] Platform not supported or URL format invalid")
        elif 'Video unavailable' in str(e):
            print(f"[DOWNLOAD] Video/audio is unavailable or private")
        elif 'No video formats' in str(e):
            print(f"[DOWNLOAD] No audio/video streams available for this content")
        
        return False, None, None


def get_lyrics_from_genius(song_title, artist=None):
    """
    Fetch lyrics from Genius API with enhanced error handling and retry logic
    
    Args:
        song_title: Song title
        artist: Artist name (optional)
    
    Returns:
        Dictionary with lyrics data or None if not found
    """
    if not genius:
        print("[GENIUS] ERROR: Genius API not initialized")
        print("[GENIUS] Reason: GENIUS_ACCESS_TOKEN not configured in .env file")
        print("[GENIUS] Get your free token at: https://genius.com/api-clients")
        return None
    
    def normalize_query(text):
        """Normalize song/artist name for better matching"""
        if not text:
            return ""
        # Remove common patterns that might interfere with search
        text = re.sub(r'\(.*?\)', '', text)  # Remove parentheses content
        text = re.sub(r'\[.*?\]', '', text)  # Remove brackets content
        text = re.sub(r'\s+feat\..*$', '', text, flags=re.IGNORECASE)  # Remove "feat. artist"
        text = re.sub(r'\s+ft\..*$', '', text, flags=re.IGNORECASE)  # Remove "ft. artist"
        text = re.sub(r'\s+featuring.*$', '', text, flags=re.IGNORECASE)  # Remove "featuring artist"
        text = re.sub(r'\s+-\s+.*$', '', text)  # Remove " - anything" suffix
        text = re.sub(r'[^\w\s]', '', text)  # Remove special characters except spaces
        text = ' '.join(text.split())  # Normalize whitespace
        return text.strip()
    
    # Try multiple search strategies
    search_strategies = []
    
    # Strategy 1: Original query
    search_strategies.append({
        'title': song_title,
        'artist': artist,
        'description': 'exact match'
    })
    
    # Strategy 2: Normalized query
    normalized_title = normalize_query(song_title)
    normalized_artist = normalize_query(artist) if artist else None
    if normalized_title != song_title or normalized_artist != artist:
        search_strategies.append({
            'title': normalized_title,
            'artist': normalized_artist,
            'description': 'normalized query'
        })
    
    # Strategy 3: Title only (no artist)
    if artist:
        search_strategies.append({
            'title': song_title,
            'artist': None,
            'description': 'title only'
        })
    
    # Strategy 4: Try direct API call if lyricsgenius fails
    use_direct_api = False
    
    # Try each strategy
    for idx, strategy in enumerate(search_strategies):
        try:
            title = strategy['title']
            art = strategy['artist']
            desc = strategy['description']
            
            if not title or not title.strip():
                continue
            
            search_query = f"{title}" + (f" {art}" if art else "")
            print(f"[GENIUS] Strategy {idx + 1}/{len(search_strategies)}: {desc} - Searching: '{search_query}'")
            
            song = None
            try:
                if art:
                    song = genius.search_song(title, art)
                else:
                    song = genius.search_song(title)
            except Exception as search_err:
                print(f"[GENIUS] lyricsgenius search failed: {search_err}")
                use_direct_api = True
                continue
            
            if song:
                print(f"[GENIUS] ✓ Found: '{song.title}' by '{song.artist}'")
                
                if song.lyrics and len(song.lyrics) > 50:  # Ensure we have actual lyrics
                    lyrics_text = song.lyrics
                    
                    # Clean up common Genius artifacts
                    lyrics_text = re.sub(r'^\d+Embed$', '', lyrics_text, flags=re.MULTILINE)
                    lyrics_text = re.sub(r'^You might also like', '', lyrics_text, flags=re.MULTILINE)
                    lyrics_text = lyrics_text.strip()
                    
                    lyrics_length = len(lyrics_text)
                    lines_count = len([l for l in lyrics_text.split('\n') if l.strip()])
                    
                    print(f"[GENIUS] ✓ SUCCESS! Retrieved {lyrics_length} chars, {lines_count} lines")
                    print(f"[GENIUS] Song: '{song.title}' by '{song.artist}'")
                    
                    return {
                        'text': lyrics_text,
                        'source': 'genius',
                        'title': song.title,
                        'artist': song.artist,
                        'words': []
                    }
                else:
                    print(f"[GENIUS] ✗ Song found but no lyrics available")
            else:
                print(f"[GENIUS] ✗ No match found with this strategy")
                
        except Exception as e:
            print(f"[GENIUS] Strategy {idx + 1} error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Fallback: Try direct Genius API if configured
    if use_direct_api and GENIUS_ACCESS_TOKEN:
        try:
            print(f"[GENIUS] Attempting direct API fallback...")
            headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}
            search_url = 'https://api.genius.com/search'
            
            query = f"{normalized_title} {normalized_artist}" if normalized_artist else normalized_title
            params = {'q': query}
            
            print(f"[GENIUS] Direct API search: {query}")
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get('response', {}).get('hits', [])
                
                if hits:
                    # Get the first hit
                    first_hit = hits[0]['result']
                    song_api_path = first_hit.get('api_path')
                    
                    print(f"[GENIUS] Found via direct API: {first_hit.get('title')} by {first_hit.get('primary_artist', {}).get('name')}")
                    print(f"[GENIUS] Note: Direct API doesn't provide lyrics - need to scrape from web")
                    print(f"[GENIUS] Consider using lyricsgenius library for full functionality")
                    
            elif response.status_code == 401:
                print(f"[GENIUS] ERROR: Invalid API token (401 Unauthorized)")
                print(f"[GENIUS] Please check your GENIUS_ACCESS_TOKEN in .env file")
            else:
                print(f"[GENIUS] Direct API returned status {response.status_code}")
                
        except Exception as api_err:
            print(f"[GENIUS] Direct API fallback failed: {api_err}")
    
    # All strategies failed
    print(f"[GENIUS] ✗ FAILED - No lyrics found after trying {len(search_strategies)} strategies")
    print(f"[GENIUS] Original query: '{song_title}' by '{artist}'")
    print(f"[GENIUS] Possible reasons:")
    print(f"  1. Song not in Genius database (try more popular songs)")
    print(f"  2. Title/artist name spelling mismatch")
    print(f"  3. Song too new (not yet added to Genius)")
    print(f"  4. Genius API rate limit reached (wait a moment)")
    print(f"  5. API token issues (check GENIUS_ACCESS_TOKEN)")
    
    return None

def predict_chords_with_timestamps(filepath):
    """
    Predict chords from an audio file with timestamps
    
    Priority:
    1. ChordMiniApp (if available) - 301 chord types, ML-based
    2. Rule-based detection (fallback) - ~48 chord types
    """
    print(f"\n[CHORD DETECTION] Starting analysis for: {filepath}")
    
    # Get audio duration first
    y_temp, sr_temp = librosa.load(filepath, sr=11025, mono=True, duration=10)
    y_full, sr = librosa.load(filepath, sr=11025, mono=True)
    duration = librosa.get_duration(y=y_full, sr=sr)
    
    # STEP 1: Try ChordMiniApp first (most accurate, 301 chord types)
    if CHORDMINI_ENABLED:
        print("[CHORD DETECTION] Attempting ChordMiniApp (ML-based, 301 chords)...")
        chordmini_chords = get_chords_from_chordmini(filepath)
        if chordmini_chords and len(chordmini_chords) > 0:
            print(f"[CHORD DETECTION] ✓ ChordMiniApp returned {len(chordmini_chords)} chords")
            return {
                'progression': chordmini_chords,
                'duration': round(duration, 2),
                'source': 'chordmini'
            }
        else:
            print("[CHORD DETECTION] ChordMiniApp unavailable or returned no results")
    
    # STEP 2: Fallback to rule-based detection
    print("[CHORD DETECTION] Using rule-based detection (fallback)...")
    
    # Optimized: Larger hop length for faster processing
    hop_length = 1024
    # Optimized: Use faster chroma_stft instead of chroma_cqt
    chroma = librosa.feature.chroma_stft(y=y_full, sr=sr, hop_length=hop_length, n_fft=2048)
    
    # Analyze chroma per segment with timestamps
    chord_progression = []
    segment_length = 50  # frames (increased for faster processing with fewer segments)
    num_segments = max(1, chroma.shape[1] // segment_length)
    
    for i in range(num_segments):
        start_idx = i * segment_length
        end_idx = min((i + 1) * segment_length, chroma.shape[1])
        chroma_segment = chroma[:, start_idx:end_idx]
        
        # Calculate timestamps
        start_time = librosa.frames_to_time(start_idx, sr=sr, hop_length=hop_length)
        end_time = librosa.frames_to_time(end_idx, sr=sr, hop_length=hop_length)
        
        # Average chroma over segment
        avg_chroma = np.mean(chroma_segment, axis=1)
        
        # Detect chord
        if use_trained_model:
            X = avg_chroma.reshape(1, -1)
            with torch.no_grad():
                output = chord_model(torch.tensor(X).unsqueeze(1).float())
                chord_idx = output.argmax(dim=1).item()
        else:
            chord_idx = chord_model.predict_from_chroma(avg_chroma)
        
        chord_name = CHORDS[chord_idx]
        
        # Add to progression (merge consecutive same chords)
        if chord_progression and chord_progression[-1]['chord'] == chord_name:
            chord_progression[-1]['end_time'] = end_time
        else:
            chord_progression.append({
                'chord': chord_name,
                'start_time': round(start_time, 2),
                'end_time': round(end_time, 2),
                'source': 'rule-based'
            })
    
    print(f"[CHORD DETECTION] ✓ Rule-based detection returned {len(chord_progression)} chords")
    
    return {
        'progression': chord_progression,
        'duration': round(duration, 2),
        'source': 'rule-based'
    }

def extract_lyrics_with_timestamps(filepath, song_info=None):
    """Extract lyrics - try Genius first, fallback to Whisper"""
    
    # Try Genius API first if we have song info
    if song_info:
        artist, song_title = extract_song_info_from_title(song_info)
        genius_lyrics = get_lyrics_from_genius(song_title, artist)
        if genius_lyrics:
            return genius_lyrics
    
    # Fallback to Whisper (speech-to-text)
    print("Using Whisper for lyrics extraction...")
    try:
        # Optimized settings for much faster processing
        result = whisper_model.transcribe(
            filepath, 
            language="en", 
            task="transcribe",
            word_timestamps=True,
            fp16=False,  # Disable FP16 for CPU
            best_of=1,   # Faster decoding
            beam_size=1,  # Faster beam search
            temperature=0,  # Deterministic, faster
            compression_ratio_threshold=2.4,  # Skip low-quality audio faster
            no_speech_threshold=0.6,  # Skip silence faster
            condition_on_previous_text=False  # Faster, no context dependency
        )
        
        # Extract word-level timestamps
        words_with_time = []
        if 'segments' in result:
            for segment in result['segments']:
                if 'words' in segment:
                    for word in segment['words']:
                        words_with_time.append({
                            'word': word.get('word', '').strip(),
                            'start': round(word.get('start', 0), 2),
                            'end': round(word.get('end', 0), 2)
                        })
        
        return {
            'text': result["text"],
            'source': 'whisper',
            'words': words_with_time
        }
    except Exception as e:
        print(f"Error extracting lyrics: {e}")
        return {'text': None, 'source': 'error', 'words': []}

def process_audio(filepath, song_info=None):
    """Process audio file to get both chords and lyrics with timestamps"""
    chord_result = predict_chords_with_timestamps(filepath)
    lyrics_data = extract_lyrics_with_timestamps(filepath, song_info)
    
    # Extract chord progression array from result
    chord_data = chord_result.get('progression', []) if isinstance(chord_result, dict) else chord_result
    
    return chord_data, lyrics_data


# ============================================
# MUSIC RECOGNITION FUNCTIONS
# ============================================

def recognize_song_acrcloud(audio_file_path):
    """
    Recognize song using ACRCloud API
    Requires: ACRCLOUD_ACCESS_KEY, ACRCLOUD_ACCESS_SECRET, ACRCLOUD_HOST in environment
    """
    access_key = os.getenv('ACRCLOUD_ACCESS_KEY')
    access_secret = os.getenv('ACRCLOUD_ACCESS_SECRET')
    host = os.getenv('ACRCLOUD_HOST', 'identify-us-west-2.acrcloud.com')
    
    if not access_key or not access_secret:
        raise ValueError("ACRCloud credentials not configured")
    
    # Read audio file
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    # Prepare request
    timestamp = int(time.time())
    string_to_sign = f"POST\n/v1/identify\n{access_key}\naudio\n1\n{timestamp}"
    
    # Create signature
    signature = base64.b64encode(
        hmac.new(
            access_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')
    
    # Prepare multipart form data
    files = {
        'sample': ('sample.wav', audio_data, 'audio/wav')
    }
    
    data = {
        'access_key': access_key,
        'data_type': 'audio',
        'signature_version': '1',
        'signature': signature,
        'sample_bytes': str(len(audio_data)),
        'timestamp': str(timestamp)
    }
    
    try:
        # Make request
        url = f'https://{host}/v1/identify'
        response = requests.post(url, files=files, data=data, timeout=10)
        result = response.json()
        
        # Parse response (don't print full response - has Unicode issues)
        status_code = result.get('status', {}).get('code')
        status_msg = result.get('status', {}).get('msg', 'Unknown error')
        
        if status_code == 0:
            music = result.get('metadata', {}).get('music', [])
            if music:
                track = music[0]
                song_result = {
                    'title': track.get('title', 'Unknown'),
                    'artist': ', '.join([a.get('name', '') for a in track.get('artists', [])]) or 'Unknown Artist',
                    'album': track.get('album', {}).get('name') if track.get('album') else None,
                    'release_date': track.get('release_date'),
                    'score': track.get('score', 100),
                    'confidence': track.get('score', 90),
                    'source': 'acrcloud'
                }
                print(f"ACRCloud found: {song_result.get('title')} by {song_result.get('artist')}")
                return song_result
            else:
                print("ACRCloud: No music found")
                return None
        elif status_code == 1001:
            print("ACRCloud: No result (song not in database)")
            return None
        elif status_code == 2004:
            print(f"ACRCloud Error 2004: Can't generate fingerprint - {status_msg}")
            print("This usually means the audio file is too short, corrupted, or in an unsupported format")
            return None
        elif status_code == 3016:
            print(f"ACRCloud Error 3016: File too large - {status_msg}")
            return None
        elif status_code == 3000:
            raise ValueError("ACRCloud: Invalid Access Key")
        elif status_code == 3001:
            raise ValueError("ACRCloud: Invalid Access Secret")
        elif status_code == 3003:
            raise ValueError("ACRCloud: Invalid Signature")
        else:
            print(f"ACRCloud Error {status_code}: {status_msg}")
            return None
        
    except Exception as e:
        print(f"ACRCloud recognition error: {e}")
        raise


def recognize_song_audd(audio_file_path):
    """
    Recognize song using AudD API
    Requires: AUDD_API_TOKEN in environment
    """
    api_token = os.getenv('AUDD_API_TOKEN')
    
    if not api_token:
        raise ValueError("AudD API token not configured")
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'api_token': api_token,
                'return': 'apple_music,spotify'
            }
            
            response = requests.post(
                'https://api.audd.io/',
                files=files,
                data=data,
                timeout=30
            )
            
        result = response.json()
        
        if result.get('status') == 'success' and result.get('result'):
            track = result['result']
            return {
                'title': track.get('title', 'Unknown'),
                'artist': track.get('artist', 'Unknown Artist'),
                'album': track.get('album'),
                'release_date': track.get('release_date'),
                'score': 100,  # AudD doesn't provide score
                'source': 'audd',
                'spotify_id': track.get('spotify', {}).get('id') if track.get('spotify') else None,
                'apple_music_id': track.get('apple_music', {}).get('id') if track.get('apple_music') else None
            }
        return None
        
    except Exception as e:
        print(f"AudD recognition error: {e}")
        raise


def recognize_song(audio_file_path):
    """
    Recognize song using available music recognition services
    Tries ACRCloud first, then falls back to AudD
    """
    result = None
    
    # Try ACRCloud first (if configured)
    if os.getenv('ACRCLOUD_ACCESS_KEY') and os.getenv('ACRCLOUD_ACCESS_SECRET'):
        try:
            print("Trying ACRCloud recognition...")
            result = recognize_song_acrcloud(audio_file_path)
            if result:
                print(f"SUCCESS - Song recognized via ACRCloud: {result['title']} by {result['artist']}")
                return result
        except Exception as e:
            print(f"ACRCloud failed, trying alternative... {e}")
    
    # Try AudD as fallback (if configured)
    if os.getenv('AUDD_API_TOKEN'):
        try:
            print("Trying AudD recognition...")
            result = recognize_song_audd(audio_file_path)
            if result:
                print(f"SUCCESS - Song recognized via AudD: {result['title']} by {result['artist']}")
                return result
        except Exception as e:
            print(f"AudD failed: {e}")
    
    # If we get here, no service was able to recognize the song
    if os.getenv('ACRCLOUD_ACCESS_KEY') or os.getenv('AUDD_API_TOKEN'):
        raise ValueError("Song not recognized. Try using a longer audio clip (15+ seconds) of a popular song with clear audio quality.")
    else:
        raise ValueError("Song recognition failed. Please configure ACRCloud or AudD API credentials in your .env file.")


# ============================================
# API ROUTES
# ============================================

@app.route("/api/recognize-song", methods=["POST"])
def recognize_song_endpoint():
    """
    Recognize a song from uploaded audio file or URL
    
    Accepts:
    - File upload (multipart/form-data with 'file' field)
    - URL (JSON with 'url' field) - Supports:
        * YouTube videos
        * TikTok videos  
        * Facebook videos
        * Instagram videos/reels
        * SoundCloud tracks
        * Twitter/X videos
        * Vimeo videos
        * 1000+ other sites via yt-dlp
    
    Returns:
        JSON with song metadata (title, artist, album, confidence, source)
    """
    print("=== RECOGNIZE SONG ENDPOINT CALLED ===")
    temp_file = None
    
    try:
        # Check if it's a file upload or YouTube URL
        if 'file' in request.files:
            # File upload
            file = request.files['file']
            
            print(f"Received file: {file.filename}")
            
            try:
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
                    temp_file = tmp.name
                    file.save(temp_file)
                
                print(f"Saved to: {temp_file}")
                print(f"Converting to WAV...")
                
                # Convert to WAV - limit to 20 seconds for ACRCloud
                wav_file = temp_file + '.wav'
                y, sr = librosa.load(temp_file, sr=16000, mono=True, duration=20)
                sf.write(wav_file, y, sr, subtype='PCM_16')
                
                print(f"Converted successfully: {wav_file}")
                
                # Clean up original
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                temp_file = wav_file
                
            except Exception as conv_error:
                print(f"CONVERSION ERROR: {conv_error}")
                import traceback
                traceback.print_exc()
                
                # Clean up
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
                    
                return jsonify({
                    'success': False,
                    'error': f'Conversion failed: {str(conv_error)}'
                }), 500
            
        elif request.is_json:
            data = request.json
            url = data.get('url') or data.get('youtube_url')  # Support both 'url' and legacy 'youtube_url'
            
            if url:
                print(f"[RECOGNIZE] Received URL: {url}")
                
                # Download audio from URL (supports YouTube, TikTok, Facebook, Instagram, etc.)
                success, audio_path, metadata = download_from_url(url)
                
                if not success or not audio_path:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to download audio from URL. Check if the link is valid and accessible.'
                    }), 400
                
                temp_file = audio_path
                print(f"[RECOGNIZE] Downloaded audio: {temp_file}")
                
                # Convert to WAV for ACRCloud (limit to 20 seconds)
                try:
                    print(f"[RECOGNIZE] Converting to WAV for recognition...")
                    wav_file = temp_file + '.wav'
                    y, sr = librosa.load(temp_file, sr=16000, mono=True, duration=20)
                    sf.write(wav_file, y, sr, subtype='PCM_16')
                    
                    # Clean up original
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    temp_file = wav_file
                    
                    print(f"[RECOGNIZE] Converted successfully for recognition")
                except Exception as conv_error:
                    print(f"[RECOGNIZE] Conversion error: {conv_error}")
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                    return jsonify({
                        'success': False,
                        'error': f'Audio conversion failed: {str(conv_error)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': 'Please provide either a file upload or url'
                }), 400
            
        else:
            return jsonify({
                'success': False,
                'error': 'Please provide either a file upload or url'
            }), 400
        
        # Recognize the song
        print(f"Recognizing song from: {temp_file}")
        song_info = recognize_song(temp_file)
        
        # Clean up
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Log recognition activity
        user_id = current_user.id if current_user.is_authenticated else None
        log_recognition(
            song_info.get('title', 'Unknown'),
            song_info.get('artist', 'Unknown'),
            song_info.get('source', 'unknown'),
            song_info.get('confidence', song_info.get('score', 0)),
            user_id
        )
        
        return jsonify({
            'success': True,
            'song': song_info,
            'message': 'Song recognized successfully'
        })
        
    except Exception as e:
        # Clean up on error
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        
        print(f"!!! MAIN ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyze music for chords and lyrics.
    Accepts either:
    - File upload (multipart/form-data with 'file' field)
    - YouTube URL (JSON with 'youtube_url' field)
    - Optional: song_title and artist for Genius lyrics
    """
    # Cleanup old cache files
    cleanup_old_cache()
    
    temp_file = None
    song_info = None
    youtube_mode = False  # Track if we're analyzing YouTube URL
    
    try:
        # Check if it's a YouTube URL request
        if request.is_json:
            data = request.get_json()
            youtube_url = data.get('youtube_url')
            song_title = data.get('song_title')
            artist = data.get('artist')
            
            if not youtube_url:
                return jsonify({"error": "No youtube_url provided in JSON"}), 400
            
            # Get YouTube info (no download - just streaming URL)
            print(f"[ANALYZE] Getting YouTube info: {youtube_url}")
            success, metadata = download_youtube_audio(youtube_url, None)
            
            if not success:
                return jsonify({"error": "Failed to get YouTube video info"}), 400
            
            # Use metadata from YouTube
            if metadata:
                title = metadata.get('title', 'Unknown Song')
                artist = metadata.get('artist', 'Unknown Artist')
                youtube_thumbnail = metadata.get('thumbnail', '')
                youtube_stream_url = metadata.get('stream_url')
                original_youtube_url = metadata.get('youtube_url')
            
            # Use provided song info if available
            if song_title and artist:
                title = song_title
                artist = artist
            
            song_info = f"{artist} - {title}"
            
            # FETCH LYRICS FROM GENIUS IMMEDIATELY
            print(f"[YOUTUBE] ===== FETCHING LYRICS NOW =====")
            print(f"[YOUTUBE] Title: '{title}'")
            print(f"[YOUTUBE] Artist: '{artist}'")
            
            youtube_lyrics = get_lyrics_from_genius(title, artist)
            
            # For YouTube URLs, we won't download - just return streaming info
            # Set audio_path to None so we skip the file processing
            audio_path = None
            youtube_mode = True
            
        # Check if it's a file upload
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "Empty filename"}), 400
            
            # Check for optional song info from form
            song_title = request.form.get('song_title')
            artist = request.form.get('artist')
            
            if song_title and artist:
                song_info = f"{artist} - {song_title}"
            elif song_title:
                song_info = song_title
            
            # Get original file extension
            original_ext = os.path.splitext(file.filename)[1].lower() if file.filename else '.mp3'
            print(f"[UPLOAD] Received file: {file.filename} (format: {original_ext})")
            
            # Save original file first
            temp_original = tempfile.NamedTemporaryFile(delete=False, suffix=original_ext)
            file.save(temp_original.name)
            temp_original.close()
            
            # Convert to WAV if needed
            if original_ext != '.wav':
                print(f"[UPLOAD] Converting {original_ext} to WAV for processing...")
                wav_path = convert_to_wav(temp_original.name)
                
                if wav_path and os.path.exists(wav_path):
                    audio_path = wav_path
                    # Clean up original if different from converted
                    if wav_path != temp_original.name:
                        try:
                            os.unlink(temp_original.name)
                        except:
                            pass
                    print(f"[UPLOAD] Conversion successful: {audio_path}")
                else:
                    # Conversion failed, try using original anyway
                    print(f"[UPLOAD] Conversion failed, attempting to use original file")
                    audio_path = temp_original.name
            else:
                audio_path = temp_original.name
                print(f"[UPLOAD] File is already WAV, no conversion needed")
            
        else:
            return jsonify({
                "error": "Please provide either a file upload or youtube_url in JSON"
            }), 400
        
        # Process the audio (skip if YouTube streaming mode)
        if audio_path and os.path.exists(audio_path):
            print(f"Analyzing audio: {audio_path}")
            chord_data, lyrics_data = process_audio(audio_path, song_info)
        else:
            # YouTube mode - no local file processing, just return placeholder data
            print(f"[YOUTUBE MODE] Skipping audio processing, using defaults")
            chord_data = {
                "progression": [
                    {"chord": "C", "start_time": 0},
                    {"chord": "G", "start_time": 15},
                    {"chord": "Am", "start_time": 30},
                    {"chord": "F", "start_time": 45}
                ]
            }
            # Use the lyrics we fetched earlier
            lyrics_data = youtube_lyrics if 'youtube_lyrics' in locals() else None
        
        # Try to extract metadata from audio file (only if not already set from YouTube)
        if 'title' not in locals():
            title = "Unknown Song"
        if 'artist' not in locals():
            artist = "Unknown Artist"
        if 'artwork_data' not in locals():
            artwork_data = None
        
        # Only extract metadata from audio file if we have one
        if audio_path and os.path.exists(audio_path):
            try:
                import mutagen
                from mutagen.id3 import ID3, APIC
                from mutagen.mp4 import MP4
                import base64
                
                audio_file = mutagen.File(audio_path)
                
                if audio_file is not None:
                    # Extract title
                    if 'TIT2' in audio_file:  # MP3 ID3
                        title = str(audio_file['TIT2'])
                    elif 'title' in audio_file:  # FLAC, OGG
                        title = str(audio_file['title'][0])
                    elif '\xa9nam' in audio_file:  # M4A
                        title = str(audio_file['\xa9nam'][0])
                    
                    # Extract artist
                    if 'TPE1' in audio_file:  # MP3 ID3
                        artist = str(audio_file['TPE1'])
                    elif 'artist' in audio_file:  # FLAC, OGG
                        artist = str(audio_file['artist'][0])
                    elif '\xa9ART' in audio_file:  # M4A
                        artist = str(audio_file['\xa9ART'][0])
                    
                    # Extract album artwork
                    if isinstance(audio_file, MP4):  # M4A
                        if 'covr' in audio_file:
                            artwork_data = base64.b64encode(audio_file['covr'][0]).decode()
                    elif hasattr(audio_file, 'tags'):  # MP3
                        for tag in audio_file.tags.values():
                            if isinstance(tag, APIC):
                                artwork_data = base64.b64encode(tag.data).decode()
                                break
            except Exception as e:
                print(f"[INFO] Could not extract metadata: {e}")
        
        # Override with song_info if provided (from YouTube)
        if song_info:
            if " - " in song_info:
                parts = song_info.split(" - ", 1)
                artist = parts[0].strip()
                title = parts[1].strip()
            elif " by " in song_info.lower():
                parts = song_info.lower().split(" by ", 1)
                title = song_info[:len(parts[0])].strip()
                artist = song_info[len(parts[0])+4:].strip()
            else:
                title = song_info
        
        # Download YouTube thumbnail if available
        if 'youtube_thumbnail' in locals() and youtube_thumbnail and not artwork_data:
            try:
                import requests
                response = requests.get(youtube_thumbnail, timeout=5)
                if response.status_code == 200:
                    import base64
                    artwork_data = base64.b64encode(response.content).decode()
            except Exception as e:
                print(f"[INFO] Could not download thumbnail: {e}")
        
        # Keep audio file for playback or use YouTube streaming URL
        audio_url = None
        
        # Check if we're in YouTube mode
        if youtube_mode and 'youtube_stream_url' in locals() and youtube_stream_url:
            # Use proxy to stream from YouTube
            audio_url = f"/api/proxy-audio?url={requests.utils.quote(youtube_stream_url)}"
            print(f"[AUDIO] [OK] Using YouTube stream via proxy: {audio_url}")
        elif audio_path and os.path.exists(audio_path):
            try:
                import hashlib
                import shutil
                
                print(f"[AUDIO] Processing audio file for playback...")
                print(f"[AUDIO] Source file: {audio_path}")
                print(f"[AUDIO] File size: {os.path.getsize(audio_path)} bytes")
                
                # Create hash from title and artist
                file_hash = hashlib.md5(f"{artist}{title}".encode()).hexdigest()[:12]
                file_ext = os.path.splitext(audio_path)[1]  # Get extension (.m4a, .webm, etc)
                
                # Copy to temp directory with hash-based name
                temp_audio_path = os.path.join(tempfile.gettempdir(), f"chordis_{file_hash}{file_ext}")
                shutil.copy2(audio_path, temp_audio_path)
                
                # Remove original temp file
                os.remove(audio_path)
                
                # Create URL for serving
                audio_url = f"/api/temp-audio/{file_hash}{file_ext}"
                print(f"[AUDIO] [OK] Saved for playback: {temp_audio_path}")
                print(f"[AUDIO] [OK] Serving at: {audio_url}")
            except Exception as e:
                print(f"[AUDIO ERROR] Could not save audio file: {e}")
                import traceback
                traceback.print_exc()
                # Clean up on error
                if os.path.exists(audio_path):
                    os.remove(audio_path)
        else:
            print(f"[AUDIO WARNING] No audio file available for playback")
        
        # Log analysis activity
        user_id = current_user.id if current_user.is_authenticated else None
        log_analysis_activity('analyze', title, artist, user_id)
        
        # Lyrics already fetched earlier for YouTube mode, only fetch for file uploads
        if not youtube_mode and not lyrics_data:
            print(f"[LYRICS] Fetching lyrics for uploaded file")
            genius_lyrics = get_lyrics_from_genius(title, artist)
            
            if genius_lyrics and genius_lyrics.get('text'):
                lines = genius_lyrics['text'].split('\n')
                lyrics_data = {'text': '\n'.join([line.strip() for line in lines if line.strip()])}
                print(f"[LYRICS] [OK] Found {len(lines)} lines from Genius")
        
        return jsonify({
            "success": True,
            "chord_data": chord_data,
            "lyrics_data": lyrics_data,
            "title": title,
            "artist": artist,
            "artwork": artwork_data,
            "audio_url": audio_url,  # Proxy URL or temp file URL
            "youtube_webpage_url": original_youtube_url if 'original_youtube_url' in locals() else None,
            "audio_available": audio_url is not None,
            "duration": 180  # Default duration, can be calculated from audio
        })
    
    except Exception as e:
        # Clean up on error
        if temp_file and os.path.exists(temp_file.name):
            os.remove(temp_file.name)
        
        return jsonify({"error": str(e), "success": False}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "models_loaded": True})

@app.route("/", methods=["GET"])
def index():
    """Serve the main Chordis landing page"""
    return send_from_directory('.', 'index.html')

@app.route("/auth", methods=["GET"])
def auth_page():
    """Serve the authentication page"""
    return send_from_directory('static', 'auth.html')

@app.route("/chordis", methods=["GET"])
@app.route("/analyze-app", methods=["GET"])
def chordis():
    """Serve the new Chordis interface"""
    return send_from_directory('.', 'chordis.html')

@app.route("/get-audio-url", methods=["POST"])
def get_audio_url():
    """Get audio URL for playback without downloading the full file"""
    try:
        data = request.get_json()
        url_type = data.get('type')
        
        if url_type == 'youtube':
            youtube_url = data.get('url')
            if not youtube_url:
                return jsonify({"error": "No YouTube URL provided"}), 400
            
            # Get audio stream URL without downloading
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                audio_url = info.get('url')
                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
                
                if audio_url:
                    return jsonify({
                        "success": True,
                        "audio_url": audio_url,
                        "title": title,
                        "duration": duration
                    })
                else:
                    return jsonify({"error": "Could not extract audio URL"}), 400
                    
        elif url_type == 'search':
            # Search for song on YouTube and get audio URL
            query = data.get('query')
            if not query:
                return jsonify({"error": "No search query provided"}), 400
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1:',  # Search YouTube and get first result
                'extract_flat': False,
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    print(f"[SEARCH] Searching YouTube for: {query}")
                    search_result = ydl.extract_info(f"ytsearch1:{query}", download=False)
                    
                    if search_result and 'entries' in search_result and len(search_result['entries']) > 0:
                        video = search_result['entries'][0]
                        audio_url = video.get('url')
                        title = video.get('title', 'Unknown')
                        duration = video.get('duration', 0)
                        
                        if audio_url:
                            print(f"[SEARCH] Found audio: {title}")
                            return jsonify({
                                "success": True,
                                "audio_url": audio_url,
                                "title": title,
                                "duration": duration
                            })
                
                return jsonify({"success": False, "error": "No results found"}), 404
                
            except Exception as e:
                print(f"[ERROR] YouTube search failed: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
            
        elif url_type == 'upload':
            # For uploaded files, we'll return a placeholder
            # In a real implementation, you'd serve the uploaded file
            return jsonify({
                "success": True,
                "audio_url": None,  # Will be handled by object URL in frontend
                "title": "Uploaded File",
                "duration": 0
            })
            
        else:
            return jsonify({"error": "Invalid URL type"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/auth", methods=["GET"])
def auth():
    """Serve the auth web interface"""
    return send_from_directory('static', 'auth.html')

@app.route("/chordai", methods=["GET"])
def chordai():
    """Serve the ChordAI-style web interface"""
    return send_from_directory('static', 'chordai.html')

@app.route("/library", methods=["GET"])
def library():
    """Serve the library page"""
    return send_from_directory('static', 'library.html')

@app.route("/js/<path:filename>", methods=["GET"])
def serve_js(filename):
    """Serve JavaScript files"""
    return send_from_directory('js', filename)

@app.route("/css/<path:filename>", methods=["GET"])
def serve_css(filename):
    """Serve CSS files"""
    return send_from_directory('static/css', filename)

@app.route("/debug.html", methods=["GET"])
def debug_page():
    """Serve debug page"""
    return send_from_directory('.', 'debug.html')

@app.route("/test-page.html", methods=["GET"])
def test_page():
    """Serve test page"""
    return send_from_directory('.', 'test-page.html')

@app.route("/simple", methods=["GET"])
def simple():
    """Serve the simple web interface"""
    return send_from_directory('static', 'index.html')

@app.route("/realtime", methods=["GET"])
def realtime_page():
    """Serve the real-time chord recognition interface"""
    return send_from_directory('static', 'realtime.html')


# ==================== AUTH ROUTES ====================

def decrypt_client_data(encrypted_text):
    """Decrypt data sent from client (AES-CBC compatible)"""
    try:
        import base64
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        
        # Use the same passphrase and salt as client
        passphrase = b'CHORDIS_PUBLIC_KEY_2025'
        salt = b'chordis-salt-2025'
        
        # Derive key using PBKDF2 (same as client)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(passphrase)
        
        # Decode base64
        encrypted_data = base64.b64decode(encrypted_text)
        
        # Extract IV (first 16 bytes) and ciphertext
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Decrypt using AES-CBC
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove PKCS7 padding
        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Decryption error: {e}")
        print(f"[DEBUG] Encrypted text length: {len(encrypted_text)}")
        # Return as-is if not encrypted
        return encrypted_text


@app.route("/api/register", methods=["POST"])
def register():
    """Register a new user and send verification email"""
    data = request.get_json()
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    is_encrypted = data.get('encrypted', False)
    
    # Decrypt if data was encrypted (BEFORE validation!)
    if is_encrypted and request.headers.get('X-Encrypted') == 'true':
        try:
            email = decrypt_client_data(email)
            password = decrypt_client_data(password)
            print(f"[SECURITY] Decrypted client data successfully")
            print(f"[SECURITY] Email after decryption: {email[:10]}...")  # Show first 10 chars
        except Exception as e:
            print(f"[ERROR] Decryption failed: {e}")
            return jsonify({"error": "Decryption failed. Please try again."}), 400
    
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Validate email format (AFTER decryption!)
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        print(f"[ERROR] Invalid email format: {email}")
        return jsonify({"error": "Invalid email format"}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400
    
    # Create new user
    user = User(username=username, email=email, email_verified=False)
    user.set_password(password)
    
    # Generate verification token
    token = user.generate_verification_token()
    user.verification_token = token
    
    db.session.add(user)
    db.session.commit()
    
    # Send verification email
    try:
        send_verification_email(user, token)
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        # Continue anyway - user can still use the app
    
    # Log user in (they can use app but should verify email)
    login_user(user)
    
    return jsonify({
        "success": True,
        "message": "Registration successful! Please check your email to verify your account.",
        "email_sent": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_verified": user.email_verified
        }
    })


@app.route("/api/login", methods=["POST"])
def login():
    """Login user"""
    data = request.get_json()
    
    username_or_email = data.get('username')
    password = data.get('password')
    is_encrypted = data.get('encrypted', False)
    original_password = password  # Keep original for fallback
    
    # Decrypt if data was encrypted
    if is_encrypted and request.headers.get('X-Encrypted') == 'true':
        try:
            password = decrypt_client_data(password)
            print(f"[SECURITY] Decrypted login password successfully")
        except Exception as e:
            print(f"[WARN] Decryption failed: {e}, using original password")
            password = original_password  # Use original if decryption fails
    
    if not username_or_email or not password:
        return jsonify({"error": "Missing username or password"}), 400
    
    # Try to find user by username first, then by email
    user = User.query.filter_by(username=username_or_email).first()
    if not user:
        # Try email - check all users and compare decrypted email
        all_users = User.query.all()
        for u in all_users:
            try:
                if u.get_email() == username_or_email:
                    user = u
                    break
            except:
                pass
    
    if not user:
        print(f"[AUTH] User not found: {username_or_email}")
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Try password check - first with potentially decrypted password
    password_ok = user.check_password(password)
    
    # If that fails and we had encryption, try with original (in case decryption was wrong)
    if not password_ok and is_encrypted and password != original_password:
        print("[AUTH] Trying with original encrypted password as fallback...")
        password_ok = user.check_password(original_password)
    
    if not password_ok:
        print(f"[AUTH] Password check failed for user: {user.username}")
        return jsonify({"error": "Invalid username or password"}), 401
    
    login_user(user, remember=data.get('remember', False))
    
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    })


@app.route("/api/logout", methods=["POST"])
@api_login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({"success": True})


# ============================================
# OTP EMAIL VERIFICATION
# ============================================
import random
import string

# Store OTPs in memory (in production, use Redis or database)
otp_storage = {}

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp, username=None):
    """Send OTP verification email"""
    try:
        msg = Message(
            subject='🎵 Chordis - Email Verification Code',
            recipients=[email],
            html=f'''
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; border-radius: 16px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">🎵 Chordis</h1>
                    <p style="margin: 10px 0 0; opacity: 0.9;">Email Verification</p>
                </div>
                <div style="padding: 40px 30px; text-align: center;">
                    <p style="font-size: 16px; color: #a0a0a0; margin-bottom: 20px;">
                        {f"Hi {username}!" if username else "Hello!"} Your verification code is:
                    </p>
                    <div style="background: rgba(59, 130, 246, 0.2); border: 2px solid #3b82f6; border-radius: 12px; padding: 20px; margin: 20px 0;">
                        <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #3b82f6;">{otp}</span>
                    </div>
                    <p style="font-size: 14px; color: #808080; margin-top: 20px;">
                        This code expires in <strong>10 minutes</strong>.
                    </p>
                    <p style="font-size: 12px; color: #606060; margin-top: 30px;">
                        If you didn't request this code, please ignore this email.
                    </p>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 20px; text-align: center; font-size: 12px; color: #808080;">
                    © 2025 Chordis - AI Music Analysis
                </div>
            </div>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[OTP] Failed to send email: {e}")
        return False


@app.route("/api/auth/check-email", methods=["POST"])
def check_email():
    """Check if email already exists in the system"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({"exists": False, "error": "Email is required"}), 400
    
    # Validate email format
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({"exists": False, "error": "Invalid email format"}), 400
    
    # Check if email exists
    existing_user = User.query.filter_by(email=email).first()
    
    if existing_user:
        return jsonify({
            "exists": True, 
            "message": "This email is already registered. Please sign in instead."
        })
    
    return jsonify({"exists": False, "message": "Email is available"})


@app.route("/api/auth/check-username", methods=["POST"])
def check_username():
    """Check if username already exists in the system"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({"exists": False, "error": "Username is required"}), 400
    
    if len(username) < 3:
        return jsonify({"exists": False, "error": "Username must be at least 3 characters"}), 400
    
    # Check if username exists
    existing_user = User.query.filter_by(username=username).first()
    
    if existing_user:
        return jsonify({
            "exists": True, 
            "message": "This username is already taken. Please choose another."
        })
    
    return jsonify({"exists": False, "message": "Username is available"})


@app.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    """Send OTP to user's email for verification"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    
    if not email:
        return jsonify({"error": "Email is required", "success": False}), 400
    
    # Validate email format
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({"error": "Invalid email format", "success": False}), 400
    
    # Check if username is taken
    if username and User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists", "success": False}), 400
    
    # Check if email is taken
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered", "success": False}), 400
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP with expiration (10 minutes)
    otp_storage[email] = {
        'otp': otp,
        'created': datetime.now(),
        'username': username
    }
    
    # Send OTP email
    if send_otp_email(email, otp, username):
        print(f"[OTP] Sent verification code to {email}")
        return jsonify({
            "success": True,
            "message": "Verification code sent to your email"
        })
    else:
        return jsonify({
            "error": "Failed to send verification email. Please try again.",
            "success": False
        }), 500


@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP and complete registration"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_encrypted = data.get('encrypted', False)
    
    # Decrypt password if encrypted
    if is_encrypted and request.headers.get('X-Encrypted') == 'true':
        try:
            password = decrypt_client_data(password)
            print("[SECURITY] Decrypted registration password successfully")
        except Exception as e:
            print(f"[WARN] Password decryption failed, using as-is: {e}")
    
    if not email or not otp:
        return jsonify({"error": "Email and OTP are required", "success": False}), 400
    
    # Check if OTP exists
    if email not in otp_storage:
        return jsonify({"error": "No verification code found. Please request a new one.", "success": False}), 400
    
    stored = otp_storage[email]
    
    # Check expiration (10 minutes)
    if (datetime.now() - stored['created']).total_seconds() > 600:
        del otp_storage[email]
        return jsonify({"error": "Verification code expired. Please request a new one.", "success": False}), 400
    
    # Verify OTP
    if stored['otp'] != otp:
        return jsonify({"error": "Invalid verification code", "success": False}), 400
    
    # OTP verified - create user account
    try:
        # Check again if user exists (race condition prevention)
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists", "success": False}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered", "success": False}), 400
        
        # Create user with verified email
        user = User(username=username, email=email, email_verified=True)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Clean up OTP
        del otp_storage[email]
        
        # Log user in
        login_user(user)
        
        print(f"[OTP] User {username} registered successfully with verified email")
        
        return jsonify({
            "success": True,
            "message": "Account created successfully!",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "email_verified": True
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[OTP] Registration error: {e}")
        return jsonify({"error": "Registration failed. Please try again.", "success": False}), 500


@app.route("/api/auth/firebase", methods=["POST"])
def firebase_auth():
    """Handle Firebase authentication (Google sign-in)"""
    data = request.get_json()
    
    id_token = data.get('idToken')
    provider = data.get('provider', 'google')
    email = data.get('email', '').strip().lower()
    display_name = data.get('displayName', '')
    photo_url = data.get('photoURL', '')
    
    if not email:
        return jsonify({"error": "Email is required", "success": False}), 400
    
    try:
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Existing user - log them in
            login_user(user)
            print(f"[FIREBASE] Existing user logged in: {user.username}")
        else:
            # New user - create account
            # Generate username from email or display name
            base_username = display_name.replace(' ', '').lower() if display_name else email.split('@')[0]
            username = base_username
            
            # Ensure unique username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user with verified email (OAuth means email is verified)
            user = User(
                username=username,
                email=email,
                email_verified=True
            )
            # Set a random password (user can reset if needed)
            import secrets
            user.set_password(secrets.token_urlsafe(32))
            
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            print(f"[FIREBASE] New user created via {provider}: {username}")
        
        return jsonify({
            "success": True,
            "message": f"Successfully signed in with {provider.title()}!",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "email_verified": user.email_verified,
                "is_admin": user.is_admin
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[FIREBASE] Auth error: {e}")
        return jsonify({"error": "Authentication failed. Please try again.", "success": False}), 500


@app.route("/api/current-user", methods=["GET"])
def current_user_info():
    """Get current logged in user info"""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "success": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "email_verified": current_user.email_verified,
                "is_admin": current_user.is_admin
            }
        })
    else:
        return jsonify({
            "authenticated": False,
            "success": False
        })


@app.route("/verify-email", methods=["GET"])
def verify_email():
    """Verify user email with token"""
    token = request.args.get('token')
    
    if not token:
        return """
        <html>
        <head><title>Invalid Link</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>❌ Invalid Verification Link</h1>
            <p>The verification link is invalid or missing.</p>
            <a href="http://localhost:5000/">Return to Chordis</a>
        </body>
        </html>
        """, 400
    
    # Verify token
    email = User.verify_token(token)
    
    if not email:
        return """
        <html>
        <head><title>Link Expired</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>⏰ Verification Link Expired</h1>
            <p>This verification link has expired or is invalid.</p>
            <p>Please request a new verification email from your account settings.</p>
            <a href="http://localhost:5000/" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">Return to Chordis</a>
        </body>
        </html>
        """, 400
    
    # Find user and verify email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return """
        <html>
        <head><title>User Not Found</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>❌ User Not Found</h1>
            <p>No user found with this email address.</p>
            <a href="http://localhost:5000/">Return to Chordis</a>
        </body>
        </html>
        """, 404
    
    if user.email_verified:
        return f"""
        <html>
        <head><title>Already Verified</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>✅ Email Already Verified</h1>
            <p>Your email address has already been verified.</p>
            <a href="http://localhost:5000/" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">Go to Chordis</a>
        </body>
        </html>
        """
    
    # Verify the user
    user.email_verified = True
    user.verification_token = None
    db.session.commit()
    
    return f"""
    <html>
    <head>
        <title>Email Verified!</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }}
            .container {{
                background: white;
                padding: 50px;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
            }}
            h1 {{ color: #667eea; margin-bottom: 20px; }}
            .checkmark {{
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 30px;
                font-size: 50px;
            }}
            a {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 40px;
                text-decoration: none;
                border-radius: 25px;
                display: inline-block;
                margin-top: 30px;
                font-weight: bold;
            }}
            a:hover {{ opacity: 0.9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✓</div>
            <h1>Email Verified Successfully!</h1>
            <p style="color: #666; font-size: 16px;">
                Welcome, <strong>{user.username}</strong>! Your email has been verified.
            </p>
            <p style="color: #999; font-size: 14px;">
                You can now enjoy all features of Chordis, including saving your analyses and more!
            </p>
            <a href="http://localhost:5000/">Start Analyzing Music</a>
        </div>
        <script>
            // Auto-redirect after 5 seconds
            setTimeout(function() {{
                window.location.href = 'http://localhost:5000/';
            }}, 5000);
        </script>
    </body>
    </html>
    """


@app.route("/api/resend-verification", methods=["POST"])
@api_login_required
def resend_verification():
    """Resend verification email"""
    if current_user.email_verified:
        return jsonify({"error": "Email already verified"}), 400
    
    # Generate new token
    token = current_user.generate_verification_token()
    current_user.verification_token = token
    db.session.commit()
    
    # Send email
    try:
        send_verification_email(current_user, token)
        return jsonify({
            "success": True,
            "message": "Verification email sent! Please check your inbox."
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to send email. Please try again later."
        }), 500


# ==================== SAVED ANALYSES ROUTES ====================

@app.route("/api/save-analysis", methods=["POST"])
@api_login_required
def save_analysis():
    """Save a music analysis"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Get title and artist
        title = data.get('title')
        artist = data.get('artist', '')
        
        # Format title with artist if separate
        if artist and artist not in title:
            full_title = f"{title} - {artist}"
        else:
            full_title = title
        
        chord_data = data.get('chord_data')
        lyrics_data = data.get('lyrics_data')
        source_type = data.get('source_type', 'file')
        source_url = data.get('source_url', '')
        
        print(f"[SAVE] Saving: {full_title}, source={source_type}, user={current_user.username}")
        
        if not title:
            return jsonify({"success": False, "error": "Title is required"}), 400
        
        if not chord_data:
            return jsonify({"success": False, "error": "Chord data is required"}), 400
            
        if not lyrics_data:
            return jsonify({"success": False, "error": "Lyrics data is required"}), 400
        
        # Create saved analysis
        analysis = SavedAnalysis(
            user_id=current_user.id,
            title=full_title,
            source_type=source_type,
            source_url=source_url
        )
        analysis.set_chord_data(chord_data)
        analysis.set_lyrics_data(lyrics_data)
        
        db.session.add(analysis)
        db.session.commit()
        
        print(f"[SAVE] SUCCESS - Analysis saved with ID: {analysis.id}")
        
        # Log save activity
        log_analysis_activity('save', title, artist, current_user.id)
        
        return jsonify({
            "success": True,
            "analysis": analysis.to_dict(),
            "message": "Analysis saved successfully"
        })
    
    except Exception as e:
        print(f"[ERROR] Save failed: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/saved-analyses", methods=["GET"])
@api_login_required
def get_saved_analyses():
    """Get all saved analyses for current user"""
    analyses = SavedAnalysis.query.filter_by(user_id=current_user.id).order_by(SavedAnalysis.created_at.desc()).all()
    
    return jsonify({
        "success": True,
        "analyses": [analysis.to_dict() for analysis in analyses]
    })


@app.route("/api/saved-analysis/<int:analysis_id>", methods=["GET"])
@api_login_required
def get_saved_analysis(analysis_id):
    """Get a specific saved analysis"""
    analysis = SavedAnalysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404
    
    return jsonify({
        "success": True,
        "analysis": analysis.to_dict()
    })


@app.route("/api/saved-analysis/<int:analysis_id>", methods=["DELETE"])
@api_login_required
def delete_saved_analysis(analysis_id):
    """Delete a saved analysis"""
    analysis = SavedAnalysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404
    
    db.session.delete(analysis)
    db.session.commit()
    
    return jsonify({"success": True})


@app.route("/api/saved-analysis/<int:analysis_id>", methods=["PUT"])
@api_login_required
def update_saved_analysis(analysis_id):
    """Update a saved analysis"""
    analysis = SavedAnalysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404
    
    data = request.get_json()
    
    if 'title' in data:
        analysis.title = data['title']
    if 'chord_data' in data:
        analysis.set_chord_data(data['chord_data'])
    if 'lyrics_data' in data:
        analysis.set_lyrics_data(data['lyrics_data'])
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "analysis": analysis.to_dict()
    })


# ==================== SONG SEARCH ROUTES ====================

@app.route("/api/search-and-analyze", methods=["POST"])
def search_and_analyze():
    """Search for a song and get its lyrics and download audio temporarily"""
    # Cleanup old cache files
    cleanup_old_cache()
    
    data = request.get_json()
    
    title = data.get('title', '')
    artist = data.get('artist', '')
    artwork = data.get('artwork', '')
    search_query = data.get('search_query', f"{artist} {title} official audio")
    
    if not title:
        return jsonify({"error": "Missing title"}), 400
    
    # Get lyrics from Genius
    print(f"[LYRICS] Fetching lyrics for: {title} by {artist}")
    lyrics_data = get_lyrics_from_genius(title, artist)
    
    if not lyrics_data:
        print(f"[LYRICS] Genius API did not find lyrics for: {title}")
    else:
        print(f"[LYRICS] Found {len(lyrics_data.get('text', '').split(chr(10)))} lines from {lyrics_data.get('source')}")
    
    # Download audio temporarily to serve it properly
    audio_url = None
    youtube_webpage_url = None
    audio_available = False
    
    try:
        import yt_dlp
        import hashlib
        
        # Create a unique filename based on search query
        file_hash = hashlib.md5(f"{artist}{title}".encode()).hexdigest()[:12]
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"chordis_{file_hash}.m4a")
        
        print(f"[AUDIO] Downloading audio for: {title}")
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': False,
            'no_warnings': False,
            'default_search': 'ytsearch1:',
            'outtmpl': temp_audio_path,
            # Don't use FFmpeg post-processor - just download as-is
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_result = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            if search_result and 'entries' in search_result and len(search_result['entries']) > 0:
                video = search_result['entries'][0]
                youtube_webpage_url = video.get('webpage_url')
                
                # yt-dlp might download with different extension - check for any downloaded file
                downloaded_file = None
                for ext in ['.m4a', '.webm', '.opus', '.mp4', '.mp3']:
                    check_path = temp_audio_path.replace('.m4a', ext)
                    if os.path.exists(check_path):
                        downloaded_file = check_path
                        actual_ext = ext
                        print(f"[AUDIO] [OK] Found downloaded file: {check_path}")
                        break
                
                if downloaded_file:
                    # Serve from our server
                    audio_url = f"/api/temp-audio/{file_hash}{actual_ext}"
                    audio_available = True
                    print(f"[AUDIO] [OK] Successfully downloaded audio")
                    print(f"[AUDIO] Serving at: {audio_url}")
                else:
                    print(f"[AUDIO] [WARNING] No audio file found after download")
                    print(f"[AUDIO] Checked path: {temp_audio_path}")
                    
    except Exception as e:
        print(f"[AUDIO ERROR] Could not download audio: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate chord progression - try ChordMiniApp first, then rule-based analysis
    chords = []
    detected_key = "C Major"
    detected_tempo = 120
    
    # STEP 1: Try ChordMiniApp for ML-based chord detection (301 chord types)
    if CHORDMINI_ENABLED and 'downloaded_file' in dir() and downloaded_file and os.path.exists(downloaded_file):
        try:
            print(f"[CHORDS] Attempting ChordMiniApp ML-based detection...")
            chordmini_chords = get_chords_from_chordmini(downloaded_file)
            if chordmini_chords and len(chordmini_chords) > 0:
                print(f"[CHORDS] ✓ ChordMiniApp returned {len(chordmini_chords)} chords")
                chords = chordmini_chords
        except Exception as e:
            print(f"[CHORDS] ChordMiniApp failed: {e}")
    
    # STEP 2: If no ChordMiniApp results and audio was downloaded, use rule-based analysis
    if not chords and 'downloaded_file' in dir() and downloaded_file and os.path.exists(downloaded_file):
        try:
            print(f"[CHORDS] Analyzing downloaded audio file for chords...")
            # Use our chord detection on the audio
            audio_data, sr = librosa.load(downloaded_file, sr=22050, duration=180)
            
            # Extract chroma features
            chroma = librosa.feature.chroma_cqt(y=audio_data, sr=sr, hop_length=512)
            
            # Segment the audio and detect chords
            segment_duration = 2.0  # 2 seconds per segment
            hop_samples = int(segment_duration * sr / 512)
            
            for i in range(0, chroma.shape[1], hop_samples):
                segment_chroma = np.mean(chroma[:, i:i+hop_samples], axis=1)
                chord_idx = chord_model.predict_from_chroma(segment_chroma)
                chord_name = CHORDS[chord_idx] if chord_idx < len(CHORDS) else 'C'
                
                start_time = i * 512 / sr
                end_time = min((i + hop_samples) * 512 / sr, len(audio_data) / sr)
                
                # Avoid duplicate consecutive chords
                if not chords or chords[-1]['chord'] != chord_name:
                    chords.append({
                        'chord': chord_name,
                        'name': chord_name,
                        'start_time': start_time,
                        'end_time': end_time,
                        'timestamp': start_time
                    })
            
            # Detect key and tempo
            try:
                tempo, _ = librosa.beat.beat_track(y=audio_data, sr=sr)
                detected_tempo = int(tempo) if tempo else 120
                print(f"[CHORDS] Detected tempo: {detected_tempo} BPM")
            except:
                pass
                
            print(f"[CHORDS] Detected {len(chords)} unique chord changes from audio")
            
        except Exception as e:
            print(f"[CHORDS] Audio analysis failed: {e}")
            import traceback
            traceback.print_exc()
    
    # STEP 3: Fallback - generate common progression if nothing else worked
    if not chords:
        print(f"[CHORDS] Using fallback chord progression")
        fallback_progression = ['C', 'G', 'Am', 'F', 'C', 'G', 'Am', 'F']
        for i, chord_name in enumerate(fallback_progression):
            chords.append({
                'chord': chord_name,
                'name': chord_name,
                'start_time': i * 15,
                'end_time': (i + 1) * 15,
                'timestamp': i * 15
            })
    
    # Prepare response
    lyrics_list = []
    lyrics_source = None
    
    if lyrics_data and lyrics_data.get('text'):
        # Split lyrics into lines
        lines = lyrics_data['text'].split('\n')
        lyrics_list = [{'text': line.strip(), 'timestamp': i * 10} for i, line in enumerate(lines) if line.strip()]
        lyrics_source = lyrics_data.get('source', 'genius')
        print(f"[LYRICS] Prepared {len(lyrics_list)} lyric lines from {lyrics_source}")
    else:
        print(f"[LYRICS] No lyrics available for this song")
    
    return jsonify({
        "success": True,
        "title": title,
        "artist": artist,
        "chords": chords,
        "lyrics": lyrics_list,
        "lyrics_source": lyrics_source,
        "has_lyrics": len(lyrics_list) > 0,
        "key": detected_key,
        "tempo": detected_tempo,
        "duration": len(lyrics_list) * 10 if lyrics_list else 180,
        "audio_url": audio_url,  # Downloaded audio served from our server
        "youtube_url": audio_url,  # Kept for backward compatibility
        "youtube_webpage_url": youtube_webpage_url,  # Permanent YouTube video page URL
        "audio_available": audio_available,
        "audio_expiry_note": "Audio downloaded and cached on server" if audio_available else None,
        "artwork": artwork if 'artwork' in locals() else None
    })


@app.route("/api/temp-audio/<filename>")
def serve_temp_audio(filename):
    """Serve temporarily downloaded audio files"""
    try:
        print(f"[SERVE] Request for audio file: {filename}")
        print(f"[SERVE] Temp directory: {tempfile.gettempdir()}")
        
        # Check if the file exists in temp directory
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"chordis_{filename}")
        print(f"[SERVE] Looking for: {temp_audio_path}")
        print(f"[SERVE] File exists: {os.path.exists(temp_audio_path)}")
        
        # List files in temp directory with chordis_ prefix for debugging
        import glob
        chordis_files = glob.glob(os.path.join(tempfile.gettempdir(), "chordis_*"))
        print(f"[SERVE] Available chordis files: {[os.path.basename(f) for f in chordis_files[:5]]}")
        
        if os.path.exists(temp_audio_path):
            # Determine mimetype based on extension
            ext = os.path.splitext(filename)[1].lower()
            mimetypes_map = {
                '.m4a': 'audio/mp4',
                '.mp4': 'audio/mp4',
                '.webm': 'audio/webm',
                '.opus': 'audio/opus',
                '.mp3': 'audio/mpeg'
            }
            mimetype = mimetypes_map.get(ext, 'audio/mpeg')
            
            print(f"[SERVE] [OK] Serving audio file: {temp_audio_path} as {mimetype}")
            return send_from_directory(
                tempfile.gettempdir(),
                f"chordis_{filename}",
                mimetype=mimetype
            )
        else:
            print(f"[SERVE ERROR] File not found: {temp_audio_path}")
            return jsonify({"error": "Audio file not found"}), 404
            
    except Exception as e:
        print(f"[SERVE ERROR] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/<filename>")
def serve_cached_audio(filename):
    """Serve cached audio files with Range header support for seeking"""
    try:
        print(f"[CACHE SERVE] Request for cached audio: {filename}")
        
        # Find the file in cache directory
        cache_path = AUDIO_CACHE_DIR / filename
        
        if not cache_path.exists():
            # Try without extension prefix
            for ext in ['.m4a', '.webm', '.opus', '.mp4', '.mp3', '.wav']:
                test_path = AUDIO_CACHE_DIR / f"{filename}{ext}"
                if test_path.exists():
                    cache_path = test_path
                    break
        
        if not cache_path.exists():
            print(f"[CACHE SERVE ERROR] File not found: {cache_path}")
            return jsonify({"error": "Audio file not found"}), 404
        
        # Determine mimetype
        ext = cache_path.suffix.lower()
        mimetypes_map = {
            '.m4a': 'audio/mp4',
            '.mp4': 'audio/mp4',
            '.webm': 'audio/webm',
            '.opus': 'audio/opus',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav'
        }
        mimetype = mimetypes_map.get(ext, 'audio/mpeg')
        
        file_size = cache_path.stat().st_size
        
        # Handle Range requests for seeking support
        range_header = request.headers.get('Range')
        
        if range_header:
            # Parse Range header
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            
            if start >= file_size:
                return Response(status=416)  # Range Not Satisfiable
            
            end = min(end, file_size - 1)
            length = end - start + 1
            
            def generate_range():
                with open(cache_path, 'rb') as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            
            response = Response(
                generate_range(),
                status=206,
                mimetype=mimetype,
                direct_passthrough=True
            )
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = length
            
            print(f"[CACHE SERVE] Serving range {start}-{end}/{file_size}")
            return response
        else:
            # Serve full file
            print(f"[CACHE SERVE] Serving full file: {cache_path} ({file_size} bytes)")
            response = send_from_directory(
                str(AUDIO_CACHE_DIR),
                filename,
                mimetype=mimetype
            )
            response.headers['Accept-Ranges'] = 'bytes'
            return response
            
    except Exception as e:
        print(f"[CACHE SERVE ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/refresh-audio-url", methods=["POST"])
def refresh_audio_url():
    """Refresh by re-downloading the audio"""
    try:
        data = request.get_json()
        youtube_webpage_url = data.get('youtube_webpage_url')
        
        if not youtube_webpage_url:
            return jsonify({"success": False, "error": "YouTube webpage URL required"}), 400
        
        print(f"[REFRESH] Re-downloading audio from: {youtube_webpage_url}")
        
        # Generate hash for filename
        import hashlib
        file_hash = hashlib.md5(youtube_webpage_url.encode()).hexdigest()[:12]
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"chordis_{file_hash}.m4a")
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': False,
            'no_warnings': False,
            'outtmpl': temp_audio_path,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_webpage_url])
            
        if os.path.exists(temp_audio_path):
            audio_url = f"/api/temp-audio/{file_hash}.m4a"
            print(f"[REFRESH] [OK] Successfully refreshed audio")
            return jsonify({
                "success": True,
                "audio_url": audio_url,
                "message": "Audio refreshed successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not download audio"
            }), 500
                
    except Exception as e:
        print(f"[REFRESH ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/proxy-audio")
def proxy_audio():
    """Proxy YouTube audio through our server to bypass CORS restrictions"""
    audio_url = request.args.get('url')
    
    if not audio_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        print(f"[PROXY] Proxying audio from: {audio_url[:80]}...")
        
        # Make request with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Range': request.headers.get('Range', 'bytes=0-')
        }
        
        response = requests.get(audio_url, headers=headers, stream=True, timeout=10)
        
        if response.status_code not in [200, 206]:
            print(f"[PROXY ERROR] Status {response.status_code}")
            return jsonify({"error": f"Upstream returned {response.status_code}"}), 502
        
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        print(f"[PROXY] Streaming audio successfully")
        
        resp = Response(stream_with_context(generate()), status=response.status_code)
        resp.headers['Content-Type'] = response.headers.get('Content-Type', 'audio/mp4')
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        
        if 'Content-Length' in response.headers:
            resp.headers['Content-Length'] = response.headers['Content-Length']
        if 'Content-Range' in response.headers:
            resp.headers['Content-Range'] = response.headers['Content-Range']
            
        return resp
        
    except requests.exceptions.Timeout:
        print(f"[PROXY ERROR] Timeout")
        return jsonify({"error": "Upstream timeout"}), 504
    except Exception as e:
        print(f"[PROXY ERROR] {type(e).__name__}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/recognize-from-chords", methods=["POST"])
def recognize_from_chords():
    """Recognize song from chord progression pattern (basic implementation)"""
    data = request.get_json()
    
    chords = data.get('chords', [])
    duration = data.get('duration', 5)
    
    if not chords:
        return jsonify({"success": False, "error": "No chord data"}), 400
    
    # Extract chord names
    chord_sequence = [c.get('chord', '') for c in chords]
    
    # Basic pattern matching (in production, use audio fingerprinting service like AcoustID)
    # For now, return a match based on common patterns
    common_songs = [
        {
            'title': 'Let It Be',
            'artist': 'The Beatles',
            'pattern': ['C', 'G', 'Am', 'F'],
            'artwork': 'https://via.placeholder.com/200/6366f1/ffffff?text=Beatles'
        },
        {
            'title': 'Someone Like You',
            'artist': 'Adele',
            'pattern': ['C', 'Am', 'F', 'G'],
            'artwork': 'https://via.placeholder.com/200/ec4899/ffffff?text=Adele'
        },
        {
            'title': 'No Woman No Cry',
            'artist': 'Bob Marley',
            'pattern': ['C', 'G', 'Am', 'F'],
            'artwork': 'https://via.placeholder.com/200/10b981/ffffff?text=Marley'
        }
    ]
    
    # Try to match pattern
    for song in common_songs:
        if any(c in song['pattern'] for c in chord_sequence):
            return jsonify({
                "success": True,
                "song": song,
                "confidence": 0.75
            })
    
    return jsonify({
        "success": False,
        "message": "Could not identify song. Try playing more of it!"
    })


@app.route("/api/search-songs", methods=["POST"])
def search_songs():
    """Search for songs using Genius API"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Query is required", "success": False}), 400
        
        results = []
        
        # Try Genius API directly (more reliable than lyricsgenius search)
        if GENIUS_ACCESS_TOKEN:
            try:
                print(f"[SEARCH] Searching Genius for: {query}")
                
                # Use Genius API directly
                headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}
                search_url = 'https://api.genius.com/search'
                params = {'q': query}
                
                response = requests.get(search_url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    response_data = response.json()
                    hits = response_data.get('response', {}).get('hits', [])
                    
                    for hit in hits[:10]:  # Limit to 10 results
                        result_data = hit.get('result', {})
                        results.append({
                            'title': result_data.get('title', 'Unknown'),
                            'artist': result_data.get('primary_artist', {}).get('name', 'Unknown Artist'),
                            'album': result_data.get('album', {}).get('name', '') if result_data.get('album') else '',
                            'artwork': result_data.get('song_art_image_thumbnail_url', ''),
                            'thumbnail': result_data.get('header_image_thumbnail_url', ''),
                            'url': result_data.get('url', ''),
                            'id': result_data.get('id', '')
                        })
                    
                    print(f"[SEARCH] Found {len(results)} results")
                else:
                    print(f"[ERROR] Genius API returned status {response.status_code}")
                    
            except Exception as e:
                print(f"[ERROR] Genius search error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("[INFO] Genius API token not configured")
        
        # Fallback: Create mock results if Genius not available or no results found
        if not results:
            print(f"[FALLBACK] Creating mock result for: {query}")
            # Parse query to extract possible artist and song
            query_parts = query.split()
            results = [
                {
                    'title': ' '.join(query_parts[:3]) if len(query_parts) >= 3 else query,
                    'artist': ' '.join(query_parts[3:]) if len(query_parts) > 3 else 'Various Artists',
                    'album': '',
                    'artwork': '',
                    'thumbnail': '',
                    'url': '',
                    'id': '1'
                }
            ]
        
        # Log search activity
        user_id = current_user.id if current_user.is_authenticated else None
        log_search(query, 'song', len(results), user_id)
        
        return jsonify({
            "success": True,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        print(f"[ERROR] Search endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "results": []
        }), 500


@app.route("/api/get-lyrics", methods=["POST"])
def get_lyrics():
    """Get lyrics for a specific song"""
    data = request.get_json()
    title = data.get('title', '').strip()
    artist = data.get('artist', '').strip()
    
    if not title:
        return jsonify({"error": "Song title is required"}), 400
    
    if not genius:
        return jsonify({
            "success": False,
            "error": "Lyrics service is not available. Please configure Genius API token."
        }), 503
    
    try:
        print(f"Getting lyrics for: {title} by {artist}")
        
        # Search for the specific song
        if artist:
            song = genius.search_song(title, artist)
        else:
            song = genius.search_song(title)
        
        if song and song.lyrics:
            # Clean up lyrics
            lyrics_text = song.lyrics
            # Remove common patterns that might appear in Genius lyrics
            lyrics_text = re.sub(r'\[.*?\]', '', lyrics_text)  # Remove [Verse], [Chorus], etc.
            lyrics_text = re.sub(r'\n\s*\n', '\n\n', lyrics_text)  # Clean up extra newlines
            lyrics_text = lyrics_text.strip()
            
            return jsonify({
                "success": True,
                "lyrics": {
                    "text": lyrics_text,
                    "source": "genius",
                    "title": song.title,
                    "artist": song.artist,
                    "url": song.url if hasattr(song, 'url') else None
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": "No lyrics found for this song"
            }), 404
            
    except Exception as e:
        print(f"Error getting lyrics: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve lyrics. Please try again."
        }), 500


# ==================== ADMIN ROUTES ====================

@app.route("/admin", methods=["GET"])
def admin_page():
    """Serve admin dashboard (auth check done in frontend)"""
    return send_from_directory('static', 'admin.html')

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def get_all_users():
    """Get all users for admin dashboard"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'email_verified': user.email_verified,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat(),
                'saved_analyses_count': len(user.saved_analyses)
            })
        
        return jsonify({
            'success': True,
            'users': users_data,
            'total_count': len(users_data)
        })
    except Exception as e:
        print(f"[ADMIN ERROR] Failed to get users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/admin/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user_details(user_id):
    """Get detailed info for a specific user"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'email_verified': user.email_verified,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat(),
                'saved_analyses': [a.to_dict() for a in user.saved_analyses]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/admin/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    """Update user information"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Prevent admins from demoting themselves
        if user.id == current_user.id and 'is_admin' in request.json:
            if not request.json['is_admin']:
                return jsonify({'success': False, 'error': 'Cannot remove your own admin status'}), 400
        
        data = request.json
        
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'email_verified' in data:
            user.email_verified = data['email_verified']
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        
        db.session.commit()
        
        print(f"[ADMIN] User {user.username} updated by {current_user.username}")
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'email_verified': user.email_verified,
                'is_admin': user.is_admin
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN ERROR] Failed to update user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Prevent admins from deleting themselves
        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        print(f"[ADMIN] User {username} deleted by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'User {username} deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN ERROR] Failed to delete user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/check-admin", methods=["GET"])
def check_admin():
    """Check if admin exists and list all users (for debugging)"""
    try:
        users = User.query.all()
        admin = User.query.filter_by(is_admin=True).first()
        return jsonify({
            'success': True,
            'admin_exists': admin is not None,
            'admin_username': admin.username if admin else None,
            'total_users': len(users),
            'users': [{'id': u.id, 'username': u.username, 'is_admin': u.is_admin} for u in users]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/seed-tutorials", methods=["POST"])
def seed_tutorials():
    """Seed default tutorials including external tools"""
    try:
        # Default tutorials data
        default_tutorials = [
            {
                'title': 'Chromatone Helper - Chord Progression Tool',
                'description': 'A powerful web-based tool to create chord progressions and arpeggios, visualize them on different instruments, and export as MIDI. Perfect for learning music theory and composition.',
                'content_type': 'tool',
                'skill_level': 'all',
                'content': '''
## Features
- Create chord progressions and arpeggios using a declarative DSL
- Visualize music on guitar, piano, bass, and more
- Visual cues show which notes to play - no staff notation needed!
- Export your creations as MIDI files
- Works offline on mobile browsers

## Quick Examples
- Jazz progression: `2 5 1`
- Pachelbel's Canon: `1 5 6 3 4 1 4 5`
- D# major scale: `1 2 3 4 5 6 7 k=D#4`

## Try It Now
Click the link below to open the multi-track sequencer!
                ''',
                'video_url': 'https://iostream.github.io/chromatone-helper/multi-track-sequencer/',
                'thumbnail': 'https://opengraph.githubassets.com/1/iostream/chromatone-helper',
                'duration': None,
                'order': 1,
                'is_published': True
            },
            {
                'title': 'Guitar Chord Basics for Beginners',
                'description': 'Learn the essential open chords every guitarist needs to know: C, G, D, E, A, and Am.',
                'content_type': 'video',
                'skill_level': 'beginner',
                'content': 'Master the fundamental open chords that form the foundation of thousands of songs.',
                'video_url': 'https://www.youtube.com/watch?v=4nJUxrDzpoo',
                'thumbnail': 'https://img.youtube.com/vi/4nJUxrDzpoo/maxresdefault.jpg',
                'duration': 12,
                'order': 2,
                'is_published': True
            },
            {
                'title': 'Understanding Music Theory: Keys & Scales',
                'description': 'Learn how keys and scales work together to create harmonious music.',
                'content_type': 'video',
                'skill_level': 'beginner',
                'content': 'A comprehensive guide to understanding musical keys, major and minor scales.',
                'video_url': 'https://www.youtube.com/watch?v=rgaTLrZGlk0',
                'thumbnail': 'https://img.youtube.com/vi/rgaTLrZGlk0/maxresdefault.jpg',
                'duration': 18,
                'order': 3,
                'is_published': True
            },
            {
                'title': 'Piano Chords for Beginners',
                'description': 'Start playing piano with these essential chord shapes and progressions.',
                'content_type': 'video',
                'skill_level': 'beginner',
                'content': 'Learn to play beautiful piano chords with proper finger positioning.',
                'video_url': 'https://www.youtube.com/watch?v=fevKfNIUJLk',
                'thumbnail': 'https://img.youtube.com/vi/fevKfNIUJLk/maxresdefault.jpg',
                'duration': 15,
                'order': 4,
                'is_published': True
            },
            {
                'title': 'Barre Chords Made Easy',
                'description': 'Master barre chords with these tips and exercises for guitar players.',
                'content_type': 'video',
                'skill_level': 'intermediate',
                'content': 'Overcome the barre chord challenge with proper technique and practice methods.',
                'video_url': 'https://www.youtube.com/watch?v=DrlF4Tc8qC8',
                'thumbnail': 'https://img.youtube.com/vi/DrlF4Tc8qC8/maxresdefault.jpg',
                'duration': 14,
                'order': 5,
                'is_published': True
            },
            {
                'title': 'Circle of Fifths Explained',
                'description': 'Understand the circle of fifths and how to use it for songwriting and improvisation.',
                'content_type': 'video',
                'skill_level': 'intermediate',
                'content': 'The circle of fifths is a powerful tool for understanding music theory.',
                'video_url': 'https://www.youtube.com/watch?v=d1aJ6HixSe0',
                'thumbnail': 'https://img.youtube.com/vi/d1aJ6HixSe0/maxresdefault.jpg',
                'duration': 11,
                'order': 6,
                'is_published': True
            }
        ]
        
        added_count = 0
        for tutorial_data in default_tutorials:
            # Check if tutorial with same title exists
            existing = Tutorial.query.filter_by(title=tutorial_data['title']).first()
            if not existing:
                tutorial = Tutorial(**tutorial_data)
                db.session.add(tutorial)
                added_count += 1
        
        db.session.commit()
        
        total_tutorials = Tutorial.query.count()
        
        return jsonify({
            'success': True,
            'message': f'Added {added_count} new tutorials',
            'total_tutorials': total_tutorials
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/setup-admin", methods=["POST"])
def setup_admin():
    """
    One-time admin setup - only works if no admin exists yet
    POST /api/setup-admin with JSON: {"username": "admin", "email": "admin@example.com", "password": "yourpassword"}
    """
    try:
        # Check if any admin already exists
        existing_admin = User.query.filter_by(is_admin=True).first()
        if existing_admin:
            return jsonify({
                'success': False, 
                'error': 'Admin already exists. Use the admin panel to manage users.'
            }), 400
        
        data = request.get_json()
        username = data.get('username', 'admin')
        email = data.get('email', 'admin@chordis.com')
        password = data.get('password')
        
        if not password or len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
        # Check if username/email already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Create admin user
        admin = User(username=username, email=email, email_verified=True, is_admin=True)
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"[ADMIN SETUP] Admin user '{username}' created successfully!")
        
        return jsonify({
            'success': True,
            'message': f'Admin user "{username}" created successfully!',
            'credentials': {
                'username': username,
                'email': email
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN SETUP ERROR] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        total_users = User.query.count()
        verified_users = User.query.filter_by(email_verified=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        total_analyses = SavedAnalysis.query.count()
        
        # Recent registrations (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = User.query.filter(User.created_at >= week_ago).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'verified_users': verified_users,
                'admin_users': admin_users,
                'total_analyses': total_analyses,
                'recent_users': recent_users
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/admin/reset-password/<int:user_id>", methods=["POST"])
@admin_required
def admin_reset_password(user_id):
    """Admin can reset user password"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        data = request.json
        new_password = data.get('new_password')
        
        if not new_password or len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
        user.set_password(new_password)
        db.session.commit()
        
        print(f"[ADMIN] Password reset for {user.username} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== LOGGING HELPER FUNCTIONS ====================

def log_search(query, search_type, results_count, user_id=None):
    """Log a search query for analytics"""
    try:
        search_log = SearchLog(
            user_id=user_id,
            search_query=query,
            search_type=search_type,
            results_count=results_count
        )
        db.session.add(search_log)
        db.session.commit()
    except Exception as e:
        print(f"[LOGGING ERROR] Failed to log search: {e}")
        db.session.rollback()


def log_recognition(song_title, artist, source, confidence, user_id=None):
    """Log a song recognition for analytics"""
    try:
        recognition_log = SongRecognitionLog(
            user_id=user_id,
            song_title=song_title,
            artist=artist,
            recognition_source=source,
            confidence=confidence
        )
        db.session.add(recognition_log)
        db.session.commit()
    except Exception as e:
        print(f"[LOGGING ERROR] Failed to log recognition: {e}")
        db.session.rollback()


def log_analysis_activity(activity_type, song_title, artist=None, user_id=None):
    """Log an analysis activity for analytics"""
    try:
        activity_log = AnalysisActivityLog(
            user_id=user_id,
            activity_type=activity_type,
            song_title=song_title,
            artist=artist or 'Unknown'
        )
        db.session.add(activity_log)
        db.session.commit()
    except Exception as e:
        print(f"[LOGGING ERROR] Failed to log activity: {e}")
        db.session.rollback()


# ==================== TUTORIAL ROUTES ====================

@app.route("/tutorials", methods=["GET"])
def tutorials_page():
    """Serve the tutorials page"""
    return send_from_directory('static', 'tutorials.html')


@app.route("/api/tutorials", methods=["GET"])
def get_tutorials():
    """Get tutorials with optional filtering"""
    try:
        skill_level = request.args.get('skill_level', 'all')
        content_type = request.args.get('content_type', 'all')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Tutorial.query.filter_by(is_published=True)
        
        if skill_level and skill_level != 'all':
            query = query.filter_by(skill_level=skill_level)
        
        if content_type and content_type != 'all':
            query = query.filter_by(content_type=content_type)
        
        tutorials = query.order_by(Tutorial.order, Tutorial.created_at.desc()).offset(offset).limit(limit).all()
        
        return jsonify({
            'success': True,
            'tutorials': [t.to_dict() for t in tutorials],
            'count': len(tutorials)
        })
    except Exception as e:
        print(f"[ERROR] Failed to get tutorials: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/tutorial/<int:id>", methods=["GET"])
def get_tutorial(id):
    """Get a single tutorial by ID"""
    try:
        tutorial = Tutorial.query.get(id)
        if not tutorial:
            return jsonify({'success': False, 'error': 'Tutorial not found'}), 404
        
        return jsonify({
            'success': True,
            'tutorial': tutorial.to_dict()
        })
    except Exception as e:
        print(f"[ERROR] Failed to get tutorial: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/admin/tutorials", methods=["POST"])
@admin_required
def create_tutorial():
    """Create a new tutorial (admin only)"""
    try:
        data = request.get_json()
        
        tutorial = Tutorial(
            title=data.get('title'),
            description=data.get('description'),
            content_type=data.get('content_type'),
            skill_level=data.get('skill_level'),
            content=data.get('content'),
            video_url=data.get('video_url'),
            thumbnail=data.get('thumbnail'),
            duration=data.get('duration'),
            order=data.get('order', 0),
            is_published=data.get('is_published', True)
        )
        
        db.session.add(tutorial)
        db.session.commit()
        
        print(f"[ADMIN] Tutorial created: {tutorial.title}")
        
        return jsonify({
            'success': True,
            'tutorial': tutorial.to_dict(),
            'message': 'Tutorial created successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN ERROR] Failed to create tutorial: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/admin/tutorials/<int:id>", methods=["PUT"])
@admin_required
def update_tutorial(id):
    """Update a tutorial (admin only)"""
    try:
        tutorial = Tutorial.query.get(id)
        if not tutorial:
            return jsonify({'success': False, 'error': 'Tutorial not found'}), 404
        
        data = request.get_json()
        
        if 'title' in data:
            tutorial.title = data['title']
        if 'description' in data:
            tutorial.description = data['description']
        if 'content_type' in data:
            tutorial.content_type = data['content_type']
        if 'skill_level' in data:
            tutorial.skill_level = data['skill_level']
        if 'content' in data:
            tutorial.content = data['content']
        if 'video_url' in data:
            tutorial.video_url = data['video_url']
        if 'thumbnail' in data:
            tutorial.thumbnail = data['thumbnail']
        if 'duration' in data:
            tutorial.duration = data['duration']
        if 'order' in data:
            tutorial.order = data['order']
        if 'is_published' in data:
            tutorial.is_published = data['is_published']
        
        tutorial.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"[ADMIN] Tutorial updated: {tutorial.title}")
        
        return jsonify({
            'success': True,
            'tutorial': tutorial.to_dict(),
            'message': 'Tutorial updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN ERROR] Failed to update tutorial: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/admin/tutorials/<int:id>", methods=["DELETE"])
@admin_required
def delete_tutorial(id):
    """Delete a tutorial (admin only)"""
    try:
        tutorial = Tutorial.query.get(id)
        if not tutorial:
            return jsonify({'success': False, 'error': 'Tutorial not found'}), 404
        
        title = tutorial.title
        db.session.delete(tutorial)
        db.session.commit()
        
        print(f"[ADMIN] Tutorial deleted: {title}")
        
        return jsonify({
            'success': True,
            'message': f'Tutorial "{title}" deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN ERROR] Failed to delete tutorial: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ANALYTICS ROUTES ====================

@app.route("/analytics", methods=["GET"])
def analytics_page():
    """Serve the analytics page"""
    return send_from_directory('static', 'analytics.html')


@app.route("/api/analytics/stats", methods=["GET"])
def get_analytics_stats():
    """Get general analytics statistics"""
    try:
        from datetime import timedelta
        from sqlalchemy import func
        
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total counts
        total_searches = SearchLog.query.filter(SearchLog.timestamp >= cutoff_date).count()
        total_recognitions = SongRecognitionLog.query.filter(SongRecognitionLog.timestamp >= cutoff_date).count()
        total_analyses = AnalysisActivityLog.query.filter(AnalysisActivityLog.timestamp >= cutoff_date).count()
        
        # Top song
        top_song = db.session.query(
            SongRecognitionLog.song_title,
            SongRecognitionLog.artist,
            func.count(SongRecognitionLog.id).label('count')
        ).filter(SongRecognitionLog.timestamp >= cutoff_date)\
         .group_by(SongRecognitionLog.song_title, SongRecognitionLog.artist)\
         .order_by(func.count(SongRecognitionLog.id).desc())\
         .first()
        
        top_song_data = None
        if top_song:
            top_song_data = {
                'title': top_song[0],
                'artist': top_song[1],
                'count': top_song[2]
            }
        
        return jsonify({
            'success': True,
            'stats': {
                'total_searches': total_searches,
                'total_recognitions': total_recognitions,
                'total_analyses': total_analyses,
                'top_song': top_song_data
            }
        })
    except Exception as e:
        print(f"[ERROR] Failed to get analytics stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/analytics/popular-searches", methods=["GET"])
def get_popular_searches():
    """Get most popular search queries"""
    try:
        from datetime import timedelta
        from sqlalchemy import func
        
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 30, type=int)
        search_type = request.args.get('search_type', 'all')
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.session.query(
            SearchLog.search_query,
            SearchLog.search_type,
            func.count(SearchLog.id).label('count')
        ).filter(SearchLog.timestamp >= cutoff_date)
        
        if search_type and search_type != 'all':
            query = query.filter_by(search_type=search_type)
        
        results = query.group_by(SearchLog.search_query, SearchLog.search_type)\
                       .order_by(func.count(SearchLog.id).desc())\
                       .limit(limit)\
                       .all()
        
        searches = [{'query': r[0], 'type': r[1], 'count': r[2]} for r in results]
        
        return jsonify({
            'success': True,
            'searches': searches,
            'count': len(searches)
        })
    except Exception as e:
        print(f"[ERROR] Failed to get popular searches: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/analytics/popular-songs", methods=["GET"])
def get_popular_songs():
    """Get most recognized/analyzed songs"""
    try:
        from datetime import timedelta
        from sqlalchemy import func
        
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 30, type=int)
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        results = db.session.query(
            SongRecognitionLog.song_title,
            SongRecognitionLog.artist,
            func.count(SongRecognitionLog.id).label('count')
        ).filter(SongRecognitionLog.timestamp >= cutoff_date)\
         .group_by(SongRecognitionLog.song_title, SongRecognitionLog.artist)\
         .order_by(func.count(SongRecognitionLog.id).desc())\
         .limit(limit)\
         .all()
        
        songs = [{'title': r[0], 'artist': r[1], 'count': r[2]} for r in results]
        
        return jsonify({
            'success': True,
            'songs': songs,
            'count': len(songs)
        })
    except Exception as e:
        print(f"[ERROR] Failed to get popular songs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/analytics/popular-lyrics", methods=["GET"])
def get_popular_lyrics():
    """Get most searched lyrics"""
    try:
        from datetime import timedelta
        from sqlalchemy import func
        
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 30, type=int)
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        results = db.session.query(
            SearchLog.search_query,
            func.count(SearchLog.id).label('count')
        ).filter(SearchLog.timestamp >= cutoff_date)\
         .filter_by(search_type='lyrics')\
         .group_by(SearchLog.search_query)\
         .order_by(func.count(SearchLog.id).desc())\
         .limit(limit)\
         .all()
        
        lyrics = [{'query': r[0], 'count': r[1]} for r in results]
        
        return jsonify({
            'success': True,
            'lyrics': lyrics,
            'count': len(lyrics)
        })
    except Exception as e:
        print(f"[ERROR] Failed to get popular lyrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/analytics/activity-timeline", methods=["GET"])
def get_activity_timeline():
    """Get activity timeline for charts"""
    try:
        from datetime import timedelta
        from sqlalchemy import func, cast, Date
        
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Searches per day
        searches = db.session.query(
            func.date(SearchLog.timestamp).label('date'),
            func.count(SearchLog.id).label('count')
        ).filter(SearchLog.timestamp >= cutoff_date)\
         .group_by(func.date(SearchLog.timestamp))\
         .order_by(func.date(SearchLog.timestamp))\
         .all()
        
        # Recognitions per day
        recognitions = db.session.query(
            func.date(SongRecognitionLog.timestamp).label('date'),
            func.count(SongRecognitionLog.id).label('count')
        ).filter(SongRecognitionLog.timestamp >= cutoff_date)\
         .group_by(func.date(SongRecognitionLog.timestamp))\
         .order_by(func.date(SongRecognitionLog.timestamp))\
         .all()
        
        # Analyses per day
        analyses = db.session.query(
            func.date(AnalysisActivityLog.timestamp).label('date'),
            func.count(AnalysisActivityLog.id).label('count')
        ).filter(AnalysisActivityLog.timestamp >= cutoff_date)\
         .group_by(func.date(AnalysisActivityLog.timestamp))\
         .order_by(func.date(AnalysisActivityLog.timestamp))\
         .all()
        
        timeline_data = {
            'searches': [{'date': str(r[0]), 'count': r[1]} for r in searches],
            'recognitions': [{'date': str(r[0]), 'count': r[1]} for r in recognitions],
            'analyses': [{'date': str(r[0]), 'count': r[1]} for r in analyses]
        }
        
        return jsonify({
            'success': True,
            'timeline': timeline_data
        })
    except Exception as e:
        print(f"[ERROR] Failed to get activity timeline: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/log-activity", methods=["POST"])
def log_activity_endpoint():
    """Endpoint for frontend to log activities"""
    try:
        data = request.get_json()
        activity_type = data.get('activity_type')
        song_title = data.get('song_title')
        artist = data.get('artist')
        
        user_id = current_user.id if current_user.is_authenticated else None
        
        log_analysis_activity(activity_type, song_title, artist, user_id)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Failed to log activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STATIC FILE ROUTES ====================
# (Routes already defined above - no duplicates needed)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


def start_chordmini_service():
    """Auto-start ChordMiniApp service if available"""
    import subprocess
    import sys
    
    # Define possible ChordMini paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chordmini_paths = [
        os.path.join(script_dir, 'chordmini', 'python_backend', 'app.py'),
        os.path.join(script_dir, '..', 'chordmini', 'python_backend', 'app.py'),
        os.path.join(script_dir, 'ChordMiniApp', 'python_backend', 'app.py'),
        # Also check Documents/nns folder (common installation location)
        r'C:\Users\Administrator\Documents\nns\chordmini\python_backend\app.py',
        os.path.expanduser('~/Documents/nns/chordmini/python_backend/app.py'),
    ]
    
    chordmini_app = None
    chordmini_dir = None
    
    for path in chordmini_paths:
        if os.path.exists(path):
            chordmini_app = path
            chordmini_dir = os.path.dirname(path)
            break
    
    if not chordmini_app:
        print("[CHORDMINI-AUTO] ChordMiniApp not found in expected locations:")
        for p in chordmini_paths:
            print(f"  - {p}")
        print("[CHORDMINI-AUTO] To install: git clone https://github.com/ptnghia-j/ChordMiniApp.git chordmini")
        return None
    
    # Check if ChordMini is already running
    try:
        response = requests.get(f"{CHORDMINI_API_URL}/", timeout=2)
        if response.status_code in [200, 404]:
            print(f"[CHORDMINI-AUTO] ✓ Already running at {CHORDMINI_API_URL}")
            return None
    except:
        pass
    
    print(f"[CHORDMINI-AUTO] Starting ChordMiniApp from: {chordmini_app}")
    
    try:
        # Start ChordMini as a background process
        if sys.platform == 'win32':
            # Windows - use CREATE_NEW_CONSOLE for separate window
            process = subprocess.Popen(
                [sys.executable, 'app.py'],
                cwd=chordmini_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Linux/Mac
            process = subprocess.Popen(
                [sys.executable, 'app.py'],
                cwd=chordmini_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        print(f"[CHORDMINI-AUTO] ✓ Started ChordMiniApp (PID: {process.pid})")
        
        # Wait a moment for it to initialize
        import time
        time.sleep(3)
        
        # Verify it started
        try:
            response = requests.get(f"{CHORDMINI_API_URL}/", timeout=5)
            if response.status_code in [200, 404]:
                print(f"[CHORDMINI-AUTO] ✓ ChordMiniApp is responding at {CHORDMINI_API_URL}")
                return process
        except:
            print(f"[CHORDMINI-AUTO] ⚠ ChordMiniApp started but not responding yet")
            print(f"[CHORDMINI-AUTO] It may still be loading models...")
        
        return process
        
    except Exception as e:
        print(f"[CHORDMINI-AUTO] ✗ Failed to start ChordMiniApp: {e}")
        return None


if __name__ == "__main__":
    # Auto-start ChordMiniApp if available (only for local development, not production)
    chordmini_process = None
    is_reloader = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('FLASK_ENV') == 'production'
    
    if CHORDMINI_ENABLED and not is_reloader and not is_production:
        chordmini_process = start_chordmini_service()
    elif is_production:
        print("[CHORDMINI-AUTO] Skipped - Running in production mode")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        print("[OK] Database initialized")
    
    # Get port from environment variable (for Railway/Render) or use 5000 for local
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    
    print("\n" + "="*50)
    print("    CHORDIS SERVER STARTED")
    print("="*50)
    print(f"Access the app at: http://localhost:{port}/")
    print(f"Debug mode: {debug_mode}")
    if chordmini_process:
        print(f"ChordMiniApp: Running (PID {chordmini_process.pid})")
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    try:
        app.run(host="0.0.0.0", port=port, debug=debug_mode)
    finally:
        # Clean up ChordMini process on exit
        if chordmini_process:
            print("\n[CLEANUP] Stopping ChordMiniApp...")
            try:
                chordmini_process.terminate()
                chordmini_process.wait(timeout=5)
                print("[CLEANUP] ChordMiniApp stopped")
            except:
                chordmini_process.kill()
                print("[CLEANUP] ChordMiniApp force killed")
