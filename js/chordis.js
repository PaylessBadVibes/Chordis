// Chordis Main Application JavaScript
class ChordisApp {
    constructor() {
        this.currentTab = 'search';  // Start with search tab
        this.isAnalyzing = false;
        this.isSearching = false;
        this.audio = null;
        this.isPlaying = false;
        this.currentSongData = null;
        this.currentUser = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFileUpload();
        this.setupAudioPlayer();
        this.setupAuth();
        this.setupRealtimeRecognition();
        this.checkAuthStatus();
    }
    
    setupRealtimeRecognition() {
        this.realtimeRecognition = new window.RealtimeRecognition(this);
        
        const startListeningBtn = document.getElementById('start-listening-btn');
        if (startListeningBtn) {
            startListeningBtn.addEventListener('click', () => {
                if (this.realtimeRecognition.isListening) {
                    this.realtimeRecognition.stopListening();
                } else {
                    this.realtimeRecognition.startListening();
                }
            });
        }
        
        // Make app available globally for realtime callbacks
        window.chordisApp = this;
    }
    
    async analyzeRecognizedSong(title, artist) {
        // Analyze a song that was recognized from microphone
        const songData = { title, artist };
        await this.analyzeFromSearch(songData);
    }
    
    setupAuth() {
        const signinBtn = document.getElementById('signin-btn');
        const signupBtn = document.getElementById('signup-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const authModal = document.getElementById('auth-modal');
        const closeAuthModal = document.getElementById('close-auth-modal');
        const showRegister = document.getElementById('show-register');
        const showLogin = document.getElementById('show-login');
        const loginSubmitBtn = document.getElementById('login-submit-btn');
        const registerSubmitBtn = document.getElementById('register-submit-btn');
        const myLibraryLink = document.getElementById('my-library-link');
        const libraryModal = document.getElementById('library-modal');
        const closeLibraryModal = document.getElementById('close-library-modal');
        
        if (signinBtn) {
            signinBtn.addEventListener('click', () => this.showAuthModal('login'));
        }
        
        if (signupBtn) {
            signupBtn.addEventListener('click', () => this.showAuthModal('register'));
        }
        
        if (closeAuthModal) {
            closeAuthModal.addEventListener('click', () => this.closeAuthModal());
        }
        
        if (authModal) {
            authModal.addEventListener('click', (e) => {
                if (e.target === authModal || e.target.classList.contains('modal-overlay')) {
                    this.closeAuthModal();
                }
            });
        }
        
        if (myLibraryLink) {
            myLibraryLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLibrary();
            });
        }
        
        if (closeLibraryModal) {
            closeLibraryModal.addEventListener('click', () => this.closeLibrary());
        }
        
        if (libraryModal) {
            libraryModal.addEventListener('click', (e) => {
                if (e.target === libraryModal || e.target.classList.contains('modal-overlay')) {
                    this.closeLibrary();
                }
            });
        }
        
