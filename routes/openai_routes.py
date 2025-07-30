"""
OpenAI Function Calling Integration Routes

This module provides endpoints designed to work with OpenAI's function calling feature.
These endpoints accept structured JSON inputs and return structured JSON outputs
that are compatible with OpenAI's function calling system.
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from typing import Dict, Any, Optional, Tuple
import base64
import tempfile
import os
from werkzeug.utils import secure_filename

from services.auth_service import get_user_by_api_key
from services.user_service import UserService
from utils.gpg_file_utils import sign_file, verify_signature_file, encrypt_file, decrypt_file
from utils.security_utils import rate_limit_api, validate_file_upload
from utils.crypto_utils import derive_gpg_passphrase
from models.pgp_key import PgpKey, PgpKeyType

# Create blueprint for OpenAI function calling endpoints
openai_bp = Blueprint('openai', __name__, url_prefix='/openai')

def require_api_key_json(f):
    """
    Decorator for API key authentication that returns JSON responses
    suitable for OpenAI function calling.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key required',
                'error_code': 'AUTH_REQUIRED'
            }), 401
            
        user = get_user_by_api_key(api_key)
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'error_code': 'AUTH_INVALID'
            }), 403
            
        return f(user, *args, **kwargs)
    return decorated_function

@openai_bp.route('/register_user', methods=['POST'])
@rate_limit_api
def register_user_function():
    """
    OpenAI Function: Register a new user with GPG key generation.
    
    Expected input format:
    {
        "username": "string",
        "password": "string", 
        "email": "string"
    }
    
    Returns structured response suitable for OpenAI function calling.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required',
                'error_code': 'INVALID_INPUT'
            }), 400
            
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not all([username, password, email]):
            return jsonify({
                'success': False,
                'error': 'username, password, and email are required',
                'error_code': 'MISSING_FIELDS'
            }), 400
            
        user_service = UserService()
        success, result = user_service.register_user(username, password, email)
        
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'user_id': result['user_id'],
                    'username': result['username'],
                    'api_key': result['api_key'],
                    'public_key': result['public_key']
                },
                'message': 'User registered successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result,
                'error_code': 'REGISTRATION_FAILED'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@openai_bp.route('/sign_text', methods=['POST'])
@require_api_key_json
@rate_limit_api
def sign_text_function(user):
    """
    OpenAI Function: Sign text content using user's private key.
    
    Expected input format:
    {
        "text": "string content to sign"
    }
    
    Returns base64-encoded signature.
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'text field is required',
                'error_code': 'MISSING_TEXT'
            }), 400
            
        text_content = data['text']
        if not isinstance(text_content, str):
            return jsonify({
                'success': False,
                'error': 'text must be a string',
                'error_code': 'INVALID_TEXT_TYPE'
            }), 400
            
        # Get user's private key
        private_key = PgpKey.query.filter_by(
            user_id=user.id, 
            key_type=PgpKeyType.PRIVATE
        ).first()
        
        if not private_key:
            return jsonify({
                'success': False,
                'error': 'Private key not found',
                'error_code': 'KEY_NOT_FOUND'
            }), 404
            
        # Create temporary file with text content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(text_content)
            temp_file_path = temp_file.name
            
        try:
            # Create signature file path
            signature_path = temp_file_path + '.sig'
            
            # Sign the file
            sign_file(temp_file_path, private_key.key_data, signature_path, 
                     derive_gpg_passphrase(user.api_key, user.id))
            
            # Read signature and encode as base64
            with open(signature_path, 'rb') as sig_file:
                signature_data = sig_file.read()
                signature_b64 = base64.b64encode(signature_data).decode('utf-8')
                
            return jsonify({
                'success': True,
                'data': {
                    'signature': signature_b64,
                    'text_signed': text_content,
                    'signature_format': 'base64'
                },
                'message': 'Text signed successfully'
            })
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if 'signature_path' in locals() and os.path.exists(signature_path):
                os.unlink(signature_path)
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Signing failed: {str(e)}',
            'error_code': 'SIGNING_FAILED'
        }), 500

