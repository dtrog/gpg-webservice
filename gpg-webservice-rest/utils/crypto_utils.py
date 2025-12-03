"""
Cryptographic utilities for secure key handling and API key generation.

This module provides functions for secure password-based key derivation,
symmetric encryption/decryption using AES-GCM, and secure API key generation.
It uses industry-standard cryptographic practices including Argon2id for
password hashing and AES-GCM for authenticated encryption.
"""

import os
import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Argon2id parameters (OWASP recommendations for password hashing)
ARGON2_TIME_COST = 4        # Number of iterations
ARGON2_MEMORY_COST = 65536  # Memory in KB (64 MB = 2^16 KB)
ARGON2_PARALLELISM = 2      # Number of parallel threads
ARGON2_HASH_LENGTH = 32     # Output length in bytes (256 bits for AES-256)

# PBKDF2 parameters (OWASP recommendations for key derivation)
PBKDF2_ITERATIONS = 100000  # Minimum recommended iterations
PBKDF2_KEY_LENGTH = 32      # Output length in bytes (256 bits)

# Cryptographic sizes
SALT_SIZE = 16              # Bytes for salt (128 bits)
NONCE_SIZE = 12             # Bytes for AES-GCM nonce (96 bits)
API_KEY_SIZE = 32           # Bytes for API key (256 bits)
MASTER_SALT_SIZE = 32       # Bytes for master salt (256 bits)

# Session window parameters for deterministic API keys
SESSION_WINDOW_SECONDS = 3600       # 1 hour session windows
SESSION_GRACE_PERIOD_SECONDS = 600  # 10 minutes grace period for clock skew


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a cryptographic key from a password using Argon2id.
    
    This function uses Argon2id, a memory-hard password hashing function
    that is resistant to both side-channel and GPU-based attacks.
    
    Args:
        password (str): The password to derive a key from
        salt (bytes): A 16-byte random salt for the derivation
        
    Returns:
        bytes: A 32-byte derived key suitable for AES-256 encryption
    """
    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LENGTH,
        type=Type.ID
    )


def encrypt_private_key(private_key_bytes: bytes, password: str) -> bytes:
    """
    Encrypt private key data using password-derived encryption.
    
    This function encrypts private key data using AES-GCM with a key derived
    from the provided password using Argon2id. The output includes the salt,
    nonce, and ciphertext concatenated together.
    
    Args:
        private_key_bytes (bytes): The private key data to encrypt
        password (str): The password to derive the encryption key from
        
    Returns:
        bytes: Concatenated salt (16 bytes) + nonce (12 bytes) + ciphertext
    """
    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ct = aesgcm.encrypt(nonce, private_key_bytes, None)
    return salt + nonce + ct


def decrypt_private_key(enc: bytes, password: str) -> bytes:
    """
    Decrypt private key data using password-derived decryption.
    
    This function decrypts data that was encrypted with encrypt_private_key().
    It extracts the salt and nonce from the encrypted data, derives the key
    using Argon2id, and decrypts using AES-GCM.
    
    Args:
        enc (bytes): Encrypted data (salt + nonce + ciphertext)
        password (str): The password to derive the decryption key from
        
    Returns:
        bytes: The decrypted private key data
        
    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (wrong password or corrupted data)
    """
    salt = enc[:SALT_SIZE]
    nonce = enc[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ct = enc[SALT_SIZE + NONCE_SIZE:]
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None)


def derive_gpg_passphrase(api_key: str, user_id: int) -> str:
    """
    Derive a secure GPG passphrase from API key and user ID using PBKDF2.

    This function creates a deterministic but secure passphrase for GPG operations
    by using PBKDF2-HMAC-SHA256 with the API key as the password and a salt
    derived from the user ID. This provides better security than simple SHA256
    hashing while remaining deterministic for the same inputs.

    Args:
        api_key (str): The user's API key
        user_id (int): The user's unique ID for salt derivation

    Returns:
        str: A 64-character hexadecimal string suitable for use as a GPG passphrase
    """
    # Create a deterministic salt from user_id 
    # Use a fixed string prefix to ensure salt uniqueness across different uses
    salt_data = f"gpg_passphrase_salt_{user_id}".encode('utf-8')
    salt = hashlib.sha256(salt_data).digest()
    
    # Derive key using PBKDF2-HMAC-SHA256
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=PBKDF2_KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(api_key.encode('utf-8'))

    # Return as hexadecimal string for GPG compatibility
    return key.hex()


def generate_api_key() -> str:
    """
    Generate a secure, random API key.

    Creates a cryptographically secure random API key using 32 random bytes
    encoded as base64url (URL-safe base64 without padding). This provides
    approximately 256 bits of entropy.

    Returns:
        str: A base64url-encoded API key string (approximately 43 characters)
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(API_KEY_SIZE)).decode().rstrip('=')


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Uses SHA256 to create a one-way hash of the API key for database storage.
    This prevents API key exposure if the database is compromised while still
    allowing authentication by hashing the provided key and comparing.

    Args:
        api_key (str): The plaintext API key to hash

    Returns:
        str: The SHA256 hash of the API key as a hexadecimal string
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


