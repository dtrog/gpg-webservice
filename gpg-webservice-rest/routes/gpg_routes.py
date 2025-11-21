"""
GPG-related routes for cryptographic operations.

DETERMINISTIC SESSION KEYS:
- Authentication supports both deterministic session keys (sk_...) and legacy API keys
- For session keys: Provide X-Username header alongside X-API-KEY
- Session keys are verified by re-deriving the expected key mathematically
- Keys expire hourly with 10-minute grace period
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import tempfile
import os
from functools import wraps
from db.database import db
from models.user import User
from models.pgp_key import PgpKey, PgpKeyType
from services.challenge_service import ChallengeService
from utils.crypto_utils import decrypt_private_key, derive_gpg_passphrase
from utils.security_utils import rate_limit_api, validate_file_upload, secure_temp_directory
from services.auth_service import get_user_by_api_key, authenticate_request
from utils.gpg_file_utils import sign_file, verify_signature_file, encrypt_file, decrypt_file
from utils.audit_logger import audit_logger, AuditEventType

# GPG-related routes
gpg_bp = Blueprint('gpg', __name__)


# --- API Key Auth Decorator ---
def require_api_key(f):
    """
    Authentication decorator supporting both deterministic session keys and legacy API keys.

    For deterministic session keys (sk_...):
        - Requires X-Username header
        - Verifies by re-deriving expected key from user's password_hash and master_salt

    For legacy API keys:
        - Looks up API key hash in database
        - No X-Username header required

    Headers:
        X-API-KEY: The session key (sk_...) or legacy API key (required)
        X-Username: The username (required for session keys, optional for legacy keys)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        raw_api_key = request.headers.get('X-API-KEY')
        username = request.headers.get('X-Username')

        if not raw_api_key:
            audit_logger.log_event(
                AuditEventType.INVALID_API_KEY,
                status='failure',
                message='API key missing from request'
            )
            return jsonify({'error': 'API key required (X-API-KEY header)'}), 401

        # Use unified authentication that handles both session keys and legacy keys
        user, message = authenticate_request(username, raw_api_key)

        if not user:
            audit_logger.log_event(
                AuditEventType.INVALID_API_KEY,
                status='failure',
                message=f'Authentication failed: {message}',
                username=username
            )
            return jsonify({'error': message}), 403

        # Determine authentication method for logging
        auth_method = 'session_key' if raw_api_key.startswith('sk_') else 'legacy_api_key'

        # Log successful authentication
        audit_logger.log_auth_success(
            user_id=user.id,
            username=user.username,
            method=auth_method
        )

        # Pass both user and raw API key to the decorated function
        # The raw API key is needed for GPG passphrase derivation
        return f(user, raw_api_key, *args, **kwargs)
    return decorated

# --- SIGN ---
@gpg_bp.route('/sign', methods=['POST'])
@rate_limit_api
@require_api_key
def sign(user, raw_api_key):
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    file = request.files['file']

    # Validate file upload
    valid, error = validate_file_upload(file, max_size_mb=5)
    if not valid:
        return jsonify({'error': error}), 400

    filename = secure_filename(file.filename or 'file')
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        file.save(input_path)
        # Get encrypted private key
        privkey = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
        if not privkey:
            return jsonify({'error': 'Private key not found'}), 404
        sig_path = os.path.join(tmpdir, filename + '.sig')
        try:
            # Use secure passphrase derivation with user ID as salt and RAW API key
            gpg_passphrase = derive_gpg_passphrase(raw_api_key, user.id)
            sign_file(input_path, privkey.key_data, sig_path, gpg_passphrase)

            # Log successful GPG sign operation
            audit_logger.log_gpg_operation(
                'sign',
                user_id=user.id,
                username=user.username,
                filename=filename,
                file_size=os.path.getsize(input_path)
            )

        except Exception as e:
            # Log GPG operation failure
            audit_logger.log_error(
                'gpg',
                message=f'GPG sign failed for user {user.username}',
                user_id=user.id,
                username=user.username,
                error=str(e)
            )
            return jsonify({'error': f'Signing failed: {str(e)}'}), 500
        return send_file(sig_path, as_attachment=True)

