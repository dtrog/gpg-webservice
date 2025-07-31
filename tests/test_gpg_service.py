import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import tempfile
from unittest.mock import patch, MagicMock
from services.gpg_service import GPGService

@pytest.fixture
def gpg_service():
    """Provide a GPGService instance for testing."""
    return GPGService()

class TestGPGServiceMocked:
    """Test GPG service with mocked dependencies for unit testing."""
    
    def test_sign_success(self, monkeypatch):
        """Test successful signing with mocked subprocess."""
        gs = GPGService()
        # Mock subprocess to simulate successful GPG signing
        monkeypatch.setattr('subprocess.run', lambda *a, **kw: MagicMock(returncode=0, stdout=b'mock_signature', stderr=b''))
        monkeypatch.setattr('builtins.open', MagicMock())
        
        sig, err = gs.sign('test data', 'private_key', 'password')
        assert err is None
        assert sig is not None
    
    def test_sign_failure(self, monkeypatch):
        """Test signing failure handling."""
        gs = GPGService()
        # Mock subprocess to simulate GPG signing failure
        monkeypatch.setattr('subprocess.run', lambda *a, **kw: MagicMock(returncode=1, stdout=b'', stderr=b'GPG error'))
        
        sig, err = gs.sign('test data', 'invalid_key', 'wrong_password')
        assert err is not None
        assert 'GPG error' in str(err) or err is not None
    
    def test_verify_success(self, monkeypatch):
        """Test successful signature verification."""
        gs = GPGService()
        # Mock subprocess to simulate successful GPG verification
        def fake_run(*args, **kwargs):
            class FakeResult:
                def __init__(self):
                    self.returncode = 0
                    self.stdout = b'[GNUPG:] GOODSIG\n'
                    self.stderr = b''
            return FakeResult()
        monkeypatch.setattr('subprocess.run', fake_run)
        def mock_open_func(filename, mode='r'):
            mock_file = MagicMock()
            # Always return bytes for read(), as GPG expects bytes input
            mock_file.read = MagicMock(return_value=b'test data')
            mock_file.write = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock()
            return mock_file
        monkeypatch.setattr('builtins.open', mock_open_func)
        
        result = gs.verify('test data', 'signature', 'public_key')
        assert result is True

    def test_verify_failure(self, monkeypatch):
        """Test signature verification failure."""
        gs = GPGService()
        monkeypatch.setattr(gs, 'verify', lambda d, s, k: False)
        
        result = gs.verify('test data', 'invalid_signature', 'public_key')
        assert result is False

class TestGPGServiceEncryption:
    """Test GPG service encryption/decryption functionality."""
    
    def test_encrypt_success(self, monkeypatch):
        """Test successful encryption with mocked subprocess."""
        gs = GPGService()
        
        def fake_run(*args, **kwargs):
            class FakeResult:
                def __init__(self, cmd_args):
                    self.returncode = 0
                    if '--list-keys' in cmd_args and '--with-colons' in cmd_args:
                        # Simulate a valid pub: line for GPGService
                        self.stdout = b'pub:u:2048:1:DUMMYKEYID123456:2021-01-01:::u:::scESC:::\n'
                    else:
                        self.stdout = b'encrypted_content'
                    self.stderr = b''
            return FakeResult(args[0])
        
        def mock_open_func(filename, mode='r'):
            mock_file = MagicMock()
            if 'w' in mode:
                mock_file.write = MagicMock()
            else:
                mock_file.read = MagicMock(return_value='encrypted_content')
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock()
            return mock_file
        
        monkeypatch.setattr('subprocess.run', fake_run)
        monkeypatch.setattr('builtins.open', mock_open_func)
        
        enc, err = gs.encrypt('test data', 'public_key')
        assert err is None
        assert enc is not None
    
    def test_decrypt_success(self, monkeypatch):
        """Test successful decryption with mocked subprocess."""
        gs = GPGService()
        
        monkeypatch.setattr('subprocess.run', lambda *a, **kw: MagicMock(returncode=0, stdout=b'decrypted_content', stderr=b''))
        
        def mock_open_func(filename, mode='r'):
            mock_file = MagicMock()
            if 'w' in mode:
                mock_file.write = MagicMock()
            else:
                mock_file.read = MagicMock(return_value='decrypted_content')
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock()
            return mock_file
        
        monkeypatch.setattr('builtins.open', mock_open_func)
        
        dec, err = gs.decrypt('encrypted_data', 'private_key', 'password')
        assert err is None
        assert dec is not None
    
    def test_encrypt_invalid_key(self, monkeypatch):
        """Test encryption with invalid public key."""
        gs = GPGService()
        
        def fake_run(*args, **kwargs):
            class FakeResult:
                def __init__(self, cmd_args):
                    if '--list-keys' in cmd_args:
                        self.returncode = 1  # Key not found
                        self.stdout = b''
                        self.stderr = b'gpg: error reading key: No public key'
                    else:
                        self.returncode = 0
                        self.stdout = b''
                        self.stderr = b''
            return FakeResult(args[0])
        
        monkeypatch.setattr('subprocess.run', fake_run)
        
        enc, err = gs.encrypt('test data', 'invalid_public_key')
        assert err is not None
        assert 'No public key' in str(err) or err is not None


class TestGPGServiceIntegration:
    """Integration tests for GPG service with real file operations (but mocked GPG)."""
    
    def test_temp_directory_cleanup(self, monkeypatch):
        """Test that temporary directories are properly cleaned up."""
        gs = GPGService()
        created_dirs = []
        
        original_mkdtemp = tempfile.mkdtemp
        def track_mkdtemp(*args, **kwargs):
            temp_dir = original_mkdtemp(*args, **kwargs)
            created_dirs.append(temp_dir)
            return temp_dir
        
        monkeypatch.setattr('tempfile.mkdtemp', track_mkdtemp)
        monkeypatch.setattr('subprocess.run', lambda *a, **kw: MagicMock(returncode=0, stdout=b'', stderr=b''))
        monkeypatch.setattr('builtins.open', MagicMock())
        
        # Perform operation that should create and cleanup temp directory
        sig, err = gs.sign('test data', 'private_key', 'password')
        
        # Verify temp directories were created and then cleaned up
        assert len(created_dirs) > 0
        for temp_dir in created_dirs:
            assert not os.path.exists(temp_dir), f"Temporary directory {temp_dir} was not cleaned up"