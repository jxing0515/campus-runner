"""文件受控上传下载、消息通知、公告查看。"""
import os

from django.conf import settings
from django.http import FileResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import schemas
from apps.common.errors import BizError
from apps.common.models import Announcement, FileAsset, Notification
from apps.common.pagination import StandardPagination
from apps.common.serializers import FileUploadSerializer
from apps.accounts.authentication import QueryTokenJWTAuthentication

ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
SIGNATURES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}


class FileUploadView(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        if upload.size > settings.UPLOAD_MAX_BYTES:
            raise BizError("文件大小超过 2MB 限制")
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in ALLOWED_EXT:
            raise BizError("仅支持 jpg / png 图片")
        head = upload.read(8)
        upload.seek(0)
        if not any(head.startswith(sig) for sig in SIGNATURES):
            raise BizError("文件内容与图片格式不符")
        asset = FileAsset.objects.create(
            file=upload,
            name=os.path.basename(upload.name)[:128],
            kind=serializer.validated_data["kind"],
            uploader=request.user,
            size=upload.size,
            target=serializer.validated_data.get("target", ""),
        )
        return Response(schemas.file_dict(asset), status=201)


class FileDownloadView(APIView):
    """受控访问：凭证/学生证仅本人与管理员可下载，不开放裸 MEDIA 目录。"""

    authentication_classes = [QueryTokenJWTAuthentication]

    def get(self, request, pk):
        asset = FileAsset.objects.filter(pk=pk).first()
        if asset is None:
            raise BizError("文件不存在", code=40400, http_status=404)
        if asset.uploader_id != request.user.id and not request.user.is_admin and asset.kind != FileAsset.Kind.EVIDENCE:
            raise BizError("无权访问该文件", code=40300, http_status=403)
        if asset.target:
            from apps.orders.models import Order

            order = Order.objects.filter(order_no=asset.target).first()
            if order and request.user.id not in (order.student_id, order.runner_id) and not request.user.is_admin:
                raise BizError("无权访问该文件", code=40300, http_status=403)
        return FileResponse(asset.file.open("rb"), filename=asset.name)


class NotificationListView(APIView):
    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        if request.query_params.get("unread") in ("1", "true"):
            qs = qs.filter(is_read=False)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([schemas.notification_dict(n) for n in page])


class NotificationReadView(APIView):
    def post(self, request, pk):
        Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
        return Response({"detail": "已读"})


class NotificationReadAllView(APIView):
    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"updated": count})


class AnnouncementListView(APIView):
    def get(self, request):
        qs = Announcement.objects.all()[:20]
        return Response(
            [{"id": a.id, "title": a.title, "content": a.content, "created_at": schemas.dt(a.created_at)} for a in qs]
        )
