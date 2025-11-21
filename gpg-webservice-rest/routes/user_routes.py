# User-related routes

from flask import Blueprint

user_bp = Blueprint('user', __name__)

from flask import request, jsonify
from utils.security_utils import rate_limit_auth, validate_username, validate_password, validate_email
from services.user_service import UserService
from utils.audit_logger import audit_logger, AuditEventType

@user_bp.route('/register', methods=['POST'])
@rate_limit_auth
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
        
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    # Validate input
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    valid, error = validate_username(username)
    if not valid:
        return jsonify({'error': error}), 400
    
    valid, error = validate_password(password)
    if not valid:
        return jsonify({'error': error}), 400
    
    if email:
        valid, error = validate_email(email)
        if not valid:
            return jsonify({'error': error}), 400
    public_key_data = data.get('public_key')  # Optional
    private_key_data = data.get('private_key')  # Optional
    user_service = UserService()
    registration_result, error = user_service.register_user(username, password, public_key_data, private_key_data)
    if error:
        # Log registration failure
        audit_logger.log_event(
            AuditEventType.REGISTRATION,
            status='failure',
            username=username,
            message=f'Registration failed for {username}: {error}'
        )
        return jsonify({'error': error}), 400

    # Log successful registration
    audit_logger.log_registration(
        user_id=registration_result.user.id,
        username=username,
        email=email
    )

    # Safely determine the public key to return
    public_key = public_key_data
    if registration_result.pgp_keypair.public_key:
        public_key = registration_result.pgp_keypair.public_key.key_data

    return jsonify({
        'message': 'User registered',
        'user_id': registration_result.user.id,
        'api_key': registration_result.api_key,  # Raw API key - only returned once!
        'public_key': public_key
    }), 201

@user_bp.route('/login', methods=['POST'])
@rate_limit_auth
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user_service = UserService()
    user, pgp_keypair_or_error = user_service.login_user(username, password)
    if not user:
        # Log login failure
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'Login failed for {username}'
        )
        return jsonify({'error': pgp_keypair_or_error}), 401

    # Log successful login
    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user.id,
        username=username,
        message=f'User {username} logged in successfully'
    )

    return jsonify({
        'message': 'Login successful',
        'user_id': user.id
        # Note: API key is NOT returned on login (only at registration)
    }), 200

@user_bp.route('/register/form', methods=['POST'])
@rate_limit_auth
def register_form():
    """Form-based registration endpoint that accepts multipart/form-data"""
    from werkzeug.utils import secure_filename
    import tempfile
    import os

    # Get form data
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')

    # Validate input
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    valid, error = validate_username(username)
    if not valid:
        return jsonify({'error': error}), 400

    valid, error = validate_password(password)
    if not valid:
        return jsonify({'error': error}), 400

    if email:
        valid, error = validate_email(email)
        if not valid:
            return jsonify({'error': error}), 400

    # Handle optional PGP key uploads
    public_key_data = None
    private_key_data = None

    # Check if keys are uploaded as files
    if 'public_key_file' in request.files:
        public_key_file = request.files['public_key_file']
        if public_key_file.filename:
            public_key_data = public_key_file.read().decode('utf-8')
    elif 'public_key_text' in request.form and request.form['public_key_text']:
        # Or provided as text
        public_key_data = request.form.get('public_key_text')

    if 'private_key_file' in request.files:
        private_key_file = request.files['private_key_file']
        if private_key_file.filename:
            private_key_data = private_key_file.read().decode('utf-8')
    elif 'private_key_text' in request.form and request.form['private_key_text']:
        private_key_data = request.form.get('private_key_text')

    # Register user
    user_service = UserService()
    registration_result, error = user_service.register_user(username, password, public_key_data, private_key_data)

    if error:
        # Log registration failure
        audit_logger.log_event(
            AuditEventType.REGISTRATION,
            status='failure',
            username=username,
            message=f'Registration failed for {username}: {error}'
        )
        return jsonify({'error': error}), 400

    # Log successful registration
    audit_logger.log_registration(
        user_id=registration_result.user.id,
        username=username,
        email=email
    )

    # Safely determine the public key to return
    public_key = public_key_data
    if registration_result.pgp_keypair.public_key:
        public_key = registration_result.pgp_keypair.public_key.key_data

    return jsonify({
        'message': 'User registered successfully',
        'user_id': registration_result.user.id,
        'api_key': registration_result.api_key,  # Raw API key - only returned once!
        'public_key': public_key
    }), 201

