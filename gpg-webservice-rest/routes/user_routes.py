# User-related routes
"""
User routes for registration, login, and profile management.

DETERMINISTIC SESSION KEYS:
- Registration returns a session key (sk_...) valid for 1 hour
- Login returns a fresh session key for the current time window
- Session keys are derived mathematically, not stored
- AI agents can regenerate keys by re-logging in
"""

from flask import Blueprint

user_bp = Blueprint('user', __name__)

from flask import request, jsonify
from utils.security_utils import rate_limit_auth, validate_username, validate_password, validate_email
from services.user_service import UserService
from utils.audit_logger import audit_logger, AuditEventType


@user_bp.route('/register', methods=['POST'])
@rate_limit_auth
def register():
    """
    Register a new user with deterministic session keys.

    Requires admin signature for authorization:
    - admin_signature: Base64-encoded PGP signature of the username
    - Server verifies signature against ADMIN_GPG_KEYS

    The password should be SHA256(successorship_contract + pgp_signature).
    This allows AI agents to regenerate their password from their immutable contract.

    Returns:
        - api_key: Derived session key (sk_...) valid for current hour
        - window_index: Current session window index
        - expires_at: When the session key expires
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    admin_signature = data.get('admin_signature')  # Required for authorization

    # Validate input
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if not admin_signature:
        return jsonify({'error': 'Admin signature required for registration'}), 400

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

    # Verify admin signature authorizes this username
    from routes.admin_auth_routes import get_admin_gpg_keys
    from utils.gpg_utils import verify_gpg_signature
    
    admin_keys = get_admin_gpg_keys()
    if not admin_keys:
        return jsonify({'error': 'Admin authorization not configured'}), 500
    
    # Try each admin's public key
    signature_valid = False
    authorizing_admin = None
    
    for admin_username, public_key in admin_keys.items():
        is_valid, error_msg = verify_gpg_signature(username, admin_signature, public_key)
        if is_valid:
            signature_valid = True
            authorizing_admin = admin_username
            break
    
    if not signature_valid:
        audit_logger.log_event(
            AuditEventType.REGISTRATION,
            status='failure',
            username=username,
            message=f'Registration denied for {username}: Invalid admin signature'
        )
        return jsonify({
            'error': 'Invalid admin signature',
            'hint': 'Admin must sign username with: echo "username" | gpg --armor --detach-sign'
        }), 403

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

    # Log successful registration with authorizing admin
    audit_logger.log_registration(
        user_id=registration_result.user.id,
        username=username,
        email=email
    )
    audit_logger.log_event(
        AuditEventType.REGISTRATION,
        status='success',
        user_id=registration_result.user.id,
        username=username,
        message=f'Registration authorized by admin: {authorizing_admin}'
    )

    # Safely determine the public key to return
    public_key = public_key_data
    if registration_result.pgp_keypair.public_key:
        public_key = registration_result.pgp_keypair.public_key.key_data

    # Return session key info (derived, not stored)
    session_info = registration_result.session_key_info
    return jsonify({
        'message': 'User registered with deterministic session keys',
        'user_id': registration_result.user.id,
        'username': username,
        'authorized_by': authorizing_admin,
        'api_key': session_info.api_key,  # Derived session key (sk_...)
        'session_window': session_info.window_index,
        'window_start': session_info.window_start,
        'expires_at': session_info.expires_at,
        'public_key': public_key,
        'note': 'Session key expires hourly. Use /login to get a fresh key when expired.'
    }), 201


@user_bp.route('/login', methods=['POST'])
@rate_limit_auth
def login():
    """
    Authenticate user and return a derived session key.

    The session key is deterministically derived from:
    - HMAC(PBKDF2(password_hash, master_salt), current_hour_index)

    AI agents should call this at the start of each session to get a fresh key.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user_service = UserService()
    login_result, error = user_service.login_user(username, password)

    if error:
        # Log login failure
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'Login failed for {username}: {error}'
        )
        return jsonify({'error': error}), 401

    # Log successful login
    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=login_result.user.id,
        username=username,
        message=f'User {username} logged in successfully'
    )

    # Return session key info
    session_info = login_result.session_key_info
    return jsonify({
        'message': 'Login successful',
        'user_id': login_result.user.id,
        'username': username,
        'api_key': session_info.api_key,  # Derived session key (sk_...)
        'session_window': session_info.window_index,
        'window_start': session_info.window_start,
        'expires_at': session_info.expires_at,
        'note': 'Session key valid for current hour + 10 min grace period.'
    }), 200


