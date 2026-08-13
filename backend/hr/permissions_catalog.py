SYSTEM_CODE = "smart-hr"

ROLE_PERMISSIONS = {
    "employee": [
        "profile.read",
        "profile.update",
        "leave.read",
        "leave.apply",
        "late_notice.read",
        "late_notice.create",
        "announcement.read",
        "notification.read",
    ],
    "manager": [
        "profile.read",
        "team.read",
        "leave.read",
        "leave.review",
        "late_notice.read",
        "late_notice.review",
        "announcement.read",
        "announcement.manage",
        "notification.read",
    ],
    "admin": [
        "profile.read",
        "employee.manage",
        "department.manage",
        "account.manage",
        "leave.read",
        "leave_type.manage",
        "profile_change.review",
        "announcement.read",
        "audit_log.read",
    ],
}


def permissions_for(user):
    role = "admin" if user.is_staff or user.is_superuser else user.role
    return ROLE_PERMISSIONS.get(role, [])
