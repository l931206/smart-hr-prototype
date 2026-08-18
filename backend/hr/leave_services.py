from decimal import Decimal
from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import AuditLog, LeaveBalance, LeaveRequest, LeaveType, McpLeaveDraft, Notification, User
from .serializers import LeaveRequestSerializer


def leave_balance_defaults(employee, leave_type, year):
    """Return yearly entitlement and eligible prior-year carry-over."""
    carried_days = Decimal("0")
    if leave_type.allow_carry_over:
        previous = LeaveBalance.objects.filter(
            employee=employee,
            leave_type=leave_type,
            year=year - 1,
        ).first()
        if previous:
            carried_days = max(previous.remaining_days, Decimal("0"))
    return {"allocated_days": leave_type.default_days, "carried_days": carried_days}


def _serializer_context(user):
    return {"request": SimpleNamespace(user=user)}


def _normalise_payload(validated_data):
    return {
        "leave_type": validated_data["leave_type"].name,
        "start_date": validated_data["start_date"].isoformat(),
        "end_date": validated_data["end_date"].isoformat(),
        "start_time": validated_data.get("start_time", ""),
        "end_time": validated_data.get("end_time", ""),
        "reason": validated_data.get("reason", "").strip(),
        "attachment_name": validated_data.get("attachment_name", ""),
        "attachment_data": validated_data.get("attachment_data", ""),
    }


def validate_leave_payload(user, payload):
    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied("只有員工可以提出請假申請。")
    serializer = LeaveRequestSerializer(data=payload, context=_serializer_context(user))
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    candidate = LeaveRequest(
        employee=user,
        leave_type=values["leave_type"],
        start_date=values["start_date"],
        end_date=values["end_date"],
        start_time=values.get("start_time", ""),
        end_time=values.get("end_time", ""),
        reason=values.get("reason", ""),
    )
    return serializer, candidate


def get_balance_snapshot(user, leave_type, year):
    existing = LeaveBalance.objects.filter(employee=user, leave_type=leave_type, year=year).first()
    if existing:
        allocated = existing.allocated_days
        carried = existing.carried_days
        used = Decimal(str(existing.used_days))
    else:
        defaults = leave_balance_defaults(user, leave_type, year)
        allocated = Decimal(str(defaults["allocated_days"]))
        carried = Decimal(str(defaults["carried_days"]))
        used = sum(
            (item.days for item in user.leave_requests.filter(
                leave_type=leave_type,
                status=LeaveRequest.Status.APPROVED,
                start_date__year=year,
            )),
            Decimal("0"),
        )
    remaining = allocated + carried - used
    return {
        "allocated_days": allocated,
        "carried_days": carried,
        "used_days": used,
        "remaining_days": remaining,
    }


def build_leave_summary(user, serializer, candidate):
    leave_type = serializer.validated_data["leave_type"]
    balance = get_balance_snapshot(user, leave_type, candidate.start_date.year)
    requested_days = Decimal(str(candidate.days))
    if leave_type.deduct_quota and balance["remaining_days"] < requested_days:
        raise ValidationError({"leave_type": "此假別剩餘額度不足，無法送出申請。"})
    remaining_after = balance["remaining_days"] - requested_days if leave_type.deduct_quota else None
    return {
        "employee_name": user.display_name or user.username,
        "department": user.department.name if user.department else None,
        "leave_type": leave_type.name,
        "start_date": candidate.start_date.isoformat(),
        "end_date": candidate.end_date.isoformat(),
        "start_time": candidate.start_time or "全天",
        "end_time": candidate.end_time or "全天",
        "requested_days": str(requested_days),
        "reason": candidate.reason,
        "requires_manager_approval": leave_type.requires_manager_approval,
        "attachment_required": leave_type.attachment_required,
        "attachment_name": serializer.validated_data.get("attachment_name", ""),
        "remaining_before": str(balance["remaining_days"]) if leave_type.deduct_quota else None,
        "remaining_after": str(remaining_after) if remaining_after is not None else None,
    }