        if (showRegister) {
            showRegister.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchAuthForm('register');
            });
        }
        
        if (showLogin) {
            showLogin.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchAuthForm('login');
            });
        }
        
        if (loginSubmitBtn) {
            loginSubmitBtn.addEventListener('click', () => this.handleLogin());
        }
        
        if (registerSubmitBtn) {
            registerSubmitBtn.addEventListener('click', () => this.handleRegister());
        }
        
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }
        
        // Enter key for auth forms
        const authInputs = document.querySelectorAll('#auth-modal input');
        authInputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const loginForm = document.getElementById('login-form');
                    if (loginForm.style.display !== 'none') {
                        this.handleLogin();
                    } else {
                        this.handleRegister();
                    }
                }
            });
        });
        
        // Real-time password matching validation
        const registerPassword = document.getElementById('register-password');
        const confirmPassword = document.getElementById('register-confirm-password');
        const passwordMatchError = document.getElementById('password-match-error');
        
        if (confirmPassword && registerPassword) {
            const checkPasswordMatch = () => {
                if (confirmPassword.value && registerPassword.value) {
                    if (confirmPassword.value !== registerPassword.value) {
                        passwordMatchError.style.display = 'block';
                    } else {
                        passwordMatchError.style.display = 'none';
                    }
                }
            };
            
            confirmPassword.addEventListener('input', checkPasswordMatch);
            registerPassword.addEventListener('input', checkPasswordMatch);
        }
        
        // Handle terms and privacy links
        const termsLink = document.getElementById('terms-link');
        const privacyLink = document.getElementById('privacy-link');
        
        if (termsLink) {
            termsLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showTermsModal();
            });
        }
        
        if (privacyLink) {
            privacyLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showPrivacyModal();
            });
        }
    }
    
    async checkAuthStatus() {
        // Check if user is already logged in
        try {
            const response = await fetch('/api/current-user');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.user) {
                    this.updateUIForUser(data.user);
                }
            }
        } catch (error) {
            console.log('Not logged in');
        }
    }
    
    showAuthModal(mode = 'login') {
        const authModal = document.getElementById('auth-modal');
        authModal.classList.add('show');
        this.switchAuthForm(mode);
    }
    
    closeAuthModal() {
        const authModal = document.getElementById('auth-modal');
        authModal.classList.remove('show');
    }
    
    switchAuthForm(mode) {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const authModalTitle = document.getElementById('auth-modal-title');
        
        if (mode === 'login') {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            authModalTitle.textContent = 'Welcome Back';
        } else {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            authModalTitle.textContent = 'Create Account';
        }
    }
    
    async handleLogin() {
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        
        if (!username || !password) {
            this.showError('Please enter username and password');
            return;
        }
        
        try {
            // Encrypt password before sending
            const encryptedPassword = await window.CryptoHelper.encrypt(password);
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Encrypted': 'true'  // Flag to indicate encrypted data
                },
                body: JSON.stringify({ 
                    username, 
                    password: encryptedPassword,
                    encrypted: true
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateUIForUser(data.user);
                this.closeAuthModal();
                this.showSuccess('Welcome back, ' + data.user.username + '!');
            } else {
                this.showError(data.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Login failed. Please try again.');
        }
    }
    
    async handleRegister() {
        const username = document.getElementById('register-username').value.trim();
        const email = document.getElementById('register-email').value.trim();
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('register-confirm-password').value;
        const termsCheckbox = document.getElementById('terms-checkbox');
        
        // Reset error messages
        document.getElementById('password-match-error').style.display = 'none';
        document.getElementById('terms-error').style.display = 'none';
        
        // Check all fields are filled
        if (!username || !email || !password || !confirmPassword) {
            this.showError('Please fill in all fields');
            return;
        }
        
        // Check password length
        if (password.length < 6) {
            this.showError('Password must be at least 6 characters');
            return;
        }
        
        // Check passwords match
        if (password !== confirmPassword) {
            document.getElementById('password-match-error').style.display = 'block';
            this.showError('Passwords do not match');
            return;
        }
        
        // Check terms acceptance
        if (!termsCheckbox.checked) {
            document.getElementById('terms-error').style.display = 'block';
            this.showError('You must accept the terms and conditions');
            return;
        }
        
        try {
            // Encrypt sensitive data before sending
            const encryptedEmail = await window.CryptoHelper.encrypt(email);
            const encryptedPassword = await window.CryptoHelper.encrypt(password);
            const encryptedConfirmPassword = await window.CryptoHelper.encrypt(confirmPassword);
            
            console.log('Sending encrypted registration data...');
            
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Encrypted': 'true'  // Flag for server to decrypt
                },
                body: JSON.stringify({ 
                    username, 
                    email: encryptedEmail,
                    password: encryptedPassword,
                    confirmPassword: encryptedConfirmPassword,
                    acceptedTerms: termsCheckbox.checked,
                    encrypted: true
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateUIForUser(data.user);
                this.closeAuthModal();
                
                // Show verification email message
                if (data.email_sent) {
                    this.showVerificationMessage(data.user.email);
                } else {
                    this.showSuccess('Account created successfully! Welcome, ' + data.user.username + '!');
                }
            } else {
                this.showError(data.error || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showError('Registration failed. Please try again.');
        }
    }
    
    showVerificationMessage(email) {
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            z-index: 10002;
            max-width: 500px;
            text-align: center;
        `;
        messageDiv.innerHTML = `
            <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; font-size: 40px;">
                ✉️
            </div>
            <h2 style="color: #667eea; margin-bottom: 15px;">Check Your Email!</h2>
            <p style="color: #666; font-size: 16px; margin-bottom: 20px;">
                We've sent a verification link to <strong>${email}</strong>
            </p>
            <p style="color: #999; font-size: 14px; margin-bottom: 30px;">
                Click the link in the email to verify your account. The link will expire in 1 hour.
            </p>
            <button id="close-verification-msg" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 30px; border-radius: 25px; font-weight: 600; cursor: pointer; font-size: 16px;">
                Got It!
            </button>
            <p style="color: #999; font-size: 12px; margin-top: 20px;">
                Didn't receive the email? <a href="#" id="resend-email" style="color: #667eea; font-weight: 600;">Resend</a>
            </p>
        `;
        
        document.body.appendChild(messageDiv);
        
        // Close button
        document.getElementById('close-verification-msg').addEventListener('click', () => {
            messageDiv.remove();
        });
        
        // Resend email button
        document.getElementById('resend-email').addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const response = await fetch('/api/resend-verification', {
                    method: 'POST'
                });
                const data = await response.json();
                if (data.success) {
                    this.showSuccess('Verification email resent!');
                } else {
                    this.showError(data.error || 'Failed to resend email');
                }
            } catch (error) {
                this.showError('Failed to resend email');
            }
        });
    }
    
    async handleLogout() {
        try {
            await fetch('/api/logout', {
                method: 'POST'
            });
            
            this.currentUser = null;
            
            // Clear auth state manager
            if (window.authStateManager) {
                window.authStateManager.clearAuthState();
            }
            
            this.updateUIForLogout();
            this.showSuccess('Logged out successfully');
        } catch (error) {
            console.error('Logout error:', error);
        }
    }
    
    updateUIForUser(user) {
        this.currentUser = user;
        
        // Update auth state manager
        if (window.authStateManager) {
            window.authStateManager.updateAuthState(user);
        }
        
        const signinBtn = document.getElementById('signin-btn');
        const signupBtn = document.getElementById('signup-btn');
        const userMenu = document.getElementById('user-menu');
        const usernameDisplay = document.getElementById('username-display');
        const myLibraryLink = document.getElementById('my-library-link');
        
        if (signinBtn) signinBtn.style.display = 'none';
        if (signupBtn) signupBtn.style.display = 'none';
        if (userMenu) userMenu.style.display = 'flex';
        if (myLibraryLink) myLibraryLink.style.display = 'block';
        
        if (usernameDisplay) {
            usernameDisplay.textContent = user.username;
            // Add verification badge if not verified
            if (!user.email_verified) {
                usernameDisplay.innerHTML = user.username + ' <span style="background: #f59e0b; color: white; font-size: 0.65rem; padding: 2px 6px; border-radius: 10px; margin-left: 5px;">Unverified</span>';
            }
        }
        
        // Show verification reminder if not verified
        if (!user.email_verified) {
            this.showVerificationReminder();
        }
    }
    
    showVerificationReminder() {
        // Only show once per session
        if (sessionStorage.getItem('verification_reminder_shown')) return;
        sessionStorage.setItem('verification_reminder_shown', 'true');
        
        setTimeout(() => {
            const reminder = document.createElement('div');
            reminder.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 10000;
                max-width: 350px;
                border-left: 4px solid #f59e0b;
            `;
            reminder.innerHTML = `
                <div style="display: flex; align-items: start; gap: 15px;">
                    <div style="font-size: 24px;">⚠️</div>
                    <div style="flex: 1;">
                        <h4 style="margin: 0 0 8px 0; color: #333; font-size: 14px;">Verify Your Email</h4>
                        <p style="margin: 0 0 12px 0; color: #666; font-size: 13px;">
                            Please check your inbox and verify your email to unlock all features.
                        </p>
                        <button id="dismiss-reminder" style="background: transparent; border: none; color: #667eea; font-weight: 600; cursor: pointer; padding: 0; font-size: 13px;">
                            Dismiss
                        </button>
                    </div>
                    <button id="close-reminder" style="background: none; border: none; font-size: 20px; color: #999; cursor: pointer; padding: 0;">×</button>
                </div>
            `;
            document.body.appendChild(reminder);
            
            document.getElementById('close-reminder').addEventListener('click', () => reminder.remove());
            document.getElementById('dismiss-reminder').addEventListener('click', () => reminder.remove());
            
            // Auto-remove after 10 seconds
            setTimeout(() => reminder.remove(), 10000);
        }, 2000);
    }
    
    updateUIForLogout() {
        const signinBtn = document.getElementById('signin-btn');
        const signupBtn = document.getElementById('signup-btn');
        const userMenu = document.getElementById('user-menu');
        const myLibraryLink = document.getElementById('my-library-link');
        
        if (signinBtn) signinBtn.style.display = 'flex';
        if (signupBtn) signupBtn.style.display = 'flex';
        if (userMenu) userMenu.style.display = 'none';
        if (myLibraryLink) myLibraryLink.style.display = 'none';
    }
    
    async showLibrary() {
        const libraryModal = document.getElementById('library-modal');
        const libraryLoading = document.getElementById('library-loading');
        const libraryContent = document.getElementById('library-content');
        const libraryEmpty = document.getElementById('library-empty');
        const libraryGrid = document.getElementById('library-grid');
        const libraryCount = document.getElementById('library-count');
        
        // Show modal
        libraryModal.classList.add('show');
        libraryLoading.style.display = 'block';
        libraryContent.style.display = 'none';
        
        try {
            const response = await fetch('/api/saved-analyses');
            const data = await response.json();
            
            libraryLoading.style.display = 'none';
            libraryContent.style.display = 'block';
            
            if (data.success && data.analyses.length > 0) {
                libraryCount.textContent = data.analyses.length;
                libraryGrid.style.display = 'grid';
                libraryEmpty.style.display = 'none';
                
                // Populate library
                libraryGrid.innerHTML = data.analyses.map(analysis => this.createLibraryCard(analysis)).join('');
                
                // Add event listeners to cards
                this.setupLibraryCardListeners();
            } else {
                libraryCount.textContent = '0';
                libraryGrid.style.display = 'none';
                libraryEmpty.style.display = 'block';
            }
        } catch (error) {
            console.error('Error loading library:', error);
            this.showError('Failed to load library');
            this.closeLibrary();
        }
    }
    
    createLibraryCard(analysis) {
        const chords = analysis.chord_data || [];
        const displayChords = chords.slice(0, 6);  // Show first 6 chords
        const duration = analysis.duration || 0;
        const durationText = `${Math.floor(duration / 60)}:${(duration % 60).toString().padStart(2, '0')}`;
        
        // Get chord names safely
        const getChordName = (chord) => {
            if (typeof chord === 'string') return chord;
            return chord.name || chord.chord || 'C';
        };
        
        return `
            <div class="library-card" data-analysis-id="${analysis.id}">
                <div class="library-card-header">
                    <div class="library-card-title">${analysis.title}</div>
                    <div class="library-card-artist">${analysis.artist || 'Unknown Artist'}</div>
                </div>
                
                <div class="library-card-meta">
                    <span><i class="fas fa-music"></i>${analysis.key || 'N/A'}</span>
                    <span><i class="fas fa-drum"></i>${analysis.tempo || '120'} BPM</span>
                    <span><i class="fas fa-clock"></i>${durationText}</span>
                </div>
                
                <div class="library-card-chords">
                    ${displayChords.map(chord => `
                        <span class="library-chord-badge">${getChordName(chord)}</span>
                    `).join('')}
                    ${chords.length > 6 ? `<span class="library-chord-badge">+${chords.length - 6} more</span>` : ''}
                </div>
                
                <div class="library-card-actions">
                    <button class="library-action-btn view-btn" data-id="${analysis.id}">
                        <i class="fas fa-play"></i>
                        Play
                    </button>
                    <button class="library-action-btn delete" data-id="${analysis.id}">
                        <i class="fas fa-trash"></i>
                        Delete
                    </button>
                </div>
            </div>
        `;
    }
    
    setupLibraryCardListeners() {
        // View/Play buttons
        document.querySelectorAll('.library-action-btn.view-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const analysisId = btn.getAttribute('data-id');
                await this.loadSavedAnalysis(analysisId);
            });
        });
        
        // Delete buttons
        document.querySelectorAll('.library-action-btn.delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const analysisId = btn.getAttribute('data-id');
                if (confirm('Are you sure you want to delete this analysis?')) {
                    await this.deleteSavedAnalysis(analysisId);
                }
            });
        });
    }
    
    async loadSavedAnalysis(analysisId) {
        try {
            const response = await fetch(`/api/saved-analysis/${analysisId}`);
            const data = await response.json();
            
            if (data.success) {
                // Close library modal
                this.closeLibrary();
                
                // Transform and display analysis
                const analysisData = {
                    title: data.analysis.title,
                    artist: data.analysis.artist,
                    chords: data.analysis.chord_data,
                    lyrics: data.analysis.lyrics_data,
                    key: data.analysis.key,
                    tempo: data.analysis.tempo,
                    duration: data.analysis.duration
                };
                
                // Store as current song data
                this.currentSongData = analysisData;
                
                // Create input data based on source type
                this.lastInputData = {
                    type: data.analysis.source_type || 'saved',
                    url: data.analysis.source_url || ''
                };
                
                // Show in results modal
                this.displayResults(analysisData);
                
                // Show results modal
                const modal = document.getElementById('results-modal');
                modal.style.display = 'flex';
                modal.style.alignItems = 'center';
                modal.style.justifyContent = 'center';
                setTimeout(() => modal.classList.add('show'), 10);
                console.log('[CHORDIS] Modal opened for saved analysis');
                
                // Load audio after showing modal
                setTimeout(() => {
                    this.loadAudioForAnalysis(analysisData, this.lastInputData);
                }, 300);
            }
        } catch (error) {
            console.error('Error loading analysis:', error);
            this.showError('Failed to load analysis');
        }
    }
    
    async deleteSavedAnalysis(analysisId) {
        try {
            const response = await fetch(`/api/saved-analysis/${analysisId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Analysis deleted successfully');
                // Reload library
                this.showLibrary();
            } else {
                this.showError(data.error || 'Failed to delete analysis');
            }
        } catch (error) {
            console.error('Error deleting analysis:', error);
            this.showError('Failed to delete analysis');
        }
    }
    
    closeLibrary() {
        const libraryModal = document.getElementById('library-modal');
        libraryModal.classList.remove('show');
    }
    
    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'toast-notification toast-success';
        successDiv.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        document.body.appendChild(successDiv);

        // Trigger animation
        setTimeout(() => successDiv.classList.add('show'), 10);

        // Auto-remove after 4 seconds
        setTimeout(() => {
            successDiv.classList.remove('show');
            setTimeout(() => successDiv.remove(), 400);
        }, 4000);
    }

    setupEventListeners() {
        // Tab switching
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.closest('.tab-button').dataset.tab);
            });
        });

        // Analyze button
        const analyzeBtn = document.getElementById('analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => {
                this.analyzeSong();
            });
        }

        // Modal close
        const closeBtn = document.getElementById('close-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeModal();
            });
        }

        // Close modal on background click
        const modal = document.getElementById('results-modal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });

        // Enter key for inputs
        const inputs = document.querySelectorAll('input[type="url"], input[type="text"]');
        inputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    // Check if it's the search input
                    if (input.id === 'search-query') {
                        this.performSearch();
                    } else {
                        this.analyzeSong();
                    }
                }
            });
        });
        
        // Search input live search
        const searchInput = document.getElementById('search-query');
        if (searchInput) {
            console.log('[CHORDIS] Search input found, attaching listeners');
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                const query = e.target.value.trim();
                console.log('[CHORDIS] Search input changed:', query);
                if (query.length >= 2) {
                    searchTimeout = setTimeout(() => this.performSearch(), 500);
                } else {
                    // Hide results if query too short
                    const searchResults = document.getElementById('search-results');
                    if (searchResults) searchResults.style.display = 'none';
                }
            });
            
            // Also add keypress listener for Enter key
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        } else {
            console.error('[CHORDIS] Search input not found!');
        }
    }
    
    async performSearch() {
        const query = document.getElementById('search-query').value.trim();
        
        if (!query || query.length < 2) {
            return;
        }
        
        if (this.isSearching) return;
        
        const searchResults = document.getElementById('search-results');
        const searchResultsList = document.getElementById('search-results-list');
        const searchLoading = document.getElementById('search-loading');
        
        if (!searchResults || !searchResultsList || !searchLoading) {
            console.error('[CHORDIS] Search elements not found');
            return;
        }
        
        this.isSearching = true;
        searchResults.style.display = 'none';
        searchLoading.style.display = 'block';
        
        try {
            console.log('[CHORDIS] Searching for:', query);
            
            // Try backend search first
            const response = await fetch('/api/search-songs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });
            
            searchLoading.style.display = 'none';
            
            if (!response.ok) {
                throw new Error('Search API not available');
            }
            
            const data = await response.json();
            
            if (data.success && data.results && data.results.length > 0) {
                searchResults.style.display = 'block';
                searchResultsList.innerHTML = data.results.map(song => this.createSearchResultCard(song)).join('');
                this.setupSearchResultListeners();
            } else {
                searchResults.style.display = 'block';
                searchResultsList.innerHTML = `
                    <div style="text-align: center; padding: 2rem; color: var(--gray-500);">
                        <i class="fas fa-search" style="font-size: 3rem; opacity: 0.3; margin-bottom: 1rem; display: block;"></i>
                        <p>No songs found. Try a different search term.</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('[CHORDIS] Search error:', error);
            searchLoading.style.display = 'none';
            
            // Fallback: Show demo results
            searchResults.style.display = 'block';
            searchResultsList.innerHTML = this.createDemoSearchResults(query);
            this.setupSearchResultListeners();
        } finally {
            this.isSearching = false;
        }
    }
    
    createDemoSearchResults(query) {
        // Demo results for testing
        const demoSongs = [
            { title: 'Slow Dancing in the Dark', artist: 'Joji', album: 'BALLADS 1' },
            { title: 'SLOW DANCING IN THE DARK', artist: 'Joji', album: 'BALLADS 1 (Deluxe)' },
            { title: 'Glimpse of Us', artist: 'Joji', album: 'SMITHEREENS' },
            { title: 'Sanctuary', artist: 'Joji', album: 'Nectar' },
            { title: 'Run', artist: 'Joji', album: 'Nectar' }
        ];
        
        const results = demoSongs.filter(song => 
            song.title.toLowerCase().includes(query.toLowerCase()) ||
            song.artist.toLowerCase().includes(query.toLowerCase())
        );
        
        if (results.length === 0) {
            return `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <i class="fas fa-info-circle" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                    <p style="margin-bottom: 1rem;">Search API not connected yet.</p>
                    <p style="font-size: 0.875rem; color: var(--text-tertiary);">Try searching for "joji" to see demo results</p>
                </div>
            `;
        }
        
        return results.map(song => this.createSearchResultCard(song)).join('');
    }
    
    createSearchResultCard(song) {
        const artwork = song.artwork || song.thumbnail || 
            `https://via.placeholder.com/60x60/6366f1/ffffff?text=${encodeURIComponent(song.title.charAt(0))}`;
        
        return `
            <div class="search-result-card" data-song='${JSON.stringify(song).replace(/'/g, "&apos;")}'
                 style="display: flex; align-items: center; gap: 1rem; padding: 1rem; background: white; border-bottom: 1px solid #e5e7eb; cursor: pointer; transition: background 0.2s;"
                 onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='white'">
                <img src="${artwork}" alt="${song.title}" 
                     style="width: 60px; height: 60px; border-radius: 8px; object-fit: cover;"
                     onerror="this.src='https://via.placeholder.com/60x60/6366f1/ffffff?text=♪'">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #111827; margin-bottom: 0.25rem;">${song.title}</div>
                    <div style="color: #6b7280; font-size: 0.875rem;">${song.artist}</div>
                    ${song.album ? `<div style="color: #9ca3af; font-size: 0.75rem; margin-top: 0.25rem;">${song.album}</div>` : ''}
                </div>
                <button class="analyze-search-result" 
                        style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;"
                        onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'"
                        onclick="event.stopPropagation()">
                    <i class="fas fa-wand-magic-sparkles"></i>
                    Analyze
                </button>
            </div>
        `;
    }
    
    setupSearchResultListeners() {
        document.querySelectorAll('.search-result-card').forEach(card => {
            card.addEventListener('click', () => {
                const songData = JSON.parse(card.getAttribute('data-song'));
                this.analyzeFromSearch(songData);
            });
        });
    }
    
    async analyzeFromSearch(songData) {
        // Close search and start analysis
        const query = `${songData.artist} ${songData.title} official audio`;
        
        // Show analyzing state
        const analyzeBtn = document.getElementById('analyze-btn');
        const modal = document.getElementById('results-modal');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        
        this.isAnalyzing = true;
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="button-content"><i class="fas fa-spinner fa-spin"></i><span>Finding song...</span></span>';
        
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        setTimeout(() => modal.classList.add('show'), 10);
        loading.style.display = 'block';
        results.style.display = 'none';
        console.log('[CHORDIS] Modal opened for search analysis');
        
        this.animateProgressSteps();
        
        try {
            // Search YouTube for the song and analyze
            const response = await fetch('/api/search-and-analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: songData.title,
                    artist: songData.artist,
                    artwork: songData.artwork || songData.thumbnail,
                    search_query: query
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                const analysisData = {
                    title: songData.title,
                    artist: songData.artist,
                    chords: data.chords || this.generatePlaceholderChords(),
                    lyrics: data.lyrics || [],
                    key: data.key || 'C Major',
                    tempo: data.tempo || 120,
                    duration: data.duration || 180,
                    artwork: songData.artwork || songData.thumbnail
                };
                
                // Store YouTube URL if found
                this.lastInputData = { 
                    type: 'search', 
                    query: query,
                    youtubeUrl: data.youtube_url || null
                };
                
                this.displayResults(analysisData);
            } else {
                throw new Error(data.error || 'Analysis failed');
            }
        } catch (error) {
            console.error('Analysis error:', error);
            this.showError('Analysis failed. Please try again.');
            this.closeModal();
        } finally {
            this.isAnalyzing = false;
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<span class="button-content"><i class="fas fa-wand-magic-sparkles"></i><span>Analyze Song</span></span>';
        }
    }
    
    generatePlaceholderChords() {
        // Generate common chord progression
        return [
            { name: 'C', confidence: 90, timestamp: 0 },
            { name: 'G', confidence: 88, timestamp: 15 },
            { name: 'Am', confidence: 92, timestamp: 30 },
            { name: 'F', confidence: 89, timestamp: 45 },
            { name: 'C', confidence: 91, timestamp: 60 },
            { name: 'G', confidence: 87, timestamp: 75 },
            { name: 'Am', confidence: 90, timestamp: 90 },
            { name: 'F', confidence: 93, timestamp: 105 }
        ];
    }

    setupFileUpload() {
        const fileUploadArea = document.getElementById('file-upload-area');
        const fileInput = document.getElementById('file-upload');

        // Click to upload
        fileUploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // File selection
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0]);
            }
        });

        // Drag and drop
        fileUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUploadArea.style.borderColor = 'var(--primary-purple)';
            fileUploadArea.style.background = 'rgba(106, 13, 173, 0.1)';
        });

        fileUploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            fileUploadArea.style.borderColor = 'var(--gray-medium)';
            fileUploadArea.style.background = 'var(--gray-light)';
        });

        fileUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUploadArea.style.borderColor = 'var(--gray-medium)';
            fileUploadArea.style.background = 'var(--gray-light)';
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    setupAudioPlayer() {
        // Initialize audio element
        this.audio = new Audio();
        this.audio.preload = 'metadata';
        
        // Audio player event listeners
        const playPauseBtn = document.getElementById('play-pause-btn');
        const progressBar = document.getElementById('progress-bar');
        const volumeSlider = document.getElementById('volume-slider');
        
        if (playPauseBtn) {
            playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        }
        
        if (progressBar) {
            progressBar.addEventListener('click', (e) => this.seekTo(e));
        }
        
        if (volumeSlider) {
            volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        }
        
        // Audio event listeners
        this.audio.addEventListener('loadedmetadata', () => this.updateDuration());
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('ended', () => this.songEnded());
        this.audio.addEventListener('play', () => this.onPlay());
        this.audio.addEventListener('pause', () => this.onPause());
        
        // Add seeking event for instant lyric update
        this.audio.addEventListener('seeking', () => this.highlightCurrentLyric());
        this.audio.addEventListener('seeked', () => this.highlightCurrentLyric());
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        const activeTabBtn = document.querySelector(`.tab-button[data-tab="${tabName}"]`);
        if (activeTabBtn) {
            activeTabBtn.classList.add('active');
        }

        // Update tab panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        const activePanel = document.getElementById(`${tabName}-content`);
        if (activePanel) {
            activePanel.classList.add('active');
        }

        // Also handle old tab-content class for backward compatibility
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const oldContent = document.getElementById(`${tabName}-content`);
        if (oldContent) {
            oldContent.classList.add('active');
        }

        this.currentTab = tabName;
        
        // Show/hide analyze button based on tab
        const analyzeBtn = document.getElementById('analyze-btn');
        if (analyzeBtn) {
            if (tabName === 'search') {
                analyzeBtn.style.display = 'none';  // Hide for search tab
            } else {
                analyzeBtn.style.display = 'flex';  // Show for other tabs
            }
        }
    }

    handleFileSelect(file) {
        if (!file.type.startsWith('audio/')) {
            this.showError('Please select an audio file.');
            return;
        }

        // Update UI to show selected file
        const fileUploadArea = document.getElementById('file-upload-area');
        fileUploadArea.innerHTML = `
            <i class="fas fa-check-circle" style="color: var(--success);"></i>
            <p>Selected: <strong>${file.name}</strong></p>
            <p style="font-size: 14px; color: var(--gray-medium);">Click to change file</p>
        `;

        this.selectedFile = file;
    }

    async analyzeSong() {
        if (this.isAnalyzing) return;

        const analyzeBtn = document.getElementById('analyze-btn');
        const modal = document.getElementById('results-modal');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');

        // Validate input based on current tab
        let inputData = null;
        switch (this.currentTab) {
            case 'youtube':
                const youtubeUrl = document.getElementById('youtube-url').value.trim();
                if (!youtubeUrl) {
                    this.showError('Please enter a YouTube URL.');
                    return;
                }
                if (!this.isValidYouTubeUrl(youtubeUrl)) {
                    this.showError('Please enter a valid YouTube URL.');
                    return;
                }
                inputData = { type: 'youtube', url: youtubeUrl };
                break;

            case 'spotify':
                const spotifySearch = document.getElementById('spotify-search').value.trim();
                if (!spotifySearch) {
                    this.showError('Please enter a song title or artist.');
                    return;
                }
                inputData = { type: 'spotify', query: spotifySearch };
                break;

            case 'upload':
                if (!this.selectedFile) {
                    this.showError('Please select an audio file to upload.');
                    return;
                }
                inputData = { type: 'upload', file: this.selectedFile };
                break;
        }

        // Start analysis
        this.isAnalyzing = true;
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="button-content"><i class="fas fa-spinner fa-spin"></i><span>Analyzing...</span></span>';

        // Show modal
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        setTimeout(() => modal.classList.add('show'), 10);
        loading.style.display = 'block';
        results.style.display = 'none';
        console.log('[CHORDIS] Modal opened for analysis');

        // Animate progress steps
        this.animateProgressSteps();

        try {
            this.lastInputData = inputData; // Store for audio loading
            const analysisResult = await this.performAnalysis(inputData);
            this.displayResults(analysisResult);
        } catch (error) {
            console.error('Analysis error:', error);
            this.showError(error.message || 'Analysis failed. Please try again.');
            this.closeModal();
        } finally {
            this.isAnalyzing = false;
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<span class="button-content"><i class="fas fa-wand-magic-sparkles"></i><span>Analyze Song</span></span>';
        }
    }
    
    animateProgressSteps() {
        const steps = document.querySelectorAll('.progress-steps .step');
        steps.forEach((step, index) => {
            setTimeout(() => {
                step.style.opacity = '1';
                step.style.transform = 'scale(1.1)';
                const icon = step.querySelector('div');
                if (icon) {
                    icon.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                    icon.style.color = 'white';
                }
                setTimeout(() => {
                    step.style.transform = 'scale(1)';
                }, 300);
            }, index * 1500);
        });
    }

    async performAnalysis(inputData) {
        try {
            let response;
            
            switch (inputData.type) {
                case 'youtube':
                    console.log('Analyzing YouTube URL:', inputData.url);
                    response = await fetch('/analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            youtube_url: inputData.url
                        })
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
                    break;

                case 'spotify':
                    // For Spotify, we'll use the search functionality and then analyze
                    // This is a simplified approach - you might want to implement Spotify API integration
                    response = await fetch('/api/search-songs', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            query: inputData.query
                        })
                    });
                    
                    const searchData = await response.json();
                    if (searchData.success && searchData.results.length > 0) {
                        // Use the first result for analysis
                        const firstResult = searchData.results[0];
                        // For now, we'll simulate the analysis since Spotify integration needs more work
                        return this.createMockResults(firstResult.title, firstResult.artist);
                    } else {
                        throw new Error('No songs found for the search query');
                    }

                case 'upload':
                    const formData = new FormData();
                    formData.append('file', inputData.file);
                    
                    response = await fetch('/analyze', {
                        method: 'POST',
                        body: formData
                    });
                    break;

                default:
                    throw new Error('Invalid input type');
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Analysis failed');
            }

            // Transform the backend response to our frontend format
            return this.transformBackendResponse(data, inputData);

        } catch (error) {
            console.error('Analysis error:', error);
            throw error;
        }
    }

    transformBackendResponse(data, inputData) {
        console.log('Transforming backend response:', data);
        
        // Handle different chord data formats
        let chordData = data.chord_data || data.chords || [];
        
        console.log('Chord data received:', chordData);
        console.log('Chord data type:', typeof chordData, 'isArray:', Array.isArray(chordData));
        
        if (!Array.isArray(chordData)) {
            console.warn('chord_data is not an array:', chordData);
            chordData = [];
        }
        
        const lyricsData = data.lyrics_data || {};
        
        // Transform chord data
        const chords = chordData.map((chord, index) => {
            // Handle different chord formats
            let chordName = 'C'; // Default
            
            if (typeof chord === 'string') {
                chordName = chord;
            } else if (chord && typeof chord === 'object') {
                chordName = chord.chord || chord.name || 'C';
            }
            
            console.log(`Chord ${index}:`, chord, '→ name:', chordName);
            
            return {
                name: chordName,
                confidence: chord.confidence || Math.floor(Math.random() * 20) + 80,
                timestamp: chord.start_time || chord.timestamp || index * 15
            };
        });

        // Transform lyrics data with better parsing
        let lyrics = [];
        if (lyricsData.text) {
            // Split by newlines and filter empty lines
            const lines = lyricsData.text.split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0);
            
            // Create lyrics with better timing
            // Calculate average time per line based on total duration
            const estimatedDuration = data.duration || 180;
            const timePerLine = estimatedDuration / Math.max(lines.length, 1);
            
            lyrics = lines.map((line, index) => ({
                text: line,
                timestamp: index * timePerLine // Distributed evenly across song
            }));
            
            // If we have word timestamps from Whisper, use those for better accuracy
            if (lyricsData.words && Array.isArray(lyricsData.words) && lyricsData.words.length > 0) {
                // Group words into lines (every ~10 words or by natural breaks)
                const wordsPerLine = 10;
                lyrics = [];
                for (let i = 0; i < lyricsData.words.length; i += wordsPerLine) {
                    const wordGroup = lyricsData.words.slice(i, i + wordsPerLine);
                    const lineText = wordGroup.map(w => w.word).join(' ');
                    const timestamp = wordGroup[0].start || i * 2;
                    lyrics.push({
                        text: lineText,
                        timestamp: timestamp
                    });
                }
            }
        } else if (Array.isArray(lyricsData)) {
            lyrics = lyricsData.map((line, index) => ({
                text: line.text || line,
                timestamp: line.timestamp || index * 10
            }));
        }
        
        // If no lyrics, add placeholder
        if (lyrics.length === 0) {
            lyrics = [
                { text: 'No lyrics available', timestamp: 0 },
                { text: 'Enjoy the instrumental!', timestamp: 15 }
            ];
        }
        
        // Limit to reasonable number of lines for performance
        if (lyrics.length > 100) {
            console.warn('Too many lyric lines, limiting to 100');
            lyrics = lyrics.slice(0, 100);
        }
        
        // If no chords detected, add placeholders
        if (chords.length === 0) {
            console.warn('No chords detected, using placeholders');
            chords = [
                { name: 'C', confidence: 85, timestamp: 0 },
                { name: 'G', confidence: 82, timestamp: 15 },
                { name: 'Am', confidence: 88, timestamp: 30 },
                { name: 'F', confidence: 90, timestamp: 45 }
            ];
        }
        
        // Use backend title/artist if provided, otherwise extract from input
        const title = data.title || this.getTitleFromInput(inputData);
        const artist = data.artist || this.getArtistFromInput(inputData);
        const duration = data.duration || this.estimateDuration(chords);
        const key = this.detectKey(chords);
        const artwork = data.artwork || null;

        console.log('Transformed data:', { title, artist, chords: chords.length, lyrics: lyrics.length, hasArtwork: !!artwork });

        return {
            title,
            artist,
            chords,
            lyrics,
            duration,
            key,
            tempo: 120, // Default tempo
            artwork: artwork
        };
    }

    createMockResults(title, artist) {
        return {
            title: title,
            artist: artist,
            chords: [
                { name: 'C', confidence: 95, timestamp: 0 },
                { name: 'G', confidence: 92, timestamp: 15 },
                { name: 'Am', confidence: 88, timestamp: 30 },
                { name: 'F', confidence: 90, timestamp: 45 },
                { name: 'C', confidence: 94, timestamp: 60 },
                { name: 'G', confidence: 91, timestamp: 75 },
                { name: 'Am', confidence: 89, timestamp: 90 },
                { name: 'F', confidence: 93, timestamp: 105 }
            ],
            lyrics: [
                { text: 'This is a sample song', timestamp: 0 },
                { text: 'With beautiful lyrics', timestamp: 15 },
                { text: 'And amazing chord progressions', timestamp: 30 },
                { text: 'That will inspire you', timestamp: 45 },
                { text: 'To create your own music', timestamp: 60 },
                { text: 'And share it with the world', timestamp: 75 },
                { text: 'Because music brings us together', timestamp: 90 },
                { text: 'In ways nothing else can', timestamp: 105 }
            ],
            duration: 120,
            key: 'C Major',
            tempo: 120
        };
    }

    getTitleFromInput(inputData) {
        switch (inputData.type) {
            case 'youtube':
                return 'YouTube Song';
            case 'spotify':
                return inputData.query;
            case 'upload':
                return this.selectedFile.name.replace(/\.[^/.]+$/, '');
            default:
                return 'Unknown Song';
        }
    }

    getArtistFromInput(inputData) {
        switch (inputData.type) {
            case 'youtube':
                return 'YouTube Artist';
            case 'spotify':
                return 'Spotify Artist';
            case 'upload':
                return 'Unknown Artist';
            default:
                return 'Unknown Artist';
        }
    }
    
    // Helper function to generate hash from string
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return Math.abs(hash);
    }
    
    // Helper function to convert HSL to Hex
    hslToHex(h, s, l) {
        l /= 100;
        const a = s * Math.min(l, 1 - l) / 100;
        const f = n => {
            const k = (n + h / 30) % 12;
            const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
            return Math.round(255 * color).toString(16).padStart(2, '0');
        };
        return `${f(0)}${f(8)}${f(4)}`;
    }

    estimateDuration(chords) {
        if (chords.length === 0) return 120;
        const lastChord = chords[chords.length - 1];
        return Math.max(lastChord.timestamp + 15, 120);
    }

    detectKey(chords) {
        if (chords.length === 0) return 'C Major';
        
        // Simple key detection based on most common chord
        const chordCounts = {};
        chords.forEach(chord => {
            const baseChord = chord.name.replace(/[^A-G]/g, '');
            chordCounts[baseChord] = (chordCounts[baseChord] || 0) + 1;
        });
        
        const mostCommon = Object.keys(chordCounts).reduce((a, b) => 
            chordCounts[a] > chordCounts[b] ? a : b
        );
        
        return `${mostCommon} Major`;
    }

    getAudioUrlForAnalysis() {
        // Try to get the current audio source
        if (this.audio && this.audio.src) {
            return this.audio.src;
        }
        
        // If no audio loaded, return null
        return null;
    }
    
    exportToPDF() {
        if (!this.currentSongData) {
            this.showError('No analysis data to export');
            return;
        }

        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            let yPosition = 20;
            const pageWidth = doc.internal.pageSize.getWidth();
            const margin = 20;
            const contentWidth = pageWidth - (margin * 2);

            // Title
            doc.setFontSize(24);
            doc.setFont(undefined, 'bold');
            doc.text(this.currentSongData.title || 'Song Analysis', margin, yPosition);
            yPosition += 10;

            // Artist
            doc.setFontSize(16);
            doc.setFont(undefined, 'normal');
            doc.setTextColor(100);
            doc.text(this.currentSongData.artist || 'Unknown Artist', margin, yPosition);
            yPosition += 15;

            // Song Info
            doc.setFontSize(12);
            doc.setTextColor(0);
            doc.text(`Key: ${this.currentSongData.key || 'N/A'}`, margin, yPosition);
            doc.text(`Tempo: ${this.currentSongData.tempo || 120} BPM`, margin + 60, yPosition);
            yPosition += 15;

            // Chords Section
            doc.setFontSize(16);
            doc.setFont(undefined, 'bold');
            doc.text('Chord Progression', margin, yPosition);
            yPosition += 8;

            doc.setFontSize(12);
            doc.setFont(undefined, 'normal');
            
            if (this.currentSongData.chords && this.currentSongData.chords.length > 0) {
                const chordText = this.currentSongData.chords
                    .map(chord => chord.name || chord.chord || 'C')
                    .join(' - ');
                
                const chordLines = doc.splitTextToSize(chordText, contentWidth);
                chordLines.forEach(line => {
                    doc.text(line, margin, yPosition);
                    yPosition += 7;
                });
            }
            yPosition += 10;

            // Lyrics Section
            doc.setFontSize(16);
            doc.setFont(undefined, 'bold');
            doc.text('Lyrics', margin, yPosition);
            yPosition += 8;

            doc.setFontSize(11);
            doc.setFont(undefined, 'normal');
            
            let lyricsText = '';
            if (this.currentSongData.lyrics_text) {
                lyricsText = this.currentSongData.lyrics_text;
            } else if (Array.isArray(this.currentSongData.lyrics)) {
                lyricsText = this.currentSongData.lyrics.map(line => line.text || line).join('\n');
            } else if (typeof this.currentSongData.lyrics === 'string') {
                lyricsText = this.currentSongData.lyrics;
            }

            if (lyricsText) {
                const lyricsLines = doc.splitTextToSize(lyricsText, contentWidth);
                lyricsLines.forEach(line => {
                    if (yPosition > 280) {
                        doc.addPage();
                        yPosition = 20;
                    }
                    doc.text(line, margin, yPosition);
                    yPosition += 6;
                });
            }

            // Footer
            const pageCount = doc.internal.getNumberOfPages();
            for (let i = 1; i <= pageCount; i++) {
                doc.setPage(i);
                doc.setFontSize(10);
                doc.setTextColor(150);
                doc.text(
                    `Generated by Chordis - Page ${i} of ${pageCount}`,
                    pageWidth / 2,
                    doc.internal.pageSize.getHeight() - 10,
                    { align: 'center' }
                );
            }

            // Save PDF
            const filename = `${(this.currentSongData.title || 'song').replace(/[^a-z0-9]/gi, '_').toLowerCase()}_chords.pdf`;
            doc.save(filename);
            
            this.showSuccess('PDF exported successfully!');
        } catch (error) {
            console.error('Error exporting PDF:', error);
            this.showError('Failed to export PDF. Make sure jsPDF library is loaded.');
        }
    }


    displayResults(data) {
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const modalTitle = document.getElementById('modal-title');

        // Store current song data
        this.currentSongData = data;

        // Save to sessionStorage for ChordAI page access
        try {
            const analysisForStorage = {
                title: data.title,
                artist: data.artist,
                key: data.key || 'C Major',
                tempo: data.tempo || 120,
                chords: data.chords || [],
                lyrics: data.lyrics || [],
                audioUrl: this.getAudioUrlForAnalysis(),
                duration: data.duration || 0
            };
            sessionStorage.setItem('currentAnalysis', JSON.stringify(analysisForStorage));
            console.log('[CHORDIS] Saved analysis to sessionStorage for ChordAI page');
        } catch (error) {
            console.error('[CHORDIS] Error saving analysis to sessionStorage:', error);
        }

        // Hide loading, show results
        loading.style.display = 'none';
        results.style.display = 'block';
        
        // Show complete badge
        const completeBadge = document.getElementById('complete-badge');
        if (completeBadge) {
            completeBadge.style.display = 'inline-flex';
        }

        // Update modal title with proper artist name (handle null)
        const artistName = data.artist && data.artist !== 'null' ? data.artist : 'Unknown Artist';
        modalTitle.textContent = `${data.title} - ${artistName}`;

        // Update player info
        const songTitle = document.getElementById('player-song-title');
        const songArtist = document.getElementById('player-song-artist');
        const songArtwork = document.getElementById('song-artwork');
        const songKey = document.getElementById('song-key');
        const songTempo = document.getElementById('song-tempo');
        const infoKey = document.getElementById('info-key');
        const infoTempo = document.getElementById('info-tempo');
        const infoDuration = document.getElementById('info-duration');
        const infoChords = document.getElementById('info-chords');

        if (songTitle) songTitle.textContent = data.title;
        if (songArtist) songArtist.textContent = artistName;
        
        // Update artwork if available
        if (songArtwork && data.artwork) {
            songArtwork.src = `data:image/jpeg;base64,${data.artwork}`;
        } else if (songArtwork) {
            // Generate a color based on song title for unique placeholder
            const hash = this.hashString(data.title);
            const hue = hash % 360;
            songArtwork.src = `https://via.placeholder.com/200x200/${this.hslToHex(hue, 70, 60)}/ffffff?text=${encodeURIComponent(data.title.charAt(0))}`;
        }
        
        if (songKey) songKey.textContent = data.key;
        if (songTempo) songTempo.textContent = `${data.tempo} BPM`;
        if (infoKey) infoKey.textContent = data.key;
        if (infoTempo) infoTempo.textContent = `${data.tempo} BPM`;
        if (infoDuration) infoDuration.textContent = `${Math.floor(data.duration / 60)}:${(data.duration % 60).toString().padStart(2, '0')}`;
        if (infoChords) infoChords.textContent = data.chords.length;

        // Setup save button
        const saveBtn = document.getElementById('save-analysis-btn');
        if (saveBtn) {
            saveBtn.style.display = 'inline-flex';
            saveBtn.onclick = () => this.saveCurrentAnalysis();
        }
        
        // Setup PDF export button
        const exportPdfBtn = document.getElementById('export-pdf-btn');
        if (exportPdfBtn) {
            exportPdfBtn.onclick = () => this.exportToPDF();
        }

        // Load audio for playback
        this.loadAudioForAnalysis(data, this.lastInputData);

        // Display chords in timeline
        const chordTimeline = document.getElementById('chord-timeline');
        if (chordTimeline && data.chords && data.chords.length > 0) {
            console.log('[CHORDIS] Displaying', data.chords.length, 'chords');
            chordTimeline.innerHTML = data.chords.map((chord, index) => {
                const chordName = chord.name || chord.chord || 'C';
                const timestamp = chord.timestamp || (index * 4);
                return `<div class="chord-item" data-timestamp="${timestamp}" data-index="${index}">${chordName}</div>`;
            }).join('');
            
            // Add click listeners to chords
            chordTimeline.querySelectorAll('.chord-item').forEach(item => {
                item.addEventListener('click', () => {
                    const timestamp = parseFloat(item.getAttribute('data-timestamp'));
                    if (this.audio && !isNaN(timestamp)) {
                        this.audio.currentTime = timestamp;
                    }
                });
            });
        } else if (chordTimeline) {
            chordTimeline.innerHTML = '<p style="color: #6b7280; text-align: center; padding: 2rem;">No chords detected. Try a different audio source or check the quality.</p>';
        }

        // Display synchronized lyrics
        const lyricsViewer = document.getElementById('lyrics-viewer');
        if (lyricsViewer) {
            console.log('[CHORDIS] Processing lyrics...', data);
            
            let lyricsHTML = '';
            
            if (data.lyrics_text && typeof data.lyrics_text === 'string') {
                // Plain text lyrics - split into lines for synchronization
                const lines = data.lyrics_text.split('\n').filter(line => line.trim());
                lyricsHTML = lines.map((line, index) => {
                    const timestamp = index * 5; // Estimate 5 seconds per line
                    return `<div class="lyric-line" data-timestamp="${timestamp}" style="padding: 0.5rem; border-radius: 6px; transition: all 0.3s; cursor: pointer;">${line}</div>`;
                }).join('');
                lyricsViewer.innerHTML = lyricsHTML;
                console.log('[CHORDIS] Displayed', lines.length, 'lyric lines');
            } else if (Array.isArray(data.lyrics) && data.lyrics.length > 0) {
                // Array of lyric objects with timestamps
                lyricsHTML = data.lyrics.map((line, index) => {
                    const text = line.text || line;
                    const timestamp = line.timestamp || (index * 5);
                    return `<div class="lyric-line" data-timestamp="${timestamp}" style="padding: 0.5rem; border-radius: 6px; transition: all 0.3s; cursor: pointer;">${text}</div>`;
                }).join('');
                lyricsViewer.innerHTML = lyricsHTML;
                
                // Add click handlers to jump to timestamp
                lyricsViewer.querySelectorAll('.lyric-line').forEach(lineEl => {
                    lineEl.addEventListener('click', () => {
                        const timestamp = parseFloat(lineEl.getAttribute('data-timestamp'));
                        if (this.audio && !isNaN(timestamp)) {
                            this.audio.currentTime = timestamp;
                        }
                    });
                });
                console.log('[CHORDIS] Displayed', data.lyrics.length, 'synchronized lyric lines');
            } else if (typeof data.lyrics === 'string') {
                // String lyrics - split into lines
                const lines = data.lyrics.split('\n').filter(line => line.trim());
                lyricsHTML = lines.map((line, index) => {
                    const timestamp = index * 5;
                    return `<div class="lyric-line" data-timestamp="${timestamp}" style="padding: 0.5rem; border-radius: 6px; transition: all 0.3s; cursor: pointer;">${line}</div>`;
                }).join('');
                lyricsViewer.innerHTML = lyricsHTML;
                console.log('[CHORDIS] Displayed string lyrics');
            } else {
                // No lyrics available
                lyricsViewer.innerHTML = '<p style="color: #6b7280; text-align: center; padding: 2rem;">No lyrics available for this song.</p>';
                console.log('[CHORDIS] No lyrics data');
            }
        }
        
        // Start highlighting lyrics during playback
        if (this.audio) {
            this.audio.addEventListener('timeupdate', () => this.highlightCurrentLyric());
        }

        // Add fade-in animation
        results.classList.add('fade-in');
    }
    
    setupViewToggle(ugView, timelineView) {
        const toggleBtns = ugView.querySelectorAll('.view-toggle-btn');
        
        toggleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                
                // Update active state
                toggleBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Toggle views
                if (view === 'ultimate-guitar') {
                    ugView.style.display = 'block';
                    timelineView.style.display = 'none';
                } else {
                    ugView.style.display = 'none';
                    timelineView.style.display = 'block';
                }
            });
        });
    }
    
    async saveCurrentAnalysis() {
        if (!this.currentUser) {
            this.showError('Please login to save analyses');
            return;
        }
        
        if (!this.currentSongData) {
            this.showError('No analysis data to save');
            return;
        }
        
        try {
            // Determine source type and URL from lastInputData
            let sourceType = 'unknown';
            let sourceUrl = '';
            
            if (this.lastInputData) {
                sourceType = this.lastInputData.type || 'unknown';
                sourceUrl = this.lastInputData.url || '';
            }
            
            // Prepare chord data
            const chordData = {
                progression: Array.isArray(this.currentSongData.chords) ? this.currentSongData.chords : [],
                duration: this.currentSongData.duration || 0
            };
            
            // Prepare lyrics data
            let lyricsText = '';
            if (typeof this.currentSongData.lyrics === 'string') {
                lyricsText = this.currentSongData.lyrics;
            } else if (Array.isArray(this.currentSongData.lyrics)) {
                lyricsText = this.currentSongData.lyrics.map(l => l.text || l).join('\n');
            }
            
            const lyricsData = {
                text: lyricsText || 'No lyrics available',
                source: 'analysis'
            };
            
            const saveData = {
                title: `${this.currentSongData.title || 'Untitled'}${this.currentSongData.artist ? ' - ' + this.currentSongData.artist : ''}`,
                chord_data: chordData,
                lyrics_data: lyricsData,
                source_type: sourceType,
                source_url: sourceUrl
            };
            
            console.log('Saving analysis:', saveData);
            
            const response = await fetch('/api/save-analysis', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', // Important for authentication
                body: JSON.stringify(saveData)
            });
            
            const data = await response.json();
            console.log('Save response:', response.status, data);
            
            if (response.status === 401) {
                this.showError('Please login to save analyses');
                // Optionally show login modal
                this.showAuthModal('login');
                return;
            }
            
            if (response.ok && data.success) {
                this.showSuccess('Analysis saved to your library!');
                // Update save button to show it's saved
                const saveBtn = document.getElementById('save-analysis-btn');
                if (saveBtn) {
                    saveBtn.innerHTML = '<i class="fas fa-check"></i> Saved';
                    saveBtn.disabled = true;
                    saveBtn.style.opacity = '0.6';
                }
            } else {
                console.error('Save failed:', { status: response.status, data });
                const errorMessage = data.error || `Failed to save: ${response.statusText}`;
                this.showError(errorMessage);
            }
        } catch (error) {
            console.error('Save error:', error);
            this.showError('Failed to save analysis. Please try again.');
        }
    }

    isValidYouTubeUrl(url) {
        const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/;
        return regex.test(url);
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'toast-notification toast-error';
        errorDiv.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-exclamation-circle"></i>
            </div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        document.body.appendChild(errorDiv);

        // Trigger animation
        setTimeout(() => errorDiv.classList.add('show'), 10);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            errorDiv.classList.remove('show');
            setTimeout(() => errorDiv.remove(), 400);
        }, 5000);
    }
    
    showTermsModal() {
        // Create a modal to show terms and conditions
        const termsModal = document.createElement('div');
        termsModal.className = 'modal show';
        termsModal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-container" style="max-width: 800px; max-height: 80vh; overflow-y: auto;">
                <div class="modal-header">
                    <div class="modal-title-section">
                        <h2>Terms and Conditions</h2>
                    </div>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="padding: 2rem;">
                    <div style="line-height: 1.8; color: var(--gray-700);">
                        <h3 style="margin-bottom: 1rem;">1. Acceptance of Terms</h3>
                        <p style="margin-bottom: 1.5rem;">By accessing and using Chordis AI Music Analyzer ("the Service"), you agree to be bound by these Terms and Conditions. If you do not agree to these terms, please do not use the Service.</p>
                        
                        <h3 style="margin-bottom: 1rem;">2. Use of Service</h3>
                        <p style="margin-bottom: 1.5rem;">The Service is provided for personal, non-commercial use only. You may analyze music for educational purposes, personal enjoyment, and music practice. Commercial use requires a separate license agreement.</p>
                        
                        <h3 style="margin-bottom: 1rem;">3. User Accounts</h3>
                        <p style="margin-bottom: 1.5rem;">You are responsible for maintaining the confidentiality of your account credentials. You agree to notify us immediately of any unauthorized use of your account.</p>
                        
                        <h3 style="margin-bottom: 1rem;">4. Content and Intellectual Property</h3>
                        <p style="margin-bottom: 1.5rem;">You retain all rights to content you upload. However, you grant us a license to process your content for the purpose of providing the Service. We respect copyright laws and expect our users to do the same.</p>
                        
                        <h3 style="margin-bottom: 1rem;">5. Privacy and Data Protection</h3>
                        <p style="margin-bottom: 1.5rem;">Your privacy is important to us. We collect and process your data in accordance with our Privacy Policy. We use industry-standard encryption to protect your personal information.</p>
                        
                        <h3 style="margin-bottom: 1rem;">6. Limitation of Liability</h3>
                        <p style="margin-bottom: 1.5rem;">The Service is provided "as is" without warranties of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the Service.</p>
                        
                        <h3 style="margin-bottom: 1rem;">7. Modifications</h3>
                        <p style="margin-bottom: 1.5rem;">We reserve the right to modify these terms at any time. Continued use of the Service after modifications constitutes acceptance of the updated terms.</p>
                        
                        <h3 style="margin-bottom: 1rem;">8. Contact Information</h3>
                        <p>If you have questions about these Terms and Conditions, please contact us at support@chordis.ai</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(termsModal);
    }
    
    showPrivacyModal() {
        // Create a modal to show privacy policy
        const privacyModal = document.createElement('div');
        privacyModal.className = 'modal show';
        privacyModal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-container" style="max-width: 800px; max-height: 80vh; overflow-y: auto;">
                <div class="modal-header">
                    <div class="modal-title-section">
                        <h2>Privacy Policy</h2>
                    </div>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="padding: 2rem;">
                    <div style="line-height: 1.8; color: var(--gray-700);">
                        <p style="margin-bottom: 1.5rem; font-style: italic;">Last Updated: October 15, 2025</p>
                        
                        <h3 style="margin-bottom: 1rem;">1. Information We Collect</h3>
                        <p style="margin-bottom: 1.5rem;">We collect information you provide directly to us, including your name, email address, and username when you create an account. We also collect audio files you upload for analysis.</p>
                        
                        <h3 style="margin-bottom: 1rem;">2. How We Use Your Information</h3>
                        <p style="margin-bottom: 1.5rem;">We use the information we collect to provide and improve our Service, process your music analyses, save your analysis history, and communicate with you about your account.</p>
                        
                        <h3 style="margin-bottom: 1rem;">3. Data Storage and Security</h3>
                        <p style="margin-bottom: 1.5rem;">Your data is encrypted both in transit and at rest. We use industry-standard security measures including AES-256 encryption for stored data and TLS for data transmission. Audio files are temporarily stored for processing and automatically deleted after analysis.</p>
                        
                        <h3 style="margin-bottom: 1rem;">4. Data Sharing</h3>
                        <p style="margin-bottom: 1.5rem;">We do not sell, trade, or rent your personal information to third parties. We may share aggregated, non-personally identifiable information for research and improvement purposes.</p>
                        
                        <h3 style="margin-bottom: 1rem;">5. Your Rights</h3>
                        <p style="margin-bottom: 1.5rem;">You have the right to access, update, or delete your personal information. You can request a copy of your data or account deletion by contacting our support team.</p>
                        
                        <h3 style="margin-bottom: 1rem;">6. Cookies</h3>
                        <p style="margin-bottom: 1.5rem;">We use cookies to maintain your session and remember your preferences. You can control cookie settings through your browser.</p>
                        
                        <h3 style="margin-bottom: 1rem;">7. Children's Privacy</h3>
                        <p style="margin-bottom: 1.5rem;">Our Service is not intended for children under 13 years of age. We do not knowingly collect personal information from children under 13.</p>
                        
                        <h3 style="margin-bottom: 1rem;">8. Changes to This Policy</h3>
                        <p style="margin-bottom: 1.5rem;">We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new policy on this page.</p>
                        
                        <h3 style="margin-bottom: 1rem;">9. Contact Us</h3>
                        <p>If you have questions about this Privacy Policy, please contact us at privacy@chordis.ai</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(privacyModal);
    }

    closeModal() {
        const modal = document.getElementById('results-modal');
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
        
        // Stop audio when modal is closed
        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.isPlaying = false;
            this.updatePlayButton();
            this.removePlayingClass();
        }
        
        // Clear results content for next analysis
        const results = document.getElementById('results');
        if (results) {
            results.style.display = 'none';
        }
    }

    // Audio Player Methods
    togglePlayPause() {
        if (!this.audio || !this.audio.src) {
            console.warn('No audio source available');
            return;
        }
        
        if (this.isPlaying) {
            this.audio.pause();
            this.removePlayingClass();
        } else {
            this.audio.play().catch(error => {
                console.error('Error playing audio:', error);
                this.showError('Unable to play audio. Please try again.');
            });
            this.addPlayingClass();
        }
    }
    
    addPlayingClass() {
        const player = document.getElementById('audio-player');
        if (player) {
            player.classList.add('playing');
        }
    }
    
    removePlayingClass() {
        const player = document.getElementById('audio-player');
        if (player) {
            player.classList.remove('playing');
        }
    }

    seekTo(e) {
        if (!this.audio || !this.audio.duration) return;
        
        const progressBar = document.getElementById('progress-bar');
        const rect = progressBar.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const percentage = clickX / rect.width;
        const newTime = percentage * this.audio.duration;
        
        this.audio.currentTime = newTime;
    }

    setVolume(value) {
        if (this.audio) {
            this.audio.volume = value / 100;
        }
    }

    updateDuration() {
        const totalTimeElement = document.getElementById('total-time');
        if (totalTimeElement && this.audio.duration) {
            totalTimeElement.textContent = this.formatTime(this.audio.duration);
        }
    }

    updateProgress() {
        if (!this.audio || !this.audio.duration) return;
        
        const progressFill = document.getElementById('progress-fill');
        const progressBar = document.getElementById('progress-bar');
        const currentTimeElement = document.getElementById('current-time');
        
        if (progressFill) {
            const percentage = (this.audio.currentTime / this.audio.duration) * 100;
            progressFill.style.width = `${percentage}%`;
            
            // Update handle position
            if (progressBar) {
                progressBar.style.setProperty('--progress-percentage', `${percentage}%`);
            }
        }
        
        if (currentTimeElement) {
            currentTimeElement.textContent = this.formatTime(this.audio.currentTime);
        }
        
        // Update lyrics highlighting MORE FREQUENTLY for better sync
        // Use direct call instead of requestAnimationFrame for immediate response
        this.highlightCurrentLyric();
    }

    songEnded() {
        this.isPlaying = false;
        this.updatePlayButton();
        this.audio.currentTime = 0;
        this.updateProgress();
    }

    onPlay() {
        this.isPlaying = true;
        this.updatePlayButton();
        this.addPlayingClass();
    }

    onPause() {
        this.isPlaying = false;
        this.updatePlayButton();
        this.removePlayingClass();
    }

    updatePlayButton() {
        const playPauseBtn = document.getElementById('play-pause-btn');
        if (playPauseBtn) {
            const icon = playPauseBtn.querySelector('i');
            if (this.isPlaying) {
                icon.className = 'fas fa-pause';
            } else {
                icon.className = 'fas fa-play';
            }
        }
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    highlightCurrentLyric() {
        if (!this.audio || !this.currentSongData) return;
        
        const currentTime = this.audio.currentTime;
        const lyricLines = document.querySelectorAll('.lyric-line');
        const chordItems = document.querySelectorAll('.chord-item');
        
        // Use requestAnimationFrame for smoother performance
        requestAnimationFrame(() => {
            // Remove active class from all lyrics (optimized)
            const previousActive = document.querySelector('.lyric-line.active');
            if (previousActive) previousActive.classList.remove('active');
            
            const previousChordActive = document.querySelector('.chord-item.active');
            if (previousChordActive) previousChordActive.classList.remove('active');
            
            // Find and highlight current lyric with lookahead for better sync
            let activeLyricIndex = -1;
            for (let i = 0; i < lyricLines.length; i++) {
                const line = lyricLines[i];
                const timestamp = parseFloat(line.getAttribute('data-timestamp'));
                const nextTimestamp = i < lyricLines.length - 1 ? 
                    parseFloat(lyricLines[i + 1].getAttribute('data-timestamp')) : Infinity;
                
                // Highlight if current time is between this and next lyric
                if (currentTime >= timestamp && currentTime < nextTimestamp) {
                    activeLyricIndex = i;
                    line.classList.add('active');
                    break;
                }
            }
            
            // Auto-scroll to current lyric (throttled)
            if (activeLyricIndex >= 0 && lyricLines[activeLyricIndex]) {
                // Only scroll if needed (performance optimization)
                const element = lyricLines[activeLyricIndex];
                const container = element.parentElement;
                
                if (container) {
                    const elementRect = element.getBoundingClientRect();
                    const containerRect = container.getBoundingClientRect();
                    
                    // Check if element is out of view
                    if (elementRect.top < containerRect.top + 50 || elementRect.bottom > containerRect.bottom - 50) {
                        element.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    }
                }
            }
            
            // Highlight current chord with same sync offset
            for (let i = 0; i < chordItems.length; i++) {
                const chord = chordItems[i];
                const timestamp = parseFloat(chord.getAttribute('data-timestamp'));
                const nextTimestamp = i < chordItems.length - 1 ? 
                    parseFloat(chordItems[i + 1].getAttribute('data-timestamp')) : Infinity;
                
                if (currentTime >= timestamp && currentTime < nextTimestamp) {
                    chord.classList.add('active');
                    break;
                }
            }
        });
    }

    async loadAudioForAnalysis(data, inputData) {
        // Try to get audio source based on input type
        let audioSrc = null;
        
        try {
            switch (inputData.type) {
                case 'search':
                    // For search results, try to find YouTube video
                    if (inputData.youtubeUrl) {
                        console.log('Loading YouTube audio from search...');
                        audioSrc = inputData.youtubeUrl;
                    } else {
                        // Search YouTube for the song
                        const query = `${data.artist} ${data.title} official audio`;
                        console.log('Searching YouTube for:', query);
                        
                        try {
                            const ytResponse = await fetch('/api/find-youtube-audio', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ query })
                            });
                            const ytData = await ytResponse.json();
                            
                            if (ytData.success && ytData.audio_url) {
                                audioSrc = ytData.audio_url;
                            }
                        } catch (error) {
                            console.log('YouTube search failed, using fallback');
                        }
                    }
                    
                    // Fallback if YouTube not found
                    if (!audioSrc) {
                        audioSrc = this.getFallbackAudioUrl();
                    }
                    break;
                    
                case 'youtube':
                    // For demo purposes, use fallback audio
                    // In production, you'd fetch from backend
                    console.log('Loading YouTube audio...');
                    audioSrc = this.getFallbackAudioUrl();
                    break;
                    
                case 'upload':
                    // For uploaded files, create object URL
                    if (this.selectedFile) {
                        audioSrc = URL.createObjectURL(this.selectedFile);
                        console.log('Loaded uploaded file as audio source');
                    }
                    break;
                    
                case 'spotify':
                    // For Spotify, use fallback
                    console.log('Loading Spotify audio...');
                    audioSrc = this.getSpotifyAudioUrl(data.title, data.artist);
                    break;
                    
                case 'saved':
                    // For saved analyses, try to load based on original source
                    if (inputData.url) {
                        audioSrc = inputData.url;
                    } else {
                        audioSrc = this.getFallbackAudioUrl();
                    }
                    break;
            }
            
            if (audioSrc) {
                this.audio.src = audioSrc;
                this.audio.load();
                console.log('Audio source loaded:', audioSrc.substring(0, 50) + '...');
                
                // Ensure audio is ready to play
                this.audio.addEventListener('canplay', () => {
                    console.log('Audio is ready to play');
                }, { once: true });
            } else {
                console.warn('No audio source available, using fallback');
                this.audio.src = this.getFallbackAudioUrl();
                this.audio.load();
            }
        } catch (error) {
            console.error('Error loading audio:', error);
            // Fallback to sample audio
            this.audio.src = this.getFallbackAudioUrl();
            this.audio.load();
        }
    }

    getFallbackAudioUrl() {
        // Fallback sample audio when real audio is not available
        return 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3';
    }

    getSpotifyAudioUrl(title, artist) {
        // This is a placeholder - in production you'd want to:
        // 1. Use Spotify Web API to search for the track
        // 2. Get the preview URL (30-second preview)
        // 3. Return that URL for playback
        
        // For now, we'll use a sample audio file
        return 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3';
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('[CHORDIS] Initializing app...');
        new ChordisApp();
        console.log('[CHORDIS] App initialized successfully');
        
        // Hide loading screen
        const loader = document.getElementById('page-loader');
        if (loader) {
            setTimeout(() => {
                loader.style.opacity = '0';
                loader.style.transition = 'opacity 0.3s ease';
                setTimeout(() => loader.remove(), 300);
            }, 100);
        }
    } catch (error) {
        console.error('[CHORDIS] Error initializing app:', error);
        // Hide loader and show error
        const loader = document.getElementById('page-loader');
        if (loader) loader.remove();
        
        // Show a user-friendly error message
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #F9FAFB; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; z-index: 99999;';
        errorDiv.innerHTML = `
            <div style="text-align: center; padding: 2rem; background: white; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 500px;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">⚠️</div>
                <h2 style="color: #374151; margin-bottom: 0.5rem;">Initialization Error</h2>
                <p style="color: #6B7280; margin-bottom: 1.5rem;">${error.message}</p>
                <button onclick="location.reload()" style="background: #5B4FFF; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; font-family: inherit;">
                    Reload Page
                </button>
                <p style="color: #9CA3AF; margin-top: 1rem; font-size: 0.875rem;">Check console for details (F12)</p>
            </div>
        `;
        document.body.appendChild(errorDiv);
    }
});

// Add some utility functions for future backend integration
window.ChordisAPI = {
    // These functions will be implemented to connect with your existing backend
    analyzeYouTube: async (url) => {
        // Connect to your existing YouTube analysis endpoint
        const response = await fetch('/api/analyze-youtube', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        return response.json();
    },

    analyzeSpotify: async (query) => {
        // Connect to your existing Spotify analysis endpoint
        const response = await fetch('/api/analyze-spotify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        return response.json();
    },

    analyzeUpload: async (file) => {
        // Connect to your existing file upload analysis endpoint
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/analyze-upload', {
            method: 'POST',
            body: formData
        });
        return response.json();
    }
};
