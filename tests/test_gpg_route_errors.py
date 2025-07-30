
import os
import sys
import tempfile
import pytest
from flask import Flask
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db.database import db
from routes.user_routes import user_bp
from routes.gpg_routes import gpg_bp

def create_test_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database before registering blueprints
    db.init_app(app)
    with app.app_context():
        db.create_all()
    
    app.register_blueprint(user_bp)
    app.register_blueprint(gpg_bp)
    return app

@pytest.fixture
def client():
    app = create_test_app()
    with app.test_client() as client:
        with app.app_context():
            yield client

def register_user(client, username, password):
    rv = client.post('/register', json={
        'username': username, 
        'password': password,
        'email': f'{username}@example.com'
    })
    assert rv.status_code == 201
    data = rv.get_json()
    return data['api_key'], data['public_key']

def test_sign_with_invalid_private_key(client):
    api_key, _ = register_user(client, 'gpgerr1', 'Password123!')
    # Patch the user's private key to be invalid
    from models.pgp_key import PgpKey, PgpKeyType
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(username='gpgerr1').first()
        if user:
            privkey = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
            if privkey:
                privkey.key_data = 'INVALID_PRIVATE_KEY'
                db.session.commit()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'data')
        f.flush()
        fname = f.name
    with open(fname, 'rb') as f:
        rv = client.post('/sign', data={'file': (f, 'test.txt')}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 500
    assert 'error' in rv.get_json()
    os.unlink(fname)

def test_encrypt_with_invalid_public_key(client):
    api_key, pubkey = register_user(client, 'gpgerr2', 'Password123!')
    # Use an invalid public key for encryption
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'data')
        f.flush()
        fname = f.name
    with tempfile.NamedTemporaryFile(delete=False) as pubf:
        pubf.write(b'INVALID_PUBLIC_KEY')
        pubf.flush()
        pubfname = pubf.name
    with open(fname, 'rb') as f, open(pubfname, 'rb') as pubf:
        rv = client.post('/encrypt', data={'file': (f, 'test.txt'), 'pubkey': (pubf, 'pubkey.asc')}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 500
    assert 'error' in rv.get_json()
    os.unlink(fname)
    os.unlink(pubfname)

def test_decrypt_with_invalid_private_key(client):
    api_key, pubkey = register_user(client, 'gpgerr3', 'Password123!')
    # Encrypt a file with a valid public key
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'data')
        f.flush()
        fname = f.name
    with tempfile.NamedTemporaryFile(delete=False) as pubf:
        pubf.write(pubkey.encode())
        pubf.flush()
        pubfname = pubf.name
    with open(fname, 'rb') as f, open(pubfname, 'rb') as pubf:
        rv = client.post('/encrypt', data={'file': (f, 'test.txt'), 'pubkey': (pubf, 'pubkey.asc')}, headers={'X-API-KEY': api_key})
    encrypted_data = rv.data
    # Patch the user's private key to be invalid
    from models.pgp_key import PgpKey, PgpKeyType
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(username='gpgerr3').first()
        if user:
            privkey = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
            if privkey:
                privkey.key_data = 'INVALID_PRIVATE_KEY'
                db.session.commit()
    with tempfile.NamedTemporaryFile(delete=False) as encf:
        encf.write(encrypted_data)
        encf.flush()
        encfname = encf.name
    with open(encfname, 'rb') as encf:
        rv = client.post('/decrypt', data={'file': (encf, 'test.txt.gpg')}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 500
    assert 'error' in rv.get_json()
    os.unlink(fname)
    os.unlink(pubfname)
    os.unlink(encfname)

def test_verify_with_invalid_signature(client):
    api_key, pubkey = register_user(client, 'gpgerr4', 'Password123!')
    # Create a valid file and public key, but use an invalid signature
    with tempfile.NamedTemporaryFile(delete=False) as sigf:
        sigf.write(b'INVALID_SIGNATURE')
        sigf.flush()
        sigfname = sigf.name
    with tempfile.NamedTemporaryFile(delete=False) as pubf:
        pubf.write(pubkey.encode())
        pubf.flush()
        pubfname = pubf.name
    with open(sigfname, 'rb') as sigf, open(pubfname, 'rb') as pubf:
        rv = client.post('/verify', data={'file': (sigf, 'test.txt.asc'), 'pubkey': (pubf, 'pubkey.asc')}, headers={'X-API-KEY': api_key})
    assert rv.status_code == 500 or rv.get_json().get('verified') is False
    os.unlink(sigfname)
    os.unlink(pubfname)
