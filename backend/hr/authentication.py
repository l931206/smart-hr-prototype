import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core import signing
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed

from .models import User
from .mock_central import TOKEN_PREFIX, verify_mock_token


class CentralAuthUnavailable(APIException):
    status_code = 503
    default_detail = "中控驗證服務目前無法使用。"
    default_code = "central_auth_unavailable"


def resolve_central_identity(token):
    """Validate a central Bearer token and return its identity claims.

    This function intentionally performs no local user lookup so the same
    verification logic can be reused by DRF and the MCP resource server.
    """
    if settings.ENABLE_MOCK_CENTRAL and token.startswith(TOKEN_PREFIX):
        try:
            identity = verify_mock_token(token)
        except (signing.BadSignature, signing.SignatureExpired) as error:
            raise AuthenticationFailed("模擬中控 Token 無效或已過期。") from error
    else:
        if not settings.CENTRAL_TOKEN_VERIFY_URL:
            raise CentralAuthUnavailable("尚未設定 CENTRAL_TOKEN_VERIFY_URL。")
        payload = json.dumps({settings.CENTRAL_TOKEN_FIELD: token}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if settings.CENTRAL_API_KEY:
            headers["X-API-Key"] = settings.CENTRAL_API_KEY
        central_request = Request(settings.CENTRAL_TOKEN_VERIFY_URL, data=payload, headers=headers, method="POST")
        try:
            with urlopen(central_request, timeout=5) as response:
                identity = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {400, 401, 403}:
                raise AuthenticationFailed("中控 Token 無效或已過期。") from error
            raise CentralAuthUnavailable() from error
        except (URLError, TimeoutError, ValueError) as error:
            raise CentralAuthUnavailable() from error

    if not identity.get("active"):
        raise AuthenticationFailed("中控 Token 無效或已過期。")
    external_user_id = identity.get("external_user_id") or identity.get("user_id") or identity.get("sub")
    if not external_user_id:
        raise AuthenticationFailed("中控回應缺少使用者識別碼。")
    identity["external_user_id"] = str(external_user_id)
    return identity


class CentralTokenAuthentication(BaseAuthentication):
    """Validate a Bearer token through a configurable central introspection API.

    The central response must contain active=true and one stable identity field:
    external_user_id, user_id, or sub. Users must be mapped in advance; this
    adapter deliberately does not auto-create HR employee records.
    """

    keyword = b"Bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword.lower():
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Bearer Token 格式錯誤。")
        try:
            token = parts[1].decode("utf-8")
        except UnicodeError as error:
            raise AuthenticationFailed("Token 編碼錯誤。") from error

        identity = resolve_central_identity(token)
        external_user_id = identity["external_user_id"]
        try:
            user = User.objects.get(external_user_id=str(external_user_id), is_active=True)
        except User.DoesNotExist as error:
            raise AuthenticationFailed("此中控帳號尚未綁定人資帳號。") from error

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return user, {"source": "central", "identity": identity}

    def authenticate_header(self, request):
        return "Bearer"
