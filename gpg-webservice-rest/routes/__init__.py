"""
Routes package for GPG webservice.
This module organizes and imports all route handlers for the Flask application.
"""

from flask import Blueprint

# Create a main blueprint for all routes
main_bp = Blueprint('main', __name__)

# Import route handlers (these would be in separate modules)
try:
    from . import auth_routes
    from . import crypto_routes
    from . import user_routes
except ImportError:
    # Routes modules don't exist yet, will need to be created
    pass

# Make the blueprint available for import
__all__ = ['main_bp']
