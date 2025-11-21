# Challenge service for challenge/response logic

from models.challenge import Challenge
from models.pgp_key import PgpKeyType
from db.database import get_session
from db.session_manager import session_scope
from datetime import datetime, timedelta, timezone
from sqlalchemy import asc, desc
from config import Config
import secrets

class ChallengeService:
    """
    Service for managing challenges and responses.
    Handles challenge creation, verification, and pruning of old challenges.
    """
    # Constants for challenge limits (loaded from config)
    MAX_CHALLENGES_PER_USER = Config.CHALLENGE_MAX_PER_USER
    MAX_AGE_DAYS = Config.CHALLENGE_MAX_AGE_DAYS

    def prune_old_challenges(self, session, user_id):
        """
        Prune old challenges for a user.
        Removes challenges older than MAX_AGE_DAYS and ensures the number of challenges does not exceed MAX_CHALLENGES_PER_USER.
        """
        # Remove challenges older than MAX_AGE_DAYS
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.MAX_AGE_DAYS)
        session.query(Challenge).filter(getattr(Challenge, 'user_id') == user_id).filter(getattr(Challenge, 'created_at') < cutoff).delete()
        # Remove oldest if more than MAX_CHALLENGES_PER_USER
        challenges = session.query(Challenge).filter_by(user_id=user_id).order_by(Challenge.created_at).all()
        if len(challenges) > self.MAX_CHALLENGES_PER_USER:
            for c in challenges[:len(challenges) - self.MAX_CHALLENGES_PER_USER]:
                session.delete(c)
            session.commit()

    def create_challenge(self, user_id):
        """
        Create a new challenge for a user.
        Ensures old challenges are pruned before creating a new one.
        """
        with session_scope() as session:
            self.prune_old_challenges(session, user_id)
            challenge_data = secrets.token_urlsafe(32)
            challenge = Challenge()
            challenge.challenge_data = challenge_data
            challenge.signature = None
            challenge.user_id = user_id
            session.add(challenge)
            session.flush()  # Flush to get challenge.id

            # Expunge challenge to detach it before session closes
            session.expunge(challenge)

            # Context manager commits here

        return challenge

    def verify_challenge(self, user_id, challenge_data, signature):
        """
        Verify a challenge response.
        Checks if the challenge exists, is not expired, and verifies the signature.
        """
        with session_scope() as session:
            # Find the challenge
            challenge = session.query(Challenge).filter_by(user_id=user_id, challenge_data=challenge_data).first()
            if not challenge:
                return False, 'Challenge not found or expired'

            # Check if challenge is expired
            # Ensure challenge.created_at is timezone-aware
            created_at = challenge.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            if (datetime.now(timezone.utc) - created_at).total_seconds() > timedelta(days=self.MAX_AGE_DAYS).total_seconds():
                return False, 'Challenge expired'

            if not signature:
                return False, 'Signature required'

            # Fetch user's public key
            user = challenge.user
            if user is None:
                return False, 'User not found'

            public_key_obj = None
            # Get iterable of PGP keys; handle both list-based and query-like interfaces
            keys = user.pgp_keys
            try:
                iterable = keys.all()
            except AttributeError:
                iterable = keys

            for key in iterable:
                if key.key_type == PgpKeyType.PUBLIC:
                    public_key_obj = key
                    break

            if not public_key_obj:
                return False, 'User public key not found'

            from utils.gpg_utils import verify_signature
            is_valid = verify_signature(challenge_data, signature, public_key_obj.key_data)

            # Mark challenge as used (delete it)
            session.delete(challenge)
            # Context manager commits here

        if is_valid:
            return True, 'Challenge verified'
        else:
            return False, 'Invalid signature'
