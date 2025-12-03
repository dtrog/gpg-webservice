# Admin GPG Authentication

Non-expiring authentication for human administrators using GPG signatures.

## Overview

The GPG Webservice supports two authentication methods for admin operations:

1. **Session Keys** (AI Agents): Expire after 1 hour, require re-login
   - Use `X-API-KEY` + `X-Username` headers
   - Configured via `ADMIN_USERNAMES` environment variable

2. **GPG Tokens** (Human Admins): Valid for 24 hours, no database storage
   - Use `X-Admin-Token` header  
   - Configured via `ADMIN_GPG_KEYS` environment variable
   - Admin public keys stored in .env only

## Why GPG Authentication for Admins?

- **No expiring keys**: Human admins don't need to re-login hourly
- **No database storage**: Admin public keys live in .env, not DB
- **Cryptographic proof**: Challenge-response with GPG signatures
- **Separate from AI agents**: Different security model for humans vs agents

## Setup

### 1. Generate or Export Your GPG Key

```bash
# If you don't have a GPG key, create one:
gpg --gen-key

# Export your public key:
gpg --armor --export your-email@example.com > admin-pubkey.asc
```

### 2. Add Public Key to Environment

Convert your public key to single-line JSON format:

```bash
# Method 1: Using helper script (recommended)
./scripts/export_gpg_for_env.sh your-email@example.com administrator

# Method 2: Using jq manually
cat admin-pubkey.asc | jq -Rs '{administrator: .}' | jq -c

# Method 3: Manual (escape newlines as \n in your editor)
# Replace actual newlines with \n (single backslash-n)
```

Copy the output and add it to **root `.env`** file on the VPS:

```bash
ADMIN_GPG_KEYS='{"administrator":"-----BEGIN PGP PUBLIC KEY BLOCK-----\nVersion: GnuPG v2\n\nmQENBF...\n-----END PGP PUBLIC KEY BLOCK-----\n"}'
```

**Important**: 
- Add this to the **root `.env` file** (not `gpg-webservice-rest/.env`)
- The root `.env` is the single source of truth - `docker-compose.yml` passes these values to all services
- The value must be a single-line JSON string with `\n` (single backslash-n) for newlines
- Ensure the entire JSON value is wrapped in single quotes
- The helper script `export_gpg_for_env.sh` outputs the correct format

### 3. Restart Services

```bash
cd gpg-webservice
docker compose -f docker-compose.yml -f docker-compose.vps.yml restart gpg-webservice-rest
```

## Usage

### Interactive Login (Recommended)

```bash
# If using conda:
conda run -n base python scripts/admin_gpg_auth.py login administrator [gpg-key-id]

# Or with system Python (if requests is installed):
python3 scripts/admin_gpg_auth.py login administrator [gpg-key-id]
```

**Specify GPG Key (Optional):**
If you have multiple GPG keys, specify which one to use by adding the key ID or email:
```bash
conda run -n base python scripts/admin_gpg_auth.py login administrator erupt.salute-0f@icloud.com
```

This will:
1. Request a challenge from the server
2. Sign it with your GPG key (prompts for passphrase)
3. Submit signature and receive 24-hour token
4. Save token to `~/.gpg-webservice-admin-token`

### Manual Flow

#### Step 1: Get Challenge

```bash
curl -X POST https://vps-b5527a39.vps.ovh.net/admin/auth/challenge \
  -H "Content-Type: application/json" \
  -d '{"username":"administrator"}'
```

Response:
```json
{
  "challenge": "abc123xyz789:1234567890",
  "expires_at": 1234567890,
  "message": "Sign this challenge with your GPG private key"
}
```

#### Step 2: Sign Challenge

```bash
echo -n "abc123xyz789:1234567890" | gpg --detach-sign --armor > signature.asc
```

Extract base64 signature (remove headers/footers):
```bash
cat signature.asc | grep -v "BEGIN\|END\|Version\|Comment" | tr -d '\n' > signature.b64
```

#### Step 3: Verify and Get Token

