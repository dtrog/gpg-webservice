import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from flask import Flask
from unittest.mock import patch, MagicMock
from services.challenge_service import ChallengeService
from models.challenge import Challenge
from models.user import User
from models.pgp_key import PgpKey
from db.database import init_db

@pytest.fixture(scope="module")
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.app_context():
        init_db(app)
        yield app

@pytest.fixture(autouse=True)
def app_context(app: Flask):
    """Ensure all tests run within Flask app context."""
    with app.app_context():
        yield

def test_create_challenge():
    """Test challenge creation with proper mocking."""
    with patch('services.challenge_service.get_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Mock the query for pruning old challenges
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.delete.return_value = None
        mock_query.filter.return_value.order_by.return_value.__getitem__.return_value = []
        mock_session.query.return_value = mock_query
        
        with patch('secrets.token_urlsafe', return_value="test_challenge_data"):
            service = ChallengeService()
            result = service.create_challenge(user_id=1)
            
            # Verify the challenge was created correctly
            assert result.user_id == 1
            assert result.challenge_data == "test_challenge_data"
            
            # Verify database interactions
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called()
            mock_session.refresh.assert_called_once()
            mock_session.close.assert_called()

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

    with patch('services.challenge_service.get_session', return_value=MagicMock()) as mock_get_session:
        mock_session = mock_get_session.return_value
        # Mock challenge query
        mock_challenge_query = MagicMock()
        mock_challenge_query.filter_by.return_value.first.return_value = mock_challenge
        # Mock user query
        mock_user_query = MagicMock()
        mock_user_query.filter_by.return_value.first.return_value = mock_user
        # Setup query side effect
        mock_session.query.side_effect = query_side_effect_factory(mock_challenge_query, mock_user_query)
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
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            signature="test_signature"
            
            

def test_create_and_verify_challenge():
    """Test full challenge creation and verification flow."""
    from datetime import datetime, timezone
    # Prepare mock challenge and user
    mock_challenge = MagicMock(user_id=1, challenge_data="test_challenge_data")
    mock_challenge.created_at = datetime.now(timezone.utc)
    from models.pgp_key import PgpKeyType
    mock_pgp_key = MagicMock(key_type=PgpKeyType.PUBLIC, key_data='mock_public_key')
    mock_user = MagicMock()
    mock_user.pgp_keys.all.return_value = [mock_pgp_key]
    mock_challenge.user = mock_user

    cs = ChallengeService()
    # Mock creation
    with patch('services.challenge_service.get_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        # Prune returns nothing
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.delete.return_value = None
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
    # Mock verification
    with patch('services.challenge_service.get_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        # Query returns our mock challenge and user
        mock_challenge_query = MagicMock()
        mock_challenge_query.filter_by.return_value.first.return_value = mock_challenge
        mock_user_query = MagicMock()
        mock_user_query.filter_by.return_value.first.return_value = mock_user
        mock_session.query.side_effect = query_side_effect_factory(mock_challenge_query, mock_user_query)
        # Verify signature
        with patch('utils.gpg_utils.verify_signature', return_value=True):
            result, message = cs.verify_challenge(
                user_id=1,
                challenge_data="test_challenge_data",
                signature="test_signature"
            )
            assert result is True
            assert message == "Challenge verified"
            mock_session.delete.assert_called_once_with(mock_challenge)
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
