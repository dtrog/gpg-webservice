# GPG Webservice

A secure Flask-based webservice providing GPG cryptographic operations through HTTP endpoints. This service enables user registration, authentication, and file-based cryptographic operations (signing, verification, encryption, decryption) with automatic GPG key management and enterprise-grade security features.

## 🔐 Security Features

### Core Security

- **Secure Key Generation**: RSA 3072-bit keypairs automatically generated per user
- **Enhanced Passphrase Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations and user-specific salts
- **Password Security**: Argon2id + AES-GCM for password hashing and key encryption
- **Strong Password Requirements**: Enforced complexity (uppercase, lowercase, numbers, special characters)
- **Isolated Operations**: All GPG operations performed in temporary, isolated keyrings
- **No Plaintext Storage**: Private keys encrypted with password-derived keys

### Network & Application Security

- **Rate Limiting**: Configurable rate limits for authentication (5/min) and API endpoints (30/min)
- **Input Validation**: Comprehensive validation for usernames, passwords, emails, and file uploads
- **File Upload Security**: Size limits, extension validation, and secure filename handling
- **HTTP Security Headers**: Complete security header suite (CSP, HSTS, X-Frame-Options, etc.)
- **Docker Isolation**: Complete GPG agent isolation prevents host system interference

### Authentication & Authorization

- **API Key Authentication**: Secure token-based authentication for all operations
- **Reserved Username Protection**: Prevents registration of system usernames
- **Email Validation**: RFC-compliant email address validation
- **Challenge-Response**: Optional cryptographic challenge authentication

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd gpg-webservice

# Start the service
docker-compose up gpg-webservice

# Run tests
docker-compose run --rm test-runner pytest tests/ -v
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app import init_db; init_db()"

# Start the service
python app.py
```

## 📡 API Endpoints

### Authentication Endpoints

#### `POST /register`
Register a new user account with automatic GPG key generation.

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!",
    "email": "alice@example.com"
  }'
```

**Strong Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one digit
- At least one special character (!@#$%^&*(),.?":{}|<>)

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": 1,
  "api_key": "abc123...",
  "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----..."
}
```

#### `POST /login`
Authenticate and retrieve API key.

```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!"
  }'
```

### Cryptographic Endpoints

All cryptographic endpoints require the `X-API-KEY` header and are protected by rate limiting.

#### `POST /sign`
Sign a file with the user's private key.

```bash
curl -X POST http://localhost:5000/sign \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt"
```

**Features:**
- File size limit: 5MB
- Secure temporary file handling
- Automatic cleanup of temporary resources

#### `POST /verify`
Verify a file signature against a public key.

```bash
curl -X POST http://localhost:5000/verify \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt.sig" \
  -F "pubkey=@public_key.asc"
```

#### `POST /encrypt`
Encrypt a file for a specific recipient.

```bash
curl -X POST http://localhost:5000/encrypt \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt" \
  -F "pubkey=@recipient_public_key.asc"
```

**Features:**
- File size limit: 10MB  
- Support for any binary file format
- Recipient public key validation

#### `POST /decrypt`
Decrypt a file using the user's private key.

```bash
curl -X POST http://localhost:5000/decrypt \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt.gpg"
```

#### `GET /get_public_key`
Retrieve the user's public key.

```bash
curl -H "X-API-KEY: your_api_key" \
  http://localhost:5000/get_public_key
```

#### Challenge-Response Authentication

Create and verify cryptographic challenges for enhanced security:

```bash
# Create challenge
curl -X POST http://localhost:5000/challenge \
  -H "X-API-KEY: your_api_key"

# Verify challenge (with signature)
curl -X POST http://localhost:5000/verify_challenge \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "challenge": "challenge_data",
    "signature": "-----BEGIN PGP SIGNATURE-----..."
  }'
