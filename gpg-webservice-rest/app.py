"""
GPG Webservice REST API Application Entry Point.
Sets up the Flask app, configuration, CORS, database,
and registers blueprints for various routes."""

import os
import logging
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS
from config import get_config
from db.database import init_db
from routes.user_routes import user_bp
from routes.gpg_routes import gpg_bp
from routes.openai_routes import openai_bp, get_function_definitions
from routes.admin_routes import admin_bp
from routes.admin_auth_routes import admin_auth_bp
from utils.security_utils import add_security_headers


# Load environment variables from .env file
load_dotenv()

# Load configuration
app = Flask(__name__)
config_class = get_config()
app.config.from_object(config_class)

# Initialize CORS
# Allow all origins for flexibility (restricted in production via env var)
allowed_origins = os.environ.get('CORS_ORIGINS', '*')
if allowed_origins == '*':
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type",
                "X-API-KEY",
                "X-Username",
                "X-Admin-Token"
            ],
            "expose_headers": ["Content-Disposition"]
        }
    })
else:
    origins_list = [origin.strip() for origin in allowed_origins.split(',')]
    CORS(app, resources={
        r"/*": {
            "origins": origins_list,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type",
                "X-API-KEY",
                "X-Username",
                "X-Admin-Token"
            ],
            "expose_headers": ["Content-Disposition"]
        }
    })

# Initialize database
init_db(app)

logging.basicConfig(
    level=getattr(logging, config_class.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.info(
    "GPG Webservice starting (env: %s)",
    os.environ.get("FLASK_ENV", "development")
)
# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(gpg_bp)
app.register_blueprint(openai_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_auth_bp)


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
    # Support optional TLS using environment variables `TLS_CERT` and `TLS_KEY`.
    # Skip TLS on Render.com (they handle TLS at the edge) or when certs don't exist.
    tls_cert = os.environ.get("TLS_CERT")
    tls_key = os.environ.get("TLS_KEY")
    is_render = os.environ.get("RENDER") is not None

    if tls_cert and tls_key and not is_render \
        and os.path.exists(tls_cert) and os.path.exists(tls_key):
        # Run Flask development server with SSL context for local testing.
        logging.info("Starting Flask with TLS (local development)")
        app.run(host=config_class.HOST, port=config_class.PORT, 
                ssl_context=(tls_cert, tls_key))
    else:
        if is_render:
            logging.info("Running on Render.com - TLS handled at edge, starting HTTP server")
        app.run(host=config_class.HOST, port=config_class.PORT)
