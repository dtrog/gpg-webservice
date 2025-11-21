# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based GPG webservice that provides cryptographic operations (signing, verification, encryption, decryption) via HTTP endpoints. The service handles user registration, authentication, and automatic GPG key management with secure storage.

## Architecture

### Core Components

- **Flask Application** (`app.py`): Main entry point with blueprint registration
- **Models** (`models/`): SQLAlchemy database models for users, PGP keys, and challenges
- **Services** (`services/`): Business logic layer for user management, authentication, and challenge handling
- **Routes** (`routes/`): HTTP endpoint handlers organized by functionality (user operations vs GPG operations)
- **Utils** (`utils/`): Cryptographic utilities and GPG operations
- **Database** (`db/`): SQLAlchemy configuration and initialization

### Security Model

- Users authenticate with API keys (SHA256 hashed before database storage)
- Passwords are hashed with Argon2id (OWASP recommended)
- API keys are only returned once at registration (never at login)
- GPG passphrases derived from raw API keys using PBKDF2 with user ID as salt
- All GPG operations use temporary, isolated keyrings for security
- RSA 3072-bit keypairs are automatically generated on user registration
- Comprehensive audit logging for all security events

## Common Development Commands

### Testing

```bash
# Run all tests in Docker (recommended for isolation)
docker-compose run --rm test-runner pytest tests/ -v

# Run specific test files
docker-compose run --rm test-runner pytest tests/test_app.py -v
docker-compose run --rm test-runner pytest tests/test_models.py -v
docker-compose run --rm test-runner pytest tests/test_services.py -v

# Run with coverage
docker-compose run --rm test-runner pytest tests/ --cov=. --cov-report=html

# Run single test
docker-compose run --rm test-runner pytest tests/test_app.py::test_register -v
```

### Local Development

```bash
# Start development server
docker-compose up gpg-webservice

# Initialize database locally
python init_database.py

# Start local Flask server (automatically initializes DB if needed)
python app.py

# Install dependencies
pip install -r requirements.txt
```

### Database Operations

```bash
# Reset database
rm -f gpg_users.db instance/gpg_users.db

# Check database schema
sqlite3 gpg_users.db ".schema"

# Inspect data
sqlite3 gpg_users.db "SELECT id, username, api_key_hash FROM users;"
```

## Key Implementation Details

### GPG Operations

- All GPG operations must use temporary directories (`tempfile.mkdtemp()`) for isolation
- GPG agent is disabled via environment variables (`GPG_AGENT_INFO=""`, `DISPLAY=""`)
- Private key passphrases are derived from raw API keys: `derive_gpg_passphrase(raw_api_key, user.id)`
- Public keys are stored as ASCII-armored text in the database
- Private keys are encrypted before database storage using `crypto_utils.encrypt_private_key()`

### Authentication Flow

1. User registration generates raw API key (returned once) and RSA keypair
2. API key is hashed with SHA256 before database storage
3. Password is hashed with Argon2id before database storage
4. Private key is encrypted with GPG passphrase derived from raw API key
5. All protected endpoints require `X-API-KEY` header validation
6. Raw API key is passed to endpoints for GPG passphrase derivation

### Database Models

- `User`: username, password_hash, api_key_hash (SHA256 of API key)
- `PgpKey`: user_id, key_type ('public'/'private'), key_data (ASCII-armored)
- `Challenge`: user_id, challenge_data, signature, created_at

### Error Handling Patterns

- Use try/except blocks around all GPG operations with proper cleanup
- Return meaningful error messages without exposing sensitive details
- Always clean up temporary directories in finally blocks
- Log errors appropriately but don't expose internal details to API responses

## Testing Considerations

### Test Environment

- Tests run in Docker with complete GPG isolation
- Each test uses fresh database state (SQLite in-memory or temporary files)
- Test fixtures include pre-generated Alice/Bob GPG keys in `tests/fixtures/`
- All tests must clean up temporary files and directories

### Test Patterns

- Use `register_user()` helper function for user setup in integration tests
- Mock external dependencies in unit tests
- Test both success and failure scenarios for all endpoints
- Verify proper cleanup of temporary resources
- Use Docker environment variables for GPG isolation: `GPG_AGENT_INFO=""`, `GPG_TTY=""`

## Important Security Notes

- Never commit actual GPG keys or API keys to the repository
- All GPG operations must be isolated using temporary directories
- Passwords are hashed with Argon2id before storage
- Private keys are never exposed in API responses
- API keys are validated on every protected endpoint access

## File Upload Handling

- Use `werkzeug.utils.secure_filename()` for all uploaded filenames
- Store uploads in temporary locations and clean up after processing
- Validate file types and sizes before processing
- Handle multipart/form-data correctly for file uploads with additional parameters

## OpenAI Integration

The service includes specialized endpoints for OpenAI function calling integration:

- `/openai/function_definitions` - Get function definitions for OpenAI
- `/openai/register_user` - Register user via AI function call
- `/openai/sign_text` - Sign text content via AI function call
- All OpenAI endpoints return structured JSON responses with `success`, `data`, and `message` fields

## Dependencies

Core dependencies from requirements.txt:

- `flask` - Web framework
- `flask-sqlalchemy` - Database ORM
- `werkzeug` - WSGI utilities
- `cryptography` - Cryptographic operations
- `argon2-cffi` - Password hashing
- `pytest` - Testing framework