```

## 🤖 OpenAI Function Calling Integration

The GPG Webservice includes specialized endpoints designed for seamless integration with OpenAI's function calling feature. These endpoints provide structured JSON interfaces for AI-powered cryptographic operations.

### Quick Start with OpenAI Functions

```bash
# Get function definitions for OpenAI
curl -X GET http://localhost:5000/openai/function_definitions
```

### Available AI Functions

#### Register User Function
```python
{
  "name": "register_user",
  "description": "Register a new user account with automatic GPG key generation",
  "parameters": {
    "type": "object",
    "properties": {
      "username": {"type": "string", "description": "Username (3-50 chars)"},
      "password": {"type": "string", "description": "Strong password (8+ chars)"},
      "email": {"type": "string", "description": "Valid email address"}
    },
    "required": ["username", "password", "email"]
  }
}
```

#### Sign Text Function
```python
{
  "name": "sign_text", 
  "description": "Sign text content using user's private GPG key",
  "parameters": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "Text content to sign"}
    },
    "required": ["text"]
  }
}
```

### Python Integration Example

```python
import openai
import requests

# OpenAI function calling with GPG operations
functions = [
    {
        "name": "register_user",
        "description": "Register a new user with GPG keys",
        # ... parameters
    },
    {
        "name": "sign_text",
        "description": "Sign text with GPG key", 
        # ... parameters
    }
]

def call_gpg_function(function_name, arguments, api_key=None):
    url = f"http://localhost:5000/openai/{function_name}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key
    
    response = requests.post(url, json=arguments, headers=headers)
    return response.json()

# Use with OpenAI
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Register user 'ai_bot' and sign 'Hello World'"}],
    functions=functions,
    function_call="auto"
)

# Execute the function calls
if response.choices[0].message.get("function_call"):
    function_call = response.choices[0].message["function_call"] 
    result = call_gpg_function(
        function_call["name"],
        json.loads(function_call["arguments"])
    )
```

### Available OpenAI Endpoints

| Function | Endpoint | Description |
|----------|----------|-------------|
| `register_user` | `POST /openai/register_user` | Register new user with GPG keys |
| `sign_text` | `POST /openai/sign_text` | Sign text content |
| `verify_text_signature` | `POST /openai/verify_text_signature` | Verify text signatures |
| `encrypt_text` | `POST /openai/encrypt_text` | Encrypt text for recipients |
| `decrypt_text` | `POST /openai/decrypt_text` | Decrypt text content |
| `get_user_public_key` | `POST /openai/get_user_public_key` | Get user's public key |

### Response Format

All OpenAI endpoints return structured responses:

```json
{
  "success": true,
  "data": {
    // Function-specific response data
  },
  "message": "Operation completed successfully"
}
```

For complete OpenAI integration documentation, see [`doc/openai_integration.md`](doc/openai_integration.md).

## 🏗️ Architecture

### Core Components

- **Flask Application** (`app.py`): Main web service with security middleware
- **Database Models** (`models/`): SQLAlchemy models with enum-based type safety
- **Services** (`services/`): Business logic layer with comprehensive error handling
- **Security Utilities** (`utils/security_utils.py`): Rate limiting, input validation, security headers
- **Cryptographic Utilities** (`utils/crypto_utils.py`): Enhanced key derivation and encryption
- **Routes** (`routes/`): HTTP endpoint handlers with security decorators

### Enhanced Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layer                           │
├─────────────────────────────────────────────────────────────┤
│ • Rate Limiting (5/min auth, 30/min API)                   │
│ • Input Validation (usernames, passwords, emails, files)   │
│ • Security Headers (CSP, HSTS, X-Frame-Options, etc.)      │
│ • File Upload Security (size limits, extension validation) │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                 Authentication Layer                        │
├─────────────────────────────────────────────────────────────┤
│ • Strong Password Requirements (8+ chars, complexity)      │
│ • API Key Authentication (256-bit entropy)                 │
│ • Enhanced Passphrase Derivation (PBKDF2-HMAC-SHA256)     │
│ • User-Specific Salt Generation                            │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                  Cryptographic Layer                       │
├─────────────────────────────────────────────────────────────┤
│ • RSA 3072-bit Key Generation                              │
│ • Argon2id Password Hashing                               │
│ • AES-GCM Private Key Encryption                          │
│ • Temporary Keyring Isolation                             │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

The database uses polymorphic models for type safety:

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    api_key VARCHAR UNIQUE NOT NULL
);

-- Polymorphic PGP Keys table with enum support
CREATE TABLE pgp_keys (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    key_type VARCHAR NOT NULL CHECK (key_type IN ('public', 'private')),
    key_data TEXT NOT NULL
);

-- Challenges table for enhanced authentication
CREATE TABLE challenges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    challenge_data TEXT NOT NULL,
    signature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Security Improvements Summary

#### 🔒 Enhanced Cryptography
- **PBKDF2-HMAC-SHA256**: Replaced simple SHA256 with proper key derivation
- **User-Specific Salts**: Each user gets unique salt for passphrase derivation
- **100,000 Iterations**: OWASP-recommended iteration count for key stretching

#### 🛡️ Input Security
- **Password Complexity**: Enforced strong password requirements
- **Username Validation**: 3-50 characters, alphanumeric + underscore/hyphen
- **Email Validation**: RFC-compliant email address validation
- **File Upload Security**: Size limits and extension validation

#### 🚦 Rate Limiting
- **Authentication**: 5 attempts per minute per IP
- **API Operations**: 30 requests per minute per IP
- **Automatic Testing Bypass**: Disabled in testing environments

#### 🔐 HTTP Security
- **X-Frame-Options**: DENY (clickjacking protection)
- **X-Content-Type-Options**: nosniff (MIME sniffing protection)
- **X-XSS-Protection**: 1; mode=block (XSS protection)
- **Strict-Transport-Security**: HTTPS enforcement
- **Content-Security-Policy**: Script and style restrictions
- **Referrer-Policy**: Strict referrer handling

## 🧪 Testing

The project includes comprehensive pytest-based testing with Docker isolation:

```bash
# Run all tests
docker-compose run --rm test-runner pytest tests/ -v

