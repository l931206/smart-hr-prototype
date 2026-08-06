from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Department, User


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(source="employees.count", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "code", "name", "is_active", "employee_count", "created_at"]
        read_only_fields = ["id", "employee_count", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "employee_no", "display_name", "email", "role",
            "role_label", "department", "department_name", "phone", "hire_date",
            "is_active",
        ]
        read_only_fields = ["id", "role_label", "department_name"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("帳號或密碼不正確。")
        attrs["user"] = user
        return attrs
