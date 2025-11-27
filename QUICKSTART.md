# GPG Webservice - Quick Start Guide

This guide will get you up and running with the GPG Webservice suite
in under 10 minutes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Method 1: Automated Setup (Easiest)](#method-1-automated-setup-easiest)
  - [Method 2: Manual Setup](#method-2-manual-setup)
- [Verification](#verification)
- [First API Call](#first-api-call)
- [Using the Dashboard](#using-the-dashboard)
- [Common Issues](#common-issues)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have:

- [ ] **Docker** (v20.10+) and **Docker Compose** (v2.0+) installed
- [ ] **Git** installed
- [ ] **curl** (for testing API)
- [ ] **OpenSSL** (usually pre-installed on Mac/Linux)
- [ ] At least **2GB free disk space**
- [ ] Ports available: **5555** (API), **3000** (MCP), **8080** (Dashboard)

### Check Prerequisites

```bash
# Check Docker
docker --version          # Should show v20.10+
docker-compose --version  # Should show v2.0+

# Check ports
lsof -i :5555  # Should be empty
lsof -i :3000  # Should be empty
lsof -i :8080  # Should be empty

# Check OpenSSL
openssl version  # Should show OpenSSL 1.1.1+
```

## Installation

### Method 1: Automated Setup (Easiest)

**Estimated time:** 3-5 minutes

```bash
# Step 1: Clone the repository
git clone <repository-url>
cd gpg-webservice

# Step 2: Run automated setup
./setup.sh

# The script will:
# ✓ Check prerequisites
# ✓ Create .env files from templates
# ✓ Generate secure secrets automatically
# ✓ Build Docker images
# ✓ Start all services
# ✓ Run health checks
# ✓ Display access URLs

# Step 3: Wait for setup to complete
# You'll see: "✅ All services are healthy!"
```

**Non-interactive mode** (for CI/CD or scripting):

```bash
./setup.sh --auto
```

---

### Method 2: Manual Setup

**Estimated time:** 5-10 minutes

#### Step 1: Clone Repository

```bash
git clone <repository-url>
cd gpg-webservice
```

#### Step 2: Create Root Environment File

```bash
# Create root .env from template
cp .env.example .env

# Edit if you want custom ports (optional)
nano .env  # or vim .env
```

#### Step 3: Create REST API Environment File

```bash
cd gpg-webservice-rest
cp .env.example .env
```

#### Step 4: Generate Secrets

```bash
# Run the secret generation script
./scripts/generate-secrets.sh

# This generates:
# - SERVICE_KEY_PASSPHRASE (required for GPG operations)
# - SECRET_KEY (required for Flask session security)
```

**Manual secret generation** (if script doesn't work):

```bash
# Generate SERVICE_KEY_PASSPHRASE
echo "SERVICE_KEY_PASSPHRASE=$(openssl rand -base64 32)" >> .env

# Generate SECRET_KEY
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
```

#### Step 5: Return to Root and Build

```bash
cd ..
docker-compose build
```

#### Step 6: Start Services

```bash
docker-compose up -d
```

#### Step 7: Check Status

```bash
# View service status
docker-compose ps

# Should show all services as "healthy":
# NAME                                    STATUS
# gpg-webservice                         Up (healthy)
# gpg-mcp-server                         Up (healthy)
# gpg-dashboard                          Up (healthy)

# View logs
docker-compose logs -f
```

---

## Verification

### 1. Check All Services Are Running

```bash
docker-compose ps
```

Expected output:

```plaintext
NAME                    STATE      PORTS
gpg-webservice          Up         0.0.0.0:5555->5555/tcp
gpg-mcp-server          Up         0.0.0.0:3000->3000/tcp
gpg-dashboard           Up         0.0.0.0:8080->80/tcp
```

### 2. Health Check Endpoints

```bash
# REST API health check
curl http://localhost:5555/openai/function_definitions

# MCP Server health check
curl http://localhost:3000/health

# Dashboard health check
curl http://localhost:8080/health
```

### 3. Access Web Interfaces

- **Dashboard**: Open browser to `http://localhost:8080`
- **API Docs**: `http://localhost:5555/openai/function_definitions`

---

## First API Call

### Step 1: Register a User

```bash
curl -X POST http://localhost:5555/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!",
    "email": "alice@example.com"
  }' | jq
```

**Expected response**:

```json
{
  "username": "alice",
  "api_key": "YjNlZDMxNTg3NDk2NDY5...",
  "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n..."
}
```

**💾 Save your API key!** You'll need it for all subsequent operations.

### Step 2: Sign a File

```bash
# Create a test file
echo "Hello from GPG Webservice!" > test.txt

# Sign the file
curl -X POST http://localhost:5555/sign \
  -H "X-API-KEY: YOUR_API_KEY_HERE" \
  -F "file=@test.txt" \
  -o test.txt.sig

# Check the signature was created
ls -lh test.txt.sig
file test.txt.sig  # Should show: PGP signature
```

### Step 3: Verify the Signature

```bash
curl -X POST http://localhost:5555/verify \
  -H "X-API-KEY: YOUR_API_KEY_HERE" \
  -F "file=@test.txt" \
  -F "signature=@test.txt.sig" | jq
```

**Expected response**:

```json
{
  "valid": true,
  "message": "Signature is valid",
  "signer": "alice@example.com"
}
```

🎉 **Success!** You've successfully signed and verified a file.

---

## Using the Dashboard

### Step 1: Open Dashboard

Navigate to: <http://localhost:8080>

### Step 2: Register via Web UI

1. Click "Register" button
2. Fill in username, email, and password
3. Click "Create Account"
4. **Save your API key** from the response

### Step 3: Sign a File

1. Go to "Sign File" page
2. Enter your API key
3. Choose a file
4. Click "Sign"
5. Download the `.sig` signature file

### Step 4: Verify a Signature

1. Go to "Verify Signature" page
2. Enter your API key
3. Upload original file
4. Upload signature file
5. Click "Verify"

---

## Common Issues

### Issue 1: "SERVICE_KEY_PASSPHRASE environment variable is required"

**Cause**: Missing required environment variable

**Solution**:

```bash
cd gpg-webservice-rest
./scripts/generate-secrets.sh
cd ..
docker-compose restart
```

---

### Issue 2: "Port already in use"

**Cause**: Another service is using ports 5555, 3000, or 8080

**Solution Option A** - Stop conflicting service:

```bash
# Find what's using the port
lsof -i :5555
# Kill the process or stop that service
```

**Solution Option B** - Change port:

```bash
# Edit gpg-webservice-rest/.env
echo "FLASK_PORT=5556" >> gpg-webservice-rest/.env

# Restart
docker-compose down
docker-compose up -d
```

---

### Issue 3: Container exits immediately

**Cause**: Configuration error or missing dependencies

**Solution**:

```bash
# Check logs for detailed error
docker logs gpg-webservice

# Common fixes:
# 1. Verify .env file exists
cd gpg-webservice-rest
ls -la .env

# 2. Verify required variables are set
grep SERVICE_KEY_PASSPHRASE .env

# 3. Regenerate secrets
./scripts/generate-secrets.sh

# 4. Rebuild and restart
cd ..
docker-compose down
docker-compose up -d --build
```

---

### Issue 4: "docker-compose: command not found"

**Cause**: Docker Compose V1 vs V2 naming

**Solution**:

```bash
# Try with space (Compose V2)
docker compose up -d

# Or install compose V1
pip install docker-compose
```

---

### Issue 5: Database file permissions error

**Cause**: Docker volume permissions mismatch

**Solution**:

```bash
# Reset database and volumes
docker-compose down -v
rm -f gpg-webservice-rest/gpg_users.db
docker-compose up -d
```

---

### Issue 6: GPG operations failing

**Cause**: GPG environment corruption

**Solution**:

```bash
# Reset GPG temporary directories
docker-compose down
sudo rm -rf /tmp/gpg-docker /tmp/gpg-test
docker-compose up -d
```

---

### Issue 7: "Module not found" errors

**Cause**: Incomplete Docker build

**Solution**:

```bash
# Force rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Next Steps

### For API Users

1. **Read the API Reference**: [docs/api_reference.md](./gpg-webservice-rest/docs/api_reference.md)
2. **Try all operations**: Sign, Verify, Encrypt, Decrypt
3. **Integrate with your application**: Use the REST API from your code

### For Developers

1. **Understand the architecture**: [docs/architecture.md](./gpg-webservice-rest/docs/architecture.md)
2. **Review code patterns**: [docs/gpg_command_builder_guide.md](./gpg-webservice-rest/docs/gpg_command_builder_guide.md)
3. **Set up development environment**: [docs/development.md](./gpg-webservice-rest/docs/development.md)

### For Production Deployment

1. **Read deployment guide**: [DEPLOYMENT.md](./gpg-webservice-rest/DEPLOYMENT.md)
2. **Configure PostgreSQL**: Replace SQLite for production
3. **Set up HTTPS**: Use reverse proxy (nginx/Traefik)
4. **Configure monitoring**: Set up logging and metrics

---

## Quick Reference Card

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart gpg-webservice

# Run tests
docker-compose run --rm test-runner

# Generate new secrets
cd gpg-webservice-rest && ./scripts/generate-secrets.sh

# Reset everything
docker-compose down -v && rm -f gpg-webservice-rest/gpg_users.db
```

---

## Getting Help

- 📖 **Full Documentation**: [README.md](./README.md)
- 🏗️ **Architecture**: [docs/architecture.md](./gpg-webservice-rest/docs/architecture.md)
- 🔐 **Security**: [docs/security.md](./gpg-webservice-rest/docs/security.md)
- 🐛 **Report Issues**: `https://github.com/dtrog/gpg-webservice/issues`

---

**Estimated Setup Time Summary:**

- Automated setup: **3-5 minutes**
- Manual setup: **5-10 minutes**
- First API call: **2 minutes**
- **Total**: **10-17 minutes** to fully operational system

🎉 **You're all set!** Happy signing!
