"""
Services package for GPG webservice.

This package contains service modules for handling GPG operations,
user authentication, and other business logic.
"""

# Import service modules when they exist
try:
    from . import auth_service
except ImportError:
    auth_service = None

try:
    from . import user_service
except ImportError:
    user_service = None

# Define what gets exported from the package
__all__ = []

# Add available services to __all__
if auth_service:
    __all__.append('auth_service')
if user_service:
    __all__.append('user_service')

__version__ = '1.0.0'
