"""
Centralized pytest configuration for GPG webservice tests.

This module provides standardized fixtures and utilities for all test modules,
ensuring consistent database setup, client configuration, and resource cleanup.
"""

import pytest
import os
import sys
import tempfile
from sqlalchemy import text

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask
from db.database import db
from models.user import User
from models.pgp_key import PgpKey, PgpKeyType
from models.challenge import Challenge


@pytest.fixture(scope="function")
def app():
    """
    Create a Flask app for testing with fresh in-memory database.
    
    This fixture ensures each test gets a clean database state and proper
    Flask application context. The database is created and torn down for
    each test function to ensure isolation.
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Register blueprints for route testing
    from routes.user_routes import user_bp
    from routes.gpg_routes import gpg_bp
    from routes.openai_routes import openai_bp
    
    app.register_blueprint(user_bp)
    app.register_blueprint(gpg_bp)
    app.register_blueprint(openai_bp)
    
    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app
        # Clean teardown
        db.session.remove()
        # Disable foreign key checks to avoid constraint errors during drop
        try:
            db.session.execute(text("PRAGMA foreign_keys = OFF"))
        except Exception:
            pass
        db.drop_all()
        # Re-enable foreign key checks
        try:
            db.session.execute(text("PRAGMA foreign_keys = ON"))
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session(app):
    """
    Provide a database session for tests.
    
    Uses the same app context and provides access to the database session
    for direct database operations in tests.
    """
    with app.app_context():
        yield db.session


@pytest.fixture(scope="function")
def client(app):
    """
    Create a test client for HTTP endpoint testing.
    
    Returns Flask test client configured for the test application,
    ready for making HTTP requests in tests.
    """
    return app.test_client()


def register_test_user(client, username='testuser', password='TestPass123!', email='test@example.com'):
    """
    Register a test user via HTTP endpoint.
    
    Args:
        client: Flask test client
        username: Username for the test user
        password: Password for the test user  
        email: Email for the test user (if required by endpoint)
    
    Returns:
        Flask response object from registration request
    """
    response = client.post('/register', 
                          json={
                              'username': username,
                              'password': password,
                              'email': email
                          },
                          content_type='application/json')
    return response


def create_test_user_with_keys(db_session, username='testuser', api_key='test_api_key', public_key_data='mock_public_key', private_key_data='mock_private_key'):
    """
    Create a test user with PGP keys directly in database.
    
    Args:
        db_session: Database session fixture
        username: Username for the test user
        api_key: API key for the test user
        public_key_data: Public key data for the test user
        private_key_data: Private key data for the test user
    
    Returns:
        Tuple of (user, public_key, private_key) objects
    """
    user = User(username=username, password_hash='hashed_password', api_key=api_key)
    db_session.add(user)
    db_session.commit()
    
    public_key = PgpKey(user_id=user.id, key_type=PgpKeyType.PUBLIC, key_data=public_key_data)
    private_key = PgpKey(user_id=user.id, key_type=PgpKeyType.PRIVATE, key_data=private_key_data)
    
    db_session.add(public_key)
    db_session.add(private_key)
    db_session.commit()
    
    return user, public_key, private_key


@pytest.fixture
def temp_file():
    """
    Create a temporary file for testing file operations.
    
    Yields the file path and ensures proper cleanup after test completion.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(b'test data')
        tmp_file.flush()
        yield tmp_file.name
    
    # Cleanup
    try:
        os.unlink(tmp_file.name)
    except OSError:
        pass  # File may already be deleted
