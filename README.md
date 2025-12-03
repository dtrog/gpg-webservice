# GPG Webservice - Complete System

A comprehensive, production-ready GPG (GNU Privacy Guard) service suite
providing cryptographic operations via a REST API, an MCP (Model
Context Protocol) server, and a web dashboard.

## 🏗️ Architecture Overview

This is a **multi-service system** consisting of three components:

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                    GPG Webservice Suite                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐   │
│  │   REST API       │  │   MCP Server     │  │Dashboard │   │
│  │  (Flask/Python)  │  │  (Node.js/TS)    │  │ (Nginx)  │   │
│  │   Port: 5555     │  │   Port: 3000     │  │Port: 8080│   │
│  └────────┬─────────┘  └────────┬─────────┘  └─────┬────┘   │
│           │                     │                   │       │
│           └─────────────────────┴───────────────────┘       │
│                                 │                           │
│                       ┌─────────▼─────────┐                 │
│                       │  Shared Network   │                 │
│                       │  (Docker Bridge)  │                 │
│                       └───────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **GPG Webservice** (`gpg-webservice-rest/`)
   - Flask REST API for GPG operations
   - Operations: Sign, Verify, Encrypt, Decrypt
   - Deterministic session key authentication (ideal for AI agents)
   - SQLAlchemy ORM with SQLite/PostgreSQL support
   - **Port**: 5555

2. **MCP Server** (`gpg-webservice-mcp/`)
   - Model Context Protocol server for AI agents
   - Provides GPG functions to Claude/other AI agents
   - Proxies requests to REST API
   - **Port**: 3000

3. **Dashboard** (`gpg-webservice-dashboard/`)
   - Web UI for user registration and key management
   - File signing/verification interface
   - Built with vanilla JavaScript and Nginx
   - **Port**: 8080

## 📁 Project Structure

```plaintext
gpg-webservice/                       # ← You are here (root)
├── README.md                         # This file
├── QUICKSTART.md                     # Step-by-step getting started
├── docker-compose.yml                # Orchestrates all 3 services
├── docker-compose.dev.yml            # Development overrides
├── .env.example                      # Environment template
├── .env                              # Your config (create from .env.example)
│
├── gpg-webservice-rest/              # Flask REST API
│   ├── README.md                     # REST API documentation
│   ├── app.py                        # Main application
│   ├── requirements.txt              # Python dependencies
│   ├── docker-compose.yml            # Standalone REST API compose
│   ├── Dockerfile
│   ├── .env                          # REST-specific config
│   ├── models/                       # Database models
│   ├── routes/                       # API endpoints
│   ├── services/                     # Business logic
│   ├── utils/                        # GPG & crypto utilities
│   ├── tests/                        # Test suite
│   ├── docs/                         # Comprehensive documentation
│   │   ├── architecture.md           # System architecture
│   │   ├── api_reference.md          # API documentation
│   │   ├── gpg_command_builder_guide.md  # Builder pattern guide
│   │   └── refactoring_changelog_2025.md # Recent improvements
│   └── scripts/
│       └── admin_gpg_auth.sh         # Admin GPG Authentication helper
│       └── generate-secrets.sh       # Secret generation
│       └── setup.sh                  # Automated setup script
│
├── gpg-webservice-mcp/               # MCP Server
│   ├── README.md
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── src/                          # TypeScript source
│
└── gpg-webservice-dashboard/         # Web Dashboard
    ├── README.md
    ├── Dockerfile
    ├── nginx.conf
    ├── index.html
    ├── js/                           # Frontend JavaScript
    └── css/                          # Stylesheets
```

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (v2.0+)
- **Git**
- **OpenSSL** (for secret generation)

### Option 1: Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd gpg-webservice

# 2. Run automated setup (interactive)
./setup.sh

# 3. Access the services
# REST API: http://localhost:5555
# MCP Server: http://localhost:3000
# Dashboard: http://localhost:8080
```

### Option 2: Manual Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd gpg-webservice

# 2. Create environment files
cp .env.example .env
cd gpg-webservice-rest
cp .env.example .env

# 3. Generate secrets
./scripts/generate-secrets.sh

# 4. Start all services
cd ..
docker-compose up -d

# 5. Check status
docker-compose ps
docker-compose logs -f
```

