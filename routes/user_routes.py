# User-related routes

from flask import Blueprint

user_bp = Blueprint('user', __name__)

from flask import request, jsonify


from services.user_service import UserService
from services.auth_service import hash_password, verify_password, get_user_by_api_key

@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
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
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user_service = UserService()
    user, pgp_keypair_or_error = user_service.login_user(username, password)
    if not user:
        return jsonify({'error': pgp_keypair_or_error}), 401
    return jsonify({
        'message': 'Login successful', 
        'user_id': getattr(user, 'id', None),
        'api_key': getattr(user, 'api_key', None)
    }), 200
