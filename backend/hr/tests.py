from django.urls import reverse
from rest_framework.test import APITestCase

from .models import AuditLog, Announcement, Department, LeaveBalance, LeaveRequest, LeaveType, ProfileChangeRequest, User


class CoreApiTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(code="IT", name="資訊部")
        self.user = User.objects.create_user(
            username="emp001",
            password="password-for-tests",
            employee_no="EMP0001",
            display_name="測試員工",
            role=User.Role.EMPLOYEE,
            department=self.department,
        )

    def test_login_returns_token_and_user(self):
        response = self.client.post(
            reverse("login"),
            {"username": "emp001", "password": "password-for-tests"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["employee_no"], "EMP0001")

    def test_health_endpoint_is_public(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_read_departments_and_employees(self):
        self.client.force_authenticate(user=self.user)
        departments = self.client.get("/api/departments/")
        employees = self.client.get("/api/employees/")
        self.assertEqual(departments.status_code, 200)
        self.assertEqual(employees.status_code, 200)
        self.assertEqual(departments.data[0]["code"], "IT")
        self.assertEqual(employees.data[0]["employee_no"], "EMP0001")

    def test_employee_can_create_and_read_own_leave_request(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/leave-requests/",
            {
                "leave_type": "特休",
                "start_date": "2026-08-10",
                "end_date": "2026-08-11",
                "start_time": "全天",
                "end_time": "全天",
                "reason": "私人事務",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["days"], 2)
        self.assertEqual(LeaveRequest.objects.count(), 1)

    def test_manager_can_approve_department_leave_request(self):
        manager = User.objects.create_user(
            username="manager001",
            password="manager-password",
            employee_no="MGR0001",
            display_name="王主管",
            role=User.Role.MANAGER,
            department=self.department,
        )
        request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type="特休假",
            start_date="2026-08-10",
            end_date="2026-08-10",
            reason="家庭事務",
        )
        self.client.force_authenticate(user=manager)
        response = self.client.patch(
            f"/api/leave-requests/{request.id}/",
            {"status": LeaveRequest.Status.APPROVED, "reviewer_comment": "核准"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(request.reviewer_comment, "核准")

    def test_leave_type_rules_are_persisted(self):
        admin = User.objects.create_superuser(username="admin-test", password="admin-password")
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            "/api/leave-types/",
            {
                "code": "OFFICIAL",
                "name": "公假",
                "default_days": "2.5",
                "quota_type": "固定年度額度",
                "minimum_unit": "半天",
                "is_paid": True,
                "deduct_quota": False,
                "requires_manager_approval": True,
                "attachment_required": True,
                "allow_hourly": False,
                "allow_carry_over": False,
                "attachment_rule": "需附公文",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        leave_type = LeaveType.objects.get(code="OFFICIAL")
        self.assertEqual(str(leave_type.default_days), "2.5")
        self.assertTrue(leave_type.attachment_required)
        self.assertEqual(leave_type.attachment_rule, "需附公文")

    def test_manager_only_sees_own_announcements(self):
        manager = User.objects.create_user(username="manager-a", password="password", role=User.Role.MANAGER, department=self.department)
        other = User.objects.create_user(username="manager-b", password="password", role=User.Role.MANAGER, department=self.department)
        own = Announcement.objects.create(title="自己的公告", content="內容", created_by=manager)
        Announcement.objects.create(title="其他主管公告", content="內容", created_by=other)
        self.client.force_authenticate(user=manager)
        response = self.client.get("/api/announcements/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [own.id])

    def test_employee_cannot_approve_own_leave_request(self):
        leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type="特休假",
            start_date="2026-08-12",
            end_date="2026-08-12",
            reason="測試權限",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/leave-requests/{leave_request.id}/",
            {"status": LeaveRequest.Status.APPROVED},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.PENDING)

    def test_employee_cannot_write_departments_or_other_employees(self):
        other = User.objects.create_user(username="other-employee", password="password", role=User.Role.EMPLOYEE)
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post("/api/departments/", {"code": "HR", "name": "人資部"}).status_code, 403)
        self.assertEqual(self.client.get(f"/api/employees/{other.id}/").status_code, 404)

    def test_only_admin_can_review_profile_change_request(self):
        request_item = ProfileChangeRequest.objects.create(employee=self.user, requested_data={"phone": "0912000000"})
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/profile-change-requests/{request_item.id}/",
            {"status": ProfileChangeRequest.Status.APPROVED},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_leave_balance_is_created_and_deducted_from_approved_requests(self):
        leave_type = LeaveType.objects.create(code="ANNUAL", name="特休假", default_days="10.0", deduct_quota=True)
        manager = User.objects.create_user(username="balance-manager", password="password", role=User.Role.MANAGER, department=self.department)
        leave_request = LeaveRequest.objects.create(employee=self.user, leave_type="特休假", start_date="2026-08-12", end_date="2026-08-13", reason="休假")
        self.client.force_authenticate(user=self.user)
        balance_response = self.client.get("/api/leave-balances/?year=2026")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.data[0]["remaining_days"], "10.0")
        self.client.force_authenticate(user=manager)
        approve = self.client.patch(f"/api/leave-requests/{leave_request.id}/", {"status": "approved"}, format="json")
        self.assertEqual(approve.status_code, 200)
        balance = LeaveBalance.objects.get(employee=self.user, leave_type=leave_type, year=2026)
        self.assertEqual(balance.remaining_days, 8)

    def test_required_leave_attachment_is_validated(self):
        LeaveType.objects.create(code="SICK", name="病假", attachment_required=True, deduct_quota=False)
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/leave-requests/", {"leave_type":"病假", "start_date":"2026-08-12", "end_date":"2026-08-12", "reason":"就醫"}, format="json")
        self.assertEqual(response.status_code, 400)
        attached = self.client.post("/api/leave-requests/", {"leave_type":"病假", "start_date":"2026-08-12", "end_date":"2026-08-12", "reason":"就醫", "attachment_name":"proof.pdf", "attachment_data":"data:application/pdf;base64,VEVTVA=="}, format="json")
        self.assertEqual(attached.status_code, 201)

    def test_audit_logs_are_admin_only_and_record_login(self):
        self.client.post(reverse("login"), {"username":"emp001", "password":"password-for-tests"}, format="json")
        self.assertTrue(AuditLog.objects.filter(action="登入", actor=self.user).exists())
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get("/api/audit-logs/").status_code, 403)
        admin = User.objects.create_superuser(username="audit-admin", password="admin-password")
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.client.get("/api/audit-logs/").status_code, 200)

    def test_admin_can_store_termination_details_and_reactivation_clears_them(self):
        admin = User.objects.create_superuser(username="hr-admin", password="admin-password")
        self.client.force_authenticate(user=admin)
        response = self.client.patch(
            f"/api/employees/{self.user.id}/",
            {"is_active": False, "termination_date": "2026-08-11", "termination_reason": "自願離職"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["termination_date"], "2026-08-11")
        self.assertEqual(response.data["termination_reason"], "自願離職")
        response = self.client.patch(f"/api/employees/{self.user.id}/", {"is_active": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["termination_date"])
        self.assertEqual(response.data["termination_reason"], "")

    def test_account_api_includes_admin_and_is_admin_only(self):
        admin = User.objects.create_superuser(username="account-admin", password="admin-password", display_name="帳號管理者")
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get("/api/accounts/").status_code, 403)
        self.client.force_authenticate(user=admin)
        response = self.client.get("/api/accounts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["username"] for item in response.data}, {"emp001", "account-admin"})
