"""Error responses in the shape the API contract promises:

- every error: {"detail": "..."}
- validation errors (422): {"detail": "<first error>", "errors": [{"field", "message"}]}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class FieldError(Exception):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def _validation_response(errors: list[dict]) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"detail": errors[0]["message"], "errors": errors}
    )


def _field_name(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or "body"


def _message(err: dict) -> str:
    msg = str(err.get("msg", "Invalid value"))
    # Pydantic prefixes errors raised by our own validators with "Value error, ".
    return msg.removeprefix("Value error, ")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": _field_name(tuple(err.get("loc", ()))), "message": _message(err)}
            for err in exc.errors()
        ]
        return _validation_response(errors or [{"field": "body", "message": "Invalid request"}])

    @app.exception_handler(FieldError)
    async def _field_error(_: Request, exc: FieldError) -> JSONResponse:
        return _validation_response([{"field": exc.field, "message": exc.message}])
