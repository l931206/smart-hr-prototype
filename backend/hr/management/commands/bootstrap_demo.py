import os

from django.core.management.base import BaseCommand

from django.utils import timezone

from hr.models import Department, LeaveBalance, LeaveType, User


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

        users = {}
        for username, password, display_name, role, employee_no in credentials:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.display_name = display_name
            user.job_title = {User.Role.EMPLOYEE: "營運專員", User.Role.MANAGER: "部門主管", User.Role.ADMIN: "系統管理者"}[role]
            user.role = role
            user.employee_no = employee_no
            user.department = department
            user.is_active = True
            user.is_staff = role == User.Role.ADMIN
            user.is_superuser = role == User.Role.ADMIN
            user.work_start_time = "09:00"
            user.work_end_time = "18:00"
            if not user.date_joined:
                user.date_joined = timezone.now()
            user.save()
            users[role] = user

        if users.get(User.Role.EMPLOYEE) and users.get(User.Role.MANAGER):
            users[User.Role.EMPLOYEE].manager = users[User.Role.MANAGER]
            users[User.Role.EMPLOYEE].save(update_fields=["manager"])

        default_types = [
            {"code": "ANNUAL", "name": "特休假", "default_days": 7, "is_paid": True, "deduct_quota": True, "description": "依年度額度使用，核准後扣除天數。"},
            {"code": "PERSONAL", "name": "事假", "default_days": 14, "is_paid": False, "deduct_quota": True, "description": "因個人事由申請。"},
            {"code": "SICK", "name": "病假", "default_days": 30, "is_paid": False, "deduct_quota": True, "attachment_required": True, "attachment_rule": "請上傳就醫證明。"},
            {"code": "OFFICIAL", "name": "公假", "default_days": 0, "is_paid": True, "deduct_quota": False, "description": "因公務需求申請，不扣年度額度。"},
        ]
        employee = users.get(User.Role.EMPLOYEE)
        for values in default_types:
            defaults = {key: value for key, value in values.items() if key != "code"}
            leave_type, _ = LeaveType.objects.update_or_create(code=values["code"], defaults=defaults)
            if employee and leave_type.deduct_quota:
                LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=timezone.localdate().year,
                    defaults={"allocated_days": leave_type.default_days},
                )

        self.stdout.write(self.style.SUCCESS("Demo accounts are ready."))
