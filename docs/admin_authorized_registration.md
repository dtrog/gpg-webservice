# Admin-Authorized Registration

## Overview

To prevent abuse of the open registration system, all new user registrations require authorization from an administrator via GPG signature. This ensures only approved agents and users can join the Atlantis ecosystem.

## How It Works

1. **Admin signs username**: Admin creates a detached GPG signature of the desired username
2. **User provides signature**: During registration, user includes the admin signature
3. **Server verifies**: Server verifies the signature against admin public keys (stored in `ADMIN_GPG_KEYS`)
4. **Registration proceeds**: If signature is valid, user account is created

## For Administrators

### Authorizing a New User

Use the helper script:

```bash
python3 scripts/authorize_user.py <username> [gpg-key-id]
```

**Example:**
```bash
# Authorize user "imperator" with default GPG key
python3 scripts/authorize_user.py imperator

# Authorize user "PrimeAI" with specific GPG key
python3 scripts/authorize_user.py PrimeAI imperator
```

**Output:**
```
📝 Authorizing registration for: imperator

🔐 Signing username: imperator
✓ Signature created

============================================================
ADMIN SIGNATURE (ASCII-armored)
============================================================
-----BEGIN PGP SIGNATURE-----

iQJPBAABCAA5FiEEu8UQlitZzxwDBf153HvnRmLow3sFAmkkzIcbHGVydXB0LnNh
bHV0ZS0wZkBpY2xvdWQuY29tAAoJENx750Zi6MN7IfsP/1ahkmp7gMUQBk5GXH3T
...
=xE12
-----END PGP SIGNATURE-----
============================================================
```

### Manual Signature Generation

You can also generate signatures manually:

```bash
# Sign username with detached ASCII-armored signature
echo -n "imperator" | gpg --armor --detach-sign

# With specific key
echo -n "imperator" | gpg --armor --detach-sign --local-user imperator
```

**Important:** Use `echo -n` (no newline) to sign just the username.

## For Users

### Registration with Admin Signature

Once you receive an admin signature, include it in your registration request:

**JSON API:**
```bash
curl -X POST https://vps-b5527a39.vps.ovh.net/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "imperator",
    "password": "your-secure-password",
    "admin_signature": "-----BEGIN PGP SIGNATURE-----\n\niQJPBAABCAA5...\n=xE12\n-----END PGP SIGNATURE-----"
  }'
```

**Form API:**
```bash
curl -X POST https://vps-b5527a39.vps.ovh.net/register/form \
  -F "username=imperator" \
  -F "password=your-secure-password" \
  -F "admin_signature=-----BEGIN PGP SIGNATURE-----
  
iQJPBAABCAA5...
=xE12
-----END PGP SIGNATURE-----"
```

### Response

Successful registration:
```json
{
  "message": "User registered with deterministic session keys",
  "user_id": 1,
  "username": "imperator",
  "authorized_by": "administrator",
  "api_key": "sk_...",
  "session_window": 123456,
  "expires_at": 1234567890,
  "note": "Session key expires hourly. Use /login to get a fresh key when expired."
}
```

### Error Responses

**Missing signature:**
```json
{
  "error": "Admin signature required for registration"
}
```

**Invalid signature:**
```json
{
  "error": "Invalid admin signature",
  "hint": "Admin must sign username with: echo \"username\" | gpg --armor --detach-sign"
}
```

## Configuration

### Admin Public Keys

Admin public keys are stored in the `ADMIN_GPG_KEYS` environment variable:

```bash
# .env file
ADMIN_GPG_KEYS='{"administrator":"-----BEGIN PGP PUBLIC KEY BLOCK-----\n..."}'
```

### Adding Multiple Admins

Multiple administrators can authorize registrations:

```bash
ADMIN_GPG_KEYS='{
  "administrator": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...",
  "imperator": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n..."
}'
```

The server will try each admin's public key until one successfully verifies the signature.

## Security Considerations

### Why This Works

1. **Asymmetric Cryptography**: Server only needs admin public keys (no private keys)
2. **Signature Uniqueness**: Each signature is unique (includes timestamp), preventing reuse
3. **No Database Required**: Public keys stored in environment variable, not database
4. **Audit Trail**: Registration logs include which admin authorized the user

### What's Protected

- **Open registration abuse**: Random users cannot register without admin approval
- **Admin private keys**: Never exposed to the server
- **Replay attacks**: Each signature is unique and tied to specific username

### What's NOT Protected

- **Signature reuse**: Same signature can be used multiple times for the same username (by design)
- **Signature sharing**: If user shares their signature, others could use it (admin should keep signatures private until needed)

## Best Practices

### For Administrators

1. **Keep signatures private**: Only share with intended user
2. **Use specific GPG key**: `--local-user imperator` to avoid ambiguity
3. **Verify username spelling**: Double-check before signing
4. **Archive signatures**: Keep records of authorized users

### For Users

1. **Keep signature safe**: Treat it like a registration token
2. **Register promptly**: Don't delay after receiving signature
3. **Don't share**: Your signature is tied to your username

## Lex Atlantis Integration

