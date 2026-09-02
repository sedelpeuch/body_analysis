"""Handlers d'erreurs HTTP au format RFC 9457."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import DomainError

PROBLEM_MEDIA_TYPE = "application/problem+json"


def _problem(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    **extra: object,
) -> JSONResponse:
    body = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
        **extra,
    }
    return JSONResponse(
        jsonable_encoder(body),
        status_code=status_code,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Traduit les exceptions de domaine et les erreurs HTTP en problem+json."""

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            request,
            status_code=exc.status_code,
            title=exc.title,
            detail=str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        return _problem(
            request,
            status_code=422,
            title="Paramètres invalides",
            detail="La requête ne respecte pas le schéma attendu.",
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _starlette_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return _problem(
            request,
            status_code=exc.status_code,
            title="Erreur HTTP",
            detail=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        return _problem(
            request,
            status_code=500,
            title="Erreur interne",
            detail="Une erreur inattendue est survenue.",
        )
