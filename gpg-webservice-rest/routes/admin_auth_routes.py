"""
Admin authentication routes using GPG signature verification.

This module provides non-expiring authentication for administrators using
GPG signatures instead of session keys. Admins sign challenges with their
private key, and the system verifies with their public key stored in .env.

Flow:
1. Admin requests a challenge from /admin/auth/challenge
2. Server returns a random nonce and timestamp
3. Admin signs the challenge string with their GPG private key
4. Admin sends signature to /admin/auth/verify
5. Server verifies signature against admin's public key
6. Server returns a long-lived admin token (valid 24 hours)

Environment Variables:
- ADMIN_GPG_KEYS: JSON object mapping usernames to PGP public keys
  Example:
  {
    "administrator": "-----BEGIN PGP PUBLIC KEY BLOCK-----\\n..."
  }
"""

from flask import Blueprint, jsonify, request
import json
import os
import time
import secrets
import hmac
import hashlib
from typing import Optional, Tuple
from utils.gpg_utils import verify_gpg_signature
import logging

admin_auth_bp = Blueprint('admin_auth', __name__)
logger = logging.getLogger(__name__)

# In-memory challenge store (username -> challenge_data)
# In production, use Redis or similar
_active_challenges = {}

# Challenge validity: 5 minutes
CHALLENGE_VALIDITY_SECONDS = 300

# Admin token validity: 24 hours
ADMIN_TOKEN_VALIDITY_SECONDS = 86400


def get_admin_gpg_keys() -> dict:
    """
    Load admin GPG public keys from environment variable.
    
    Returns:
        dict: Mapping of username to PGP public key
    """
    admin_keys_json = os.environ.get('ADMIN_GPG_KEYS', '{}')
    try:
        return json.loads(admin_keys_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ADMIN_GPG_KEYS: {e}")
        return {}


def generate_admin_token(username: str) -> str:
    """
    Generate a long-lived admin token.
    
    Token format: admin_<username>_<timestamp>_<hmac>
    
    Args:
        username: Admin username
        
    Returns:
        str: Admin token string
    """
    # Use app secret key for HMAC
    secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-me')
    timestamp = str(int(time.time()))
    
    # Create HMAC of username + timestamp
    message = f"{username}:{timestamp}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:32]
    
    return f"admin_{username}_{timestamp}_{signature}"


def verify_admin_token(token: str) -> Optional[str]:
    """
    Verify an admin token and extract username.
    
    Args:
        token: Admin token string
        
    Returns:
        Optional[str]: Username if valid, None otherwise
    """
    try:
        parts = token.split('_')
        if len(parts) != 4 or parts[0] != 'admin':
            return None
        
        _, username, timestamp, signature = parts
        
        # Check if token is expired
        token_time = int(timestamp)
        if time.time() - token_time > ADMIN_TOKEN_VALIDITY_SECONDS:
            logger.warning(f"Expired admin token for {username}")
            return None
        
        # Verify HMAC
        secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-me')
        message = f"{username}:{timestamp}"
        expected_sig = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning(f"Invalid HMAC for admin token: {username}")
            return None
        
        # Verify username is in admin list
        admin_keys = get_admin_gpg_keys()
        if username not in admin_keys:
            logger.warning(f"Token for non-admin user: {username}")
            return None
        
        return username
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Malformed admin token: {e}")
        return None


@admin_auth_bp.route('/admin/auth/challenge', methods=['POST'])
def get_challenge():
    """
    Generate an authentication challenge for admin.
    
    Request:
        {
            "username": "administrator"
        }
        
    Response:
        {
            "challenge": "nonce:timestamp",
            "expires_at": 1234567890
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    username = data.get('username')
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    # Check if username has GPG key configured
    admin_keys = get_admin_gpg_keys()
    if username not in admin_keys:
        logger.warning(f"Challenge requested for non-admin: {username}")
        return jsonify({'error': 'Admin GPG key not configured'}), 403
    
    # Generate challenge
    nonce = secrets.token_urlsafe(32)
    timestamp = int(time.time())
    challenge = f"{nonce}:{timestamp}"
    expires_at = timestamp + CHALLENGE_VALIDITY_SECONDS
    
    # Store challenge
    _active_challenges[username] = {
        'challenge': challenge,
        'expires_at': expires_at
    }
    
    logger.info(f"Generated auth challenge for {username}")
    
    return jsonify({
        'challenge': challenge,
        'expires_at': expires_at,
        'message': 'Sign this challenge with your GPG private key'
    }), 200


@admin_auth_bp.route('/admin/auth/verify', methods=['POST'])
def verify_challenge():
    """
    Verify a signed challenge and issue admin token.
    
    Request:
        {
            "username": "administrator",
            "challenge": "nonce:timestamp",
            "signature": "base64-encoded GPG signature"
        }
        
    Response:
        {
            "token": "admin_administrator_1234567890_abc123...",
            "expires_at": 1234567890,
            "username": "administrator"
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    username = data.get('username')
    challenge = data.get('challenge')
    signature = data.get('signature')
    
    if not all([username, challenge, signature]):
        return jsonify({
            'error': 'username, challenge, and signature required'
        }), 400
    
    # Check if challenge exists and is valid
    if username not in _active_challenges:
        return jsonify({'error': 'No active challenge for user'}), 400
    
    challenge_data = _active_challenges[username]
    
    # Verify challenge hasn't expired
    if time.time() > challenge_data['expires_at']:
        del _active_challenges[username]
        return jsonify({'error': 'Challenge expired'}), 400
    
    # Verify challenge matches
    if challenge != challenge_data['challenge']:
        return jsonify({'error': 'Challenge mismatch'}), 400
    
    # Get admin's public key
    admin_keys = get_admin_gpg_keys()
    public_key = admin_keys.get(username)
    
    if not public_key:
        return jsonify({'error': 'Admin GPG key not configured'}), 403
    
    # Verify GPG signature
    is_valid, error = verify_gpg_signature(challenge, signature, public_key)
    
    if not is_valid:
        logger.warning(
            f"Failed GPG signature verification for {username}: {error}"
        )
        return jsonify({
            'error': 'Invalid signature',
            'details': error
        }), 403
    
    # Clear the used challenge
    del _active_challenges[username]
    
    # Generate admin token
    token = generate_admin_token(username)
    expires_at = int(time.time()) + ADMIN_TOKEN_VALIDITY_SECONDS
    
    logger.info(f"Issued admin token for {username}")
    
    return jsonify({
        'token': token,
        'expires_at': expires_at,
        'username': username,
        'message': 'Authentication successful'
    }), 200


@admin_auth_bp.route('/admin/auth/info', methods=['GET'])
def auth_info():
    """
    Get information about admin GPG authentication.
    
    Returns configured admin usernames (not the keys themselves).
    """
    admin_keys = get_admin_gpg_keys()
    
    return jsonify({
        'authentication_method': 'GPG signature verification',
        'token_validity_hours': ADMIN_TOKEN_VALIDITY_SECONDS / 3600,
        'challenge_validity_seconds': CHALLENGE_VALIDITY_SECONDS,
        'configured_admins': list(admin_keys.keys()),
        'flow': [
            '1. POST /admin/auth/challenge with {"username": "admin"}',
            '2. Sign the returned challenge with your GPG private key',
            '3. POST /admin/auth/verify with signature',
            '4. Use returned token in X-Admin-Token header'
        ]
    }), 200
