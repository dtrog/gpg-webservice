"""
Audit logging for security-critical operations.

This module provides structured logging for security events including authentication,
GPG operations, rate limiting, and errors. Logs are formatted as JSON for easy parsing
and analysis by security monitoring tools.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, has_request_context
from config import Config


# Define audit event types
class AuditEventType:
    """Enumeration of audit event types."""
    # Authentication events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    REGISTRATION = "user.registration"
    LOGIN_SUCCESS = "user.login.success"
    LOGIN_FAILURE = "user.login.failure"

    # GPG operations
    GPG_SIGN = "gpg.sign"
    GPG_VERIFY = "gpg.verify"
    GPG_ENCRYPT = "gpg.encrypt"
    GPG_DECRYPT = "gpg.decrypt"
    GPG_KEYGEN = "gpg.keygen"

    # Challenge operations
    CHALLENGE_CREATE = "challenge.create"
    CHALLENGE_VERIFY_SUCCESS = "challenge.verify.success"
    CHALLENGE_VERIFY_FAILURE = "challenge.verify.failure"

    # Security events
    RATE_LIMIT_HIT = "security.rate_limit"
    INVALID_API_KEY = "security.invalid_api_key"
    FILE_UPLOAD = "security.file_upload"

    # Errors
    ERROR_GPG = "error.gpg"
    ERROR_DATABASE = "error.database"
    ERROR_VALIDATION = "error.validation"


class AuditLogger:
    """
    Centralized audit logger for security events.

    Logs are structured JSON with consistent fields:
    - timestamp: ISO8601 timestamp
    - event_type: Type of event (see AuditEventType)
    - user_id: User ID if authenticated
    - username: Username if known
    - ip_address: Client IP address
    - user_agent: Client user agent
    - data: Event-specific data
    - status: success/failure
    - message: Human-readable message
    """

    def __init__(self):
        """Initialize the audit logger."""
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

        # Configure handler based on config
        if Config.AUDIT_LOG_FILE:
            handler = logging.FileHandler(Config.AUDIT_LOG_FILE)
        else:
            handler = logging.StreamHandler(sys.stdout)

        # Use JSON formatter if configured
        if Config.LOG_FORMAT == 'json':
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _get_request_context(self) -> Dict[str, Any]:
        """Extract request context information."""
        context = {}

        if has_request_context():
            context['ip_address'] = request.remote_addr
            context['user_agent'] = request.headers.get('User-Agent', 'Unknown')
            context['method'] = request.method
            context['path'] = request.path
            context['endpoint'] = request.endpoint

        return context

    def log_event(
        self,
        event_type: str,
        status: str = 'success',
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        message: Optional[str] = None,
        **data
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of event (use AuditEventType constants)
            status: 'success' or 'failure'
            user_id: User ID if applicable
            username: Username if known
            message: Human-readable message
            **data: Additional event-specific data
        """
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'status': status,
        }

        # Add request context
        event.update(self._get_request_context())

        # Add user info
        if user_id:
            event['user_id'] = user_id
        if username:
            event['username'] = username

        # Add message
        if message:
            event['message'] = message

        # Add additional data
        if data:
            event['data'] = data

        # Log at appropriate level
        if status == 'failure' or event_type.startswith('error.'):
            self.logger.warning(json.dumps(event) if Config.LOG_FORMAT == 'json' else str(event))
        else:
            self.logger.info(json.dumps(event) if Config.LOG_FORMAT == 'json' else str(event))

    # Convenience methods for common events

    def log_auth_success(self, user_id: int, username: str, method: str = 'api_key'):
        """Log successful authentication."""
        self.log_event(
            AuditEventType.AUTH_SUCCESS,
            user_id=user_id,
            username=username,
            message=f'User {username} authenticated successfully',
            auth_method=method
        )

    def log_auth_failure(self, username: Optional[str] = None, reason: str = 'invalid_credentials'):
        """Log failed authentication attempt."""
        self.log_event(
            AuditEventType.AUTH_FAILURE,
            status='failure',
            username=username,
            message=f'Authentication failed: {reason}',
            reason=reason
        )

    def log_registration(self, user_id: int, username: str, email: Optional[str] = None):
        """Log user registration."""
        self.log_event(
            AuditEventType.REGISTRATION,
            user_id=user_id,
            username=username,
            message=f'New user registered: {username}',
            email=email
        )

    def log_gpg_operation(self, operation: str, user_id: int, username: str, **details):
        """Log GPG operation (sign, verify, encrypt, decrypt)."""
        event_type = f"gpg.{operation}"
        self.log_event(
            event_type,
            user_id=user_id,
            username=username,
            message=f'GPG {operation} operation by {username}',
            **details
        )

    def log_challenge_create(self, user_id: int, challenge_id: int):
        """Log challenge creation."""
        self.log_event(
            AuditEventType.CHALLENGE_CREATE,
            user_id=user_id,
            message=f'Challenge created for user {user_id}',
            challenge_id=challenge_id
        )

    def log_challenge_verify(self, user_id: int, success: bool, reason: Optional[str] = None):
        """Log challenge verification attempt."""
        event_type = AuditEventType.CHALLENGE_VERIFY_SUCCESS if success else AuditEventType.CHALLENGE_VERIFY_FAILURE
        self.log_event(
            event_type,
            status='success' if success else 'failure',
            user_id=user_id,
            message=f'Challenge verification {"succeeded" if success else "failed"}',
            reason=reason
        )

    def log_rate_limit_hit(self, limit_type: str, username: Optional[str] = None):
        """Log rate limit violation."""
        self.log_event(
            AuditEventType.RATE_LIMIT_HIT,
            status='failure',
            username=username,
            message=f'Rate limit exceeded: {limit_type}',
            limit_type=limit_type
        )

    def log_file_upload(self, user_id: int, filename: str, size: int, file_type: str):
        """Log file upload."""
        self.log_event(
            AuditEventType.FILE_UPLOAD,
            user_id=user_id,
            message=f'File uploaded: {filename}',
            filename=filename,
            size_bytes=size,
            file_type=file_type
        )

    def log_error(self, error_type: str, message: str, **details):
        """Log error event."""
        event_type = f"error.{error_type}"
        self.log_event(
            event_type,
            status='failure',
            message=message,
            **details
        )


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
        }

        # If the message is already JSON (from audit logger), parse it
        try:
            message_data = json.loads(record.getMessage())
            log_data.update(message_data)
        except (json.JSONDecodeError, ValueError):
            # Not JSON, just use the message
            log_data['message'] = record.getMessage()

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


# Global audit logger instance
audit_logger = AuditLogger()


def audit_log(event_type: str, **default_data):
    """
    Decorator to automatically log function calls.

    Usage:
        @audit_log(AuditEventType.GPG_SIGN, operation='sign')
        def sign_data(user_id, data):
            ...

    Args:
        event_type: Type of event to log
        **default_data: Default data to include in log
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)

                # Extract user info from kwargs if present
                user_id = kwargs.get('user_id')
                username = kwargs.get('username')

                # Log success
                audit_logger.log_event(
                    event_type,
                    status='success',
                    user_id=user_id,
                    username=username,
                    **default_data
                )

                return result
            except Exception as e:
                # Log failure
                audit_logger.log_event(
                    event_type,
                    status='failure',
                    message=str(e),
                    **default_data
                )
                raise

        return wrapper
    return decorator
