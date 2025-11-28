#!/bin/bash
# VPS Deployment Script for GPG Webservice
# =========================================
# Deploys the unified service to VPS via SSH
#
# Usage:
#   VPS_HOST=user@your-server.com ./deploy-vps.sh

set -e

if [ -z "$VPS_HOST" ]; then
  echo "❌ Error: VPS_HOST environment variable not set"
  echo ""
  echo "Usage:"
  echo "  VPS_HOST=user@your-server.com ./deploy-vps.sh"
  echo ""
  echo "Example:"
  echo "  VPS_HOST=ubuntu@your-vps.example.com ./deploy-vps.sh"
  exit 1
fi

DEPLOY_DIR="${DEPLOY_DIR:-gpg-webservice}"

echo "🚀 Deploying to VPS: $VPS_HOST"
echo "📁 Deploy directory: $DEPLOY_DIR"
echo ""

# Push latest code
echo "📤 Pushing latest code to GitHub..."
git push origin main

# SSH into VPS and deploy
echo "🔧 Deploying on VPS..."
ssh "$VPS_HOST" <<'ENDSSH'
set -e
cd gpg-webservice

echo "📥 Pulling latest code..."
git pull

echo "🔧 Creating data directory for persistence..."
mkdir -p data/gnupg
chmod 700 data/gnupg

echo "📝 Checking for .env file..."
if [ ! -f .env ]; then
  echo "⚠️  Creating .env file with default values..."
  cat > .env <<'ENVEOF'
# Flask REST API
FLASK_ENV=production
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=CHANGE_ME_$(openssl rand -hex 32)
SERVICE_KEY_PASSPHRASE=CHANGE_ME_$(openssl rand -base64 32)
ADMIN_USERNAMES=administrator
ADMIN_GPG_KEYS={}

# Database
DATABASE=/app/rest/gpg_users.db

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
ENVEOF
  echo "⚠️  WARNING: Please edit .env and set proper SECRET_KEY, SERVICE_KEY_PASSPHRASE, and ADMIN_GPG_KEYS"
  echo "⚠️  Then run: docker compose -f docker-compose.vps.yml restart"
fi

echo "🐳 Stopping old containers..."
docker compose down 2>/dev/null || true
docker compose -f docker-compose.vps.yml down 2>/dev/null || true

echo "🐳 Building and starting unified service..."
docker compose -f docker-compose.vps.yml down
docker compose -f docker-compose.vps.yml up -d --build

echo "⏳ Waiting for service to be healthy..."
sleep 5

echo "📊 Service status:"
docker compose -f docker-compose.vps.yml ps

echo ""
echo "📋 Recent logs:"
docker compose -f docker-compose.vps.yml logs --tail 20

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Service should be accessible at:"
echo "   Dashboard: http://\$VPS_HOST/"
echo "   REST API:  http://\$VPS_HOST/api/"
echo "   MCP:       http://\$VPS_HOST/mcp/"
ENDSSH

echo ""
echo "🎉 Done! Check the service:"
echo "   curl http://YOUR_VPS_HOST/api/openai/function_definitions"
