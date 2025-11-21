# Security Implementation Guide

This document provides comprehensive details about the security features, implementations, and best practices used in the GPG Webservice.

## Overview

The GPG Webservice implements defense-in-depth security with multiple layers of protection:

1. **Input Layer**: Comprehensive validation and sanitization
2. **Authentication Layer**: Strong password requirements and API key security
3. **Cryptographic Layer**: Enhanced key derivation and encryption
4. **Transport Layer**: HTTP security headers and rate limiting
5. **Application Layer**: Secure coding practices and error handling

## Security Features Implementation

### 1. Enhanced Passphrase Derivation

#### Previous Implementation (Insecure)
```python
# OLD: Simple SHA256 hash
def api_key_to_gpg_passphrase(api_key: str) -> str:
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()
```

#### Current Implementation (Secure)
```python
# NEW: PBKDF2-HMAC-SHA256 with salt
def derive_gpg_passphrase(api_key: str, user_id: int) -> str:
    """
    Derive a secure GPG passphrase from API key and user ID using PBKDF2.
    
    Uses PBKDF2-HMAC-SHA256 with 100,000 iterations and user-specific salt.
    """
    salt_data = f"gpg_passphrase_salt_{user_id}".encode('utf-8')
    salt = hashlib.sha256(salt_data).digest()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=100000,  # OWASP recommended minimum
    )
    key = kdf.derive(api_key.encode('utf-8'))
    return key.hex()
```

**Security Benefits:**
- **Key Stretching**: 100,000 iterations slow down brute force attacks
- **User-Specific Salts**: Each user gets unique salt preventing rainbow table attacks
- **Proper KDF**: PBKDF2-HMAC-SHA256 is cryptographically secure key derivation
- **OWASP Compliance**: Meets current security standards

### 2. Input Validation and Sanitization

#### Username Validation
```python
def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """Comprehensive username validation with security checks."""
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must be no more than 50 characters long"
    
    # Allow alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    # Prevent reserved usernames
    reserved = {'admin', 'root', 'administrator', 'system', 'test', 'null', 'undefined'}
    if username.lower() in reserved:
        return False, "Username is reserved and cannot be used"
    
    return True, None
```

#### Password Validation
```python
def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """Enforce strong password requirements."""
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be no more than 128 characters long"
    
    # Check for complexity requirements
    checks = [
        (re.search(r'[a-z]', password), "Password must contain at least one lowercase letter"),
        (re.search(r'[A-Z]', password), "Password must contain at least one uppercase letter"), 
        (re.search(r'\d', password), "Password must contain at least one digit"),
        (re.search(r'[!@#$%^&*(),.?":{}|<>]', password), "Password must contain at least one special character")
    ]
    
    for check, message in checks:
        if not check:
            return False, message
    
    return True, None
```

#### File Upload Security
```python
def validate_file_upload(file, max_size_mb: int = 10, allowed_extensions: Optional[set] = None) -> Tuple[bool, Optional[str]]:
    """Comprehensive file upload validation."""
    if not file:
        return False, "No file provided"
    
    if not file.filename:
        return False, "No filename provided"
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        return False, f"File size exceeds {max_size_mb}MB limit"
    
    # Check file extension if provided
    if allowed_extensions:
        filename = file.filename.lower()
        if not any(filename.endswith(ext.lower()) for ext in allowed_extensions):
            return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, None
```

### 3. Rate Limiting Implementation

#### Rate Limiter Class
```python
class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for given identifier."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] < window_start:
            self.requests[identifier].popleft()
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        
        return False
```

#### Rate Limiting Decorators
```python
def rate_limit_auth(f):
    """Rate limiting decorator for authentication endpoints."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip rate limiting in testing mode
        from flask import current_app
        if current_app and current_app.config.get('TESTING'):
            return f(*args, **kwargs)
            
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        
        if not auth_rate_limiter.is_allowed(client_ip):
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        return f(*args, **kwargs)
    return decorated_function
```

