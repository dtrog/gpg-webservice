
import os
import sys
import tempfile
import pytest
from flask import Flask
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db.database import db

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Import blueprints
from routes.user_routes import user_bp
from routes.gpg_routes import gpg_bp

def create_test_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.register_blueprint(user_bp)
    app.register_blueprint(gpg_bp)
    with app.app_context():
        db.init_app(app)
        db.create_all()
    return app

@pytest.fixture
def client():
    app = create_test_app()
    with app.test_client() as client:
        yield client

def test_register_missing_fields(client):
    rv = client.post('/register', json={})
    assert rv.status_code == 400
    assert 'error' in rv.get_json()

def test_login_missing_fields(client):
    rv = client.post('/login', json={})
    assert rv.status_code == 401 or rv.status_code == 400
    assert 'error' in rv.get_json()

def test_register_duplicate_user(client):
    client.post('/register', json={'username': 'alice', 'password': 'pw'})
    rv = client.post('/register', json={'username': 'alice', 'password': 'pw'})
    assert rv.status_code == 400
    assert 'error' in rv.get_json()

def test_login_invalid_user(client):
    rv = client.post('/login', json={'username': 'nouser', 'password': 'pw'})
    assert rv.status_code == 401
    assert 'error' in rv.get_json()

def test_sign_requires_api_key(client):
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'data')
        f.flush()
        fname = f.name
    with open(fname, 'rb') as f:
        rv = client.post('/sign', data={'file': (f, 'test.txt')})
    assert rv.status_code == 401
    os.unlink(fname)

def test_sign_invalid_api_key(client):
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'data')
        f.flush()
        fname = f.name
    with open(fname, 'rb') as f:
        rv = client.post('/sign', data={'file': (f, 'test.txt')}, headers={'X-API-KEY': 'badkey'})
    assert rv.status_code == 403
    os.unlink(fname)

def test_encrypt_missing_fields(client):
    api_key = client.post('/register', json={'username': 'bob', 'password': 'pw'}).get_json()['api_key']
    rv = client.post('/encrypt', data={}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 400
    assert 'error' in rv.get_json()

def test_decrypt_missing_fields(client):
    api_key = client.post('/register', json={'username': 'bob2', 'password': 'pw'}).get_json()['api_key']
    rv = client.post('/decrypt', data={}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 400
    assert 'error' in rv.get_json()

def test_get_public_key_requires_api_key(client):
    rv = client.get('/get_public_key')
    assert rv.status_code == 401
    assert 'error' in rv.get_json()

def test_get_public_key_invalid_api_key(client):
    rv = client.get('/get_public_key', headers={'X-API-KEY': 'badkey'})
    assert rv.status_code == 403
    assert 'error' in rv.get_json()

def test_challenge_requires_api_key(client):
    rv = client.post('/challenge')
    assert rv.status_code == 401
    assert 'error' in rv.get_json()

def test_challenge_invalid_api_key(client):
    rv = client.post('/challenge', headers={'X-API-KEY': 'badkey'})
    assert rv.status_code == 403
    assert 'error' in rv.get_json()

def test_verify_challenge_missing_fields(client):
    api_key = client.post('/register', json={'username': 'eve', 'password': 'pw'}).get_json()['api_key']
    rv = client.post('/verify_challenge', json={}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 400
    assert 'error' in rv.get_json()
