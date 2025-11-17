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
