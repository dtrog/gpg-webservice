from .user import User
from .challenge import Challenge
from .pgp_key import PgpKey, PrivatePgpKey, PublicPgpKey
from typing import NamedTuple, Optional

class PgpKeyPair(NamedTuple):
    """Named tuple for holding a public/private key pair."""
    public_key: Optional[PublicPgpKey]
    private_key: Optional[PrivatePgpKey]

__all__ = ['User', 'Challenge', 'PgpKey', 'PublicPgpKey', 'PrivatePgpKey', 'PgpKeyPair']
