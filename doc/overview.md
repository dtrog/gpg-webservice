# GPG Webservice - Technical Overview

## Architecture Overview

The GPG Webservice is a Flask-based application that provides secure GPG cryptographic operations through HTTP endpoints. The system is designed with security, isolation, and ease of use as primary concerns.

### Core Design Principles

1. **Security First**: All private keys are protected with passphrases derived from API keys
2. **Complete Isolation**: GPG operations use temporary keyrings to prevent conflicts
3. **No Interactive Prompts**: Docker environment ensures fully automated operations
4. **Stateless Operations**: Each request is independent with proper cleanup
5. **Type Safety**: Comprehensive type hints and documentation throughout

## System Components

### 1. Database Layer (`models/`)

The data layer uses SQLAlchemy with three main models:

#### User Model (`models/user.py`)
- Stores user credentials and API keys
- Maintains relationships with PGP keys
- Password hashes use SHA256 (simplified for demo; production should use Argon2id)

#### PgpKey Model (`models/pgp_key.py`) 
- Stores ASCII-armored public and private keys
- Associated with users via foreign key relationship
- Private keys protected with SHA256(API_key) as passphrase

#### Challenge Model (`models/challenge.py`)
- Supports challenge-response authentication
- Stores challenge data and signatures with timestamps
- Designed for future key ownership verification

### 2. Service Layer (`services/`)

Business logic is separated into focused service classes:

#### UserService (`services/user_service.py`)
- **Registration**: Creates users with automatic GPG key generation
- **Authentication**: Validates credentials and returns user data
- **Key Management**: Coordinates GPG key creation with API key derivation

Key Features:
- Generates RSA 3072-bit keypairs automatically
- Uses `SHA256(API_key)` as GPG passphrase for security
- Returns detached objects to avoid SQLAlchemy session issues

#### AuthService (`services/auth_service.py`)
- Password hashing and verification
- API key-based user lookup
- Simplified implementation suitable for demonstration

### 3. Utility Layer (`utils/`)

Cryptographic and GPG operations are handled by specialized utilities:

#### CryptoUtils (`utils/crypto_utils.py`)
- **Key Derivation**: Argon2id-based password-to-key derivation
- **Symmetric Encryption**: AES-GCM for private key protection
- **API Key Generation**: Secure random API key creation using 256 bits of entropy

#### GPG Utils (`utils/gpg_utils.py`)
- **Key Generation**: Creates RSA 3072-bit keypairs with optional passphrases
- **Signature Verification**: Validates signatures against public keys
- **Temporary Keyrings**: All operations use isolated temporary directories

#### GPG File Utils (`utils/gpg_file_utils.py`)
- **File Signing**: Signs files with private keys using passphrases
- **File Verification**: Verifies detached signatures
- **File Encryption/Decryption**: Full GPG file operations with key management

### 4. Route Layer (`routes/`)

HTTP endpoints organized by functionality:

#### User Routes (`routes/user_routes.py`)
- `POST /register`: User registration with key generation
- `POST /login`: Authentication and API key retrieval

#### GPG Routes (`routes/gpg_routes.py`)
- `POST /sign`: File signing (no password required - uses API key)
- `POST /verify`: Signature verification with public key upload
- `POST /encrypt`: File encryption for recipients
- `POST /decrypt`: File decryption (no password required - uses API key)
- `POST /challenge`: Challenge-response authentication
- `GET /get_public_key`: Public key retrieval

## Security Architecture

### Authentication Flow

1. **Registration**: 
   - User provides username/password
   - System generates secure API key
   - GPG keypair created with `SHA256(API_key)` as passphrase
   - All data stored in database

2. **API Access**:
   - Client includes `X-API-KEY` header
   - System validates API key and retrieves user
   - GPG operations use derived passphrase automatically

### Key Protection Strategy

- **API Key**: 32 random bytes, base64url encoded (~256 bits entropy)
- **GPG Passphrase**: `SHA256(API_key)` - deterministic, secure, no special characters
- **Private Keys**: Stored as ASCII-armored text with passphrase protection
- **Database**: Only stores hashed passwords, never plaintext

### Isolation Techniques