### Option 3: Automated Setup (Non-interactive)

```bash
./scripts/setup.sh --auto
```

## 📚 Documentation

### Quick Links

|Document|Description|
|--------|-----------|
|[QUICKSTART.md](./QUICKSTART.md)|Detailed getting started guide|
|[REST API Docs](./gpg-webservice-rest/README.md)|Complete REST API documentation|
|[Architecture Guide](./gpg-webservice-rest/docs/architecture.md)|System architecture & design patterns|
|[API Reference](./gpg-webservice-rest/docs/api_reference.md)|Endpoint documentation with examples|
|[GPG Command Builder](./gpg-webservice-rest/docs/gpg_command_builder_guide.md)|Developer guide for GPG operations|
|[MCP Server Docs](./gpg-webservice-mcp/README.md)|MCP server setup and usage|
|[Dashboard Docs](./gpg-webservice-dashboard/README.md)|Web dashboard guide|

### For Different Audiences

#### 🎯 API Users

1. [QUICKSTART.md](./QUICKSTART.md) - Get up and running
2. [API Reference](./gpg-webservice-rest/docs/api_reference.md)  
  All endpoints with examples
3. Test with:  
  `curl http://localhost:5555/openai/function_definitions`

#### 👨‍💻 Developers

1. [Architecture Guide](./gpg-webservice-rest/docs/architecture.md)  
  Understand the system
2. [Development Guide](./gpg-webservice-rest/docs/development.md)  
  Setup dev environment
3. [Refactoring Changelog](./gpg-webservice-rest/docs/refactoring_changelog_2025.md)  
  Recent improvements

#### 🔒 Security Reviewers

