"""
Standardized error handling utilities for the GPG webservice.

This module provides consistent error response formatting, custom exception classes,
and error logging for all API endpoints.
"""

from flask import jsonify
from typing import Optional, Tuple, Dict, Any
import logging

from utils.audit_logger import audit_logger


# Custom exception classes for domain-specific errors
class GPGWebserviceError(Exception):
    """Base exception for all GPG webservice errors."""

    def __init__(self, message: str, error_code: str = 'INTERNAL_ERROR', status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(GPGWebserviceError):
    """Exception raised for input validation failures."""

    def __init__(self, message: str, error_code: str = 'VALIDATION_ERROR'):
        super().__init__(message, error_code, 400)


class AuthenticationError(GPGWebserviceError):
    """Exception raised for authentication failures."""

    def __init__(self, message: str, error_code: str = 'AUTH_ERROR'):
        super().__init__(message, error_code, 401)


class AuthorizationError(GPGWebserviceError):
    """Exception raised for authorization failures."""

    def __init__(self, message: str, error_code: str = 'AUTHORIZATION_ERROR'):
        super().__init__(message, error_code, 403)


class ResourceNotFoundError(GPGWebserviceError):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str, error_code: str = 'NOT_FOUND'):
        super().__init__(message, error_code, 404)


class GPGOperationError(GPGWebserviceError):
    """Exception raised for GPG operation failures."""

    def __init__(self, operation: str, message: str, error_code: str = 'GPG_ERROR'):
        full_message = f"GPG {operation} failed: {message}"
        super().__init__(full_message, error_code, 500)
        self.operation = operation


class DatabaseError(GPGWebserviceError):
    """Exception raised for database operation failures."""

    def __init__(self, message: str, error_code: str = 'DATABASE_ERROR'):
        super().__init__(message, error_code, 500)


class RateLimitError(GPGWebserviceError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = 'Rate limit exceeded', error_code: str = 'RATE_LIMIT_EXCEEDED'):
        super().__init__(message, error_code, 429)


def create_error_response(
    error: Exception,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    include_details: bool = False
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response with logging.

    Args:
        error: The exception that occurred
        user_id: Optional user ID for logging
        username: Optional username for logging
        include_details: Whether to include technical details (only in development)

    Returns:
        Tuple of (response dict, status code)
    """
    # Handle custom GPGWebserviceError exceptions
    if isinstance(error, GPGWebserviceError):
        status_code = error.status_code
        error_code = error.error_code
        message = error.message

        # Log based on severity
        if status_code >= 500:
            audit_logger.log_error(
                'application',
                message=message,
                user_id=user_id,
                username=username,
                error_code=error_code
            )

        response = {
            'error': message,
            'error_code': error_code
        }

        if include_details and hasattr(error, '__dict__'):
            response['details'] = {k: v for k, v in error.__dict__.items()
                                 if k not in ['message', 'error_code', 'status_code']}

    # Handle unexpected exceptions
    else:
        status_code = 500
        error_code = 'INTERNAL_ERROR'

        # Log unexpected errors with full details
        audit_logger.log_error(
            'application',
            message=f'Unexpected error: {str(error)}',
            user_id=user_id,
            username=username,
            error_code=error_code,
            error_type=type(error).__name__
        )

        # Don't expose internal error details to users in production
        if include_details:
            message = str(error)
        else:
            message = 'An internal error occurred. Please try again later.'

        response = {
            'error': message,
            'error_code': error_code
        }

    return response, status_code


def create_success_response(
    data: Optional[Dict[str, Any]] = None,
    message: str = 'Operation successful',
    status_code: int = 200
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized success response.

    Args:
        data: Optional data payload
        message: Success message
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (response dict, status code)
    """
    response = {
        'success': True,
        'message': message
    }

    if data is not None:
        response['data'] = data

    return response, status_code


def create_openai_error_response(
    error: Exception,
    user_id: Optional[int] = None,
    username: Optional[str] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response for OpenAI function calling endpoints.

    This follows the OpenAI function calling convention with success, error, and error_code fields.

    Args:
        error: The exception that occurred
        user_id: Optional user ID for logging
        username: Optional username for logging

    Returns:
        Tuple of (response dict, status code)
    """
    # Get standard error response
    error_response, status_code = create_error_response(error, user_id, username, include_details=False)

    # Wrap in OpenAI format
    openai_response = {
        'success': False,
        'error': error_response['error'],
        'error_code': error_response.get('error_code', 'INTERNAL_ERROR')
    }

    return openai_response, status_code


def create_openai_success_response(
    data: Optional[Dict[str, Any]] = None,
    message: str = 'Operation successful',
    status_code: int = 200
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized success response for OpenAI function calling endpoints.

    Args:
        data: Optional data payload
        message: Success message
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (response dict, status code)
    """
    response = {
        'success': True,
        'message': message
    }

    if data is not None:
        response['data'] = data

    return response, status_code
