from django.contrib.auth import logout
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import status, viewsets
from rest_framework import serializers as drf_serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView

from .models import AuditLog, Announcement, Department, LateNotice, LeaveBalance, LeaveRequest, LeaveType, Notification, ProfileChangeRequest, User
from .leave_services import (
    create_leave_request,
    create_mcp_leave_draft,
    leave_balance_defaults,
    leave_request_result,
    submit_mcp_leave_draft,
    withdraw_leave_request,
)
from .serializers import (
    AnnouncementSerializer,
    AuditLogSerializer,
    DepartmentSerializer,
    LateNoticeSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    LoginSerializer,
    NotificationSerializer,
    ProfileChangeRequestSerializer,
    UserSerializer,
)


def is_admin(user):
    return user.is_staff or user.role == User.Role.ADMIN


def record_audit(request, action, target, details=None, actor_override=None):
    AuditLog.objects.create(
        actor=actor_override or (request.user if request.user.is_authenticated else None),
        action=action,
        target_type=target.__class__.__name__,
        target_id=str(getattr(target, "pk", "") or ""),
        target_label=str(target),
        details=details or {},
        ip_address=request.META.get("REMOTE_ADDR"),
    )


class AdminWriteMixin:
    """所有登入者可讀，只有系統管理者可寫入。"""

    def _require_admin(self, request):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以執行此操作。")

    def create(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        target = serializer.save()
        record_audit(self.request, "新增", target)

    def perform_update(self, serializer):
        target = serializer.save()
        record_audit(self.request, "更新", target)

    def perform_destroy(self, instance):
        record_audit(self.request, "刪除", instance)
        instance.delete()


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="使用人資系統本機帳號登入",
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                name="LoginResponse",
                fields={"token": drf_serializers.CharField(), "user": UserSerializer()},
            )
        },
        auth=[],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        now = timezone.now()
        update_fields = ["last_login"]
        user.last_login = now
        if not user.date_joined:
            user.date_joined = now
            update_fields.append("date_joined")
        user.save(update_fields=update_fields)
        token, _ = Token.objects.get_or_create(user=user)
        record_audit(request, "登入", user, actor_override=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="檢查 API 服務狀態",
        responses={200: inline_serializer(name="HealthResponse", fields={"status": drf_serializers.CharField()})},
        auth=[],
    )
    def get(self, request):
        return Response({"status": "ok"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, summary="登出並撤銷本機 Token", responses={204: OpenApiResponse(description="已登出")})
    def post(self, request):
        record_audit(request, "登出", request.user)
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="取得目前登入者資料", responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(summary="更新目前登入者頭像", request=UserSerializer, responses={200: UserSerializer})
    def put(self, request):
        # 基本資料異動必須走審核流程；頭貼允許本人即時更新。
        user = request.user
        if "avatar_data" in request.data:
            user.avatar_data = request.data["avatar_data"]
            user.save(update_fields=["avatar_data"])
            record_audit(request, "更新頭貼", user)
        return Response(UserSerializer(user).data)


class LeaveAssistantPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="建立對話式請假確認草稿",
        request=LeaveRequestSerializer,
        responses={200: OpenApiResponse(description="請假草稿與確認摘要")},
    )
    def post(self, request):
        draft = create_mcp_leave_draft(request.user, request.data)
        return Response({
            "valid": True,
            "requires_confirmation": True,
            "draft_id": str(draft.id),
            "expires_at": draft.expires_at,
            "summary": draft.summary,
        })


class LeaveAssistantSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="確認並送出對話式請假草稿",
        request=inline_serializer(
            name="LeaveAssistantSubmitRequest",
            fields={"draft_id": drf_serializers.UUIDField()},
        ),
        responses={201: OpenApiResponse(description="已建立請假申請")},
    )
    def post(self, request):
        draft_id = request.data.get("draft_id")
        if not draft_id:
            raise ValidationError({"draft_id": "請提供要送出的請假草稿。"})
        leave_request = submit_mcp_leave_draft(request.user, draft_id, source="assistant")
        return Response({"submitted": True, "request": leave_request_result(leave_request)}, status=status.HTTP_201_CREATED)


class DepartmentViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class EmployeeViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related("department", "manager").all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_staff=False)
        if is_admin(self.request.user):
            return queryset
        if self.request.user.role == User.Role.MANAGER:
            return queryset.filter(department=self.request.user.department)
        return queryset.filter(pk=self.request.user.pk)


class AccountViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related("department", "manager").all()
    serializer_class = UserSerializer

    def get_queryset(self):
        if not is_admin(self.request.user):
            raise PermissionDenied("只有系統管理者可以查看帳號資料。")
        return super().get_queryset()


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.select_related("created_by").all()
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.EMPLOYEE:
            return queryset.filter(is_published=True)
        if self.request.user.role == User.Role.MANAGER:
            return queryset.filter(Q(is_published=True) | Q(created_by=self.request.user)).distinct()
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可發布公告。")
        values = {"created_by": self.request.user}
        if serializer.validated_data.get("is_published"):
            values["published_at"] = timezone.now()
        announcement = serializer.save(**values)
        record_audit(self.request, "發布公告" if announcement.is_published else "建立公告草稿", announcement)
        if announcement.is_published:
            Notification.objects.bulk_create([
                Notification(recipient=employee, title="最新公告", content=announcement.title, category="announcement")
                for employee in User.objects.filter(role__in=[User.Role.EMPLOYEE, User.Role.MANAGER], is_active=True).exclude(pk=self.request.user.pk)
            ])

    def perform_update(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可修改公告。")
        was_published = serializer.instance.is_published
        values = {}
        if serializer.validated_data.get("is_published") and not serializer.instance.published_at:
            values["published_at"] = timezone.now()
        announcement = serializer.save(**values)
        record_audit(self.request, "更新公告", announcement)
        if announcement.is_published and not was_published:
            Notification.objects.bulk_create([
                Notification(recipient=employee, title="公告已發布", content=announcement.title, category="announcement")
                for employee in User.objects.filter(role__in=[User.Role.EMPLOYEE, User.Role.MANAGER], is_active=True).exclude(pk=self.request.user.pk)
            ])

    def destroy(self, request, *args, **kwargs):
        if request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可刪除公告。")
        record_audit(request, "刪除公告", self.get_object())
        return super().destroy(request, *args, **kwargs)


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return super().get_queryset().filter(recipient=self.request.user)

    def perform_update(self, serializer):
        serializer.save(recipient=self.request.user)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE")


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee", "employee__department").all()
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_admin(self.request.user):
            return queryset
        if self.request.user.role == User.Role.MANAGER:
            return queryset.filter(employee__department=self.request.user.department)
        return queryset.filter(employee=self.request.user)

    def perform_create(self, serializer):
        create_leave_request(self.request.user, serializer, source="web")

    def perform_update(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可修改請假審核狀態。")
        status_value = serializer.validated_data.get("status")
        if status_value == LeaveRequest.Status.APPROVED and serializer.instance.status != LeaveRequest.Status.APPROVED:
            leave_type = serializer.instance.leave_type
            if leave_type and leave_type.deduct_quota:
                balance, _ = LeaveBalance.objects.get_or_create(
                    employee=serializer.instance.employee,
                    leave_type=leave_type,
                    year=serializer.instance.start_date.year,
                    defaults={"allocated_days": leave_type.default_days},
                )
                if balance.remaining_days < serializer.instance.days:
                    raise ValidationError({"status": "員工此假別的剩餘額度不足，無法核准。"})
        if status_value in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED}:
            leave_request = serializer.save(reviewed_at=timezone.now())
            Notification.objects.create(
                recipient=leave_request.employee,
                title="請假申請審核結果",
                content=f"您的{leave_request.leave_type.name}申請{leave_request.get_status_display()}。",
                category="leave",
            )
            record_audit(self.request, "核准請假" if status_value == LeaveRequest.Status.APPROVED else "退回請假", leave_request)
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以刪除請假紀錄。")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        leave_request = withdraw_leave_request(request.user, pk, source="web")
        return Response(self.get_serializer(leave_request).data)


class LateNoticeViewSet(viewsets.ModelViewSet):
    queryset = LateNotice.objects.select_related("employee", "employee__department").all()
    serializer_class = LateNoticeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_admin(self.request.user):
            return queryset
        if self.request.user.role == User.Role.MANAGER:
            return queryset.filter(employee__department=self.request.user.department)
        return queryset.filter(employee=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.EMPLOYEE:
            raise PermissionDenied("只有員工可以送出晚到通知。")
        notice = serializer.save(employee=self.request.user, status=LateNotice.Status.NOTIFIED)
        record_audit(self.request, "送出晚到通知", notice)
        department = self.request.user.department
        manager = self.request.user.manager or (department.employees.filter(role=User.Role.MANAGER).first() if department else None)
        if manager:
            Notification.objects.create(
                recipient=manager,
                title="收到新的晚到通知",
                content=f"{self.request.user.display_name or self.request.user.username} 預計 {notice.expected_arrival.strftime('%H:%M')} 到班。",
                category="late",
            )

    def update(self, request, *args, **kwargs):
        if request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可修改已送出的晚到通知。")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可修改已送出的晚到通知。")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以刪除晚到通知。")
        return super().destroy(request, *args, **kwargs)


class LeaveTypeViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

    def perform_create(self, serializer):
        leave_type = serializer.save()
        if leave_type.deduct_quota:
            year = timezone.localdate().year
            for employee in User.objects.filter(role=User.Role.EMPLOYEE, is_active=True):
                LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=year,
                    defaults=leave_balance_defaults(employee, leave_type, year),
                )
        record_audit(self.request, "新增", leave_type)


class LeaveBalanceViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.select_related("employee", "leave_type").all()
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        year = int(self.request.query_params.get("year") or timezone.localdate().year)
        employees = User.objects.filter(role=User.Role.EMPLOYEE, is_active=True)
        if not is_admin(self.request.user):
            if self.request.user.role == User.Role.MANAGER:
                employees = employees.filter(department=self.request.user.department)
            else:
                employees = employees.filter(pk=self.request.user.pk)
        for employee in employees:
            for leave_type in LeaveType.objects.filter(is_active=True, deduct_quota=True):
                LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=year,
                    defaults=leave_balance_defaults(employee, leave_type, year),
                )
        return super().get_queryset().filter(employee__in=employees, year=year)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        if not is_admin(self.request.user):
            raise PermissionDenied("只有系統管理者可以查看操作紀錄。")
        return super().get_queryset()


class ProfileChangeRequestViewSet(viewsets.ModelViewSet):
    queryset = ProfileChangeRequest.objects.select_related("employee", "employee__department").all()
    serializer_class = ProfileChangeRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(employee=self.request.user)

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            raise PermissionDenied("系統管理者不需提出個人資料修改申請。")
        serializer.save(employee=self.request.user, status=ProfileChangeRequest.Status.PENDING)

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        request_item = serializer.save(reviewed_at=timezone.now())
        if request_item.status == ProfileChangeRequest.Status.APPROVED:
            allowed_fields = {"display_name", "email", "phone", "avatar_data"}
            changed_fields = []
            for field, value in request_item.requested_data.items():
                if field in allowed_fields:
                    setattr(request_item.employee, field, value)
                    changed_fields.append(field)
            if changed_fields:
                request_item.employee.save(update_fields=changed_fields)
        if request_item.status != previous_status and request_item.status in {
            ProfileChangeRequest.Status.APPROVED,
            ProfileChangeRequest.Status.REJECTED,
        }:
            Notification.objects.create(
                recipient=request_item.employee,
                title="個人資料修改申請審核結果",
                content=f"您的個人資料修改申請{request_item.get_status_display()}。",
                category="profile",
            )
            record_audit(self.request, "核准資料修改" if request_item.status == ProfileChangeRequest.Status.APPROVED else "退回資料修改", request_item)

    def update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以審核資料修改申請。")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以審核資料修改申請。")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以刪除資料修改申請。")
        return super().destroy(request, *args, **kwargs)
