#!/usr/bin/env python3
"""
Admin script to authorize new user registrations.

Usage:
    python3 scripts/authorize_user.py <username> [gpg-key-id]

This script:
1. Signs the username with the admin's GPG private key
2. Outputs the signature in base64 format
3. Provides the curl command for registration

Example:
    python3 scripts/authorize_user.py imperator
    python3 scripts/authorize_user.py PrimeAI imperator
"""

import sys
import subprocess


def sign_username(username: str, gpg_key_id: str = None) -> str:
    """
    Sign a username with GPG.
    
    Args:
        username: The username to authorize
        gpg_key_id: Optional GPG key ID to use for signing
        
    Returns:
        Base64-encoded ASCII-armored signature
    """
    print(f"🔐 Signing username: {username}")
    
    # Build GPG command
    cmd = ['gpg', '--armor', '--detach-sign']
    if gpg_key_id:
        cmd.extend(['--local-user', gpg_key_id])
    
    try:
        # Sign the username
        result = subprocess.run(
            cmd,
            input=username.encode(),
            capture_output=True,
            check=True
        )
        
        signature = result.stdout.decode()
        print("✓ Signature created\n")
        
        return signature
        
    except subprocess.CalledProcessError as e:
        print(f"❌ GPG signing failed: {e.stderr.decode()}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/authorize_user.py <username> [gpg-key-id]")
        print("\nExample:")
        print("  python3 scripts/authorize_user.py imperator")
        print("  python3 scripts/authorize_user.py PrimeAI imperator")
        sys.exit(1)
    
    username = sys.argv[1]
    gpg_key_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n📝 Authorizing registration for: {username}\n")
    
    # Sign the username
    signature = sign_username(username, gpg_key_id)
    
    # Display the signature
    print("=" * 60)
    print("ADMIN SIGNATURE (ASCII-armored)")
    print("=" * 60)
    print(signature)
    print("=" * 60)
    
    # Create registration data
    print("\n📋 Registration Instructions:")
    print("\n1. Provide this signature to the user")
    print("2. User includes it in registration request as 'admin_signature'")
    
    print("\n3. Example registration (JSON):")
    print(f"""
curl -X POST $VPS_HOST/register \\
  -H "Content-Type: application/json" \\
  -d '{{
    "username": "{username}",
    "password": "your-secure-password",
    "admin_signature": "{signature.replace(chr(10), '\\n')}"
  }}'
""")
    
    print("\n✅ Authorization complete!")
    print(f"\n💡 Tip: Save this signature for user '{username}'")


if __name__ == '__main__':
    main()
