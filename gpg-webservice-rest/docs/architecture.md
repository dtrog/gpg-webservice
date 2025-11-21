# GPG Webservice Architecture

## Table of Contents
- [Project Overview](#project-overview)
- [Directory Structure](#directory-structure)
- [Layered Architecture](#layered-architecture)
- [Core Components](#core-components)
- [Design Patterns](#design-patterns)
- [Security Architecture](#security-architecture)
- [Data Flow](#data-flow)
- [Testing Strategy](#testing-strategy)
- [Performance Considerations](#performance-considerations)
- [Future Architecture Improvements](#future-architecture-improvements)
- [References](#references)

## Project Overview

The GPG Webservice is a secure Flask-based REST API that provides cryptographic operations (signing, verification, encryption, decryption) with automatic GPG key management and enterprise-grade security.

### Architecture Principles
- **Separation of Concerns**: Routes, Services, Utils clearly separated
- **Builder Pattern**: Fluent interface for GPG command construction
- **Error Hierarchy**: Comprehensive exception handling
- **Security by Design**: Multiple layers of protection
- **Testability**: Mock-friendly design with isolated components

### Technology Stack
- **Backend**: Python 3.14 with Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cryptography**: GPG, Argon2id, AES-GCM, PBKDF2
- **Containerization**: Docker and Docker Compose
- **MCP Adapter**: TypeScript/Node.js
- **Dashboard**: Static HTML/JavaScript with nginx

---

## Directory Structure

```
gpg-webservice/
├── gpg-webservice-rest/          # Flask REST API (Python)
│   ├── app.py                    # Application entry point
│   ├── config.py                 # Configuration management
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py              # User authentication model
│   │   ├── pgp_key.py           # PGP key storage (encrypted)
│   │   └── challenge.py         # Challenge-response authentication
│   │
│   ├── routes/                   # HTTP endpoints (Flask blueprints)
│   │   ├── user_routes.py       # Registration, login, logout
│   │   ├── gpg_routes.py        # File-based GPG operations
│   │   └── openai_routes.py     # OpenAI function calling endpoints
│   │
│   ├── services/                 # Business logic layer
│   │   ├── user_service.py      # User management logic
│   │   ├── auth_service.py      # Authentication logic
│   │   └── challenge_service.py # Challenge-response protocol
│   │
│   ├── utils/                    # Utility functions
│   │   ├── gpg_file_utils.py    # ⭐ GPG operations (Builder Pattern)
│   │   ├── crypto_utils.py      # ⭐ Cryptography (Named Constants)
│   │   ├── error_handling.py    # Exception hierarchy
│   │   ├── security_utils.py    # Security helpers (validation, rate limiting)
│   │   └── audit_logger.py      # Structured audit logging
│   │
│   ├── db/                       # Database configuration
│   │   └── database.py          # SQLAlchemy setup
│   │
│   ├── tests/                    # Test suite
│   │   ├── test_routes.py       # Integration tests for routes
│   │   ├── test_crypto_utils.py # Unit tests for cryptography
│   │   └── test_openai_routes.py# Tests for OpenAI integration
│   │
│   └── docs/                     # Documentation
│       ├── architecture.md      # ⭐ This file
│       ├── gpg_command_builder_guide.md  # ⭐ Builder pattern guide
│       ├── refactoring_changelog_2025.md # ⭐ Refactoring history
│       ├── api_reference.md     # API documentation
│       └── security.md          # Security documentation
│
├── gpg-webservice-mcp/           # MCP adapter (TypeScript)
│   └── src/index.ts             # MCP server implementation
│
└── gpg-webservice-dashboard/     # Web dashboard (HTML/JS)
    └── index.html               # Dashboard entry point
```

**⭐ Recently Refactored Components** (January 2025)

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Layer (Flask Routes)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ user_routes.py   gpg_routes.py   openai_routes.py    │  │
│  │ - Request/response handling                           │  │
│  │ - Input validation                                    │  │
│  │ - Authentication (API key verification)               │  │
│  │ - Rate limiting                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              Business Logic Layer (Services)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ user_service.py  auth_service.py  challenge_service.py│  │
│  │ - User management                                     │  │
│  │ - Authentication logic                                │  │
│  │ - Challenge-response protocols                        │  │
│  │ - Orchestration of utilities                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                  Utility Layer (Utils)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ GPGCommandBuilder (Builder Pattern) ⭐                │  │
│  │ crypto_utils (Named Constants) ⭐                     │  │
│  │ error_handling (Exception Hierarchy)                  │  │
│  │ security_utils (Validation, Rate Limiting)            │  │
│  │ audit_logger (Structured Logging)                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│               Data Layer (SQLAlchemy Models)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ User  PgpKey  Challenge                               │  │
│  │ - Database schema                                     │  │
│  │ - ORM mappings                                        │  │
│  │ - Relationships                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             ↓
                        PostgreSQL
```

### Layer Responsibilities

#### 1. HTTP Layer (routes/)
**Purpose**: Handle HTTP requests and responses

**Responsibilities**:
- Parse HTTP requests
- Validate input data
- Authenticate users (API key verification)
- Apply rate limiting
- Return HTTP responses with appropriate status codes
- Error response formatting

**Example**:
```python
@gpg_bp.route('/sign', methods=['POST'])
@rate_limit_api
@require_api_key
def sign(user, raw_api_key):
    # Validate file upload
    # Call service layer
    # Return response
```

---

#### 2. Business Logic Layer (services/)
**Purpose**: Implement business rules and orchestration

**Responsibilities**:
- User registration and authentication
- GPG key generation and management
- Challenge-response protocols
- Orchestrate utility functions
- Transaction management

**Example**:
```python
def register_user(username, password, email):
    # Hash password
    # Generate API key
    # Generate GPG keypair
    # Encrypt private key
    # Save to database
```

---

#### 3. Utility Layer (utils/)
**Purpose**: Provide reusable, focused utilities

**Responsibilities**:
- GPG command construction and execution
- Cryptographic operations
- Input validation
- Rate limiting
- Audit logging
- Error handling

**Example**:
```python
(GPGCommandBuilder(gnupg_home)
 .with_yes()
 .sign(input_path, output_path)
 .execute('signing'))
```

---

#### 4. Data Layer (models/)
**Purpose**: Define database schema and ORM

**Responsibilities**:
- Database table definitions
- Column constraints and indexes
- Relationships between models
- Query methods

**Example**:
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # ... other fields ...
```

---

## Core Components

### gpg_file_utils.py (Recently Refactored)

**Location**: `utils/gpg_file_utils.py` (315 lines)

**Architecture**:
```python
# Helper Functions (Private - Internal Use)
_create_gpg_isolated_env(gnupg_home: str) -> Dict[str, str]
    # Creates environment variables for GPG isolation
    # Returns dict with GNUPGHOME, GPG_AGENT_INFO, etc.

_kill_gpg_agent() -> None
    # Kills any existing GPG agent
    # Prevents interference with isolated operations

_import_key_to_gnupg(gnupg_home, key_content, key_type, raise_on_error) -> bool
    # Imports PGP key into temporary keyring
    # Supports both error raising and boolean return

# GPGCommandBuilder Class (Builder Pattern)
class GPGCommandBuilder:
    __init__(gnupg_home)

    # Configuration Methods (Chainable)
    with_yes()
    with_passphrase_stdin(passphrase)
    with_pinentry_loopback()
    with_trust_always()

    # Operation Methods (Chainable)
    sign(input_path, output_path)
    verify(sig_path, input_path)
    encrypt(input_path, output_path, recipient)
    decrypt(input_path, output_path)
    list_keys()

    # Execution Methods
    build() -> list
    execute(operation_name) -> CompletedProcess

# Public API Functions
sign_file(input_path, private_key, output_path, passphrase)
verify_signature_file(input_path, sig_path, public_key) -> bool
encrypt_file(input_path, public_key, output_path)
decrypt_file(input_path, private_key, output_path, passphrase)
```

**Key Features**:
- **Builder Pattern**: Fluent interface for GPG command construction
- **Environment Isolation**: All operations in temporary directories with custom environment
- **Error Handling**: Comprehensive `GPGOperationError` exceptions
- **Security**: Passphrases via stdin, GPG agent cleanup

**Usage Example**:
```python
# Signing with builder pattern
(GPGCommandBuilder(gnupg_home)
 .with_yes()
 .with_pinentry_loopback()
 .with_passphrase_stdin(passphrase)
 .sign(input_path, output_path)
 .execute('signing'))
```

**Design Rationale**:
- Eliminates 77 lines of duplicated command construction code
- Centralized environment isolation and error handling
- Testable without GPG execution (`.build()` method)
- Easy to extend with new operations

---

### crypto_utils.py (Recently Refactored)

**Location**: `utils/crypto_utils.py` (153 lines)

**Architecture**:
```python
# Named Constants (OWASP-Compliant)
ARGON2_TIME_COST = 4                # Argon2 iterations
ARGON2_MEMORY_COST = 65536          # Memory in KB (64 MB)
ARGON2_PARALLELISM = 2              # Parallel threads
ARGON2_HASH_LENGTH = 32             # Output length (256 bits)

PBKDF2_ITERATIONS = 100000          # PBKDF2 iterations (OWASP minimum)
PBKDF2_KEY_LENGTH = 32              # Output length (256 bits)

SALT_SIZE = 16                      # Salt size (128 bits)
NONCE_SIZE = 12                     # AES-GCM nonce (96 bits)
API_KEY_SIZE = 32                   # API key size (256 bits)

# Key Derivation
derive_key(password, salt) -> bytes
    # Uses Argon2id with OWASP-recommended parameters
    # Returns 32-byte key for AES-256 encryption

derive_gpg_passphrase(api_key, user_id) -> str
    # Uses PBKDF2-HMAC-SHA256 with 100,000 iterations
    # Deterministic but secure passphrase derivation

# Encryption/Decryption
encrypt_private_key(private_key_bytes, password) -> bytes
    # AES-GCM encryption with Argon2id key derivation
    # Returns salt + nonce + ciphertext

decrypt_private_key(enc, password) -> bytes
    # AES-GCM decryption
    # Raises InvalidTag on wrong password

# API Key Management
generate_api_key() -> str
    # Generates 256-bit random key
    # Returns base64url-encoded string

hash_api_key(api_key) -> str
    # SHA256 hash for database storage
    # One-way hash for secure storage
```

**Key Features**:
- **Named Constants**: All magic numbers replaced with documented constants
- **OWASP Compliance**: Industry-standard cryptographic parameters
- **Module-level Imports**: Performance optimization
- **Comprehensive Docstrings**: Every function fully documented

**Design Rationale**:
- Self-documenting code with named constants
- Easy to adjust security parameters (change constant, not scattered numbers)
- Clear compliance with security standards

---

### error_handling.py

**Location**: `utils/error_handling.py` (232 lines)

**Exception Hierarchy**:
```python
GPGWebserviceError (base exception)
├── ValidationError              # 400 - Input validation failures
├── AuthenticationError          # 401 - Authentication failures
├── AuthorizationError           # 403 - Authorization failures
├── ResourceNotFoundError        # 404 - Resource not found
├── GPGOperationError           # 500 - GPG command failures
├── DatabaseError               # 500 - Database operation failures
└── RateLimitError              # 429 - Rate limit exceeded
```

**Helper Functions**:
```python
create_error_response(error, user_id, username, include_details)
    # Standard error response with logging
    # Returns (dict, status_code)

create_success_response(data, message, status_code)
    # Standard success response
    # Returns (dict, status_code)

create_openai_error_response(error, user_id, username)
    # OpenAI-compatible error response
    # Returns {'success': False, 'error': ..., 'error_code': ...}

create_openai_success_response(data, message, status_code)
    # OpenAI-compatible success response
    # Returns {'success': True, 'data': ..., 'message': ...}
```

**Usage Pattern**:
```python
# In utils (raise specific exception)
if result.returncode != 0:
    raise GPGOperationError('signing', result.stderr.decode())

# In routes (catch and convert to HTTP response)
try:
    # ... operation ...
except GPGOperationError as e:
    return create_openai_error_response(e, user.id, user.username)
```

---

## Design Patterns

### 1. Builder Pattern (GPGCommandBuilder)

**Intent**: Separate construction of complex GPG commands from their execution

**Implementation**:
```python
class GPGCommandBuilder:
    def __init__(self, gnupg_home):
        self.cmd = ['gpg', '--homedir', gnupg_home, '--batch']
        self.passphrase_input = None

    def with_yes(self):
        self.cmd.append('--yes')
        return self  # ⭐ Return self for chaining

    def sign(self, input_path, output_path):
        self.cmd.extend(['--output', output_path, '--detach-sign', input_path])
        return self  # ⭐ Return self for chaining

    def execute(self, operation_name):
        # ⭐ Centralized execution logic
        _kill_gpg_agent()
        env = _create_gpg_isolated_env(self.gnupg_home)
        result = subprocess.run(self.cmd, input=self.passphrase_input, env=env, ...)
        if result.returncode != 0:
            raise GPGOperationError(operation_name, result.stderr.decode())
        return result
```

**Benefits**:
- **Fluent API**: `builder.with_yes().sign(input, output).execute('signing')`
- **Testability**: `cmd = builder.build()` without execution
- **Maintainability**: Single source of truth for GPG commands
- **Extensibility**: Easy to add new operations

**Before/After Comparison**:
```python
# Before (77 lines duplicated across 4 functions)
sign_cmd = ['gpg', '--homedir', gnupg_home, '--batch', '--yes', '--pinentry-mode', 'loopback']
if passphrase:
    sign_cmd.extend(['--passphrase-fd', '0'])
    passphrase_input = (passphrase + '\n').encode()
sign_cmd.extend(['--output', output_path, '--detach-sign', input_path])
_kill_gpg_agent()
env = _create_gpg_isolated_env(gnupg_home)
result = subprocess.run(sign_cmd, input=passphrase_input, env=env, ...)
if result.returncode != 0:
    raise GPGOperationError('signing', result.stderr.decode())

# After (6 lines with builder)
(GPGCommandBuilder(gnupg_home)
 .with_yes()
 .with_pinentry_loopback()
 .with_passphrase_stdin(passphrase)
 .sign(input_path, output_path)
 .execute('signing'))
```

---

### 2. DRY Principle (Don't Repeat Yourself)

**Problem Identified**:
- GPG environment setup: Duplicated 3 times (~30 lines)
- Key import operations: Duplicated 4 times (~40 lines)
- Command construction: Duplicated in 4 functions (~77 lines)

**Solution Applied**:
1. Created `_create_gpg_isolated_env()` helper
2. Created `_kill_gpg_agent()` helper
3. Created `_import_key_to_gnupg()` helper
4. Created `GPGCommandBuilder` class

**Result**: Eliminated ~170 lines of duplicated code

---

### 3. Dependency Injection

**Pattern**: Routes depend on service abstractions, not implementations

**Example**:
```python
# Routes inject dependencies via decorators
@gpg_bp.route('/sign', methods=['POST'])
@require_api_key  # ⭐ Injects user and raw_api_key
def sign(user, raw_api_key):
    # Use injected dependencies
    passphrase = derive_gpg_passphrase(raw_api_key, user.id)
    # ...
```

**Benefits**:
- Testable (can mock `get_user_by_api_key()`)
- Flexible (easy to swap authentication methods)
- Clear dependencies

---

### 4. Template Method (in execute())

**Pattern**: `execute()` provides template for all GPG operations

**Implementation**:
```python
def execute(self, operation_name):
    # Step 1: Cleanup
    _kill_gpg_agent()

    # Step 2: Setup isolated environment
    env = _create_gpg_isolated_env(self.gnupg_home)

    # Step 3: Execute subprocess
    result = subprocess.run(self.cmd, input=self.passphrase_input, env=env, ...)

    # Step 4: Error checking
    if result.returncode != 0:
        raise GPGOperationError(operation_name, result.stderr.decode())

    return result
```

**Benefit**: Consistent execution flow with centralized error handling

---

## Security Architecture

### Defense in Depth

```
┌───────────────────────────────────────────────────────────┐
│ Layer 1: Network Security                                 │
│ - Rate Limiting (5/min auth, 30/min API)                  │
│ - HTTPS enforcement                                       │
│ - Security headers (CSP, HSTS, X-Frame-Options)           │
└───────────────────────────────────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────────┐
│ Layer 2: Application Security                             │
│ - API key authentication (SHA256 hashed in DB)            │
│ - Input validation (username, email, file uploads)        │
│ - File upload restrictions (size, type)                   │
│ - Reserved username protection                            │
└───────────────────────────────────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────────┐
│ Layer 3: Cryptographic Security                           │
│ - Argon2id password hashing (OWASP recommended)           │
│ - PBKDF2-HMAC-SHA256 key derivation (100k iterations)     │
│ - AES-GCM authenticated encryption                        │
│ - RSA 3072-bit keypairs                                   │
└───────────────────────────────────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────────┐
│ Layer 4: Process Isolation Security                       │
│ - Temporary GPG keyrings (no persistent storage)          │
│ - Custom environment variables (isolation)                │
│ - GPG agent cleanup (prevent caching)                     │
│ - Docker containerization                                 │
│ - Passphrase via stdin (not command-line)                 │
└───────────────────────────────────────────────────────────┘
```

### Security Features by Component

#### Passphrase Protection
- **Storage**: Never stored in plaintext
- **Transmission**: Via stdin (`--passphrase-fd 0`), never command-line
- **Derivation**: PBKDF2 with 100,000 iterations for GPG operations
- **Visibility**: Not visible in `ps aux` (process list)

#### Key Management
- **Generation**: RSA 3072-bit keys per user
- **Storage**: Private keys encrypted with AES-GCM + user password
- **Access**: Retrieved only during operations, never cached
- **Isolation**: Each operation uses fresh temporary keyring

#### Environment Isolation
- **Temporary Keyrings**: Each operation uses `tempfile.TemporaryDirectory()`
- **Environment Variables**: Custom env prevents system GPG interference
- **Agent Cleanup**: GPG agent killed before each operation
- **Docker**: Additional containerization layer

---

## Data Flow

### User Registration Flow

```
Client Request
    ↓
POST /user/register
{username, password, email}
    ↓
user_routes.py
├─ validate_username(username)
├─ validate_password(password)
└─ validate_email(email)
    ↓
UserService.register_user()
    ↓
┌──────────────────────────────────────┐
│ 1. Hash password (Argon2id)          │
│ 2. Create User record                │
│ 3. Generate API key (256-bit random) │
│ 4. Hash API key (SHA256)             │
│ 5. Generate GPG keypair (RSA 3072)   │
│ 6. Encrypt private key (AES-GCM)     │
│ 7. Store in database                 │
└──────────────────────────────────────┘
    ↓
Return to client
{
  "api_key": "...",  ⭐ Only time shown
  "public_key": "..."
}
```

---

### Signing Operation Flow

```
Client Request
    ↓
POST /gpg/sign
Headers: {X-API-KEY: "..."}
Body: {file: <binary>}
    ↓
gpg_routes.py
├─ @rate_limit_api (check rate limit)
└─ @require_api_key (validate API key)
       ↓
   get_user_by_api_key(raw_api_key)
   ├─ hash_api_key(raw_api_key)
   └─ Query User by hashed key
       ↓
   Retrieve encrypted private key from DB
       ↓
   decrypt_private_key(encrypted_key, user.password)
       ↓
   derive_gpg_passphrase(raw_api_key, user.id)
       ↓
   sign_file(input_path, private_key, output_path, passphrase)
       ↓
   ┌────────────────────────────────────────┐
   │ Create temporary directory             │
   │ _import_key_to_gnupg(private_key)      │
   │ GPGCommandBuilder(gnupg_home)          │
   │   .with_yes()                          │
   │   .with_pinentry_loopback()            │
   │   .with_passphrase_stdin(passphrase)   │
   │   .sign(input_path, output_path)       │
   │   .execute('signing')                  │
   │       ├─ _kill_gpg_agent()             │
   │       ├─ _create_gpg_isolated_env()    │
   │       └─ subprocess.run(gpg command)   │
   └────────────────────────────────────────┘
       ↓
   Return signed file to client
       ↓
   Cleanup temporary directory (automatic)
```

---

## Testing Strategy

### Unit Tests
**Target**: Individual functions in utils/

**Approach**:
- Test GPGCommandBuilder without GPG execution (using `.build()`)
- Test cryptographic functions with known inputs/outputs
- Test validation functions with edge cases
- Mock external dependencies

**Example**:
```python
def test_sign_command_construction():
    builder = GPGCommandBuilder('/tmp/test')
    cmd = builder.with_yes().sign('/in.txt', '/out.sig').build()

    assert '--yes' in cmd
    assert '--detach-sign' in cmd
    assert '/in.txt' in cmd
    assert '/out.sig' in cmd
```

---

### Integration Tests
**Target**: Complete request/response cycles

**Approach**:
- Test full endpoint flows
- Use test database
- Mock GPG operations where appropriate
- Verify error handling

**Example**:
```python
def test_sign_endpoint(client, auth_headers):
    response = client.post(
        '/gpg/sign',
        headers=auth_headers,
        data={'file': (BytesIO(b'test'), 'test.txt')}
    )
    assert response.status_code == 200
    assert 'signature' in response.json
```

---

### Security Tests
**Target**: Security properties and vulnerabilities

**Approach**:
- Verify passphrase not in process list
- Verify temporary file cleanup
- Test rate limiting enforcement
- Test input validation (SQL injection, XSS, path traversal)
- Verify key encryption

**Example**:
```python
def test_passphrase_not_in_process_list():
    # Start signing operation
    # Check ps aux output
    # Verify passphrase not visible
```

---

## Performance Considerations

### Recent Optimizations (January 2025)

1. **Module-level Imports** ⭐
   - Imports happen once at module load, not per function call
   - Applied to: `crypto_utils.py`, `openai_routes.py`
   - Impact: Reduced function call overhead

2. **Named Constants** ⭐
   - Compile-time evaluation of cryptographic parameters
   - Applied to: `crypto_utils.py`
   - Impact: Eliminates runtime calculations

3. **Builder Pattern** ⭐
   - Efficient command construction without redundant operations
   - Applied to: `gpg_file_utils.py`
   - Impact: Reduces code execution paths

### Caching Strategy

**Cached**:
- API key hashes (in database)
- Session tokens (in database)
- Configuration values (loaded once)

**Never Cached**:
- Private keys (retrieved per-operation, immediately discarded)
- Passphrases (never stored, only derived)
- GPG command results

### Resource Management

- **Temporary Directories**: Automatically cleaned by `tempfile.TemporaryDirectory()`
- **GPG Agent**: Killed to prevent resource leaks
- **Database Connections**: Pooled by SQLAlchemy
- **File Handles**: Context managers ensure proper cleanup

---

## Future Architecture Improvements

### Planned Enhancements

1. **Error Handler Integration**
   - Use `create_openai_error_response()` throughout routes
   - Add blueprint-level error handlers for consistent error formatting
   - Centralized error logging

2. **Async Operations**
   - Consider async GPG operations for large files
   - Non-blocking file processing with async/await
   - Background job queue for long-running operations

3. **Metrics & Monitoring**
   - Prometheus metrics endpoint
   - Operation timing/latency tracking
   - Error rate monitoring
   - GPG operation success/failure metrics

4. **Health Checks**
   - `/health` endpoint with component checks
   - GPG availability check
   - Database connectivity check
   - Dependency status

5. **API Versioning**
   - `/api/v1/` prefix for all endpoints
   - Versioned schemas
   - Deprecation strategy
   - Backward compatibility support

---

## References

- **GPGCommandBuilder Guide**: [gpg_command_builder_guide.md](gpg_command_builder_guide.md) - Complete developer guide for builder pattern
- **Security Documentation**: [../security.md](../security.md) - Security features and best practices
- **API Reference**: [api_reference.md](api_reference.md) - Complete endpoint documentation
- **Refactoring Changelog**: [refactoring_changelog_2025.md](refactoring_changelog_2025.md) - Recent code improvements
- **Error Handling Guide**: [error_handling.md](error_handling.md) - Exception handling documentation
- **OpenAI Integration**: [openai_integration.md](openai_integration.md) - Function calling integration
- **Development Guide**: [development.md](development.md) - Development workflow and setup
