/**
 * Chordis App Initialization and Core Functionality
 * This file ensures the app works even if backend APIs are not fully configured
 */

(function() {
    'use strict';
    
    console.log('[CHORDIS-INIT] Starting initialization...');
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[CHORDIS-INIT] DOM ready, initializing features...');
        
        // Test if all required elements exist
        const requiredElements = {
            'search-query': 'Search Input',
            'analyze-btn': 'Analyze Button',
            'results-modal': 'Results Modal'
        };
        
        let allElementsFound = true;
        for (const [id, name] of Object.entries(requiredElements)) {
            const el = document.getElementById(id);
            if (el) {
                console.log(`[CHORDIS-INIT] ✅ Found: ${name}`);
            } else {
                console.error(`[CHORDIS-INIT] ❌ Missing: ${name} (#${id})`);
                allElementsFound = false;
            }
        }
        
        if (allElementsFound) {
            console.log('[CHORDIS-INIT] ✅ All required elements found');
        } else {
            console.error('[CHORDIS-INIT] ❌ Some elements are missing!');
        }
        
        // Add immediate search functionality test
        const searchInput = document.getElementById('search-query');
        if (searchInput) {
            console.log('[CHORDIS-INIT] Setting up immediate search test...');
            
            // Add visual feedback when typing
            searchInput.addEventListener('input', function(e) {
                const value = e.target.value;
                console.log('[SEARCH] Input changed:', value);
                
                // Show immediate visual feedback
                if (value.length > 0) {
                    searchInput.style.borderColor = '#6366f1';
                    searchInput.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.1)';
                } else {
                    searchInput.style.borderColor = '#e5e7eb';
                    searchInput.style.boxShadow = 'none';
                }
            });
            
            searchInput.addEventListener('focus', function() {
                console.log('[SEARCH] Input focused');
            });
        }
        
        // Test analyze button
        const analyzeBtn = document.getElementById('analyze-btn');
        if (analyzeBtn) {
            console.log('[CHORDIS-INIT] Analyze button found');
            analyzeBtn.addEventListener('click', function() {
                console.log('[ANALYZE] Button clicked!');
            });
        }
        
        // Test backend connectivity
        testBackendConnection();
        
        console.log('[CHORDIS-INIT] ✅ Initialization complete');
    });
    
    async function testBackendConnection() {
        try {
            console.log('[BACKEND] Testing server connection...');
            const response = await fetch('/api/current-user', {
                credentials: 'include'
            });
            console.log('[BACKEND] ✅ Server is responding! Status:', response.status);
        } catch (error) {
            console.error('[BACKEND] ❌ Server connection failed:', error);
            console.log('[BACKEND] Make sure Python server is running: python api.py');
        }
    }
    
})();

