import os
from flask import Flask, request, send_from_directory
from config import get_config
from db.database import db, init_db
from models.user import User
from models.pgp_key import PgpKey
from models.challenge import Challenge
from utils.crypto_utils import encrypt_private_key, decrypt_private_key
from utils.gpg_utils import generate_gpg_keypair

from routes.user_routes import user_bp
from routes.gpg_routes import gpg_bp
from routes.openai_routes import openai_bp, get_function_definitions
from utils.security_utils import add_security_headers

# Load configuration
app = Flask(__name__)
config_class = get_config()
app.config.from_object(config_class)

# Initialize database
init_db(app)

# Log application startup
import logging

logging.basicConfig(
    level=getattr(logging, config_class.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.info(
    f"GPG Webservice starting (env: {os.environ.get('FLASK_ENV', 'development')})"
)

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(gpg_bp)
app.register_blueprint(openai_bp)


# Serve the index page at root
@app.route("/")
def index():
    return send_from_directory(os.path.join(app.root_path, "static"), "index.html")


# Serve a root favicon.ico from the existing `favicon/` folder so browsers
# can fetch `/favicon.ico` directly (many browsers expect it at site root).
@app.route("/favicon.ico")
def favicon_route():
    # Send the favicon file located in the repo's `favicon/` directory
    return send_from_directory(os.path.join(app.root_path, "favicon"), "favicon.ico")


# Expose a static openai.json at the site root so clients can fetch it from
# `/openai.json` (useful for hosting a client-side copy of function definitions).
@app.route("/openai.json")
def openai_json():
    # Return dynamic function definitions so base_url reflects the request host
    # by delegating to the existing implementation in routes.openai_routes.
    return get_function_definitions()


# Serve files from the repo's `favicon/` directory under `/static/favicons/`
# so consumers can reference `/static/favicons/<name>` without copying binaries.
@app.route("/static/favicons/<path:filename>")
def static_favicons(filename):
    return send_from_directory(os.path.join(app.root_path, "favicon"), filename)


# Serve a small Swagger UI page that loads `/swagger.json` so you can view
# the minimal OpenAPI spec in a browser at `/swagger-ui`.
@app.route("/swagger-ui")
def swagger_ui():
    return send_from_directory(os.path.join(app.root_path, "static"), "swagger_ui.html")


# Simple disclaimer page served from static/disclaimer.html at `/disclaimer`.
@app.route("/disclaimer")
def disclaimer():
    return send_from_directory(os.path.join(app.root_path, "static"), "disclaimer.html")


# Serve a minimal swagger/openapi JSON file at `/swagger.json` so it can be
# loaded by Swagger UI or other tools.
@app.route("/swagger.json")
def swagger_json():
    return send_from_directory(os.path.join(app.root_path, "static"), "swagger.json")


# Add security headers to all responses
@app.after_request
def after_request(response):
    return add_security_headers(response)


# This block allows the app to be run directly for development purposes
if __name__ == "__main__":
    app.run(host=config_class.HOST, port=config_class.PORT)
