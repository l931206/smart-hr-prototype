from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, User


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "created_at"]
    search_fields = ["code", "name"]


@admin.register(User)
class HrUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("人資資料", {"fields": ("employee_no", "display_name", "role", "department", "phone", "hire_date")}),
    )
    list_display = ["username", "display_name", "employee_no", "role", "department", "is_active"]
    list_filter = ["role", "department", "is_active"]
    search_fields = ["username", "display_name", "employee_no", "email"]
