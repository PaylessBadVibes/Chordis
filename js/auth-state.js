/**
 * Authentication State Manager
 * Manages authentication state across multiple tabs/windows
 */

class AuthStateManager {
    constructor() {
        this.currentUser = null;
        this.listeners = [];
        this.init();
    }

    init() {
        // Check for existing auth state
        this.loadAuthState();

        // Listen for storage changes from other tabs
        window.addEventListener('storage', (e) => {
            if (e.key === 'chordis_auth_state') {
                console.log('[AUTH-STATE] Auth state changed in another tab');
                this.loadAuthState();
                this.notifyListeners();
            }
        });

        // Check auth status from server on load
        this.checkServerAuthStatus();
    }

    async checkServerAuthStatus() {
        try {
            const response = await fetch('/api/current-user', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.user) {
                    this.updateAuthState(data.user);
                } else {
                    this.clearAuthState();
                }
            } else {
                this.clearAuthState();
            }
        } catch (error) {
            console.log('[AUTH-STATE] Not logged in or server unavailable');
            this.clearAuthState();
        }
    }

    loadAuthState() {
        try {
            const authStateStr = localStorage.getItem('chordis_auth_state');
            if (authStateStr) {
                const authState = JSON.parse(authStateStr);
                this.currentUser = authState.user;
                console.log('[AUTH-STATE] Loaded auth state:', this.currentUser?.username);
            } else {
                this.currentUser = null;
            }
        } catch (error) {
            console.error('[AUTH-STATE] Error loading auth state:', error);
            this.currentUser = null;
        }
    }

    updateAuthState(user) {
        this.currentUser = user;
        
        // Save to localStorage
        try {
            localStorage.setItem('chordis_auth_state', JSON.stringify({
                user: user,
                timestamp: Date.now()
            }));
            console.log('[AUTH-STATE] Auth state updated:', user.username);
        } catch (error) {
            console.error('[AUTH-STATE] Error saving auth state:', error);
        }

        this.notifyListeners();
    }

    clearAuthState() {
        this.currentUser = null;
        
        try {
            localStorage.removeItem('chordis_auth_state');
            console.log('[AUTH-STATE] Auth state cleared');
        } catch (error) {
            console.error('[AUTH-STATE] Error clearing auth state:', error);
        }

        this.notifyListeners();
    }

    getCurrentUser() {
        return this.currentUser;
    }

    isLoggedIn() {
        return this.currentUser !== null;
    }

    addListener(callback) {
        this.listeners.push(callback);
    }

    removeListener(callback) {
        this.listeners = this.listeners.filter(cb => cb !== callback);
    }

    notifyListeners() {
        this.listeners.forEach(callback => {
            try {
                callback(this.currentUser);
            } catch (error) {
                console.error('[AUTH-STATE] Error in listener:', error);
            }
        });
    }

    // Update UI elements based on auth state
    updateUI() {
        const userInfoDisplay = document.getElementById('user-info-display');
        const usernameDisplay = document.getElementById('username');
        const verificationBadge = document.getElementById('verification-badge');
        const authBtnSignin = document.getElementById('auth-btn-signin');
        const authBtnSignup = document.getElementById('auth-btn-signup');
        const authBtnLogout = document.getElementById('auth-btn-logout');

        if (this.isLoggedIn()) {
            // Show user info
            if (userInfoDisplay) userInfoDisplay.style.display = 'flex';
            if (usernameDisplay) usernameDisplay.textContent = this.currentUser.username;
            
            // Update verification badge
            if (verificationBadge) {
                if (this.currentUser.email_verified) {
                    verificationBadge.textContent = '✓ Verified';
                    verificationBadge.className = 'user-badge verified';
                } else {
                    verificationBadge.textContent = 'Unverified';
                    verificationBadge.className = 'user-badge unverified';
                }
            }

            // Hide sign in/up buttons, show logout
            if (authBtnSignin) authBtnSignin.style.display = 'none';
            if (authBtnSignup) authBtnSignup.style.display = 'none';
            if (authBtnLogout) authBtnLogout.style.display = 'inline-flex';
        } else {
            // Show sign in/up buttons
            if (userInfoDisplay) userInfoDisplay.style.display = 'none';
            if (authBtnSignin) authBtnSignin.style.display = 'inline-flex';
            if (authBtnSignup) authBtnSignup.style.display = 'inline-flex';
            if (authBtnLogout) authBtnLogout.style.display = 'none';
        }
    }

    // Handle logout
    async logout() {
        try {
            await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('[AUTH-STATE] Logout error:', error);
        }

        this.clearAuthState();
        this.showToast('Logged out successfully', 'success');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        document.body.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }
}

// Create global instance
window.authStateManager = new AuthStateManager();

// Initialize UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Update UI initially
    window.authStateManager.updateUI();

    // Add listener to update UI on auth state changes
    window.authStateManager.addListener(() => {
        window.authStateManager.updateUI();
    });

    // Setup logout button
    const logoutBtn = document.getElementById('auth-btn-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await window.authStateManager.logout();
        });
    }

    console.log('[AUTH-STATE] Auth state manager initialized');
});

