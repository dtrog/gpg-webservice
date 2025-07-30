# GPG utility functions



import tempfile
import subprocess
import os
SERVICE_KEYSTORE_PATH = os.environ.get('SERVICE_KEYSTORE_PATH', '/srv/gpg-keystore')
SERVICE_KEY_EMAIL = os.environ.get('SERVICE_KEY_EMAIL', 'service@example.com')
SERVICE_KEY_NAME = os.environ.get('SERVICE_KEY_NAME', 'GPG Webservice')
SERVICE_KEY_PASSPHRASE = os.environ.get('SERVICE_KEY_PASSPHRASE', 'service-default-passphrase')

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
        subprocess.run([
            'gpg', '--homedir', gnupg_home, '--batch', '--pinentry-mode', 'loopback', '--gen-key', batch_file
        ], check=True)
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
