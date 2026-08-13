from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions_catalog import ROLE_PERMISSIONS, SYSTEM_CODE, permissions_for


class IntegrationManifestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="取得人資系統整合資訊與角色權限清單",
        responses={200: OpenApiResponse(description="系統代碼、認證模式及角色權限")},
        auth=[],
    )
    def get(self, request):
        return Response({
            "system_code": SYSTEM_CODE,
            "name": "智慧人資管理平台",
            "auth_mode": settings.AUTH_MODE,
            "roles": ROLE_PERMISSIONS,
        })


class IntegrationMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="取得目前登入者在人資系統的身分與權限",
        responses={200: OpenApiResponse(description="使用者資料及可執行權限")},
    )
    def get(self, request):
        user = request.user
        role = "admin" if user.is_staff or user.is_superuser else user.role
        return Response({
            "system_code": SYSTEM_CODE,
            "user": {
                "id": user.id,
                "external_user_id": user.external_user_id,
                "employee_no": user.employee_no,
                "username": user.username,
                "name": user.display_name or user.get_full_name() or user.username,
                "email": user.email,
                "role": role,
                "department": user.department.name if user.department else None,
            },
            "permissions": permissions_for(user),
        })
