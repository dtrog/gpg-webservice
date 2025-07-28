"""
User service for user-related business logic.

This module provides the UserService class which handles user registration,
authentication, and user data management. It coordinates between the database
models, authentication system, and GPG key generation.
"""

import hashlib
from typing import Optional, Tuple, Union
from models.user import User
from models.pgp_key import PgpKey, PgpKeyPair
from db.database import get_session
from services.auth_service import hash_password, verify_password
from utils.crypto_utils import generate_api_key


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
    ) -> Tuple[Optional[object], Union[str, PgpKeyPair]]:
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
            Tuple[Optional[object], Union[str, PgpKeyPair]]: 
                - Success: (SimpleUser object, PgpKeyPair object)
                - Failure: (None, error_message_string)
        """
        session = get_session()
        try:
            if session.query(User).filter_by(username=username).first():
                return None, 'Username already exists'
            password_hash = hash_password(password)
            api_key = generate_api_key()
            user = User(username=username, password_hash=password_hash, api_key=api_key)
            session.add(user)
            session.commit()
            session.refresh(user)  # Ensure user.id is populated
            
            # Store user ID before detaching
            user_id = user.id
            user_username = user.username
            user_api_key = user.api_key
            user_password_hash = user.password_hash
            
            # Generate GPG keys if not provided
            if not public_key_data or not private_key_data:
                from utils.gpg_utils import generate_gpg_keypair
                # Use username as email if no email provided
                email = f"{username}@example.com"  # Default email format
                # Use SHA256 hash of API key as GPG passphrase for security and consistency
                gpg_passphrase = api_key_to_gpg_passphrase(api_key)
                public_key_data, private_key_data = generate_gpg_keypair(username, email, gpg_passphrase)
            
            # Add PGP keys
            public_key = PgpKey(user_id=user.id, key_type='public', key_data=public_key_data)
            private_key = PgpKey(user_id=user.id, key_type='private', key_data=private_key_data)
            session.add(public_key)
            session.add(private_key)
            session.commit()
            
            # Refresh objects to make sure they're properly loaded
            session.refresh(public_key)
            session.refresh(private_key)
            
            # Create a simple object with the data we need
            class SimpleUser:
                def __init__(self, id, username, password_hash, api_key):
                    self.id = id
                    self.username = username
                    self.password_hash = password_hash
                    self.api_key = api_key
            
            simple_user = SimpleUser(user_id, user_username, user_password_hash, user_api_key)
            pgp_keypair = PgpKeyPair(public_key, private_key)
            return simple_user, pgp_keypair
        finally:
            session.close()

    def login_user(self, username: str, password: str) -> Tuple[Optional[object], Union[str, PgpKeyPair]]:
        """
        Authenticate a user and return their account data.
        
        Verifies the provided credentials against the stored password hash
        and returns the user's account information along with their PGP keys
        if authentication is successful.
        
        Args:
            username (str): The username to authenticate
            password (str): The plain text password to verify
            
        Returns:
            Tuple[Optional[object], Union[str, PgpKeyPair]]:
                - Success: (SimpleUser object, PgpKeyPair object)
                - Failure: (None, error_message_string)
        """
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user or not getattr(user, 'password_hash', None) or not isinstance(user.password_hash, str) or not verify_password(password, user.password_hash):
                return None, 'Invalid credentials'
            
            # Store user data before detaching
            user_id = user.id  
            user_username = user.username
            user_api_key = user.api_key
            user_password_hash = user.password_hash
            
            # Fetch PGP keys
            public_key = session.query(PgpKey).filter_by(user_id=user.id, key_type='public').first()
            private_key = session.query(PgpKey).filter_by(user_id=user.id, key_type='private').first()
            
            # Refresh objects to ensure they're properly loaded
            if public_key:
                session.refresh(public_key)
            if private_key:
                session.refresh(private_key)
                
            # Create a simple object with the data we need
            class SimpleUser:
                def __init__(self, id, username, password_hash, api_key):
                    self.id = id
                    self.username = username
                    self.password_hash = password_hash
                    self.api_key = api_key
            
            simple_user = SimpleUser(user_id, user_username, user_password_hash, user_api_key)
            pgp_keypair = PgpKeyPair(public_key, private_key)
            return simple_user, pgp_keypair
        finally:
            session.close()
