# Error Handling Standards

This document describes the error handling standards and patterns used in the GPG Webservice.

## Error Response Format

All API endpoints return consistent JSON error responses with the following structure:

### Standard Endpoints

```json
{
  "error": "Human-readable error message"
}
```

### OpenAI Function Calling Endpoints

OpenAI endpoints use an enhanced format compatible with function calling:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ERROR_CODE_CONSTANT"
}
```

## HTTP Status Codes

The service uses standard HTTP status codes to indicate the type of error:

- **400 Bad Request**: Invalid input, validation failures, missing required fields
- **401 Unauthorized**: Missing or invalid authentication credentials
- **403 Forbidden**: Valid credentials but insufficient permissions
- **404 Not Found**: Requested resource (key, user, challenge) does not exist
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Unexpected server errors, GPG operation failures

## Custom Exception Classes

The `utils/error_handling.py` module provides custom exception classes for domain-specific errors:

### GPGWebserviceError (Base Class)
Base exception for all application-specific errors.

```python
class GPGWebserviceError(Exception):
    def __init__(self, message: str, error_code: str = 'INTERNAL_ERROR', status_code: int = 500)
```

### ValidationError
Raised for input validation failures (400 status).

```python
raise ValidationError("Username must be at least 3 characters")
```

### AuthenticationError
Raised for authentication failures (401 status).

```python
raise AuthenticationError("Invalid API key")
```

### ResourceNotFoundError
Raised when a requested resource is not found (404 status).

```python
raise ResourceNotFoundError("Private key not found")
```

### GPGOperationError
Raised for GPG operation failures (500 status).

```python
raise GPGOperationError("sign", "Invalid key format")
```

### DatabaseError
Raised for database operation failures (500 status).

```python
raise DatabaseError("Failed to create user record")
```

### RateLimitError
Raised when rate limit is exceeded (429 status).

```python
raise RateLimitError()
```

## Error Logging

All errors are logged through the audit logger (`utils/audit_logger.py`):

- **Client errors (4xx)**: Logged at INFO or WARNING level
- **Server errors (5xx)**: Logged at ERROR level with full details

### Example

```python
from utils.audit_logger import audit_logger, AuditEventType

try:
    # ... operation
except Exception as e:
    audit_logger.log_error(
        'gpg',
        message=f'GPG sign failed for user {user.username}',
        user_id=user.id,
        username=user.username,
        error=str(e)
    )
    return jsonify({'error': 'Signing failed'}), 500
```

## Error Response Helper Functions

The `utils/error_handling.py` module provides helper functions for creating standardized responses:

### create_error_response()
Creates a standard error response with automatic logging.

```python
from utils.error_handling import create_error_response, GPGOperationError

try:
    # ... GPG operation
except Exception as e:
    error = GPGOperationError("decrypt", str(e))
    response, status_code = create_error_response(error, user_id=user.id)
    return jsonify(response), status_code
```

### create_success_response()
Creates a standard success response.

```python
from utils.error_handling import create_success_response

response, status_code = create_success_response(
    data={'user_id': user.id},
    message='User registered successfully',
    status_code=201
)
return jsonify(response), status_code
```

### create_openai_error_response()
Creates an OpenAI-compatible error response.

```python
from utils.error_handling import create_openai_error_response

response, status_code = create_openai_error_response(error, user_id=user.id)
return jsonify(response), status_code
```

### create_openai_success_response()
Creates an OpenAI-compatible success response.

```python
from utils.error_handling import create_openai_success_response

response, status_code = create_openai_success_response(
    data={'signature': signature_b64},
    message='Text signed successfully'
)
return jsonify(response), status_code
```

## Security Considerations

### Don't Expose Internal Details

Never expose sensitive internal details in error messages:

**Bad:**
```python
return jsonify({'error': f'Database connection failed: {connection_string}'}), 500
```

**Good:**
```python
logger.error(f'Database connection failed: {connection_string}')
return jsonify({'error': 'An internal error occurred'}), 500
```

### Prevent Information Disclosure

Use generic messages for authentication failures to prevent user enumeration:

**Bad:**
```python
if not user:
    return jsonify({'error': 'User does not exist'}), 401
if not verify_password(password, user.password_hash):
    return jsonify({'error': 'Invalid password'}), 401
```

**Good:**
```python
if not user or not verify_password(password, user.password_hash):
    return jsonify({'error': 'Invalid credentials'}), 401
```

### Log Security Events

Always log security-relevant errors:

```python
from utils.audit_logger import audit_logger, AuditEventType

if not api_key:
    audit_logger.log_event(
        AuditEventType.INVALID_API_KEY,
        status='failure',
        message='API key missing from request'
    )
    return jsonify({'error': 'API key required'}), 401
```

## Common Error Patterns

### Missing Required Fields

```python
data = request.get_json()
if not data:
    return jsonify({'error': 'JSON data required'}), 400

if not data.get('username') or not data.get('password'):
    return jsonify({'error': 'Username and password are required'}), 400
```

### Validation Failures

```python
from utils.security_utils import validate_username

valid, error = validate_username(username)
if not valid:
    return jsonify({'error': error}), 400
```

### Resource Not Found

```python
privkey = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
if not privkey:
    return jsonify({'error': 'Private key not found'}), 404
```

### GPG Operation Failures

```python
try:
    sign_file(input_path, privkey.key_data, sig_path, gpg_passphrase)

    audit_logger.log_gpg_operation(
        'sign',
        user_id=user.id,
        username=user.username,
        filename=filename
    )
except Exception as e:
    audit_logger.log_error(
        'gpg',
        message=f'GPG sign failed for user {user.username}',
        user_id=user.id,
        error=str(e)
    )
    return jsonify({'error': f'Signing failed: {str(e)}'}), 500
```

## Testing Error Handling

When writing tests, verify both success and error cases:

```python
def test_sign_requires_api_key(client):
    """Test that signing requires an API key."""
    rv = client.post('/sign', data={'file': (io.BytesIO(b'test'), 'test.txt')})
    assert rv.status_code == 401
    assert 'error' in rv.get_json()

def test_sign_invalid_api_key(client):
    """Test that signing fails with invalid API key."""
    rv = client.post('/sign',
                     data={'file': (io.BytesIO(b'test'), 'test.txt')},
                     headers={'X-API-KEY': 'invalid'})
    assert rv.status_code == 403
    assert 'error' in rv.get_json()
```
