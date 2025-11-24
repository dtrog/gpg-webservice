# GPG utility functions

import base64
import tempfile
import subprocess
import os
from typing import Tuple
SERVICE_KEYSTORE_PATH = os.environ.get('SERVICE_KEYSTORE_PATH', '/srv/gpg-keystore')
SERVICE_KEY_EMAIL = os.environ.get('SERVICE_KEY_EMAIL', 'service@example.com')
SERVICE_KEY_NAME = os.environ.get('SERVICE_KEY_NAME', 'GPG Webservice')
# Service key passphrase MUST be set - no insecure defaults
SERVICE_KEY_PASSPHRASE = os.environ.get('SERVICE_KEY_PASSPHRASE')
if not SERVICE_KEY_PASSPHRASE:
    raise ValueError(
        "SERVICE_KEY_PASSPHRASE environment variable is required.\n"
        "Generate a strong passphrase with: openssl rand -base64 32\n"
        "Set it in your .env file or environment."
    )
if len(SERVICE_KEY_PASSPHRASE) < 16:
    raise ValueError(
        "SERVICE_KEY_PASSPHRASE is too weak. Must be at least 16 characters.\n"
        "Generate a strong passphrase with: openssl rand -base64 32"
    )

def ensure_service_keystore():
    """
    Ensure the service keystore exists and has a keypair. Generate on first run.
    Returns the fingerprint of the service key.
    """
    os.makedirs(SERVICE_KEYSTORE_PATH, exist_ok=True)
    # Check if a secret key exists
    list_cmd = [
        'gpg', '--homedir', SERVICE_KEYSTORE_PATH, '--list-secret-keys', '--with-colons'
    ]
    result = subprocess.run(list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if b'fpr:' in result.stdout:
        # Already exists, extract fingerprint
        for line in result.stdout.decode().splitlines():
            if line.startswith('fpr:'):
                return line.split(':')[9]
    # Generate new key
    batch = f"""
    Key-Type: RSA
    Key-Length: 3072
    Key-Usage: sign
    Subkey-Type: RSA
    Subkey-Length: 3072
    Subkey-Usage: encrypt
    Name-Real: {SERVICE_KEY_NAME}
    Name-Email: {SERVICE_KEY_EMAIL}
    Expire-Date: 0
    Passphrase: {SERVICE_KEY_PASSPHRASE}
    %commit
    """
    batch_file = os.path.join(SERVICE_KEYSTORE_PATH, 'batch.txt')
    with open(batch_file, 'w') as f:
        f.write(batch)
    subprocess.run([
        'gpg', '--homedir', SERVICE_KEYSTORE_PATH, '--batch', '--pinentry-mode', 'loopback', '--gen-key', batch_file
    ], check=True)
    # Get fingerprint
    result = subprocess.run(list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in result.stdout.decode().splitlines():
        if line.startswith('fpr:'):
            return line.split(':')[9]
    raise RuntimeError('Failed to generate service GPG key')

def generate_gpg_keypair(username, email, passphrase=None, keystore_path=None):
    """
    Generate a GPG keypair non-interactively, returns (public_key, private_key).
    If keystore_path is provided, use it as the GPG home (for service keys).
    Otherwise, use a temporary keyring (for user keys).
    """
    if keystore_path:
        gnupg_home = keystore_path
        os.makedirs(gnupg_home, exist_ok=True)
    else:
        gnupg_home = tempfile.mkdtemp()
    try:
        if passphrase:
            batch = f"""
            Key-Type: RSA
            Key-Length: 3072
            Key-Usage: sign
            Subkey-Type: RSA
            Subkey-Length: 3072
            Subkey-Usage: encrypt
            Name-Real: {username}
            Name-Email: {email}
            Expire-Date: 0
            Passphrase: {passphrase}
            %commit
            """
        else:
            batch = f"""
            %no-protection
            Key-Type: RSA
            Key-Length: 3072
            Key-Usage: sign
            Subkey-Type: RSA
            Subkey-Length: 3072
            Subkey-Usage: encrypt
            Name-Real: {username}
            Name-Email: {email}
            Expire-Date: 0
            %commit
            """
        batch_file = os.path.join(gnupg_home, 'batch.txt')
        with open(batch_file, 'w') as f:
            f.write(batch)

        # Immediately restrict permissions (owner read-only)
        os.chmod(batch_file, 0o400)

        try:
            subprocess.run([
                'gpg', '--homedir', gnupg_home, '--batch', '--pinentry-mode', 'loopback', '--gen-key', batch_file
            ], check=True)
        finally:
            # Securely delete the batch file
            try:
                os.unlink(batch_file)
            except:
                pass
        pub = subprocess.check_output(['gpg', '--homedir', gnupg_home, '--armor', '--export', email])
        if passphrase:
            env = os.environ.copy()
            env['GNUPGHOME'] = gnupg_home
            export_cmd = [
                'gpg', '--homedir', gnupg_home, '--batch', '--pinentry-mode', 'loopback',
                '--passphrase-fd', '0', '--armor', '--export-secret-keys', email
            ]
            passphrase_input = (passphrase + '\n').encode()
            priv = subprocess.check_output(export_cmd, input=passphrase_input, env=env)
        else:
            priv = subprocess.check_output(['gpg', '--homedir', gnupg_home, '--armor', '--export-secret-keys', email])
        return pub.decode('utf-8'), priv.decode('utf-8')
    finally:
        if not keystore_path:
            import shutil
            shutil.rmtree(gnupg_home, ignore_errors=True)


def verify_signature(data: str, signature: str, public_key: str) -> bool:
    """
    Verifies a signature using GPG in a temporary keyring.
    Returns True if valid, False otherwise.
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import public key
        pubkey_path = os.path.join(gnupg_home, 'pubkey.asc')
        with open(pubkey_path, 'w') as f:
            f.write(public_key)
        import_cmd = [
            'gpg', '--homedir', gnupg_home, '--import', pubkey_path
        ]
        subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Write data and signature to temp files
        data_path = os.path.join(gnupg_home, 'data.txt')
        sig_path = os.path.join(gnupg_home, 'data.sig')
        with open(data_path, 'w') as f:
            f.write(data)
        with open(sig_path, 'w') as f:
            f.write(signature)

        # Verify signature
        verify_cmd = [
            'gpg', '--homedir', gnupg_home, '--verify', sig_path, data_path
        ]
        result = subprocess.run(verify_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0


def verify_gpg_signature(message: str, signature: str, public_key: str) -> Tuple[bool, str]:
    """
    Verify a GPG signature against a public key.
    
    Args:
        message: The original text that was signed
        signature: Base64-encoded detached signature or ASCII-armored signature
        public_key: ASCII-armored PGP public key
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Create temporary GPG home
            gnupg_home = os.path.join(tmpdir, '.gnupg')
            os.makedirs(gnupg_home, mode=0o700)
            
            # Import public key
            pubkey_path = os.path.join(tmpdir, 'pubkey.asc')
            with open(pubkey_path, 'w') as f:
                f.write(public_key)
            
            import_cmd = [
                'gpg', '--homedir', gnupg_home,
                '--batch', '--import', pubkey_path
            ]
            import_result = subprocess.run(
                import_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if import_result.returncode != 0:
                return False, f"Failed to import public key: {import_result.stderr.decode()}"
            
            # Write message to file
            message_path = os.path.join(tmpdir, 'message.txt')
            with open(message_path, 'w') as f:
                f.write(message)
            
            # Handle signature format
            sig_path = os.path.join(tmpdir, 'signature.sig')
            
            # If signature starts with -----BEGIN PGP, it's ASCII-armored
            if signature.strip().startswith('-----BEGIN PGP'):
                with open(sig_path, 'w') as f:
                    f.write(signature)
            else:
                # Assume it's base64-encoded, decode it
                try:
                    import base64
                    sig_bytes = base64.b64decode(signature)
                    with open(sig_path, 'wb') as f:
                        f.write(sig_bytes)
                except Exception as e:
                    return False, f"Failed to decode signature: {str(e)}"
            
            # Verify signature
            verify_cmd = [
                'gpg', '--homedir', gnupg_home,
                '--batch', '--verify', sig_path, message_path
            ]
            verify_result = subprocess.run(
                verify_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if verify_result.returncode == 0:
                return True, "Signature valid"
            else:
                error_msg = verify_result.stderr.decode()
                return False, f"Signature verification failed: {error_msg}"
                
        except Exception as e:
            return False, f"Verification error: {str(e)}"
