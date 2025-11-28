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
