from django.conf import settings
from django.core import signing


TOKEN_PREFIX = "mock."
TOKEN_SALT = "smart-hr.mock-central.v1"


def issue_mock_token(user):
    identity = {
        "active": True,
        "external_user_id": user.external_user_id,
        "username": user.username,
        "name": user.display_name or user.username,
        "role": user.role,
        "systems": [settings.CENTRAL_SYSTEM_CODE],
    }
    return TOKEN_PREFIX + signing.dumps(identity, salt=TOKEN_SALT, compress=True)


def verify_mock_token(token):
    if not token.startswith(TOKEN_PREFIX):
        raise signing.BadSignature("Invalid mock token prefix")
    identity = signing.loads(
        token[len(TOKEN_PREFIX):],
        salt=TOKEN_SALT,
        max_age=settings.MOCK_CENTRAL_TOKEN_MAX_AGE,
    )
    if settings.CENTRAL_SYSTEM_CODE not in identity.get("systems", []):
        raise signing.BadSignature("Token is not valid for Smart HR")
    return identity
