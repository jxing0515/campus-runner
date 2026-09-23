from rest_framework.renderers import JSONRenderer

SKIP_PREFIXES = ("/api/schema", "/api/docs")


class EnvelopeJSONRenderer(JSONRenderer):
    """统一响应信封：{"code":0,"message":"ok","data":...}"""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        ctx = renderer_context or {}
        request = ctx.get("request")
        response = ctx.get("response")
        if request is not None and str(request.path).startswith(SKIP_PREFIXES):
            return super().render(data, accepted_media_type, renderer_context)
        if isinstance(data, dict) and "code" in data and "message" in data:
            return super().render(data, accepted_media_type, renderer_context)
        if response is not None and response.status_code >= 400:
            payload = {"code": 40001 if response.status_code < 500 else 50000, "message": "请求失败", "data": data}
        else:
            payload = {"code": 0, "message": "ok", "data": data}
        return super().render(payload, accepted_media_type, renderer_context)
