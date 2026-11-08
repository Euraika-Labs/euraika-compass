from starlette.exceptions import HTTPException

from compass.errors import error_response


class UploadLimitExceeded(HTTPException):
    def __init__(self):
        super().__init__(status_code=413, detail="The image exceeds the upload size limit.")


class UploadBodyLimitMiddleware:
    """Bound multipart bytes before Starlette can spool an unbounded file to disk."""

    def __init__(self, app, max_upload_bytes: int):
        self.app = app
        # Allow a small multipart envelope in addition to the actual image limit.
        self.limit = max_upload_bytes + 64 * 1024

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST" or scope.get("path") != "/api/v1/images":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = 0
        if length > self.limit:
            await error_response(413, "image_too_large", "The image exceeds the upload size limit.")(scope, receive, send)
            return
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            event = await receive()
            if event["type"] == "http.request":
                consumed += len(event.get("body", b""))
                if consumed > self.limit:
                    raise UploadLimitExceeded
            return event

        try:
            await self.app(scope, bounded_receive, send)
        except UploadLimitExceeded:
            await error_response(413, "image_too_large", "The image exceeds the upload size limit.")(scope, receive, send)