@user_bp.route('/register/form', methods=['POST'])
@rate_limit_auth
def register_form():
    """Form-based registration endpoint that accepts multipart/form-data
    
    Requires admin signature for authorization.
    """
    # Get form data
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    admin_signature = request.form.get('admin_signature')  # Required

    # Validate input
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if not admin_signature:
        return jsonify({'error': 'Admin signature required'}), 400

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

    # Verify admin signature
    from routes.admin_auth_routes import get_admin_gpg_keys
    from utils.gpg_utils import verify_gpg_signature
    
    admin_keys = get_admin_gpg_keys()
    if not admin_keys:
        return jsonify({'error': 'Admin authorization not configured'}), 500
    
    signature_valid = False
    authorizing_admin = None
    
    for admin_username, public_key in admin_keys.items():
        is_valid, _ = verify_gpg_signature(
            username, admin_signature, public_key
        )
        if is_valid:
            signature_valid = True
            authorizing_admin = admin_username
            break
    
    if not signature_valid:
        audit_logger.log_event(
            AuditEventType.REGISTRATION,
            status='failure',
            username=username,
            message=f'Registration denied: Invalid admin signature'
        )
        return jsonify({'error': 'Invalid admin signature'}), 403

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
    elif 'private_key_text' in request.form:
        if request.form['private_key_text']:
            private_key_data = request.form.get('private_key_text')

    # Register user
    user_service = UserService()
    registration_result, error = user_service.register_user(
        username, password, public_key_data, private_key_data
    )

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
    audit_logger.log_event(
        AuditEventType.REGISTRATION,
        status='success',
        user_id=registration_result.user.id,
        username=username,
        message=f'Registration authorized by: {authorizing_admin}'
    )

    # Safely determine the public key to return
    public_key = public_key_data
    if registration_result.pgp_keypair.public_key:
        public_key = registration_result.pgp_keypair.public_key.key_data

    # Return session key info
    session_info = registration_result.session_key_info
    return jsonify({
        'message': 'User registered successfully',
        'user_id': registration_result.user.id,
        'username': username,
        'authorized_by': authorizing_admin,
        'api_key': session_info.api_key,
        'session_window': session_info.window_index,
        'window_start': session_info.window_start,
        'expires_at': session_info.expires_at,
        'public_key': public_key,
        'note': 'Session key expires hourly. Use /login to refresh.'
    }), 201


@user_bp.route('/get_session_key', methods=['POST'])
@rate_limit_auth
def get_session_key():
    """
    Get current session key with password authentication.

    This is functionally equivalent to /login but named for clarity.
    AI agents should call this when their session key has expired.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user_service = UserService()
    login_result, error = user_service.login_user(username, password)

    if error:
        # Log session key retrieval failure
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'Session key retrieval failed for {username}: {error}'
        )
        return jsonify({'error': error}), 401

    # Log session key retrieval
    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=login_result.user.id,
        username=username,
        message=f'Session key retrieved by {username}'
    )

    session_info = login_result.session_key_info
    return jsonify({
        'message': 'Session key retrieved',
        'user_id': login_result.user.id,
        'username': username,
        'api_key': session_info.api_key,
        'session_window': session_info.window_index,
        'window_start': session_info.window_start,
        'expires_at': session_info.expires_at,
        'note': 'This session key is deterministically derived. You can get the same key by calling /login again within the same hour.'
    }), 200


# LEGACY: Keep for backward compatibility, but redirect to new system
@user_bp.route('/get_api_key', methods=['POST'])
@rate_limit_auth
def get_api_key():
    """
    LEGACY: Retrieve API key with password authentication.

    This endpoint now returns a derived session key instead of a stored API key.
    For backward compatibility, it returns the same format as before.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user_service = UserService()
    login_result, error = user_service.login_user(username, password)

    if error:
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'API key retrieval failed for {username}: {error}'
        )
        return jsonify({'error': 'Invalid credentials'}), 401

    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=login_result.user.id,
        username=username,
        message=f'Session key retrieved by {username} (via legacy endpoint)'
    )

    session_info = login_result.session_key_info
    return jsonify({
        'message': 'Session key retrieved (deterministic system)',
        'user_id': login_result.user.id,
        'username': username,
        'api_key': session_info.api_key,
        'expires_at': session_info.expires_at,
        'note': 'API keys are now deterministic session keys that expire hourly. Use /login or /get_session_key to refresh.'
    }), 200


