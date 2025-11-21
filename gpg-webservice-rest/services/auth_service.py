"""
Authentication service for password hashing and user verification.

This module provides authentication-related functions including password hashing,
verification, and session key-based user lookup. It uses Argon2id for password hashing,
which is a memory-hard algorithm resistant to GPU and side-channel attacks.

DETERMINISTIC SESSION KEYS:
- Session keys are derived from: HMAC(PBKDF2(password_hash, master_salt), hour_index)
- Verification is mathematical (re-derive expected key and compare)
- Keys expire hourly with 10-minute grace period
- No session keys are stored in the database
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from typing import Optional, Tuple
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
    LEGACY: Retrieve a user by their API key hash.

    This function is deprecated for new users using deterministic session keys.
    It remains for backward compatibility with existing users who have api_key_hash.

    Args:
        api_key (str): The plaintext API key to look up

    Returns:
        Optional[User]: The User object if found, None otherwise
    """
    from utils.crypto_utils import hash_api_key
    api_key_hash = hash_api_key(api_key)
    return User.query.filter_by(api_key_hash=api_key_hash).first()


def get_user_by_username(username: str) -> Optional[User]:
    """
    Retrieve a user by their username.

    Args:
        username (str): The username to look up

    Returns:
        Optional[User]: The User object if found, None otherwise
    """
    return User.query.filter_by(username=username).first()


def verify_session_key_for_user(user: User, provided_session_key: str) -> Tuple[bool, str]:
    """
    Verify a session key for a user using deterministic derivation.

    This function re-derives the expected session key from the user's
    password_hash and master_salt, then compares it to the provided key.
    It checks both the current time window and the previous window if
    within the grace period.

    Args:
        user (User): The user object to verify against
        provided_session_key (str): The session key provided in the request

    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    from utils.crypto_utils import verify_session_key

    # Check if user uses deterministic keys
    if not user.uses_deterministic_keys:
        return False, "User does not use deterministic session keys"

    # Verify the session key
    is_valid, window_used, message = verify_session_key(
        contract_hash=user.password_hash,
        master_salt=user.master_salt,
        provided_key=provided_session_key
    )

    return is_valid, message


def authenticate_by_session_key(username: str, session_key: str) -> Tuple[Optional[User], str]:
    """
    Authenticate a user by username and session key.

    This is the primary authentication method for the deterministic session key
    system. It looks up the user by username, then verifies the session key
    by re-deriving the expected key and comparing.

    Args:
        username (str): The username to authenticate
        session_key (str): The session key (sk_...) to verify

    Returns:
        Tuple[Optional[User], str]:
            - Success: (User object, "Authenticated successfully")
            - Failure: (None, error_message)
    """
    # Look up user by username
    user = get_user_by_username(username)
    if not user:
        return None, "User not found"

    # Verify the session key
    is_valid, message = verify_session_key_for_user(user, session_key)
    if not is_valid:
        return None, message

    return user, "Authenticated successfully"


def authenticate_request(username: Optional[str], api_key: str) -> Tuple[Optional[User], str]:
    """
    Authenticate a request using either deterministic session keys or legacy API keys.

    This function provides backward compatibility by supporting both authentication
    methods. If a username is provided, it uses the new deterministic session key
    system. Otherwise, it falls back to the legacy API key hash lookup.

    Args:
        username (Optional[str]): The username (required for deterministic keys)
        api_key (str): The session key (sk_...) or legacy API key

    Returns:
        Tuple[Optional[User], str]:
            - Success: (User object, success_message)
            - Failure: (None, error_message)
    """
    # If session key format (sk_...), require username for stateless verification
    if api_key.startswith('sk_'):
        if not username:
            return None, "Username required for session key authentication"
        return authenticate_by_session_key(username, api_key)

    # Legacy: API key hash lookup (for users without deterministic keys)
    user = get_user_by_api_key(api_key)
    if user:
        return user, "Authenticated via legacy API key"

    return None, "Invalid or expired API key"
