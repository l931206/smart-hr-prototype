import os

from django.core.management.base import BaseCommand

from hr.models import Department, User


class Command(BaseCommand):
    help = "Create or update the demo accounts used by the prototype."

    def handle(self, *args, **options):
        credentials = [
            (
                os.getenv("DEMO_EMPLOYEE_USERNAME", "employee01"),
                os.getenv("DEMO_EMPLOYEE_PASSWORD"),
                "員工示範帳號",
                User.Role.EMPLOYEE,
                "EMP0001",
            ),
            (
                os.getenv("DEMO_MANAGER_USERNAME", "manager01"),
                os.getenv("DEMO_MANAGER_PASSWORD"),
                "主管示範帳號",
                User.Role.MANAGER,
                "EMP0002",
            ),
            (
                os.getenv("DEMO_ADMIN_USERNAME", "admin01"),
                os.getenv("DEMO_ADMIN_PASSWORD"),
                "系統管理者示範帳號",
                User.Role.ADMIN,
                "EMP0003",
            ),
        ]
        if any(not password for _, password, *_ in credentials):
            self.stdout.write("Demo account passwords are not configured; skipping.")
            return

        department, _ = Department.objects.get_or_create(
            code="OPS", defaults={"name": "營運部"}
        )

        for username, password, display_name, role, employee_no in credentials:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.display_name = display_name
            user.role = role
            user.employee_no = employee_no
            user.department = department
            user.is_active = True
            user.is_staff = role == User.Role.ADMIN
            user.is_superuser = role == User.Role.ADMIN
            user.save()

        self.stdout.write(self.style.SUCCESS("Demo accounts are ready."))
