#!/bin/bash
# Setup environment files on VPS
# This creates the necessary .env files if they don't exist

set -e

echo "📝 Setting up environment files..."

# Root .env
if [ ! -f .env ]; then
  echo "Creating root .env..."
  cat > .env <<'EOF'
# Ports for local development / VPS
FLASK_PORT=5555
MCP_PORT=3000
DASHBOARD_PORT=8080
REST_SECURE_PORT=5443
MCP_SECURE_PORT=3443
DASHBOARD_SECURE_PORT=8443

# Environment
ENVIRONMENT=production
FLASK_ENV=production
LOG_LEVEL=INFO

# Security (CHANGE THESE!)
SECRET_KEY=CHANGE_ME_$(openssl rand -hex 32)
SERVICE_KEY_PASSPHRASE=CHANGE_ME_$(openssl rand -base64 32)

# Admin access
ADMIN_USERNAMES=administrator
ADMIN_GPG_KEYS={}

# Dashboard API URL (for Caddy reverse proxy)
API_URL=https://vps-b5527a39.vps.ovh.net
EOF
  echo "⚠️  WARNING: Edit .env and set proper SECRET_KEY, SERVICE_KEY_PASSPHRASE, and ADMIN_GPG_KEYS"
fi

# gpg-webservice-rest/.env
if [ ! -f gpg-webservice-rest/.env ]; then
  echo "Creating gpg-webservice-rest/.env (inherits from root .env via docker-compose)..."
  mkdir -p gpg-webservice-rest
  cat > gpg-webservice-rest/.env <<'EOF'
# Flask REST API Configuration
# Note: SECRET_KEY, SERVICE_KEY_PASSPHRASE, ADMIN_* are inherited from root .env via docker-compose.yml

# Server
HOST=0.0.0.0
PORT=5555

# Environment
FLASK_ENV=production
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database
DATABASE=/app/gpg_users.db

# Rate limiting
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_AUTH_WINDOW=60
RATE_LIMIT_API_REQUESTS=30
RATE_LIMIT_API_WINDOW=60

# File uploads
MAX_FILE_SIZE_MB=10
MAX_SIGNATURE_SIZE_MB=1
MAX_CONTENT_LENGTH=16777216

# GPG settings
GPG_KEY_LENGTH=3072
GPG_KEY_TYPE=RSA
GNUPGHOME=/tmp/gnupg
EOF
fi

# gpg-webservice-mcp/.env
if [ ! -f gpg-webservice-mcp/.env ]; then
  echo "Creating gpg-webservice-mcp/.env..."
  mkdir -p gpg-webservice-mcp
  cat > gpg-webservice-mcp/.env <<'EOF'
# GPG Webservice MCP Adapter Configuration

# Base URL of the Flask GPG webservice (internal docker network)
GPG_API_BASE=http://gpg-webservice-rest:5555

# HTTP Transport Configuration
MCP_PORT=3000
MCP_HOST=0.0.0.0
EOF
fi

echo "✅ Environment files created"
echo ""
echo "⚠️  IMPORTANT: Edit root .env to set:"
echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
echo "   - SERVICE_KEY_PASSPHRASE (generate with: openssl rand -base64 32)"
echo "   - ADMIN_GPG_KEYS (your GPG public key in JSON format)"
echo ""
echo "These values are automatically passed to services via docker-compose.yml"