```bash
curl -X POST https://vps-b5527a39.vps.ovh.net/admin/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "username":"administrator",
    "challenge":"abc123xyz789:1234567890",
    "signature":"iQEcBAABCg..."
  }'
```

Response:
```json
{
  "token": "admin_administrator_1701234567_abc123def456",
  "expires_at": 1701320967,
  "username": "administrator",
  "message": "Authentication successful"
}
```

### Using the Token

Use the token in API requests with `X-Admin-Token` header:

```bash
# List users
curl https://vps-b5527a39.vps.ovh.net/admin/users \
  -H "X-Admin-Token: admin_administrator_1701234567_abc123def456"

# Delete user
curl -X DELETE https://vps-b5527a39.vps.ovh.net/admin/users/some_user \
  -H "X-Admin-Token: admin_administrator_1701234567_abc123def456"
```

## Token Details

- **Format**: `admin_<username>_<timestamp>_<hmac>`
- **Validity**: 24 hours from issue time
- **Storage**: Not stored in database (stateless verification)
- **Verification**: HMAC using server SECRET_KEY

## Security Considerations

1. **Public Keys Only**: Only public keys are stored (in .env, not DB)
2. **Challenge-Response**: Prevents replay attacks (5-minute validity)
3. **HMAC Verification**: Token integrity protected by SECRET_KEY
4. **Time-Limited**: Tokens expire after 24 hours
5. **Audit Logging**: All admin actions logged with username

## Comparison: Session Keys vs GPG Tokens

| Feature | Session Keys (Agents) | GPG Tokens (Admins) |
|---------|----------------------|-------------------|
| **Authentication** | Password → HMAC | GPG Signature |
| **Validity** | 1 hour + 10min grace | 24 hours |
| **Storage** | Derived from DB | Public key in .env only |
| **Use Case** | AI agents (hourly refresh) | Human admins |
| **Headers** | X-API-KEY + X-Username | X-Admin-Token |
| **Config** | ADMIN_USERNAMES | ADMIN_GPG_KEYS |

## Troubleshooting

### "Admin GPG key not configured"

Check that your username is in `ADMIN_GPG_KEYS`:

```bash
# View current config (in container)
docker compose exec gpg-webservice-rest env | grep ADMIN_GPG_KEYS
```

### "Challenge expired"

Challenges are valid for 5 minutes. Get a new challenge and sign faster.

### "Invalid signature"

- Ensure you're signing the exact challenge string (no extra whitespace)
- Verify your GPG key is working: `echo "test" | gpg --clearsign`
- Check that the public key in ADMIN_GPG_KEYS matches your private key

### "Invalid or expired admin token"

Tokens expire after 24 hours. Run the login flow again to get a new token.

## API Endpoints

- `POST /admin/auth/challenge` - Get authentication challenge
- `POST /admin/auth/verify` - Verify signature and get token  
- `GET /admin/auth/info` - Get authentication info

## Example: Complete Admin Workflow

```bash
# 1. Export your GPG public key
gpg --armor --export admin@example.com > my-key.asc

# 2. Convert to JSON (one line, escape newlines)
PUBLIC_KEY=$(cat my-key.asc | jq -Rs '.')

# 3. Add to gpg-webservice-rest/.env
echo "ADMIN_GPG_KEYS='{\"administrator\":$PUBLIC_KEY}'" >> gpg-webservice-rest/.env

# 4. Restart service
docker compose -f docker-compose.yml -f docker-compose.vps.yml restart gpg-webservice-rest

# 5. Login interactively
python scripts/admin_gpg_auth.py login administrator

# 6. Token is saved to ~/.gpg-webservice-admin-token
TOKEN=$(cat ~/.gpg-webservice-admin-token)

# 7. Use token for admin operations
curl -H "X-Admin-Token: $TOKEN" \
  https://vps-b5527a39.vps.ovh.net/admin/users
```

## Benefits for Lex Atlantis Use Case

- **AI Agents**: Use hourly session keys (security requirement)
- **Human Operators**: Use 24h GPG tokens (convenience)
- **Clean Separation**: Agents in DB, admin keys in .env
- **No Database Bloat**: Admin authentication doesn't create DB users