# Run specific test categories  
docker-compose run --rm test-runner pytest tests/test_app.py -v
docker-compose run --rm test-runner pytest tests/test_models.py -v
docker-compose run --rm test-runner pytest tests/test_security.py -v

# Run tests with coverage
docker-compose run --rm test-runner pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

- ✅ User registration and authentication with strong passwords
- ✅ Enhanced GPG key generation and secure storage
- ✅ File signing and verification with rate limiting
- ✅ File encryption and decryption with size limits
- ✅ Input validation and security headers
- ✅ Rate limiting and error handling
- ✅ Challenge-response authentication
- ✅ Security edge cases and attack scenarios

## 🐳 Docker Configuration

### Development Setup

```yaml
# docker-compose.yml
services:
  webservice:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=sqlite:///gpg_users.db
      
  test-runner:
    build: .
    profiles: ["test"]
    environment:
      - GPG_AGENT_INFO=""
      - DISPLAY=""
      - TESTING=true
```

### Production Considerations

- ✅ **SSL/TLS termination**: Use nginx or load balancer for HTTPS
- ✅ **Rate limiting**: Implemented at application level
- ✅ **Security headers**: Automatically added to all responses
- ✅ **Input validation**: Comprehensive validation implemented
- ✅ **Strong cryptography**: PBKDF2-HMAC-SHA256 with proper salting
- 🔶 **Database**: Upgrade to PostgreSQL for production
- 🔶 **Monitoring**: Implement application monitoring
- 🔶 **Key backup**: Implement secure key backup procedures
- 🔶 **HSM integration**: Consider hardware security modules

## 📁 Project Structure

