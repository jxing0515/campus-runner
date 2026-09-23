"""API 路由：/api/v1/ 下全部端点。"""
from django.urls import path

from apps.accounts import api as accounts_api
from apps.common import admin_api, api as common_api
from apps.credit import api as credit_api
from apps.finance import api as finance_api
from apps.orders import api as orders_api

urlpatterns = [
    # 认证
    path("auth/register", accounts_api.RegisterView.as_view()),
    path("auth/login", accounts_api.LoginView.as_view()),
    path("auth/refresh", accounts_api.RefreshView.as_view()),
    path("auth/logout", accounts_api.LogoutView.as_view()),
    path("auth/me", accounts_api.MeView.as_view()),
    path("auth/password", accounts_api.ChangePasswordView.as_view()),
    path("stats/me", accounts_api.StatsView.as_view()),
    # 文件与消息
    path("files", common_api.FileUploadView.as_view()),
    path("files/<int:pk>", common_api.FileDownloadView.as_view()),
    path("notifications", common_api.NotificationListView.as_view()),
    path("notifications/read-all", common_api.NotificationReadAllView.as_view()),
    path("notifications/<int:pk>/read", common_api.NotificationReadView.as_view()),
    path("announcements", common_api.AnnouncementListView.as_view()),
    # 信用与认证
    path("credit/me", credit_api.CreditMeView.as_view()),
    path("credit/logs", credit_api.CreditLogListView.as_view()),
    path("runner/certification", accounts_api.CertificationView.as_view()),
    path("runner/income", finance_api.IncomeView.as_view()),
    path("runner/withdrawals", finance_api.WithdrawalListCreateView.as_view()),
    # 订单
    path("orders", orders_api.OrderListCreateView.as_view()),
    path("orders/available", orders_api.AvailableOrderListView.as_view()),
    path("orders/reviews/received", orders_api.ReceivedReviewView.as_view()),
    path("orders/<str:order_no>", orders_api.OrderDetailView.as_view()),
    path("orders/<str:order_no>/pay", orders_api.OrderPayView.as_view()),
    path("orders/<str:order_no>/cancel", orders_api.OrderCancelView.as_view()),
    path("orders/<str:order_no>/confirm", orders_api.OrderConfirmView.as_view()),
    path("orders/<str:order_no>/review", orders_api.OrderReviewView.as_view()),
    path("orders/<str:order_no>/appeal", orders_api.OrderAppealView.as_view()),
    path("orders/<str:order_no>/accept", orders_api.OrderAcceptView.as_view()),
    path("orders/<str:order_no>/pickup", orders_api.OrderPickupView.as_view()),
    path("orders/<str:order_no>/deliver", orders_api.OrderDeliverView.as_view()),
    # 管理端
    path("admin/certifications", admin_api.CertificationListView.as_view()),
    path("admin/certifications/<int:pk>/audit", admin_api.CertificationAuditView.as_view()),
    path("admin/users", admin_api.AdminUserListView.as_view()),
    path("admin/users/<int:pk>/ban", admin_api.UserBanView.as_view()),
    path("admin/users/<int:pk>/credit", admin_api.UserCreditView.as_view()),
    path("admin/demands", admin_api.AdminDemandListView.as_view()),
    path("admin/orders", admin_api.AdminOrderListView.as_view()),
    path("admin/orders/<str:order_no>", admin_api.AdminOrderDetailView.as_view()),
    path("admin/orders/<str:order_no>/resolve", admin_api.AdminOrderResolveView.as_view()),
    path("admin/fund-flows", admin_api.FundFlowListView.as_view()),
    path("admin/fund-flows/export", admin_api.FundFlowExportView.as_view()),
    path("admin/escrow", admin_api.EscrowView.as_view()),
    path("admin/settlements", admin_api.SettlementListView.as_view()),
    path("admin/refunds", admin_api.RefundListView.as_view()),
    path("admin/withdrawals", admin_api.AdminWithdrawalListView.as_view()),
    path("admin/withdrawals/<int:pk>/audit", admin_api.AdminWithdrawalAuditView.as_view()),
    path("admin/rules", admin_api.RuleListCreateView.as_view()),
    path("admin/rules/<int:pk>", admin_api.RuleDetailView.as_view()),
    path("admin/appeals", admin_api.AdminAppealListView.as_view()),
    path("admin/appeals/<int:pk>/arbitrate", admin_api.AdminAppealArbitrateView.as_view()),
    path("admin/stats/overview", admin_api.StatsOverviewView.as_view()),
    path("admin/stats/orders-trend", admin_api.StatsOrdersTrendView.as_view()),
    path("admin/stats/credit-distribution", admin_api.StatsCreditDistributionView.as_view()),
    path("admin/reconcile", admin_api.ReconcileView.as_view()),
    path("admin/announcements", admin_api.AnnouncementListCreateView.as_view()),
    path("admin/announcements/<int:pk>", admin_api.AnnouncementDeleteView.as_view()),
    path("admin/operation-logs", admin_api.OperationLogListView.as_view()),
    path("admin/operation-logs/export", admin_api.OperationLogExportView.as_view()),
]
