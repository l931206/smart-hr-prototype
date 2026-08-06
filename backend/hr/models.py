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
    phone = models.CharField(max_length=30, blank=True)
    hire_date = models.DateField(null=True, blank=True)

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
