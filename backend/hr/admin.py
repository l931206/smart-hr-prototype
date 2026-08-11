from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Department, LeaveBalance, LeaveRequest, LeaveType, User


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "created_at"]
    search_fields = ["code", "name"]


@admin.register(User)
class HrUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("人資資料", {"fields": ("employee_no", "display_name", "job_title", "role", "department", "phone", "hire_date", "work_start_time", "work_end_time")}),
    )
    list_display = ["username", "display_name", "employee_no", "role", "department", "is_active"]
    list_filter = ["role", "department", "is_active"]
    search_fields = ["username", "display_name", "employee_no", "email"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "status", "created_at"]
    list_filter = ["status", "leave_type"]
    search_fields = ["employee__display_name", "employee__employee_no", "reason"]


admin.site.register(LeaveType)
admin.site.register(LeaveBalance)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "target_type", "target_label"]
    list_filter = ["action", "target_type"]
    search_fields = ["actor__username", "actor__display_name", "target_label"]
    readonly_fields = ["actor", "action", "target_type", "target_id", "target_label", "details", "ip_address", "created_at"]
