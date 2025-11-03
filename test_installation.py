"""
Test script to verify all dependencies are installed correctly
"""

import sys

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...\n")
    
    tests = [
        ("Flask", lambda: __import__('flask')),
        ("PyTorch", lambda: __import__('torch')),
        ("Librosa", lambda: __import__('librosa')),
        ("NumPy", lambda: __import__('numpy')),
        ("Whisper", lambda: __import__('whisper')),
        ("yt-dlp", lambda: __import__('yt_dlp')),
        ("chord_recognition", lambda: __import__('chord_recognition')),
    ]
    
    failed = []
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name} - OK")
        except ImportError as e:
            print(f"✗ {name} - FAILED")
            failed.append((name, str(e)))
    
    print("\n" + "="*50)
    
    if failed:
        print("\n❌ Some dependencies are missing:\n")
        for name, error in failed:
            print(f"  - {name}: {error}")
        print("\nTo fix, run:")
        print("  pip install openai-whisper yt-dlp flask-cors")
        return False
    else:
        print("\n✓ All dependencies installed successfully!")
        print("\nYou can now run:")
        print("  python api.py")
        return True

def test_ffmpeg():
    """Test if FFmpeg is available"""
    print("\n" + "="*50)
    print("Testing FFmpeg...\n")
    
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg installed: {version}")
            return True
        else:
            print("✗ FFmpeg found but returned error")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg not found")
        print("\nFFmpeg is required for YouTube downloads.")
        print("Install it with: choco install ffmpeg")
        return False
    except Exception as e:
        print(f"✗ Error testing FFmpeg: {e}")
        return False

def test_model_structure():
    """Test if model structure is set up correctly"""
    print("\n" + "="*50)
    print("Testing project structure...\n")
    
    import os
    
    required_dirs = [
        ('chord_recognition/', 'Chord recognition module'),
        ('models/', 'Model storage directory'),
        ('static/', 'Web interface directory'),
    ]
    
    required_files = [
        ('api.py', 'Main API file'),
        ('chord_recognition/__init__.py', 'Chord module init'),
        ('chord_recognition/model.py', 'Model definition'),
        ('chord_recognition/utils.py', 'Utility functions'),
        ('chord_recognition/constants.py', 'Constants'),
        ('static/index.html', 'Web interface'),
    ]
    
    all_good = True
    
    for path, desc in required_dirs:
        if os.path.isdir(path):
            print(f"✓ {desc}: {path}")
        else:
            print(f"✗ Missing {desc}: {path}")
            all_good = False
    
    for path, desc in required_files:
        if os.path.isfile(path):
            print(f"✓ {desc}: {path}")
        else:
            print(f"✗ Missing {desc}: {path}")
            all_good = False
    
    # Check for optional trained model
    if os.path.isfile('models/cnn_model.pth'):
        print("✓ Trained chord model found (will use CNN)")
    else:
        print("ℹ No trained model (will use rule-based detection)")
    
    return all_good

if __name__ == "__main__":
    print("="*50)
    print("Music Analysis API - Installation Test")
    print("="*50 + "\n")
    
    imports_ok = test_imports()
    structure_ok = test_model_structure()
    ffmpeg_ok = test_ffmpeg()
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50 + "\n")
    
    if imports_ok and structure_ok:
        print("✓ Core system ready!")
        if ffmpeg_ok:
            print("✓ FFmpeg ready for YouTube downloads!")
        else:
            print("⚠ FFmpeg missing - YouTube downloads won't work")
        
        print("\n🚀 Ready to start! Run: python api.py")
        sys.exit(0)
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)

