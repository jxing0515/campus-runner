"""管理端 Web 接口：13 项管理员功能的 API 实现。"""
import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.perms import IsAdmin, IsSuperAdmin, require_perm
from apps.common import locks, rules, schemas
from apps.common.errors import BizError
from apps.common.models import Announcement, FileAsset, Notification, OperationLog, RuleConfig, log_action
from apps.common.notify import notify, notify_many
from apps.common.pagination import StandardPagination
from apps.common.serializers import (
    AnnouncementSerializer,
    ArbitrateSerializer,
    AuditSerializer,
    BanSerializer,
    CreditAdjustSerializer,
    ResolveSerializer,
    RuleSerializer,
)
from apps.common.tasks import reconcile
from apps.credit import services as credit_services
from apps.credit.models import CreditLog
from apps.finance import services as finance
from apps.finance.models import FundFlow, PlatformAccount, Withdrawal
from apps.orders import services as order_services
from apps.orders.models import Appeal, Order, Review


def paginate(view, qs, request, builder):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response([builder(item) for item in page])


def csv_response(filename, header, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return response


# ---------- 1. 认证审核 ----------
class CertificationListView(APIView):
    permission_classes = [require_perm("cert.audit")]

    def get(self, request):
        status = request.query_params.get("status", "pending")
        qs = User.objects.exclude(cert_status=User.CertStatus.NONE)
        if status:
            qs = qs.filter(cert_status=status)
        return paginate(self, qs.order_by("-updated_at"), request, schemas.user_dict)


class CertificationAuditView(APIView):
    permission_classes = [require_perm("cert.audit")]

    def post(self, request, pk):
        serializer = AuditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approve = serializer.validated_data["approve"]
        reason = serializer.validated_data["reason"]
        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise BizError("用户不存在", code=40400, http_status=404)
        if user.cert_status != User.CertStatus.PENDING:
            raise BizError("该申请不在待审核状态", code=40900, http_status=409)
        user.cert_status = User.CertStatus.APPROVED if approve else User.CertStatus.REJECTED
        user.cert_reject_reason = "" if approve else reason
        user.cert_reviewed_by = request.user
        user.cert_reviewed_at = timezone.now()
        user.save(update_fields=["cert_status", "cert_reject_reason", "cert_reviewed_by", "cert_reviewed_at", "updated_at"])
        user.sync_runner_flag()  # is_runner 与认证状态同事务一致
        notify(user, "认证审核结果", "认证已通过，可开启跑腿员模式" if approve else f"认证被驳回：{reason}")
        log_action(request.user, "认证审核", "审核", f"{user.username} → {user.cert_status}", request)
        return Response(schemas.user_dict(user))


# ---------- 2. 用户管理 ----------
class AdminUserListView(APIView):
    permission_classes = [require_perm("user.view")]

    def get(self, request):
        qs = User.objects.all()
        keyword = request.query_params.get("keyword", "").strip()
        if keyword:
            qs = qs.filter(Q(username__icontains=keyword) | Q(name__icontains=keyword) | Q(student_no__icontains=keyword))
        if request.query_params.get("banned") in ("1", "true"):
            qs = qs.filter(banned=True)
        if request.query_params.get("is_runner") in ("1", "true"):
            qs = qs.filter(is_runner=True)
        return paginate(self, qs.order_by("-id"), request, schemas.user_dict)


class UserBanView(APIView):
    permission_classes = [require_perm("user.ban")]

    def post(self, request, pk):
        serializer = BanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise BizError("用户不存在", code=40400, http_status=404)
        if user.is_super_admin:
            raise BizError("不可封禁超级管理员", code=40300, http_status=403)
        user.banned = serializer.validated_data["banned"]
        user.ban_reason = serializer.validated_data["reason"]
        user.is_active = not user.banned
        user.save(update_fields=["banned", "ban_reason", "is_active", "updated_at"])
        if user.banned:  # 封禁即拉黑已签发 token
            from apps.accounts.api import _blacklist_all

            _blacklist_all(user)
        log_action(request.user, "用户管理", "封禁" if user.banned else "解封", f"{user.username} {user.ban_reason}", request)
        return Response(schemas.user_dict(user))


class UserCreditView(APIView):
    permission_classes = [require_perm("user.credit")]

    def post(self, request, pk):
        serializer = CreditAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise BizError("用户不存在", code=40400, http_status=404)
        data = serializer.validated_data
        record = credit_services.change(user, data["delta"], CreditLog.Reason.ADMIN_ADJUST, remark=data["reason"])
        log_action(request.user, "用户管理", "调整信用", f"{user.username} {data['delta']} 分：{data['reason']}", request)
        return Response({"user": schemas.user_dict(User.objects.get(pk=pk)), "log": schemas.credit_log_dict(record)})


# ---------- 3–4. 需求 / 订单监控 ----------
def _order_qs(request):
    qs = Order.objects.select_related("student", "runner")
    status_param = request.query_params.get("status", "")
    if status_param:
        qs = qs.filter(status__in=[s for s in status_param.split(",") if s])
    if request.query_params.get("abnormal") in ("1", "true"):
        qs = qs.filter(status=Order.Status.ABNORMAL)
    keyword = request.query_params.get("keyword", "").strip()
    if keyword:
        qs = qs.filter(Q(order_no__icontains=keyword) | Q(description__icontains=keyword))
    return qs


class AdminDemandListView(APIView):
    permission_classes = [require_perm("demand.view")]

    def get(self, request):
        return paginate(self, _order_qs(request), request, schemas.order_dict)


class AdminOrderListView(APIView):
    permission_classes = [require_perm("order.view")]

    def get(self, request):
        return paginate(self, _order_qs(request), request, schemas.order_dict)


class AdminOrderDetailView(APIView):
    permission_classes = [require_perm("order.view")]

    def get(self, request, order_no):
        return Response(schemas.order_dict(order_services.get_order(order_no), detail=True))


class AdminOrderResolveView(APIView):
    """异常订单人工处理：确认完成（结算）或取消（退款）。"""

    permission_classes = [require_perm("order.resolve")]

    def post(self, request, order_no):
        serializer = ResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = order_services.resolve_abnormal(order_no, request.user, data["action"], data["remark"])
        log_action(request.user, "订单监控", f"异常处理-{data['action']}", f"{order_no} {data['remark']}", request)
        return Response(schemas.order_dict(order, detail=True))


# ---------- 5–8. 资金流水 / 托管 / 结算 / 退款 ----------
def _flow_qs(request, types=None):
    qs = FundFlow.objects.select_related("order", "user", "withdrawal")
    if types:
        qs = qs.filter(type__in=types)
    if request.query_params.get("type"):
        qs = qs.filter(type=request.query_params["type"])
    fee_part = request.query_params.get("fee_part")
    if fee_part == "runner":
        qs = qs.filter(runner_fee_part__gt=0)
    elif fee_part == "item":
        qs = qs.filter(item_fee_part__gt=0)
    if request.query_params.get("order_no"):
        qs = qs.filter(order__order_no=request.query_params["order_no"])
    if request.query_params.get("status"):
        qs = qs.filter(status=request.query_params["status"])
    return qs.order_by("-id")


class FundFlowListView(APIView):
    permission_classes = [require_perm("flow.view")]

    def get(self, request):
        return paginate(self, _flow_qs(request), request, schemas.flow_dict)


class FundFlowExportView(APIView):
    permission_classes = [require_perm("flow.view")]

    def get(self, request):
        rows = [
            [f.flow_no, f.order.order_no if f.order_id else "", f.get_type_display(), f.get_status_display(),
             f.get_direction_display(), f"{f.amount:.2f}", f"{f.runner_fee_part:.2f}", f"{f.item_fee_part:.2f}",
             f"{f.balance_after:.2f}", f.external_no, schemas.dt(f.created_at)]
            for f in _flow_qs(request)[:5000]
        ]
        return csv_response("fund_flows.csv", ["流水号", "订单号", "类型", "状态", "方向", "金额", "跑腿费", "物品费", "余额快照", "外部单号", "时间"], rows)


class EscrowView(APIView):
    """托管监控：平台账户 vs Σ托管中流水。"""

    permission_classes = [require_perm("escrow.view")]

    def get(self, request):
        account = PlatformAccount.load()
        from_flows = finance.account_escrow_total()
        return Response(
            {
                "account_escrow_total": schemas.s(account.escrow_total),
                "flows_escrow_total": schemas.s(from_flows),
                "matched": finance.money(account.escrow_total) == from_flows,
                "total_paid": schemas.s(account.total_paid),
                "total_settled": schemas.s(account.total_settled),
                "total_refunded": schemas.s(account.total_refunded),
                "pending_appeals": Appeal.objects.filter(status__in=[Appeal.Status.PENDING, Appeal.Status.PROCESSING]).count(),
                "updated_at": schemas.dt(account.updated_at),
            }
        )


class SettlementListView(APIView):
    permission_classes = [require_perm("settle.view")]

    def get(self, request):
        return paginate(self, _flow_qs(request, [FundFlow.Type.SETTLE]), request, schemas.flow_dict)


class RefundListView(APIView):
    permission_classes = [require_perm("refund.view")]

    def get(self, request):
        return paginate(self, _flow_qs(request, [FundFlow.Type.REFUND]), request, schemas.flow_dict)


# ---------- 9. 提现审核 ----------
class AdminWithdrawalListView(APIView):
    permission_classes = [require_perm("withdraw.audit")]

    def get(self, request):
        qs = Withdrawal.objects.select_related("runner", "handler")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return paginate(self, qs.order_by("-id"), request, schemas.withdrawal_dict)


class AdminWithdrawalAuditView(APIView):
    permission_classes = [require_perm("withdraw.audit")]

    def post(self, request, pk):
        serializer = AuditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wd = Withdrawal.objects.filter(pk=pk).first()
        if wd is None:
            raise BizError("提现记录不存在", code=40400, http_status=404)
        data = serializer.validated_data
        wd = finance.audit_withdrawal(wd, data["approve"], data["reason"], request.user)
        notify(wd.runner, "提现审核结果", "提现已通过（模拟出账）" if data["approve"] else f"提现被驳回：{data['reason']}，金额已回滚")
        log_action(request.user, "提现审核", "通过" if data["approve"] else "驳回", f"提现#{wd.pk} 金额 {wd.amount}", request)
        return Response(schemas.withdrawal_dict(wd))


# ---------- 10. 信用规则配置 ----------
class RuleListCreateView(APIView):
    permission_classes = [require_perm("rule.write")]

    def get(self, request):
        rules.ensure_default_rules()
        return Response([schemas.rule_dict(r) for r in RuleConfig.objects.all().order_by("rule_type", "key")])

    def post(self, request):
        serializer = RuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        row = rules.set_rule(data["key"], data["value"], data["rule_type"], data["description"])
        log_action(request.user, "规则配置", "新增规则", f"{row.key}={row.value}", request)
        return Response(schemas.rule_dict(row), status=201)


class RuleDetailView(APIView):
    permission_classes = [require_perm("rule.write")]

    def put(self, request, pk):
        row = RuleConfig.objects.filter(pk=pk).first()
        if row is None:
            raise BizError("规则不存在", code=40400, http_status=404)
        serializer = RuleSerializer(data={**request.data, "key": row.key})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        row.value = data["value"]
        row.rule_type = data["rule_type"]
        row.description = data.get("description") or row.description
        row.save()
        rules.invalidate_rule_cache()  # 修改后删缓存键，读时回填
        log_action(request.user, "规则配置", "修改规则", f"{row.key}={row.value}", request)
        return Response(schemas.rule_dict(row))


# ---------- 11. 争议仲裁 ----------
class AdminAppealListView(APIView):
    permission_classes = [require_perm("appeal.arbitrate")]

    def get(self, request):
        qs = Appeal.objects.select_related("order", "initiator", "respondent", "handler")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return paginate(self, qs.order_by("-id"), request, schemas.appeal_dict)


class AdminAppealArbitrateView(APIView):
    permission_classes = [require_perm("appeal.arbitrate")]

    def post(self, request, pk):
        serializer = ArbitrateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appeal = Appeal.objects.filter(pk=pk).first()
        if appeal is None:
            raise BizError("申诉不存在", code=40400, http_status=404)
        data = serializer.validated_data
        appeal = order_services.arbitrate(appeal, request.user, data["winner"], data["student_ratio"], data["remark"])
        log_action(
            request.user, "争议仲裁", "仲裁出账",
            f"申诉#{appeal.pk} 订单{appeal.order.order_no} 学生比例 {appeal.student_ratio}%", request,
        )
        return Response(schemas.appeal_dict(appeal))


# ---------- 12. 数据统计 ----------
class StatsOverviewView(APIView):
    permission_classes = [require_perm("stats.view")]

    def get(self, request):
        total = Order.objects.count()
        completed = Order.objects.filter(status=Order.Status.COMPLETED).count()
        account = PlatformAccount.load()
        return Response(
            {
                "order_total": total,
                "order_completed": completed,
                "complete_rate": round(completed / total, 4) if total else 0.0,
                "status_distribution": list(
                    Order.objects.values("status").annotate(count=Count("id")).order_by("-count")
                ),
                "user_total": User.objects.filter(role=User.Role.USER).count(),
                "runner_total": User.objects.filter(is_runner=True).count(),
                "pending_certifications": User.objects.filter(cert_status=User.CertStatus.PENDING).count(),
                "pending_withdrawals": Withdrawal.objects.filter(status=Withdrawal.Status.PENDING).count(),
                "pending_appeals": Appeal.objects.filter(status=Appeal.Status.PENDING).count(),
                "abnormal_orders": Order.objects.filter(status=Order.Status.ABNORMAL).count(),
                "escrow_total": schemas.s(account.escrow_total),
                "total_paid": schemas.s(account.total_paid),
                "total_settled": schemas.s(account.total_settled),
                "total_refunded": schemas.s(account.total_refunded),
                "avg_credit": round(User.objects.filter(role=User.Role.USER).aggregate(a=Avg("credit_score"))["a"] or 0, 2),
                "fund_flows": [
                    {"type": f["type"], "amount": schemas.s(f["amount"]), "count": f["count"]}
                    for f in FundFlow.objects.values("type").annotate(amount=Sum("amount"), count=Count("id")).order_by("type")
                ],
            }
        )


class StatsOrdersTrendView(APIView):
    permission_classes = [require_perm("stats.view")]

    def get(self, request):
        try:
            days = min(int(request.query_params.get("days", 7)), 90)
        except ValueError:
            days = 7
        start = (timezone.now() - timedelta(days=days - 1)).date()
        rows = (
            Order.objects.filter(created_at__date__gte=start)
            .annotate(day=__import__("django").db.models.functions.TruncDate("created_at"))
            .values("day")
            .annotate(created=Count("id"), completed=Count("id", filter=Q(status=Order.Status.COMPLETED)))
            .order_by("day")
        )
        data = {str(r["day"]): r for r in rows}
        out = []
        for i in range(days):
            day = str(start + timedelta(days=i))
            row = data.get(day, {"created": 0, "completed": 0})
            out.append({"date": day, "created": row["created"], "completed": row["completed"]})
        return Response(out)


class StatsCreditDistributionView(APIView):
    permission_classes = [require_perm("stats.view")]

    def get(self, request):
        buckets = {"优秀(≥90)": 0, "良好(80-89)": 0, "一般(60-79)": 0, "受限(<60)": 0}
        for score in User.objects.filter(role=User.Role.USER).values_list("credit_score", flat=True):
            level = credit_services.level_of(score)
            key = {"excellent": "优秀(≥90)", "good": "良好(80-89)", "normal": "一般(60-79)", "limited": "受限(<60)"}[level]
            buckets[key] += 1
        flows = (
            FundFlow.objects.values("type").annotate(amount=Sum("amount"), count=Count("id")).order_by("type")
        )
        return Response(
            {
                "levels": [{"name": k, "value": v} for k, v in buckets.items()],
                "funds": [{"type": f["type"], "amount": schemas.s(f["amount"]), "count": f["count"]} for f in flows],
            }
        )


class ReconcileView(APIView):
    permission_classes = [require_perm("stats.view")]

    def post(self, request):
        result = reconcile()
        log_action(request.user, "对账", "手动对账", result["detail"], request)
        return Response(result)


# ---------- 13. 公告与操作日志 ----------
class AnnouncementListCreateView(APIView):
    permission_classes = [require_perm("announce.view")]

    def get(self, request):
        qs = Announcement.objects.select_related("publisher")
        return paginate(self, qs.order_by("-id"), request,
                        lambda a: {"id": a.id, "title": a.title, "content": a.content,
                                   "publisher": a.publisher.name or a.publisher.username, "created_at": schemas.dt(a.created_at)})

    def post(self, request):
        if not request.user.is_super_admin:
            raise BizError("仅超级管理员可发布公告", code=40300, http_status=403)
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        announcement = Announcement.objects.create(title=data["title"], content=data["content"], publisher=request.user)
        users = list(User.objects.filter(role=User.Role.USER))
        notify_many(users, f"公告：{data['title']}", data["content"][:200], kind=Notification.Kind.ANNOUNCEMENT)
        log_action(request.user, "公告", "发布公告", data["title"], request)
        return Response({"id": announcement.id, "delivered": len(users)}, status=201)


class AnnouncementDeleteView(APIView):
    permission_classes = [require_perm("announce.write")]

    def delete(self, request, pk):
        deleted, _ = Announcement.objects.filter(pk=pk).delete()
        log_action(request.user, "公告", "删除公告", f"公告#{pk}", request)
        return Response({"deleted": deleted})


class OperationLogListView(APIView):
    permission_classes = [require_perm("log.view")]

    def get(self, request):
        qs = OperationLog.objects.select_related("operator")
        if request.query_params.get("module"):
            qs = qs.filter(module=request.query_params["module"])
        return paginate(self, qs.order_by("-id"), request, schemas.log_dict)


class OperationLogExportView(APIView):
    permission_classes = [require_perm("log.view")]

    def get(self, request):
        rows = [
            [l.id, (l.operator.name or l.operator.username) if l.operator_id else "系统", l.module, l.action, l.detail, l.ip or "", schemas.dt(l.created_at)]
            for l in OperationLog.objects.select_related("operator").order_by("-id")[:5000]
        ]
        return csv_response("operation_logs.csv", ["ID", "操作人", "模块", "动作", "详情", "IP", "时间"], rows)
