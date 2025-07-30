import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from flask import Flask
from unittest.mock import patch, MagicMock
from services.gpg_service import GPGService
from db.database import init_db

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

@pytest.fixture
def gpg_service():
    return GPGService()

def test_gpg_service_sign_verify(monkeypatch):
    gs = GPGService()
    # Patch subprocess and file I/O
    monkeypatch.setattr('subprocess.run', lambda *a, **kw: MagicMock(returncode=0, stdout=b'', stderr=b''))
    monkeypatch.setattr('builtins.open', MagicMock())
    sig, err = gs.sign('data', 'priv', 'pw')
    assert err is None
    monkeypatch.setattr('utils.gpg_utils.verify_signature', lambda d, s, k: True)
    assert gs.verify('data', 'sig', 'pub')

def test_gpg_service_encrypt_decrypt(monkeypatch):
    gs = GPGService()
    # Patch subprocess.run to simulate key id extraction and encryption
    def fake_run(*args, **kwargs):
        class FakeResult:
            def __init__(self, cmd_args):
                self.returncode = 0
                if '--list-keys' in cmd_args and '--with-colons' in cmd_args:
                    # Simulate a valid pub: line for GPGService (format: pub:trust:length:algo:keyid:...)
                    self.stdout = b'pub:u:2048:1:DUMMYKEYID123456:2021-01-01:::u:::scESC:::\n'
                else:
                    self.stdout = b''
                self.stderr = b''
        return FakeResult(args[0])
    
    # Mock file operations to simulate successful file creation/reading
    mock_file_content = ""
    def mock_open_func(filename, mode='r'):
        mock_file = MagicMock()
        if 'w' in mode:
            mock_file.write = MagicMock()
        else:
            mock_file.read = MagicMock(return_value=mock_file_content)
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock()
        return mock_file
    
    monkeypatch.setattr('subprocess.run', fake_run)
    monkeypatch.setattr('builtins.open', mock_open_func)
    
    enc, err = gs.encrypt('data', 'pub')
    assert err is None
    dec, err = gs.decrypt('data', 'priv', 'pw')
    assert err is None
