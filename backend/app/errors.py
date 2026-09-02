"""Hiérarchie d'exceptions du domaine et traduction RFC 9457.

Établi par ce plan car c'est le premier à poser des routes d'écriture. Tout
plan qui ajoute des endpoints — lecture ou front — réutilise ce module au
lieu d'en recréer un : `register_error_handlers` doit être appelé une seule
fois, dans `app.main.create_app`.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"


class DomainError(Exception):
    """Base de toutes les erreurs métier traduites en RFC 9457."""

    status_code: int = 500
    title: str = "Erreur interne"

    def __init__(self, detail: str, **extra: object) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class NotFoundError(DomainError):
    status_code = 404
    title = "Ressource introuvable"


class ValidationError(DomainError):
    status_code = 422
    title = "Requête invalide"


class ConflictError(DomainError):
    status_code = 409
    title = "Conflit"


class UnsupportedMediaTypeError(DomainError):
    status_code = 415
    title = "Type de fichier non supporté"


class PayloadTooLargeError(DomainError):
    status_code = 413
    title = "Fichier trop volumineux"


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


def register_error_handlers(app: FastAPI) -> None:
    """Enregistre les handlers qui font que toute réponse d'erreur est du
    application/problem+json."""

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            request,
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            **exc.extra,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _problem(
            request,
            status_code=422,
            title="Requête invalide",
            detail="La requête ne respecte pas le schéma attendu.",
            errors=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(
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
