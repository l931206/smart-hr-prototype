from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Department, LeaveRequest, User
from .serializers import DepartmentSerializer, LeaveRequestSerializer, LoginSerializer, UserSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("department").all()
    serializer_class = UserSerializer

    def get_queryset(self):
        return super().get_queryset().filter(is_staff=False)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee", "employee__department").all()
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.ADMIN or self.request.user.is_staff:
            return queryset
        if self.request.user.role == User.Role.MANAGER:
            return queryset.filter(employee__department=self.request.user.department)
        return queryset.filter(employee=self.request.user)

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role == User.Role.EMPLOYEE:
            serializer.save(employee=self.request.user)
            return
        status_value = serializer.validated_data.get("status")
        if status_value in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED}:
            serializer.save(reviewed_at=timezone.now())
        else:
            serializer.save()
