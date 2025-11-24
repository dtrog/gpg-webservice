"""Admin routes for user management."""
from flask import Blueprint, jsonify, request
from functools import wraps
from db.database import get_session
from models.user import User
from services.auth_service import authenticate_request
from routes.admin_auth_routes import verify_admin_token
import logging
import os

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

# Get admin usernames from environment variable (comma-separated)
# Example: ADMIN_USERNAMES="alice,bob,administrator"
ADMIN_USERNAMES = set(
    username.strip() 
    for username in os.environ.get('ADMIN_USERNAMES', '').split(',') 
    if username.strip()
)

def require_admin(f):
    """
    Decorator to require admin authentication.
    
    Supports two authentication methods:
    1. Admin Token (X-Admin-Token): GPG-signed, 24h validity, no expiration
    2. Session Key (X-API-KEY + X-Username): For AI agents, 1h expiration
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try admin token first (GPG-based, non-expiring)
        admin_token = request.headers.get('X-Admin-Token')
        if admin_token:
            username = verify_admin_token(admin_token)
            if username:
                request.admin_username = username
                logger.info(f"Admin {username} authenticated via GPG token")
                return f(*args, **kwargs)
            else:
                return jsonify({
                    'error': 'Invalid or expired admin token'
                }), 403
        
        # Fall back to session key authentication (for AI agents)
        api_key = request.headers.get('X-API-KEY')
        username_header = request.headers.get('X-Username')
        
        if not api_key:
            return jsonify({
                'error': 'Authentication required',
                'hint': 'Use X-Admin-Token (GPG) or X-API-KEY (session)'
            }), 401
        
        # Authenticate with session key
        user, message = authenticate_request(username_header, api_key)
        
        if not user:
            return jsonify({'error': message}), 403
        
        # Check if user is an admin
        if not ADMIN_USERNAMES:
            logger.warning(
                "No admin usernames configured. "
                "Set ADMIN_USERNAMES environment variable."
            )
            return jsonify({
                'error': 'Admin access not configured'
            }), 403
        
        if user.username not in ADMIN_USERNAMES:
            logger.warning(
                f"User {user.username} attempted admin action "
                f"but is not in admin list"
            )
            return jsonify({
                'error': 'Admin access required'
            }), 403
        
        # Store username for logging
        request.admin_username = user.username
        logger.info(
            f"Admin {user.username} authenticated via session key"
        )
        return f(*args, **kwargs)
    
    return decorated_function


@admin_bp.route('/admin/users', methods=['GET'])
def list_users():
    """List all users (no auth required for basic listing)."""
    try:
        session = get_session()
        
        users = session.query(User).order_by(User.id.desc()).all()
        
        user_list = []
        for user in users:
            user_list.append({
                'username': user.username,
                'email': None,  # User model doesn't have email field
                'created_at': None  # User model doesn't have timestamp
            })
        
        session.close()
        
        return jsonify({'users': user_list}), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/users/<username>', methods=['DELETE'])
@require_admin
def delete_user(username):
    """Delete a user and all associated data."""
    try:
        admin_user = request.admin_username
        logger.info(f"Admin {admin_user} deleting user: {username}")
        
        session = get_session()
        
        # Find user
        user = session.query(User).filter_by(username=username).first()
        
        if not user:
            session.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Delete user (cascade will handle related records)
        session.delete(user)
        session.commit()
        session.close()
        
        logger.info(f"Admin {admin_user} deleted user: {username}")
        return jsonify({
            'message': f'User {username} deleted successfully',
            'deleted_by': admin_user
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting user {username}: {e}")
        return jsonify({'error': str(e)}), 500
