"""信用中心接口。"""
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import schemas
from apps.common.pagination import StandardPagination
from apps.credit import services as credit_services
from apps.credit.models import CreditLog


class CreditMeView(APIView):
    def get(self, request):
        user = request.user
        logs = CreditLog.objects.filter(user=user).order_by("-id")[:20]
        return Response(
            {
                "score": user.credit_score,
                "limits": credit_services.limits_of(user),
                "level_label": credit_services.LEVEL_LABELS[credit_services.level_of(user.credit_score)],
                "logs": [schemas.credit_log_dict(l) for l in logs],
            }
        )


class CreditLogListView(APIView):
    def get(self, request):
        qs = CreditLog.objects.filter(user=request.user).select_related("order")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([schemas.credit_log_dict(l) for l in page])