@user_bp.route('/get_api_key', methods=['POST'])
@rate_limit_auth
def get_api_key():
    """Retrieve API key with password authentication"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user_service = UserService()
    user, pgp_keypair_or_error = user_service.login_user(username, password)
    if not user:
        # Log API key retrieval failure
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'API key retrieval failed for {username}'
        )
        return jsonify({'error': 'Invalid credentials'}), 401

    # Log API key retrieval
    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user.id,
        username=username,
        message=f'API key retrieved by {username}'
    )

    # Return a masked version of the API key hash for security
    masked_key = f"{user.api_key_hash[:8]}...{user.api_key_hash[-4:]}"

    return jsonify({
        'message': 'API key retrieved',
        'user_id': user.id,
        'username': username,
        'api_key_masked': masked_key,
        'note': 'For security reasons, the full API key cannot be retrieved. It was only shown once during registration. Use /regenerate_api_key to generate a new one.'
    }), 200

@user_bp.route('/regenerate_api_key', methods=['POST'])
@rate_limit_auth
def regenerate_api_key():
    """Regenerate API key with password authentication (for AI agents that lost their key)"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # Authenticate user
    user_service = UserService()
    user, pgp_keypair_or_error = user_service.login_user(username, password)
    if not user:
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'API key regeneration failed for {username}: invalid credentials'
        )
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate new API key
    import secrets
    import hashlib
    from db.database import db, session_scope

    new_api_key = secrets.token_urlsafe(32)
    new_api_key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()

    # Update user's API key hash
    try:
        with session_scope() as session:
            from models.user import User
            db_user = session.query(User).filter_by(id=user.id).first()
            if db_user:
                db_user.api_key_hash = new_api_key_hash
                session.commit()

        # Log successful API key regeneration
        audit_logger.log_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user.id,
            username=username,
            message=f'API key regenerated by {username}'
        )

        return jsonify({
            'message': 'API key regenerated successfully',
            'user_id': user.id,
            'username': username,
            'api_key': new_api_key,
            'warning': 'This is your new API key. The old one is now invalid. Save it securely - it will only be shown once.'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to regenerate API key: {str(e)}'}), 500

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get user profile (requires API key authentication)"""
    from services.auth_service import get_user_by_api_key

    raw_api_key = request.headers.get('X-API-KEY')
    if not raw_api_key:
        return jsonify({'error': 'API key required'}), 401

    user = get_user_by_api_key(raw_api_key)
    if not user:
        return jsonify({'error': 'Invalid API key'}), 403

    # Get user's public key
    from models.pgp_key import PgpKey, PgpKeyType
    public_key = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PUBLIC).first()

    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'has_public_key': public_key is not None,
        'api_key_masked': f"{user.api_key_hash[:8]}...{user.api_key_hash[-4:]}"
    }), 200

@user_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update user profile (requires API key authentication)"""
    from services.auth_service import get_user_by_api_key
    from db.database import db

    raw_api_key = request.headers.get('X-API-KEY')
    if not raw_api_key:
        return jsonify({'error': 'API key required'}), 401

    user = get_user_by_api_key(raw_api_key)
    if not user:
        return jsonify({'error': 'Invalid API key'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    # Update email if provided
    if 'email' in data:
        email = data['email']
        if email:
            valid, error = validate_email(email)
            if not valid:
                return jsonify({'error': error}), 400
            user.email = email
        else:
            user.email = None

    db.session.commit()

    # Log profile update
    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user.id,
        username=user.username,
        message=f'Profile updated for {user.username}'
    )

    return jsonify({
        'message': 'Profile updated successfully',
        'user_id': user.id,
        'username': user.username,
        'email': user.email or ''
    }), 200

@user_bp.route('/keys/download', methods=['GET'])
def download_keys():
    """Download user's PGP keys"""
    from services.auth_service import get_user_by_api_key
    from models.pgp_key import PgpKey, PgpKeyType
    from flask import make_response

    raw_api_key = request.headers.get('X-API-KEY')
    if not raw_api_key:
        return jsonify({'error': 'API key required'}), 401

    user = get_user_by_api_key(raw_api_key)
    if not user:
        return jsonify({'error': 'Invalid API key'}), 403

    key_type = request.args.get('type', 'public')

    if key_type == 'public':
        key = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PUBLIC).first()
        filename = f'{user.username}_public.asc'
    elif key_type == 'private':
        key = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
        filename = f'{user.username}_private.asc'
    else:
        return jsonify({'error': 'Invalid key type. Use "public" or "private"'}), 400

    if not key:
        return jsonify({'error': f'{key_type.capitalize()} key not found'}), 404

    response = make_response(key.key_data)
    response.headers['Content-Type'] = 'application/pgp-keys'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'

    return response

@user_bp.route('/keys/upload', methods=['POST'])
def upload_keys():
    """Upload user's PGP keys (requires password confirmation)"""
    from services.auth_service import get_user_by_api_key
    from models.pgp_key import PgpKey, PgpKeyType
    from db.database import db
    from utils.crypto_utils import encrypt_private_key, derive_gpg_passphrase

    raw_api_key = request.headers.get('X-API-KEY')
    if not raw_api_key:
        return jsonify({'error': 'API key required'}), 401

    user = get_user_by_api_key(raw_api_key)
    if not user:
        return jsonify({'error': 'Invalid API key'}), 403

    # Require password confirmation for security
    password = request.form.get('password')
    if not password:
        return jsonify({'error': 'Password confirmation required'}), 400

    # Verify password
    user_service = UserService()
    verified_user, error = user_service.login_user(user.username, password)
    if not verified_user:
        return jsonify({'error': 'Invalid password'}), 401

    # Handle key uploads
    updated_keys = []

    if 'public_key_file' in request.files:
        public_key_file = request.files['public_key_file']
        if public_key_file.filename:
            public_key_data = public_key_file.read().decode('utf-8')

            # Update or create public key
            public_key = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PUBLIC).first()
            if public_key:
                public_key.key_data = public_key_data
            else:
                public_key = PgpKey(user_id=user.id, key_type=PgpKeyType.PUBLIC, key_data=public_key_data)
                db.session.add(public_key)
            updated_keys.append('public')

    if 'private_key_file' in request.files:
        private_key_file = request.files['private_key_file']
        if private_key_file.filename:
            private_key_data = private_key_file.read().decode('utf-8')

            # Encrypt private key before storing
            gpg_passphrase = derive_gpg_passphrase(raw_api_key, user.id)
            encrypted_private_key = encrypt_private_key(private_key_data, gpg_passphrase)

            # Update or create private key
            private_key = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
            if private_key:
                private_key.key_data = encrypted_private_key
            else:
                private_key = PgpKey(user_id=user.id, key_type=PgpKeyType.PRIVATE, key_data=encrypted_private_key)
                db.session.add(private_key)
            updated_keys.append('private')

    if not updated_keys:
        return jsonify({'error': 'No keys provided'}), 400

    db.session.commit()

    # Log key upload
    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user.id,
        username=user.username,
        message=f'Keys uploaded for {user.username}: {", ".join(updated_keys)}'
    )

    return jsonify({
        'message': 'Keys uploaded successfully',
        'updated_keys': updated_keys
    }), 200