# LEGACY: regenerate_api_key is no longer needed with deterministic keys
@user_bp.route('/regenerate_api_key', methods=['POST'])
@rate_limit_auth
def regenerate_api_key():
    """
    LEGACY: Regenerate API key.

    With deterministic session keys, this is no longer needed.
    Session keys are automatically derived from the current time window.
    Simply call /login to get a fresh session key.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user_service = UserService()
    login_result, error = user_service.login_user(username, password)

    if error:
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            status='failure',
            username=username,
            message=f'API key regeneration failed for {username}: {error}'
        )
        return jsonify({'error': 'Invalid credentials'}), 401

    audit_logger.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=login_result.user.id,
        username=username,
        message=f'Session key regenerated by {username}'
    )

    session_info = login_result.session_key_info
    return jsonify({
        'message': 'Session key generated (deterministic system)',
        'user_id': login_result.user.id,
        'username': username,
        'api_key': session_info.api_key,
        'session_window': session_info.window_index,
        'expires_at': session_info.expires_at,
        'note': 'With deterministic keys, regeneration is automatic. Simply call /login when your key expires to get a fresh one for the current hour.'
    }), 200


@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get user profile (requires session key + username authentication)"""
    from services.auth_service import authenticate_request

    raw_api_key = request.headers.get('X-API-KEY')
    username = request.headers.get('X-Username')

    if not raw_api_key:
        return jsonify({'error': 'API key required (X-API-KEY header)'}), 401

    user, message = authenticate_request(username, raw_api_key)
    if not user:
        return jsonify({'error': message}), 403

    # Get user's public key
    from models.pgp_key import PgpKey, PgpKeyType
    public_key = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PUBLIC).first()

    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'has_public_key': public_key is not None,
        'uses_deterministic_keys': user.uses_deterministic_keys,
        'master_salt_preview': f"{user.master_salt[:8]}..." if user.master_salt else None
    }), 200


@user_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update user profile (requires session key + username authentication)"""
    from services.auth_service import authenticate_request
    from db.database import db

    raw_api_key = request.headers.get('X-API-KEY')
    username = request.headers.get('X-Username')

    if not raw_api_key:
        return jsonify({'error': 'API key required (X-API-KEY header)'}), 401

    user, message = authenticate_request(username, raw_api_key)
    if not user:
        return jsonify({'error': message}), 403

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
        'email': getattr(user, 'email', '') or ''
    }), 200


@user_bp.route('/keys/download', methods=['GET'])
def download_keys():
    """Download user's PGP keys"""
    from services.auth_service import authenticate_request
    from models.pgp_key import PgpKey, PgpKeyType
    from flask import make_response

    raw_api_key = request.headers.get('X-API-KEY')
    username = request.headers.get('X-Username')

    if not raw_api_key:
        return jsonify({'error': 'API key required (X-API-KEY header)'}), 401

    user, message = authenticate_request(username, raw_api_key)
    if not user:
        return jsonify({'error': message}), 403

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
    from services.auth_service import authenticate_request
    from models.pgp_key import PgpKey, PgpKeyType
    from db.database import db
    from utils.crypto_utils import encrypt_private_key, derive_gpg_passphrase

    raw_api_key = request.headers.get('X-API-KEY')
    username_header = request.headers.get('X-Username')

    if not raw_api_key:
        return jsonify({'error': 'API key required (X-API-KEY header)'}), 401

    user, message = authenticate_request(username_header, raw_api_key)
    if not user:
        return jsonify({'error': message}), 403

    # Require password confirmation for security
    password = request.form.get('password')
    if not password:
        return jsonify({'error': 'Password confirmation required'}), 400

    # Verify password
    user_service = UserService()
    verified_result, error = user_service.login_user(user.username, password)
    if error:
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
            encrypted_private_key = encrypt_private_key(private_key_data.encode(), gpg_passphrase)

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
