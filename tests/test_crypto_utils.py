import pytest
import base64
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import utils.crypto_utils as crypto_utils
from cryptography.exceptions import InvalidTag

def test_derive_key_length_and_type():
    password = 'testpassword'
    salt = b'0' * 16
    key = crypto_utils.derive_key(password, salt)
    assert isinstance(key, bytes)
    assert len(key) == 32

def test_encrypt_decrypt_private_key_success():
    password = 'strongpassword'
    private_key = b'my super secret key data'
    enc = crypto_utils.encrypt_private_key(private_key, password)
    dec = crypto_utils.decrypt_private_key(enc, password)
    assert dec == private_key

def test_encrypt_private_key_output_structure():
    password = 'pw'
    private_key = b'data'
    enc = crypto_utils.encrypt_private_key(private_key, password)
    # salt (16) + nonce (12) + ciphertext (>=len(data))
    assert len(enc) > 16 + 12
    assert isinstance(enc, bytes)

def test_decrypt_private_key_wrong_password():
    password = 'pw1'
    wrong_password = 'pw2'
    private_key = b'data'
    enc = crypto_utils.encrypt_private_key(private_key, password)
    with pytest.raises(InvalidTag):
        crypto_utils.decrypt_private_key(enc, wrong_password)

def test_generate_api_key_length_and_charset():
    key = crypto_utils.generate_api_key()
    # Should be base64url, 43 chars for 32 bytes, no padding
    assert isinstance(key, str)
    assert 42 <= len(key) <= 44
    # Should be urlsafe base64
    base64.urlsafe_b64decode(key + '==')

def test_generate_api_key_uniqueness():
    keys = {crypto_utils.generate_api_key() for _ in range(100)}
    assert len(keys) == 100
