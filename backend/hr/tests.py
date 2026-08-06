from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Department, LeaveRequest, User


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
