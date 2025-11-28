#!/bin/bash
# VPS Deployment Script for GPG Webservice
# =========================================
# Deploys services to VPS via SSH (Caddy handles routing)
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

echo "📝 Setting up environment files..."
bash setup-vps-env.sh

echo "🐳 Stopping old containers..."
docker compose down 2>/dev/null || true

echo "🐳 Building and starting services with VPS config (no TLS, Caddy handles it)..."
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d --build

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo "📊 Service status:"
docker compose -f docker-compose.yml -f docker-compose.vps.yml ps

echo ""
echo "📋 Recent logs:"
docker compose -f docker-compose.yml -f docker-compose.vps.yml logs --tail 20

echo ""
echo "✅ Deployment complete!"
echo ""

# Check if Caddy is running
if command -v caddy >/dev/null 2>&1 && systemctl is-active --quiet caddy; then
  echo "🌐 Caddy detected - services accessible via reverse proxy:"
  echo "   Dashboard: https://\$(hostname)/"
  echo "   REST API:  https://\$(hostname)/api/"
  echo "   MCP:       https://\$(hostname)/mcp/"
  echo ""
  echo "   See docs/CADDY_SETUP.md for configuration"
else
  echo "🌐 Direct access (no Caddy):"
  echo "   Dashboard: http://\$(hostname):8080/"
  echo "   REST API:  http://\$(hostname):5555/"
  echo "   MCP:       http://\$(hostname):3000/"
  echo ""
  echo "   Optional: Set up Caddy for HTTPS and clean URLs"
  echo "   See docs/CADDY_SETUP.md"
fi
ENDSSH

echo ""
echo "🎉 Deployment complete!"
