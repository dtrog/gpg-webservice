// GPG Webservice Dashboard - Shared JavaScript

// API Configuration
// Determine API base URL based on environment
function getApiBase() {
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // Development: Direct connection to Flask
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:5555';
    }
    
    // Production via domain (Caddy handles routing): no port needed
    if (port === '' || port === '443' || port === '80') {
        return window.location.protocol + '//' + hostname;
    }
    
    // Production via direct port access (8080): use explicit Flask port
    return window.location.protocol + '//' + hostname + ':5555';
}

const API_BASE = getApiBase();

console.log('[GPG Dashboard] Environment:', {
    hostname: window.location.hostname,
    port: window.location.port,
    protocol: window.location.protocol,
    apiBase: API_BASE
});

// Utility function to show alerts
function showAlert(message, type = 'info') {
    const container = document.getElementById('alert-container');
    if (!container) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    container.innerHTML = '';
    container.appendChild(alert);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transition = 'opacity 0.5s';
        setTimeout(() => alert.remove(), 500);
    }, 5000);
}

// Utility function to validate email
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Utility function to validate password strength
function validatePassword(password) {
    const errors = [];

    if (password.length < 8) {
        errors.push('Password must be at least 8 characters long');
    }
    if (!/[a-z]/.test(password)) {
        errors.push('Password must contain at least one lowercase letter');
    }
    if (!/[A-Z]/.test(password)) {
        errors.push('Password must contain at least one uppercase letter');
    }
    if (!/\d/.test(password)) {
        errors.push('Password must contain at least one digit');
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
        errors.push('Password must contain at least one special character');
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}

// Utility function to validate username
function validateUsername(username) {
    const errors = [];

    if (username.length < 3) {
        errors.push('Username must be at least 3 characters long');
    }
    if (username.length > 50) {
        errors.push('Username must be no more than 50 characters long');
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
        errors.push('Username can only contain letters, numbers, underscores, and hyphens');
    }

    const reserved = ['admin', 'root', 'administrator', 'system', 'test', 'null', 'undefined'];
    if (reserved.includes(username.toLowerCase())) {
        errors.push('Username is reserved and cannot be used');
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}

// Session management
function storeApiKey(apiKey) {
    sessionStorage.setItem('gpg_api_key', apiKey);
}

function getApiKey() {
    return sessionStorage.getItem('gpg_api_key');
}

function clearSession() {
    sessionStorage.removeItem('gpg_api_key');
}

// Check if user is authenticated
function checkAuth() {
    const apiKey = getApiKey();
    if (!apiKey) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

// Make authenticated API requests
async function authenticatedFetch(url, options = {}) {
    const apiKey = getApiKey();
    if (!apiKey) {
        throw new Error('Not authenticated');
    }

    const headers = {
        ...options.headers,
        'X-API-KEY': apiKey
    };

    return fetch(url, {
        ...options,
        headers
    });
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Copy text to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return true;
        } catch (e) {
            document.body.removeChild(textArea);
            return false;
        }
    }
}

// Global error handler for fetch requests
async function handleFetchResponse(response) {
    if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
            const data = await response.json();
            errorMessage = data.error || data.message || errorMessage;
        } catch (e) {
            // Response wasn't JSON
        }
        throw new Error(errorMessage);
    }
    return response;
}

// Initialize tooltips or other UI enhancements
document.addEventListener('DOMContentLoaded', () => {
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to focus search (if present)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            const searchInput = document.querySelector('input[type="search"]');
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
            }
        }
    });

    // Add form validation helpers
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Visual feedback
                submitBtn.classList.add('loading');
            }
        });
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        API_BASE,
        showAlert,
        isValidEmail,
        validatePassword,
        validateUsername,
        storeApiKey,
        getApiKey,
        clearSession,
        checkAuth,
        authenticatedFetch,
        formatFileSize,
        copyToClipboard,
        handleFetchResponse
    };
}
