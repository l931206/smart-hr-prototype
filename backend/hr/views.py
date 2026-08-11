from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Announcement, Department, LateNotice, LeaveRequest, LeaveType, Notification, ProfileChangeRequest, User
from .serializers import (
    AnnouncementSerializer,
    DepartmentSerializer,
    LateNoticeSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    LoginSerializer,
    NotificationSerializer,
    ProfileChangeRequestSerializer,
    UserSerializer,
)


def is_admin(user):
    return user.is_staff or user.role == User.Role.ADMIN


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


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        # 基本資料異動必須走審核流程；頭貼允許本人即時更新。
        user = request.user
        if "avatar_data" in request.data:
            user.avatar_data = request.data["avatar_data"]
            user.save(update_fields=["avatar_data"])
        return Response(UserSerializer(user).data)


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


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.select_related("created_by").all()
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.EMPLOYEE:
            return queryset.filter(is_published=True)
        if self.request.user.role == User.Role.MANAGER:
            return queryset.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可發布公告。")
        values = {"created_by": self.request.user}
        if serializer.validated_data.get("is_published"):
            values["published_at"] = timezone.now()
        announcement = serializer.save(**values)
        if announcement.is_published:
            Notification.objects.bulk_create([
                Notification(recipient=employee, title="最新公告", content=announcement.title, category="announcement")
                for employee in User.objects.filter(role=User.Role.EMPLOYEE, is_active=True)
            ])

    def perform_update(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可修改公告。")
        was_published = serializer.instance.is_published
        values = {}
        if serializer.validated_data.get("is_published") and not serializer.instance.published_at:
            values["published_at"] = timezone.now()
        announcement = serializer.save(**values)
        if announcement.is_published and not was_published:
            Notification.objects.bulk_create([
                Notification(recipient=employee, title="公告已發布", content=announcement.title, category="announcement")
                for employee in User.objects.filter(role=User.Role.EMPLOYEE, is_active=True)
            ])

    def destroy(self, request, *args, **kwargs):
        if request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可刪除公告。")
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
        if self.request.user.role != User.Role.EMPLOYEE:
            raise PermissionDenied("只有員工可以提出請假申請。")
        leave_request = serializer.save(employee=self.request.user, status=LeaveRequest.Status.PENDING)
        department = self.request.user.department
        manager = self.request.user.manager or (department.employees.filter(role=User.Role.MANAGER).first() if department else None)
        if manager:
            Notification.objects.create(
                recipient=manager,
                title="收到新的請假申請",
                content=f"{self.request.user.display_name or self.request.user.username} 提出{leave_request.leave_type}申請。",
                category="leave",
            )

    def perform_update(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            raise PermissionDenied("員工不可修改請假審核狀態。")
        status_value = serializer.validated_data.get("status")
        if status_value in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED}:
            leave_request = serializer.save(reviewed_at=timezone.now())
            Notification.objects.create(
                recipient=leave_request.employee,
                title="請假申請審核結果",
                content=f"您的{leave_request.leave_type}申請{leave_request.get_status_display()}。",
                category="leave",
            )
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("只有系統管理者可以刪除請假紀錄。")
        return super().destroy(request, *args, **kwargs)


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
