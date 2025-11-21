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
import secrets
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
