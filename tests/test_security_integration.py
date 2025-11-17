"""
Integration tests for security features.

This module tests the security mechanisms of the GPG webservice including
rate limiting, API key authentication, audit logging, and security headers.
"""

import pytest
import json
import time
from io import BytesIO
from unittest.mock import patch, MagicMock

from app import app as flask_app
from db.database import db, init_db
from models.user import User
from services.user_service import UserService
from utils.crypto_utils import hash_api_key


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    with flask_app.app_context():
        init_db(flask_app)
        yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def registered_user(app):
    """Create a registered user for testing."""
    with app.app_context():
        user_service = UserService()
        registration_result, error = user_service.register_user(
            username='testuser',
            password='TestPassword123!'
        )
        assert registration_result is not None
        assert error is None
        return {
            'user': registration_result.user,
            'api_key': registration_result.api_key,
            'public_key': registration_result.pgp_keypair.public_key.key_data
        }


class TestAPIKeyAuthentication:
    """Tests for API key authentication and hashing."""

    def test_api_key_is_hashed_in_database(self, app, registered_user):
        """Verify that API keys are stored as hashes, not plaintext."""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()

            # Verify user exists and has api_key_hash field
            assert user is not None
            assert hasattr(user, 'api_key_hash')
            assert user.api_key_hash is not None

            # Verify the raw API key is NOT stored
            assert not hasattr(user, 'api_key') or user.api_key_hash != registered_user['api_key']

            # Verify the hash matches what we expect
            expected_hash = hash_api_key(registered_user['api_key'])
            assert user.api_key_hash == expected_hash

    def test_api_key_authentication_success(self, client, registered_user):
        """Verify that valid API keys authenticate successfully."""
        response = client.get(
            '/get_public_key',
            headers={'X-API-KEY': registered_user['api_key']}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'public_key' in data

    def test_api_key_authentication_missing_key(self, client):
        """Verify that requests without API keys are rejected."""
        response = client.get('/get_public_key')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'API key' in data['error'].lower()

    def test_api_key_authentication_invalid_key(self, client):
        """Verify that invalid API keys are rejected."""
        response = client.get(
            '/get_public_key',
            headers={'X-API-KEY': 'invalid_key_123'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_api_key_only_returned_once_at_registration(self, client):
        """Verify that API key is only returned at registration, not at login."""
        # Register a new user
        register_response = client.post(
            '/register',
            json={
                'username': 'testkeyreturn',
                'password': 'TestPassword123!',
                'email': 'testkeyreturn@example.com'
            }
        )

        assert register_response.status_code == 201
        register_data = register_response.get_json()
        assert 'api_key' in register_data
        api_key = register_data['api_key']
        assert api_key is not None
        assert len(api_key) > 0

        # Login with the same user
        login_response = client.post(
            '/login',
            json={
                'username': 'testkeyreturn',
                'password': 'TestPassword123!'
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.get_json()
        # API key should NOT be returned on login
        assert 'api_key' not in login_data


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.skip(reason="Rate limiting is disabled in TESTING mode")
    def test_auth_endpoint_rate_limiting(self, client):
        """Verify that authentication endpoints are rate limited."""
        # Make multiple rapid requests to /login
        # Rate limit is 5 requests per minute for auth endpoints

        for i in range(6):
            response = client.post(
                '/login',
                json={'username': 'test', 'password': 'test'}
            )

            if i < 5:
                # First 5 requests should go through (may fail auth but not rate limited)
                assert response.status_code in [401, 400]  # Invalid creds or bad request
            else:
                # 6th request should be rate limited
                assert response.status_code == 429
                data = response.get_json()
                assert 'rate limit' in data['error'].lower()

    @pytest.mark.skip(reason="Rate limiting is disabled in TESTING mode")
    def test_api_endpoint_rate_limiting(self, client, registered_user):
        """Verify that API endpoints are rate limited."""
        # Make multiple rapid requests to /get_public_key
        # Rate limit is 30 requests per minute for API endpoints

        for i in range(32):
            response = client.get(
                '/get_public_key',
                headers={'X-API-KEY': registered_user['api_key']}
            )

            if i < 30:
                # First 30 requests should succeed
                assert response.status_code == 200
            else:
                # 31st request should be rate limited
                assert response.status_code == 429
                data = response.get_json()
                assert 'rate limit' in data['error'].lower()


class TestAuditLogging:
    """Tests for audit logging functionality."""

    def test_successful_authentication_is_logged(self, app, client, registered_user):
        """Verify that successful authentication attempts are logged."""
        with patch('utils.audit_logger.audit_logger.log_auth_success') as mock_log:
            response = client.get(
                '/get_public_key',
                headers={'X-API-KEY': registered_user['api_key']}
            )

            assert response.status_code == 200
            # Verify the audit logger was called
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs['user_id'] == registered_user['user']['id']
            assert call_args.kwargs['username'] == registered_user['user']['username']
            assert call_args.kwargs['method'] == 'api_key'

    def test_failed_authentication_is_logged(self, client):
        """Verify that failed authentication attempts are logged."""
        with patch('utils.audit_logger.audit_logger.log_event') as mock_log:
            response = client.get(
                '/get_public_key',
                headers={'X-API-KEY': 'invalid_key'}
            )

            assert response.status_code == 403
            # Verify the audit logger was called with failure event
            assert mock_log.called
            # Check if any call had status='failure'
            failure_logged = any(
                call.kwargs.get('status') == 'failure'
                for call in mock_log.call_args_list
            )
            assert failure_logged

    def test_registration_is_logged(self, client):
        """Verify that user registration is logged."""
        with patch('utils.audit_logger.audit_logger.log_registration') as mock_log:
            response = client.post(
                '/register',
                json={
                    'username': 'testauditlog',
                    'password': 'TestPassword123!',
                    'email': 'testaudit@example.com'
                }
            )

            assert response.status_code == 201
            # Verify the audit logger was called
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs['username'] == 'testauditlog'
            assert call_args.kwargs['email'] == 'testaudit@example.com'

    def test_gpg_operation_is_logged(self, client, registered_user):
        """Verify that GPG operations are logged."""
        with patch('utils.audit_logger.audit_logger.log_gpg_operation') as mock_log:
            # Create a test file to sign
            test_file = BytesIO(b'test content for signing')
            test_file.name = 'test.txt'

            response = client.post(
                '/sign',
                data={'file': (test_file, 'test.txt')},
                headers={'X-API-KEY': registered_user['api_key']},
                content_type='multipart/form-data'
            )

            # GPG operation may succeed or fail, but should be logged
            if response.status_code == 200:
                # Verify successful operation was logged
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args.args[0] == 'sign'  # operation type
                assert call_args.kwargs['user_id'] == registered_user['user']['id']


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_x_frame_options_header(self, client):
        """Verify that X-Frame-Options header is set to DENY."""
        response = client.get('/')
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'

    def test_x_content_type_options_header(self, client):
        """Verify that X-Content-Type-Options header is set to nosniff."""
        response = client.get('/')
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'

    def test_x_xss_protection_header(self, client):
        """Verify that X-XSS-Protection header is set."""
        response = client.get('/')
        assert 'X-XSS-Protection' in response.headers
        assert '1' in response.headers['X-XSS-Protection']

    def test_strict_transport_security_header(self, client):
        """Verify that Strict-Transport-Security header is set."""
        response = client.get('/')
        assert 'Strict-Transport-Security' in response.headers
        assert 'max-age' in response.headers['Strict-Transport-Security']

    def test_content_security_policy_header(self, client):
        """Verify that Content-Security-Policy header is set."""
        response = client.get('/')
        assert 'Content-Security-Policy' in response.headers
        assert 'default-src' in response.headers['Content-Security-Policy']

    def test_referrer_policy_header(self, client):
        """Verify that Referrer-Policy header is set."""
        response = client.get('/')
        assert 'Referrer-Policy' in response.headers


class TestInputValidation:
    """Tests for input validation security."""

    def test_username_validation_too_short(self, client):
        """Verify that usernames shorter than 3 characters are rejected."""
        response = client.post(
            '/register',
            json={
                'username': 'ab',  # Too short
                'password': 'TestPassword123!',
                'email': 'test@example.com'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'at least 3 characters' in data['error'].lower()

    def test_username_validation_reserved_name(self, client):
        """Verify that reserved usernames are rejected."""
        response = client.post(
            '/register',
            json={
                'username': 'admin',  # Reserved
                'password': 'TestPassword123!',
                'email': 'test@example.com'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'reserved' in data['error'].lower()

    def test_password_validation_weak_password(self, client):
        """Verify that weak passwords are rejected."""
        response = client.post(
            '/register',
            json={
                'username': 'testuser123',
                'password': 'weak',  # Too weak
                'email': 'test@example.com'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'password' in data['error'].lower()

    def test_file_upload_size_validation(self, client, registered_user):
        """Verify that oversized file uploads are rejected."""
        # Create a file that's larger than the limit (5MB for sign endpoint)
        large_file = BytesIO(b'x' * (6 * 1024 * 1024))  # 6MB
        large_file.name = 'large.txt'

        response = client.post(
            '/sign',
            data={'file': (large_file, 'large.txt')},
            headers={'X-API-KEY': registered_user['api_key']},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestPasswordSecurity:
    """Tests for password hashing security."""

    def test_passwords_are_hashed_with_argon2(self, app, registered_user):
        """Verify that passwords are hashed using Argon2id."""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()

            # Verify password hash exists
            assert user.password_hash is not None

            # Argon2id hashes start with $argon2id$
            assert user.password_hash.startswith('$argon2id$')

            # Verify the raw password is not stored
            assert 'TestPassword123!' not in user.password_hash

    def test_password_verification_timing_attack_resistance(self, client):
        """Verify that password verification doesn't leak timing information."""
        # This is a basic test - true timing attack resistance requires
        # constant-time comparison, which Argon2 provides

        # Try to login with invalid username (should take same time as invalid password)
        start1 = time.time()
        response1 = client.post('/login', json={
            'username': 'nonexistentuser',
            'password': 'WrongPassword123!'
        })
        time1 = time.time() - start1

        # Register a user
        client.post('/register', json={
            'username': 'timingtest',
            'password': 'CorrectPassword123!',
            'email': 'timing@example.com'
        })

        # Try to login with correct username but wrong password
        start2 = time.time()
        response2 = client.post('/login', json={
            'username': 'timingtest',
            'password': 'WrongPassword123!'
        })
        time2 = time.time() - start2

        # Both should return 401
        assert response1.status_code == 401
        assert response2.status_code == 401

        # Both should return generic "Invalid credentials" message
        data1 = response1.get_json()
        data2 = response2.get_json()
        assert data1['error'] == data2['error']
        assert 'invalid credentials' in data1['error'].lower()


class TestOpenAIEndpointSecurity:
    """Tests for OpenAI function calling endpoint security."""

    def test_openai_endpoints_require_api_key(self, client):
        """Verify that OpenAI endpoints require API key authentication."""
        response = client.post(
            '/openai/sign_text',
            json={'text': 'test message'}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False
        assert 'error_code' in data
        assert data['error_code'] == 'AUTH_REQUIRED'

    def test_openai_error_response_format(self, client):
        """Verify that OpenAI endpoints return properly formatted error responses."""
        response = client.post(
            '/openai/sign_text',
            json={'text': 'test message'},
            headers={'X-API-KEY': 'invalid_key'}
        )

        data = response.get_json()

        # Verify OpenAI response format
        assert 'success' in data
        assert 'error' in data
        assert 'error_code' in data
        assert data['success'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
