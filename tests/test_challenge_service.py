import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from flask import Flask
from services.challenge_service import ChallengeService
from models.challenge import Challenge
from db.database import init_db
from unittest.mock import patch, MagicMock
import sys
import importlib

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

def test_create_challenge(monkeypatch):
    class MockSession:
        def __init__(self):
            self.challenges = []

        def add(self, obj):
            self.challenges.append(obj)

        def commit(self):
            pass

        def query(self, model):
            class MockQuery:
                def __init__(self, challenges):
                    self.challenges = challenges
                    
                def filter_by(self, **kwargs):
                    for challenge in self.challenges:
                        if challenge.user_id == kwargs.get("user_id"):
                            return MockResult(challenge)
                    return MockResult(None)

            return MockQuery(self.challenges)

    class MockResult:
        def __init__(self, result):
            self.result = result

        def first(self):
            return self.result

    monkeypatch.setattr("db.database.get_session", lambda: MockSession())

    service = ChallengeService()
    challenge = service.create_challenge(user_id=1)
    assert challenge.user_id == 1
    assert challenge.challenge_data is not None

def test_verify_challenge(monkeypatch):
    class MockSession:
        def __init__(self):
            self.challenges = []

        def query(self, model):
            class MockQuery:
                def __init__(self, challenges):
                    self.challenges = challenges
                    
                def filter_by(self, **kwargs):
                    for challenge in self.challenges:
                        if challenge.user_id == kwargs.get("user_id") and challenge.challenge_data == kwargs.get("challenge_data"):
                            return MockResult(challenge)
                    return MockResult(None)
                
            return MockQuery(self.challenges)
        
        def add(self, obj):
            self.challenges.append(obj)


        def delete(self, obj):
            self.challenges.remove(obj)

        def commit(self):
            pass

        def close(self):
            pass
        

    class MockResult:
        def __init__(self, result):
            self.result = result

        def first(self):
            return self.result
        def all(self):
            return self.result
            

    monkeypatch.setattr("db.database.get_session", lambda: MockSession())
    monkeypatch.setattr("utils.gpg_utils.verify_signature", lambda d, s, k: True)

    service = ChallengeService()
    result, message = service.verify_challenge(user_id=1, challenge_data="data", signature="signature")
    assert result
    assert message == "Challenge verified"

def test_create_and_verify_challenge(monkeypatch):
    # Patch DB session and GPG verify
    class DummySession:
        def __init__(self):
            self.challenges = []
            self.users = {1: DummyUser()}
            self.committed = False
        def query(self, model):
            parent = self
            class Q:
                def __init__(self):
                    self.parent = parent
                def filter_by(self, **kwargs):
                    if model is Challenge:
                        for c in self.parent.challenges:
                            if c.user_id == kwargs.get('user_id') and c.challenge_data == kwargs.get('challenge_data'):
                                return DummyResult(c)
                        return DummyResult(None)
                def filter(self, *args):
                    return DummyResult(None)
                def order_by(self, *args):
                    return self.parent.challenges
            return Q()
        def add(self, obj):
            self.challenges.append(obj)
        def commit(self):
            self.committed = True
        def close(self):
            pass
        def refresh(self, obj):
            pass
        def delete(self, obj):
            self.challenges.remove(obj)
    class DummyUser:
        pgp_keys = [MagicMock(key_type='public', key_data='PUBKEY')]
    class DummyResult:
        def __init__(self, val):
            self.val = val
        def first(self):
            return self.val
        def all(self):
            return self.val
    monkeypatch.setattr('db.database.get_session', lambda: DummySession())
    monkeypatch.setattr('utils.gpg_utils.verify_signature', lambda d, s, k: True)
    sys.path.insert(0, '.')
    app_mod = importlib.import_module('app')
    app = app_mod.app
    with app.app_context():
        cs = ChallengeService()
        challenge = cs.create_challenge(1)
        assert challenge.user_id == 1
        ok, msg = cs.verify_challenge(1, challenge.challenge_data, 'sig')
        assert ok
        assert msg == 'Challenge verified'
