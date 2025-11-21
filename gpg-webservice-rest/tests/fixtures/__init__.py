"""Test fixtures for GPG keys and test data."""
import os

def get_fixture_path(filename):
    """Get the absolute path to a fixture file."""
    return os.path.join(os.path.dirname(__file__), filename)

def load_test_key(username, key_type):
    """Load a test GPG key from fixtures.
    
    Args:
        username: 'alice' or 'bob'
        key_type: 'public' or 'private'
    
    Returns:
        str: The GPG key content
    """
    filename = f"{username}_{key_type}_key.asc"
    filepath = get_fixture_path(filename)
    with open(filepath, 'r') as f:
        return f.read()

def get_test_users():
    """Get test user data with their GPG keys."""
    return {
        'alice': {
            'username': 'alice',
            'password': 'testpass',
            'email': 'alice@example.com',
            'public_key': load_test_key('alice', 'public'),
            'private_key': load_test_key('alice', 'private'),
            'passphrase': None  # Alice's key has no passphrase
        },
        'bob': {
            'username': 'bob',
            'password': 'builder',
            'email': 'bob@example.com',
            'public_key': load_test_key('bob', 'public'),
            'private_key': load_test_key('bob', 'private'),
            'passphrase': 'builder'  # Bob's key is protected with passphrase
        }
    }