@openai_bp.route('/verify_text_signature', methods=['POST'])
@require_api_key_json
@rate_limit_api
def verify_text_signature_function(user):
    """
    OpenAI Function: Verify a text signature against a public key.
    
    Expected input format:
    {
        "text": "original text content",
        "signature": "base64-encoded signature",
        "public_key": "ASCII-armored public key"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required',
                'error_code': 'INVALID_INPUT'
            }), 400
            
        text_content = data.get('text')
        signature_b64 = data.get('signature')
        public_key = data.get('public_key')
        
        if not all([text_content, signature_b64, public_key]):
            return jsonify({
                'success': False,
                'error': 'text, signature, and public_key are required',
                'error_code': 'MISSING_FIELDS'
            }), 400
            
        # Decode base64 signature
        try:
            signature_data = base64.b64decode(signature_b64)
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid base64 signature',
                'error_code': 'INVALID_SIGNATURE_FORMAT'
            }), 400
            
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as text_file:
            text_file.write(text_content)
            text_file_path = text_file.name
            
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sig') as sig_file:
            sig_file.write(signature_data)
            sig_file_path = sig_file.name
            
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.asc') as key_file:
            key_file.write(public_key)
            key_file_path = key_file.name
            
        try:
            # Verify signature
            is_valid = verify_signature_file(text_file_path, sig_file_path, key_file_path)
            
            return jsonify({
                'success': True,
                'data': {
                    'verified': is_valid,
                    'text_verified': text_content,
                    'signature_valid': is_valid
                },
                'message': f'Signature verification {"successful" if is_valid else "failed"}'
            })
            
        finally:
            # Clean up temporary files
            for temp_path in [text_file_path, sig_file_path, key_file_path]:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Verification failed: {str(e)}',
            'error_code': 'VERIFICATION_FAILED'
        }), 500

@openai_bp.route('/encrypt_text', methods=['POST'])
@require_api_key_json
@rate_limit_api
def encrypt_text_function(user):
    """
    OpenAI Function: Encrypt text for a recipient using their public key.
    
    Expected input format:
    {
        "text": "text content to encrypt",
        "recipient_public_key": "ASCII-armored public key of recipient"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required',
                'error_code': 'INVALID_INPUT'
            }), 400
            
        text_content = data.get('text')
        recipient_key = data.get('recipient_public_key')
        
        if not all([text_content, recipient_key]):
            return jsonify({
                'success': False,
                'error': 'text and recipient_public_key are required',
                'error_code': 'MISSING_FIELDS'
            }), 400
            
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as text_file:
            text_file.write(text_content)
            text_file_path = text_file.name
            
        try:
            # Create encrypted file path
            encrypted_file_path = text_file_path + '.gpg'
            
            # Encrypt the file (encrypt_file expects public key content, not file path)
            encrypt_file(text_file_path, recipient_key, encrypted_file_path)
            
            # Read encrypted data and encode as base64
            with open(encrypted_file_path, 'rb') as enc_file:
                encrypted_data = enc_file.read()
                encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
                
            return jsonify({
                'success': True,
                'data': {
                    'encrypted_text': encrypted_b64,
                    'original_text_length': len(text_content),
                    'format': 'base64'
                },
                'message': 'Text encrypted successfully'
            })
            
        finally:
            # Clean up temporary files
            if os.path.exists(text_file_path):
                os.unlink(text_file_path)
            if 'encrypted_file_path' in locals() and os.path.exists(encrypted_file_path):
                os.unlink(encrypted_file_path)
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Encryption failed: {str(e)}',
            'error_code': 'ENCRYPTION_FAILED'
        }), 500

@openai_bp.route('/decrypt_text', methods=['POST'])
@require_api_key_json
@rate_limit_api
def decrypt_text_function(user):
    """
    OpenAI Function: Decrypt text using user's private key.
    
    Expected input format:
    {
        "encrypted_text": "base64-encoded encrypted content"
    }
    """
    try:
        data = request.get_json()
        if not data or 'encrypted_text' not in data:
            return jsonify({
                'success': False,
                'error': 'encrypted_text field is required',
                'error_code': 'MISSING_ENCRYPTED_TEXT'
            }), 400
            
        encrypted_b64 = data['encrypted_text']
        
        # Decode base64 encrypted content
        try:
            encrypted_data = base64.b64decode(encrypted_b64)
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid base64 encrypted content',
                'error_code': 'INVALID_ENCRYPTED_FORMAT'
            }), 400
            
        # Get user's private key
        private_key = PgpKey.query.filter_by(
            user_id=user.id,
            key_type=PgpKeyType.PRIVATE
        ).first()
        
        if not private_key:
            return jsonify({
                'success': False,
                'error': 'Private key not found',
                'error_code': 'KEY_NOT_FOUND'
            }), 404
            
        # Create temporary file with encrypted content
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.gpg') as enc_file:
            enc_file.write(encrypted_data)
            enc_file_path = enc_file.name
            
        try:
            # Create decrypted file path
            decrypted_file_path = enc_file_path + '.dec'
            
            # Decrypt the file
            decrypt_file(enc_file_path, private_key.key_data, decrypted_file_path, 
                        derive_gpg_passphrase(user.api_key, user.id))
            
            # Read decrypted content
            with open(decrypted_file_path, 'r', encoding='utf-8') as dec_file:
                decrypted_text = dec_file.read()
                
            return jsonify({
                'success': True,
                'data': {
                    'decrypted_text': decrypted_text,
                    'text_length': len(decrypted_text)
                },
                'message': 'Text decrypted successfully'
            })
            
        finally:
            # Clean up temporary files
            if os.path.exists(enc_file_path):
                os.unlink(enc_file_path)
            if 'decrypted_file_path' in locals() and os.path.exists(decrypted_file_path):
                os.unlink(decrypted_file_path)
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Decryption failed: {str(e)}',
            'error_code': 'DECRYPTION_FAILED'
        }), 500

