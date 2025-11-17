"""
User service for user-related business logic.

This module provides the UserService class which handles user registration,
authentication, and user data management. It coordinates between the database
models, authentication system, and GPG key generation.
"""

import hashlib
from typing import Optional, Tuple, Union, NamedTuple
from models.user import User
from models.pgp_key import PublicPgpKey, PrivatePgpKey, PgpKey
from db.database import get_session
from db.session_manager import session_scope
from services.auth_service import hash_password, verify_password
from utils.crypto_utils import generate_api_key, hash_api_key, derive_gpg_passphrase


class PgpKeyPair(NamedTuple):
    """Named tuple for holding a public/private key pair."""
    public_key: Optional[PublicPgpKey]
    private_key: Optional[PrivatePgpKey]


class UserRegistrationResult(NamedTuple):
    """Named tuple for holding user registration result including raw API key."""
    user: 'User'
    api_key: str  # Raw API key (only returned once at registration)
    pgp_keypair: PgpKeyPair


# Deprecated: Use derive_gpg_passphrase from crypto_utils instead
def api_key_to_gpg_passphrase(api_key: str) -> str:
    """
    Convert API key to a suitable GPG passphrase using SHA256 hash.
    
    This function creates a deterministic, secure passphrase for GPG operations
    by hashing the user's API key. The resulting hash is safe to use as a GPG
    passphrase without special character issues.
    
    Args:
        api_key (str): The user's API key
        
    Returns:
        str: A 64-character hexadecimal string suitable for use as a GPG passphrase
    """
    import warnings
    warnings.warn("api_key_to_gpg_passphrase is deprecated, use derive_gpg_passphrase from crypto_utils", DeprecationWarning)
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


class UserService:
    """
    Service class for user-related operations.
    
    This service handles user registration, authentication, and user data retrieval.
    It manages the coordination between user accounts and their associated PGP keys,
    ensuring proper key generation and secure storage.
    
    Methods:
        register_user: Create a new user account with PGP keys
        login_user: Authenticate a user and return their data
    """
    def register_user(
        self,
        username: str,
        password: str,
        public_key_data: Optional[str] = None,
        private_key_data: Optional[str] = None
    ) -> Tuple[Optional[User], Union[str, 'PgpKeyPair']]:
        """
        Register a new user account with PGP keys.

        Creates a new user account with the specified credentials and generates
        a unique API key. If PGP keys are not provided, generates a new RSA 3072-bit
        key pair using the SHA256 hash of the API key as the passphrase.

        Args:
            username (str): Unique username for the new account
            password (str): Plain text password (will be hashed with Argon2id)
            public_key_data (str, optional): ASCII-armored public key. Generated if not provided.
            private_key_data (str, optional): ASCII-armored private key. Generated if not provided.

        Returns:
            Tuple[Optional[User], Union[str, Tuple[PublicPgpKey, PrivatePgpKey]]]:
                - Success: (User object, PgpKeyPair object)
                - Failure: (None, error_message_string)
        """
        try:
            with session_scope() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(username=username).first()
                if existing_user:
                    return None, "Username already exists"

                # Hash the provided password
                password_hash_val = hash_password(password)

                # Generate API key and hash it for storage
                raw_api_key = generate_api_key()
                api_key_hash_val = hash_api_key(raw_api_key)

                # Create user with hashed password and API key hash
                user = User(username=username, password_hash=password_hash_val, api_key_hash=api_key_hash_val)
                session.add(user)
                session.flush()  # Flush to get user.id without committing

                # Generate GPG keys if not provided
                if not public_key_data or not private_key_data:
                    from utils.gpg_utils import generate_gpg_keypair
                    # Use username as email if no email provided
                    email = f"{username}@example.com"  # Default email format
                    # Use secure passphrase derivation with user ID as salt and RAW API key
                    gpg_passphrase = derive_gpg_passphrase(raw_api_key, user.id)
                    public_key_data, private_key_data = generate_gpg_keypair(username, email, gpg_passphrase)

                # Add PGP keys
                public_key = PublicPgpKey(key_data=public_key_data, user_id=user.id)
                private_key = PrivatePgpKey(key_data=private_key_data, user_id=user.id)
                session.add(public_key)
                session.add(private_key)
                session.flush()  # Flush to ensure keys are persisted

                # Expunge objects from session to detach them before session closes
                session.expunge(user)
                session.expunge(public_key)
                session.expunge(private_key)

                # Context manager commits here

            # Objects are now detached but have all their data
            # Return UserRegistrationResult with raw API key (only time it's returned!)
            return UserRegistrationResult(
                user=user,
                api_key=raw_api_key,
                pgp_keypair=PgpKeyPair(public_key, private_key)
            ), None

        except Exception as e:
            return None, f"Registration failed: {str(e)}"

    def login_user(self, username: str, password: str) -> Tuple[Optional[User], Union[str, 'PgpKeyPair']]:
        """
        Authenticate a user and return their account data.

        Verifies the provided credentials against the stored password hash
        and returns the user's account information along with their PGP keys
        if authentication is successful.

        Args:
            username (str): The username to authenticate
            password (str): The plain text password to verify

        Returns:
            Tuple[Optional[User], Union[str, PgpKeyPair]]:
                - Success: (User object, PgpKeyPair object)
                - Failure: (None, error_message_string)
        """
        try:
            with session_scope() as session:
                user = session.query(User).filter_by(username=username).first()

                if not user or not getattr(user, 'password_hash', None) or not isinstance(user.password_hash, str) or not verify_password(password, user.password_hash):
                    return None, 'Invalid credentials'

                # Fetch PGP keys
                public_key = session.query(PublicPgpKey).filter_by(user_id=user.id).first()
                private_key = session.query(PrivatePgpKey).filter_by(user_id=user.id).first()

                # Expunge objects from session to detach them before session closes
                session.expunge(user)
                if public_key:
                    session.expunge(public_key)
                if private_key:
                    session.expunge(private_key)

                # Context manager commits here (though this is read-only)

            # Objects are now detached but have all their data
            return user, PgpKeyPair(public_key, private_key)

        except Exception as e:
            return None, f'Login failed: {str(e)}'
