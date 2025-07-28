import os
import sys

from utils.crypto_utils import generate_api_key
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from flask import Flask
from services.user_service import UserService
from services.auth_service import hash_password, verify_password
from models.user import User
from models.pgp_key import PgpKey
from db.database import init_db
import sys
import importlib
from typing import cast

# Add a fixture to set up the application context
@pytest.fixture(scope="module")
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.app_context():
        init_db(app)
        yield app

@pytest.fixture(autouse=True)
def app_context(app):
    with app.app_context():
        yield

def test_register_user(monkeypatch):
    class MockUser:
        def __init__(self, username, password_hash, api_key):
            self.id = 1
            self.username = username
            self.password_hash = password_hash
            self.api_key = api_key

    class MockPgpKey:
        def __init__(self, user_id, key_type, key_data):
            self.user_id = user_id
            self.key_type = key_type
            self.key_data = key_data

    class MockSession:
        def __init__(self):
            self.users = {}
            self.next_id = 1

        def query(self, model):
            class MockQuery:
                def __init__(self, parent):
                    self.parent = parent
                def filter_by(self, **kwargs):
                    username = kwargs.get("username")
                    return MockResult(self.parent.users.get(username))
            return MockQuery(self)

        def add(self, obj):
            if hasattr(obj, 'username'):  # User object
                obj.id = self.next_id
                self.next_id += 1
                self.users[obj.username] = obj

        def commit(self):
            pass
            
        def refresh(self, obj):
            pass
        
        def expunge(self, obj):
            pass
        
        def close(self):
            pass

    class MockResult:
        def __init__(self, result):
            self.result = result

        def first(self):
            return self.result

    def mock_user_constructor(*args, **kwargs):
        return MockUser(**kwargs)
    
    def mock_pgpkey_constructor(*args, **kwargs):
        return MockPgpKey(**kwargs)

    monkeypatch.setattr("db.database.get_session", lambda: MockSession())
    monkeypatch.setattr("models.user.User", mock_user_constructor)
    monkeypatch.setattr("models.pgp_key.PgpKey", mock_pgpkey_constructor)

    service = UserService()
    user, _ = service.register_user(username="testuser", password="password", public_key_data="pubkey", private_key_data="privkey")
    assert user is not None, "User should not be None"
    user = cast(MockUser, user)
    assert cast(MockUser, user).username == "testuser"
    assert user.password_hash is not None

def test_login_user(monkeypatch):
    class MockUser:
        def __init__(self, username, password_hash, api_key):
            self.username = username
            self.password_hash = password_hash
            self.api_key = api_key

    class MockSession:
        def __init__(self):
            self.users = {
                "testuser": MockUser(username="testuser", password_hash="hashedpassword", api_key="mockkey")
            }

        def query(self, model):
            class MockQuery:
                def __init__(self, parent):
                    self.parent = parent
                def filter_by(self, **kwargs):
                    username = kwargs.get("username")
                    return MockResult(self.parent.users.get(username))
            return MockQuery(self)

    class MockResult:
        def __init__(self, result):
            self.result = result

        def first(self):
            return self.result

    monkeypatch.setattr("db.database.get_session", lambda: MockSession())
    def mock_verify_password(password, password_hash):
        return password == "password" and password_hash == "hashedpassword"

    monkeypatch.setattr("services.auth_service.verify_password", mock_verify_password)

    service = UserService()
    user, _ = service.login_user(username="testuser", password="password")

    assert user is not None, "User should not be None"
    assert cast(MockUser, user).username == "testuser"

    user, error = service.login_user(username="testuser", password="wrongpassword")
    assert user is None
    assert error == "Invalid credentials"

def test_register_and_login_user(monkeypatch):
    """Test user registration and login with simplified mocking."""
    import sys
    sys.path.insert(0, '.')
    from unittest.mock import Mock, patch
    from models.user import User
    from models.pgp_key import PgpKey
    
    # Mock user storage
    users_db = {}
    
    def mock_generate_gpg_keypair(name, email, passphrase):
        return "MOCK_PUBLIC_KEY", "MOCK_PRIVATE_KEY"
    
    def create_mock_session():
        mock_session = Mock()
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_result = Mock()
        
        # Setup the chain: session.query().filter_by().first()
        def filter_by_func(**kwargs):
            if 'username' in kwargs:
                username = kwargs['username']
                existing_user = users_db.get(username)
                mock_result.first.return_value = existing_user
            elif 'user_id' in kwargs and 'key_type' in kwargs:
                # For PGP key queries, return None (no existing keys)
                mock_result.first.return_value = None
            return mock_result
        
        mock_query.filter_by = filter_by_func
        mock_session.query.return_value = mock_query
        
        # Mock add method to store users
        def add_func(obj):
            if isinstance(obj, User):
                obj.id = len(users_db) + 1
                users_db[obj.username] = obj
            # For PGP keys, just ignore
        
        mock_session.add = add_func
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        mock_session.close = Mock()
        
        return mock_session
    
    # Use patch instead of monkeypatch for better control
    with patch('db.database.get_session', create_mock_session):
        with patch('utils.gpg_utils.generate_gpg_keypair', mock_generate_gpg_keypair):
            from services.user_service import UserService
            import importlib
            app_mod = importlib.import_module('app')
            app = app_mod.app
            
            with app.app_context():
                us = UserService()
                
                # Test user registration with unique username
                import uuid
                unique_user = f"testuser_{str(uuid.uuid4())[:8]}"
                user, result = us.register_user(unique_user, 'testpass', 'PUBLIC_KEY_DATA', 'PRIVATE_KEY_DATA')
                assert user is not None, f"Registration should succeed, got error: {result}"
                assert user.username == unique_user
                assert hasattr(user, 'api_key')
                assert user.api_key is not None
                
                # Test successful login
                user2, keypair2 = us.login_user(unique_user, 'testpass')
                assert user2 is not None, "Login should succeed"
                assert user2.username == unique_user
                
                # Test failed login with wrong password
                user3, err = us.login_user(unique_user, 'wrongpass')
                assert user3 is None
                assert err == 'Invalid credentials'
                
                # Test duplicate registration
                user4, err = us.register_user(unique_user, 'testpass', 'PUB', 'PRIV')
                assert user4 is None
                assert err == 'Username already exists'