@openai_bp.route('/get_user_public_key', methods=['POST'])
@require_api_key_json
@rate_limit_api
def get_user_public_key_function(user):
    """
    OpenAI Function: Get the authenticated user's public key.
    
    No input parameters required (uses API key for authentication).
    """
    try:
        public_key = PgpKey.query.filter_by(
            user_id=user.id,
            key_type=PgpKeyType.PUBLIC
        ).first()
        
        if not public_key:
            return jsonify({
                'success': False,
                'error': 'Public key not found',
                'error_code': 'KEY_NOT_FOUND'
            }), 404
            
        return jsonify({
            'success': True,
            'data': {
                'public_key': public_key.key_data,
                'username': user.username,
                'key_format': 'ASCII-armored'
            },
            'message': 'Public key retrieved successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve public key: {str(e)}',
            'error_code': 'RETRIEVAL_FAILED'
        }), 500

@openai_bp.route('/function_definitions', methods=['GET'])
def get_function_definitions():
    """
    OpenAI Function: Get function definitions for all available GPG functions.
    
    This endpoint returns the OpenAI function calling schema definitions
    for all available GPG operations.
    """
    functions = [
        {
            "name": "register_user",
            "description": "Register a new user account with automatic GPG key generation",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username (3-50 chars, alphanumeric + underscore/hyphen)",
                        "minLength": 3,
                        "maxLength": 50
                    },
                    "password": {
                        "type": "string",
                        "description": "Strong password (8+ chars, uppercase, lowercase, digit, special char)",
                        "minLength": 8
                    },
                    "email": {
                        "type": "string",
                        "description": "Valid email address",
                        "format": "email"
                    }
                },
                "required": ["username", "password", "email"]
            }
        },
        {
            "name": "sign_text",
            "description": "Sign text content using the user's private GPG key",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text content to sign"
                    }
                },
                "required": ["text"]
            }
        },
        {
            "name": "verify_text_signature",
            "description": "Verify a text signature against a public key",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Original text content that was signed"
                    },
                    "signature": {
                        "type": "string",
                        "description": "Base64-encoded signature"
                    },
                    "public_key": {
                        "type": "string",
                        "description": "ASCII-armored public key for verification"
                    }
                },
                "required": ["text", "signature", "public_key"]
            }
        },
        {
            "name": "encrypt_text",
            "description": "Encrypt text content for a recipient using their public key",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text content to encrypt"
                    },
                    "recipient_public_key": {
                        "type": "string",
                        "description": "ASCII-armored public key of the recipient"
                    }
                },
                "required": ["text", "recipient_public_key"]
            }
        },
        {
            "name": "decrypt_text",
            "description": "Decrypt text content using the user's private key",
            "parameters": {
                "type": "object",
                "properties": {
                    "encrypted_text": {
                        "type": "string",
                        "description": "Base64-encoded encrypted content"
                    }
                },
                "required": ["encrypted_text"]
            }
        },
        {
            "name": "get_user_public_key",
            "description": "Get the authenticated user's public GPG key",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'functions': functions,
            'base_url': request.host_url + 'openai/',
            'authentication': 'API key required via X-API-KEY header',
            'rate_limits': {
                'api_endpoints': '30 requests per minute per IP'
            }
        },
        'message': 'Function definitions retrieved successfully'
    })