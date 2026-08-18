from django.urls import reverse
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.exceptions import ValidationError
from unittest.mock import MagicMock, patch
from datetime import timedelta
import asyncio

from .authentication import CentralTokenAuthentication
from .leave_services import create_mcp_leave_draft, submit_mcp_leave_draft
from .mcp_server import SmartHRCentralTokenVerifier, mcp
from .mock_central import issue_mock_token
from .models import AuditLog, Announcement, Department, LeaveBalance, LeaveRequest, LeaveType, McpLeaveDraft, ProfileChangeRequest, User


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
        self.default_leave_type = LeaveType.objects.create(
            code="VACATION",
            name="特休",
            default_days="10.0",
            deduct_quota=True,
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
        self.assertEqual(response.data["days"], "2.000")
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
            leave_type=self.default_leave_type,
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

    def test_carry_over_is_applied_when_creating_leave_type_and_yearly_balance(self):
        admin = User.objects.create_superuser(username="carry-admin", password="admin-password")
        previous_type = LeaveType.objects.create(
            code="CARRY-EXISTING",
            name="既有結轉假",
            default_days="5.0",
            deduct_quota=True,
            allow_carry_over=True,
        )
        year = timezone.localdate().year
        LeaveBalance.objects.create(
            employee=self.user,
            leave_type=previous_type,
            year=year - 1,
            allocated_days="4.0",
        )
        self.client.force_authenticate(user=self.user)
        balance_response = self.client.get(f"/api/leave-balances/?year={year}")
        self.assertEqual(balance_response.status_code, 200)
        existing_balance = LeaveBalance.objects.get(employee=self.user, leave_type=previous_type, year=year)
        self.assertEqual(existing_balance.carried_days, 4)

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            "/api/leave-types/",
            {
                "code": "CARRY-NEW",
                "name": "新結轉假",
                "default_days": "3.0",
                "minimum_unit": "半天",
                "deduct_quota": True,
                "allow_carry_over": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(LeaveBalance.objects.filter(employee=self.user, leave_type__code="CARRY-NEW", year=year).exists())

    def test_hourly_leave_enforces_configured_minimum_unit(self):
        hourly_type = LeaveType.objects.create(
            code="HOURLY",
            name="時數假",
            deduct_quota=False,
            allow_hourly=True,
            minimum_unit="2 小時",
        )
        self.client.force_authenticate(user=self.user)
        too_short = self.client.post(
            "/api/leave-requests/",
            {
                "leave_type": hourly_type.name,
                "start_date": "2026-08-18",
                "end_date": "2026-08-18",
                "start_time": "09:00",
                "end_time": "10:00",
                "reason": "時數測試",
            },
            format="json",
        )
        self.assertEqual(too_short.status_code, 400)
        valid = self.client.post(
            "/api/leave-requests/",
            {
                "leave_type": hourly_type.name,
                "start_date": "2026-08-18",
                "end_date": "2026-08-18",
                "start_time": "09:00",
                "end_time": "11:00",
                "reason": "時數測試",
            },
            format="json",
        )
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(valid.data["days"], "0.250")

    def test_leave_without_manager_approval_is_approved_immediately(self):
        leave_type = LeaveType.objects.create(
            code="AUTO",
            name="免簽核假",
            deduct_quota=False,
            requires_manager_approval=False,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/leave-requests/",
            {
                "leave_type": leave_type.name,
                "start_date": "2026-08-18",
                "end_date": "2026-08-18",
                "start_time": "上午",
                "end_time": "下午",
                "reason": "免簽核測試",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], LeaveRequest.Status.APPROVED)

    def test_manager_sees_published_company_announcements_and_own_drafts(self):
        manager = User.objects.create_user(username="manager-a", password="password", role=User.Role.MANAGER, department=self.department)
        other = User.objects.create_user(username="manager-b", password="password", role=User.Role.MANAGER, department=self.department)
        own = Announcement.objects.create(title="自己的草稿", content="內容", created_by=manager)
        published = Announcement.objects.create(title="公司公告", content="內容", created_by=other, is_published=True)
        Announcement.objects.create(title="其他主管草稿", content="內容", created_by=other)
        self.client.force_authenticate(user=manager)
        response = self.client.get("/api/announcements/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"] for item in response.data}, {own.id, published.id})

    def test_employee_cannot_approve_own_leave_request(self):
        leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.default_leave_type,
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
        leave_request = LeaveRequest.objects.create(employee=self.user, leave_type=leave_type, start_date="2026-08-12", end_date="2026-08-13", reason="休假")
        self.client.force_authenticate(user=self.user)
        balance_response = self.client.get("/api/leave-balances/?year=2026")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.data[0]["remaining_days"], "10.0")
        self.client.force_authenticate(user=manager)
        approve = self.client.patch(f"/api/leave-requests/{leave_request.id}/", {"status": "approved"}, format="json")
        self.assertEqual(approve.status_code, 200)
        balance = LeaveBalance.objects.get(employee=self.user, leave_type=leave_type, year=2026)
        self.assertEqual(balance.remaining_days, 8)

    def test_leave_days_exclude_weekends_and_support_half_day(self):
        request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.default_leave_type,
            start_date="2026-08-14",
            end_date="2026-08-17",
            start_time="下午",
            end_time="下午",
            reason="跨週末休假",
        )
        self.assertEqual(request.days, 1.5)

    def test_employee_can_withdraw_pending_leave(self):
        request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.default_leave_type,
            start_date="2026-08-17",
            end_date="2026-08-17",
            start_time="上午",
            end_time="下午",
            reason="測試撤回",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f"/api/leave-requests/{request.id}/withdraw/")
        self.assertEqual(response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.WITHDRAWN)

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
        admin_data = next(item for item in response.data if item["username"] == "account-admin")
        self.assertIn("last_login", admin_data)
        self.assertIn("date_joined", admin_data)

    def test_integration_manifest_is_public_and_lists_real_roles(self):
        response = self.client.get("/api/integration/manifest/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["system_code"], "smart-hr")
        self.assertEqual(set(response.data["roles"]), {"employee", "manager", "admin"})
        self.assertIn("leave.apply", response.data["roles"]["employee"])
        self.assertIn("leave.review", response.data["roles"]["manager"])
        self.assertIn("account.manage", response.data["roles"]["admin"])

    def test_integration_me_requires_authentication(self):
        response = self.client.get("/api/integration/me/")
        self.assertEqual(response.status_code, 401)

    def test_integration_me_returns_mapped_identity_and_permissions(self):
        self.user.external_user_id = "central-user-123"
        self.user.save(update_fields=["external_user_id"])
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/integration/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["external_user_id"], "central-user-123")
        self.assertEqual(response.data["user"]["role"], "employee")
        self.assertEqual(response.data["user"]["department"], self.department.name)
        self.assertIn("leave.apply", response.data["permissions"])
        self.assertNotIn("account.manage", response.data["permissions"])

    def test_openapi_schema_and_swagger_are_available(self):
        schema = self.client.get("/api/schema/")
        docs = self.client.get("/api/docs/")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(docs.status_code, 200)

    @override_settings(
        CENTRAL_TOKEN_VERIFY_URL="https://central.example.test/token/verify",
        CENTRAL_TOKEN_FIELD="token",
        CENTRAL_API_KEY="test-api-key",
    )
    def test_central_bearer_token_maps_only_prelinked_user(self):
        self.user.external_user_id = "central-user-123"
        self.user.save(update_fields=["external_user_id"])
        response = MagicMock()
        response.read.return_value = b'{"active": true, "user_id": "central-user-123"}'
        response.__enter__.return_value = response
        request = APIRequestFactory().get("/api/integration/me/", HTTP_AUTHORIZATION="Bearer central-token")
        with patch("hr.authentication.urlopen", return_value=response):
            authenticated_user, auth_context = CentralTokenAuthentication().authenticate(request)
        self.assertEqual(authenticated_user, self.user)
        self.assertEqual(auth_context["source"], "central")

    @override_settings(
        AUTH_MODE="hybrid",
        ENABLE_MOCK_CENTRAL=True,
        MOCK_CENTRAL_TOKEN_MAX_AGE=900,
        CENTRAL_TOKEN_VERIFY_URL="",
    )
    def test_mock_central_login_and_bearer_authentication_flow(self):
        self.user.username = "employee01"
        self.user.external_user_id = "central-employee-001"
        self.user.save(update_fields=["username", "external_user_id"])
        response = self.client.post(
            "/api/mock-central/login/",
            {"external_user_id": "central-employee-001"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token_type"], "Bearer")
        token = response.data["access_token"]
        request = APIRequestFactory().get("/api/integration/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        authenticated_user, auth_context = CentralTokenAuthentication().authenticate(request)
        self.assertEqual(authenticated_user, self.user)
        self.assertEqual(auth_context["identity"]["external_user_id"], "central-employee-001")

    @override_settings(ENABLE_MOCK_CENTRAL=True)
    def test_mock_central_login_rejects_non_demo_account(self):
        self.user.external_user_id = "central-private-user"
        self.user.save(update_fields=["external_user_id"])
        response = self.client.post(
            "/api/mock-central/login/",
            {"external_user_id": "central-private-user"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(ENABLE_MOCK_CENTRAL=False)
    def test_mock_central_endpoints_can_be_disabled(self):
        response = self.client.post(
            "/api/mock-central/login/",
            {"external_user_id": "central-employee-001"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(MCP_DRAFT_TTL_SECONDS=600)
    def test_mcp_preview_requires_confirmation_and_submit_is_single_use(self):
        draft = create_mcp_leave_draft(self.user, {
            "leave_type": self.default_leave_type.name,
            "start_date": "2026-08-19",
            "end_date": "2026-08-19",
            "start_time": "上午",
            "end_time": "下午",
            "reason": "MCP 請假測試",
        })
        self.assertEqual(LeaveRequest.objects.count(), 0)
        self.assertEqual(draft.summary["requested_days"], "1")
        self.assertEqual(draft.summary["remaining_after"], "9.0")

        leave_request = submit_mcp_leave_draft(self.user, str(draft.id))
        self.assertEqual(leave_request.status, LeaveRequest.Status.PENDING)
        self.assertEqual(LeaveRequest.objects.count(), 1)
        draft.refresh_from_db()
        self.assertEqual(draft.submitted_request, leave_request)
        self.assertTrue(AuditLog.objects.filter(target_id=str(leave_request.id), details__source="mcp").exists())
        with self.assertRaises(ValidationError):
            submit_mcp_leave_draft(self.user, str(draft.id))

    def test_expired_mcp_leave_draft_cannot_be_submitted(self):
        draft = create_mcp_leave_draft(self.user, {
            "leave_type": self.default_leave_type.name,
            "start_date": "2026-08-20",
            "end_date": "2026-08-20",
            "start_time": "上午",
            "end_time": "下午",
            "reason": "過期草稿測試",
        })
        McpLeaveDraft.objects.filter(pk=draft.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValidationError):
            submit_mcp_leave_draft(self.user, str(draft.id))
        self.assertEqual(LeaveRequest.objects.count(), 0)

    @override_settings(ENABLE_MOCK_CENTRAL=True, MOCK_CENTRAL_TOKEN_MAX_AGE=900)
    def test_mcp_token_verifier_maps_central_subject(self):
        self.user.external_user_id = "central-employee-001"
        self.user.save(update_fields=["external_user_id"])
        access_token = asyncio.run(SmartHRCentralTokenVerifier().verify_token(issue_mock_token(self.user)))
        self.assertIsNotNone(access_token)
        self.assertEqual(access_token.subject, "central-employee-001")
        self.assertIn("smart-hr", access_token.scopes)

    def test_mcp_server_exposes_expected_leave_tools(self):
        tools = asyncio.run(mcp.list_tools())
        names = {tool.name for tool in tools}
        self.assertEqual(names, {
            "get_current_user",
            "list_leave_types",
            "get_leave_balance",
            "preview_leave_request",
            "submit_leave_request",
            "list_my_leave_requests",
            "withdraw_leave_request",
        })