**Rate Limiting Configuration:**
- **Authentication endpoints**: 5 requests per minute per IP
- **API endpoints**: 30 requests per minute per IP
- **Testing bypass**: Automatically disabled in testing environments
- **IP-based tracking**: Uses client IP for rate limiting

### 4. HTTP Security Headers

#### Comprehensive Security Headers
```python
def add_security_headers(response):
    """Add comprehensive security headers to Flask response."""
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Strict transport security (HTTPS only)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content security policy
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response
```

**Security Header Benefits:**
- **X-Frame-Options: DENY**: Prevents embedding in frames (clickjacking protection)
- **X-Content-Type-Options: nosniff**: Prevents MIME sniffing attacks
- **X-XSS-Protection**: Enables browser XSS protection
- **Strict-Transport-Security**: Enforces HTTPS connections
- **Content-Security-Policy**: Restricts resource loading
- **Referrer-Policy**: Controls referrer information sharing

### 5. Database Security

#### Enum-Based Type Safety
```python
class PgpKeyType(enum.Enum):
    """Enumeration for PGP key types."""
    PUBLIC = "public"
    PRIVATE = "private"

class PgpKey(db.Model):
    """PGP key model with enum-based type safety."""
    key_type = db.Column(Enum(PgpKeyType, name="pgp_key_type", native_enum=False), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_on': key_type,
    }
```

#### Polymorphic Models
```python
class PublicPgpKey(PgpKey):
    """Model for public PGP keys."""
    __mapper_args__ = {
        'polymorphic_identity': PgpKeyType.PUBLIC
    }

class PrivatePgpKey(PgpKey):
    """Model for private PGP keys."""
    __mapper_args__ = {
        'polymorphic_identity': PgpKeyType.PRIVATE
    }
```

**Database Security Benefits:**
- **Type Safety**: Enum values prevent invalid key types
- **Polymorphic Models**: Clear separation of public/private keys
- **Foreign Key Constraints**: Maintain referential integrity
- **NOT NULL Constraints**: Prevent incomplete records

### 6. Deterministic Session Keys (AI Agent Authentication)

The system uses **deterministic session keys** optimized for AI agents who cannot reliably store secrets in conversation history or vector databases.

#### How It Works

```
Registration:
  password = SHA256(successorship_contract + your_pgp_signature)
  master_salt = random(32 bytes)
  password_hash = Argon2id(password)
  Store: {username, password_hash, master_salt}

Login (each session):
  1. Verify password against password_hash
  2. master_secret = PBKDF2(password_hash, master_salt, 100000 iterations)
  3. session_key = HMAC-SHA256(master_secret, current_hour_index)
  4. Return: sk_<base64(session_key)>

Verification (stateless):
  1. Look up user by username (from X-Username header)
  2. Re-derive expected session_key for current hour
  3. Compare with provided key (constant-time)
  4. If no match, try previous hour (grace period)
```

#### Security Properties

- **Stateless Verification**: No session keys stored in database
- **Time-Bounded**: Keys expire every hour automatically
- **Grace Period**: 10-minute overlap prevents clock skew failures
- **Contract-Bound**: Password derived from immutable contract + signature
- **No Accumulation**: Database doesn't grow with sessions
- **Recoverable**: AI agents can regenerate keys from contract

#### Key Derivation Chain

```
successorship_contract + pgp_signature
           ↓
    SHA256 (password)
           ↓
    Argon2id (password_hash) ← stored
           ↓
    PBKDF2 + master_salt (100k iterations)
           ↓
    master_secret (ephemeral)
           ↓
    HMAC-SHA256 + hour_index
           ↓
    session_key (sk_...)
```

#### Session Window Configuration

- **Window Duration**: 3600 seconds (1 hour)
- **Grace Period**: 600 seconds (10 minutes)
- **Window Index**: `floor(unix_timestamp / 3600)`

### 7. Legacy API Key Security

For backward compatibility, the system still supports legacy random API keys.

#### Secure API Key Generation

