# GPG utility functions for file-based operations

import tempfile
import subprocess
import os

from typing import Optional, Dict

from utils.error_handling import GPGOperationError


def _create_gpg_isolated_env(gnupg_home: str) -> Dict[str, str]:
    """
    Create an isolated GPG environment to prevent interference with system GPG.

    Args:
        gnupg_home: Path to the temporary GPG home directory

    Returns:
        Environment dict with GPG-specific variables set for isolation
    """
    env = os.environ.copy()
    env.update({
        'GNUPGHOME': gnupg_home,
        'GPG_AGENT_INFO': '',     # Disable GPG agent
        'GPG_TTY': '',            # Disable TTY
        'DISPLAY': '',            # Disable X11 prompts
        'PINENTRY_USER_DATA': 'USE_CURSES=0',  # Disable curses prompts
    })
    return env


def _kill_gpg_agent() -> None:
    """Kill any existing GPG agent to prevent interference with isolated operations."""
    subprocess.run(
        ['gpgconf', '--kill', 'gpg-agent'],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        check=False
    )


class GPGCommandBuilder:
    """
    Builder pattern for constructing GPG commands with common options.

    This class provides a fluent interface for building GPG command-line arguments
    with consistent configuration and security settings.
    """

    def __init__(self, gnupg_home: str):
        """
        Initialize GPG command builder.

        Args:
            gnupg_home: Path to the GPG home directory
        """
        self.gnupg_home = gnupg_home
        self.cmd = ['gpg', '--homedir', gnupg_home, '--batch']
        self.passphrase_input = None

    def with_yes(self):
        """Add --yes flag to auto-confirm prompts."""
        self.cmd.append('--yes')
        return self

    def with_passphrase_stdin(self, passphrase: Optional[str]):
        """
        Configure passphrase input via stdin (secure method).

        Args:
            passphrase: The passphrase to use (if None, no passphrase configured)
        """
        if passphrase:
            self.cmd.extend(['--passphrase-fd', '0'])
            self.passphrase_input = (passphrase + '\n').encode()
        return self

    def with_pinentry_loopback(self):
        """Use loopback pinentry mode for non-interactive passphrase entry."""
        self.cmd.extend(['--pinentry-mode', 'loopback', '--no-use-agent'])
        return self

    def with_trust_always(self):
        """Trust all keys unconditionally (for isolated operations)."""
        self.cmd.extend(['--trust-model', 'always'])
        return self

    def sign(self, input_path: str, output_path: str):
        """
        Configure for detached signature creation.

        Args:
            input_path: Path to file to sign
            output_path: Path for signature output
        """
        self.cmd.extend(['--output', output_path, '--detach-sign', input_path])
        return self

    def verify(self, sig_path: str, input_path: str):
        """
        Configure for signature verification.

        Args:
            sig_path: Path to signature file
            input_path: Path to file being verified
        """
        self.cmd.extend(['--verify', sig_path, input_path])
        return self

    def encrypt(self, input_path: str, output_path: str, recipient: str):
        """
        Configure for encryption.

        Args:
            input_path: Path to file to encrypt
            output_path: Path for encrypted output
            recipient: Key fingerprint or ID of recipient
        """
        self.cmd.extend(['--output', output_path, '--encrypt', '--recipient', recipient, input_path])
        return self

    def decrypt(self, input_path: str, output_path: str):
        """
        Configure for decryption.

        Args:
            input_path: Path to encrypted file
            output_path: Path for decrypted output
        """
        self.cmd.extend(['--output', output_path, '--decrypt', input_path])
        return self

    def list_keys(self):
        """Configure for listing keys with machine-readable output."""
        self.cmd.extend(['--list-keys', '--with-colons'])
        return self

    def build(self) -> list:
        """Return the constructed command list."""
        return self.cmd

    def execute(self, operation_name: str) -> subprocess.CompletedProcess:
        """
        Execute the GPG command in an isolated environment.

        Args:
            operation_name: Name of operation for error reporting (e.g., 'signing', 'encryption')

        Returns:
            CompletedProcess result

        Raises:
            GPGOperationError: If the command fails
        """
        _kill_gpg_agent()
        env = _create_gpg_isolated_env(self.gnupg_home)

        result = subprocess.run(
            self.cmd,
            input=self.passphrase_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        if result.returncode != 0:
            raise GPGOperationError(operation_name, result.stderr.decode())

        return result


def _import_key_to_gnupg(gnupg_home: str, key_content: str, key_type: str = 'key', raise_on_error: bool = True) -> bool:
    """
    Import a PGP key into a temporary GPG home directory.

    Args:
        gnupg_home: Path to GPG home directory
        key_content: ASCII-armored key content
        key_type: Type identifier for filename (e.g., 'privkey', 'pubkey')
        raise_on_error: If True, raise exception on import failure; if False, return success status

    Returns:
        True if import succeeded, False if failed (only when raise_on_error=False)

    Raises:
        GPGOperationError: If key import fails and raise_on_error=True
    """
    key_path = os.path.join(gnupg_home, f'{key_type}.asc')
    with open(key_path, 'w') as f:
        f.write(key_content)

    import_cmd = ['gpg', '--homedir', gnupg_home, '--batch', '--import', key_path]
    result = subprocess.run(import_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        if raise_on_error:
            raise GPGOperationError('import', result.stderr.decode())
        return False
    return True


def sign_file(input_path: str, private_key: str, output_path: str, passphrase: Optional[str] = None):
    """
    Signs a file using GPG in a temporary keyring with the provided private key.

    Args:
        input_path: Path to the file to sign
        private_key: ASCII-armored private key
        output_path: Path for the detached signature output
        passphrase: Optional passphrase to unlock the private key

    Raises:
        GPGOperationError: If signing fails
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import private key
        _import_key_to_gnupg(gnupg_home, private_key, 'privkey')

        # Build and execute sign command
        (GPGCommandBuilder(gnupg_home)
         .with_yes()
         .with_pinentry_loopback()
         .with_passphrase_stdin(passphrase)
         .sign(input_path, output_path)
         .execute('signing'))

def verify_signature_file(input_path: str, sig_path: str, public_key: str) -> bool:
    """
    Verifies a file signature using GPG in a temporary keyring.

    Args:
        input_path: Path to the file being verified
        sig_path: Path to the detached signature file
        public_key: ASCII-armored public key of the signer

    Returns:
        True if signature is valid, False otherwise
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import public key (ignore errors to allow verification to proceed)
        _import_key_to_gnupg(gnupg_home, public_key, 'pubkey', raise_on_error=False)

        # Build and execute verify command (returns result without raising exception)
        try:
            (GPGCommandBuilder(gnupg_home)
             .with_trust_always()
             .verify(sig_path, input_path)
             .execute('verification'))
            return True
        except GPGOperationError:
            return False

def encrypt_file(input_path: str, public_key: str, output_path: str):
    """
    Encrypts a file for a recipient using their public key in a temporary keyring.

    Args:
        input_path: Path to the file to encrypt
        public_key: ASCII-armored public key of the recipient
        output_path: Path for the encrypted output

    Raises:
        GPGOperationError: If encryption fails or key fingerprint cannot be extracted
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import public key
        _import_key_to_gnupg(gnupg_home, public_key, 'pubkey')

        # Get key fingerprint using builder
        result = (GPGCommandBuilder(gnupg_home)
                  .list_keys()
                  .execute('key listing'))

        lines = result.stdout.decode().splitlines()
        fpr = None
        for line in lines:
            if line.startswith('fpr:'):
                fpr = line.split(':')[9]
                break

        if not fpr:
            raise GPGOperationError('encryption', 'Could not extract key fingerprint')

        # SECURITY: Validate fingerprint is hexadecimal only to prevent command injection
        import re
        if not re.match(r'^[A-F0-9]+$', fpr, re.IGNORECASE):
            raise GPGOperationError('encryption', 'Invalid key fingerprint format')

        # Encrypt file using builder
        (GPGCommandBuilder(gnupg_home)
         .with_yes()
         .with_trust_always()
         .encrypt(input_path, output_path, fpr)
         .execute('encryption'))

def decrypt_file(input_path: str, private_key: str, output_path: str, passphrase: Optional[str] = None):
    """
    Decrypts a file using the provided private key in a temporary keyring.

    Args:
        input_path: Path to the encrypted file
        private_key: ASCII-armored private key
        output_path: Path for the decrypted output
        passphrase: Optional passphrase to unlock the private key

    Raises:
        GPGOperationError: If decryption fails
    """
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import private key
        _import_key_to_gnupg(gnupg_home, private_key, 'privkey')

        # Build and execute decrypt command
        (GPGCommandBuilder(gnupg_home)
         .with_yes()
         .with_pinentry_loopback()
         .with_passphrase_stdin(passphrase)
         .decrypt(input_path, output_path)
         .execute('decryption'))