1. [Security Architecture](./gpg-webservice-rest/docs/overview.md#security-architecture)
2. [Threat Model](./gpg-webservice-rest/docs/security.md)
3. [OWASP Compliance](./gpg-webservice-rest/docs/security.md#owasp-compliance)

## 🔧 Configuration

### Environment Variables

Key variables (see `.env.example` for complete list):

```bash
# Flask Service
PORT=5555
SECRET_KEY=<generated-by-setup-script>
SERVICE_KEY_PASSPHRASE=<generated-by-setup-script>  # ⚠️ REQUIRED
FLASK_ENV=development

# MCP Server
MCP_PORT=3000
GPG_API_BASE=http://localhost:5555

# Dashboard
DASHBOARD_PORT=8080
API_URL=http://localhost:5555
```

### Port Configuration

| Service    | Default Port | Environment Variable | Change In                  |
|------------|--------------|----------------------|----------------------------|
| REST API   | 5555         | `FLASK_PORT`         | `gpg-webservice-rest/.env` |
| MCP Server | 3000         | `MCP_PORT`           | Root `.env` or MCP `.env`  |
| Dashboard  | 8080         | `DASHBOARD_PORT`     | Root `.env`                |

## 🐳 Docker Commands

### Basic Operations

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
docker-compose logs -f gpg-webservice  # Specific service

# Check status
docker-compose ps

# Stop services
docker-compose down

# Restart specific service
docker-compose restart gpg-webservice

# Rebuild after code changes
docker-compose up -d --build
```

### Development Mode

```bash
# Start with dev overrides (hot-reload, debug mode)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Run tests
docker-compose run --rm test-runner
```

### Troubleshooting

```bash
# Check service health
curl http://localhost:5555/openai/function_definitions
curl http://localhost:3000/health
curl http://localhost:8080/health

# View container logs
docker logs gpg-webservice

# Enter container for debugging
docker exec -it gpg-webservice /bin/bash

# Reset everything
docker-compose down -v
rm -rf gpg-webservice-rest/gpg_users.db
docker-compose up -d
```

## 🧪 Testing

### Run Full Test Suite

```bash
# Using Docker (recommended)
docker-compose run --rm test-runner

# Local (requires Python 3.11+)
cd gpg-webservice-rest
python -m pytest tests/ -v
```

### Quick API Test

```bash
# 1. Register a user (returns deterministic session key)
curl -X POST http://localhost:5555/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123!@#","email":"test@example.com"}'

# Response contains session key (sk_...), session_window, and expires_at
# Session keys rotate hourly - re-login to get new key when expired

# 2. Sign a file (use X-Username with session keys)
echo "Hello World" > test.txt
curl -X POST http://localhost:5555/sign \
  -H "X-API-KEY: sk_your_session_key" \
  -H "X-Username: testuser" \
  -F "file=@test.txt" \
  -o test.txt.sig

# 3. Verify signature
curl -X POST http://localhost:5555/verify \
  -H "X-API-KEY: sk_your_session_key" \
  -H "X-Username: testuser" \
  -F "file=@test.txt" \
  -F "signature=@test.txt.sig"
```

## 🚨 Common Issues

### Issue: "SERVICE_KEY_PASSPHRASE environment variable is required"

**Solution**:

```bash
cd gpg-webservice-rest
./scripts/generate-secrets.sh
docker-compose up -d
```

### Issue: "Port already in use"

**Solution**:

```bash
# Check what's using the port
lsof -i :5555

# Change port in .env
echo "FLASK_PORT=5556" >> gpg-webservice-rest/.env
docker-compose up -d
```

### Issue: "Container exits immediately"

**Solution**:

```bash
# Check logs for detailed error
docker logs gpg-webservice

# Common fixes:
# 1. Ensure .env file exists and has required variables
# 2. Regenerate secrets: ./scripts/generate-secrets.sh
# 3. Check Docker resources (memory, disk space)
```

### Issue: "GPG operations failing"

**Solution**:

```bash
# Reset GPG environment
docker-compose down
rm -rf /tmp/gpg-docker /tmp/gpg-test
docker-compose up -d
```

## 📊 Production Deployment

### Using Docker Compose

```bash
# 1. Set production environment
echo "FLASK_ENV=production" >> gpg-webservice-rest/.env
echo "DEBUG=false" >> gpg-webservice-rest/.env

# 2. Generate production secrets
cd gpg-webservice-rest
./scripts/generate-secrets.sh

# 3. Use PostgreSQL (recommended)
echo "DATABASE_URL=postgresql://user:pass@host:5432/gpg_db" >> .env

# 4. Start services
docker-compose up -d
```

See [DEPLOYMENT.md](./gpg-webservice-rest/DEPLOYMENT.md) for detailed
production setup.

## 🔐 Security Features

- **Deterministic Session Keys**: Stateless authentication ideal for AI
  agents (hourly rotation)
- **Argon2id Password Hashing**: OWASP-recommended (4 iterations,
  64MB memory)
- **AES-256-GCM Encryption**: For private key storage
- **PBKDF2-HMAC-SHA256**: 100,000 iterations for key derivation
- **Rate Limiting**: Protection against brute force attacks
- **Process Isolation**: GPG operations in isolated temporary
  directories
- **Input Validation**: Comprehensive validation on all inputs
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **No Secret Storage**: Session keys derived mathematically, not
  stored in database

## 🤝 Contributing

We welcome contributions! See individual service READMEs for contribution guidelines:

- [REST API Contributing](./gpg-webservice-rest/docs/development.md#contributing-guidelines)
- [MCP Server Contributing](./gpg-webservice-mcp/README.md#contributing)
- [Dashboard Contributing](./gpg-webservice-dashboard/README.md#contributing)

## 📄 License

MIT License - See [LICENSE](./gpg-webservice-rest/LICENSE)

## 🔗 Links

- **Documentation**: [./gpg-webservice-rest/docs/](./gpg-webservice-rest/docs/)
- **Issue Tracker**: `https://github.com/dtrog/gpg-webservice/issues`
- **Changelog**: [./gpg-webservice-rest/CHANGES.md](./gpg-webservice-rest/CHANGES.md)

## 📞 Support

- 📖 Check [QUICKSTART.md](./QUICKSTART.md) for setup help
- 🐛 Report issues in the issue tracker
- 💬 Read the comprehensive docs in `gpg-webservice-rest/docs/`
- 🔍 Search existing issues before creating new ones

---

**Quick Commands Cheat Sheet:**

```bash
./scripts/setup.sh
./scripts/setup.sh --auto
docker-compose up -d
docker-compose logs -f
docker-compose ps
docker-compose down
docker-compose run --rm test-runner
```

**Made with ❤️** using **Flask**, **Node.js**, **GPG**
