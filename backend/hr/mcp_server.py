import asyncio
import time
from typing import Any

from django.conf import settings
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from rest_framework.exceptions import APIException

from .authentication import resolve_central_identity
from .leave_services import (
    create_mcp_leave_draft,
    get_balance_snapshot,
    leave_request_result,
    submit_mcp_leave_draft,
    withdraw_leave_request as withdraw_leave_request_service,
)
from .models import LeaveRequest, LeaveType, User
from .permissions_catalog import permissions_for


class SmartHRCentralTokenVerifier:
    """Validate the same short-lived central Bearer token used by the REST API."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            identity = await asyncio.to_thread(resolve_central_identity, token)
        except APIException:
            return None
        return AccessToken(
            token=token,
            client_id=str(identity.get("client_id") or "smart-hr-central"),
            scopes=[settings.MCP_REQUIRED_SCOPE],
            expires_at=int(time.time()) + settings.MOCK_CENTRAL_TOKEN_MAX_AGE if token.startswith("mock.") else None,
            resource=settings.MCP_PUBLIC_URL,
            subject=identity["external_user_id"],
            claims=identity,
        )


def _current_user():
    access_token = get_access_token()
    if not access_token or not access_token.subject:
        raise ValueError("缺少可辨識使用者的中控 Bearer Token。")
    try:
        return User.objects.select_related("department", "manager").get(
            external_user_id=access_token.subject,
            is_active=True,
        )
    except User.DoesNotExist as error:
        raise ValueError("此中控帳號尚未綁定啟用中的人資帳號。") from error


def _call(action):
    try:
        return action()
    except APIException as error:
        raise ValueError(str(error.detail)) from error


mcp = MCPServer(
    name="smart_hr",
    title="智慧人資管理平台",
    description="提供中控 AI 查詢假別與額度、預覽請假、確認送出、查詢紀錄及撤回申請。",
    instructions=(
        "所有資料都依中控 Bearer Token 對應的使用者權限處理。"
        "呼叫 preview_leave_request 後，必須把摘要與明確日期顯示給使用者；"
        "只有使用者確認後，才可用 draft_id 呼叫 submit_leave_request。"
    ),
    version="1.0.0",
    token_verifier=SmartHRCentralTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(settings.MCP_AUTH_ISSUER_URL),
        resource_server_url=AnyHttpUrl(settings.MCP_PUBLIC_URL),
        required_scopes=[settings.MCP_REQUIRED_SCOPE],
    ),
)


@mcp.tool()
def get_current_user(ctx: Context) -> dict[str, Any]:
    """取得目前中控登入者在人資系統中的身分與可執行權限。"""
    user = _current_user()
    role = User.Role.ADMIN if user.is_staff or user.is_superuser else user.role
    return {
        "system_code": settings.CENTRAL_SYSTEM_CODE,
        "user": {
            "external_user_id": user.external_user_id,
            "employee_no": user.employee_no,
            "name": user.display_name or user.username,
            "role": role,
            "department": user.department.name if user.department else None,
            "manager": user.manager.display_name if user.manager else None,
        },
        "permissions": permissions_for(user),
    }


@mcp.tool()
def list_leave_types(ctx: Context) -> dict[str, Any]:
    """列出目前可申請的假別及其申請單位、附件、額度與簽核規則。"""
    _current_user()
    items = LeaveType.objects.filter(is_active=True).order_by("name")
    return {
        "leave_types": [{
            "code": item.code,
            "name": item.name,
            "minimum_unit": item.minimum_unit,
            "default_days": str(item.default_days),
            "deduct_quota": item.deduct_quota,
            "requires_manager_approval": item.requires_manager_approval,
            "attachment_required": item.attachment_required,
            "attachment_rule": item.attachment_rule,
            "allow_hourly": item.allow_hourly,
            "allow_carry_over": item.allow_carry_over,
        } for item in items]
    }


@mcp.tool()
def get_leave_balance(ctx: Context, year: int | None = None) -> dict[str, Any]:
    """查詢目前員工指定年度的各假別已用與剩餘額度；未指定年度時使用今年。"""
    user = _current_user()
    if user.role != User.Role.EMPLOYEE:
        raise ValueError("只有員工可以查詢自己的請假額度。")
    target_year = year or timezone.localdate().year
    balances = []
    for leave_type in LeaveType.objects.filter(is_active=True, deduct_quota=True).order_by("name"):
        snapshot = get_balance_snapshot(user, leave_type, target_year)
        balances.append({
            "leave_type": leave_type.name,
            "year": target_year,
            **{key: str(value) for key, value in snapshot.items()},
        })
    return {"employee_name": user.display_name or user.username, "balances": balances}


@mcp.tool()
def preview_leave_request(
    ctx: Context,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str,
    start_time: str = "上午",
    end_time: str = "下午",
    attachment_name: str = "",
    attachment_data: str = "",
) -> dict[str, Any]:
    """驗證請假內容並建立 10 分鐘有效的確認草稿；此步驟不會正式送出請假。"""
    user = _current_user()
    payload = {
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
        "reason": reason,
        "attachment_name": attachment_name,
        "attachment_data": attachment_data,
    }
    draft = _call(lambda: create_mcp_leave_draft(user, payload))
    return {
        "valid": True,
        "requires_confirmation": True,
        "draft_id": str(draft.id),
        "expires_at": draft.expires_at.isoformat(),
        "summary": draft.summary,
        "message": "請向使用者顯示完整摘要；取得明確確認後才可正式送出。",
    }


@mcp.tool()
def submit_leave_request(ctx: Context, draft_id: str) -> dict[str, Any]:
    """正式送出已由使用者確認的請假草稿；同一 draft_id 只能成功送出一次。"""
    user = _current_user()
    item = _call(lambda: submit_mcp_leave_draft(user, draft_id))
    return {
        "submitted": True,
        "request": leave_request_result(item),
        "message": "請假申請已正式送出。" if item.status == LeaveRequest.Status.PENDING else "請假申請已依假別規則自動核准。",
    }


@mcp.tool()
def list_my_leave_requests(ctx: Context, limit: int = 10) -> dict[str, Any]:
    """列出目前員工最近的請假申請及審核狀態，最多 50 筆。"""
    user = _current_user()
    if user.role != User.Role.EMPLOYEE:
        raise ValueError("只有員工可以查詢自己的請假紀錄。")
    safe_limit = min(max(limit, 1), 50)
    items = LeaveRequest.objects.select_related("leave_type").filter(employee=user)[:safe_limit]
    return {"requests": [leave_request_result(item) for item in items]}


@mcp.tool()
def withdraw_leave_request(ctx: Context, request_id: int) -> dict[str, Any]:
    """撤回目前員工自己仍在待審核狀態的請假申請。"""
    user = _current_user()
    item = _call(lambda: withdraw_leave_request_service(user, request_id, source="mcp"))
    return {"withdrawn": True, "request": leave_request_result(item), "message": "請假申請已撤回。"}


transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=settings.MCP_ALLOWED_HOSTS,
    allowed_origins=settings.MCP_ALLOWED_ORIGINS,
)

mcp_http_application = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    transport_security=transport_security,
    host="0.0.0.0",
)
