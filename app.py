import os
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from db.database import db, init_db
from models.user import User
from models.pgp_key import PgpKey
from models.challenge import Challenge
from services.auth_service import hash_password, verify_password, get_user_by_api_key
from utils.crypto_utils import encrypt_private_key, decrypt_private_key, generate_api_key
from utils.gpg_utils import generate_gpg_keypair
import base64

from routes.user_routes import user_bp
from routes.gpg_routes import gpg_bp
from routes.openai_routes import openai_bp
from utils.security_utils import add_security_headers

app = Flask(__name__)
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/gpg_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gpg_users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_db(app)

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(gpg_bp)
app.register_blueprint(openai_bp)

# Add security headers to all responses
@app.after_request
def after_request(response):
    return add_security_headers(response)

# This block allows the app to be run directly for development purposes
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
