"""
Tests for OpenAI Function Calling Integration Routes

This module tests all OpenAI-compatible endpoints to ensure they work correctly
with the expected input/output formats for function calling.
"""

import pytest
import json
import base64
import tempfile
import os
from unittest.mock import patch, MagicMock

from app import app
from db.database import db
from models.user import User
from models.pgp_key import PgpKey, PgpKeyType
from services.user_service import UserService


@pytest.fixture
def client():
    """Create a test client with in-memory database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def register_test_user(client, username='testuser', password='TestPass123!', email='test@example.com'):
    """Helper function to register a test user via OpenAI endpoint."""
    response = client.post('/openai/register_user', 
                          json={
                              'username': username,
                              'password': password,
                              'email': email
                          },
                          content_type='application/json')
    return response


class TestOpenAIRoutes:
    """Test class for OpenAI function calling routes."""
    
    def test_function_definitions_endpoint(self, client):
        """Test the function definitions endpoint."""
        response = client.get('/openai/function_definitions')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert 'functions' in data['data']
        assert isinstance(data['data']['functions'], list)
        assert len(data['data']['functions']) == 6  # All 6 functions
        
        # Check that all expected functions are present
        function_names = [f['name'] for f in data['data']['functions']]
        expected_functions = [
            'register_user', 'sign_text', 'verify_text_signature',
            'encrypt_text', 'decrypt_text', 'get_user_public_key'
        ]
        
        for expected in expected_functions:
            assert expected in function_names
    
    def test_register_user_function_success(self, client):
        """Test successful user registration via OpenAI endpoint."""
        response = register_test_user(client)
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert data['success'] is True
        assert 'data' in data
        assert data['data']['username'] == 'testuser'
        assert 'api_key' in data['data']
        assert 'public_key' in data['data']
        assert data['message'] == 'User registered successfully'
    
    def test_register_user_function_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post('/openai/register_user',
                              json={'username': 'testuser'},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'MISSING_FIELDS'
        assert 'username, password, and email are required' in data['error']
    
    def test_register_user_function_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post('/openai/register_user',
                              json={
                                  'username': 'testuser',
                                  'password': 'weak',
                                  'email': 'test@example.com'
                              },
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'REGISTRATION_FAILED'
    
    def test_sign_text_function_success(self, client):
        """Test successful text signing via OpenAI endpoint."""
        # First register a user
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        # Sign some text
        response = client.post('/openai/sign_text',
                              json={'text': 'Hello, this is a test message'},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert 'signature' in data['data']
        assert data['data']['text_signed'] == 'Hello, this is a test message'
        assert data['data']['signature_format'] == 'base64'
        assert data['message'] == 'Text signed successfully'
    
    def test_sign_text_function_no_api_key(self, client):
        """Test signing without API key."""
        response = client.post('/openai/sign_text',
                              json={'text': 'Hello, this is a test message'},
                              content_type='application/json')
        
        assert response.status_code == 401
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'AUTH_REQUIRED'
        assert data['error'] == 'API key required'
    
    def test_sign_text_function_invalid_api_key(self, client):
        """Test signing with invalid API key."""
        response = client.post('/openai/sign_text',
                              json={'text': 'Hello, this is a test message'},
                              headers={'X-API-KEY': 'invalid_key'},
                              content_type='application/json')
        
        assert response.status_code == 403
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'AUTH_INVALID'
        assert data['error'] == 'Invalid API key'
    
    def test_sign_text_function_missing_text(self, client):
        """Test signing without text field."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        response = client.post('/openai/sign_text',
                              json={},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'MISSING_TEXT'
        assert data['error'] == 'text field is required'
    
    def test_get_user_public_key_function_success(self, client):
        """Test successful public key retrieval via OpenAI endpoint."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        response = client.post('/openai/get_user_public_key',
                              json={},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert 'public_key' in data['data']
        assert data['data']['username'] == 'testuser'
        assert data['data']['key_format'] == 'ASCII-armored'
        assert data['message'] == 'Public key retrieved successfully'
    
    def test_verify_text_signature_function_success(self, client):
        """Test successful signature verification via OpenAI endpoint."""
        # Register user and sign text
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        public_key = reg_response.get_json()['data']['public_key']
        
        # Sign text
        sign_response = client.post('/openai/sign_text',
                                   json={'text': 'Test message for verification'},
                                   headers={'X-API-KEY': api_key},
                                   content_type='application/json')
        
        signature = sign_response.get_json()['data']['signature']
        
        # Verify signature
        response = client.post('/openai/verify_text_signature',
                              json={
                                  'text': 'Test message for verification',
                                  'signature': signature,
                                  'public_key': public_key
                              },
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert data['data']['verified'] is True
        assert data['data']['signature_valid'] is True
        assert data['data']['text_verified'] == 'Test message for verification'
    
    def test_verify_text_signature_function_missing_fields(self, client):
        """Test verification with missing required fields."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        response = client.post('/openai/verify_text_signature',
                              json={'text': 'Test message'},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'MISSING_FIELDS'
        assert 'text, signature, and public_key are required' in data['error']
    
    def test_verify_text_signature_function_invalid_signature(self, client):
        """Test verification with invalid base64 signature."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        public_key = reg_response.get_json()['data']['public_key']
        
        response = client.post('/openai/verify_text_signature',
                              json={
                                  'text': 'Test message',
                                  'signature': 'invalid_base64!@#',
                                  'public_key': public_key
                              },
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'INVALID_SIGNATURE_FORMAT'
        assert 'Invalid base64 signature' in data['error']
    
    @patch('routes.openai_routes.encrypt_file')
    def test_encrypt_text_function_success(self, mock_encrypt, client):
        """Test successful text encryption via OpenAI endpoint."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        public_key = reg_response.get_json()['data']['public_key']
        
        # Mock the encrypt_file function to return a temp file with encrypted content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('encrypted_content_here')
            mock_encrypt.return_value = temp_file.name
        
        try:
            response = client.post('/openai/encrypt_text',
                                  json={
                                      'text': 'Secret message',
                                      'recipient_public_key': public_key
                                  },
                                  headers={'X-API-KEY': api_key},
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert 'encrypted_text' in data['data']
            assert data['data']['original_text_length'] == 14  # len('Secret message')
            assert data['data']['format'] == 'base64'
            assert data['message'] == 'Text encrypted successfully'
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_encrypt_text_function_missing_fields(self, client):
        """Test encryption with missing required fields."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        response = client.post('/openai/encrypt_text',
                              json={'text': 'Secret message'},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'MISSING_FIELDS'
        assert 'text and recipient_public_key are required' in data['error']
    
    @patch('routes.openai_routes.decrypt_file')
    def test_decrypt_text_function_success(self, mock_decrypt, client):
        """Test successful text decryption via OpenAI endpoint."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        # Mock the decrypt_file function to return a temp file with decrypted content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('Decrypted secret message')
            mock_decrypt.return_value = temp_file.name
        
        # Create base64 encoded "encrypted" content for testing
        encrypted_b64 = base64.b64encode(b'fake_encrypted_content').decode('utf-8')
        
        try:
            response = client.post('/openai/decrypt_text',
                                  json={'encrypted_text': encrypted_b64},
                                  headers={'X-API-KEY': api_key},
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['data']['decrypted_text'] == 'Decrypted secret message'
            assert data['data']['text_length'] == 24  # len('Decrypted secret message')
            assert data['message'] == 'Text decrypted successfully'
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_decrypt_text_function_missing_field(self, client):
        """Test decryption with missing encrypted_text field."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        response = client.post('/openai/decrypt_text',
                              json={},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'MISSING_ENCRYPTED_TEXT'
        assert data['error'] == 'encrypted_text field is required'
    
    def test_decrypt_text_function_invalid_base64(self, client):
        """Test decryption with invalid base64 encrypted content."""
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        
        response = client.post('/openai/decrypt_text',
                              json={'encrypted_text': 'invalid_base64!@#'},
                              headers={'X-API-KEY': api_key},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_code'] == 'INVALID_ENCRYPTED_FORMAT'
        assert 'Invalid base64 encrypted content' in data['error']
    
    def test_all_endpoints_rate_limiting_compatibility(self, client):
        """Test that all endpoints work with rate limiting (testing bypass active)."""
        # Register user first
        reg_response = register_test_user(client)
        api_key = reg_response.get_json()['data']['api_key']
        public_key = reg_response.get_json()['data']['public_key']
        
        # Test all endpoints quickly to ensure rate limiting doesn't interfere in testing
        endpoints_and_data = [
            ('/openai/get_user_public_key', {}),
            ('/openai/sign_text', {'text': 'Test message'}),
        ]
        
        for endpoint, data in endpoints_and_data:
            response = client.post(endpoint,
                                  json=data,
                                  headers={'X-API-KEY': api_key},
                                  content_type='application/json')
            
            # Should not get rate limited in testing mode
            assert response.status_code != 429
            response_data = response.get_json()
            assert 'success' in response_data
    
    def test_function_definitions_schema_validity(self, client):
        """Test that function definitions match OpenAI schema requirements."""
        response = client.get('/openai/function_definitions')
        data = response.get_json()
        
        for function in data['data']['functions']:
            # Each function must have required fields
            assert 'name' in function
            assert 'description' in function
            assert 'parameters' in function
            
            # Parameters must have required schema structure
            params = function['parameters']
            assert params['type'] == 'object'
            assert 'properties' in params
            assert 'required' in params
            
            # Check that required fields are actually in properties
            for required_field in params['required']:
                assert required_field in params['properties']
    
    def test_error_response_consistency(self, client):
        """Test that all error responses follow consistent format."""
        # Test various error scenarios
        error_scenarios = [
            # Missing API key
            ('/openai/sign_text', {}, {}, 401),
            # Invalid API key 
            ('/openai/sign_text', {}, {'X-API-KEY': 'invalid'}, 403),
            # Missing JSON data
            ('/openai/register_user', None, {}, 400),
        ]
        
        for endpoint, json_data, headers, expected_status in error_scenarios:
            if json_data is None:
                response = client.post(endpoint, headers=headers)
            else:
                response = client.post(endpoint, 
                                      json=json_data, 
                                      headers=headers,
                                      content_type='application/json')
            
            assert response.status_code == expected_status
            data = response.get_json()
            
            # All error responses should have consistent structure
            assert 'success' in data
            assert data['success'] is False
            assert 'error' in data
            assert 'error_code' in data
            assert isinstance(data['error'], str)
            assert isinstance(data['error_code'], str)