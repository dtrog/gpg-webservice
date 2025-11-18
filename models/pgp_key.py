import enum
from typing import Any, Optional
from db.database import db
from sqlalchemy import Enum
from abc import abstractmethod
import hashlib


class PgpKeyType(enum.Enum):
    """Enumeration for PGP key types."""
    PUBLIC = "public"
    PRIVATE = "private"


class PgpKey(db.Model):
    """
    Abstract base class for PGP keys.
    """
    __tablename__ = "pgp_keys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', use_alter=True), nullable=False)
    key_type = db.Column(Enum(PgpKeyType, name="pgp_key_type", native_enum=False), nullable=False)
    key_data = db.Column(db.String, nullable=False)
    
    # Relationship back to user
    user = db.relationship('User', back_populates='pgp_keys')

    @abstractmethod
    def key_role(self) -> str:
        """Describe the key's role (public/private)."""
        pass

    __mapper_args__ = {
        'polymorphic_on': key_type,
    }

    def __init__(self, key_type: PgpKeyType, key_data: str, user_id: Optional[int] = None, **kwargs):
        """
        Initialize a PGP key instance.
        
        Args:
            key_type (PgpKeyType): The type of the PGP key (public or private)
            key_data (str): The actual key data
            **kwargs: Additional keyword arguments for SQLAlchemy model initialization
        """
        super().__init__(**kwargs)
        self.key_type = key_type
        self.key_data = key_data
        if user_id is not None:
            self.user_id = user_id

    def __repr__(self) -> str:
        """Return a string representation of the PGP key."""
        data_hash = hashlib.sha256(self.key_data.encode('utf-8')).hexdigest() if self.key_data else "None"
        return f"<{self.__class__.__name__}(id={self.id}, data_hash='{data_hash}')>"

class PublicPgpKey(PgpKey):
    """Model for public PGP keys."""
    __mapper_args__ = {
        'polymorphic_identity': PgpKeyType.PUBLIC
    }

    def __init__(self, key_data: str, user_id: Optional[int] = None, **kwargs: Any):
        super().__init__(key_type=PgpKeyType.PUBLIC, key_data=key_data, user_id=user_id, **kwargs)

    def key_role(self):
        return "public"
       
class PrivatePgpKey(PgpKey):
    """Model for private PGP keys."""
    __mapper_args__ = {
        'polymorphic_identity': PgpKeyType.PRIVATE
    }

    def __init__(self, key_data: str, user_id: Optional[int] = None, **kwargs: Any):
        super().__init__(key_type=PgpKeyType.PRIVATE, key_data=key_data, user_id=user_id, **kwargs)

    def key_role(self) -> str:
        return "private"
