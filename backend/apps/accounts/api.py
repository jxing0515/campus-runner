"""认证与跑腿员认证接口。"""
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common import locks, rules, schemas
from apps.common.errors import BizError
from apps.common.models import FileAsset
from apps.common.notify import notify
from apps.common.serializers import (
    ChangePasswordSerializer,
    CertificationSerializer,
    LoginSerializer,
    RegisterSerializer,
)

User = get_user_model()
LOCK_SECONDS = 15 * 60
MAX_FAILS = 5


def _token_payload(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": schemas.user_dict(user, with_limits=True)}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if User.objects.filter(username=data["username"]).exists():
            raise BizError("账号已存在")
        user = User.objects.create_user(
            username=data["username"],
            password=data["password"],
            name=data.get("name", ""),
            student_no=data.get("student_no", ""),
            credit_score=int(rules.get_rule("credit_initial")),
        )
        return Response(schemas.user_dict(user, with_limits=True), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
        fail_key = f"loginfail:{username}"
        if locks.counter(fail_key) >= MAX_FAILS:
            raise BizError("登录失败次数过多，账号已锁定 15 分钟", code=40300, http_status=403)
        allowed, _ = locks.rate_limit(f"login:{ip}:{username}", 5, 60)
        if not allowed:
            raise BizError("登录请求过于频繁，请稍后再试")
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            count = locks.bump(fail_key, LOCK_SECONDS)
            left = max(MAX_FAILS - count, 0)
            raise BizError(f"账号或密码错误，剩余尝试次数 {left}", code=40100, http_status=401)
        locks.clear(fail_key)
        return Response(_token_payload(user))


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            raise BizError("缺少 refresh token", code=40100, http_status=401)
        try:
            refresh = RefreshToken(token)
        except Exception:
            raise BizError("refresh token 无效或已失效", code=40100, http_status=401)
        user = User.objects.filter(pk=refresh["user_id"]).first()
        if user is None or not user.is_active:
            raise BizError("账号不可用", code=40100, http_status=401)
        return Response({"access": str(refresh.access_token)})


class LogoutView(APIView):
    def post(self, request):
        token = request.data.get("refresh")
        if token:
            try:
                RefreshToken(token).blacklist()
            except Exception:
                pass
        return Response({"detail": "已退出登录"})


def _blacklist_all(user):
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class MeView(APIView):
    def get(self, request):
        return Response(schemas.user_dict(request.user, with_limits=True))


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            raise BizError("原密码错误")
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        _blacklist_all(user)  # 改密即拉黑全部 refresh token
        return Response({"detail": "密码已修改，请重新登录"})


class CertificationView(APIView):
    """跑腿员认证：提交后待审核，驳回可改资料重新提交。"""

    def get(self, request):
        user = request.user
        return Response(
            {
                "cert_status": user.cert_status,
                "cert_reject_reason": user.cert_reject_reason,
                "is_runner": user.is_runner,
                "student_no": user.student_no,
                "real_name": user.name,
                "card_file": user.card_file_id,
            }
        )

    def post(self, request):
        serializer = CertificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if user.is_admin:
            raise BizError("管理员不可申请跑腿员认证", code=40300, http_status=403)
        if user.cert_status == User.CertStatus.PENDING:
            raise BizError("认证申请审核中，请勿重复提交", code=40900, http_status=409)
        data = serializer.validated_data
        card = FileAsset.objects.filter(pk=data.get("card_file_id")).first() if data.get("card_file_id") else None
        user.student_no = data["student_no"]
        user.name = data["real_name"]
        user.card_file = card
        user.cert_status = User.CertStatus.PENDING
        user.cert_reject_reason = ""
        user.cert_reviewed_at = None
        user.save(update_fields=["student_no", "name", "card_file", "cert_status", "cert_reject_reason", "updated_at"])
        user.sync_runner_flag()
        notify(user, "认证申请已提交", "管理员审核后即可开启跑腿员模式")
        return Response({"cert_status": user.cert_status})


class StatsView(APIView):
    """个人中心统计（学生/跑腿员通用）。"""

    def get(self, request):
        user = request.user
        from apps.orders.models import Order

        return Response(
            {
                "published": Order.objects.filter(student=user).count(),
                "accepted": Order.objects.filter(runner=user).count(),
                "completed": Order.objects.filter(runner=user, status=Order.Status.COMPLETED).count(),
                "credit_score": user.credit_score,
                "runner_balance": schemas.s(user.runner_balance),
                "unread_notifications": user.notifications.filter(is_read=False).count(),
                "server_time": schemas.dt(timezone.now()),
                "limits": schemas.credit_limits(user),
            }
        )
