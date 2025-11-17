"""
Security utilities for the GPG webservice.

This module provides security-related utilities including input validation,
rate limiting, and secure temporary file handling.
"""

import os
import re
import tempfile
import functools
from typing import Optional, Tuple
from flask import request, jsonify
from werkzeug.exceptions import BadRequest
import time
from collections import defaultdict, deque


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for given identifier.
        
        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] < window_start:
            self.requests[identifier].popleft()
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        
        return False


# Global rate limiters for different endpoint types
# Note: These will be initialized with config values at import time
from config import Config

auth_rate_limiter = RateLimiter(
    max_requests=Config.RATE_LIMIT_AUTH_REQUESTS,
    window_seconds=Config.RATE_LIMIT_AUTH_WINDOW
)
api_rate_limiter = RateLimiter(
    max_requests=Config.RATE_LIMIT_API_REQUESTS,
    window_seconds=Config.RATE_LIMIT_API_WINDOW
)


def rate_limit_auth(f):
    """Rate limiting decorator for authentication endpoints."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip rate limiting in testing mode
        from flask import current_app
        if current_app and current_app.config.get('TESTING'):
            return f(*args, **kwargs)

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        if not auth_rate_limiter.is_allowed(client_ip):
            # Log rate limit violation
            from utils.audit_logger import audit_logger
            audit_logger.log_rate_limit_hit('auth', username=None)
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

        return f(*args, **kwargs)
    return decorated_function


def rate_limit_api(f):
    """Rate limiting decorator for general API endpoints."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip rate limiting in testing mode
        from flask import current_app
        if current_app and current_app.config.get('TESTING'):
            return f(*args, **kwargs)

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        if not api_rate_limiter.is_allowed(client_ip):
            # Log rate limit violation
            from utils.audit_logger import audit_logger
            audit_logger.log_rate_limit_hit('api', username=None)
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

        return f(*args, **kwargs)
    return decorated_function


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username according to security requirements.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must be no more than 50 characters long"
    
    # Allow alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    # Prevent reserved usernames
    reserved = {'admin', 'root', 'administrator', 'system', 'test', 'null', 'undefined'}
    if username.lower() in reserved:
        return False, "Username is reserved and cannot be used"
    
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password according to security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be no more than 128 characters long"
    
    # Check for at least one lowercase, uppercase, digit, and special character
    checks = [
        (re.search(r'[a-z]', password), "Password must contain at least one lowercase letter"),
        (re.search(r'[A-Z]', password), "Password must contain at least one uppercase letter"), 
        (re.search(r'\d', password), "Password must contain at least one digit"),
        (re.search(r'[!@#$%^&*(),.?":{}|<>]', password), "Password must contain at least one special character")
    ]
    
    for check, message in checks:
        if not check:
            return False, message
    
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if len(email) > 254:
        return False, "Email address is too long"
    
    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email address format"
    
    return True, None


def secure_temp_directory() -> str:
    """
    Create a secure temporary directory with restricted permissions.
    
    Returns:
        Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    # Set restrictive permissions (owner read/write/execute only)
    os.chmod(temp_dir, 0o700)
    return temp_dir


def add_security_headers(response):
    """
    Add security headers to Flask response.
    
    Args:
        response: Flask response object
        
    Returns:
        Response object with security headers added
    """
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Strict transport security (HTTPS only)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content security policy
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response


def validate_file_upload(file, max_size_mb: int = 10, allowed_extensions: Optional[set] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file for security.
    
    Args:
        file: Werkzeug FileStorage object
        max_size_mb: Maximum file size in MB
        allowed_extensions: Set of allowed file extensions
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    if not file.filename:
        return False, "No filename provided"
    
    # Check file size (approximate, since we can't get exact size without reading)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        return False, f"File size exceeds {max_size_mb}MB limit"
    
    # Check file extension if provided
    if allowed_extensions:
        filename = file.filename.lower()
        if not any(filename.endswith(ext.lower()) for ext in allowed_extensions):
            return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, None