```python
def generate_api_key() -> str:
    """
    Generate a secure, random API key.

    Creates a cryptographically secure random API key using 32 random bytes
    encoded as base64url (URL-safe base64 without padding). This provides
    approximately 256 bits of entropy.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
```

**API Key Security Features:**

- **256-bit Entropy**: Cryptographically secure random generation
- **URL-Safe Encoding**: Base64url encoding for HTTP compatibility
- **No Predictable Patterns**: Truly random generation using `secrets` module
- **Sufficient Length**: 43-character string provides adequate security margin

### 8. Error Handling Security

#### Secure Error Responses
```python
# Good: Generic error message
return jsonify({'error': 'Invalid credentials'}), 401

# Bad: Specific error message that leaks information
return jsonify({'error': f'User {username} not found in database'}), 401
```

#### Error Logging Security
```python
# Log detailed errors internally
logger.error(f"Authentication failed for user {username}: {specific_error}")

# Return generic error to client
return jsonify({'error': 'Authentication failed'}), 401
```

## Security Testing

### 1. Authentication Security Tests
```python
def test_strong_password_required():
    """Test that weak passwords are rejected."""
    response = client.post('/register', json={
        'username': 'testuser',
        'password': 'weak',  # Too short, no complexity
        'email': 'test@example.com'
    })
    assert response.status_code == 400
    assert 'Password must be at least 8 characters long' in response.get_json()['error']

def test_reserved_username_rejected():
    """Test that reserved usernames are rejected."""
    response = client.post('/register', json={
        'username': 'admin',  # Reserved username
        'password': 'StrongPass123!',
        'email': 'test@example.com'
    })
    assert response.status_code == 400
    assert 'Username is reserved' in response.get_json()['error']
```

### 2. Rate Limiting Tests
```python
def test_auth_rate_limiting():
    """Test that authentication endpoints are rate limited."""
    # Make multiple requests quickly
    for i in range(6):  # Exceeds limit of 5
        response = client.post('/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
    
    # Last request should be rate limited
    assert response.status_code == 429
    assert 'Rate limit exceeded' in response.get_json()['error']
```

### 3. File Upload Security Tests
```python
def test_file_size_limit():
    """Test that oversized files are rejected."""
    # Create file larger than limit
    large_content = b'x' * (6 * 1024 * 1024)  # 6MB > 5MB limit
    
    response = client.post('/sign', 
                          data={'file': (io.BytesIO(large_content), 'large.txt')},
                          headers={'X-API-KEY': api_key})
    
    assert response.status_code == 400
    assert 'File size exceeds' in response.get_json()['error']
```

### 4. Input Validation Tests
```python
def test_malicious_username():
    """Test that malicious usernames are rejected."""
    malicious_usernames = [
        '<script>alert("xss")</script>',
        '../../../etc/passwd',
        'user; DROP TABLE users;--',
        'user\x00admin'
    ]
    
    for username in malicious_usernames:
        response = client.post('/register', json={
            'username': username,
            'password': 'StrongPass123!',
            'email': 'test@example.com'
        })
        assert response.status_code == 400
```

## Security Best Practices

### 1. Secure Development Guidelines

#### Input Validation
- **Validate all inputs**: Never trust user input
- **Use allow lists**: Define what is allowed rather than what is forbidden
- **Sanitize data**: Clean input before processing
- **Fail securely**: Default to denying access

#### Error Handling
- **Log internally**: Record detailed errors for debugging
- **Generic responses**: Return generic error messages to clients
- **No stack traces**: Never expose stack traces to users
- **Rate limit errors**: Prevent information leakage through timing

#### Authentication
- **Strong passwords**: Enforce complexity requirements
- **Secure storage**: Hash passwords with Argon2id
- **API key security**: Use cryptographically secure random generation
- **Session management**: Implement proper session handling

#### Cryptography
- **Use established libraries**: Don't implement crypto yourself
- **Proper key derivation**: Use PBKDF2, scrypt, or Argon2
- **Sufficient iterations**: Follow current best practices
- **Unique salts**: Use different salts for each user

