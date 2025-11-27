#!/bin/bash
# VPS Deployment Script for GPG Webservice
# =========================================
# Deploys the unified service to VPS via SSH

set -e

VPS_HOST="${VPS_HOST:-ubuntu@vps-b5527a39.vps.ovh.net}"
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
echo "🌐 Service accessible at:"
echo "   Dashboard: http://vps-b5527a39.vps.ovh.net/"
echo "   REST API:  http://vps-b5527a39.vps.ovh.net/api/"
echo "   MCP:       http://vps-b5527a39.vps.ovh.net/mcp/"
ENDSSH

echo ""
echo "🎉 Done! Check the service:"
echo "   curl http://vps-b5527a39.vps.ovh.net/api/openai/function_definitions"
