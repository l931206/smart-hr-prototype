from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, DepartmentViewSet, EmployeeViewSet, HealthView, LateNoticeViewSet, LeaveRequestViewSet, LeaveTypeViewSet, LoginView, LogoutView, MeView, NotificationViewSet, ProfileChangeRequestViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("late-notices", LateNoticeViewSet, basename="late-notice")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("profile-change-requests", ProfileChangeRequestViewSet, basename="profile-change-request")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
