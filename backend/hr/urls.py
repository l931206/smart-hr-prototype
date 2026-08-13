from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .integration_views import IntegrationManifestView, IntegrationMeView
from .views import AccountViewSet, AnnouncementViewSet, AuditLogViewSet, DepartmentViewSet, EmployeeViewSet, HealthView, LateNoticeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet, LeaveTypeViewSet, LoginView, LogoutView, MeView, NotificationViewSet, ProfileChangeRequestViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("accounts", AccountViewSet, basename="account")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("late-notices", LateNoticeViewSet, basename="late-notice")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("profile-change-requests", ProfileChangeRequestViewSet, basename="profile-change-request")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("integration/manifest/", IntegrationManifestView.as_view(), name="integration-manifest"),
    path("integration/me/", IntegrationMeView.as_view(), name="integration-me"),
    path("", include(router.urls)),
]