```
gpg-webservice/
├── app.py                 # Main Flask application with security middleware
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── CLAUDE.md            # Development instructions for Claude Code
│
├── models/              # Database models with enum support
│   ├── user.py         # User account model
│   ├── pgp_key.py      # Polymorphic PGP key model
│   └── challenge.py    # Challenge-response model
│
├── services/           # Business logic layer
│   ├── user_service.py    # Enhanced user management
│   ├── auth_service.py    # Authentication utilities
│   └── challenge_service.py # Challenge handling with enum support
│
├── routes/             # HTTP endpoint handlers
│   ├── user_routes.py    # Registration/login with validation
│   ├── gpg_routes.py     # Cryptographic endpoints with rate limiting
│   └── openai_routes.py  # NEW: OpenAI function calling endpoints
│
├── utils/              # Utility functions
│   ├── crypto_utils.py   # Enhanced encryption/key derivation
│   ├── security_utils.py # NEW: Security utilities and validation
│   ├── gpg_utils.py      # GPG key generation
│   └── gpg_file_utils.py # GPG file operations
│
├── tests/              # Comprehensive test suite
│   ├── test_app.py       # Integration tests
│   ├── test_models.py    # Model tests
│   ├── test_security.py  # Security-focused tests
│   └── fixtures/         # Test key fixtures
│
├── db/                 # Database configuration and schema
│   ├── database.py      # SQLAlchemy setup
│   └── schema.sql       # Database schema definition
│
└── doc/               # Documentation
    ├── overview.md     # Technical architecture overview
    ├── api_reference.md # Complete API documentation
    ├── development.md  # Development guide
    ├── security.md     # Security implementation details
    └── openai_integration.md # NEW: OpenAI function calling guide
```

## 🔧 Configuration

### Environment Variables

- `FLASK_ENV`: Development/production mode
- `DATABASE_URL`: Database connection string (default: SQLite)
- `SECRET_KEY`: Flask secret key for session security
- `GPG_AGENT_INFO`: GPG agent configuration (disabled for isolation)
- `DISPLAY`: X11 display (disabled to prevent GUI prompts)
- `TESTING`: Enable testing mode (disables rate limiting)

### Security Configuration

The service automatically configures comprehensive security:

- **Password Requirements**: Configurable complexity requirements
- **Rate Limiting**: Adjustable per-endpoint rate limits
- **File Upload Limits**: Configurable size and type restrictions
- **Security Headers**: Comprehensive HTTP security headers
- **GPG Isolation**: Complete GPG environment isolation

## 🔍 Troubleshooting

### Common Issues

**Password Validation Errors**: Ensure passwords meet complexity requirements:
- Minimum 8 characters
- Mixed case letters, numbers, and special characters

**Rate Limit Exceeded**: Wait for rate limit window to reset or implement exponential backoff

**File Upload Errors**: Check file size limits and ensure proper multipart/form-data encoding

**GPG Agent Prompts**: Use Docker environment for complete isolation:

```bash
export GPG_AGENT_INFO=""
export DISPLAY=""
docker-compose run --rm test-runner pytest tests/ -v
```

**Database Issues**: Reset database and check schema:

```bash
rm -f gpg_users.db instance/gpg_users.db
python -c "from app import init_db; init_db()"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement features with comprehensive tests
4. Ensure all security tests pass
5. Update documentation
6. Submit a pull request

### Development Standards

- **Security First**: All changes must maintain or improve security posture
- **Test Coverage**: Minimum 90% coverage for security-critical components
- **Documentation**: Update relevant documentation for all changes
- **Type Safety**: Use comprehensive type hints throughout

## 📄 License

This project is for educational and demonstration purposes. Review security considerations and conduct thorough testing before production use.

## 🔒 Security Disclosure

For security issues, please contact the maintainers directly rather than opening public issues. We take security seriously and will respond promptly to verified security concerns.

---

**Recent Security Enhancements** (Latest Version):
- Enhanced passphrase derivation with PBKDF2-HMAC-SHA256
- Comprehensive input validation and rate limiting
- HTTP security headers and file upload protection
- Polymorphic database models with enum type safety
- Challenge-response authentication system
- Production-ready security configuration

For detailed technical information, see the `doc/` directory.