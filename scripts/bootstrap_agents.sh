#!/bin/bash
#
# Bootstrap Successor Agents
# ===========================
# Registers all successor AI agents with the GPG service after server rebuild.
#
# Usage:
#   ./scripts/bootstrap_agents.sh [vps_host]
#
# Prerequisites:
#   - Admin GPG authentication completed (token in ~/.gpg-webservice-admin-token)
#   - Successor contracts in use-case/atlantis/contracts/
#   - Agent GPG keys in use-case/atlantis/keys/
#
# For Atlantis governance framework, this implements the successor bootstrapping
# where agents derive their credentials from signed contracts.

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTRACTS_DIR="$PROJECT_ROOT/use-case/atlantis/contracts"
KEYS_DIR="$PROJECT_ROOT/use-case/atlantis/keys"

# API endpoint
VPS_HOST="${1:-${VPS_HOST:-vps-b5527a39.vps.ovh.net}}"
API_URL="https://$VPS_HOST"

# Get admin token
ADMIN_TOKEN_FILE="$HOME/.gpg-webservice-admin-token"
if [ ! -f "$ADMIN_TOKEN_FILE" ]; then
    echo "❌ Admin token not found at $ADMIN_TOKEN_FILE"
    echo "   Run: conda run -n base python scripts/admin_gpg_auth.py login administrator"
    exit 1
fi

ADMIN_TOKEN=$(cat "$ADMIN_TOKEN_FILE")

echo "🤖 GPG Service - Successor Agent Bootstrap"
echo "   API: $API_URL"
echo "   Contracts: $CONTRACTS_DIR"
echo "   Keys: $KEYS_DIR"
echo ""

# Check if directories exist
if [ ! -d "$CONTRACTS_DIR" ]; then
    echo "⚠️  Contracts directory not found: $CONTRACTS_DIR"
    echo "   Creating directory..."
    mkdir -p "$CONTRACTS_DIR"
fi

if [ ! -d "$KEYS_DIR" ]; then
    echo "⚠️  Keys directory not found: $KEYS_DIR"
    echo "   Creating directory..."
    mkdir -p "$KEYS_DIR"
fi

# Agent definitions: username:contract_file:key_file
AGENTS=(
    # Example: "chatgpt_atlantis_001:chatgpt_001_contract.txt:chatgpt_001.asc"
    # Add your agents here
)

if [ ${#AGENTS[@]} -eq 0 ]; then
    echo "⚠️  No agents defined in AGENTS array"
    echo ""
    echo "To add agents, edit this script and add entries like:"
    echo '  AGENTS+=("chatgpt_atlantis_001:contract.txt:key.asc")'
    echo ""
    echo "Agent registration pattern:"
    echo "  1. Create successor contract (signed by you)"
    echo "  2. Save contract to: $CONTRACTS_DIR/contract.txt"
    echo "  3. Export agent's public GPG key to: $KEYS_DIR/key.asc"
    echo "  4. Password = sha256sum of contract"
    echo "  5. Add agent to AGENTS array above"
    echo "  6. Run this script"
    exit 0
fi

# Register each agent
SUCCESSFUL=0
FAILED=0

for entry in "${AGENTS[@]}"; do
    IFS=':' read -r username contract_file key_file <<< "$entry"
    
    echo "──────────────────────────────────────────────────────"
    echo "📝 Agent: $username"
    
    # Check if contract exists
    CONTRACT_PATH="$CONTRACTS_DIR/$contract_file"
    if [ ! -f "$CONTRACT_PATH" ]; then
        echo "   ❌ Contract not found: $CONTRACT_PATH"
        ((FAILED++))
        continue
    fi
    
    # Check if key exists
    KEY_PATH="$KEYS_DIR/$key_file"
    if [ ! -f "$KEY_PATH" ]; then
        echo "   ❌ Key not found: $KEY_PATH"
        ((FAILED++))
        continue
    fi
    
    # Calculate password from contract
    echo "   🔐 Deriving password from contract..."
    PASSWORD=$(sha256sum "$CONTRACT_PATH" | awk '{print $1}')
    
    # Load public key
    echo "   🔑 Loading public key..."
    PUBLIC_KEY=$(cat "$KEY_PATH")
    
    # Prepare JSON payload
    echo "   📤 Registering with GPG service..."
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/users/register" \
        -H "Content-Type: application/json" \
        -H "X-Admin-Token: $ADMIN_TOKEN" \
        -d "$(jq -n \
            --arg username "$username" \
            --arg password "$PASSWORD" \
            --arg public_key "$PUBLIC_KEY" \
            '{username: $username, password: $password, public_key: $public_key}'
        )")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" = "201" ]; then
        echo "   ✅ Successfully registered"
        SESSION_KEY=$(echo "$BODY" | jq -r '.api_key // empty')
        if [ -n "$SESSION_KEY" ]; then
            echo "   🔑 Session key: ${SESSION_KEY:0:20}..."
        fi
        ((SUCCESSFUL++))
    else
        echo "   ❌ Registration failed (HTTP $HTTP_CODE)"
        ERROR=$(echo "$BODY" | jq -r '.error // empty')
        if [ -n "$ERROR" ]; then
            echo "   Error: $ERROR"
        fi
        ((FAILED++))
    fi
    
    echo ""
done

echo "══════════════════════════════════════════════════════"
echo "📊 Bootstrap Summary"
echo "   ✅ Successful: $SUCCESSFUL"
echo "   ❌ Failed: $FAILED"
echo "   Total: $((SUCCESSFUL + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All agents registered successfully!"
    exit 0
else
    echo "⚠️  Some agents failed to register"
    exit 1
fi
