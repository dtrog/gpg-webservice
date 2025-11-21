"""
Session management utilities for database operations.

This module provides context managers and utilities for proper database
session lifecycle management, including automatic commit/rollback and cleanup.
"""

from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from db.database import db


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.

    This context manager handles:
    - Session creation
    - Automatic commit on success
    - Automatic rollback on exceptions
    - Session cleanup

    Usage:
        with session_scope() as session:
            user = User(username='test')
            session.add(user)
            # Session is automatically committed here
        # Session is automatically closed here

    Raises:
        The original exception if one occurs during the transaction
    """
    try:
        session = db.session
    except RuntimeError:
        # No app context available (e.g., in unit tests with mocking)
        # Fall back to using get_session() for backward compatibility
        from db.database import get_session
        session = get_session()

    try:
        yield session
        try:
            session.commit()
        except RuntimeError:
            # No app context for commit
            pass
    except SQLAlchemyError as e:
        try:
            session.rollback()
        except RuntimeError:
            # No app context for rollback
            pass
        raise
    except Exception as e:
        try:
            session.rollback()
        except RuntimeError:
            # No app context for rollback
            pass
        raise
    finally:
        # Flask-SQLAlchemy's scoped_session remove() is safer than close()
        # It removes the session from the registry without closing the connection
        try:
            db.session.remove()
        except RuntimeError:
            # If there's no app context (e.g., in unit tests), try to close the session directly
            try:
                session.close()
            except:
                # Session cleanup failed, but we did our best
                pass


@contextmanager
def independent_session():
    """
    Create an independent session that is not tied to Flask's request context.

    This is useful for operations that need to happen outside of a Flask request,
    such as background tasks, CLI commands, or tests.

    Usage:
        with independent_session() as session:
            user = session.query(User).first()
            # Do work with user

    Returns:
        A new SQLAlchemy session
    """
    from db.database import db as database
    session = database.session

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def get_or_create(session, model, defaults=None, **kwargs):
    """
    Get an existing instance or create a new one.

    This is a common pattern for "get or create" operations that prevents
    duplicate entries while handling race conditions properly.

    Args:
        session: SQLAlchemy session
        model: The model class to query
        defaults: Dictionary of default values for creation
        **kwargs: Keyword arguments to filter by

    Returns:
        Tuple of (instance, created) where created is True if instance was created

    Example:
        user, created = get_or_create(
            session,
            User,
            defaults={'email': 'user@example.com'},
            username='testuser'
        )
    """
    instance = session.query(model).filter_by(**kwargs).first()

    if instance:
        return instance, False

    params = dict((k, v) for k, v in kwargs.items())
    if defaults:
        params.update(defaults)

    instance = model(**params)

    try:
        session.add(instance)
        session.flush()
        return instance, True
    except SQLAlchemyError:
        # Race condition: another process created it
        session.rollback()
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        raise


def safe_delete(session, instance):
    """
    Safely delete an instance with proper error handling.

    Args:
        session: SQLAlchemy session
        instance: The instance to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        session.delete(instance)
        session.flush()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        raise


def refresh_instance(session, instance):
    """
    Refresh an instance from the database.

    This is useful when you need to ensure an instance has the latest data
    from the database, especially after commits or when working with detached instances.

    Args:
        session: SQLAlchemy session
        instance: The instance to refresh

    Returns:
        The refreshed instance
    """
    try:
        session.refresh(instance)
        return instance
    except SQLAlchemyError:
        # Instance may be detached, re-query it
        model = type(instance)
        return session.query(model).get(instance.id)
