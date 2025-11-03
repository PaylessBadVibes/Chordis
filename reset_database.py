"""
Database Reset Script
Run this to recreate the database with new schema
"""

import os
import sys
from models import db, User, SavedAnalysis

# Check if database files exist
db_files = ['music_analyzer.db', 'instance/music_analyzer.db']
for db_file in db_files:
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"[OK] Deleted {db_file}")
        except PermissionError:
            print(f"[ERROR] Cannot delete {db_file} - file is in use")
            print("Please close all Python processes and try again")
            sys.exit(1)

# Import app and create new database
from api import app

with app.app_context():
    db.create_all()
    print("\n[OK] Database created with new schema!")
    print("New fields added:")
    print("  - User.email_verified (Boolean)")
    print("  - User.verification_token (String)")
    print("\nYou can now start the server with: python api.py")

