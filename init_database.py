#!/usr/bin/env python3
"""
Initialize the GPG Webservice database.

This script creates all database tables without starting the web server.
Useful for development and testing.
"""

from app import app
from db.database import init_db

if __name__ == '__main__':
    print("Initializing GPG Webservice database...")
    init_db(app)
    print("Database initialized successfully!")
    print(f"Database location: {app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///gpg_users.db')}")