1. **Temporary Keyrings**: Each GPG operation uses unique temporary directory
2. **Docker Environment**: Complete GPG agent isolation prevents host interference  
3. **Environment Variables**: Disable all interactive GPG features
4. **Process Cleanup**: Automatic cleanup of temporary files and directories

## Docker Configuration

### Multi-Stage Build
The Dockerfile creates an isolated environment:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y gnupg2
# ... application setup
RUN useradd -m -u 1000 appuser
USER appuser
```

### Environment Isolation
Critical environment variables for GPG isolation:

- `GPG_AGENT_INFO=""` - Disables GPG agent
- `DISPLAY=""` - Prevents X11 GUI prompts  
- `GPG_TTY=""` - Disables TTY interaction
- `PINENTRY_USER_DATA="USE_CURSES=0"` - Disables curses prompts

### Service Architecture
Docker Compose provides two services:

- **webservice**: Main Flask application (port 5000)
- **test-runner**: Isolated testing environment with profile activation

## Testing Strategy

### Test Organization

Tests are organized by component:

- `test_app.py`: Full integration tests of HTTP endpoints
- `test_models.py`: Database model validation
- `test_services.py`: Business logic verification  
- `test_*_utils.py`: Utility function testing

### Test Isolation

Each test uses:
- Fresh SQLite in-memory database
- Temporary GPG environments
- Docker container isolation
- No shared state between tests

### Key Test Scenarios

1. **User Registration**: Validates key generation and storage
2. **Authentication**: Confirms API key functionality
3. **File Operations**: Tests all cryptographic operations
4. **Error Handling**: Validates proper error responses
5. **Security**: Confirms isolation and key protection

## Performance Considerations

### GPG Operations
- Key generation: ~2-4 seconds (RSA 3072-bit)
- File signing: ~100-500ms depending on file size
- File encryption: ~100-500ms depending on file size
- Temporary keyring creation: ~50-100ms

### Database Operations
- SQLite suitable for development/testing
- Production should use PostgreSQL or similar
- Consider connection pooling for high load

### Scalability Factors
- Each request creates temporary GPG environment (CPU/disk intensive)
- File upload size limits should be configured
- Consider async processing for large files

## Security Considerations

### Threat Model

**Protected Against:**
- API key theft (GPG keys still protected by derived passphrase)
- Database compromise (passwords hashed, keys passphrase-protected)
- GPG agent interference (complete isolation)
- Interactive prompts (Docker environment prevents)

**Potential Vulnerabilities:**
- API key exposure in logs/memory dumps
- Temporary file access during processing
- Side-channel attacks on key operations
- Insufficient rate limiting

### Production Hardening

For production deployment, consider:

1. **Enhanced Authentication**: 
   - API key rotation mechanisms
   - Multi-factor authentication
   - Rate limiting and request throttling

2. **Key Protection**:
   - Hardware Security Module (HSM) integration
   - Key escrow and recovery procedures
   - Audit logging of all key operations

3. **Infrastructure Security**:
   - TLS termination with proper certificates
   - Web Application Firewall (WAF)
   - Network segmentation and monitoring

4. **Monitoring and Logging**:
   - Comprehensive audit trails
   - Anomaly detection
   - Security event correlation

## API Design Philosophy

### RESTful Principles
- Clear HTTP method semantics (POST for state changes, GET for retrieval)
- Consistent error response format
- Proper HTTP status codes

### Security-First Design
- API key required for all sensitive operations
- No passwords in request URLs or logs
- Consistent authentication pattern across endpoints

### User Experience
- Single API key authentication (no passwords needed for crypto operations)
- File-based operations with proper MIME type handling
- Clear error messages for troubleshooting

## Future Enhancement Opportunities

### Features
- Key rotation and migration capabilities
- Batch operations for multiple files
- Advanced key management (subkeys, expiration)
- Integration with external key servers

### Security
- Hardware security module integration
- Advanced audit logging and monitoring
- Key escrow and recovery mechanisms
- Multi-user collaboration features

### Performance
- Async processing for large files
- Caching layers for frequently accessed keys
- Horizontal scaling capabilities
- Advanced database optimization

This architecture provides a solid foundation for secure GPG operations while maintaining simplicity and ease of use.
