"""
Quick script to help you get your Genius Access Token
"""

import webbrowser
import time

print("="*60)
print("🎵 Genius API Setup Helper")
print("="*60)
print()
print("You've already created your API client! Great! ✅")
print()
print("Now you need to generate an ACCESS TOKEN:")
print()
print("Step 1: Opening Genius API Clients page...")
print("        (If it doesn't open, go to: https://genius.com/api-clients)")
print()

# Open the Genius API clients page
webbrowser.open("https://genius.com/api-clients")

time.sleep(2)

print("Step 2: On the Genius page:")
print("        1. Click on your API client")
print("        2. Look for 'Generate Access Token' button")
print("        3. Click it and COPY the token")
print()
print("Step 3: Paste the token here:")
print()

access_token = input("Paste your Access Token: ").strip()

if access_token:
    print()
    print("✅ Token received!")
    print()
    print("Updating .env file...")
    
    # Read the .env file
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Update the GENIUS_ACCESS_TOKEN line
    with open('.env', 'w') as f:
        for line in lines:
            if line.startswith('GENIUS_ACCESS_TOKEN='):
                f.write(f'GENIUS_ACCESS_TOKEN={access_token}\n')
            else:
                f.write(line)
    
    print("✅ .env file updated!")
    print()
    print("="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Start your server: python api.py")
    print("2. You should see: '✓ Genius API initialized'")
    print("3. Enjoy perfect lyrics from Genius.com!")
    print()
    print("Your token is saved in the .env file")
    print("It will load automatically every time you start the server")
    print()
else:
    print()
    print("❌ No token provided")
    print()
    print("Please run this script again when you have the token")
    print("Or manually edit the .env file and add your token after GENIUS_ACCESS_TOKEN=")
    print()

