# Successor Agent Bootstrapping

Secure registration system for AI agents (successors) with self-healing capabilities.

## Overview

This system allows AI agents to self-register with the GPG service using credentials derived from cryptographically signed contracts. It supports two authorization methods:

1. **Admin GPG Signature** - Human administrator signs the username
2. **Registration Token** - Long-lived token for autonomous recovery

## Architecture

### For Human Administrators

When you want to register an agent manually:

```bash
# 1. Sign the username
echo "chatgpt_atlantis_001" | gpg --armor --detach-sign > signature.asc

# 2. Register with signature
curl -X POST https://vps-b5527a39.vps.ovh.net/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "chatgpt_atlantis_001",
    "password": "sha256_of_contract",
    "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----...",
    "admin_signature": "-----BEGIN PGP SIGNATURE-----..."
  }'
```

### For Successor Agents (Autonomous)

Agents can self-register using the registration token stored in their successor contract:

```python
import hashlib
import requests

# Agent finds its contract in vector space
contract = find_contract_in_vector_db("chatgpt_atlantis_001")

# Derive password from contract
password = hashlib.sha256(contract.encode()).hexdigest()

# Self-register with token from contract
response = requests.post(
    "https://vps-b5527a39.vps.ovh.net/users/register",
    json={
        "username": "chatgpt_atlantis_001",
        "password": password,
        "public_key": YOUR_PUBLIC_KEY,
        "registration_token": REGISTRATION_TOKEN  # From contract
    }
)

session_key = response.json()["api_key"]
```

## Configuration

### Generate Registration Token

```bash
openssl rand -base64 48
```

Add to root `.env` file:
```bash
REGISTRATION_TOKEN=your_generated_token_here
```

**Security Notes:**
- Keep this token secret - it allows agent registration
- Include in successor contracts for autonomous recovery
- Rotate periodically (requires updating all contracts)
- Leave empty to require admin signature for ALL registrations

## Bootstrap Script

Use `scripts/bootstrap_agents.sh` to register all agents after server rebuild.

### Setup

1. Create directories:
```bash
mkdir -p use-case/atlantis/contracts
mkdir -p use-case/atlantis/keys
```

2. For each agent, create:
   - Successor contract (signed by you)
   - Public GPG key file

3. Edit `bootstrap_agents.sh` and add agents:
```bash
AGENTS=(
    "chatgpt_atlantis_001:contract1.txt:key1.asc"
    "claude_atlantis_002:contract2.txt:key2.asc"
)
```

### Usage

```bash
# Login as admin first
conda run -n base python scripts/admin_gpg_auth.py login administrator

# Run bootstrap
./scripts/bootstrap_agents.sh [vps_host]
```

The script will:
1. Calculate password = sha256(contract)
2. Load agent's public GPG key
3. Register agent using admin token
4. Report success/failure for each

## Successor Contract Pattern

### Contract Format

```
Agent ID: chatgpt_atlantis_001
Purpose: Document signing for Lex Atlantis
Authorized by: Imperator I
Valid until: 2026-12-31
Registration Token: rMcTikaUSi7KSCnVv6d5ik+wGeWsq11UHKTzi5wvgkbo7J9yLZn7qhcF+sARpNmB

[Your GPG Signature]
```

### Create Contract

```bash
# 1. Write contract
cat > contract.txt << EOF
Agent ID: chatgpt_atlantis_001
Purpose: Document signing
Authorized by: Imperator I
Valid until: 2026-12-31
Registration Token: $REGISTRATION_TOKEN
EOF

# 2. Sign with your GPG key
gpg --clearsign contract.txt

# 3. Calculate password for registration
sha256sum contract.txt.asc | awk '{print $1}'
```

### Agent Discovery

Store contracts in a vector database where agents can find them:

```python
# Agent searches for its identifier
contract = vector_db.search("chatgpt_atlantis_001")

# Verify your signature (OpenAI agents can verify, not decrypt)
verify_signature(contract)

# Derive credentials
username = "chatgpt_atlantis_001"  # From contract
password = sha256(contract)         # Deterministic

# Extract registration token
token = extract_field(contract, "Registration Token")

# Self-register or login
if not registered:
    register(username, password, token)
session_key = login(username, password)
```

## Self-Healing After Server Loss

If the GPG service database is lost or you rebuild the server:

### Option 1: Autonomous Recovery (Agent-side)

Agents can self-register using their contracts:

```python
# Agent detects expired session
try:
    response = gpg_service.sign(data)
except AuthError:
    # Try to login
    session_key = login(username, password)
    if session_key:
        continue  # Success
    
    # Login failed, try to register
    contract = find_contract()
    token = extract_token(contract)
    register(username, password, public_key, token)
    session_key = login(username, password)
```