# --- VERIFY ---
@gpg_bp.route('/verify', methods=['POST'])
@rate_limit_api
@require_api_key
def verify(user, raw_api_key):
    if 'file' not in request.files or 'pubkey' not in request.files:
        return jsonify({'error': 'file and pubkey required'}), 400
    sig_file = request.files['file']  # This is the signature file
    pubkey_file = request.files['pubkey']  # This is the public key file
    original_file = request.files.get('original')  # Optional: original file for detached signatures

    # Validate file uploads
    files_to_validate = [(sig_file, 'signature file'), (pubkey_file, 'public key file')]
    if original_file:
        files_to_validate.append((original_file, 'original file'))

    for file_obj, name in files_to_validate:
        valid, error = validate_file_upload(file_obj, max_size_mb=1)
        if not valid:
            return jsonify({'error': f'{name}: {error}'}), 400

    sig_filename = secure_filename(sig_file.filename or 'file.sig')
    pubkey_filename = secure_filename(pubkey_file.filename or 'pubkey')

    with tempfile.TemporaryDirectory() as tmpdir:
        sig_path = os.path.join(tmpdir, sig_filename)
        pubkey_path = os.path.join(tmpdir, pubkey_filename)
        sig_file.save(sig_path)
        pubkey_file.save(pubkey_path)

        # Read public key from file
        with open(pubkey_path, 'r') as f:
            pubkey_data = f.read()

        try:
            # Check if this is a detached signature by reading the file content
            with open(sig_path, 'rb') as f:
                sig_data = f.read()

            # If it's binary data (detached signature), we need the original file
            if sig_data.startswith(b'\x89') or sig_filename.endswith('.sig'):
                # This is a detached signature - we need the original file
                if not original_file:
                    return jsonify({'error': 'Detached signature requires original file (use "original" field)'}), 400

                original_filename = secure_filename(original_file.filename or 'original')
                original_path = os.path.join(tmpdir, original_filename)
                original_file.save(original_path)

                verified = verify_signature_file(original_path, sig_path, pubkey_data)
            else:
                # This is a signed file, verify directly using GPG
                import subprocess
                with tempfile.TemporaryDirectory() as gnupg_home:
                    # Import public key
                    import_pubkey_path = os.path.join(gnupg_home, 'pubkey.asc')
                    with open(import_pubkey_path, 'w') as f:
                        f.write(pubkey_data)
                    import_cmd = ['gpg', '--homedir', gnupg_home, '--import', import_pubkey_path]
                    subprocess.run(import_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    # Verify the signed file
                    verify_cmd = ['gpg', '--homedir', gnupg_home, '--trust-model', 'always', '--verify', sig_path]
                    result = subprocess.run(verify_cmd, capture_output=True)
                    verified = result.returncode == 0

        except Exception as e:
            return jsonify({'error': f'Verification failed: {str(e)}'}), 500
        return jsonify({'verified': verified}), 200

# --- ENCRYPT ---
@gpg_bp.route('/encrypt', methods=['POST'])
@rate_limit_api
@require_api_key
def encrypt(user, raw_api_key):
    if 'file' not in request.files or 'pubkey' not in request.files:
        return jsonify({'error': 'file and pubkey required'}), 400
    file = request.files['file']
    pubkey_file = request.files['pubkey']
    
    # Validate file uploads
    for file_obj, name in [(file, 'data file'), (pubkey_file, 'public key file')]:
        valid, error = validate_file_upload(file_obj, max_size_mb=10)
        if not valid:
            return jsonify({'error': f'{name}: {error}'}), 400
    filename = secure_filename(file.filename or 'file')
    pubkey_filename = secure_filename(pubkey_file.filename or 'pubkey')
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        pubkey_path = os.path.join(tmpdir, pubkey_filename)
        file.save(input_path)
        pubkey_file.save(pubkey_path)
        # Read public key from file
        with open(pubkey_path, 'r') as f:
            pubkey_data = f.read()
        enc_path = os.path.join(tmpdir, filename + '.gpg')
        try:
            encrypt_file(input_path, pubkey_data, enc_path)
        except Exception as e:
            return jsonify({'error': f'Encryption failed: {str(e)}'}), 500
        return send_file(enc_path, as_attachment=True)

# --- DECRYPT ---
@gpg_bp.route('/decrypt', methods=['POST'])
@rate_limit_api
@require_api_key
def decrypt(user, raw_api_key):
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    file = request.files['file']

    # Validate file upload
    valid, error = validate_file_upload(file, max_size_mb=10)
    if not valid:
        return jsonify({'error': error}), 400
    filename = secure_filename(file.filename or 'file')
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        file.save(input_path)
        # Get private key
        privkey = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PRIVATE).first()
        if not privkey:
            return jsonify({'error': 'Private key not found'}), 404
        dec_path = os.path.join(tmpdir, filename + '.dec')
        try:
            # Use secure passphrase derivation with user ID as salt and RAW API key
            gpg_passphrase = derive_gpg_passphrase(raw_api_key, user.id)
            decrypt_file(input_path, privkey.key_data, dec_path, gpg_passphrase)
        except Exception as e:
            return jsonify({'error': f'Decryption failed: {str(e)}'}), 500
        return send_file(dec_path, as_attachment=True)

# --- CHALLENGE ---
@gpg_bp.route('/challenge', methods=['POST'])
@rate_limit_api
@require_api_key
def challenge(user, raw_api_key):
    challenge_service = ChallengeService()
    challenge = challenge_service.create_challenge(user.id)
    return jsonify({'challenge': challenge.challenge_data, 'challenge_id': challenge.id}), 201

# --- VERIFY CHALLENGE ---
@gpg_bp.route('/verify_challenge', methods=['POST'])
@rate_limit_api
@require_api_key
def verify_challenge(user, raw_api_key):
    data = request.get_json()
    challenge_data = data.get('challenge')
    signature = data.get('signature')
    if not challenge_data or not signature:
        return jsonify({'error': 'challenge and signature required'}), 400
    challenge_service = ChallengeService()
    result, message = challenge_service.verify_challenge(user.id, challenge_data, signature)
    if result:
        return jsonify({'message': 'Challenge verified'}), 200
    else:
        return jsonify({'error': message}), 400

# --- GET PUBLIC KEY ---
@gpg_bp.route('/get_public_key', methods=['GET'])
@rate_limit_api
@require_api_key
def get_public_key(user, raw_api_key):
    pubkey = PgpKey.query.filter_by(user_id=user.id, key_type=PgpKeyType.PUBLIC).first()
    if not pubkey:
        return jsonify({'error': 'Public key not found'}), 404
    return jsonify({'public_key': pubkey.key_data}), 200
