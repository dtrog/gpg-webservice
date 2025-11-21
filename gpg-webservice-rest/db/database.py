# --- Flask-SQLAlchemy ORM helpers ---
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
# --- Flask app initialization ---
def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
# --- Flask app context management ---
def get_session():
    """Get a new session from the database."""
    return db.session
# --- Flask app configuration ---
