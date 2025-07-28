# GPG utility functions


import tempfile
import subprocess
import os

def generate_gpg_keypair(username, email, passphrase=None):
    # Generate a GPG keypair non-interactively, returns (public_key, private_key)
    with tempfile.TemporaryDirectory() as gnupg_home:
        if passphrase:
            # Generate with passphrase protection
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
            # Generate without passphrase protection
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
        # Export public key
        pub = subprocess.check_output(['gpg', '--homedir', gnupg_home, '--armor', '--export', email])
        # Export private key (with passphrase if needed)
        if passphrase:
            # For passphrase-protected keys, we need to provide the passphrase for export
            # Use stdin to avoid issues with passphrases that start with hyphens
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
