@echo off
echo ===============================================
echo CHORDIS - GITHUB SETUP HELPER
echo ===============================================
echo.

echo Step 1: Initializing Git repository...
git init
echo.

echo Step 2: Adding all files...
git add .
echo.

echo Step 3: Creating initial commit...
git commit -m "Initial commit - Chordis AI Music Analysis App"
echo.

echo ===============================================
echo NEXT STEPS:
echo ===============================================
echo 1. Go to https://github.com/new
echo 2. Create a new repository called "chordis"
echo 3. Copy the repository URL (e.g., https://github.com/YOUR_USERNAME/chordis.git)
echo 4. Run these commands:
echo.
echo    git remote add origin YOUR_REPO_URL_HERE
echo    git branch -M main
echo    git push -u origin main
echo.
echo ===============================================
echo Then go to Railway.app to deploy!
echo ===============================================
pause



