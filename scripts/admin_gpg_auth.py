#!/usr/bin/env python3
"""
Admin GPG Authentication Helper Script

This script helps administrators authenticate using GPG signatures
instead of expiring session keys.

Usage:
    1. Get challenge: python admin_gpg_auth.py challenge
    2. Sign the challenge with GPG
    3. Verify and get token: python admin_gpg_auth.py verify <signature>
    
Or use the interactive flow:
    python admin_gpg_auth.py login
"""
import sys
import json
from pathlib import Path
from os import environ
import subprocess
import requests


# Configuration
API_BASE_URL = "https://"+ environ.get(
    "VPS_HOST", "localhost") +":"+ environ.get("FLASK_PORT", "5555")
TOKEN_FILE = Path.home() / ".gpg-webservice-admin-token"


def get_challenge(username):
    """Request an authentication challenge."""
    response = requests.post(
        f"{API_BASE_URL}/admin/auth/challenge",
        json={"username": username},
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print("✓ Challenge received")
        print(f"  Challenge: {data['challenge']}")
        print(f"  Expires at: {data['expires_at']}")
        return data['challenge']
    else:
        print(f"✗ Failed to get challenge: {response.json()}")
        return None


def sign_challenge_with_gpg(challenge, gpg_key_id=None):
    """Sign the challenge using GPG command line."""
    print("\n🔐 Signing challenge with GPG...")

    # Use gpg --detach-sign --armor to create a signature
    cmd = ["gpg", "--detach-sign", "--armor"]
    if gpg_key_id:
        cmd.extend(["--local-user", gpg_key_id])

    try:
        result = subprocess.run(
            cmd,
            input=challenge.encode(),
            capture_output=True,
            check=True
        )

        signature = result.stdout.decode('utf-8')
        print("✓ Challenge signed successfully")
        return signature

    except subprocess.CalledProcessError as e:
        print(f"✗ GPG signing failed: {e.stderr.decode()}")
        return None


def verify_challenge(username, challenge, signature):
    """Verify the signed challenge and get admin token."""
    # Convert signature to base64 if it's ASCII armored
    if signature.startswith("-----BEGIN PGP SIGNATURE-----"):
        # Extract the base64 part from ASCII armor
        lines = signature.split('\n')
        base64_lines = []
        in_body = False
        for line in lines:
            if line.startswith("-----BEGIN"):
                in_body = True
                continue
            if line.startswith("-----END"):
                break
            if in_body and line.strip() and not line.startswith('='):
                base64_lines.append(line.strip())
        signature_b64 = ''.join(base64_lines)
    else:
        signature_b64 = signature

    response = requests.post(
        f"{API_BASE_URL}/admin/auth/verify",
        json={
            "username": username,
            "challenge": challenge,
            "signature": signature_b64
        },
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print("\n✓ Authentication successful!")
        print(f"  Token: {data['token']}")
        print(f"  Expires at: {data['expires_at']}")
        print("  Valid for: 24 hours")

        # Save token to file
        TOKEN_FILE.write_text(data['token'])
        TOKEN_FILE.chmod(0o600)
        print(f"\n💾 Token saved to: {TOKEN_FILE}")
        print("\nUse this token in API requests:")
        print(f"  curl -H 'X-Admin-Token: {data['token']}' ...")

        return data['token']
    else:
        error_data = response.json()
        print(f"\n✗ Verification failed: {error_data.get('error')}")
        if 'details' in error_data:
            print(f"  Details: {error_data['details']}")
        return None


def interactive_login(username, gpg_key_id=None):
    """Interactive login flow."""
    print("🔑 GPG-based Admin Authentication")
    print(f"   Username: {username}")
    print(f"   API: {API_BASE_URL}")
    print()

    # Step 1: Get challenge
    print("Step 1/3: Requesting authentication challenge...")
    challenge = get_challenge(username)
    if not challenge:
        return False

    # Step 2: Sign challenge
    print("\nStep 2/3: Signing challenge with your GPG key...")
    signature = sign_challenge_with_gpg(challenge, gpg_key_id)
    if not signature:
        return False

    # Step 3: Verify and get token
    print("\nStep 3/3: Verifying signature and obtaining token...")
    token = verify_challenge(username, challenge, signature)
    if not token:
        return False

    print("\n✅ Login complete!")
    return True


def show_info():
    """Show information about admin authentication."""
    response = requests.get(f"{API_BASE_URL}/admin/auth/info", timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Failed to get info: {response.status_code}")


def main():
    """
    Main entry point for the script.
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python admin_gpg_auth.py login [username] [gpg-key-id]")
        print("  python admin_gpg_auth.py challenge <username>")
        print("  python admin_gpg_auth.py verify <username> <challenge> <sig>")
        print("  python admin_gpg_auth.py info")
        sys.exit(1)

    command = sys.argv[1]

    if command == "login":
        username = sys.argv[2] if len(sys.argv) > 2 else "administrator"
        gpg_key_id = sys.argv[3] if len(sys.argv) > 3 else None
        success = interactive_login(username, gpg_key_id)
        sys.exit(0 if success else 1)

    elif command == "challenge":
        if len(sys.argv) < 3:
            print("Usage: python admin_gpg_auth.py challenge <username>")
            sys.exit(1)
        username = sys.argv[2]
        get_challenge(username)

    elif command == "verify":
        if len(sys.argv) < 5:
            print("Usage: python admin_gpg_auth.py verify <user> <chal> <sig>")
            sys.exit(1)
        username = sys.argv[2]
        challenge = sys.argv[3]
        signature = sys.argv[4]
        verify_challenge(username, challenge, signature)

    elif command == "info":
        show_info()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
