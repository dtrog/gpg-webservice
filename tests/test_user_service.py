import os
import sys

import pytest

# Ensure project root is in sys.path for imports
@pytest.fixture(scope="session", autouse=True)
def add_project_root_to_syspath():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


from flask import Flask
from services.user_service import UserService
from db.database import init_db
from typing import cast

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

class MockResult:
    def __init__(self, result):
        self.result = result
    def first(self):
        return self.result

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
        if hasattr(obj, 'username'):
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
def app_context(app: Flask):
    with app.app_context():
        yield

def test_register_user(monkeypatch: pytest.MonkeyPatch):
    """Test user registration with simplified mocking."""

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

def test_login_user(monkeypatch: pytest.MonkeyPatch):
    """Test user login with simplified mocking."""

    class MockSessionLogin(MockSession):
        def __init__(self):
            super().__init__()
            self.users = {
                "testuser": MockUser(username="testuser", password_hash="hashedpassword", api_key="mockkey")
            }

    monkeypatch.setattr("db.database.get_session", lambda: MockSessionLogin())
    def mock_verify_password(password, password_hash):
        return password == "password" and password_hash == "hashedpassword"

    monkeypatch.setattr("services.auth_service.verify_password", mock_verify_password)

    service = UserService()
    user, _ = service.login_user(username="testuser", password="password")

    assert user is not None, "User should not be None"
    assert cast(MockUser, user).username == "testuser"

    from unittest.mock import Mock, patch
    from models.user import User
    # Mock user storage
    users_db = {}

def test_register_and_login_user(monkeypatch: pytest.MonkeyPatch):
    """Test user registration and login with simplified mocking."""
    from unittest.mock import Mock, patch
    from models.user import User
    # Mock user storage
    users_db = {}
    def mock_generate_gpg_keypair(name, email, passphrase):
        return "MOCK_PUBLIC_KEY", "MOCK_PRIVATE_KEY"
    
    # Use patch instead of monkeypatch for better control
    with patch('utils.gpg_utils.generate_gpg_keypair', mock_generate_gpg_keypair):
        from services.user_service import UserService
        from flask import Flask
        from db.database import init_db

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        with app.app_context():
            init_db(app)
            us = UserService()
            
            # Test user registration with unique username
            import uuid
            from typing import cast  # added import
            unique_user = f"testuser_{str(uuid.uuid4())[:8]}"
            user, result = us.register_user(unique_user, 'testpass', 'PUBLIC_KEY_DATA', 'PRIVATE_KEY_DATA')
            assert user is not None, f"Registration should succeed, got error: {result}"
            assert cast(User, user).username == unique_user
            assert hasattr(user, 'api_key')
            assert cast(User, user).api_key is not None
            
            # Test successful login
            user2, keypair2 = us.login_user(unique_user, 'testpass')
            assert user2 is not None, "Login should succeed"
            assert cast(User, user2).username == unique_user
            
            # Test failed login with wrong password
            user3, err = us.login_user(unique_user, 'wrongpass')
            assert user3 is None
            assert err == 'Invalid credentials'
            
            # Test duplicate registration
            user4, err = us.register_user(unique_user, 'testpass', 'PUB', 'PRIV')
            assert user4 is None
            assert err == 'Username already exists'
