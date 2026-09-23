"""跑腿员收入与提现接口。"""
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import schemas
from apps.common.errors import BizError
from apps.common.pagination import StandardPagination
from apps.common.serializers import WithdrawApplySerializer
from apps.finance import services as finance
from apps.finance.models import FundFlow, Withdrawal


class IncomeView(APIView):
    def get(self, request):
        user = request.user
        flows = FundFlow.objects.filter(user=user, type=FundFlow.Type.SETTLE).select_related("order")
        total = finance.money(flows.aggregate(s=Sum("amount"))["s"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(flows.order_by("-id"), request)
        return Response(
            {
                "total_income": schemas.s(total),
                "balance": schemas.s(user.runner_balance),
                "frozen": schemas.s(
                    finance.money(
                        FundFlow.objects.filter(
                            user=user, type=FundFlow.Type.WITHDRAW, status=FundFlow.Status.FROZEN
                        ).aggregate(s=Sum("amount"))["s"]
                    )
                ),
                "records": [schemas.flow_dict(f) for f in page],
                "count": paginator.page.paginator.count,
            }
        )


class WithdrawalListCreateView(APIView):
    def get(self, request):
        qs = Withdrawal.objects.filter(runner=request.user).select_related("runner", "handler")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([schemas.withdrawal_dict(w) for w in page])

    def post(self, request):
        if request.user.is_admin:
            raise BizError("管理员不可提现", code=40300, http_status=403)
        serializer = WithdrawApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        wd = finance.apply_withdrawal(request.user, data["amount"], data["method"], data["account"])
        request.user.refresh_from_db()
        return Response({"withdrawal": schemas.withdrawal_dict(wd), "balance": schemas.s(request.user.runner_balance)}, status=201)
