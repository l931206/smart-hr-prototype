from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Announcement, Department, LateNotice, LeaveRequest, Notification, User


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
        fields = ["id", "title", "content", "category", "category_label", "is_published", "author_name", "created_at", "published_at"]
        read_only_fields = ["id", "category_label", "author_name", "created_at", "published_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "code", "name", "is_active", "employee_count", "created_at"]
        read_only_fields = ["id", "employee_count", "created_at"]

    def get_employee_count(self, department):
        return department.employees.filter(role=User.Role.EMPLOYEE, is_active=True).count()


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    manager_name = serializers.CharField(source="manager.display_name", read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "employee_no", "display_name", "email", "role",
            "role_label", "department", "department_name", "manager", "manager_name", "phone", "hire_date", "avatar_data",
            "is_active", "password",
        ]
        read_only_fields = ["id", "role_label", "department_name"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
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
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "employee_no", "employee_department", "leave_type",
            "start_date", "end_date", "start_time", "end_time", "days", "reason",
            "status", "status_label", "reviewer_comment", "created_at", "reviewed_at",
        ]
        read_only_fields = [
            "id", "employee", "employee_name", "employee_no", "days", "status_label",
            "created_at", "reviewed_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("結束日期不能早於開始日期。")
        return attrs


class LateNoticeSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_department = serializers.CharField(source="employee.department.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LateNotice
        fields = ["id", "employee", "employee_name", "employee_department", "date", "expected_arrival", "reason_type", "reason", "status", "status_label", "created_at"]
        read_only_fields = ["id", "employee", "employee_name", "employee_department", "status_label", "created_at"]
