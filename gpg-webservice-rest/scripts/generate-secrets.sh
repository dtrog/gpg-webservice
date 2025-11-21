#!/bin/bash
# generate-secrets.sh
# Generates secure secrets for .env file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

echo "🔐 GPG Webservice Secret Generator"
echo "=================================="
echo ""

# Check if .env exists
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: .env file already exists at: $ENV_FILE"
    read -p "Do you want to regenerate secrets? This will UPDATE existing .env file. (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled. Existing .env file preserved."
        exit 0
    fi
else
    echo "📝 Creating new .env file from .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
fi

echo ""
echo "🔑 Generating secrets..."
echo ""

# Generate SERVICE_KEY_PASSPHRASE
SERVICE_KEY_PASSPHRASE=$(openssl rand -base64 32)
echo "✓ Generated SERVICE_KEY_PASSPHRASE: ${SERVICE_KEY_PASSPHRASE:0:16}... (hidden)"

# Generate SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)
echo "✓ Generated SECRET_KEY: ${SECRET_KEY:0:16}... (hidden)"

# Update .env file
if grep -q "^SERVICE_KEY_PASSPHRASE=" "$ENV_FILE"; then
    sed -i.bak "s|^SERVICE_KEY_PASSPHRASE=.*|SERVICE_KEY_PASSPHRASE=$SERVICE_KEY_PASSPHRASE|" "$ENV_FILE"
else
    echo "SERVICE_KEY_PASSPHRASE=$SERVICE_KEY_PASSPHRASE" >> "$ENV_FILE"
fi

if grep -q "^SECRET_KEY=" "$ENV_FILE"; then
    sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$ENV_FILE"
else
    echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
fi

# Remove backup file
rm -f "$ENV_FILE.bak"

echo ""
echo "✅ Secrets generated and saved to: $ENV_FILE"
echo ""
echo "⚠️  IMPORTANT: Keep your .env file secure and NEVER commit it to version control!"
echo ""
