from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error(_request: Request, exc: APIError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Do not echo uploaded content, personal messages or credentials from invalid input.
        return error_response(422, "invalid_request", "The request contains invalid or missing fields.")

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return error_response(
            503, "database_unavailable", "PostgreSQL is unavailable. Check its status and migrations."
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(404, "not_found", "This resource was not found.")
        if exc.status_code == 413:
            return error_response(413, "image_too_large", "The image exceeds the upload size limit.")
        return error_response(exc.status_code, "http_error", "This request could not be completed.")
