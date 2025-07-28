#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '.')

# Test if the patching works
def test_simple():
    import importlib
    from unittest.mock import Mock, patch
    
    # Mock user storage
    users_db = {}
    
    # Create a simple mock session
    mock_session = Mock()
    mock_query = Mock()
    mock_filter_by = Mock()
    mock_result = Mock()
    
    # Setup the chain: session.query().filter_by().first()
    mock_result.first.return_value = None  # No existing user
    mock_filter_by.return_value = mock_result
    mock_query.filter_by = mock_filter_by
    mock_session.query.return_value = mock_query
    
    # Mock other session methods
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.refresh = Mock()
    mock_session.close = Mock()
    
    # Mock GPG key generation
    def mock_generate_gpg_keypair(name, email, passphrase):
        return "MOCK_PUBLIC_KEY", "MOCK_PRIVATE_KEY"
    
    with patch('db.database.get_session', return_value=mock_session):
        with patch('utils.gpg_utils.generate_gpg_keypair', mock_generate_gpg_keypair):
            app_mod = importlib.import_module('app')
            app = app_mod.app
            
            with app.app_context():
                from services.user_service import UserService
                us = UserService()
                
                user, result = us.register_user('alice', 'testpass', 'PUBLIC_KEY_DATA', 'PRIVATE_KEY_DATA')
                print(f"Result: user={user}, result={result}")
                print(f"Session.query called: {mock_session.query.called}")
                print(f"Session.add called: {mock_session.add.called}")
                print(f"Session.commit called: {mock_session.commit.called}")

if __name__ == "__main__":
    test_simple()
