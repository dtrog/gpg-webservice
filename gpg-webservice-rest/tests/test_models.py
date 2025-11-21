"""
Comprehensive tests for database models.

This module tests all database models (User, PgpKey, Challenge) with proper
database integration to ensure relationships, constraints, and business logic work correctly.
"""

import pytest
import secrets
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from models.user import User
from models.pgp_key import PgpKey, PgpKeyType, PublicPgpKey, PrivatePgpKey
from models.challenge import Challenge
from db.database import db


class TestUserModel:
    """Test the User model with database integration."""
    
    def test_user_creation(self, app, db_session):
        """Test basic user creation with database."""
        with app.app_context():
            user = User(
                username='testuser',
                password_hash='hashed_password',
                api_key='test_api_key_123'
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.password_hash == 'hashed_password'
            assert user.api_key == 'test_api_key_123'
    
    def test_user_unique_username(self, app, db_session):
        """Test username uniqueness constraint."""
        with app.app_context():
            user1 = User(username='duplicate', password_hash='hash1', api_key='key1')
            user2 = User(username='duplicate', password_hash='hash2', api_key='key2')
            
            db.session.add(user1)
            db.session.commit()
            
            db.session.add(user2)
            with pytest.raises(IntegrityError):
                db.session.commit()


class TestChallengeModel:
    """Test the Challenge model with database integration."""
    
    def test_challenge_creation_basic(self, app, db_session):
        """Test basic challenge creation - debug the user_id issue."""
        with app.app_context():
            user = User(username='testuser', password_hash='hash', api_key='key')
            db.session.add(user)
            db.session.commit()
            
            # Create challenge step by step to debug the issue
            challenge = Challenge()
            challenge.user_id = user.id
            challenge.challenge_data = 'test_challenge_data'
            challenge.signature = None
            
            # Verify user_id is set before adding to session
            assert challenge.user_id == user.id
            assert challenge.user_id is not None
            
            db.session.add(challenge)
            db.session.commit()
            
            assert challenge.id is not None
            assert challenge.user_id == user.id
            assert challenge.challenge_data == 'test_challenge_data'
            assert challenge.signature is None
            assert challenge.created_at is not None
    
    def test_challenge_creation_with_constructor(self, app, db_session):
        """Test challenge creation using constructor parameters."""
        with app.app_context():
            user = User(username='testuser', password_hash='hash', api_key='key')
            db.session.add(user)
            db.session.commit()
            
            challenge_data = secrets.token_urlsafe(32)
            challenge = Challenge(
                user_id=user.id,
                challenge_data=challenge_data,
                signature=None
            )
            db.session.add(challenge)
            db.session.commit()
            
            assert challenge.user_id == user.id
            assert challenge.challenge_data == challenge_data
    
    def test_challenge_user_relationship(self, app, db_session):
        """Test Challenge-User relationship."""
        with app.app_context():
            user = User(username='testuser', password_hash='hash', api_key='key')
            db.session.add(user)
            db.session.commit()
            
            challenge = Challenge()
            challenge.user_id = user.id
            challenge.challenge_data = 'test_data'
            db.session.add(challenge)
            db.session.commit()
            
            # Test relationship
            assert challenge.user.username == 'testuser'
            assert challenge.user.id == user.id


class TestPgpKeyModel:
    """Test the PgpKey model with database integration."""
    
    def test_public_key_creation(self, app, db_session):
        """Test PublicPgpKey creation."""
        with app.app_context():
            user = User(username='testuser', password_hash='hash', api_key='key')
            db.session.add(user)
            db.session.commit()
            
            public_key = PublicPgpKey(key_data='public_key_data', user_id=user.id)
            db.session.add(public_key)
            db.session.commit()
            
            assert public_key.key_type == PgpKeyType.PUBLIC
            assert public_key.key_data == 'public_key_data'
            assert public_key.user_id == user.id
            assert public_key.key_role() == 'public'
    
    def test_private_key_creation(self, app, db_session):
        """Test PrivatePgpKey creation."""
        with app.app_context():
            user = User(username='testuser', password_hash='hash', api_key='key')
            db.session.add(user)
            db.session.commit()
            
            private_key = PrivatePgpKey(key_data='private_key_data', user_id=user.id)
            db.session.add(private_key)
            db.session.commit()
            
            assert private_key.key_type == PgpKeyType.PRIVATE
            assert private_key.key_data == 'private_key_data'
            assert private_key.user_id == user.id
            assert private_key.key_role() == 'private'


# Legacy tests for backward compatibility
def test_user_model_init():
    """Legacy test for basic user initialization."""
    user = User(username='alice', password_hash='hash', api_key='key123')
    assert user.username == 'alice'
    assert user.password_hash == 'hash'
    assert user.api_key == 'key123'

def test_challenge_model_init():
    """Legacy test for basic challenge initialization."""
    user = User(username='dave', password_hash='hash4', api_key='key456')
    user.id = 3  # Simulate DB assignment
    now = datetime.now(timezone.utc)
    challenge = Challenge(user_id=user.id, challenge_data='challenge', signature='sig', created_at=now)
    assert challenge.user_id == user.id
    assert challenge.challenge_data == 'challenge'
    assert challenge.signature == 'sig'
    assert isinstance(challenge.created_at, datetime)
    assert challenge.created_at.tzinfo is not None
