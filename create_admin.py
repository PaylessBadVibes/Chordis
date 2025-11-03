"""
Create admin user or promote existing user to admin
Run this script to make a user an administrator
"""

from api import app, db
from models import User

def create_admin():
    with app.app_context():
        print("=" * 50)
        print("CHORDIS - CREATE ADMIN USER")
        print("=" * 50)
        
        # Show existing users
        users = User.query.all()
        if users:
            print("\nExisting users:")
            for user in users:
                admin_status = "[ADMIN]" if user.is_admin else ""
                print(f"  - {user.username} {admin_status}")
        else:
            print("\nNo users found in database.")
            print("Please register a user first at http://localhost:5000/auth")
            return
        
        print("\n" + "=" * 50)
        username = input("Enter username to make admin: ").strip()
        
        if not username:
            print("No username provided. Exiting.")
            return
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            if user.is_admin:
                print(f"\n{username} is already an admin!")
            else:
                user.is_admin = True
                db.session.commit()
                print(f"\nSUCCESS - {username} is now an admin!")
                print(f"They can now access the admin dashboard at:")
                print(f"http://localhost:5000/admin")
        else:
            print(f"\nERROR - User '{username}' not found")
            print("Available users:", ", ".join([u.username for u in users]))

if __name__ == "__main__":
    create_admin()