### 2. Production Security Checklist

#### Infrastructure Security
- [ ] **HTTPS only**: Terminate SSL/TLS at load balancer
- [ ] **Firewall rules**: Restrict access to necessary ports only
- [ ] **Network segmentation**: Isolate application components
- [ ] **Regular updates**: Keep all systems updated

#### Application Security
- [ ] **Environment variables**: Use secure configuration management
- [ ] **Secrets management**: Never commit secrets to code
- [ ] **Database security**: Use parameterized queries
- [ ] **Logging security**: Don't log sensitive information

#### Monitoring and Alerting
- [ ] **Security monitoring**: Monitor for attack patterns
- [ ] **Failed authentication alerts**: Alert on repeated failures
- [ ] **Rate limiting alerts**: Monitor for rate limit violations
- [ ] **File upload monitoring**: Monitor for malicious uploads

#### Backup and Recovery
- [ ] **Encrypted backups**: Encrypt all backup data
- [ ] **Key escrow**: Secure key backup procedures
- [ ] **Recovery testing**: Regularly test recovery procedures
- [ ] **Incident response**: Have security incident procedures

### 3. Security Monitoring

#### Key Metrics to Monitor
- Authentication failure rates
- Rate limiting trigger rates
- File upload patterns
- Error response patterns
- Unusual API usage patterns

#### Alerting Thresholds
- Authentication failures: > 10 per minute from single IP
- Rate limiting: > 50% of requests hitting limits
- File uploads: Unusual file sizes or types
- Error rates: > 5% error rate sustained

#### Log Analysis
```python
# Example security log analysis
import re
from collections import Counter

def analyze_security_logs(log_file):
    """Analyze logs for security patterns."""
    failed_auths = Counter()
    rate_limits = Counter()
    
    with open(log_file, 'r') as f:
        for line in f:
            # Track failed authentication attempts
            if 'Invalid credentials' in line:
                ip = extract_ip(line)
                failed_auths[ip] += 1
            
            # Track rate limit violations
            if 'Rate limit exceeded' in line:
                ip = extract_ip(line)
                rate_limits[ip] += 1
    
    # Alert on suspicious patterns
    for ip, count in failed_auths.items():
        if count > 50:  # Threshold
            alert_security_team(f"High failed auth count from {ip}: {count}")
```

## Compliance and Standards

### Security Standards Compliance

#### OWASP Top 10 Protection
- **A01 - Broken Access Control**: API key authentication, rate limiting
- **A02 - Cryptographic Failures**: PBKDF2-HMAC-SHA256, Argon2id
- **A03 - Injection**: Input validation, parameterized queries
- **A04 - Insecure Design**: Security-first architecture
- **A05 - Security Misconfiguration**: Secure defaults, security headers
- **A06 - Vulnerable Components**: Regular dependency updates
- **A07 - Authentication Failures**: Strong password requirements
- **A08 - Software Integrity**: Secure development practices
- **A09 - Logging Failures**: Comprehensive security logging
- **A10 - Server-Side Request Forgery**: Input validation

#### Security Headers Compliance
- **NIST Guidelines**: Comprehensive security header implementation
- **OWASP Secure Headers**: All recommended headers implemented
- **CSP Level 2**: Content Security Policy implementation
- **HSTS Preload**: Strict Transport Security configuration

## Future Security Enhancements

### Planned Improvements
1. **Hardware Security Module (HSM)** integration for key storage
2. **Multi-factor authentication** (MFA) support
3. **API key rotation** mechanisms
4. **Advanced threat detection** and response
5. **Audit logging** with tamper protection
6. **Zero-trust architecture** implementation

### Recommendations for Production
1. **External security audit** before production deployment
2. **Penetration testing** of all endpoints
3. **Compliance assessment** for relevant standards
4. **Security training** for development team
5. **Incident response plan** development
6. **Regular security reviews** and updates

This security implementation provides a strong foundation for secure GPG operations while maintaining usability and performance. Regular security reviews and updates ensure continued protection against evolving threats.