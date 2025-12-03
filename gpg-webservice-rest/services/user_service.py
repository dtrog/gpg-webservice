"""
User service for user-related business logic.

This module provides the UserService class which handles user registration,
authentication, and user data management. It coordinates between the database
models, authentication system, and GPG key generation.

DETERMINISTIC SESSION KEYS:
- Registration: Creates user with master_salt, returns first session key
- Login: Derives session key from contract_hash + master_salt + time_window
- Session keys expire hourly with 10-minute grace period
- AI agents can regenerate keys by re-logging in (no storage needed)
"""

import hashlib
from typing import Optional, Tuple, Union, NamedTuple
from models.user import User
from models.pgp_key import PublicPgpKey, PrivatePgpKey, PgpKey
from db.database import get_session
from db.session_manager import session_scope
from services.auth_service import hash_password, verify_password
from utils.crypto_utils import (
    generate_api_key,
    hash_api_key,
    derive_gpg_passphrase,
    generate_master_salt,
    generate_session_key_for_user,
)


class PgpKeyPair(NamedTuple):
    """Named tuple for holding a public/private key pair."""
    public_key: Optional[PublicPgpKey]
    private_key: Optional[PrivatePgpKey]


class SessionKeyInfo(NamedTuple):
    """Named tuple for session key information."""
    api_key: str           # The derived session key (sk_...)
    window_index: int      # Current session window index
    window_start: str      # ISO timestamp of window start
    expires_at: str        # ISO timestamp when key expires


class UserRegistrationResult(NamedTuple):
    """Named tuple for holding user registration result with session key."""
    user: 'User'
    session_key_info: SessionKeyInfo  # Derived session key (regenerable)
    pgp_keypair: PgpKeyPair


class UserLoginResult(NamedTuple):
    """Named tuple for holding user login result with session key."""
    user: 'User'
    session_key_info: SessionKeyInfo  # Derived session key for current window
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

    DETERMINISTIC SESSION KEYS:
    - Users authenticate with username + contract_hash (as password)
    - Session keys are derived: HMAC(PBKDF2(contract_hash, master_salt), hour_index)
    - Keys expire hourly, AI agents must re-login to get new keys
    - No API keys are stored - verification is mathematical

    Methods:
        register_user: Create a new user account with PGP keys
        login_user: Authenticate a user and return their session key
    """

    def register_user(
        self,
        username: str,
        password: str,
        public_key_data: Optional[str] = None,
        private_key_data: Optional[str] = None
    ) -> Tuple[Optional[UserRegistrationResult], Optional[str]]:
        """
        Register a new user account with PGP keys and deterministic session key.

        Creates a new user account with the specified credentials and generates
        a master salt for session key derivation. If PGP keys are not provided,
        generates a new RSA 3072-bit key pair.

        The password should be the SHA256 hash of the successorship contract
        plus your PGP signature. This allows AI agents to regenerate their
        "password" from their immutable contract.

        Args:
            username (str): Unique username (agent name from contract)
            password (str): SHA256(successorship_contract + pgp_signature)
            public_key_data (str, optional): ASCII-armored public key. Generated if not provided.
            private_key_data (str, optional): ASCII-armored private key. Generated if not provided.

        Returns:
            Tuple[Optional[UserRegistrationResult], Optional[str]]:
                - Success: (UserRegistrationResult with session key, None)
                - Failure: (None, error_message_string)
        """
        try:
            with session_scope() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(username=username).first()
                if existing_user:
                    # SECURITY: Use generic error to prevent username enumeration
                    return None, "Registration failed. Please verify your credentials or contact administrator."

                # Hash the provided password (contract_hash) with Argon2id
                password_hash_val = hash_password(password)

                # Generate random master salt for PBKDF2 derivation
                master_salt = generate_master_salt()

                # Create user with deterministic key system
                user = User(
                    username=username,
                    password_hash=password_hash_val,
                    master_salt=master_salt,
                    api_key_hash=None  # LEGACY: Not used with deterministic keys
                )
                session.add(user)
                session.flush()  # Flush to get user.id without committing

                # Generate first session key (for this registration response)
                # Note: We use password_hash_val (the Argon2id hash) for derivation
                # This is more secure than using the raw password
                session_key_dict = generate_session_key_for_user(
                    contract_hash=password_hash_val,
                    master_salt=master_salt
                )
                session_key_info = SessionKeyInfo(
                    api_key=session_key_dict['api_key'],
                    window_index=session_key_dict['window_index'],
                    window_start=session_key_dict['window_start'],
                    expires_at=session_key_dict['expires_at']
                )

                # Generate GPG keys if not provided
                if not public_key_data or not private_key_data:
                    from utils.gpg_utils import generate_gpg_keypair
                    # Use username as email if no email provided
                    email = f"{username}@example.com"  # Default email format
                    # Use secure passphrase derivation with user ID
                    # For GPG passphrase, we use the session key as the raw input
                    gpg_passphrase = derive_gpg_passphrase(session_key_info.api_key, user.id)
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
            return UserRegistrationResult(
                user=user,
                session_key_info=session_key_info,
                pgp_keypair=PgpKeyPair(public_key, private_key)
            ), None

        except Exception as e:
            return None, f"Registration failed: {str(e)}"

    def login_user(self, username: str, password: str) -> Tuple[Optional[UserLoginResult], Optional[str]]:
        """
        Authenticate a user and return a derived session key.

        Verifies the provided credentials against the stored password hash
        and derives a session key valid for the current time window (1 hour).
        The session key expires automatically and must be regenerated by
        logging in again.

        Args:
            username (str): The username to authenticate
            password (str): The contract_hash (SHA256 of contract + signature)

        Returns:
            Tuple[Optional[UserLoginResult], Optional[str]]:
                - Success: (UserLoginResult with session key, None)
                - Failure: (None, error_message_string)
        """
        try:
            with session_scope() as session:
                user = session.query(User).filter_by(username=username).first()

                if not user:
                    return None, 'Invalid credentials'

                # Verify password
                if not getattr(user, 'password_hash', None):
                    return None, 'Invalid credentials'
                if not isinstance(user.password_hash, str):
                    return None, 'Invalid credentials'
                if not verify_password(password, user.password_hash):
                    return None, 'Invalid credentials'

                # Check if user has deterministic key system enabled
                if not user.uses_deterministic_keys:
                    return None, 'User account requires migration to deterministic keys'

                # Derive session key for current time window
                session_key_dict = generate_session_key_for_user(
                    contract_hash=user.password_hash,
                    master_salt=user.master_salt
                )
                session_key_info = SessionKeyInfo(
                    api_key=session_key_dict['api_key'],
                    window_index=session_key_dict['window_index'],
                    window_start=session_key_dict['window_start'],
                    expires_at=session_key_dict['expires_at']
                )

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
            return UserLoginResult(
                user=user,
                session_key_info=session_key_info,
                pgp_keypair=PgpKeyPair(public_key, private_key)
            ), None

        except Exception as e:
            return None, f'Login failed: {str(e)}'
