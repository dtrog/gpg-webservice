"""
PGP Key models for database operations.

This module defines models for storing PGP keys associated with users.
Each user has a public and private key pair stored separately for
cryptographic operations.
"""

from typing import Optional, TYPE_CHECKING
from db.database import db

if TYPE_CHECKING:
    from models.user import User


class PgpKey(db.Model):
    """
    PGP Key model representing a single public or private key.
    
    This model stores PGP keys (both public and private) in ASCII-armored format.
    Each key is associated with a specific user and marked as either 'public' or 'private'.
    Private keys are stored with passphrases derived from the user's API key hash.
    
    Attributes:
        id (int): Primary key, auto-generated unique identifier
        user_id (int): Foreign key reference to the owning user
        key_type (str): Type of key - either 'public' or 'private'
        key_data (str): ASCII-armored PGP key content
        user (relationship): Back-reference to the User who owns this key
    
    Relationships:
        - Many-to-one with User
    """
    __tablename__ = 'pgp_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key_type = db.Column(db.String, nullable=False)  # 'public' or 'private'
    key_data = db.Column(db.String, nullable=False)  # ASCII-armored key
    user = db.relationship('User', back_populates='pgp_keys')

    def __init__(self, user_id: int, key_type: str, key_data: str, user: Optional['User'] = None, **kwargs):
        """
        Initialize a new PgpKey instance.
        
        Args:
            user_id (int): ID of the user who owns this key
            key_type (str): Type of key ('public' or 'private')
            key_data (str): ASCII-armored PGP key content
            user (User, optional): User instance (will be loaded from DB if not provided)
            **kwargs: Additional keyword arguments passed to SQLAlchemy Model
        """
        super().__init__(**kwargs)
        self.user_id = user_id
        self.key_type = key_type
        self.key_data = key_data
        if user is not None:
            self.user = user

    def __repr__(self) -> str:
        """Return a string representation of the PgpKey instance."""
        key_preview = self.key_data[:50] + "..." if len(self.key_data) > 50 else self.key_data
        return f"<PgpKey(id={self.id}, user_id={self.user_id}, type='{self.key_type}', data='{key_preview}')>"


class PgpKeyPair:
    """
    Convenience class representing a public/private key pair.
    
    This is not a database model but a simple container class used to group
    a user's public and private keys together for easier handling in services
    and API endpoints.
    
    Attributes:
        public_key (PgpKey): The user's public key instance
        private_key (PgpKey): The user's private key instance
    """
    
    def __init__(self, public_key: Optional[PgpKey], private_key: Optional[PgpKey]):
        """
        Initialize a new PgpKeyPair instance.
        
        Args:
            public_key (PgpKey, optional): The user's public key
            private_key (PgpKey, optional): The user's private key
        """
        self.public_key = public_key
        self.private_key = private_key

    def __repr__(self) -> str:
        """Return a string representation of the PgpKeyPair instance."""
        pub_id = self.public_key.id if self.public_key else None
        priv_id = self.private_key.id if self.private_key else None
        return f"<PgpKeyPair(public_id={pub_id}, private_id={priv_id})>"
