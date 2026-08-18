import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_application = get_asgi_application()

from hr.mcp_server import mcp_http_application  # noqa: E402


class SmartHRASGIApplication:
    """Route MCP protocol traffic and ordinary Django HTTP through one service."""

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if (
            scope["type"] == "lifespan"
            or path == "/mcp"
            or path.startswith("/.well-known/oauth-protected-resource")
        ):
            await mcp_http_application(scope, receive, send)
            return
        await django_application(scope, receive, send)


application = SmartHRASGIApplication()
