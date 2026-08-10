from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, DepartmentViewSet, EmployeeViewSet, HealthView, LateNoticeViewSet, LeaveRequestViewSet, LoginView, LogoutView, MeView, NotificationViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("late-notices", LateNoticeViewSet, basename="late-notice")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
