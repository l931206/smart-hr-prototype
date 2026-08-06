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
