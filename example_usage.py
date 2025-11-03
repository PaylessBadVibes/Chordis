"""
Example usage of the Music Analysis API
"""
import requests
import json

# Base URL of the API
BASE_URL = "http://localhost:5000"

def test_health():
    """Test the health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def analyze_file(filepath):
    """Analyze a local audio file"""
    print(f"Analyzing file: {filepath}")
    
    with open(filepath, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/analyze", files=files)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"\nChords detected: {result.get('chords')}")
        print(f"\nLyrics:\n{result.get('lyrics')}\n")
    else:
        print(f"Error: {response.json()}\n")

def analyze_youtube(url):
    """Analyze a YouTube video"""
    print(f"Analyzing YouTube video: {url}")
    
    headers = {'Content-Type': 'application/json'}
    data = {'youtube_url': url}
    response = requests.post(f"{BASE_URL}/analyze", headers=headers, json=data)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"\nChords detected: {result.get('chords')}")
        print(f"\nLyrics:\n{result.get('lyrics')}\n")
    else:
        print(f"Error: {response.json()}\n")

if __name__ == "__main__":
    # Test health check
    test_health()
    
    # Example 1: Analyze a local file
    # Uncomment and replace with your file path
    # analyze_file("path/to/your/song.wav")
    
    # Example 2: Analyze a YouTube video
    # Uncomment and replace with your YouTube URL
    # analyze_youtube("https://www.youtube.com/watch?v=VIDEO_ID")
    
    print("Examples are commented out. Uncomment them to test with real files/URLs.")

