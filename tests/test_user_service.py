import os
import sys
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
    monkeypatch.setattr("services.auth_service.verify_password", lambda p, h: p == "password" and h == "hashedpassword")

    service = UserService()
    user, _ = service.login_user(username="testuser", password="password")

    assert user is not None, "User should not be None"
    assert cast(MockUser, user).username == "testuser"

    user, error = service.login_user(username="testuser", password="wrongpassword")
    assert user is None
    assert error == "Invalid credentials"

def test_register_and_login_user(monkeypatch):
    # Mock User class to ensure it has password_hash attribute
    class MockUser:
        def __init__(self, username, password_hash=None, api_key=None):
            self.id = None
            self.username = username
            self.password_hash = password_hash
            self.api_key = api_key
    
    monkeypatch.setattr('models.user.User', MockUser)
    
    # Mock DB session
    class DummySession:
        def __init__(self):
            self.users = {}
            self.pgp_keys = []
            self.committed = False
        def query(self, model):
            parent = self
            class Q:
                def __init__(self):
                    self.parent = parent
                def filter_by(self, **kwargs):
                    if model is MockUser:
                        username = kwargs.get('username')
                        return DummyResult(self.parent.users.get(username))
                    if model is PgpKey:
                        user_id = kwargs.get('user_id')
                        key_type = kwargs.get('key_type')
                        for k in self.parent.pgp_keys:
                            if k.user_id == user_id and k.key_type == key_type:
                                return DummyResult(k)
                        return DummyResult(None)
            return Q()
        def add(self, obj):
            if isinstance(obj, User):
                obj.id = len(self.users) + 1  # Set ID for the user
                self.users[obj.username] = obj
            if isinstance(obj, PgpKey):
                self.pgp_keys.append(obj)
        def commit(self):
            self.committed = True
        def close(self):
            pass
        def refresh(self, obj):
            if isinstance(obj, User):
                # Make sure the user has all required attributes
                if not hasattr(obj, 'password_hash'):
                    obj.password_hash = hash_password('pw')
    class DummyResult:
        def __init__(self, val):
            self.val = val
        def first(self):
            return self.val
    monkeypatch.setattr('db.database.get_session', lambda: DummySession())
    sys.path.insert(0, '.')
    app_mod = importlib.import_module('app')
    app = app_mod.app
    with app.app_context():
        us = UserService()
        user, keypair = us.register_user('alice', 'pw', 'PUB', 'PRIV')
        assert user is not None, "register_user returned None for user"
        assert cast(User, user).username == 'alice'
        user2, _ = us.login_user('alice', 'pw')
        assert user2 is not None
        user2 = cast(User, user2)
        assert user2.username == 'alice'
        assert user2.username == 'alice'
        user3, err = us.login_user('alice', 'wrong')
        assert user3 is None
        assert err == 'Invalid credentials'
        user4, err = us.register_user('alice', 'pw', 'PUB', 'PRIV')
        assert user4 is None
        assert err == 'Username already exists'
