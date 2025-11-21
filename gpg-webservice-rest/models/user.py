"""
User model for database operations.

This module defines the User model which represents a user account in the GPG webservice.
Each user has a unique username, hashed password (contract hash), master salt for key
derivation, and associated PGP keys for cryptographic operations.

The system uses deterministic session keys:
- password_hash: Argon2id hash of SHA256(successorship_contract + pgp_signature)
- master_salt: Random salt used with PBKDF2 to derive master secret
- Session keys are derived from master_secret + time_window, not stored

AI agents can regenerate their session keys by:
1. Computing: password = SHA256(contract + signature)
2. Logging in to get a derived session key valid for the current hour
3. Keys expire automatically, forcing re-authentication
"""


from sqlalchemy.orm import relationship
from db.database import db
from models.pgp_key import PublicPgpKey, PrivatePgpKey


class User(db.Model):
    """
    User model for database operations.

    Authentication Flow:
    1. User provides username + password (contract_hash)
    2. Server verifies password against password_hash (Argon2id)
    3. Server derives master_secret = PBKDF2(password_hash, master_salt)
    4. Server derives session_key = HMAC(master_secret, current_hour)
    5. Session key returned to client, valid for 1 hour + 10min grace
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)

    # Argon2id hash of the contract_hash (password)
    # The password IS the SHA256(successorship_contract + pgp_signature)
    password_hash = db.Column(db.String, nullable=False)

    # Random salt for PBKDF2 master secret derivation
    # Used to derive deterministic session keys
    master_salt = db.Column(db.String, nullable=False)

    # LEGACY: api_key_hash - kept for migration, nullable for new users
    # Remove this column after migrating existing users
    api_key_hash = db.Column(db.String, unique=True, nullable=True)

    # Relationships to PGP keys
    pgp_keys = relationship('PgpKey', back_populates='user', cascade='all, delete-orphan')

    def __init__(self, username: str, password_hash: str, master_salt: str,
                 api_key_hash: str = None, **kwargs):
        """
        Initialize a new User.

        Args:
            username: Unique identifier (agent name from contract)
            password_hash: Argon2id hash of the contract hash
            master_salt: Random hex string for PBKDF2 derivation
            api_key_hash: LEGACY - SHA256 hash of API key (nullable for new users)
        """
        super().__init__(**kwargs)
        self.username = username
        self.password_hash = password_hash
        self.master_salt = master_salt
        self.api_key_hash = api_key_hash
        self.pgp_keys = []

    @property
    def uses_deterministic_keys(self) -> bool:
        """Check if this user uses the new deterministic key system."""
        return self.master_salt is not None and len(self.master_salt) == 64

    def __repr__(self) -> str:
        salt_display = f"{self.master_salt[:8]}..." if self.master_salt else "None"
        return f"<User(id={self.id}, username='{self.username}', master_salt='{salt_display}')>"
