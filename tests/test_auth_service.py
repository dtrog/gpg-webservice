import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from flask import Flask
from services.auth_service import hash_password, verify_password, get_user_by_api_key
from models.user import User
from unittest.mock import patch
import importlib

@pytest.fixture(autouse=True)
def app_context():
    app = Flask(__name__)
    app.config['TESTING'] = True
    with app.app_context():
        yield

def test_hash_and_verify_password():
    pw = 'secret'
    h = hash_password(pw)
    assert h != pw
    assert verify_password(pw, h)
    assert not verify_password('wrong', h)

def test_get_user_by_api_key(monkeypatch):
    class DummyUser:
        api_key = 'abc123'
    class DummyQuery:
        def filter_by(self, api_key=None):
            if api_key == 'abc123':
                return DummyResult(DummyUser())
            return DummyResult(None)
    class DummyResult:
        def __init__(self, val):
            self.val = val
        def first(self):
            return self.val
    app_mod = importlib.import_module('app')
    app = app_mod.app
    with app.app_context():
        monkeypatch.setattr('models.user.User.query', DummyQuery())
        user = get_user_by_api_key('abc123')
        assert user is not None
        assert user.api_key == 'abc123'
        assert get_user_by_api_key('nope') is None
