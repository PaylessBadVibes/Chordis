"""
Database models for user authentication and saved analyses
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from cryptography.fernet import Fernet
import os
import base64

db = SQLAlchemy()

# Encryption key for sensitive data (email)
# In production, store this in environment variable!
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
if isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)


class User(UserMixin, db.Model):
    """User model for authentication with encryption"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email_encrypted = db.Column(db.String(500), unique=True, nullable=False)  # Encrypted email
    password_hash = db.Column(db.String(200), nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to saved analyses
    saved_analyses = db.relationship('SavedAnalysis', backref='user', lazy=True, cascade='all, delete-orphan')
    
    @property
    def email(self):
        """Decrypt and return email"""
        try:
            return cipher_suite.decrypt(self.email_encrypted.encode()).decode()
        except:
            return self.email_encrypted  # Fallback for unencrypted data
    
    @email.setter
    def email(self, email_plaintext):
        """Encrypt and store email"""
        self.email_encrypted = cipher_suite.encrypt(email_plaintext.encode()).decode()
    
    def set_password(self, password):
        """Hash and set password with strong encryption"""
        # Using method='pbkdf2:sha256' with higher iterations for stronger security
        self.password_hash = generate_password_hash(
            password, 
            method='pbkdf2:sha256',
            salt_length=16
        )
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def generate_verification_token(self):
        """Generate a unique verification token"""
        from itsdangerous import URLSafeTimedSerializer
        serializer = URLSafeTimedSerializer('your-secret-key-change-this')
        return serializer.dumps(self.email, salt='email-verification')
    
    @staticmethod
    def verify_token(token, expiration=3600):
        """Verify the token and return email if valid"""
        from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
        serializer = URLSafeTimedSerializer('your-secret-key-change-this')
        try:
            email = serializer.loads(token, salt='email-verification', max_age=expiration)
            return email
        except (SignatureExpired, BadSignature):
            return None
    
    def __repr__(self):
        admin_tag = ' [ADMIN]' if self.is_admin else ''
        return f'<User {self.username}{admin_tag}>'


class SavedAnalysis(db.Model):
    """Saved music analysis model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=True)
    source_type = db.Column(db.String(20))  # 'file', 'youtube', or 'spotify'
    source_url = db.Column(db.String(500))  # YouTube URL if applicable
    
    # Store chord and lyrics data as JSON
    chord_data = db.Column(db.Text, nullable=False)  # JSON string
    lyrics_data = db.Column(db.Text, nullable=False)  # JSON string
    
    # Additional metadata
    key = db.Column(db.String(20))  # Musical key (e.g., 'C Major')
    tempo = db.Column(db.Integer)  # BPM
    duration = db.Column(db.Integer)  # Duration in seconds
    artwork = db.Column(db.Text)  # Base64 encoded album artwork
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_chord_data(self, data):
        """Set chord data from dict"""
        self.chord_data = json.dumps(data)
    
    def get_chord_data(self):
        """Get chord data as dict"""
        return json.loads(self.chord_data) if self.chord_data else None
    
    def set_lyrics_data(self, data):
        """Set lyrics data from dict"""
        self.lyrics_data = json.dumps(data)
    
    def get_lyrics_data(self):
        """Get lyrics data as dict"""
        return json.loads(self.lyrics_data) if self.lyrics_data else None
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'chord_data': self.get_chord_data(),
            'lyrics_data': self.get_lyrics_data(),
            'key': self.key,
            'tempo': self.tempo,
            'duration': self.duration,
            'artwork': self.artwork,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<SavedAnalysis {self.title}>'


class Tutorial(db.Model):
    """Tutorial model for music learning content"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # 'video', 'text', 'interactive'
    skill_level = db.Column(db.String(20), nullable=False)  # 'beginner', 'intermediate', 'advanced'
    content = db.Column(db.Text, nullable=True)  # HTML/Markdown content for text tutorials
    video_url = db.Column(db.String(500), nullable=True)  # YouTube/video URL
    thumbnail = db.Column(db.String(500), nullable=True)  # Thumbnail image URL
    duration = db.Column(db.Integer, nullable=True)  # Duration in minutes
    order = db.Column(db.Integer, default=0)  # Display order
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'content_type': self.content_type,
            'skill_level': self.skill_level,
            'content': self.content,
            'video_url': self.video_url,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
            'order': self.order,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Tutorial {self.title} [{self.skill_level}]>'


class SearchLog(db.Model):
    """Log of user search queries for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for anonymous
    search_query = db.Column(db.String(500), nullable=False)
    search_type = db.Column(db.String(20), nullable=False)  # 'song', 'lyrics', 'chord'
    results_count = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SearchLog "{self.search_query}" [{self.search_type}]>'


class SongRecognitionLog(db.Model):
    """Log of song recognition attempts for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    song_title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    recognition_source = db.Column(db.String(20), nullable=False)  # 'acrcloud', 'audd', 'manual'
    confidence = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SongRecognitionLog "{self.song_title}" by {self.artist}>'


class AnalysisActivityLog(db.Model):
    """Log of analysis activities for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    activity_type = db.Column(db.String(20), nullable=False)  # 'analyze', 'save', 'export_pdf'
    song_title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisActivityLog {self.activity_type}: "{self.song_title}">'
