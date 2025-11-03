#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify Genius API search is working
Run this while the server is running to test the search endpoint
"""

import requests
import json
import os
import sys
from dotenv import load_dotenv

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

print("=" * 60)
print("TESTING GENIUS API SEARCH")
print("=" * 60)

# Check if token is loaded
token = os.getenv('GENIUS_ACCESS_TOKEN')
print(f"\n1. Checking .env file...")
if token:
    print(f"   ✅ GENIUS_ACCESS_TOKEN found: {token[:20]}...")
else:
    print(f"   ❌ GENIUS_ACCESS_TOKEN not found in .env file!")
    print(f"   Make sure .env file exists in project root")
    exit(1)

# Test direct Genius API
print(f"\n2. Testing direct Genius API call...")
try:
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        'https://api.genius.com/search',
        headers=headers,
        params={'q': 'Joji'},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        hits = data.get('response', {}).get('hits', [])
        print(f"   ✅ Genius API is working!")
        print(f"   Found {len(hits)} results for 'Joji'")
        if hits:
            first = hits[0]['result']
            print(f"   First result: {first['title']} by {first['primary_artist']['name']}")
    else:
        print(f"   ❌ Genius API returned status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Error calling Genius API: {e}")

# Test local API endpoint
print(f"\n3. Testing local API endpoint...")
try:
    response = requests.post(
        'http://localhost:5000/api/search-songs',
        json={'query': 'Joji'},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        print(f"   ✅ Local API endpoint is working!")
        print(f"   Found {len(results)} results")
        if results:
            print(f"   First result: {results[0]['title']} by {results[0]['artist']}")
    else:
        print(f"   ❌ Local API returned status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except requests.exceptions.ConnectionError:
    print(f"   ❌ Could not connect to local server!")
    print(f"   Make sure the server is running: python api.py")
except Exception as e:
    print(f"   ❌ Error calling local API: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\nIf all tests passed (✅), the search should work!")
print("If any test failed (❌), check the error messages above.")
print("\nTo use search:")
print("1. Make sure server is running: python api.py")
print("2. Open: http://localhost:5000")
print("3. Type 'Joji' in search box")
print("4. Check browser console (F12) for any errors")

