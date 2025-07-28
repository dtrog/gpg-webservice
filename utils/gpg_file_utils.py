# GPG utility functions for file-based operations

import tempfile
import subprocess
import os

from typing import Optional

def sign_file(input_path: str, private_key: str, output_path: str, passphrase: Optional[str] = None):
    """
    Signs a file using GPG in a temporary keyring with the provided private key.
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import private key
        privkey_path = os.path.join(gnupg_home, 'privkey.asc')
        with open(privkey_path, 'w') as f:
            f.write(private_key)
        
        # Import with passphrase if provided
        if passphrase:
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--batch', '--pinentry-mode', 'loopback',
                '--passphrase', passphrase, '--import', privkey_path
            ]
        else:
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--import', privkey_path
            ]
        subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Sign file
        sign_cmd = [
            'gpg', '--homedir', gnupg_home, '--batch', '--yes', '--pinentry-mode', 'loopback', '--no-use-agent'
        ]
        
        # Use stdin for passphrase
        passphrase_input = None
        if passphrase:
            sign_cmd.extend(['--passphrase-fd', '0'])
            passphrase_input = (passphrase + '\n').encode()
            
        sign_cmd.extend(['--output', output_path, '--detach-sign', input_path])
        
        try:
            # Kill any existing GPG agent first
            subprocess.run(['gpgconf', '--kill', 'gpg-agent'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            # Set environment variables to ensure GPG isolation
            env = os.environ.copy()
            env.update({
                'GNUPGHOME': gnupg_home,
                'GPG_AGENT_INFO': '',  # Disable GPG agent
                'GPG_TTY': '',  # Disable TTY
                'DISPLAY': '',  # Disable X11 prompts
                'PINENTRY_USER_DATA': 'USE_CURSES=0',  # Disable curses prompts
            })
            
            result = subprocess.run(sign_cmd, input=passphrase_input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            if result.returncode != 0:
                raise Exception(f'GPG signing failed: {result.stderr.decode()}')
        finally:
            pass  # No cleanup needed for stdin approach

def verify_signature_file(input_path: str, sig_path: str, public_key: str) -> bool:
    """
    Verifies a file signature using GPG in a temporary keyring.
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
        # Verify signature
        verify_cmd = [
            'gpg', '--homedir', gnupg_home, '--trust-model', 'always', '--verify', sig_path, input_path
        ]
        result = subprocess.run(verify_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0

def encrypt_file(input_path: str, public_key: str, output_path: str):
    """
    Encrypts a file for a recipient using their public key in a temporary keyring.
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
        # Get key fingerprint
        list_keys_cmd = [
            'gpg', '--homedir', gnupg_home, '--list-keys', '--with-colons'
        ]
        result = subprocess.run(list_keys_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        lines = result.stdout.decode().splitlines()
        fpr = None
        for line in lines:
            if line.startswith('fpr:'):
                fpr = line.split(':')[9]
                break
        if not fpr:
            raise Exception('Could not extract key fingerprint')
        # Encrypt file
        encrypt_cmd = [
            'gpg', '--homedir', gnupg_home, '--batch', '--yes', '--trust-model', 'always', '--output', output_path, '--encrypt', '--recipient', fpr, input_path
        ]
        result = subprocess.run(encrypt_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception(f'GPG encryption failed: {result.stderr.decode()}')

def decrypt_file(input_path: str, private_key: str, output_path: str, passphrase: Optional[str] = None):
    """
    Decrypts a file using the provided private key in a temporary keyring.
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import private key
        privkey_path = os.path.join(gnupg_home, 'privkey.asc')
        with open(privkey_path, 'w') as f:
            f.write(private_key)
        
        # Import with passphrase if provided
        if passphrase:
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--batch', '--pinentry-mode', 'loopback',
                '--passphrase', passphrase, '--import', privkey_path
            ]
        else:
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--import', privkey_path
            ]
        subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Decrypt file
        decrypt_cmd = [
            'gpg', '--homedir', gnupg_home, '--batch', '--yes', '--pinentry-mode', 'loopback', '--no-use-agent'
        ]
        
        # Use stdin for passphrase
        passphrase_input = None
        if passphrase:
            decrypt_cmd.extend(['--passphrase-fd', '0'])
            passphrase_input = (passphrase + '\n').encode()
            
        decrypt_cmd.extend(['--output', output_path, '--decrypt', input_path])
        
        try:
            # Kill any existing GPG agent first
            subprocess.run(['gpgconf', '--kill', 'gpg-agent'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            
            # Set environment variables to ensure GPG isolation
            env = os.environ.copy()
            env.update({
                'GNUPGHOME': gnupg_home,
                'GPG_AGENT_INFO': '',  # Disable GPG agent
                'GPG_TTY': '',  # Disable TTY
                'DISPLAY': '',  # Disable X11 prompts
                'PINENTRY_USER_DATA': 'USE_CURSES=0',  # Disable curses prompts
            })
            
            result = subprocess.run(decrypt_cmd, input=passphrase_input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            if result.returncode != 0:
                raise Exception(f'GPG decryption failed: {result.stderr.decode()}')
        finally:
            pass  # No cleanup needed for stdin approach

# Alias for backward compatibility
def decrypt_file_with_passphrase(input_path: str, private_key: str, output_path: str, passphrase: str):
    """
    Decrypts a file using the provided private key with passphrase in a temporary keyring.
    """
    return decrypt_file(input_path, private_key, output_path, passphrase)
