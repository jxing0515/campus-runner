"""初始化演示数据：三角色账号 + 全状态样例订单 + 规则配置 + 公告。

用法：python manage.py seed_demo [--reset]
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common import rules
from apps.common.models import Announcement, Notification
from apps.common.notify import notify_many
from apps.finance import services as finance
from apps.finance.models import Withdrawal
from apps.orders import services
from apps.orders import state as order_state
from apps.orders.models import Order

PASSWORDS = {"admin": "Admin@123", "operator": "Admin@123", "student": "Student@123", "runner": "Runner@123"}


class Command(BaseCommand):
    help = "初始化演示账号、规则配置与全状态样例订单"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="先清空业务数据（不含管理员）")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("清空业务数据…")
            Order.objects.all().delete()
            User.objects.filter(role=User.Role.USER).delete()
            Withdrawal.objects.all().delete()

        rules.ensure_default_rules()
        admin = self._user("admin", User.Role.ADMIN, User.AdminLevel.SUPER, "系统管理员")
        operator = self._user("operator", User.Role.ADMIN, User.AdminLevel.OPERATOR, "运营管理员")
        students = [self._user(f"s00{i}", User.Role.USER, name=f"学生{i}") for i in range(1, 4)]
        runners = [self._runner(f"r00{i}", f"跑腿员{i}") for i in range(1, 3)]

        made = []
        # 全状态样例
        made.append(self._build("pending_pay", students[0], mode="platform", item_fee=Decimal("15.00")))
        made.append(self._build("pending_accept", students[0], mode="none"))
        made.append(self._build("accepted", students[1], runners[0], mode="none"))
        made.append(self._build("delivering", students[1], runners[0], mode="offline"))
        made.append(self._build("pending_confirm", students[2], runners[1], mode="platform", item_fee=Decimal("20.00")))
        made.append(self._build("completed", students[0], runners[0], mode="none"))
        made.append(self._build("completed", students[1], runners[1], mode="platform", item_fee=Decimal("12.00"), actual=Decimal("9.50")))
        made.append(self._build("cancelled", students[2], mode="none", runner=runners[0]))
        made.append(self._build("appealing", students[0], runners[1], mode="platform", item_fee=Decimal("18.00")))
        made.append(self._build("abnormal", students[1], runners[1], mode="offline"))

        # 提现：待审 / 通过 / 驳回
        self._withdrawals(runners[0], operator, admin)
        # 公告 + 通知投递
        ann = Announcement.objects.create(title="平台使用说明", content="本系统所有资金均为模拟记账，无真实交易。", publisher=admin)
        notify_many(list(User.objects.filter(role=User.Role.USER)), f"公告：{ann.title}", ann.content[:200],
                    kind=Notification.Kind.ANNOUNCEMENT)

        self.stdout.write(self.style.SUCCESS(
            f"完成：管理员 2、学生 {len(students)}、跑腿员 {len(runners)}、样例订单 {len(made)} 笔"
        ))
        self.stdout.write(f"  超级管理员 {admin.username}/{PASSWORDS['admin']}；运营管理员 {operator.username}/{PASSWORDS['operator']}")
        self.stdout.write(f"  学生 {students[0].username}/{PASSWORDS['student']}；跑腿员 {runners[0].username}/{PASSWORDS['runner']}")

    # ---- helpers ----
    def _user(self, username, role, admin_level=User.AdminLevel.NONE, name=""):
        user, _ = User.objects.get_or_create(username=username)
        user.role = role
        user.admin_level = admin_level
        user.name = name or username
        user.credit_score = user.credit_score or 100
        user.is_staff = role == User.Role.ADMIN
        user.is_superuser = admin_level == User.AdminLevel.SUPER
        user.set_password(PASSWORDS["admin" if role == User.Role.ADMIN else "student"])
        user.save()
        return user

    def _runner(self, username, name):
        user = self._user(username, User.Role.USER, name=name)
        user.student_no = f"2021{username[-3:]}"
        user.cert_status = User.CertStatus.APPROVED
        user.set_password(PASSWORDS["runner"])
        user.save()
        user.sync_runner_flag()
        return user

    def _order(self, student, runner=None, mode="none", item_fee=Decimal("0.00"), actual=None):
        now = timezone.now()
        return Order.objects.create(
            order_no=services.new_order_no(),
            student=student,
            runner=runner,
            description="演示订单：代取包裹并送到宿舍楼下",
            pickup_address="菜鸟驿站 A 区 3 号柜",
            delivery_address="学生公寓 5 号楼 302",
            time_window_start=now + timedelta(hours=1),
            time_window_end=now + timedelta(hours=3),
            runner_fee=Decimal("6.00"),
            item_fee_mode=mode,
            item_fee_estimate=item_fee,
            actual_item_fee=actual,
            status=Order.Status.PENDING_PAY,
        )

    def _build(self, stage, student, runner=None, mode="none", item_fee=Decimal("0.00"), actual=None):
        order = self._order(student, None, mode, item_fee, actual)
        no = order.order_no
        if stage == "pending_pay":
            return order
        services.pay(student, no)
        if stage == "pending_accept":
            return Order.objects.get(order_no=no)
        if stage == "cancelled":
            services.cancel(student, no, "演示：主动取消（未接单前）")
            return Order.objects.get(order_no=no)
        services.accept(runner, no)
        if stage == "accepted":
            return Order.objects.get(order_no=no)
        services.pickup(runner, no)
        if stage == "delivering":
            return Order.objects.get(order_no=no)
        if mode == Order.ItemFeeMode.PLATFORM:
            services.deliver(runner, no, actual_item_fee=actual if actual is not None else item_fee)
        else:
            services.deliver(runner, no)
        if stage == "pending_confirm":
            return Order.objects.get(order_no=no)
        if stage == "abnormal":
            order = Order.objects.get(order_no=no)
            order_state.transition(order, Order.Status.ABNORMAL, None, "演示：超时未确认且无送达凭证")
            return order
        services.confirm(student, no)
        if stage == "appealing":
            services.appeal(student, no, "dispute", "演示申诉：物品费与预估不符，申请仲裁")
            return Order.objects.get(order_no=no)
        order = Order.objects.get(order_no=no)
        if stage == "completed":
            services.review(student, no, 5, "送达及时，感谢！")
            if runner:
                services.review(runner, no, 5, "沟通顺畅，配合很好")
        return order

    def _withdrawals(self, runner, operator, admin):
        runner.refresh_from_db()
        if runner.runner_balance <= 0:
            return
        first = finance.apply_withdrawal(runner, Decimal("1.00"), "模拟收款", "demo-alipay-001")
        finance.audit_withdrawal(first, True, "演示：审核通过", admin)
        second = finance.apply_withdrawal(runner, Decimal("0.50"), "模拟收款", "demo-alipay-002")
        finance.audit_withdrawal(second, False, "演示：账号信息不符，驳回", operator)
        if runner.runner_balance > Decimal("0.10"):
            finance.apply_withdrawal(runner, Decimal("0.10"), "模拟收款", "demo-alipay-003")
