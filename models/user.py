"""
User model for database operations.

This module defines the User model which represents a user account in the GPG webservice.
Each user has a unique username, hashed password, API key for authentication, and
associated PGP keys for cryptographic operations.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.database import db


class User(db.Model):
    """
    User model representing a user account in the system.
    
    This model stores user credentials and maintains relationships with PGP keys.
    Each user gets a unique API key for authenticating API requests, and their
    password is stored as a secure hash.
    
    Attributes:
        id (int): Primary key, auto-generated unique identifier
        username (str): Unique username for the user account
        password_hash (str): Argon2id hash of the user's password
        api_key (str): Unique API key for authentication (base64url encoded)
        pgp_keys (relationship): Related PGP keys (public/private) for this user
    
    Relationships:
        - One-to-many with PgpKey (cascade delete)
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    api_key = db.Column(db.String, unique=True, nullable=True)
    pgp_keys = db.relationship('PgpKey', back_populates='user', cascade="all, delete-orphan")

    def __init__(self, username: str, password_hash: str, api_key: str | None = None, **kwargs):
        """
        Initialize a new User instance.
        
        Args:
            username (str): Unique username for the account
            password_hash (str): Argon2id hash of the user's password
            api_key (str, optional): API key for authentication. Generated if not provided.
            **kwargs: Additional keyword arguments passed to SQLAlchemy Model
        """
        super().__init__(**kwargs)
        self.username = username
        self.password_hash = password_hash
        self.api_key = api_key

    def __repr__(self) -> str:
        """Return a string representation of the User instance."""
        api_key_display = f"{self.api_key[:8]}..." if self.api_key else "None"
        return f"<User(id={self.id}, username='{self.username}', api_key='{api_key_display}')>"