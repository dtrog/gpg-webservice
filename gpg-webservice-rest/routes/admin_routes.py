"""Admin routes for user management."""
from flask import Blueprint, jsonify, request
from functools import wraps
from db.database import get_session
from models.user import User
import logging

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)


def require_admin(f):
    """Decorator to require admin authentication via API key."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        
        if not api_key:
            return jsonify({'error': 'Admin API key required'}), 401
        
        # Verify the API key belongs to a user
        session = get_session()
        try:
            user = session.query(User).filter_by(api_key=api_key).first()
            
            if not user:
                return jsonify({'error': 'Invalid API key'}), 403
            
            # Store username for logging
            request.admin_username = user.username
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Admin auth error: {e}")
            return jsonify({'error': 'Authentication failed'}), 500
        finally:
            session.close()
    
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
