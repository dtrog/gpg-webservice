import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import User, PgpKey, PgpKeyPair, Challenge
from datetime import datetime, timezone

def test_user_model_init():
    user = User(username='alice', password_hash='hash', api_key='key123')
    assert user.username == 'alice'
    assert user.password_hash == 'hash'
    assert user.api_key == 'key123'

def test_pgpkey_model_init():
    user = User(username='bob2', password_hash='hash2')
    key = PgpKey(user_id=1, key_type='public', key_data='PUBKEYDATA', user=user)
    assert key.user_id == 1
    assert key.key_type == 'public'
    assert key.key_data == 'PUBKEYDATA'
    assert key.user == user

def test_pgpkeypair():
    user = User(username='bob', password_hash='hash')
    pub = PgpKey(user_id=1, key_type='public', key_data='PUB', user=user)
    priv = PgpKey(user_id=1, key_type='private', key_data='PRIV', user=user)
    pair = PgpKeyPair(pub, priv)
    assert pair.public_key == pub
    assert pair.private_key == priv
    pair = PgpKeyPair(pub, priv)
    assert pair.public_key == pub
    assert pair.private_key == priv

def test_apikey_model_init():
    user = User(username='carol', password_hash='hash3', api_key='apikey123')
    assert user.api_key == 'apikey123'

def test_challenge_model_init():
    user = User(username='dave', password_hash='hash4')
    # Simulate user.id assignment as would happen in a real DB session
    user.id = 3
    now = datetime.now(timezone.utc)
    challenge = Challenge(user_id=user.id, challenge_data='challenge', signature='sig', user=user, created_at=now)
    assert challenge.user_id == user.id
    assert challenge.challenge_data == 'challenge'
    assert challenge.signature == 'sig'
    assert challenge.user == user
    assert isinstance(challenge.created_at, datetime)
    assert challenge.created_at.tzinfo is not None
