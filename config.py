"""
Centralized configuration for GPG Webservice.

This module provides a single source of truth for all configuration settings,
with environment variable support and validation.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Base configuration class with common settings."""

    # Application
    APP_NAME = "GPG Webservice"
    APP_VERSION = "1.0.0"

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    TESTING = os.environ.get('TESTING', 'false').lower() == 'true'
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    PORT = int(os.environ.get('PORT', 5555))
    HOST = os.environ.get('HOST', '0.0.0.0')

    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///gpg_users.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # File Uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/gpg_uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', 10))  # File upload limit
    MAX_SIGNATURE_SIZE_MB = int(os.environ.get('MAX_SIGNATURE_SIZE_MB', 1))  # Signature files

    # Rate Limiting
    RATE_LIMIT_ENABLED = not TESTING  # Disable in tests
    RATE_LIMIT_AUTH_REQUESTS = int(os.environ.get('RATE_LIMIT_AUTH_REQUESTS', 5))  # per minute
    RATE_LIMIT_AUTH_WINDOW = int(os.environ.get('RATE_LIMIT_AUTH_WINDOW', 60))  # seconds
    RATE_LIMIT_API_REQUESTS = int(os.environ.get('RATE_LIMIT_API_REQUESTS', 30))  # per minute
    RATE_LIMIT_API_WINDOW = int(os.environ.get('RATE_LIMIT_API_WINDOW', 60))  # seconds

    # Challenge Settings
    CHALLENGE_MAX_PER_USER = int(os.environ.get('CHALLENGE_MAX_PER_USER', 100))
    CHALLENGE_MAX_AGE_DAYS = int(os.environ.get('CHALLENGE_MAX_AGE_DAYS', 7))

    # Username Validation
    USERNAME_MIN_LENGTH = int(os.environ.get('USERNAME_MIN_LENGTH', 3))
    USERNAME_MAX_LENGTH = int(os.environ.get('USERNAME_MAX_LENGTH', 50))
    USERNAME_PATTERN = r'^[a-zA-Z0-9_-]+$'
    USERNAME_RESERVED = {'admin', 'root', 'administrator', 'system', 'test', 'null', 'undefined'}

    # Password Validation
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_MAX_LENGTH = int(os.environ.get('PASSWORD_MAX_LENGTH', 128))
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_DIGIT = os.environ.get('PASSWORD_REQUIRE_DIGIT', 'true').lower() == 'true'
    PASSWORD_REQUIRE_SPECIAL = os.environ.get('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'
    PASSWORD_SPECIAL_CHARS = r'!@#$%^&*(),.?":{}|<>'

    # Email Validation
    EMAIL_MAX_LENGTH = int(os.environ.get('EMAIL_MAX_LENGTH', 254))
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # Security Headers
    SECURITY_HEADERS_ENABLED = os.environ.get('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'
    HSTS_MAX_AGE = int(os.environ.get('HSTS_MAX_AGE', 31536000))  # 1 year
    CSP_POLICY = os.environ.get('CSP_POLICY', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'")

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')  # 'json' or 'text'
    LOG_FILE = os.environ.get('LOG_FILE', None)  # None = stdout only
    AUDIT_LOG_FILE = os.environ.get('AUDIT_LOG_FILE', 'audit.log')

    # GPG Settings
    GPG_KEYSTORE_PATH = os.environ.get('GPG_KEYSTORE_PATH', '/srv/gpg-keystore')
    GPG_KEY_LENGTH = int(os.environ.get('GPG_KEY_LENGTH', 3072))  # RSA key length
    GPG_KEY_TYPE = os.environ.get('GPG_KEY_TYPE', 'RSA')

    # API Keys
    API_KEY_LENGTH = int(os.environ.get('API_KEY_LENGTH', 32))  # bytes, before base64
    API_KEY_HASH_ALGORITHM = os.environ.get('API_KEY_HASH_ALGORITHM', 'sha256')

    # PBKDF2 Settings for GPG Passphrase Derivation
    PBKDF2_ITERATIONS = int(os.environ.get('PBKDF2_ITERATIONS', 100000))
    PBKDF2_ALGORITHM = os.environ.get('PBKDF2_ALGORITHM', 'sha256')

    @classmethod
    def validate(cls):
        """Validate configuration values."""
        errors = []

        # Validate rate limits
        if cls.RATE_LIMIT_AUTH_REQUESTS < 1:
            errors.append("RATE_LIMIT_AUTH_REQUESTS must be >= 1")
        if cls.RATE_LIMIT_API_REQUESTS < 1:
            errors.append("RATE_LIMIT_API_REQUESTS must be >= 1")

        # Validate file sizes
        if cls.MAX_FILE_SIZE_MB < 1:
            errors.append("MAX_FILE_SIZE_MB must be >= 1")

        # Validate username constraints
        if cls.USERNAME_MIN_LENGTH < 1:
            errors.append("USERNAME_MIN_LENGTH must be >= 1")
        if cls.USERNAME_MAX_LENGTH < cls.USERNAME_MIN_LENGTH:
            errors.append("USERNAME_MAX_LENGTH must be >= USERNAME_MIN_LENGTH")

        # Validate password constraints
        if cls.PASSWORD_MIN_LENGTH < 1:
            errors.append("PASSWORD_MIN_LENGTH must be >= 1")
        if cls.PASSWORD_MAX_LENGTH < cls.PASSWORD_MIN_LENGTH:
            errors.append("PASSWORD_MAX_LENGTH must be >= PASSWORD_MIN_LENGTH")

        # Validate challenge settings
        if cls.CHALLENGE_MAX_PER_USER < 1:
            errors.append("CHALLENGE_MAX_PER_USER must be >= 1")
        if cls.CHALLENGE_MAX_AGE_DAYS < 1:
            errors.append("CHALLENGE_MAX_AGE_DAYS must be >= 1")

        # Validate GPG settings
        if cls.GPG_KEY_LENGTH not in [2048, 3072, 4096]:
            errors.append("GPG_KEY_LENGTH must be 2048, 3072, or 4096")

        # Validate API key settings
        if cls.API_KEY_LENGTH < 16:
            errors.append("API_KEY_LENGTH must be >= 16 for security")

        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        return True

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        Path(cls.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True, mode=0o700)
        if cls.LOG_FILE:
            Path(cls.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        if cls.AUDIT_LOG_FILE:
            Path(cls.AUDIT_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'  # In-memory database for tests
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    RATE_LIMIT_ENABLED = False  # Disable rate limiting in tests
    SECURITY_HEADERS_ENABLED = True  # Still test headers


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False

    # Production should use strong secret key from environment
    @classmethod
    def validate(cls):
        """Additional validation for production."""
        super().validate()
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production")
        if cls.DATABASE_URL.startswith('sqlite:///'):
            import warnings
            warnings.warn("SQLite is not recommended for production. Use PostgreSQL or MySQL.")


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env: Optional[str] = None) -> type[Config]:
    """
    Get configuration class for specified environment.

    Args:
        env: Environment name ('development', 'testing', 'production')
             If None, uses FLASK_ENV environment variable

    Returns:
        Configuration class for the environment
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')

    config_class = config.get(env, config['default'])
    config_class.validate()
    config_class.ensure_directories()

    return config_class
