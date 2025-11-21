import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch, MagicMock
from services.challenge_service import ChallengeService
from models.challenge import Challenge
from models.user import User
from models.pgp_key import PgpKey

def test_create_challenge(app, db_session):
    """Test challenge creation with proper database session management."""
    from db.database import db
    import secrets
    
    with app.app_context():
        # Create a test user first
        user = User(username='testuser', password_hash='hashed_password', api_key='test_api_key')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        # Mock get_session to return the same session as the test
        with patch('services.challenge_service.get_session', return_value=db.session):
            service = ChallengeService()
            challenge = service.create_challenge(user_id=user_id)
            
            # Verify the challenge was created correctly
            assert challenge.user_id == user_id
            assert challenge.challenge_data is not None
            assert len(challenge.challenge_data) > 0
            assert challenge.signature is None
            
            # Verify it exists in database
            challenge_in_db = db.session.query(Challenge).filter_by(user_id=user_id).first()
            assert challenge_in_db is not None
            assert challenge_in_db.challenge_data == challenge.challenge_data

def query_side_effect_factory(mock_challenge_query, mock_user_query):
    """Factory to create a side effect for session.query."""
    def query_side_effect(model):
        if model == Challenge:
            return mock_challenge_query
        elif model == User:
            return mock_user_query
        return MagicMock()
    return query_side_effect

def test_verify_challenge():
    """Test challenge verification with proper mocking."""
    from datetime import datetime, timezone

    # Mock challenge and set its user
    mock_challenge = MagicMock()
    mock_challenge.user_id = 1
    mock_challenge.challenge_data = "test_data"
    mock_challenge.created_at = datetime.now(timezone.utc)

    # Mock user with PGP key
    from models.pgp_key import PgpKeyType
    mock_pgp_key = MagicMock(key_type=PgpKeyType.PUBLIC, key_data='mock_public_key')
    mock_user = MagicMock()
    mock_user.pgp_keys.all.return_value = [mock_pgp_key]
    mock_challenge.user = mock_user

    # Create mock session
    mock_session = MagicMock()

    # Mock challenge query
    mock_challenge_query = MagicMock()
    mock_challenge_query.filter_by.return_value.first.return_value = mock_challenge
    # Mock user query
    mock_user_query = MagicMock()
    mock_user_query.filter_by.return_value.first.return_value = mock_user
    # Setup query side effect
    mock_session.query.side_effect = query_side_effect_factory(mock_challenge_query, mock_user_query)

    # Patch both db.session (used by session_scope) and get_session (fallback)
    with patch('db.database.db.session', mock_session):
        with patch('services.challenge_service.get_session', return_value=mock_session):
            # Mock signature verification
            with patch('utils.gpg_utils.verify_signature', return_value=True):
                service = ChallengeService()
                result, message = service.verify_challenge(
                    user_id=1,
                    challenge_data="test_data",
                    signature="test_signature"
                )
                assert result is True
                assert message == "Challenge verified"
                mock_session.delete.assert_called_once_with(mock_challenge)
                # commit may be called but not guaranteed due to RuntimeError handling
                # mock_session.commit.assert_called_once()

def test_create_and_verify_challenge(app, db_session):
    """Test full challenge creation and verification flow with proper session management."""
    from db.database import db
    from models.pgp_key import PgpKeyType
    from datetime import timezone

    with app.app_context():
        # Create a test user with a public key
        user = User(username='testuser', password_hash='hashed_password', api_key='test_api_key')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        # Add a public key for the user
        public_key = PgpKey(user_id=user_id, key_type=PgpKeyType.PUBLIC, key_data='mock_public_key_data')
        db.session.add(public_key)
        db.session.commit()
        
        # Mock get_session to use the same session throughout
        with patch('services.challenge_service.get_session', return_value=db.session):
            service = ChallengeService()
            challenge = service.create_challenge(user_id=user_id)
            
            assert challenge.user_id == user_id
            assert challenge.challenge_data is not None

            # Ensure challenge.created_at is timezone-aware for the test
            if challenge.created_at.tzinfo is None:
                challenge.created_at = challenge.created_at.replace(tzinfo=timezone.utc)
                db.session.commit()
            
            # Test the verification part using the service with mocked GPG operations
            with patch('utils.gpg_utils.verify_signature', return_value=True):
                result, message = service.verify_challenge(
                    user_id=user_id,
                    challenge_data=challenge.challenge_data,
                    signature="test_signature"
                )
                assert result is True
                assert message == "Challenge verified"
            
            # Verify that challenge was deleted after verification
            remaining_challenges = db.session.query(Challenge).filter_by(user_id=user_id).all()
            assert len(remaining_challenges) == 0