def create_mcp_leave_draft(user, payload):
    serializer, candidate = validate_leave_payload(user, payload)
    summary = build_leave_summary(user, serializer, candidate)
    draft = McpLeaveDraft.objects.create(
        employee=user,
        payload=_normalise_payload(serializer.validated_data),
        summary=summary,
        expires_at=timezone.now() + timedelta(seconds=settings.MCP_DRAFT_TTL_SECONDS),
    )
    return draft


def create_leave_request(user, serializer, source="web"):
    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied("只有員工可以提出請假申請。")
    leave_type = serializer.validated_data["leave_type"]
    initial_status = LeaveRequest.Status.PENDING if leave_type.requires_manager_approval else LeaveRequest.Status.APPROVED
    leave_request = serializer.save(
        employee=user,
        status=initial_status,
        reviewed_at=None if initial_status == LeaveRequest.Status.PENDING else timezone.now(),
    )
    AuditLog.objects.create(
        actor=user,
        action="提出請假",
        target_type="LeaveRequest",
        target_id=str(leave_request.pk),
        target_label=str(leave_request),
        details={"source": source},
    )
    department = user.department
    manager = user.manager or (department.employees.filter(role=User.Role.MANAGER).first() if department else None)
    if manager and initial_status == LeaveRequest.Status.PENDING:
        Notification.objects.create(
            recipient=manager,
            title="收到新的請假申請",
            content=f"{user.display_name or user.username} 提出{leave_request.leave_type.name}申請。",
            category="leave",
        )
    return leave_request


@transaction.atomic
def submit_mcp_leave_draft(user, draft_id):
    try:
        draft = McpLeaveDraft.objects.select_for_update().get(id=draft_id, employee=user)
    except (McpLeaveDraft.DoesNotExist, ValueError) as error:
        raise ValidationError({"draft_id": "找不到這筆請假草稿。"}) from error
    if draft.submitted_request_id:
        raise ValidationError({"draft_id": "這筆草稿已經送出，不能重複送出。"})
    if draft.is_expired:
        raise ValidationError({"draft_id": "請假草稿已過期，請重新預覽。"})

    serializer, candidate = validate_leave_payload(user, draft.payload)
    build_leave_summary(user, serializer, candidate)
    leave_request = create_leave_request(user, serializer, source="mcp")
    draft.submitted_request = leave_request
    draft.submitted_at = timezone.now()
    draft.save(update_fields=["submitted_request", "submitted_at"])
    return leave_request


def withdraw_leave_request(user, request_id, source="mcp"):
    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied("只有員工可以撤回請假申請。")
    try:
        leave_request = LeaveRequest.objects.get(pk=request_id, employee=user)
    except LeaveRequest.DoesNotExist as error:
        raise ValidationError({"request_id": "找不到這筆請假申請。"}) from error
    if leave_request.status != LeaveRequest.Status.PENDING:
        raise ValidationError({"request_id": "只有待審核的請假申請可以撤回。"})
    leave_request.status = LeaveRequest.Status.WITHDRAWN
    leave_request.save(update_fields=["status"])
    AuditLog.objects.create(
        actor=user,
        action="撤回請假",
        target_type="LeaveRequest",
        target_id=str(leave_request.pk),
        target_label=str(leave_request),
        details={"source": source},
    )
    return leave_request


def leave_request_result(item):
    return {
        "request_id": item.id,
        "request_number": f"LEAVE-{item.id:06d}",
        "leave_type": item.leave_type.name,
        "start_date": item.start_date.isoformat(),
        "end_date": item.end_date.isoformat(),
        "start_time": item.start_time,
        "end_time": item.end_time,
        "days": str(item.days),
        "reason": item.reason,
        "status": item.status,
        "status_label": item.get_status_display(),
        "attachment_name": item.attachment_name,
        "created_at": item.created_at.isoformat(),
    }
