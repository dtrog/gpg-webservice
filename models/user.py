"""
User model for database operations.

This module defines the User model which represents a user account in the GPG webservice.
Each user has a unique username, hashed password, API key for authentication, and
associated PGP keys for cryptographic operations.
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
    api_key = db.Column(db.String, unique=True, nullable=False)
    public_pgp_key_id = db.Column(db.Integer, db.ForeignKey('pgp_keys.id'), unique=True)
    private_pgp_key_id = db.Column(db.Integer, db.ForeignKey('pgp_keys.id'), unique=True)

    public_pgp_key = relationship('PublicPgpKey', foreign_keys=[public_pgp_key_id], uselist=False, post_update=True)
    private_pgp_key = relationship('PrivatePgpKey', foreign_keys=[private_pgp_key_id], uselist=False, post_update=True)

    def __init__(self, username: str, password_hash: str, api_key: str, public_pgp_key: PublicPgpKey = None, private_pgp_key: PrivatePgpKey = None, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.password_hash = password_hash
        self.api_key = api_key
        if public_pgp_key is not None:
            self.public_pgp_key = public_pgp_key
        if private_pgp_key is not None:
            self.private_pgp_key = private_pgp_key

    def __repr__(self) -> str:
        api_key_display = f"{self.api_key[:8]}..." if self.api_key else "None"
        return f"<User(id={self.id}, username='{self.username}', api_key='{api_key_display}')>"