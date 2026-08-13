from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import AuditLog, Announcement, Department, LateNotice, LeaveBalance, LeaveRequest, LeaveType, Notification, ProfileChangeRequest, User


def validate_attachment_payload(name, data):
    if not data:
        return
    if not name:
        raise serializers.ValidationError({"attachment_name": "附件缺少檔名。"})
    allowed_prefixes = ("data:application/pdf;base64,", "data:image/jpeg;base64,", "data:image/png;base64,")
    if not data.startswith(allowed_prefixes):
        raise serializers.ValidationError({"attachment_data": "附件只支援 PDF、JPG 或 PNG。"})
    if len(data) > 2_800_000:
        raise serializers.ValidationError({"attachment_data": "附件大小不可超過 2 MB。"})


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "content", "category", "is_read", "created_at"]
        read_only_fields = ["id", "title", "content", "category", "created_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    author_name = serializers.CharField(source="created_by.display_name", read_only=True)

    class Meta:
        model = Announcement
        fields = ["id", "title", "content", "category", "category_label", "is_published", "author_name", "attachment_name", "attachment_data", "created_at", "published_at"]
        read_only_fields = ["id", "category_label", "author_name", "created_at", "published_at"]

    def validate(self, attrs):
        validate_attachment_payload(
            attrs.get("attachment_name", getattr(self.instance, "attachment_name", "")),
            attrs.get("attachment_data", getattr(self.instance, "attachment_data", "")),
        )
        return attrs


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "code", "name", "is_active", "employee_count", "created_at"]
        read_only_fields = ["id", "employee_count", "created_at"]

    def get_employee_count(self, department) -> int:
        return department.employees.filter(role=User.Role.EMPLOYEE, is_active=True).count()


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    manager_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "employee_no", "external_user_id", "display_name", "job_title", "email", "role",
            "role_label", "department", "department_name", "manager", "manager_name", "phone", "hire_date", "termination_date", "termination_reason", "avatar_data",
            "work_start_time", "work_end_time", "is_active", "last_login", "date_joined", "password",
        ]
        read_only_fields = ["id", "role_label", "department_name", "last_login", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def get_manager_name(self, user) -> str:
        manager = user.manager
        if not manager and user.department_id:
            manager = user.department.employees.filter(role=User.Role.MANAGER, is_active=True).first()
        return (manager.display_name or manager.username) if manager else ""

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if validated_data.get("is_active") is True:
            validated_data["termination_date"] = None
            validated_data["termination_reason"] = ""
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("帳號或密碼不正確。")
        attrs["user"] = user
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_no = serializers.CharField(source="employee.employee_no", read_only=True)
    employee_department = serializers.CharField(source="employee.department.name", read_only=True)
    employee_job_title = serializers.CharField(source="employee.job_title", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "employee_no", "employee_department", "employee_job_title", "leave_type",
            "start_date", "end_date", "start_time", "end_time", "days", "reason",
            "status", "status_label", "reviewer_comment", "attachment_name", "attachment_data", "created_at", "reviewed_at",
        ]
        read_only_fields = [
            "id", "employee", "employee_name", "employee_no", "employee_department", "employee_job_title", "days", "status_label",
            "created_at", "reviewed_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("結束日期不能早於開始日期。")
        attachment_data = attrs.get("attachment_data", getattr(self.instance, "attachment_data", ""))
        attachment_name = attrs.get("attachment_name", getattr(self.instance, "attachment_name", ""))
        leave_type_name = attrs.get("leave_type", getattr(self.instance, "leave_type", ""))
        leave_type = LeaveType.objects.filter(name=leave_type_name, is_active=True).first()
        if leave_type and leave_type.attachment_required and not attachment_data:
            raise serializers.ValidationError({"attachment_data": "此假別要求上傳附件。"})
        validate_attachment_payload(attachment_name, attachment_data)
        return attrs


class LateNoticeSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_department = serializers.CharField(source="employee.department.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LateNotice
        fields = ["id", "employee", "employee_name", "employee_department", "date", "expected_arrival", "reason_type", "reason", "status", "status_label", "created_at"]
        read_only_fields = ["id", "employee", "employee_name", "employee_department", "status_label", "created_at"]


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id", "code", "name", "default_days", "quota_type", "minimum_unit", "is_paid",
            "deduct_quota", "requires_manager_approval", "attachment_required", "allow_hourly",
            "allow_carry_over", "attachment_rule", "is_active", "description", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProfileChangeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_no = serializers.CharField(source="employee.employee_no", read_only=True)
    employee_department = serializers.CharField(source="employee.department.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ProfileChangeRequest
        fields = ["id", "employee", "employee_name", "employee_no", "employee_department", "requested_data", "status", "status_label", "reviewer_comment", "created_at", "reviewed_at"]
        read_only_fields = ["id", "employee", "employee_name", "employee_no", "employee_department", "status_label", "created_at", "reviewed_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    used_days = serializers.DecimalField(max_digits=6, decimal_places=1, read_only=True)
    remaining_days = serializers.DecimalField(max_digits=6, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "employee", "employee_name", "leave_type", "leave_type_name", "year", "allocated_days", "carried_days", "used_days", "remaining_days"]
        read_only_fields = ["id", "employee_name", "leave_type_name", "used_days", "remaining_days"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "actor_name", "action", "target_type", "target_id", "target_label", "details", "ip_address", "created_at"]
        read_only_fields = fields

    def get_actor_name(self, item) -> str:
        return (item.actor.display_name or item.actor.username) if item.actor else "系統"
