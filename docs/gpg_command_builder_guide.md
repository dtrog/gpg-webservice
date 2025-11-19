# GPGCommandBuilder Developer Guide

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Usage Patterns](#usage-patterns)
- [Testing Guide](#testing-guide)
- [Design Rationale](#design-rationale)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Overview

The `GPGCommandBuilder` class provides a fluent, builder-pattern interface for constructing and executing GPG commands with consistent security settings and error handling.

### Key Benefits
- **Readability**: Self-documenting method names (`.sign()`, `.encrypt()`, etc.)
- **Safety**: Automatic environment isolation and GPG agent cleanup
- **Testability**: Can test command construction without executing GPG
- **Maintainability**: Single source of truth for GPG command construction
- **Consistency**: Uniform error handling across all operations

### Location
```python
from utils.gpg_file_utils import GPGCommandBuilder
```

**File**: `utils/gpg_file_utils.py` (lines 43-170)

---

## Quick Start

### Basic Signing
```python
from utils.gpg_file_utils import GPGCommandBuilder, _import_key_to_gnupg
import tempfile

with tempfile.TemporaryDirectory() as gnupg_home:
    # Import key first
    _import_key_to_gnupg(gnupg_home, private_key, 'privkey')

    # Build and execute sign command
    (GPGCommandBuilder(gnupg_home)
     .with_yes()
     .with_pinentry_loopback()
     .with_passphrase_stdin(passphrase)
     .sign(input_path, output_path)
     .execute('signing'))
```

### Basic Verification
```python
with tempfile.TemporaryDirectory() as gnupg_home:
    _import_key_to_gnupg(gnupg_home, public_key, 'pubkey', raise_on_error=False)

    try:
        (GPGCommandBuilder(gnupg_home)
         .with_trust_always()
         .verify(sig_path, input_path)
         .execute('verification'))
        return True  # Signature valid
    except GPGOperationError:
        return False  # Signature invalid
```

---

## API Reference

### Constructor

#### `__init__(gnupg_home: str)`
Initialize the builder with a GPG home directory.

**Parameters**:
- `gnupg_home` (str): Path to temporary GPG home directory

**Returns**: GPGCommandBuilder instance

**Example**:
```python
builder = GPGCommandBuilder('/tmp/tmpdir123')
```

**Initial Command**: `['gpg', '--homedir', gnupg_home, '--batch']`

---

### Configuration Methods (Chainable)

All configuration methods return `self` for method chaining.

#### `with_yes() -> self`
Add `--yes` flag to auto-confirm all prompts.

**Use Case**: Required for non-interactive operations (signing, encryption, decryption)

**Adds to Command**: `['--yes']`

**Example**:
```python
builder.with_yes()
# Command becomes: ['gpg', '--homedir', '...', '--batch', '--yes']
```

---

#### `with_passphrase_stdin(passphrase: Optional[str]) -> self`
Configure passphrase input via stdin (secure method).

**Parameters**:
- `passphrase` (Optional[str]): Passphrase to unlock private key. If `None`, no passphrase configured.

**Security**: Uses `--passphrase-fd 0` to pass passphrase via stdin, preventing exposure in process list (`ps aux`).

**Adds to Command**: `['--passphrase-fd', '0']` (if passphrase provided)

**Sets Internal State**: `self.passphrase_input = (passphrase + '\n').encode()`

**Example**:
```python
builder.with_passphrase_stdin(user_passphrase)  # With passphrase
# Command: ['gpg', '--homedir', '...', '--batch', '--passphrase-fd', '0']
# Internal: passphrase_input = b'user_passphrase\n'

builder.with_passphrase_stdin(None)              # Without passphrase
# Command unchanged, passphrase_input = None
```

---

#### `with_pinentry_loopback() -> self`
Use loopback pinentry mode for non-interactive passphrase entry.

**Flags Added**: `['--pinentry-mode', 'loopback', '--no-use-agent']`

**Use Case**: Required when using passphrases in automated/server environments without interactive terminals

**Example**:
```python
builder.with_pinentry_loopback()
# Command: ['gpg', '--homedir', '...', '--batch', '--pinentry-mode', 'loopback', '--no-use-agent']
```

---

#### `with_trust_always() -> self`
Trust all keys unconditionally (for isolated operations).

**Flags Added**: `['--trust-model', 'always']`

**Use Case**: Verification operations in isolated temporary keyrings where trust db is not available

**Example**:
```python
builder.with_trust_always()
# Command: ['gpg', '--homedir', '...', '--batch', '--trust-model', 'always']
```

---

### Operation Methods (Chainable)

#### `sign(input_path: str, output_path: str) -> self`
Configure for detached signature creation.

**Parameters**:
- `input_path` (str): Path to file to sign
- `output_path` (str): Path for signature output (detached signature)

**Flags Added**: `['--output', output_path, '--detach-sign', input_path]`

**Example**:
```python
builder.sign('/tmp/document.txt', '/tmp/document.txt.sig')
# Command: [..., '--output', '/tmp/document.txt.sig', '--detach-sign', '/tmp/document.txt']
```

---

#### `verify(sig_path: str, input_path: str) -> self`
Configure for signature verification.

**Parameters**:
- `sig_path` (str): Path to signature file (detached signature)
- `input_path` (str): Path to file being verified

**Flags Added**: `['--verify', sig_path, input_path]`

**Example**:
```python
builder.verify('/tmp/document.txt.sig', '/tmp/document.txt')
# Command: [..., '--verify', '/tmp/document.txt.sig', '/tmp/document.txt']
```

---

#### `encrypt(input_path: str, output_path: str, recipient: str) -> self`
Configure for encryption.

**Parameters**:
- `input_path` (str): Path to file to encrypt
- `output_path` (str): Path for encrypted output
- `recipient` (str): Key fingerprint or ID of recipient

**Flags Added**: `['--output', output_path, '--encrypt', '--recipient', recipient, input_path]`

**Example**:
```python
fpr = "1234567890ABCDEF1234567890ABCDEF12345678"
builder.encrypt('/tmp/secret.txt', '/tmp/secret.txt.gpg', fpr)
# Command: [..., '--output', '/tmp/secret.txt.gpg', '--encrypt', '--recipient', fpr, '/tmp/secret.txt']
```

**Note**: You must obtain the recipient's key fingerprint first (see encryption usage pattern).

---

#### `decrypt(input_path: str, output_path: str) -> self`
Configure for decryption.

**Parameters**:
- `input_path` (str): Path to encrypted file
- `output_path` (str): Path for decrypted output

**Flags Added**: `['--output', output_path, '--decrypt', input_path]`

**Example**:
```python
builder.decrypt('/tmp/secret.txt.gpg', '/tmp/secret.txt')
# Command: [..., '--output', '/tmp/secret.txt', '--decrypt', '/tmp/secret.txt.gpg']
```

---

#### `list_keys() -> self`
Configure for listing keys with machine-readable output.

**Flags Added**: `['--list-keys', '--with-colons']`

**Use Case**: Extracting key fingerprints for encryption

**Output Format**: Colon-separated values (one key per line)

**Example**:
```python
result = (GPGCommandBuilder(gnupg_home)
          .list_keys()
          .execute('key listing'))

lines = result.stdout.decode().splitlines()
for line in lines:
    if line.startswith('fpr:'):
        fingerprint = line.split(':')[9]
        print(f"Found key: {fingerprint}")
```

---

### Execution Methods

#### `build() -> list`
Return the constructed command list without executing.

**Returns**: List of command arguments (as would be passed to `subprocess.run`)

**Use Case**: Testing, debugging, logging

**Example**:
```python
cmd = (GPGCommandBuilder(gnupg_home)
       .with_yes()
       .sign(input_path, output_path)
       .build())

print(cmd)
# Output: ['gpg', '--homedir', '/tmp/...', '--batch', '--yes', '--output', '/tmp/...', '--detach-sign', '/tmp/...']

# Use in tests without executing GPG
assert '--yes' in cmd
assert '--detach-sign' in cmd
```

---

#### `execute(operation_name: str) -> subprocess.CompletedProcess`
Execute the GPG command in an isolated environment.

**Parameters**:
- `operation_name` (str): Name for error reporting (e.g., 'signing', 'encryption', 'verification')

**Returns**: `subprocess.CompletedProcess` with stdout/stderr

**Raises**: `GPGOperationError` if command fails (non-zero exit code)

**Automatic Actions**:
1. Kills any existing GPG agent (`_kill_gpg_agent()`)
2. Creates isolated environment (`_create_gpg_isolated_env()`)
3. Executes command with passphrase via stdin if configured
4. Raises `GPGOperationError` with stderr on failure

**Example**:
```python
try:
    result = (GPGCommandBuilder(gnupg_home)
              .sign(input_path, output_path)
              .execute('signing'))
    # Success: result contains stdout/stderr
    print("Signing successful")
except GPGOperationError as e:
    # Failure: exception contains operation name and GPG error message
    print(f"Signing failed: {e}")
```

**Internal Implementation**:
```python
def execute(self, operation_name: str) -> subprocess.CompletedProcess:
    _kill_gpg_agent()  # Cleanup
    env = _create_gpg_isolated_env(self.gnupg_home)  # Isolation

    result = subprocess.run(
        self.cmd,
        input=self.passphrase_input,  # Passphrase via stdin
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )

    if result.returncode != 0:
        raise GPGOperationError(operation_name, result.stderr.decode())

    return result
```

---

## Usage Patterns

### Pattern 1: Signing with Passphrase
```python
def sign_file(input_path, private_key, output_path, passphrase=None):
    """Sign a file using GPG."""
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
```

**Key Points**:
- Import key first with `_import_key_to_gnupg()`
- Use `with_yes()` for non-interactive operation
- Use `with_pinentry_loopback()` when using passphrase
- Use `with_passphrase_stdin()` to securely pass passphrase
- `execute()` raises `GPGOperationError` on failure

---

### Pattern 2: Verification with Error Handling
```python
def verify_signature(input_path, sig_path, public_key) -> bool:
    """Verify a file signature, returning True/False."""
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import public key (ignore import errors)
        _import_key_to_gnupg(gnupg_home, public_key, 'pubkey', raise_on_error=False)

        # Try to verify
        try:
            (GPGCommandBuilder(gnupg_home)
             .with_trust_always()
             .verify(sig_path, input_path)
             .execute('verification'))
            return True  # Signature is valid
        except GPGOperationError:
            return False  # Signature is invalid or verification failed
```

**Key Points**:
- Import with `raise_on_error=False` (verification can proceed even if import fails)
- Use `with_trust_always()` for isolated keyring
- Catch `GPGOperationError` to return boolean instead of raising exception
- No passphrase needed for verification (uses public key)

---

### Pattern 3: Encryption with Fingerprint Extraction
```python
def encrypt_file(input_path, public_key, output_path):
    """Encrypt a file for a recipient."""
    with tempfile.TemporaryDirectory() as gnupg_home:
        # Import recipient's public key
        _import_key_to_gnupg(gnupg_home, public_key, 'pubkey')

        # Extract key fingerprint
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

        # Encrypt file using fingerprint
        (GPGCommandBuilder(gnupg_home)
         .with_yes()
         .with_trust_always()
         .encrypt(input_path, output_path, fpr)
         .execute('encryption'))
```

**Key Points**:
- First use `.list_keys()` to get key fingerprint
- Parse colon-separated output to extract fingerprint
- Use fingerprint (not key ID) for encryption
- Use `with_trust_always()` for isolated keyring

---

### Pattern 4: Decryption
```python
def decrypt_file(input_path, private_key, output_path, passphrase=None):
    """Decrypt a file using private key."""
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
```

**Key Points**:
- Similar to signing (requires private key and passphrase)
- Use `with_passphrase_stdin()` to provide passphrase
- File is decrypted to `output_path`

---

## Testing Guide

### Unit Testing: Command Construction

Test command building without executing GPG:

```python
def test_sign_command_construction():
    """Test that sign() adds correct flags."""
    builder = GPGCommandBuilder('/tmp/test')
    cmd = builder.with_yes().sign('/in.txt', '/out.sig').build()

    assert 'gpg' in cmd
    assert '--homedir' in cmd
    assert '/tmp/test' in cmd
    assert '--batch' in cmd
    assert '--yes' in cmd
    assert '--output' in cmd
    assert '/out.sig' in cmd
    assert '--detach-sign' in cmd
    assert '/in.txt' in cmd

def test_passphrase_configuration():
    """Test that passphrase is configured correctly."""
    builder = GPGCommandBuilder('/tmp/test')
    builder.with_passphrase_stdin('my_secret')

    cmd = builder.build()
    assert '--passphrase-fd' in cmd
    assert '0' in cmd
    assert builder.passphrase_input == b'my_secret\n'

def test_no_passphrase():
    """Test that None passphrase doesn't add flags."""
    builder = GPGCommandBuilder('/tmp/test')
    builder.with_passphrase_stdin(None)

    cmd = builder.build()
    assert '--passphrase-fd' not in cmd
    assert builder.passphrase_input is None

def test_method_chaining():
    """Test that all methods return self for chaining."""
    builder = GPGCommandBuilder('/tmp/test')
    result = (builder
              .with_yes()
              .with_trust_always()
              .with_pinentry_loopback()
              .sign('/in', '/out'))

    assert result is builder  # Methods return self

    cmd = builder.build()
    assert '--yes' in cmd
    assert '--trust-model' in cmd
    assert 'always' in cmd
    assert '--pinentry-mode' in cmd
```

### Integration Testing: With Mock

```python
from unittest.mock import patch, MagicMock
import pytest

def test_execute_success():
    """Test successful GPG command execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b'signature created',
            stderr=b''
        )

        builder = GPGCommandBuilder('/tmp/test')
        result = builder.sign('/in.txt', '/out.sig').execute('signing')

        assert result.returncode == 0
        mock_run.assert_called_once()

def test_execute_failure():
    """Test GPG command failure handling."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=2,
            stdout=b'',
            stderr=b'gpg: signing failed: Bad passphrase'
        )

        builder = GPGCommandBuilder('/tmp/test')

        with pytest.raises(GPGOperationError) as exc_info:
            builder.sign('/in.txt', '/out.sig').execute('signing')

        assert 'signing' in str(exc_info.value)
        assert 'Bad passphrase' in str(exc_info.value)
```

---

## Design Rationale

### Why Builder Pattern?

**Problem**: GPG command construction was duplicated across 4 functions with ~77 lines of similar code.

**Solution**: Builder pattern provides:

1. **Fluent Interface**: Readable, self-documenting method chains
   ```python
   # Easy to read and understand
   builder.with_yes().with_trust_always().sign(input, output)
   ```

2. **Reusability**: Single implementation for all operations
   - No more copy-pasting command construction code
   - Change once, fixes everywhere

3. **Testability**: Can test command construction without GPG
   ```python
   cmd = builder.sign(input, output).build()
   assert '--detach-sign' in cmd
   ```

4. **Extensibility**: Easy to add new operations or flags
   ```python
   # Just add a new method
   def with_armor(self):
       self.cmd.append('--armor')
       return self
   ```

### Why Centralized Execution?

The `.execute()` method centralizes:

- **GPG agent cleanup** (`_kill_gpg_agent()`)
- **Environment isolation** (`_create_gpg_isolated_env()`)
- **Error handling** (raises `GPGOperationError`)
- **Subprocess execution** with stdin passphrase

**Benefit**: Ensures **consistent security** across all GPG operations.

**Before (Duplicated)**:
```python
# Duplicated in 4 places
_kill_gpg_agent()
env = _create_gpg_isolated_env(gnupg_home)
result = subprocess.run(cmd, input=passphrase_input, env=env, ...)
if result.returncode != 0:
    raise GPGOperationError(...)
```

**After (Centralized)**:
```python
# Single implementation in execute()
result = builder.execute('operation_name')
```

### Security Considerations

1. **Passphrase Safety**: Uses stdin (`--passphrase-fd 0`), never command-line arguments
   - Command-line arguments visible in `ps aux` (security risk)
   - Stdin input not visible in process list

2. **Process Isolation**: Kills GPG agent before each operation
   - Prevents agent from caching keys
   - Ensures clean state for each operation

3. **Environment Isolation**: Custom environment variables prevent system interference
   - `GNUPGHOME`: Uses temporary directory, not system keyring
   - Disables GPG agent, TTY, X11 prompts

4. **Temporary Storage**: All operations in temporary directories
   - Keys never written to persistent storage
   - Automatic cleanup via `tempfile.TemporaryDirectory()`

5. **Error Propagation**: Failures raise exceptions with descriptive messages
   - No silent failures
   - Error messages include operation name and GPG stderr

---

## Troubleshooting

### Common Issues

#### Error: "gpg: signing failed: Inappropriate ioctl for device"

**Cause**: Missing `with_pinentry_loopback()` configuration when using passphrase

**Solution**:
```python
builder.with_pinentry_loopback()  # Add this when using passphrases
```

**Explanation**: GPG tries to use interactive pinentry by default. In server/automated environments, you must use loopback mode.

---

#### Error: "gpg: no default secret key: No secret key"

**Cause**: Private key not imported to keyring before signing/decrypting

**Solution**:
```python
_import_key_to_gnupg(gnupg_home, private_key, 'privkey')  # Import before operation
```

**Explanation**: GPG can't sign/decrypt without a private key in the keyring.

---

#### Error: "gpg: decryption failed: No secret key"

**Cause**: Wrong key type imported (public instead of private)

**Solution**:
```python
# For signing/decryption: use private key
_import_key_to_gnupg(gnupg_home, private_key, 'privkey')

# For verification/encryption: use public key
_import_key_to_gnupg(gnupg_home, public_key, 'pubkey')
```

---

#### Verification Always Fails

**Cause**: Missing `with_trust_always()` configuration

**Solution**:
```python
builder.with_trust_always()  # Trust keys in isolated keyring
```

**Explanation**: Isolated keyrings don't have trust database. Use `--trust-model always` to bypass trust checks.

---

#### Error: "gpg: signing failed: Bad passphrase"

**Cause**: Incorrect passphrase or passphrase not provided

**Solutions**:
1. Check passphrase is correct
2. Ensure `with_passphrase_stdin()` is called with passphrase
3. Verify key actually requires passphrase

```python
# Make sure passphrase is provided
builder.with_passphrase_stdin(passphrase)  # Not None
```

---

### Debugging Tips

#### 1. Inspect Command Before Execution
```python
cmd = builder.sign(input_path, output_path).build()
print("GPG Command:", ' '.join(cmd))
# Output: gpg --homedir /tmp/... --batch --yes --output /tmp/... --detach-sign /tmp/...
```

#### 2. Check GPG Error Output
```python
try:
    result = builder.execute('signing')
except GPGOperationError as e:
    print(f"GPG Error: {e}")  # Contains operation name and stderr
```

#### 3. Verify Key Import
```python
# Check if key was imported successfully
result = GPGCommandBuilder(gnupg_home).list_keys().execute('listing')
print(result.stdout.decode())  # Should show imported key
```

#### 4. Test Without Execution
```python
# Build command without executing
cmd = builder.sign(input, output).build()
print(cmd)  # See exact command that would be executed
```

---

## References

- **GPG Manual**: [https://www.gnupg.org/documentation/manuals/gnupg/](https://www.gnupg.org/documentation/manuals/gnupg/)
- **Code Architecture**: [architecture.md](architecture.md)
- **Security Best Practices**: [../security.md](../security.md)
- **Refactoring Changelog**: [refactoring_changelog_2025.md](refactoring_changelog_2025.md)
- **Error Handling Guide**: [error_handling.md](error_handling.md)
