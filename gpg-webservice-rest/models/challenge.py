"""
Challenge model for database operations.

This module defines the Challenge model used for cryptographic challenge-response
authentication. Challenges are temporary data that users must sign to prove
ownership of their private keys.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from db.database import db

if TYPE_CHECKING:
    from models.user import User


def utcnow() -> datetime:
    """Return the current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


class Challenge(db.Model):
    """
    Challenge model representing a cryptographic challenge for user authentication.
    
    Challenges are used to verify that a user possesses the private key
    corresponding to their registered public key. A challenge contains random
    data that the user must sign, and the signature is verified against their
    public key.
    
    Attributes:
        id (int): Primary key, auto-generated unique identifier
        user_id (int): Foreign key reference to the user being challenged
        challenge_data (str): Random challenge string to be signed
        signature (str, optional): User's signature of the challenge data
        created_at (datetime): Timestamp when the challenge was created
        user (relationship): Back-reference to the User being challenged
    
    Relationships:
        - Many-to-one with User
    """
    __tablename__ = 'challenges'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', use_alter=True), nullable=False)
    challenge_data = db.Column(db.String, nullable=False)
    signature = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    user = db.relationship('User')

    def __repr__(self) -> str:
        """Return a string representation of the Challenge instance."""
        challenge_preview = self.challenge_data[:20] + "..." if len(self.challenge_data) > 20 else self.challenge_data
        has_signature = "signed" if self.signature else "unsigned"
        return f"<Challenge(id={self.id}, user_id={self.user_id}, data='{challenge_preview}', {has_signature})>"
