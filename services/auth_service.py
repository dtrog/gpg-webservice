"""
Authentication service for password hashing and user verification.

This module provides authentication-related functions including password hashing,
verification, and API key-based user lookup. It uses SHA256 for password hashing
(note: in production, consider using more secure algorithms like Argon2id).
"""

import hashlib
from typing import Optional
from models.user import User


def hash_password(password: str) -> str:
    """
    Hash a password using SHA256.
    
    Note: This is a simplified implementation for demonstration purposes.
    In production, use a more secure algorithm like Argon2id with salt.
    
    Args:
        password (str): The plain text password to hash
        
    Returns:
        str: The SHA256 hash of the password as a hexadecimal string
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hash_: str) -> bool:
    """
    Verify a password against its stored hash.
    
    Args:
        password (str): The plain text password to verify
        hash_ (str): The stored password hash to compare against
        
    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    return hash_password(password) == hash_


def get_user_by_api_key(api_key: str) -> Optional[User]:
    """
    Retrieve a user by their API key.
    
    This function is used for API key-based authentication to identify
    which user is making a request.
    
    Args:
        api_key (str): The API key to look up
        
    Returns:
        Optional[User]: The User object if found, None otherwise
    """
    return User.query.filter_by(api_key=api_key).first()
