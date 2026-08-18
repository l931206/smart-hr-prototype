from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime, timedelta
import uuid


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code}｜{self.name}"


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "員工"
        MANAGER = "manager", "主管"
        ADMIN = "admin", "系統管理者"

    employee_no = models.CharField(max_length=30, unique=True, null=True, blank=True)
    external_user_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    manager = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="direct_reports", limit_choices_to={"role": "manager"},
    )
    phone = models.CharField(max_length=30, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)
    avatar_data = models.TextField(blank=True)
    work_start_time = models.TimeField(default="09:00")
    work_end_time = models.TimeField(default="18:00")

    def __str__(self):
        return self.display_name or self.get_full_name() or self.username


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待審核"
        APPROVED = "approved", "已核准"
        REJECTED = "rejected", "已退回"
        WITHDRAWN = "withdrawn", "已撤回"

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey("LeaveType", on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.CharField(max_length=20, blank=True)
    end_time = models.CharField(max_length=20, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer_comment = models.TextField(blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_data = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def days(self):
        start_date = date.fromisoformat(self.start_date) if isinstance(self.start_date, str) else self.start_date
        end_date = date.fromisoformat(self.end_date) if isinstance(self.end_date, str) else self.end_date
        day = start_date
        business_days = 0
        while day <= end_date:
            if day.weekday() < 5:
                business_days += 1
            day += timedelta(days=1)
        if not business_days:
            return Decimal("0")

        time_pattern = "%H:%M"
        if start_date == end_date and ":" in self.start_time and ":" in self.end_time:
            try:
                start = datetime.strptime(self.start_time, time_pattern)
                end = datetime.strptime(self.end_time, time_pattern)
                hours = Decimal(str(max((end - start).total_seconds() / 3600, 0)))
                return (hours / Decimal("8")).quantize(Decimal("0.125"))
            except ValueError:
                pass

        result = Decimal(business_days)
        if self.start_time == "下午":
            result -= Decimal("0.5")
        if self.end_time == "上午":
            result -= Decimal("0.5")
        return max(result, Decimal("0"))


class McpLeaveDraft(models.Model):
    """Short-lived, single-use leave draft created by an MCP preview tool."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mcp_leave_drafts")
    payload = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)
    expires_at = models.DateTimeField()
    submitted_request = models.OneToOneField(
        LeaveRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mcp_draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class Announcement(models.Model):
    class Category(models.TextChoices):
        COMPANY = "company", "公司公告"
        SYSTEM = "system", "系統公告"
        HR = "hr", "人事公告"
        ADMIN = "admin", "行政公告"

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.COMPANY)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="announcements")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_data = models.TextField(blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=30, default="system")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LateNotice(models.Model):
    class Status(models.TextChoices):
        NOTIFIED = "notified", "已通知主管"
        ARRIVED = "arrived", "已到班"

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="late_notices")
    date = models.DateField()
    expected_arrival = models.TimeField()
    reason_type = models.CharField(max_length=50)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOTIFIED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LeaveType(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    default_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    quota_type = models.CharField(max_length=30, default="固定年度額度")
    minimum_unit = models.CharField(max_length=30, default="1 天")
    is_paid = models.BooleanField(default=False)
    deduct_quota = models.BooleanField(default=True)
    requires_manager_approval = models.BooleanField(default=True)
    attachment_required = models.BooleanField(default=False)
    allow_hourly = models.BooleanField(default=False)
    allow_carry_over = models.BooleanField(default=False)
    attachment_rule = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="balances")
    year = models.PositiveIntegerField()
    allocated_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    carried_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        ordering = ["-year", "leave_type__name"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "leave_type", "year"], name="unique_employee_leave_balance")
        ]

    @property
    def used_days(self):
        requests = self.employee.leave_requests.filter(
            leave_type=self.leave_type,
            status=LeaveRequest.Status.APPROVED,
            start_date__year=self.year,
        )
        return sum((request.days for request in requests), 0)

    @property
    def remaining_days(self):
        return self.allocated_days + self.carried_days - self.used_days


class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=50, blank=True)
    target_label = models.CharField(max_length=200, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ProfileChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待審核"
        APPROVED = "approved", "已核准"
        REJECTED = "rejected", "已退回"

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile_change_requests")
    requested_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
