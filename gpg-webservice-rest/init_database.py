#!/usr/bin/env python3
"""
Initialize the GPG Webservice database.

This script creates all database tables without starting the web server.
Useful for development and testing.

Note: The database is automatically initialized when importing app,
so this script just ensures tables are created.
"""

from app import app
from db.database import db

if __name__ == '__main__':
    print("Initializing GPG Webservice database...")

    # The database is already initialized by app.py when imported
    # We just need to create the tables if they don't exist
    with app.app_context():
        db.create_all()

    print("Database initialized successfully!")
    print(f"Database location: {app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///gpg_users.db')}")
