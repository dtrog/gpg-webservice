"""
Authentication service for password hashing and user verification.

This module provides authentication-related functions including password hashing,
verification, and API key-based user lookup. It uses Argon2id for password hashing,
which is a memory-hard algorithm resistant to GPU and side-channel attacks.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from typing import Optional
from models.user import User

# Initialize Argon2 password hasher with secure defaults
_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    This function uses the Argon2id algorithm, which is the winner of the Password
    Hashing Competition and recommended by OWASP for password storage. It provides
    resistance to both GPU cracking attacks and side-channel attacks.

    Args:
        password (str): The plain text password to hash

    Returns:
        str: The Argon2id hash of the password (includes salt and parameters)
    """
    return _ph.hash(password)


def verify_password(password: str, hash_: str) -> bool:
    """
    Verify a password against its stored Argon2id hash.

    This function also handles automatic rehashing if the password hash
    uses outdated parameters (though we don't implement rehashing here).

    Args:
        password (str): The plain text password to verify
        hash_ (str): The stored Argon2id password hash to compare against

    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    try:
        _ph.verify(hash_, password)
        return True
    except (VerifyMismatchError, InvalidHash):
        return False


def get_user_by_api_key(api_key: str) -> Optional[User]:
    """
    Retrieve a user by their API key.

    This function hashes the provided API key and looks up the user by the hash.
    This is used for API key-based authentication to identify which user is
    making a request.

    Args:
        api_key (str): The plaintext API key to look up

    Returns:
        Optional[User]: The User object if found, None otherwise
    """
    from utils.crypto_utils import hash_api_key
    api_key_hash = hash_api_key(api_key)
    return User.query.filter_by(api_key_hash=api_key_hash).first()
