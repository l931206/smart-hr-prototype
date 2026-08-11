from django.contrib.auth.models import AbstractUser
from django.db import models


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
    display_name = models.CharField(max_length=100, blank=True)
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
    avatar_data = models.TextField(blank=True)

    def __str__(self):
        return self.display_name or self.get_full_name() or self.username


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待審核"
        APPROVED = "approved", "已核准"
        REJECTED = "rejected", "已退回"

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.CharField(max_length=20, blank=True)
    end_time = models.CharField(max_length=20, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1


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
    default_days = models.PositiveIntegerField(default=0)
    is_paid = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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
