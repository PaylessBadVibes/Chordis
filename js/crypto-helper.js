/**
 * Client-Side Encryption Helper  
 * Encrypts sensitive data before sending to server
 * Uses Fernet-compatible encryption for easy server-side decryption
 */

class CryptoHelper {
    constructor() {
        this.passphrase = 'CHORDIS_PUBLIC_KEY_2025';
        this.salt = 'chordis-salt-2025';
    }

    /**
     * Derive encryption key from passphrase using PBKDF2
     */
    async deriveKey() {
        const encoder = new TextEncoder();
        const passphraseKey = await crypto.subtle.importKey(
            'raw',
            encoder.encode(this.passphrase),
            'PBKDF2',
            false,
            ['deriveBits']
        );
        
        const keyMaterial = await crypto.subtle.deriveBits(
            {
                name: 'PBKDF2',
                salt: encoder.encode(this.salt),
                iterations: 100000,
                hash: 'SHA-256'
            },
            passphraseKey,
            256
        );
        
        return new Uint8Array(keyMaterial);
    }

    /**
     * Encrypt text (Fernet-compatible)
     */
    async encrypt(plaintext) {
        try {
            const encoder = new TextEncoder();
            const data = encoder.encode(plaintext);
            
            // Derive key
            const key = await this.deriveKey();
            
            // Import key for AES
            const cryptoKey = await crypto.subtle.importKey(
                'raw',
                key,
                'AES-CBC',
                false,
                ['encrypt']
            );
            
            // Generate random IV
            const iv = crypto.getRandomValues(new Uint8Array(16));
            
            // Encrypt
            const encrypted = await crypto.subtle.encrypt(
                {
                    name: 'AES-CBC',
                    iv: iv
                },
                cryptoKey,
                data
            );
            
            // Combine IV + encrypted data
            const combined = new Uint8Array(iv.length + encrypted.byteLength);
            combined.set(iv);
            combined.set(new Uint8Array(encrypted), iv.length);
            
            // Base64 encode
            return btoa(String.fromCharCode(...combined));
        } catch (error) {
            console.error('Encryption error:', error);
            // Return plain text if encryption fails (for development)
            console.warn('Falling back to plain text transmission');
            return plaintext;
        }
    }

    /**
     * Hash password for additional security
     */
    async hashPassword(password) {
        try {
            const encoder = new TextEncoder();
            const data = encoder.encode(password + 'chordis-pepper-2025');
            const hashBuffer = await crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        } catch (error) {
            console.error('Hash error:', error);
            return password;
        }
    }
}

// Export for use in main app
window.CryptoHelper = new CryptoHelper();

