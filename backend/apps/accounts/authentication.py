from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuth


class JWTAuthentication(BaseJWTAuth):
    """封禁用户在鉴权阶段即时拒绝；RBAC 由权限类收口。"""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result and result[0] is not None and not result[0].is_active:
            raise AuthenticationFailed("账号已被封禁")
        return result


class QueryTokenJWTAuthentication(JWTAuthentication):
    """文件受控下载：允许 ?token=<access> 传递（浏览器直接打开链接场景）。"""

    def authenticate(self, request):
        if not request.META.get("HTTP_AUTHORIZATION"):
            token = request.GET.get("token")
            if token:
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return super().authenticate(request)
