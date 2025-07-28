"""Database package for GPG webservice."""

import sqlite3
import os
from flask import current_app, g


def get_db():
    """Get database connection for current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database with schema."""
    db = get_db()
    
    # Create users table
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            public_key TEXT NOT NULL,
            encrypted_private_key TEXT NOT NULL,
            salt BLOB NOT NULL,
            nonce BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create api_keys table
    db.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    db.commit()


def init_app(app):
    """Initialize database with Flask app."""
    app.teardown_appcontext(close_db)
    
    # Create database file if it doesn't exist
    if not os.path.exists(app.config['DATABASE']):
        os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
        with app.app_context():
            init_db()


# Export commonly used functions
__all__ = ['get_db', 'close_db', 'init_db', 'init_app']
