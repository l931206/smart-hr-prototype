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
