# GPG service for cryptographic operations

from utils.gpg_utils import verify_signature
# You would implement sign, encrypt, decrypt with GPG subprocess calls as in verify_signature
import tempfile
import subprocess
import os

class GPGService:
    def sign(self, data, private_key, password):
        with tempfile.TemporaryDirectory() as gnupg_home:
            # Import private key
            privkey_path = os.path.join(gnupg_home, 'privkey.asc')
            with open(privkey_path, 'w') as f:
                f.write(private_key)
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--import', privkey_path
            ]
            subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Write data to temp file
            data_path = os.path.join(gnupg_home, 'data.txt')
            with open(data_path, 'w') as f:
                f.write(data)
            sig_path = os.path.join(gnupg_home, 'data.sig')

            # Sign data
            sign_cmd = [
                'gpg', '--homedir', gnupg_home, '--batch', '--yes', '--pinentry-mode', 'loopback',
                '--passphrase', password, '--output', sig_path, '--detach-sign', data_path
            ]
            result = subprocess.run(sign_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                return None, result.stderr.decode()
            with open(sig_path, 'r') as f:
                signature = f.read()
            return signature, None

    def verify(self, data, signature, public_key):
        return verify_signature(data, signature, public_key)

    def encrypt(self, data, public_key):
        with tempfile.TemporaryDirectory() as gnupg_home:
            pubkey_path = os.path.join(gnupg_home, 'pubkey.asc')
            with open(pubkey_path, 'w') as f:
                f.write(public_key)
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--import', pubkey_path
            ]
            subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            data_path = os.path.join(gnupg_home, 'data.txt')
            with open(data_path, 'w') as f:
                f.write(data)
            enc_path = os.path.join(gnupg_home, 'data.enc')

            # Find key id
            list_keys_cmd = [
                'gpg', '--homedir', gnupg_home, '--list-keys', '--with-colons'
            ]
            result = subprocess.run(list_keys_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            keyid = None
            for line in result.stdout.decode().splitlines():
                if line.startswith('pub:'):
                    keyid = line.split(':')[4]
                    break
            if not keyid:
                return None, 'No public key found'

            encrypt_cmd = [
                'gpg', '--homedir', gnupg_home, '--yes', '--batch', '-r', keyid, '--output', enc_path, '--encrypt', data_path
            ]
            result = subprocess.run(encrypt_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                return None, result.stderr.decode()
            with open(enc_path, 'r') as f:
                encrypted = f.read()
            return encrypted, None

    def decrypt(self, data, private_key, password):
        with tempfile.TemporaryDirectory() as gnupg_home:
            privkey_path = os.path.join(gnupg_home, 'privkey.asc')
            with open(privkey_path, 'w') as f:
                f.write(private_key)
            import_cmd = [
                'gpg', '--homedir', gnupg_home, '--import', privkey_path
            ]
            subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            data_path = os.path.join(gnupg_home, 'data.enc')
            with open(data_path, 'w') as f:
                f.write(data)
            dec_path = os.path.join(gnupg_home, 'data.dec')

            decrypt_cmd = [
                'gpg', '--homedir', gnupg_home, '--batch', '--yes', '--pinentry-mode', 'loopback',
                '--passphrase', password, '--output', dec_path, '--decrypt', data_path
            ]
            result = subprocess.run(decrypt_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                return None, result.stderr.decode()
            with open(dec_path, 'r') as f:
                decrypted = f.read()
            return decrypted, None
