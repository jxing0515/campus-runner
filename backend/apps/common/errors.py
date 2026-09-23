from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

STATUS_TO_CODE = {
    400: 40001,
    401: 40100,
    403: 40300,
    404: 40400,
    405: 40001,
    409: 40900,
    429: 40001,
}


class BizError(exceptions.APIException):
    """业务异常：状态码冲突/重复动作等，前端按 code 处理。"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "业务处理失败"

    def __init__(self, message, code=40001, http_status=None):
        self.code = code
        super().__init__(message)
        if http_status:
            self.status_code = http_status


def conflict(message, code=40900):
    return BizError(message, code=code, http_status=status.HTTP_409_CONFLICT)


def _flatten(detail):
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            text = _flatten(value)
            parts.append(f"{key}: {text}" if key != "detail" else text)
        return "; ".join(parts)
    if isinstance(detail, (list, tuple)):
        return "; ".join(_flatten(item) for item in detail)
    return str(detail)


def exception_handler(exc, context):
    if isinstance(exc, BizError):
        return Response({"code": exc.code, "message": str(exc.detail), "data": None}, status=exc.status_code)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    code = STATUS_TO_CODE.get(response.status_code, 50000 if response.status_code >= 500 else 40001)
    return Response({"code": code, "message": _flatten(response.data), "data": None}, status=response.status_code)