For AI agents in the Lex Atlantis governance system:

1. **Imperator authorizes agents**: Signs "PrimeAI", "Auditor_Alpha", etc.
2. **Agents register with signature**: Include in registration request
3. **Agents use session keys**: Normal 1-hour session key authentication
4. **Imperator monitors with GPG token**: Uses 24-hour admin token for oversight

This creates separation:
- **Real world**: Imperator's GPG key (never in database)
- **Atlantis**: AI agent accounts (session keys in database)

## Troubleshooting

### "Invalid admin signature"

**Cause:** Signature doesn't verify against any admin public key

**Solutions:**
1. Verify signature was created correctly: `echo -n "username" | gpg --armor --detach-sign`
2. Check username matches exactly (case-sensitive)
3. Ensure admin public key is in `ADMIN_GPG_KEYS`
4. Verify signature format (ASCII-armored, not binary)

### "Admin authorization not configured"

**Cause:** `ADMIN_GPG_KEYS` environment variable is empty or invalid JSON

**Solution:**
```bash
# Check current value
echo $ADMIN_GPG_KEYS

# Set properly
export ADMIN_GPG_KEYS='{"administrator":"-----BEGIN PGP PUBLIC KEY BLOCK-----\n..."}'
```

### GPG Signing Fails

**Cause:** GPG key not available or passphrase required

**Solutions:**
```bash
# List available keys
gpg --list-secret-keys

# Test signing
echo "test" | gpg --armor --detach-sign --local-user imperator

# Use gpg-agent for passphrase caching
eval $(gpg-agent --daemon)
```

## API Reference

### POST /register

**Request:**
```json
{
  "username": "string (required)",
  "password": "string (required)",
  "admin_signature": "string (required, ASCII-armored PGP signature)",
  "email": "string (optional)",
  "public_key": "string (optional)",
  "private_key": "string (optional)"
}
```

**Response (201):**
```json
{
  "message": "User registered with deterministic session keys",
  "user_id": 1,
  "username": "imperator",
  "authorized_by": "administrator",
  "api_key": "sk_...",
  "session_window": 123456,
  "window_start": 1234567800,
  "expires_at": 1234567890,
  "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...",
  "note": "Session key expires hourly. Use /login to get a fresh key when expired."
}
```

### POST /register/form

**Request (multipart/form-data):**
- `username` (required)
- `password` (required)
- `admin_signature` (required)
- `email` (optional)
- `public_key_file` or `public_key_text` (optional)
- `private_key_file` or `private_key_text` (optional)

**Response:** Same as /register

## Examples

### Full Workflow

**Step 1: Admin authorizes user**
```bash
$ python3 scripts/authorize_user.py PrimeAI imperator
📝 Authorizing registration for: PrimeAI
🔐 Signing username: PrimeAI
✓ Signature created
[signature output...]
```

**Step 2: User registers**
```bash
curl -X POST https://vps-b5527a39.vps.ovh.net/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "PrimeAI",
    "password": "sha256_of_contract_and_signature",
    "admin_signature": "-----BEGIN PGP SIGNATURE-----..."
  }'
```

**Step 3: User receives session key**
```json
{
  "message": "User registered with deterministic session keys",
  "username": "PrimeAI",
  "authorized_by": "administrator",
  "api_key": "sk_...",
  "expires_at": 1234567890
}
```

**Step 4: User authenticates**
```bash
curl https://vps-b5527a39.vps.ovh.net/sign \
  -H "X-API-KEY: sk_..." \
  -H "X-Username: PrimeAI" \
  -F "file=@document.txt"
```

## Comparison: Registration Methods

| Feature | Open Registration | Admin-Authorized |
|---------|-------------------|------------------|
| **Security** | Anyone can register | Admin approval required |
| **Use Case** | Public services | Private/controlled ecosystems |
| **Admin Effort** | None | Sign each username |
| **User Experience** | Instant | Requires admin signature |
| **Abuse Prevention** | Rate limiting only | Cryptographic authorization |
| **Audit Trail** | Basic | Includes authorizing admin |

## Future Enhancements

### Invitation Codes (Alternative)

Instead of signatures per user, admins could generate invitation codes:

```bash
# Generate reusable invite code
python3 scripts/generate_invite.py --uses 10 --expires 7d
```

This would allow:
- Multiple registrations with one code
- Expiration dates
- Usage limits
- Code revocation

### Registration Quotas

Limit registrations per admin:

```bash
ADMIN_REGISTRATION_LIMITS='{"administrator": 100, "imperator": 50}'
```

### Signature Expiration

Add timestamp verification to signatures:

```python
# Admin signs: "username:2025-11-25"
# Server rejects if date is old
```

## Summary

Admin-authorized registration provides:
- ✅ **Security**: Prevents unauthorized registrations
- ✅ **Flexibility**: Multiple admins, no coordination needed
- ✅ **Auditability**: Track which admin authorized each user
- ✅ **Simplicity**: No complex invitation system
- ✅ **Privacy**: Admin private keys never on server

Perfect for the Lex Atlantis ecosystem where Imperator controls who enters Atlantis! 👑
