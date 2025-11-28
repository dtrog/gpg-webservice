#!/bin/bash
# Export GPG public key in the correct format for .env file
# Usage: ./scripts/export_gpg_for_env.sh your-email@example.com administrator

set -e

if [ $# -lt 2 ]; then
  echo "Usage: $0 <email-or-key-id> <username>"
  echo ""
  echo "Example:"
  echo "  $0 admin@example.com administrator"
  echo ""
  echo "This will generate the ADMIN_GPG_KEYS line to add to your .env file"
  exit 1
fi

EMAIL="$1"
USERNAME="$2"

echo "📤 Exporting GPG public key for $EMAIL..."
echo ""

# Export the public key
if ! gpg --armor --export "$EMAIL" > /tmp/gpg-export-$$.asc 2>/dev/null; then
  echo "❌ Error: Could not export GPG key for $EMAIL"
  echo ""
  echo "Available keys:"
  gpg --list-keys
  exit 1
fi

# Check if key was exported
if [ ! -s /tmp/gpg-export-$$.asc ]; then
  echo "❌ Error: No key found for $EMAIL"
  echo ""
  echo "Available keys:"
  gpg --list-keys
  rm -f /tmp/gpg-export-$$.asc
  exit 1
fi

# Convert to JSON format (escape newlines as \n)
PUBLIC_KEY=$(cat /tmp/gpg-export-$$.asc | jq -Rs '.')

# Clean up temp file
rm -f /tmp/gpg-export-$$.asc

# Generate the .env line
echo "✅ Success! Add this line to your .env file:"
echo ""
echo "ADMIN_GPG_KEYS='{\"$USERNAME\":$PUBLIC_KEY}'"
echo ""
echo "⚠️  Note: Copy the entire line including the single quotes"
echo ""
echo "Then restart services:"
echo "  cd gpg-webservice"
echo "  docker compose -f docker-compose.yml -f docker-compose.vps.yml restart gpg-webservice-rest"
