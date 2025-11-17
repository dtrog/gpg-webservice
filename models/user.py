"""
User model for database operations.

This module defines the User model which represents a user account in the GPG webservice.
Each user has a unique username, hashed password, hashed API key for authentication, and
associated PGP keys for cryptographic operations.

Note: API keys are stored as SHA256 hashes for security. The plaintext API key is only
      returned once during registration and must be saved by the client.
"""


from sqlalchemy.orm import relationship
from db.database import db
from models.pgp_key import PublicPgpKey, PrivatePgpKey

class User(db.Model):
    """User model for database operations."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    api_key_hash = db.Column(db.String, unique=True, nullable=False)  # SHA256 hash of API key
    # Relationships to PGP keys
    pgp_keys = relationship('PgpKey', back_populates='user', cascade='all, delete-orphan')

    def __init__(self, username: str, password_hash: str, api_key_hash: str, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.password_hash = password_hash
        self.api_key_hash = api_key_hash
        self.pgp_keys = []

    def __repr__(self) -> str:
        api_key_display = f"{self.api_key_hash[:8]}..." if self.api_key_hash else "None"
        return f"<User(id={self.id}, username='{self.username}', api_key_hash='{api_key_display}')>"