# =============================================================================
# DETERMINISTIC SESSION KEY DERIVATION
# =============================================================================
# These functions implement a stateless API key system where keys are derived
# from an immutable contract hash rather than stored randomly. This allows
# AI agents to regenerate their session keys without storing secrets.
# =============================================================================


def generate_master_salt() -> str:
    """
    Generate a random master salt for a new user.

    This salt is stored in the database and used with PBKDF2 to derive
    the master secret from the contract hash.

    Returns:
        str: A 64-character hexadecimal string (256 bits of entropy)
    """
    return secrets.token_hex(MASTER_SALT_SIZE)


def derive_master_secret(contract_hash: str, master_salt: str) -> bytes:
    """
    Derive a master secret from the contract hash and salt using PBKDF2.

    The contract_hash is SHA256(successorship_contract + pgp_signature),
    which serves as the "password" in the derivation. The master_salt
    is random and stored per-user.

    Args:
        contract_hash (str): SHA256 hash of the successorship contract + signature
        master_salt (str): Hexadecimal string of the user's master salt

    Returns:
        bytes: 32-byte master secret for session key derivation
    """
    salt_bytes = bytes.fromhex(master_salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=PBKDF2_KEY_LENGTH,
        salt=salt_bytes,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(contract_hash.encode('utf-8'))


def get_session_window(timestamp: float = None) -> int:
    """
    Get the session window index for a given timestamp.

    The window index is the Unix timestamp divided by the session window
    duration (default: 1 hour = 3600 seconds).

    Args:
        timestamp (float, optional): Unix timestamp. Defaults to current time.

    Returns:
        int: The session window index (e.g., 481234 for a specific hour)
    """
    if timestamp is None:
        timestamp = time.time()
    return int(timestamp // SESSION_WINDOW_SECONDS)


def get_session_window_bounds(window_index: int = None) -> tuple:
    """
    Get the start and end timestamps for a session window.

    Args:
        window_index (int, optional): The window index. Defaults to current window.

    Returns:
        tuple: (start_timestamp, end_timestamp, grace_end_timestamp)
    """
    if window_index is None:
        window_index = get_session_window()

    start = window_index * SESSION_WINDOW_SECONDS
    end = start + SESSION_WINDOW_SECONDS
    grace_end = end + SESSION_GRACE_PERIOD_SECONDS

    return (start, end, grace_end)


def derive_session_key(master_secret: bytes, window_index: int) -> str:
    """
    Derive a deterministic session key for a specific time window.

    Uses HMAC-SHA256 to combine the master secret with the window index,
    producing a unique but deterministic key for each session window.

    Args:
        master_secret (bytes): The 32-byte master secret from derive_master_secret()
        window_index (int): The session window index from get_session_window()

    Returns:
        str: A session key prefixed with 'sk_' (e.g., 'sk_a1b2c3d4e5...')
    """
    # Create HMAC-SHA256 of window index using master secret as key
    message = f"session_key_v1:{window_index}".encode('utf-8')
    signature = hmac.new(master_secret, message, hashlib.sha256).digest()

    # Encode as URL-safe base64 and prefix with 'sk_' for identification
    key_part = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    return f"sk_{key_part}"


def is_within_grace_period(timestamp: float = None) -> bool:
    """
    Check if the current time is within the grace period of the previous window.

    The grace period is the first N seconds (default: 10 minutes) of a new
    session window where the previous window's key is still accepted.

    Args:
        timestamp (float, optional): Unix timestamp. Defaults to current time.

    Returns:
        bool: True if within the grace period of the previous window
    """
    if timestamp is None:
        timestamp = time.time()

    current_window = get_session_window(timestamp)
    window_start = current_window * SESSION_WINDOW_SECONDS
    time_into_window = timestamp - window_start

    return time_into_window < SESSION_GRACE_PERIOD_SECONDS


def generate_session_key_for_user(contract_hash: str, master_salt: str,
                                   window_index: int = None) -> dict:
    """
    Generate a complete session key response for a user.

    This is a convenience function that combines all the steps needed to
    generate a session key for a user during login.

    Args:
        contract_hash (str): The user's stored contract hash (password hash)
        master_salt (str): The user's stored master salt
        window_index (int, optional): Session window. Defaults to current.

    Returns:
        dict: Session key information including:
            - api_key: The derived session key (sk_...)
            - window_index: The session window index
            - window_start: ISO timestamp of window start
            - expires_at: ISO timestamp when key expires (including grace period)
    """
    if window_index is None:
        window_index = get_session_window()

    # Derive the session key
    master_secret = derive_master_secret(contract_hash, master_salt)
    session_key = derive_session_key(master_secret, window_index)

    # Calculate timestamps
    start, end, grace_end = get_session_window_bounds(window_index)

    return {
        'api_key': session_key,
        'window_index': window_index,
        'window_start': datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
        'expires_at': datetime.fromtimestamp(grace_end, tz=timezone.utc).isoformat(),
    }


def verify_session_key(contract_hash: str, master_salt: str,
                       provided_key: str) -> tuple:
    """
    Verify a provided session key against the expected derived key.

    This function checks if the provided key matches either the current
    session window or the previous window (if within grace period).

    SECURITY: Uses constant-time comparison to prevent timing attacks.
    Always derives both current and previous keys to avoid timing side-channels.

    Args:
        contract_hash (str): The user's stored contract hash
        master_salt (str): The user's stored master salt
        provided_key (str): The session key provided in the request

    Returns:
        tuple: (is_valid: bool, window_used: int or None, message: str)
    """
    master_secret = derive_master_secret(contract_hash, master_salt)
    current_window = get_session_window()
    previous_window = current_window - 1

    # SECURITY: Always derive both keys (constant-time behavior)
    # This prevents timing attacks that could reveal grace period boundaries
    expected_current = derive_session_key(master_secret, current_window)
    expected_previous = derive_session_key(master_secret, previous_window)

    # Check current window (constant-time comparison)
    valid_current = hmac.compare_digest(provided_key, expected_current)

    # Check previous window (constant-time comparison)
    valid_previous = hmac.compare_digest(provided_key, expected_previous)

    # Only accept previous window if within grace period
    within_grace = is_within_grace_period()

    # Return results (checked in order of preference)
    if valid_current:
        return (True, current_window, "Valid for current session window")
    elif valid_previous and within_grace:
        return (True, previous_window, "Valid via grace period (previous window)")
    else:
        return (False, None, "Invalid or expired session key")
