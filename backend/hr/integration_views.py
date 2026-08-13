from django.conf import settings
from django.core import signing
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.views import APIView

from .permissions_catalog import ROLE_PERMISSIONS, SYSTEM_CODE, permissions_for
from .mock_central import issue_mock_token, verify_mock_token
from .models import User


class MockCentralLoginSerializer(serializers.Serializer):
    external_user_id = serializers.CharField(max_length=100)


class MockCentralVerifySerializer(serializers.Serializer):
    token = serializers.CharField()


class MockCentralLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="模擬中控登入（僅供展示環境）",
        request=MockCentralLoginSerializer,
        responses={200: OpenApiResponse(description="短效 Bearer Token 與對應使用者")},
        auth=[],
    )
    def post(self, request):
        if not settings.ENABLE_MOCK_CENTRAL:
            return Response({"detail": "模擬中控未啟用。"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MockCentralLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(
                external_user_id=serializer.validated_data["external_user_id"],
                username__in=["employee01", "manager01", "admin01"],
                is_active=True,
            )
        except User.DoesNotExist:
            return Response({"detail": "找不到可用的中控示範帳號。"}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "access_token": issue_mock_token(user),
            "token_type": "Bearer",
            "expires_in": settings.MOCK_CENTRAL_TOKEN_MAX_AGE,
            "user": {
                "external_user_id": user.external_user_id,
                "username": user.username,
                "name": user.display_name or user.username,
                "role": user.role,
            },
        })


class MockCentralVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="模擬中控 Token 驗證（僅供展示環境）",
        request=MockCentralVerifySerializer,
        responses={200: OpenApiResponse(description="模擬中控身分資料")},
        auth=[],
    )
    def post(self, request):
        if not settings.ENABLE_MOCK_CENTRAL:
            return Response({"detail": "模擬中控未啟用。"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MockCentralVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            identity = verify_mock_token(serializer.validated_data["token"])
        except (signing.BadSignature, signing.SignatureExpired):
            return Response({"active": False}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(identity)


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
