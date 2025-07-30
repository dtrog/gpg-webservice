# User-related routes

from flask import Blueprint

user_bp = Blueprint('user', __name__)

from flask import request, jsonify
from utils.security_utils import rate_limit_auth, validate_username, validate_password, validate_email
from services.user_service import UserService

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
    user, pgp_keypair_or_error = user_service.register_user(username, password, public_key_data, private_key_data)
    if not user:
        return jsonify({'error': pgp_keypair_or_error}), 400
    # Safely determine the public key to return
    public_key = public_key_data
    if not isinstance(pgp_keypair_or_error, str) and hasattr(pgp_keypair_or_error, 'public_key') and pgp_keypair_or_error.public_key is not None:
        public_key = pgp_keypair_or_error.public_key.key_data
        
    return jsonify({
        'message': 'User registered', 
        'user_id': getattr(user, 'id', None), 
        'api_key': getattr(user, 'api_key', None),
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
        return jsonify({'error': pgp_keypair_or_error}), 401
    return jsonify({
        'message': 'Login successful', 
        'user_id': getattr(user, 'id', None),
        'api_key': getattr(user, 'api_key', None)
    }), 200
