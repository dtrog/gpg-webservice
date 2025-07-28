<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->


# Copilot Instructions for eid_webservice

## Project Overview
This project is a Flask-based webservice that exposes GPG cryptographic operations (sign, verify, encrypt, decrypt, challenge) via HTTP endpoints. It supports user registration, login, API key authentication, and secure key storage in SQLite. All cryptographic operations are performed using GPG, with private keys encrypted using Argon2id and AES-GCM.

## Key Points for Copilot

- **Language:** Python 3.11+
- **Framework:** Flask
- **Database:** SQLite (path set via `app.config['DATABASE']`)
- **Crypto:** GPG (with temporary keyrings for per-request isolation)
- **Key Storage:**
	- Public and encrypted private keys are stored in the database.
	- Private keys are encrypted with a password-derived key (Argon2id + AES-GCM).
- **Endpoints:**
	- `/register` — Register a new user, generates GPG keypair
	- `/login` — Authenticate and get API key
	- `/sign` — Sign a file (requires password)
	- `/verify` — Verify a signature with a public key
	- `/encrypt` — Encrypt a file for a given public key
	- `/decrypt` — Decrypt a file (requires password)
	- `/challenge` — Sign a challenge file (requires password)
	- `/get_public_key` — Retrieve the user's public key
- **API Key Auth:** All sensitive endpoints require `X-API-KEY` header
- **Testing:**
	- Uses pytest
	- Each test uses a temporary database and isolated GPG environment
	- Tests are split per operation for clarity
- **GPG Key Generation:**
	- Primary key: RSA, usage=sign
	- Subkey: RSA, usage=encrypt
	- Batch file is used for non-interactive key generation
- **Error Handling:**
	- Encryption endpoint returns GPG output on failure for easier debugging

## Best Practices
- Always use temporary directories for GPG operations in endpoints to avoid keyring conflicts.
- Use the Flask app's `DATABASE` config for all DB access (see `models.py`).
- Clean up all temporary files after use in tests and endpoints.
- Never expose private keys in API responses.
- Use strong passwords for registration and key encryption.

## Troubleshooting
- If encryption fails, check the GPG output in the API response for details.
- If tests fail with DB errors, ensure the test fixture sets `app.config['DATABASE']` before initializing the app.
- If you see `Unusable public key`, ensure the GPG batch file sets `Subkey-Usage: encrypt`.

---

For further details, see the README.md and the code in `app.py`, `gpg_utils.py`, and `test_app.py`.
