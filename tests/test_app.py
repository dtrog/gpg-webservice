import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile
import pytest
from app import app, init_db

def test_get_public_key(client):
    api_key, pubkey = register_user(client, 'bob', 'builder', 'bob@example.com')
    rv = client.get('/get_public_key', headers={'X-API-KEY': api_key})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'public_key' in data
    assert data['public_key'] == pubkey

def test_get_api_key(client):
    api_key, _ = register_user(client, 'bob', 'builder', 'bob@example.com')
    api_key2 = login_user(client, 'bob', 'builder')
    assert api_key2 == api_key

@pytest.fixture
def client():
    # Create a fresh Flask app for testing
    from flask import Flask
    from db.database import db
    
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Import and register routes
    from routes.user_routes import user_bp
    from routes.gpg_routes import gpg_bp
    test_app.register_blueprint(user_bp)
    test_app.register_blueprint(gpg_bp)
    
    with test_app.test_client() as client:
        with test_app.app_context():
            db.init_app(test_app)
            db.create_all()
        yield client


def register_user(client, username, password, email=None):
    # Let the system generate keys automatically with API key as passphrase
    rv = client.post('/register', json={
        'username': username,
        'password': password,
        'email': email or f'{username}@example.com'
        # No public_key/private_key provided - let system generate them
    })
    assert rv.status_code == 201  # Registration should return 201 Created
    data = rv.get_json()
    return data['api_key'], data['public_key']

def login_user(client, username, password):
    rv = client.post('/login', json={
        'username': username,
        'password': password
    })
    assert rv.status_code == 200
    return rv.get_json()['api_key']

def test_register(client):
    api_key, pubkey = register_user(client, 'bob', 'builder', 'bob@example.com')
    assert api_key
    assert pubkey

def test_login(client):
    api_key, _ = register_user(client, 'bob', 'builder', 'bob@example.com')
    api_key2 = login_user(client, 'bob', 'builder')
    assert api_key2 == api_key

def test_sign(client):
    api_key, _ = register_user(client, 'bob', 'builder', 'bob@example.com')
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'goodbye world')
        f.flush()
        fname = f.name
    with open(fname, 'rb') as f:
        rv = client.post('/sign', data={
            'file': (f, 'test.txt')
        }, headers={'X-API-KEY': api_key})
    assert rv.status_code == 200
    os.unlink(fname)

def test_verify(client):
    api_key, pubkey = register_user(client, 'bob', 'builder', 'bob@example.com')
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'goodbye world')
        f.flush()
        fname = f.name
    with open(fname, 'rb') as f:
        rv = client.post('/sign', data={
            'file': (f, 'test.txt')
        }, headers={'X-API-KEY': api_key})
    signed_data = rv.data
    with tempfile.NamedTemporaryFile(delete=False) as sigf:
        sigf.write(signed_data)
        sigf.flush()
        sigfname = sigf.name
    with tempfile.NamedTemporaryFile(delete=False) as pubf:
        pubf.write(pubkey.encode())
        pubf.flush()
        pubfname = pubf.name
    with open(sigfname, 'rb') as sigf, open(pubfname, 'rb') as pubf:
        rv = client.post('/verify', data={
            'file': (sigf, 'test.txt.asc'),
            'pubkey': (pubf, 'pubkey.asc')
        }, headers={'X-API-KEY': api_key})
    assert rv.status_code == 200
    assert rv.get_json()['verified'] is True
    os.unlink(fname)
    os.unlink(sigfname)
    os.unlink(pubfname)

def test_encrypt(client):
    api_key, pubkey = register_user(client, 'bob', 'builder', 'bob@example.com')
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'goodbye world')
        f.flush()
        fname = f.name
    with tempfile.NamedTemporaryFile(delete=False) as pubf:
        pubf.write(pubkey.encode())
        pubf.flush()
        pubfname = pubf.name
    with open(fname, 'rb') as f, open(pubfname, 'rb') as pubf:
        rv = client.post('/encrypt', data={
            'file': (f, 'test.txt'),
            'pubkey': (pubf, 'pubkey.asc')
        }, headers={'X-API-KEY': api_key})
        if rv.status_code != 200:
            print('ENCRYPT ERROR:', rv.get_json())
    assert rv.status_code == 200
    encrypted_data = rv.data
    with tempfile.NamedTemporaryFile(delete=False) as encf:
        encf.write(encrypted_data)
        encf.flush()
        encfname = encf.name
    os.unlink(fname)
    os.unlink(pubfname)
    os.unlink(encfname)

def test_decrypt(client):
    api_key, pubkey = register_user(client, 'bob', 'builder', 'bob@example.com')
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'goodbye world')
        f.flush()
        fname = f.name
    with tempfile.NamedTemporaryFile(delete=False) as pubf:
        pubf.write(pubkey.encode())
        pubf.flush()
        pubfname = pubf.name
    with open(fname, 'rb') as f, open(pubfname, 'rb') as pubf:
        rv = client.post('/encrypt', data={
            'file': (f, 'test.txt'),
            'pubkey': (pubf, 'pubkey.asc')
        }, headers={'X-API-KEY': api_key})
    encrypted_data = rv.data
    with tempfile.NamedTemporaryFile(delete=False) as encf:
        encf.write(encrypted_data)
        encf.flush()
        encfname = encf.name
    with open(encfname, 'rb') as encf:
        rv = client.post('/decrypt', data={
            'file': (encf, 'test.txt.gpg')
        }, headers={'X-API-KEY': api_key})
    assert rv.status_code == 200
    os.unlink(fname)
    os.unlink(pubfname)
    os.unlink(encfname)
