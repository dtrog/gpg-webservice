
# GPG Webservice

A secure Flask-based webservice providing GPG cryptographic operations through HTTP endpoints. This service enables user registration, authentication, and file-based cryptographic operations (signing, verification, encryption, decryption) with automatic GPG key management.

## 🔐 Security Features

- **Secure Key Generation**: RSA 3072-bit keypairs automatically generated per user
- **API Key Authentication**: SHA256-hashed API keys used as GPG passphrases
- **Password Security**: Argon2id + AES-GCM for password hashing and key encryption
- **Isolated Operations**: All GPG operations performed in temporary, isolated keyrings
- **No Plaintext Storage**: Private keys stored with passphrase protection derived from API keys
- **Docker Isolation**: Complete GPG agent isolation prevents host system interference

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd gpg-webservice

# Start the service
docker-compose up webservice

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
    "password": "secure_password",
    "email": "alice@example.com"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully",
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
    "password": "secure_password"
  }'
```

### Cryptographic Endpoints

All cryptographic endpoints require the `X-API-KEY` header for authentication.

#### `POST /sign`
Sign a file with the user's private key.

```bash
curl -X POST http://localhost:5000/sign \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt"
```

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

## 🏗️ Architecture

### Core Components

- **Flask Application** (`app.py`): Main web service with endpoint routing
- **Database Models** (`models/`): SQLAlchemy models for users, keys, and challenges
- **Services** (`services/`): Business logic layer for user management and authentication
- **Utilities** (`utils/`): Cryptographic operations and GPG key management
- **Routes** (`routes/`): HTTP endpoint handlers organized by functionality

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    api_key VARCHAR UNIQUE
);

-- PGP Keys table
CREATE TABLE pgp_keys (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    key_type VARCHAR NOT NULL,  -- 'public' or 'private'
    key_data TEXT NOT NULL      -- ASCII-armored key
);

-- Challenges table (for future challenge-response auth)
CREATE TABLE challenges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    challenge_data TEXT NOT NULL,
    signature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Security Architecture

1. **User Registration**: Generates unique API key and RSA 3072-bit keypair
2. **Key Protection**: Private keys use SHA256(API_key) as GPG passphrase
3. **Authentication**: All endpoints validate API key before processing
4. **Isolation**: Each operation uses temporary GPG homedir for security
5. **No Agent**: GPG agent disabled to prevent interactive prompts

## 🧪 Testing

The project includes comprehensive pytest-based testing with Docker isolation:

```bash
# Run all tests
docker-compose run --rm test-runner pytest tests/ -v

# Run specific test categories
docker-compose run --rm test-runner pytest tests/test_app.py -v
docker-compose run --rm test-runner pytest tests/test_models.py -v
docker-compose run --rm test-runner pytest tests/test_services.py -v
```

### Test Coverage

- ✅ User registration and authentication
- ✅ GPG key generation and storage
- ✅ File signing and verification
- ✅ File encryption and decryption
- ✅ API key authentication
- ✅ Error handling and edge cases

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
      
  test-runner:
    build: .
    profiles: ["test"]
    environment:
      - GPG_AGENT_INFO=""
      - DISPLAY=""
```

### Production Considerations

- Use proper SSL/TLS termination
- Implement rate limiting
- Set up proper logging and monitoring  
- Use production-grade database (PostgreSQL)
- Implement backup strategies for user keys
- Consider HSM integration for key protection

## 📁 Project Structure

```
gpg-webservice/
├── app.py                 # Main Flask application
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── README.md            # This file
│
├── models/              # Database models
│   ├── user.py         # User account model
│   ├── pgp_key.py      # PGP key storage model
│   └── challenge.py    # Challenge model
│
├── services/           # Business logic layer
│   ├── user_service.py    # User management
│   ├── auth_service.py    # Authentication
│   └── challenge_service.py # Challenge handling
│
├── routes/             # HTTP endpoint handlers
│   ├── user_routes.py    # Registration/login endpoints
│   └── gpg_routes.py     # Cryptographic endpoints
│
├── utils/              # Utility functions
│   ├── crypto_utils.py   # Encryption/key derivation
│   ├── gpg_utils.py      # GPG key generation
│   └── gpg_file_utils.py # GPG file operations
│
├── tests/              # Test suite
│   ├── test_app.py       # Integration tests
│   ├── test_models.py    # Model tests
│   └── fixtures/         # Test key fixtures
│
├── db/                 # Database configuration
│   └── database.py      # SQLAlchemy setup
│
└── doc/               # Documentation
    └── overview.md     # Detailed technical overview
```

## 🔧 Configuration

### Environment Variables

- `FLASK_ENV`: Development/production mode
- `DATABASE_URL`: Database connection string (default: SQLite)
- `GPG_AGENT_INFO`: GPG agent configuration (disabled for isolation)
- `DISPLAY`: X11 display (disabled to prevent GUI prompts)

### GPG Configuration

The service automatically configures GPG for isolated operation:

- Temporary homedirs for each operation
- GPG agent disabled to prevent interactive prompts
- Trust model set to "always" for public key operations
- Batch mode enabled for non-interactive operation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `docker-compose run --rm test-runner pytest`
5. Submit a pull request

## 📄 License

This project is for educational and demonstration purposes. Review security considerations before production use.

## 🔍 Troubleshooting

### Common Issues

**GPG Agent Prompts**: The Docker environment completely isolates GPG operations. If running locally, ensure GPG agent is disabled:

```bash
export GPG_AGENT_INFO=""
export DISPLAY=""
```

**Permission Errors**: Ensure proper file permissions for GPG operations:

```bash
chmod 700 ~/.gnupg
```

**Test Failures**: Run tests in Docker for complete isolation:

```bash
docker-compose run --rm test-runner pytest tests/ -v
```

For more detailed information, see `doc/overview.md`.
