"""订单接口：学生发单/支付/确认/取消/评价/申诉，跑腿员接单/打卡。"""
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import locks, schemas
from apps.common.errors import BizError
from apps.common.serializers import (
    AppealSerializer,
    CancelSerializer,
    DeliverSerializer,
    OrderCreateSerializer,
    PaySerializer,
    PickupSerializer,
    ReviewSerializer,
)
from apps.orders import services
from apps.orders.models import Order


def get_user_orders(user, role, statuses):
    if role == "runner":
        qs = Order.objects.filter(runner=user)
    else:
        qs = Order.objects.filter(student=user)
    if statuses:
        qs = qs.filter(status__in=statuses)
    return qs.select_related("student", "runner").prefetch_related("reviews")


class OrderListCreateView(APIView):
    def get(self, request):
        role = request.query_params.get("role", "student")
        statuses = [s for s in request.query_params.get("status", "").split(",") if s]
        qs = get_user_orders(request.user, role, statuses)
        paginator = self._paginator()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([schemas.order_dict(o) for o in page])

    def post(self, request):
        if request.user.is_admin:
            raise BizError("管理员不可发布需求", code=40300, http_status=403)
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.create_order(request.user, serializer.validated_data)
        return Response(schemas.order_dict(order, detail=True), status=201)

    @staticmethod
    def _paginator():
        from apps.common.pagination import StandardPagination

        return StandardPagination()


class AvailableOrderListView(APIView):
    """待接单大厅：自行判断，不抢单。"""

    def get(self, request):
        sort = request.query_params.get("sort", "time")
        qs = Order.objects.filter(status=Order.Status.PENDING_ACCEPT).exclude(student=request.user).select_related("student")
        qs = qs.order_by("time_window_end" if sort == "time" else "-runner_fee")
        paginator = OrderListCreateView._paginator()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([schemas.order_dict(o) for o in page])


class OrderDetailView(APIView):
    def get(self, request, order_no):
        order = services.get_order(order_no)
        if request.user.id not in (order.student_id, order.runner_id) and not request.user.is_admin:
            raise BizError("无权查看该订单", code=40300, http_status=403)
        return Response(schemas.order_dict(order, detail=True))


class OrderPayView(APIView):
    @locks.throttled("pay", 60)
    def post(self, request, order_no):
        serializer = PaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data.get("idempotency_key") or request.headers.get("Idempotency-Key")
        order = services.pay(request.user, order_no, key)
        return Response(schemas.order_dict(order, detail=True))


class OrderCancelView(APIView):
    def post(self, request, order_no):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.cancel(request.user, order_no, serializer.validated_data["reason"])
        return Response(schemas.order_dict(order, detail=True))


class OrderConfirmView(APIView):
    def post(self, request, order_no):
        order = services.confirm(request.user, order_no)  # 幂等：重复确认不重复结算
        return Response(schemas.order_dict(order, detail=True))


class OrderReviewView(APIView):
    def post(self, request, order_no):
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.review(request.user, order_no, **serializer.validated_data)
        return Response(schemas.review_dict(record), status=201)


class OrderAppealView(APIView):
    def post(self, request, order_no):
        serializer = AppealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.appeal(request.user, order_no, **serializer.validated_data)
        return Response(schemas.appeal_dict(record), status=201)


class OrderAcceptView(APIView):
    def post(self, request, order_no):
        order = services.accept(request.user, order_no)
        return Response(schemas.order_dict(order, detail=True))


class OrderPickupView(APIView):
    def post(self, request, order_no):
        serializer = PickupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.pickup(request.user, order_no, **serializer.validated_data)
        return Response(schemas.order_dict(order, detail=True))


class OrderDeliverView(APIView):
    def post(self, request, order_no):
        serializer = DeliverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.deliver(request.user, order_no, **serializer.validated_data)
        return Response(schemas.order_dict(order, detail=True))


class ReceivedReviewView(APIView):
    """我收到的评价（跑腿员/学生通用）。"""

    def get(self, request):
        from apps.orders.models import Review

        qs = Review.objects.filter(reviewee=request.user).select_related("reviewer", "reviewee", "order")
        paginator = OrderListCreateView._paginator()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([schemas.review_dict(r) for r in page])
