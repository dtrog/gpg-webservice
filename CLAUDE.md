# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GPG Webservice Suite** - A production-ready GPG cryptographic service with three components:

1. **gpg-webservice-rest/** - Flask REST API (Python) providing GPG operations (sign, verify, encrypt, decrypt)
2. **gpg-webservice-mcp/** - Model Context Protocol server (TypeScript/Node.js) for AI agent integration
3. **gpg-webservice-dashboard/** - Web dashboard (Nginx/HTML/JS) for user management

This is a multi-service Docker Compose project with shared authentication, deterministic session keys for AI agents, and comprehensive security features.

## Architecture

### Multi-Service Structure

The root directory orchestrates three independent services via [docker-compose.yml](docker-compose.yml):

- **REST API** (Port 5555): Core service - Flask app with SQLAlchemy ORM, Argon2id password hashing, AES-256-GCM key encryption
- **MCP Server** (Port 3000): Proxies GPG operations to REST API for AI agents (Claude, GPT-4, etc.)
- **Dashboard** (Port 8080): User-facing web UI for registration and file operations

Services communicate over a Docker bridge network (`gpg-network`).

### REST API Architecture (Primary Codebase)

Located in `gpg-webservice-rest/`:

**Layered Design**:
- **Routes** ([routes/](gpg-webservice-rest/routes/)): HTTP endpoints - `user_routes.py`, `gpg_routes.py`, `openai_routes.py`, `admin_routes.py`
- **Services** ([services/](gpg-webservice-rest/services/)): Business logic - `user_service.py`, `auth_service.py`, `challenge_service.py`
- **Utils** ([utils/](gpg-webservice-rest/utils/)): Reusable components - `gpg_file_utils.py` (Builder Pattern), `crypto_utils.py` (Named Constants)
- **Models** ([models/](gpg-webservice-rest/models/)): SQLAlchemy ORM - `user.py`, `pgp_key.py`, `challenge.py`

**Key Design Patterns**:
- **Builder Pattern** (`GPGCommandBuilder` in [utils/gpg_file_utils.py](gpg-webservice-rest/utils/gpg_file_utils.py)): Fluent interface for GPG command construction
- **Named Constants** ([utils/crypto_utils.py](gpg-webservice-rest/utils/crypto_utils.py)): OWASP-compliant cryptographic parameters
- **Exception Hierarchy** ([utils/error_handling.py](gpg-webservice-rest/utils/error_handling.py)): Structured error handling with HTTP status codes

## Common Commands

### Starting/Stopping Services

```bash
# Start all services (REST API + MCP + Dashboard)
docker compose up -d

# Start only REST API
docker compose up -d gpg-webservice-rest

# View logs
docker compose logs -f
docker compose logs -f gpg-webservice-rest  # Specific service

# Stop all services
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

### Development Mode (Hot Reload)

```bash
# Start with development overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Testing

```bash
# Run full test suite (in Docker - recommended for GPG isolation)
docker compose run --rm test-runner

# Run specific test file
docker compose run --rm test-runner pytest tests/test_app.py -v

# Run single test function
docker compose run --rm test-runner pytest tests/test_app.py::test_register -v

# Run with coverage report
docker compose run --rm test-runner pytest tests/ --cov=. --cov-report=html

# Run tests locally (requires Python 3.11+, GPG installed)
cd gpg-webservice-rest
python -m pytest tests/ -v
```

### Database Operations

```bash
# Reset SQLite database
rm -f gpg-webservice-rest/gpg_users.db

# Inspect database
sqlite3 gpg-webservice-rest/gpg_users.db "SELECT id, username, master_salt FROM users;"

# View schema
sqlite3 gpg-webservice-rest/gpg_users.db ".schema"
```

### Setup & Configuration

```bash
# Initial setup (interactive)
./setup.sh

# Automated setup (non-interactive)
./setup.sh --auto

# Generate secrets manually
cd gpg-webservice-rest
./scripts/generate-secrets.sh
```

## Authentication Architecture

### Deterministic Session Keys (AI Agents)

**Design Philosophy**: Stateless authentication ideal for AI agents with hourly key rotation.

**Flow**:
1. **Registration**: User created with `master_salt` (256-bit random). First session key derived from `HMAC(PBKDF2(password_hash, master_salt), window_index)` and returned.
2. **Login**: Session key re-derived from stored `password_hash + master_salt + current_time_window`.
3. **Rotation**: Keys expire hourly (with 10-minute grace period). AI agents re-login to regenerate.
4. **Verification**: Server re-derives expected key and compares (no database storage of keys).

**Session Key Format**: `sk_<base64url_encoded_hmac>`

**Headers**: `X-API-KEY: sk_...` + `X-Username: alice`

See [gpg-webservice-rest/services/user_service.py:1-50](gpg-webservice-rest/services/user_service.py) for implementation.

### Legacy API Keys (Backward Compatibility)

**Flow**:
1. Registration generates random API key (returned once)
2. SHA256 hash stored in `api_key_hash` column
3. No username required in headers

**Format**: `<base64url_encoded_random>`

**Headers**: `X-API-KEY: <random_key>`

### Admin Authentication (Two Methods)

1. **Session Keys** (AI Agent Admins): Configure `ADMIN_USERNAMES=alice,bob` in `.env`
2. **GPG Tokens** (Human Admins): Challenge-response with GPG signatures, 24-hour validity, configured via `ADMIN_GPG_KEYS` in `.env`

See [docs/admin_gpg_authentication.md](docs/admin_gpg_authentication.md) for GPG admin setup.

## Security Architecture

### Key Security Features

- **Argon2id Password Hashing**: 4 iterations, 64MB memory (OWASP recommended)
- **PBKDF2-HMAC-SHA256**: 100,000 iterations for GPG passphrase derivation
- **AES-256-GCM**: Authenticated encryption for private keys
- **Process Isolation**: Each GPG operation in isolated `tempfile.TemporaryDirectory()` with custom environment
- **GPG Agent Cleanup**: Agent killed before operations to prevent caching
- **Passphrase Protection**: Via stdin (`--passphrase-fd 0`), never command-line visible
- **Rate Limiting**: 5/min for auth endpoints, 30/min for API endpoints

### GPG Operations Pattern

**Always use temporary isolated environments**:

```python
from utils.gpg_file_utils import GPGCommandBuilder

# Builder pattern for GPG commands
(GPGCommandBuilder(gnupg_home)
 .with_yes()
 .with_pinentry_loopback()
 .with_passphrase_stdin(passphrase)
 .sign(input_path, output_path)
 .execute('signing'))
```

**Key Requirements**:
- All GPG operations use `tempfile.mkdtemp()` for `GNUPGHOME`
- Custom environment variables prevent system GPG interference
- Private key passphrases derived via `derive_gpg_passphrase(raw_api_key, user.id)`
- Cleanup happens automatically via context managers

See [gpg-webservice-rest/docs/architecture.md](gpg-webservice-rest/docs/architecture.md) for complete security documentation.

## Important Implementation Details

### GPG Command Builder (Builder Pattern)

**Location**: [gpg-webservice-rest/utils/gpg_file_utils.py](gpg-webservice-rest/utils/gpg_file_utils.py)

**Usage**:
```python
# Sign operation
builder = GPGCommandBuilder(gnupg_home)
builder.with_yes().with_pinentry_loopback().with_passphrase_stdin(passphrase)
builder.sign(input_path, output_path).execute('signing')

# Verify operation
builder = GPGCommandBuilder(gnupg_home)
result = builder.verify(sig_path, input_path).execute('verification')

# Testing (without execution)
cmd = builder.with_yes().sign(input_path, output_path).build()
assert '--yes' in cmd
```

**Internal Helpers** (private - do not call directly from routes):
- `_create_gpg_isolated_env(gnupg_home)`: Creates isolated GPG environment variables
- `_kill_gpg_agent()`: Kills GPG agent to prevent caching
- `_import_key_to_gnupg(gnupg_home, key_content, key_type)`: Imports keys into temporary keyring

### Cryptographic Constants

**Location**: [gpg-webservice-rest/utils/crypto_utils.py](gpg-webservice-rest/utils/crypto_utils.py)

All cryptographic parameters are defined as module-level named constants (OWASP-compliant):

```python
ARGON2_TIME_COST = 4                    # Iterations
ARGON2_MEMORY_COST = 65536              # Memory (64 MB)
PBKDF2_ITERATIONS = 100000              # Key derivation iterations
MASTER_SALT_SIZE = 32                   # Master salt (256 bits)
SESSION_WINDOW_SECONDS = 3600           # Hourly session windows
SESSION_GRACE_PERIOD_SECONDS = 600      # 10-minute grace period
```

Never use magic numbers - always reference these constants.

### Error Handling Pattern

**Location**: [gpg-webservice-rest/utils/error_handling.py](gpg-webservice-rest/utils/error_handling.py)

**Exception Hierarchy**:
```
GPGWebserviceError (base)
├── ValidationError (400)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── ResourceNotFoundError (404)
├── GPGOperationError (500)
├── DatabaseError (500)
└── RateLimitError (429)
```

**Usage Pattern**:
```python
# In utils/services - raise specific exceptions
if result.returncode != 0:
    raise GPGOperationError('signing', result.stderr.decode())

# In routes - convert to HTTP responses
try:
    result = sign_file(...)
except GPGOperationError as e:
    return create_error_response(e, user.id, user.username)
```

### Database Models

**Location**: [gpg-webservice-rest/models/](gpg-webservice-rest/models/)

- **User** ([user.py](gpg-webservice-rest/models/user.py)): `username`, `password_hash` (Argon2id), `master_salt` (for session keys), `api_key_hash` (legacy, nullable)
- **PgpKey** ([pgp_key.py](gpg-webservice-rest/models/pgp_key.py)): `user_id`, `key_type` ('public'/'private'), `key_data` (ASCII-armored, private keys AES-encrypted)
- **Challenge** ([challenge.py](gpg-webservice-rest/models/challenge.py)): `user_id`, `challenge_data`, `signature`, `created_at`

**Important**: Private keys are encrypted with `crypto_utils.encrypt_private_key()` before storage and decrypted during operations.

## File Structure for Adding Features

### Adding a New GPG Operation

1. **Utils Layer** (`gpg-webservice-rest/utils/gpg_file_utils.py`):
   - Add method to `GPGCommandBuilder` (e.g., `.clearsign()`)
   - Add public API function (e.g., `clearsign_file()`)

2. **Routes Layer** (`gpg-webservice-rest/routes/gpg_routes.py`):
   - Add endpoint with `@require_api_key` decorator
   - Handle file upload, call utils function, return response

3. **Tests** (`gpg-webservice-rest/tests/`):
   - Add integration test in `test_routes.py`
   - Add unit test in `test_gpg_file_utils.py`

### Adding a New Authentication Method

1. **Service Layer** (`gpg-webservice-rest/services/auth_service.py`):
   - Implement authentication logic

2. **Utils Layer** (`gpg-webservice-rest/utils/security_utils.py`):
   - Add decorator (e.g., `@require_bearer_token`)

3. **Routes Layer**:
   - Apply decorator to protected endpoints

4. **Tests** (`gpg-webservice-rest/tests/test_auth_service.py`):
   - Add authentication flow tests

## Environment Variables

### Critical Variables (Required)

Located in `.env` (root) and `gpg-webservice-rest/.env`:

```bash
# Security (REQUIRED - generate with ./gpg-webservice-rest/scripts/generate-secrets.sh)
SERVICE_KEY_PASSPHRASE=<generated_secret>  # Protects internal GPG keys
SECRET_KEY=<generated_secret>               # Flask session encryption

# Ports
FLASK_PORT=5555
MCP_PORT=3000
DASHBOARD_PORT=8080

# Admin Access
ADMIN_USERNAMES=                           # Comma-separated: alice,bob
ADMIN_GPG_KEYS={}                          # JSON: {"admin":"-----BEGIN PGP..."}
```

### Optional Variables

```bash
# Environment
ENVIRONMENT=development  # development, testing, production
LOG_LEVEL=INFO

# Database (default: SQLite)
DATABASE_URL=sqlite:///gpg_users.db
# DATABASE_URL=postgresql://user:pass@host:5432/gpg_db  # Production

# Rate Limiting
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_API_REQUESTS=30

# GPG Settings
GPG_KEY_LENGTH=3072  # 2048, 3072, or 4096
```

## Testing Strategy

### Test Organization

Located in `gpg-webservice-rest/tests/`:

- **conftest.py**: Pytest fixtures (client, test DB, authentication)
- **test_app.py**: Integration tests for all endpoints
- **test_models.py**: Database model tests
- **test_services.py**: Business logic tests
- **test_crypto_utils.py**: Cryptography unit tests
- **test_openai_routes.py**: OpenAI function calling integration
- **test_security_integration.py**: Security feature tests

### Test Environment

- **Docker Isolation**: Tests run in container with clean GPG environment
- **Environment Variables**: `GPG_AGENT_INFO=""`, `GPG_TTY=""`, `GNUPGHOME=/tmp/gnupg`
- **Database**: SQLite in-memory or temporary file
- **Fixtures**: Pre-generated Alice/Bob GPG keys in `tests/fixtures/`

### Test Patterns

```python
# Use fixtures for authentication
def test_sign_file(client, auth_headers):
    response = client.post('/gpg/sign', headers=auth_headers, ...)
    assert response.status_code == 200

# Mock external dependencies in unit tests
@patch('utils.gpg_file_utils.subprocess.run')
def test_gpg_command_construction(mock_run):
    cmd = GPGCommandBuilder('/tmp').build()
    assert '--batch' in cmd
```

## Use Cases

### Lex Atlantis Integration (Use Case Example)

Located in `use-case/`:

- **Gemini/agents_definitons.py**: Multi-agent architecture using GPG authentication
- **lex_atlantis_core_integrated.py**: Core governance system with GPG signatures
- **Agents**: Justiciar, Sentinel, Logician (different models with mandate-specific roles)
- **Pattern**: Challenge-response with deterministic session keys for AI agent governance

This demonstrates the system's ability to provide cryptographic identity verification for AI agents in governance systems.

## Troubleshooting

### GPG Operations Failing

```bash
# Reset GPG environment
docker compose down
rm -rf /tmp/gpg-docker /tmp/gpg-test
docker compose up -d
```

### Database Issues

```bash
# Reset database
rm -f gpg-webservice-rest/gpg_users.db
docker compose up -d  # Will reinitialize on startup
```

### Port Conflicts

```bash
# Check what's using the port
lsof -i :5555

# Change port in .env
echo "FLASK_PORT=5556" >> .env
docker compose up -d
```

### Service Won't Start - Missing Secrets

```bash
# Generate required secrets
cd gpg-webservice-rest
./scripts/generate-secrets.sh
cd ..
docker compose up -d
```

## Documentation

### Key Documentation Files

- **Root README** ([README.md](README.md)): Quick start and overview
- **Architecture Guide** ([gpg-webservice-rest/docs/architecture.md](gpg-webservice-rest/docs/architecture.md)): Complete system architecture with design patterns
- **GPG Builder Guide** ([gpg-webservice-rest/docs/gpg_command_builder_guide.md](gpg-webservice-rest/docs/gpg_command_builder_guide.md)): Builder pattern API reference
- **API Reference** ([gpg-webservice-rest/docs/api_reference.md](gpg-webservice-rest/docs/api_reference.md)): All endpoints with examples
- **Refactoring Changelog** ([gpg-webservice-rest/docs/refactoring_changelog_2025.md](gpg-webservice-rest/docs/refactoring_changelog_2025.md)): 2025 code improvements
- **Admin GPG Auth** ([docs/admin_gpg_authentication.md](docs/admin_gpg_authentication.md)): Admin authentication setup

### REST API Specific Docs

Located in `gpg-webservice-rest/docs/`:
- **development.md**: Development setup and contribution guidelines
- **security.md**: Security features and threat model
- **openai_integration.md**: OpenAI function calling integration
- **error_handling.md**: Exception handling guide

## Dependencies

### Core Python Dependencies (REST API)

From [gpg-webservice-rest/requirements.txt](gpg-webservice-rest/requirements.txt):

```
flask                # Web framework
flask-sqlalchemy     # ORM
flask-cors           # CORS support
werkzeug             # WSGI utilities
cryptography         # AES-GCM encryption
argon2-cffi          # Password hashing
pytest               # Testing framework
python-dotenv        # Environment variables
```

### System Dependencies

- **Docker** & **Docker Compose** (v2.0+)
- **GPG** (GNU Privacy Guard) - installed in Docker containers
- **PostgreSQL** (optional, for production)

## Recent Improvements (January 2025)

See [gpg-webservice-rest/docs/refactoring_changelog_2025.md](gpg-webservice-rest/docs/refactoring_changelog_2025.md) for complete details:

1. **Builder Pattern**: `GPGCommandBuilder` class eliminates 77 lines of duplicated code
2. **Named Constants**: All cryptographic parameters now OWASP-documented constants
3. **Module-level Imports**: Performance optimization in `crypto_utils.py` and `openai_routes.py`
4. **Error Handling**: Comprehensive exception hierarchy with HTTP status codes
5. **Admin Authentication**: Dual authentication system (session keys for agents, GPG tokens for humans)

## Project Status

- **Production-Ready**: Comprehensive security, testing, and documentation
- **Multi-Service**: REST API, MCP server, and web dashboard
- **AI Agent Focused**: Deterministic session keys ideal for AI governance systems
- **Well-Documented**: 2000+ lines of documentation across 14 files
- **Test Coverage**: Integration and unit tests with Docker isolation