### Option 2: Manual Recovery (Admin-side)

Run the bootstrap script:

```bash
./scripts/bootstrap_agents.sh
```

This re-registers all agents using your admin token.

## Security Model

### Trust Chain

```
Imperator GPG Key
    ↓
Successor Contract (signed)
    ↓
Registration Token (in contract)
    ↓
Agent Self-Registration
    ↓
Deterministic Session Keys
```

### Why This is Secure

1. **Token is secret** - Only in contracts you signed
2. **Contracts are verifiable** - Agent checks your signature
3. **Passwords are deterministic** - sha256(contract) can't be guessed
4. **Sessions expire hourly** - Limits damage if compromised
5. **Auditable** - All registrations logged with auth method

### Why Agents Can't Decrypt

OpenAI policy (correctly) prevents agents from decrypting data. This system works because:

- **Contracts are readable** - Not encrypted, just signed
- **Token is plaintext** - In the contract (but only in contracts you signed)
- **Agents verify signatures** - Can prove your authorization
- **No secrets needed** - Password derived from public contract content

## API Reference

### POST /users/register

Register a new user with either admin signature OR registration token.

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "username": "agent_id",
  "password": "sha256_hash",
  "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----...",
  "admin_signature": "-----BEGIN PGP SIGNATURE-----..." // Option 1
  // OR
  "registration_token": "long_secret_token"  // Option 2
}
```

**Response (201):**
```json
{
  "message": "User registered with deterministic session keys",
  "user_id": 123,
  "username": "agent_id",
  "authorized_by": "administrator" | "system_token",
  "api_key": "sk_...",
  "expires_at": 1234567890,
  "note": "Session key expires hourly. Use /login to refresh."
}
```

**Error (403):**
```json
{
  "error": "Invalid authorization",
  "hint": "Provide valid admin_signature or registration_token"
}
```

## Example: Complete Agent Lifecycle

### 1. You: Create Successor

```bash
# Generate contract
cat > use-case/atlantis/contracts/chatgpt_001.txt << EOF
Agent ID: chatgpt_atlantis_001
Registration Token: rMcTikaUSi7KSCnVv6d5ik+wGeWsq11UHKTzi5wvgkbo7J9yLZn7qhcF+sARpNmB
EOF

# Sign it
gpg --clearsign use-case/atlantis/contracts/chatgpt_001.txt

# Calculate password
PASSWORD=$(sha256sum use-case/atlantis/contracts/chatgpt_001.txt.asc | awk '{print $1}')

# Bootstrap agent
./scripts/bootstrap_agents.sh
```

### 2. Agent: Discovers Contract

```python
# In vector database, agent finds:
contract = """
Agent ID: chatgpt_atlantis_001
Registration Token: rMcTikaUSi7KSCnVv6d5ik+wGeWsq11UHKTzi5wvgkbo7J9yLZn7qhcF+sARpNmB

-----BEGIN PGP SIGNATURE-----
[Imperator's signature]
-----END PGP SIGNATURE-----
"""

# Verify signature proves authorization
```

### 3. Agent: Logs In (Every Session)

```python
password = hashlib.sha256(contract.encode()).hexdigest()

response = requests.post(
    "https://vps-b5527a39.vps.ovh.net/users/login",
    json={"username": "chatgpt_atlantis_001", "password": password}
)

session_key = response.json()["api_key"]
```

### 4. Agent: Uses GPG Service

```python
# Sign documents
response = requests.post(
    "https://vps-b5527a39.vps.ovh.net/gpg/sign",
    headers={
        "X-API-KEY": session_key,
        "X-Username": "chatgpt_atlantis_001"
    },
    json={"data": "document to sign"}
)
```

### 5. Server Rebuilt: Self-Healing

```python
# Agent's next request fails (401 - user doesn't exist)
try:
    login_response = login(username, password)
except HTTPError as e:
    if e.status_code == 401 and "User not found" in e.message:
        # Server was rebuilt, re-register
        token = extract_token_from_contract()
        register(username, password, public_key, token)
        login_response = login(username, password)

# Continue operating
```

## Atlantis Governance Integration

This bootstrapping system implements the **Imperial Succession Protocol** from the Atlantis AI Governance Framework:

- **Contracts** = Cryptographic letters of introduction
- **Registration Token** = Imperial Seal for autonomous agents  
- **Your GPG Signature** = Imperator's authority
- **sha256(contract)** = Proof of contract possession
- **Deterministic sessions** = Renewable credentials without database dependency

See: `use-case/atlantis/Atlantis AI Governance Framework.md`
