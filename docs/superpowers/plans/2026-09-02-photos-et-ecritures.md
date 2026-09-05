# Photos et écritures — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stocker les photos de suivi dans MinIO et les servir depuis le back
(dérivés mis en cache, flou serveur, correction de l'orientation EXIF),
exposer le CRUD des phases, et rendre l'import d'un export Samsung Health
possible par HTTP avec suivi de progression — le tout avec des erreurs au
format RFC 9457.

**Architecture:** Trois surfaces d'écriture indépendantes partageant la même
frontière `storage/` → `services/` → `api/` déjà esquissée dans la spec.
`storage/minio.py` est le seul point de contact avec le SDK MinIO — mockable,
donc testable en dehors de MinIO. `services/photo_image.py` est un module de
calcul pur (octets en, octets out) qui ne connaît ni la base ni MinIO, sur le
modèle des `analytics/` de la spec. L'import ZIP réutilise tel quel
`discover_source` et `run_ingestion` du plan précédent ; le seul changement
apporté à `pipeline.py` est un paramètre additif (`run: IngestionRun | None`)
qui permet de créer la ligne `ingestion_run` avant l'extraction, pour qu'un
identifiant soit disponible dès la réponse HTTP, sans dupliquer la logique
d'ingestion.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 asynchrone, asyncpg,
Pillow, MinIO SDK, pytest, pytest-asyncio, httpx (`AsyncClient` +
`ASGITransport`), zipfile et hashlib de la bibliothèque standard. Aucune
nouvelle dépendance : `minio>=7.2` et `pillow>=11.0` sont déjà dans
`backend/pyproject.toml` depuis le plan « Socle et ingestion ».

**Spec:** `docs/superpowers/specs/2026-09-02-migration-fastapi-react-design.md`
(sections 4.3, 4.10, 6 « Phases », « Photos », « Imports », 7 « Flux
d'ingestion »).

## Global Constraints

- Python `>=3.13`. Aucun code compatible 3.11 requis.
- Planchers de dépendances, jamais de versions figées. Ce plan n'ajoute
  aucune dépendance à `backend/pyproject.toml`.
- **Aucun identifiant en dur dans le code.** `BA_DATABASE_URL`,
  `BA_MINIO_ACCESS_KEY` et `BA_MINIO_SECRET_KEY` restent obligatoires et sans
  valeur par défaut.
- **Une valeur absente est `None`, jamais `0` ni `NaN`.**
- **Tous les horodatages sont conservés avec leur fuseau** (`TIMESTAMPTZ`).
- Le code, les noms de tables et de colonnes, les messages de commit sont en
  anglais. Les commentaires et la documentation sont en français.
- Les données réelles ne sont jamais modifiées : `scripts/seed_photos.py` ne
  fait que lire `/home/sedelpeuch/migration_body-analysis/photos/`.
- **Le back sert toujours les images lui-même**, jamais par URL présignée.
  Le front ne connaît jamais l'existence de MinIO.
- **Toutes les erreurs suivent la RFC 9457** (`application/problem+json`),
  y compris les erreurs de validation Pydantic et les 404 de routage — pas
  seulement les exceptions du domaine.
- **L'archive ZIP d'import est une entrée non fiable** : zip-slip et bombe de
  décompression sont bloqués avant qu'un octet ne soit écrit au-delà des
  seuils, avec des tests qui construisent une archive malveillante.
- Le contenu d'une photo envoyée est validé par inspection des octets, jamais
  par le Content-Type déclaré ni par l'extension.

## État réel du code au démarrage de ce plan

Le plan « Socle et ingestion » est en cours (11/14 tâches). Existant et
testé, que ce plan consomme sans le modifier sauf mention contraire :

- `app.config.Settings` / `app.config.settings` — `database_url`,
  `minio_endpoint`, `minio_access_key`, `minio_secret_key`, `minio_bucket`,
  `minio_secure`.
- `app.db.engine`, `app.db.session_factory`, `app.db.get_session()`.
- `app.models.Photo` — `id`, `taken_on: date`, `tag: str`,
  `object_key: str`, `sha256: str` (unique), `width`, `height`, `byte_size`,
  `content_type`, contrainte unique `(taken_on, tag)`.
- `app.models.Phase`, `app.models.PhaseKind` (`free|bulk|cut|maintain`) —
  `starts_on`, `ends_on` (CHECK `ends_on >= starts_on`, aucune exclusion de
  chevauchement), quatre colonnes d'objectifs nullables, `notes`.
- `app.models.IngestionRun`, `app.models.IngestionStatus`
  (`running|success|failed`) — `kind`, `source_name`, `started_at`,
  `finished_at`, `counts: dict | None` (JSONB), `error: str | None`.
- `app.ingestion.samsung.pipeline` :
  `SamsungSource` (dataclass : `weight_csv`, `food_csv`, `exercise_csv`,
  `exercise_dir`, `phases_json`, tous `Path | None`),
  `discover_source(root: Path) -> SamsungSource`,
  `run_ingestion(session, source, *, kind, source_name) -> IngestionRun`.
- `backend/tests/integration/conftest.py` : fixture `engine` (session-scope,
  `create_all` sur une base jetable désignée par `BA_TEST_DATABASE_URL`,
  défaut `postgresql+asyncpg://body:body-local-dev@localhost:5432/body_analysis_test`)
  et fixture `session`.
- `backend/pyproject.toml` :
  `asyncio_default_test_loop_scope = "session"`,
  `asyncio_default_fixture_loop_scope = "session"`. Ruff :
  `select = ["E","F","I","UP","B","SIM","RUF"]`, ligne 88, py313,
  `migrations/versions` exclu.
- `backend/tests/fixtures/samsung/weight_sample.csv`,
  `backend/tests/fixtures/phases.json` (utilisés par les tests
  d'intégration du pipeline).

Aucun de `app/api/`, `app/services/`, `app/schemas/`, `app/storage/` ni
`app/errors.py` n'existe encore : le plan « Analytics et API de lecture »
(incrément 4, endpoints corps/nutrition/entraînement) n'a pas encore tourné
au moment de la rédaction de ce plan. **Ce plan crée donc ces paquets et
`app/errors.py` en premier.** Si le plan de lecture s'exécute avant celui-ci,
son implémenteur doit fusionner ces paquets plutôt que les recréer, et
réutiliser `app.errors.register_error_handlers` / `DomainError` au lieu d'en
recréer une variante — c'est signalé explicitement dans les tâches 1, 4 et 7
ci-dessous.

## Chiffres de référence des données réelles

| Grandeur | Valeur |
| --- | --- |
| Photos | 85 |
| Dates distinctes | 21 |
| Tags | `face`, `profil`, `dos`, `bras`, `epaule` |
| Arborescence source | `photos/YYYY-MM-DD/<tag>.jpg` |
| Phases (déjà en base via le plan « Socle ») | 8 |
| Taille de l'export ZIP réel | 1,3 Go, 88 093 JSON + 87 CSV |

## Structure des fichiers

```
backend/app/
  errors.py                      DomainError et ses sous-classes, handlers RFC 9457
  db.py                          (Modify) + get_session_factory()
  storage/
    __init__.py
    minio.py                     client MinIO fin : put/get/exists/delete/delete_prefix
  services/
    __init__.py
    photo_image.py                traitement d'image pur : EXIF, empreinte, dérivés, flou
    photos.py                     orchestration photo : upload, service d'image, suppression
    phases.py                     orchestration phase : CRUD + validations
    imports.py                    orchestration import ZIP : run précoce, extraction, délégation
  schemas/
    __init__.py
    photos.py                     PhotoOut
    phases.py                     PhaseCreate, PhaseUpdate, PhaseOut
    imports.py                    IngestionRunOut
  api/
    __init__.py
    photos.py                     router /api/photos
    phases.py                     router /api/phases
    imports.py                    router /api/imports
  ingestion/
    zip_safety.py                 zip-slip et bombe de décompression
    samsung/pipeline.py           (Modify) run_ingestion accepte un run préexistant
  main.py                         (Modify) enregistrement des handlers et des routers
backend/scripts/
  seed_photos.py                  seed one-shot des 85 photos réelles, via le service photo
backend/tests/
  unit/
    test_errors.py
    test_photo_image.py
    test_zip_safety.py
  integration/
    conftest.py                   (Modify) + fixture minio_storage, + fixture session_factory
    test_minio_storage.py
    test_photos_service.py
    test_photos_api.py
    test_phases_service.py
    test_phases_api.py
    test_pipeline_reuses_run.py
    test_imports_service.py
    test_imports_api.py
```

Découpage assumé : `photo_image.py` reste séparé de `photos.py` pour la même
raison que `analytics/` reste séparé de `services/` dans la spec — c'est la
frontière testable sans infrastructure. `zip_safety.py` vit sous
`ingestion/` et non sous `services/` parce qu'il ne connaît que des chemins
et des octets, comme `parsers.py` ; `services/imports.py` l'utilise mais ne
le contient pas.

---

### Task 1: Hiérarchie d'erreurs de domaine et handlers RFC 9457

Cette tâche établit `app/errors.py`, consommé par toutes les tâches
suivantes de ce plan et par tout futur plan qui pose des routes.

**Files:**
- Create: `backend/app/errors.py`
- Create: `backend/tests/unit/test_errors.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `DomainError(detail: str, **extra: object)` — base, `status_code: int`,
    `title: str`.
  - `NotFoundError` (404), `ValidationError` (422), `ConflictError` (409),
    `UnsupportedMediaTypeError` (415), `PayloadTooLargeError` (413).
  - `register_error_handlers(app: FastAPI) -> None`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_errors.py` :

```python
"""Vérifie la traduction des erreurs en application/problem+json (RFC 9457)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
    register_error_handlers,
)

PROBLEM_MEDIA_TYPE = "application/problem+json"


class _Body(BaseModel):
    name: str


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/not-found")
    async def not_found() -> None:
        raise NotFoundError("Phase 42 introuvable")

    @app.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("sha256 déjà utilisé", sha256="abc")

    @app.get("/validation")
    async def validation() -> None:
        raise ValidationError("ends_on doit être postérieure à starts_on")

    @app.get("/unsupported")
    async def unsupported() -> None:
        raise UnsupportedMediaTypeError("Type non reconnu", allowed=["image/jpeg"])

    @app.get("/too-large")
    async def too_large() -> None:
        raise PayloadTooLargeError("Fichier trop volumineux")

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("panne imprévue")

    @app.post("/echo")
    async def echo(body: _Body) -> dict[str, str]:
        return {"name": body.name}

    return app


def _client() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


def test_domain_error_is_problem_json() -> None:
    response = _client().get("/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert body["status"] == 404
    assert body["title"] == "Ressource introuvable"
    assert body["detail"] == "Phase 42 introuvable"
    assert body["instance"] == "/not-found"


def test_domain_error_extra_fields_are_included() -> None:
    body = _client().get("/conflict").json()

    assert body["status"] == 409
    assert body["sha256"] == "abc"


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/validation", 422),
        ("/unsupported", 415),
        ("/too-large", 413),
    ],
)
def test_every_domain_error_maps_to_its_status(path: str, status: int) -> None:
    response = _client().get(path)

    assert response.status_code == status
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)


def test_pydantic_validation_error_is_problem_json() -> None:
    """Le handler par défaut de FastAPI renvoie du JSON simple ; RFC 9457
    exige application/problem+json même pour les erreurs de schéma."""
    response = _client().post("/echo", json={"name": 123, "extra": "trop"})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert body["title"] == "Requête invalide"
    assert isinstance(body["errors"], list)
    assert body["errors"]


def test_missing_route_is_problem_json() -> None:
    """Un 404 de routage Starlette doit lui aussi être traduit."""
    response = _client().get("/route-inexistante")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)


def test_unhandled_exception_is_problem_json_and_does_not_leak_details() -> None:
    response = _client().get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert "panne imprévue" not in body["detail"]
```

Ajouter `import pytest` en tête du fichier, avant les autres imports.

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_errors.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.errors'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/errors.py` :

```python
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
    request: Request, *, status_code: int, title: str, detail: str, **extra: object
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
        jsonable_encoder(body), status_code=status_code, media_type=PROBLEM_MEDIA_TYPE
    )


def register_error_handlers(app: FastAPI) -> None:
    """Enregistre les quatre handlers qui font que toute réponse d'erreur de
    l'API — domaine, validation Pydantic, routage Starlette, ou exception
    non prévue — est du application/problem+json."""

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
        request: Request, exc: RequestValidationError
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
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _problem(
            request, status_code=exc.status_code, title="Erreur HTTP", detail=str(exc.detail)
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        return _problem(
            request,
            status_code=500,
            title="Erreur interne",
            detail="Une erreur inattendue est survenue.",
        )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_errors.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/errors.py backend/tests/unit/test_errors.py
git commit -m "feat: add domain error hierarchy translated to RFC 9457"
```

---

### Task 2: Client MinIO

**Files:**
- Create: `backend/app/storage/__init__.py`
- Create: `backend/app/storage/minio.py`
- Create: `backend/tests/integration/test_minio_storage.py`
- Modify: `backend/tests/integration/conftest.py`

**Interfaces:**
- Consumes: `app.config.settings` (`minio_endpoint`, `minio_access_key`,
  `minio_secret_key`, `minio_bucket`, `minio_secure`).
- Produces:
  - `StoredObject` (dataclass : `data: bytes`, `content_type: str | None`)
  - `MinioStorage(config: Settings = settings)` avec `.put(key, data,
    content_type)`, `.get(key) -> StoredObject | None`, `.exists(key) ->
    bool`, `.delete(key) -> None`, `.delete_prefix(prefix) -> None`,
    `.is_reachable() -> bool`.
  - `get_storage() -> MinioStorage` — fournisseur singleton pour
    l'injection de dépendances FastAPI, surchargeable dans les tests via
    `app.dependency_overrides`.

- [ ] **Step 1: Écrire le test d'intégration et la fixture de disponibilité**

Ajouter à `backend/tests/integration/conftest.py`, à la suite du contenu
existant (fixtures `engine` et `session`) :

```python
import pytest

from app.storage.minio import MinioStorage


@pytest.fixture(scope="session")
def minio_storage() -> MinioStorage:
    """MinIO réel de compose. Sauté proprement s'il est injoignable, sur le
    même principe que la fixture engine pour BA_TEST_DATABASE_URL."""
    storage = MinioStorage()
    if not storage.is_reachable():
        pytest.skip("MinIO indisponible : lancer `docker compose up -d minio`")
    return storage
```

Créer `backend/tests/integration/test_minio_storage.py` :

```python
"""Tests d'intégration du client MinIO contre le service réel de compose."""

import pytest

from app.storage.minio import MinioStorage

TEST_PREFIX = "tests/minio-storage"


@pytest.fixture(autouse=True)
def _clean(minio_storage: MinioStorage):
    yield
    minio_storage.delete_prefix(TEST_PREFIX)


def test_put_then_get_roundtrips_bytes_and_content_type(minio_storage: MinioStorage) -> None:
    key = f"{TEST_PREFIX}/roundtrip.jpg"

    minio_storage.put(key, b"donnees-binaires", "image/jpeg")
    stored = minio_storage.get(key)

    assert stored is not None
    assert stored.data == b"donnees-binaires"
    assert stored.content_type == "image/jpeg"


def test_get_missing_key_returns_none(minio_storage: MinioStorage) -> None:
    assert minio_storage.get(f"{TEST_PREFIX}/absent.jpg") is None


def test_exists_reflects_presence(minio_storage: MinioStorage) -> None:
    key = f"{TEST_PREFIX}/exists.jpg"
    assert minio_storage.exists(key) is False

    minio_storage.put(key, b"x", "image/jpeg")

    assert minio_storage.exists(key) is True


def test_delete_removes_the_object(minio_storage: MinioStorage) -> None:
    key = f"{TEST_PREFIX}/to-delete.jpg"
    minio_storage.put(key, b"x", "image/jpeg")

    minio_storage.delete(key)

    assert minio_storage.exists(key) is False


def test_delete_missing_key_does_not_raise(minio_storage: MinioStorage) -> None:
    minio_storage.delete(f"{TEST_PREFIX}/jamais-cree.jpg")


def test_delete_prefix_removes_every_matching_object(minio_storage: MinioStorage) -> None:
    minio_storage.put(f"{TEST_PREFIX}/derived/thumb/a.jpg", b"1", "image/jpeg")
    minio_storage.put(f"{TEST_PREFIX}/derived/thumb/b.jpg", b"2", "image/jpeg")
    minio_storage.put(f"{TEST_PREFIX}/derived/full/a.jpg", b"3", "image/jpeg")

    minio_storage.delete_prefix(f"{TEST_PREFIX}/derived/thumb/")

    assert minio_storage.exists(f"{TEST_PREFIX}/derived/thumb/a.jpg") is False
    assert minio_storage.exists(f"{TEST_PREFIX}/derived/thumb/b.jpg") is False
    assert minio_storage.exists(f"{TEST_PREFIX}/derived/full/a.jpg") is True


def test_is_reachable_is_true_against_the_real_service(minio_storage: MinioStorage) -> None:
    assert minio_storage.is_reachable() is True


def test_bucket_is_created_on_first_use_if_absent(minio_storage: MinioStorage) -> None:
    """Le bucket configuré existe déjà dans un compose qui tourne depuis un
    moment ; ce test vérifie seulement que _ensure_bucket ne lève pas quand
    on l'appelle plusieurs fois de suite."""
    minio_storage.put(f"{TEST_PREFIX}/bucket-check.jpg", b"x", "image/jpeg")
    minio_storage.put(f"{TEST_PREFIX}/bucket-check-2.jpg", b"y", "image/jpeg")

    assert minio_storage.exists(f"{TEST_PREFIX}/bucket-check.jpg") is True
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_minio_storage.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.storage'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/storage/__init__.py` vide.

Créer `backend/app/storage/minio.py` :

```python
"""Client MinIO fin, unique point de contact avec le SDK MinIO.

Toute opération de stockage objet passe par MinioStorage : le reste de
l'application (services, routes) ne connaît jamais le SDK directement, ce
qui rend le stockage mockable dans les tests unitaires. Le bucket est créé
au premier usage s'il n'existe pas encore.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from minio import Minio
from minio.error import S3Error

from app.config import Settings, settings


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str | None


class MinioStorage:
    def __init__(self, config: Settings = settings) -> None:
        self._bucket = config.minio_bucket
        self._client = Minio(
            config.minio_endpoint,
            access_key=config.minio_access_key,
            secret_key=config.minio_secret_key,
            secure=config.minio_secure,
        )
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        self._bucket_ready = True

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get(self, key: str) -> StoredObject | None:
        self._ensure_bucket()
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as error:
            if error.code == "NoSuchKey":
                return None
            raise
        try:
            return StoredObject(
                data=response.read(),
                content_type=response.headers.get("Content-Type"),
            )
        finally:
            response.close()
            response.release_conn()

    def exists(self, key: str) -> bool:
        self._ensure_bucket()
        try:
            self._client.stat_object(self._bucket, key)
        except S3Error as error:
            if error.code == "NoSuchKey":
                return False
            raise
        return True

    def delete(self, key: str) -> None:
        """Idempotent : supprimer une clé absente ne lève pas, comme S3."""
        self._ensure_bucket()
        self._client.remove_object(self._bucket, key)

    def delete_prefix(self, prefix: str) -> None:
        self._ensure_bucket()
        for obj in self._client.list_objects(self._bucket, prefix=prefix, recursive=True):
            self._client.remove_object(self._bucket, obj.object_name)

    def is_reachable(self) -> bool:
        try:
            self._client.bucket_exists(self._bucket)
        except Exception:
            return False
        return True


_storage: MinioStorage | None = None


def get_storage() -> MinioStorage:
    """Fournisseur singleton pour Depends(). Surchargé dans les tests par
    app.dependency_overrides[get_storage]."""
    global _storage
    if _storage is None:
        _storage = MinioStorage()
    return _storage
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run:
```bash
docker compose up -d minio
cd backend && uv run pytest tests/integration/test_minio_storage.py -v
```
Expected: PASS, 9 tests (ou SKIPPED si MinIO n'est pas lancé — vérifier les
deux cas en arrêtant puis relançant `docker compose stop minio`)

- [ ] **Step 5: Commiter**

```bash
git add backend/app/storage backend/tests/integration/test_minio_storage.py \
  backend/tests/integration/conftest.py
git commit -m "feat: add thin minio storage client"
```

---

### Task 3: Traitement d'image pur — orientation EXIF, empreinte, dérivés, flou

Cette tâche corrige le bug documenté en section 6 de la spec (endpoint
photos) : la rotation historique se déclenchait sur `width > height`, ce qui
retournait à tort toute photo réellement prise en paysage.

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/photo_image.py`
- Create: `backend/tests/unit/test_photo_image.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `DERIVATIVE_SIZES: dict[str, int]` (`thumb: 320, medium: 800, full:
    1600`)
  - `sniff_content_type(data: bytes) -> str | None`
  - `sha256_of(data: bytes) -> str`
  - `NormalizedImage` (dataclass : `data: bytes`, `width: int`,
    `height: int`, `content_type: str`)
  - `normalize_orientation(data: bytes) -> NormalizedImage`
  - `make_derivative(normalized: bytes, *, max_dimension: int, blur: bool =
    False) -> bytes`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/test_photo_image.py` :

```python
"""Tests du traitement d'image pur : aucune base, aucun MinIO."""

import io

import pytest
from PIL import Image

from app.services.photo_image import (
    DERIVATIVE_SIZES,
    make_derivative,
    normalize_orientation,
    sha256_of,
    sniff_content_type,
)


def _jpeg_bytes(size: tuple[int, int], *, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, "red")
    buffer = io.BytesIO()
    if orientation is not None:
        exif = image.getexif()
        exif[0x0112] = orientation  # tag EXIF Orientation
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_bytes(size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size, "blue")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_sniff_content_type_recognizes_jpeg() -> None:
    assert sniff_content_type(_jpeg_bytes((10, 10))) == "image/jpeg"


def test_sniff_content_type_recognizes_png() -> None:
    assert sniff_content_type(_png_bytes((10, 10))) == "image/png"


def test_sniff_content_type_rejects_anything_else() -> None:
    assert sniff_content_type(b"pas une image, juste du texte") is None


def test_sniff_content_type_ignores_a_forged_extension_or_header() -> None:
    """Ne fait jamais confiance à ce qui accompagne les octets, seulement
    aux octets eux-mêmes."""
    fake_jpeg_named_file_content = b"<html>ceci n'est pas une image</html>"
    assert sniff_content_type(fake_jpeg_named_file_content) is None


def test_sha256_of_is_deterministic() -> None:
    data = b"mêmes octets"
    assert sha256_of(data) == sha256_of(data)
    assert sha256_of(data) != sha256_of(b"octets différents")


def test_normalize_orientation_does_not_rotate_a_true_landscape_photo() -> None:
    """Verrou de non-régression du bug corrigé : l'ancienne heuristique
    tournait toute image dont la largeur dépassait la hauteur, y compris une
    photo réellement prise en paysage sans besoin de rotation (orientation
    EXIF normale)."""
    landscape = _jpeg_bytes((120, 60), orientation=1)

    normalized = normalize_orientation(landscape)

    assert normalized.width == 120
    assert normalized.height == 60


def test_normalize_orientation_rotates_according_to_exif_tag() -> None:
    """Orientation 6 (rotation 90° horaire nécessaire) doit inverser les
    dimensions, indépendamment du fait que largeur > hauteur ou non."""
    tagged = _jpeg_bytes((120, 60), orientation=6)

    normalized = normalize_orientation(tagged)

    assert normalized.width == 60
    assert normalized.height == 120


def test_normalize_orientation_without_exif_leaves_dimensions_untouched() -> None:
    plain = _jpeg_bytes((60, 120))

    normalized = normalize_orientation(plain)

    assert normalized.width == 60
    assert normalized.height == 120


def test_normalize_orientation_always_returns_jpeg() -> None:
    normalized = normalize_orientation(_png_bytes((40, 40)))

    assert normalized.content_type == "image/jpeg"
    with Image.open(io.BytesIO(normalized.data)) as reopened:
        assert reopened.format == "JPEG"


@pytest.mark.parametrize("size_name", list(DERIVATIVE_SIZES))
def test_make_derivative_never_exceeds_its_target_dimension(size_name: str) -> None:
    source = _jpeg_bytes((3000, 1500))

    derivative = make_derivative(source, max_dimension=DERIVATIVE_SIZES[size_name])

    with Image.open(io.BytesIO(derivative)) as image:
        assert max(image.size) <= DERIVATIVE_SIZES[size_name]


def test_make_derivative_never_upscales() -> None:
    source = _jpeg_bytes((100, 50))

    derivative = make_derivative(source, max_dimension=DERIVATIVE_SIZES["full"])

    with Image.open(io.BytesIO(derivative)) as image:
        assert image.size == (100, 50)


def test_make_derivative_blur_changes_the_bytes() -> None:
    source = _jpeg_bytes((200, 200))

    sharp = make_derivative(source, max_dimension=200, blur=False)
    blurred = make_derivative(source, max_dimension=200, blur=True)

    assert sharp != blurred
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_photo_image.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/services/__init__.py` vide.

Créer `backend/app/services/photo_image.py` :

```python
"""Traitement d'image pur : octets en, octets out.

Ce module ne connaît ni la base ni MinIO — c'est ce qui le rend testable
sans infrastructure, sur le même principe que analytics/ dans la spec.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_CONTENT_TYPE_BY_MAGIC: tuple[tuple[bytes, str], ...] = (
    (_JPEG_MAGIC, "image/jpeg"),
    (_PNG_MAGIC, "image/png"),
)

DERIVATIVE_SIZES: dict[str, int] = {"thumb": 320, "medium": 800, "full": 1600}
_BLUR_RADIUS = 25
_JPEG_QUALITY = 90


@dataclass(frozen=True, slots=True)
class NormalizedImage:
    """Image dont l'orientation EXIF a été appliquée aux pixels."""

    data: bytes
    width: int
    height: int
    content_type: str


def sniff_content_type(data: bytes) -> str | None:
    """Détecte le vrai type d'image en inspectant les octets.

    Ne fait jamais confiance au Content-Type déclaré par le client ni à
    l'extension du fichier envoyé.
    """
    for magic, content_type in _CONTENT_TYPE_BY_MAGIC:
        if data.startswith(magic):
            return content_type
    return None


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_orientation(data: bytes) -> NormalizedImage:
    """Corrige la rotation selon l'orientation EXIF, jamais selon la forme.

    Bug corrigé : l'application historique tournait l'image dès que
    largeur > hauteur, ce qui inversait à tort toute photo réellement prise
    en paysage. ImageOps.exif_transpose lit le tag d'orientation EXIF et
    applique exactement la rotation qu'il décrit, ou aucune s'il est absent
    ou vaut 1 (normal).

    Le résultat est toujours réencodé en JPEG : les dérivés et le flou n'ont
    ainsi qu'un seul format à connaître.
    """
    with Image.open(io.BytesIO(data)) as opened:
        transposed = ImageOps.exif_transpose(opened) or opened
        rgb = transposed.convert("RGB")
        buffer = io.BytesIO()
        rgb.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
        return NormalizedImage(
            data=buffer.getvalue(),
            width=rgb.width,
            height=rgb.height,
            content_type="image/jpeg",
        )


def make_derivative(normalized: bytes, *, max_dimension: int, blur: bool = False) -> bytes:
    """Redimensionne sans jamais agrandir, et floute optionnellement.

    Le flou n'est jamais mis en cache par l'appelant : c'est un rendu à la
    demande du mode confidentiel, recalculé à chaque requête.
    """
    with Image.open(io.BytesIO(normalized)) as opened:
        image = opened.convert("RGB")
        image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
        if blur:
            image = image.filter(ImageFilter.GaussianBlur(_BLUR_RADIUS))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
        return buffer.getvalue()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_photo_image.py -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/services/__init__.py backend/app/services/photo_image.py \
  backend/tests/unit/test_photo_image.py
git commit -m "fix: derive photo rotation from EXIF orientation, not aspect ratio"
```

---

### Task 4: Service et schémas photo

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/photos.py`
- Create: `backend/app/services/photos.py`
- Create: `backend/tests/integration/test_photos_service.py`

**Interfaces:**
- Consumes: `app.models.Photo` ; `app.errors.{NotFoundError,
  UnsupportedMediaTypeError, ConflictError}` (tâche 1) ; `MinioStorage`
  (tâche 2) ; `DERIVATIVE_SIZES`, `make_derivative`, `normalize_orientation`,
  `sha256_of`, `sniff_content_type` (tâche 3).
- Produces:
  - `PhotoOut` (schéma Pydantic)
  - `ALLOWED_TAGS: frozenset[str]`
  - `async upload_photo(session, storage, *, taken_on: date, tag: str,
    raw_bytes: bytes) -> Photo`
  - `async list_photos(session, *, tag: str | None = None) -> list[Photo]`
  - `async delete_photo(session, storage, *, photo_id: int) -> None`
  - `async get_photo_image(session, storage, *, photo_id: int, size: str,
    blur: bool) -> tuple[bytes, str]`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/integration/test_photos_service.py` :

```python
"""Tests d'intégration du service photo : base réelle + MinIO réel."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError, UnsupportedMediaTypeError
from app.models import Photo
from app.services.photo_image import DERIVATIVE_SIZES, sha256_of
from app.services.photos import delete_photo, get_photo_image, list_photos, upload_photo
from app.storage.minio import MinioStorage

FIXTURES = __import__("pathlib").Path(__file__).parents[1] / "fixtures" / "photos"


def _jpeg(color: str = "red", size: tuple[int, int] = (200, 100)) -> bytes:
    import io

    from PIL import Image

    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(Photo.__table__.delete())
    await session.commit()
    yield


async def test_upload_creates_a_photo_with_derived_metadata(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    assert photo.id is not None
    assert photo.tag == "face"
    assert photo.taken_on == date(2026, 8, 31)
    assert photo.content_type == "image/jpeg"
    assert photo.width == 200
    assert photo.height == 100
    assert minio_storage.exists(photo.object_key) is True


async def test_upload_rejects_an_unknown_tag(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await upload_photo(
            session, minio_storage, taken_on=date(2026, 8, 31), tag="genou", raw_bytes=_jpeg()
        )


async def test_upload_rejects_content_that_is_not_an_image(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await upload_photo(
            session,
            minio_storage,
            taken_on=date(2026, 8, 31),
            tag="face",
            raw_bytes=b"pas une image",
        )


async def test_second_upload_for_same_date_and_tag_replaces_the_first(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    first = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg("red")
    )
    old_key = first.object_key

    replaced = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg("blue")
    )

    assert replaced.id == first.id
    photos = await list_photos(session, tag="face")
    assert len(photos) == 1
    assert minio_storage.exists(old_key) is False
    assert minio_storage.exists(replaced.object_key) is True


async def test_uploading_the_same_bytes_twice_is_a_no_op(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    data = _jpeg()
    first = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=data
    )
    second = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=data
    )

    assert first.id == second.id
    assert first.sha256 == second.sha256


async def test_upload_rejects_a_sha256_already_used_by_another_photo(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    data = _jpeg()
    await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=data
    )

    with pytest.raises(ConflictError):
        await upload_photo(
            session, minio_storage, taken_on=date(2026, 9, 1), tag="dos", raw_bytes=data
        )


async def test_list_photos_filters_by_tag(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg("red")
    )
    await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="dos", raw_bytes=_jpeg("blue")
    )

    assert len(await list_photos(session)) == 2
    assert len(await list_photos(session, tag="face")) == 1


async def test_delete_photo_removes_row_and_object(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    await delete_photo(session, minio_storage, photo_id=photo.id)

    assert (await session.execute(select(Photo))).scalars().all() == []
    assert minio_storage.exists(photo.object_key) is False


async def test_delete_unknown_photo_raises_not_found(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    with pytest.raises(NotFoundError):
        await delete_photo(session, minio_storage, photo_id=999999)


async def test_get_photo_image_generates_and_caches_the_derivative(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session,
        minio_storage,
        taken_on=date(2026, 8, 31),
        tag="face",
        raw_bytes=_jpeg(size=(2000, 1000)),
    )
    cache_key = f"derived/thumb/{photo.sha256}.jpg"
    assert minio_storage.exists(cache_key) is False

    data, content_type = await get_photo_image(
        session, minio_storage, photo_id=photo.id, size="thumb", blur=False
    )

    assert content_type == "image/jpeg"
    assert minio_storage.exists(cache_key) is True

    import io

    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        assert max(image.size) <= DERIVATIVE_SIZES["thumb"]


async def test_get_photo_image_blur_is_never_cached(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    sharp, _ = await get_photo_image(
        session, minio_storage, photo_id=photo.id, size="medium", blur=False
    )
    blurred, _ = await get_photo_image(
        session, minio_storage, photo_id=photo.id, size="medium", blur=True
    )

    assert sharp != blurred
    assert minio_storage.exists(f"derived/medium/{photo.sha256}.jpg") is True


async def test_get_photo_image_rejects_an_unknown_size(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    with pytest.raises(Exception):
        await get_photo_image(
            session, minio_storage, photo_id=photo.id, size="xxl", blur=False
        )
```

Créer un répertoire vide `backend/tests/fixtures/photos/` (non utilisé
directement par ce test, qui génère ses images en mémoire, mais réservé pour
les fixtures de la tâche seed) :

```bash
mkdir -p backend/tests/fixtures/photos
touch backend/tests/fixtures/photos/.gitkeep
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_photos_service.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.schemas'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/schemas/__init__.py` vide.

Créer `backend/app/schemas/photos.py` :

```python
"""Schémas Pydantic exposés par l'API photos."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    taken_on: date
    tag: str
    width: int | None
    height: int | None
    byte_size: int | None
    content_type: str | None
    created_at: datetime
```

Créer `backend/app/services/photos.py` :

```python
"""Service photo : upload, dérivés à la demande, suppression.

Fait le pont entre app.storage.minio (octets) et le modèle Photo (métadonnées
en base). Aucune route HTTP ne parle directement à MinIO ou à Pillow.
"""

from __future__ import annotations

from datetime import date

from PIL import UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError, UnsupportedMediaTypeError, ValidationError
from app.models import Photo
from app.services.photo_image import (
    DERIVATIVE_SIZES,
    make_derivative,
    normalize_orientation,
    sha256_of,
    sniff_content_type,
)
from app.storage.minio import MinioStorage

ALLOWED_TAGS = frozenset({"face", "profil", "dos", "bras", "epaule"})


def _object_key(taken_on: date, tag: str, sha256: str) -> str:
    return f"photos/{taken_on.isoformat()}/{tag}-{sha256[:8]}.jpg"


def _derivative_key(size: str, sha256: str) -> str:
    return f"derived/{size}/{sha256}.jpg"


async def upload_photo(
    session: AsyncSession,
    storage: MinioStorage,
    *,
    taken_on: date,
    tag: str,
    raw_bytes: bytes,
) -> Photo:
    """Enregistre une photo. Un envoi pour un (date, tag) déjà connu
    remplace l'existant ; un envoi identique octet pour octet est un no-op.
    """
    if tag not in ALLOWED_TAGS:
        raise UnsupportedMediaTypeError(
            f"Tag inconnu : {tag}", allowed=sorted(ALLOWED_TAGS)
        )
    if sniff_content_type(raw_bytes) is None:
        raise UnsupportedMediaTypeError(
            "Le contenu envoyé n'est ni un JPEG ni un PNG reconnaissable."
        )

    try:
        normalized = normalize_orientation(raw_bytes)
    except UnidentifiedImageError as error:
        raise UnsupportedMediaTypeError("Image illisible ou corrompue.") from error

    checksum = sha256_of(raw_bytes)
    key = _object_key(taken_on, tag, checksum)

    existing = (
        await session.execute(
            select(Photo).where(Photo.taken_on == taken_on, Photo.tag == tag)
        )
    ).scalar_one_or_none()

    if existing is not None and existing.sha256 == checksum:
        return existing

    old_key = existing.object_key if existing is not None else None
    old_sha = existing.sha256 if existing is not None else None

    storage.put(key, normalized.data, normalized.content_type)

    if existing is not None:
        existing.object_key = key
        existing.sha256 = checksum
        existing.width = normalized.width
        existing.height = normalized.height
        existing.byte_size = len(normalized.data)
        existing.content_type = normalized.content_type
        photo = existing
    else:
        photo = Photo(
            taken_on=taken_on,
            tag=tag,
            object_key=key,
            sha256=checksum,
            width=normalized.width,
            height=normalized.height,
            byte_size=len(normalized.data),
            content_type=normalized.content_type,
        )
        session.add(photo)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        storage.delete(key)
        raise ConflictError(
            "Cette image (sha256 identique) est déjà associée à une autre photo."
        ) from error

    await session.refresh(photo)

    if old_key is not None and old_key != key:
        storage.delete(old_key)
        for size in DERIVATIVE_SIZES:
            storage.delete(_derivative_key(size, old_sha))

    return photo


async def list_photos(session: AsyncSession, *, tag: str | None = None) -> list[Photo]:
    query = select(Photo).order_by(Photo.taken_on.desc(), Photo.tag)
    if tag is not None:
        query = query.where(Photo.tag == tag)
    return list((await session.execute(query)).scalars().all())


async def delete_photo(session: AsyncSession, storage: MinioStorage, *, photo_id: int) -> None:
    photo = await session.get(Photo, photo_id)
    if photo is None:
        raise NotFoundError(f"Photo {photo_id} introuvable")

    storage.delete(photo.object_key)
    for size in DERIVATIVE_SIZES:
        storage.delete(_derivative_key(size, photo.sha256))

    await session.delete(photo)
    await session.commit()


async def get_photo_image(
    session: AsyncSession,
    storage: MinioStorage,
    *,
    photo_id: int,
    size: str,
    blur: bool,
) -> tuple[bytes, str]:
    if size not in DERIVATIVE_SIZES:
        raise ValidationError(f"Taille inconnue : {size}", allowed=sorted(DERIVATIVE_SIZES))

    photo = await session.get(Photo, photo_id)
    if photo is None:
        raise NotFoundError(f"Photo {photo_id} introuvable")

    cache_key = _derivative_key(size, photo.sha256)
    if not blur:
        cached = storage.get(cache_key)
        if cached is not None:
            return cached.data, "image/jpeg"

    original = storage.get(photo.object_key)
    if original is None:
        raise NotFoundError(
            f"Fichier de la photo {photo_id} introuvable dans le stockage"
        )

    derivative = make_derivative(
        original.data, max_dimension=DERIVATIVE_SIZES[size], blur=blur
    )
    if not blur:
        storage.put(cache_key, derivative, "image/jpeg")
    return derivative, "image/jpeg"
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run:
```bash
docker compose up -d db minio
cd backend && uv run pytest tests/integration/test_photos_service.py -v
```
Expected: PASS, 13 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/schemas backend/app/services/photos.py \
  backend/tests/integration/test_photos_service.py backend/tests/fixtures/photos
git commit -m "feat: add photo service with derivative caching and dedup"
```

---

### Task 5: Endpoints photo

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/photos.py`
- Create: `backend/tests/integration/test_photos_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `app.db.get_session` ; `app.storage.minio.get_storage` (tâche
  2) ; `PhotoOut`, `ALLOWED_TAGS`, `upload_photo`, `list_photos`,
  `delete_photo`, `get_photo_image` (tâche 4) ; `app.errors.ValidationError,
  PayloadTooLargeError` (tâche 1).
- Produces: `router: APIRouter` monté sur `/api/photos` dans
  `backend/app/api/photos.py`, inclus par `app.main.create_app`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/integration/test_photos_api.py` :

```python
"""Tests d'intégration des endpoints /api/photos, via ASGITransport."""

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import create_app
from app.models import Photo
from app.storage.minio import MinioStorage, get_storage


def _jpeg_bytes(color: str = "red", size: tuple[int, int] = (300, 150)) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
async def client(session: AsyncSession, minio_storage: MinioStorage):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_storage] = lambda: minio_storage
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as opened:
        yield opened


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(Photo.__table__.delete())
    await session.commit()
    yield


async def test_post_photo_returns_201_with_metadata(client: AsyncClient) -> None:
    response = await client.post(
        "/api/photos",
        data={"taken_on": "2026-08-31", "tag": "face"},
        files={"file": ("face.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["tag"] == "face"
    assert body["taken_on"] == "2026-08-31"
    assert body["width"] == 300
    assert body["height"] == 150


async def test_post_photo_with_forged_content_type_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/photos",
        data={"taken_on": "2026-08-31", "tag": "face"},
        files={"file": ("face.jpg", b"pas une image", "image/jpeg")},
    )

    assert response.status_code == 415
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_post_photo_with_unknown_tag_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/photos",
        data={"taken_on": "2026-08-31", "tag": "genou"},
        files={"file": ("x.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 415


async def test_get_photos_lists_uploaded_photos(client: AsyncClient) -> None:
    await client.post(
        "/api/photos",
        data={"taken_on": "2026-08-31", "tag": "face"},
        files={"file": ("a.jpg", _jpeg_bytes("red"), "image/jpeg")},
    )
    await client.post(
        "/api/photos",
        data={"taken_on": "2026-08-31", "tag": "dos"},
        files={"file": ("b.jpg", _jpeg_bytes("blue"), "image/jpeg")},
    )

    all_photos = await client.get("/api/photos")
    filtered = await client.get("/api/photos", params={"tag": "face"})

    assert len(all_photos.json()) == 2
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["tag"] == "face"


async def test_get_photo_image_returns_jpeg_bytes(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/photos",
            data={"taken_on": "2026-08-31", "tag": "face"},
            files={"file": ("a.jpg", _jpeg_bytes(size=(2000, 1000)), "image/jpeg")},
        )
    ).json()

    response = await client.get(f"/api/photos/{created['id']}/image", params={"size": "thumb"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    with Image.open(io.BytesIO(response.content)) as image:
        assert max(image.size) <= 320


async def test_get_photo_image_with_unknown_size_is_a_problem_response(
    client: AsyncClient,
) -> None:
    created = (
        await client.post(
            "/api/photos",
            data={"taken_on": "2026-08-31", "tag": "face"},
            files={"file": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
        )
    ).json()

    response = await client.get(f"/api/photos/{created['id']}/image", params={"size": "xxl"})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_get_photo_image_blurred_differs_from_sharp(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/photos",
            data={"taken_on": "2026-08-31", "tag": "face"},
            files={"file": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
        )
    ).json()

    sharp = await client.get(f"/api/photos/{created['id']}/image", params={"size": "medium"})
    blurred = await client.get(
        f"/api/photos/{created['id']}/image", params={"size": "medium", "blur": "true"}
    )

    assert sharp.content != blurred.content


async def test_delete_photo_returns_204_and_removes_it(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/photos",
            data={"taken_on": "2026-08-31", "tag": "face"},
            files={"file": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
        )
    ).json()

    delete_response = await client.delete(f"/api/photos/{created['id']}")
    list_response = await client.get("/api/photos")

    assert delete_response.status_code == 204
    assert list_response.json() == []


async def test_delete_unknown_photo_is_404_problem_json(client: AsyncClient) -> None:
    response = await client.delete("/api/photos/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_photos_api.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.api'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/api/__init__.py` vide.

Créer `backend/app/api/photos.py` :

```python
"""Endpoints photo : liste, envoi, suppression, service de l'image."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import PayloadTooLargeError, ValidationError
from app.schemas.photos import PhotoOut
from app.services import photos as photos_service
from app.services.photo_image import DERIVATIVE_SIZES
from app.storage.minio import MinioStorage, get_storage

router = APIRouter(prefix="/api/photos", tags=["photos"])

# Une photo de suivi issue d'un téléphone ne dépasse jamais quelques Mo ;
# 25 Mo laisse une large marge sans permettre un envoi déraisonnable.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("", response_model=list[PhotoOut])
async def list_photos(
    tag: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[PhotoOut]:
    photos = await photos_service.list_photos(session, tag=tag)
    return [PhotoOut.model_validate(photo) for photo in photos]


@router.post("", response_model=PhotoOut, status_code=201)
async def upload_photo(
    taken_on: Annotated[date, Form()],
    tag: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    session: AsyncSession = Depends(get_session),
    storage: MinioStorage = Depends(get_storage),
) -> PhotoOut:
    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(
            f"Photo trop volumineuse (maximum {MAX_UPLOAD_BYTES} octets)."
        )
    photo = await photos_service.upload_photo(
        session, storage, taken_on=taken_on, tag=tag, raw_bytes=raw_bytes
    )
    return PhotoOut.model_validate(photo)


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: int,
    session: AsyncSession = Depends(get_session),
    storage: MinioStorage = Depends(get_storage),
) -> Response:
    await photos_service.delete_photo(session, storage, photo_id=photo_id)
    return Response(status_code=204)


@router.get("/{photo_id}/image")
async def get_photo_image(
    photo_id: int,
    size: str = Query("medium"),
    blur: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    storage: MinioStorage = Depends(get_storage),
) -> Response:
    if size not in DERIVATIVE_SIZES:
        raise ValidationError(f"Taille inconnue : {size}", allowed=sorted(DERIVATIVE_SIZES))
    data, content_type = await photos_service.get_photo_image(
        session, storage, photo_id=photo_id, size=size, blur=blur
    )
    return Response(content=data, media_type=content_type)
```

Remplacer entièrement `backend/app/main.py` par :

```python
"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI

from app.api.photos import router as photos_router
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(photos_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run:
```bash
docker compose up -d db minio
cd backend && uv run pytest tests/integration/test_photos_api.py tests/unit/test_health.py -v
```
Expected: PASS, 10 + 1 tests

- [ ] **Step 5: Lancer toute la suite et vérifier ruff**

Run: `cd backend && uv run ruff check . && uv run pytest -v`
Expected: aucune erreur ruff, tous les tests PASS ou SKIPPED (MinIO/DB absents)

- [ ] **Step 6: Commiter**

```bash
git add backend/app/api backend/app/main.py backend/tests/integration/test_photos_api.py
git commit -m "feat: expose photo endpoints"
```

---

### Task 6: Seed des 85 photos réelles dans MinIO

**Files:**
- Create: `backend/scripts/seed_photos.py`
- Modify: `backend/scripts/README.md`

**Interfaces:**
- Consumes: `app.db.session_factory` ; `app.storage.minio.get_storage` ;
  `ALLOWED_TAGS`, `upload_photo` (tâche 4).
- Produces: rien que d'autres tâches consomment. Script jetable, comme
  `scripts/migrate_legacy.py`.

- [ ] **Step 1: Écrire le script**

Créer `backend/scripts/seed_photos.py` :

```python
"""Seed one-shot des photos historiques dans MinIO.

Réutilise app.services.photos.upload_photo, le même service que
POST /api/photos : aucune logique de stockage n'est dupliquée. Idempotent
grâce à la contrainte unique sur sha256 et à la déduplication du service —
relancer le script ne duplique rien. Les données sources ne sont jamais
modifiées : lecture seule sur l'arborescence donnée.

Usage :
    uv run python -m scripts.seed_photos /home/sedelpeuch/migration_body-analysis/photos
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from app.db import session_factory
from app.services.photos import ALLOWED_TAGS, upload_photo
from app.storage.minio import get_storage


async def main(root: Path) -> int:
    if not root.is_dir():
        print(f"Répertoire introuvable : {root}", file=sys.stderr)
        return 2

    storage = get_storage()
    uploaded = 0
    ignored = 0

    async with session_factory() as session:
        for date_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            try:
                taken_on = date.fromisoformat(date_dir.name)
            except ValueError:
                print(f"  ignoré (nom de dossier non daté) : {date_dir.name}")
                ignored += 1
                continue

            for image_path in sorted(date_dir.glob("*.jpg")):
                tag = image_path.stem
                if tag not in ALLOWED_TAGS:
                    print(f"  ignoré (tag inconnu '{tag}') : {image_path}")
                    ignored += 1
                    continue

                raw_bytes = image_path.read_bytes()
                photo = await upload_photo(
                    session, storage, taken_on=taken_on, tag=tag, raw_bytes=raw_bytes
                )
                uploaded += 1
                print(f"  {taken_on} / {tag:<8} -> photo #{photo.id} ({image_path.name})")

    print(f"\n{uploaded} photo(s) traitée(s), {ignored} ignorée(s).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", type=Path, help="répertoire racine des photos (arborescence YYYY-MM-DD/tag.jpg)"
    )
    raise SystemExit(asyncio.run(main(parser.parse_args().root)))
```

Ajouter à `backend/scripts/README.md`, à la suite de la section
`migrate_legacy.py` déjà présente :

```markdown

## seed_photos.py

Envoie les photos de suivi historiques dans MinIO via le même service que
l'endpoint POST /api/photos. Jetable, comme migrate_legacy.py : l'envoi
courant de photos passe par l'API.

```bash
cd backend
uv run python -m scripts.seed_photos /home/sedelpeuch/migration_body-analysis/photos
```

Idempotent : le relancer ne duplique aucune photo, et un fichier modifié
depuis le dernier passage remplace l'ancien pour son (date, tag).
```

- [ ] **Step 2: Lancer le seed sur les données réelles**

Run:
```bash
docker compose up -d db minio
cd backend && uv run python -m scripts.seed_photos \
  /home/sedelpeuch/migration_body-analysis/photos
```
Expected: `85 photo(s) traitée(s), 0 ignorée(s).`

- [ ] **Step 3: Vérifier en base et dans MinIO**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c \
  "SELECT tag, count(*) FROM photo GROUP BY tag ORDER BY tag;"
```
Expected : `bras`, `dos`, `epaule`, `face`, `profil`, 17 chacun (85 / 5).

Run:
```bash
docker compose exec minio mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
docker compose exec minio mc ls --recursive local/body-analysis-photos/photos | wc -l
```
Expected: `85`

- [ ] **Step 4: Vérifier l'idempotence**

Run:
```bash
cd backend && uv run python -m scripts.seed_photos \
  /home/sedelpeuch/migration_body-analysis/photos
docker compose exec db psql -U body -d body_analysis -c "SELECT count(*) FROM photo;"
```
Expected: toujours `85` — aucune ligne supplémentaire.

- [ ] **Step 5: Commiter**

```bash
git add backend/scripts/seed_photos.py backend/scripts/README.md
git commit -m "feat: add one-shot photo seeding script"
```

---

### Task 7: Schémas et service phase

**Files:**
- Create: `backend/app/schemas/phases.py`
- Create: `backend/app/services/phases.py`
- Create: `backend/tests/integration/test_phases_service.py`

**Interfaces:**
- Consumes: `app.models.{Phase, PhaseKind}` ; `app.errors.{NotFoundError,
  ValidationError}` (tâche 1).
- Produces:
  - `PhaseCreate`, `PhaseUpdate`, `PhaseOut` (schémas Pydantic)
  - `async list_phases(session) -> list[Phase]`
  - `async get_phase(session, phase_id: int) -> Phase`
  - `async create_phase(session, payload: PhaseCreate) -> Phase`
  - `async update_phase(session, phase_id: int, payload: PhaseUpdate) ->
    Phase`
  - `async delete_phase(session, phase_id: int) -> None`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/integration/test_phases_service.py` :

```python
"""Tests d'intégration du service phase."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError, ValidationError
from app.models import Phase, PhaseKind
from app.schemas.phases import PhaseCreate, PhaseUpdate
from app.services.phases import (
    create_phase,
    delete_phase,
    get_phase,
    list_phases,
    update_phase,
)


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(Phase.__table__.delete())
    await session.commit()
    yield


async def test_create_phase_persists_it(session: AsyncSession) -> None:
    payload = PhaseCreate(
        name="Sèche automne",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 9, 1),
        ends_on=date(2026, 11, 30),
        weight_target_kg=78.0,
    )

    phase = await create_phase(session, payload)

    assert phase.id is not None
    stored = (await session.execute(select(Phase))).scalar_one()
    assert stored.name == "Sèche automne"
    assert stored.weight_target_kg == 78.0


async def test_list_phases_orders_by_start_date(session: AsyncSession) -> None:
    await create_phase(
        session,
        PhaseCreate(
            name="B", kind=PhaseKind.MAINTAIN, starts_on=date(2026, 6, 1), ends_on=date(2026, 7, 1)
        ),
    )
    await create_phase(
        session,
        PhaseCreate(
            name="A", kind=PhaseKind.BULK, starts_on=date(2026, 1, 1), ends_on=date(2026, 2, 1)
        ),
    )

    phases = await list_phases(session)

    assert [p.name for p in phases] == ["A", "B"]


async def test_overlapping_phases_are_allowed(session: AsyncSession) -> None:
    """Verrou de non-régression : les données réelles contiennent un
    chevauchement d'un jour entre une sèche et le maintien qui la suit."""
    await create_phase(
        session,
        PhaseCreate(
            name="Sèche", kind=PhaseKind.CUT, starts_on=date(2026, 6, 1), ends_on=date(2026, 9, 1)
        ),
    )

    overlapping = await create_phase(
        session,
        PhaseCreate(
            name="Maintien",
            kind=PhaseKind.MAINTAIN,
            starts_on=date(2026, 9, 1),
            ends_on=date(2026, 10, 1),
        ),
    )

    assert overlapping.id is not None
    assert len(await list_phases(session)) == 2


async def test_get_unknown_phase_raises_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await get_phase(session, 999999)


async def test_update_phase_changes_only_given_fields(session: AsyncSession) -> None:
    phase = await create_phase(
        session,
        PhaseCreate(
            name="Sèche", kind=PhaseKind.CUT, starts_on=date(2026, 6, 1), ends_on=date(2026, 9, 1)
        ),
    )

    updated = await update_phase(
        session, phase.id, PhaseUpdate(daily_calories_target=2200)
    )

    assert updated.daily_calories_target == 2200
    assert updated.name == "Sèche"
    assert updated.starts_on == date(2026, 6, 1)


async def test_update_rejects_ends_on_before_starts_on(session: AsyncSession) -> None:
    phase = await create_phase(
        session,
        PhaseCreate(
            name="Sèche", kind=PhaseKind.CUT, starts_on=date(2026, 6, 1), ends_on=date(2026, 9, 1)
        ),
    )

    with pytest.raises(ValidationError):
        await update_phase(session, phase.id, PhaseUpdate(ends_on=date(2026, 5, 1)))


async def test_update_unknown_phase_raises_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await update_phase(session, 999999, PhaseUpdate(name="x"))


async def test_delete_phase_removes_it(session: AsyncSession) -> None:
    phase = await create_phase(
        session,
        PhaseCreate(
            name="Sèche", kind=PhaseKind.CUT, starts_on=date(2026, 6, 1), ends_on=date(2026, 9, 1)
        ),
    )

    await delete_phase(session, phase.id)

    assert (await session.execute(select(Phase))).scalars().all() == []


async def test_delete_unknown_phase_raises_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await delete_phase(session, 999999)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_phases_service.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.schemas.phases'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/schemas/phases.py` :

```python
"""Schémas Pydantic exposés par l'API phases."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import PhaseKind


class PhaseCreate(BaseModel):
    name: str
    kind: PhaseKind
    starts_on: date
    ends_on: date
    weight_target_kg: float | None = None
    body_fat_target_pct: float | None = None
    skeletal_muscle_target_kg: float | None = None
    daily_calories_target: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _ends_not_before_starts(self) -> PhaseCreate:
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on doit être postérieure ou égale à starts_on")
        return self


class PhaseUpdate(BaseModel):
    name: str | None = None
    kind: PhaseKind | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    weight_target_kg: float | None = None
    body_fat_target_pct: float | None = None
    skeletal_muscle_target_kg: float | None = None
    daily_calories_target: int | None = None
    notes: str | None = None


class PhaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: PhaseKind
    starts_on: date
    ends_on: date
    weight_target_kg: float | None
    body_fat_target_pct: float | None
    skeletal_muscle_target_kg: float | None
    daily_calories_target: int | None
    notes: str | None
```

Créer `backend/app/services/phases.py` :

```python
"""Service phase : CRUD.

ends_on >= starts_on est déjà garanti à la création par la validation du
schéma PhaseCreate ; ce module la revérifie côté service seulement pour
PATCH, où seul un sous-ensemble des deux dates peut être fourni et doit donc
être fusionné avec les valeurs existantes avant comparaison. Aucune
contrainte d'exclusion de chevauchement : les données réelles contiennent un
chevauchement d'un jour entre une sèche et le maintien qui la suit.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError, ValidationError
from app.models import Phase
from app.schemas.phases import PhaseCreate, PhaseUpdate


async def list_phases(session: AsyncSession) -> list[Phase]:
    result = await session.execute(select(Phase).order_by(Phase.starts_on))
    return list(result.scalars().all())


async def get_phase(session: AsyncSession, phase_id: int) -> Phase:
    phase = await session.get(Phase, phase_id)
    if phase is None:
        raise NotFoundError(f"Phase {phase_id} introuvable")
    return phase


async def create_phase(session: AsyncSession, payload: PhaseCreate) -> Phase:
    phase = Phase(**payload.model_dump())
    session.add(phase)
    await session.commit()
    await session.refresh(phase)
    return phase


async def update_phase(session: AsyncSession, phase_id: int, payload: PhaseUpdate) -> Phase:
    phase = await get_phase(session, phase_id)
    updates = payload.model_dump(exclude_unset=True)

    starts_on = updates.get("starts_on", phase.starts_on)
    ends_on = updates.get("ends_on", phase.ends_on)
    if ends_on < starts_on:
        raise ValidationError("ends_on doit être postérieure ou égale à starts_on")

    for field_name, value in updates.items():
        setattr(phase, field_name, value)

    await session.commit()
    await session.refresh(phase)
    return phase


async def delete_phase(session: AsyncSession, phase_id: int) -> None:
    phase = await get_phase(session, phase_id)
    await session.delete(phase)
    await session.commit()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_phases_service.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/schemas/phases.py backend/app/services/phases.py \
  backend/tests/integration/test_phases_service.py
git commit -m "feat: add phase CRUD service"
```

---

### Task 8: Endpoints phase

**Files:**
- Create: `backend/app/api/phases.py`
- Create: `backend/tests/integration/test_phases_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `app.db.get_session` ; `PhaseCreate`, `PhaseUpdate`, `PhaseOut`,
  `list_phases`, `get_phase`, `create_phase`, `update_phase`,
  `delete_phase` (tâche 7).
- Produces: `router: APIRouter` monté sur `/api/phases`, inclus par
  `app.main.create_app`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/integration/test_phases_api.py` :

```python
"""Tests d'intégration des endpoints /api/phases."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import create_app
from app.models import Phase


@pytest.fixture
async def client(session: AsyncSession):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as opened:
        yield opened


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(Phase.__table__.delete())
    await session.commit()
    yield


_PAYLOAD = {
    "name": "Sèche automne",
    "kind": "cut",
    "starts_on": "2026-09-01",
    "ends_on": "2026-11-30",
    "weight_target_kg": 78.0,
}


async def test_post_phase_returns_201(client: AsyncClient) -> None:
    response = await client.post("/api/phases", json=_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sèche automne"
    assert body["kind"] == "cut"


async def test_post_phase_with_invalid_dates_is_422_problem_json(client: AsyncClient) -> None:
    invalid = {**_PAYLOAD, "starts_on": "2026-11-30", "ends_on": "2026-09-01"}

    response = await client.post("/api/phases", json=invalid)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_post_phase_with_invalid_kind_is_422(client: AsyncClient) -> None:
    invalid = {**_PAYLOAD, "kind": "shred"}

    response = await client.post("/api/phases", json=invalid)

    assert response.status_code == 422


async def test_get_phases_lists_created_phases(client: AsyncClient) -> None:
    await client.post("/api/phases", json=_PAYLOAD)

    response = await client.get("/api/phases")

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_phase_by_id(client: AsyncClient) -> None:
    created = (await client.post("/api/phases", json=_PAYLOAD)).json()

    response = await client.get(f"/api/phases/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_unknown_phase_is_404_problem_json(client: AsyncClient) -> None:
    response = await client.get("/api/phases/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_patch_phase_updates_a_single_field(client: AsyncClient) -> None:
    created = (await client.post("/api/phases", json=_PAYLOAD)).json()

    response = await client.patch(
        f"/api/phases/{created['id']}", json={"daily_calories_target": 2100}
    )

    assert response.status_code == 200
    assert response.json()["daily_calories_target"] == 2100
    assert response.json()["name"] == "Sèche automne"


async def test_patch_phase_with_invalid_dates_is_422(client: AsyncClient) -> None:
    created = (await client.post("/api/phases", json=_PAYLOAD)).json()

    response = await client.patch(
        f"/api/phases/{created['id']}", json={"ends_on": "2020-01-01"}
    )

    assert response.status_code == 422


async def test_delete_phase_returns_204(client: AsyncClient) -> None:
    created = (await client.post("/api/phases", json=_PAYLOAD)).json()

    response = await client.delete(f"/api/phases/{created['id']}")
    listing = await client.get("/api/phases")

    assert response.status_code == 204
    assert listing.json() == []
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_phases_api.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.api.phases'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/api/phases.py` :

```python
"""Endpoints CRUD des phases."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.phases import PhaseCreate, PhaseOut, PhaseUpdate
from app.services import phases as phases_service

router = APIRouter(prefix="/api/phases", tags=["phases"])


@router.get("", response_model=list[PhaseOut])
async def list_phases(session: AsyncSession = Depends(get_session)) -> list[PhaseOut]:
    phases = await phases_service.list_phases(session)
    return [PhaseOut.model_validate(p) for p in phases]


@router.post("", response_model=PhaseOut, status_code=201)
async def create_phase(
    payload: PhaseCreate, session: AsyncSession = Depends(get_session)
) -> PhaseOut:
    phase = await phases_service.create_phase(session, payload)
    return PhaseOut.model_validate(phase)


@router.get("/{phase_id}", response_model=PhaseOut)
async def get_phase(phase_id: int, session: AsyncSession = Depends(get_session)) -> PhaseOut:
    phase = await phases_service.get_phase(session, phase_id)
    return PhaseOut.model_validate(phase)


@router.patch("/{phase_id}", response_model=PhaseOut)
async def update_phase(
    phase_id: int, payload: PhaseUpdate, session: AsyncSession = Depends(get_session)
) -> PhaseOut:
    phase = await phases_service.update_phase(session, phase_id, payload)
    return PhaseOut.model_validate(phase)


@router.delete("/{phase_id}", status_code=204)
async def delete_phase(
    phase_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await phases_service.delete_phase(session, phase_id)
    return Response(status_code=204)
```

Remplacer entièrement `backend/app/main.py` par :

```python
"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI

from app.api.phases import router as phases_router
from app.api.photos import router as photos_router
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(photos_router)
    app.include_router(phases_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_phases_api.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Lancer toute la suite et vérifier ruff**

Run: `cd backend && uv run ruff check . && uv run pytest -v`
Expected: aucune erreur ruff, tous les tests PASS ou SKIPPED

- [ ] **Step 6: Commiter**

```bash
git add backend/app/api/phases.py backend/app/main.py \
  backend/tests/integration/test_phases_api.py
git commit -m "feat: expose phase CRUD endpoints"
```

---

### Task 9: Garde-fous d'archive ZIP

**Files:**
- Create: `backend/app/ingestion/zip_safety.py`
- Create: `backend/tests/unit/test_zip_safety.py`

**Interfaces:**
- Consumes: `app.errors.ValidationError` (tâche 1).
- Produces:
  - `MAX_TOTAL_UNCOMPRESSED_BYTES: int`
  - `MAX_ENTRY_COUNT: int`
  - `safe_extract(zip_path: Path, destination: Path, *, max_entries: int =
    MAX_ENTRY_COUNT, max_total_bytes: int = MAX_TOTAL_UNCOMPRESSED_BYTES) ->
    None`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/test_zip_safety.py` :

```python
"""Tests des garde-fous d'extraction ZIP : zip-slip et bombe de décompression.

L'archive d'import est une entrée non fiable ; ces tests construisent des
archives réellement malveillantes plutôt que de simuler leur détection.
"""

import zipfile
from pathlib import Path

import pytest

from app.errors import ValidationError
from app.ingestion.zip_safety import safe_extract


def _make_zip(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


def test_extracts_a_well_formed_archive(tmp_path: Path) -> None:
    zip_path = _make_zip(
        tmp_path / "export.zip",
        {
            "com.samsung.health.weight.csv": b"start_time,weight\n",
            "com.samsung.shealth.exercise/1/a.json": b"{}",
        },
    )
    destination = tmp_path / "extracted"

    safe_extract(zip_path, destination)

    assert (destination / "com.samsung.health.weight.csv").read_bytes() == (
        b"start_time,weight\n"
    )
    assert (destination / "com.samsung.shealth.exercise" / "1" / "a.json").exists()


def test_rejects_an_entry_that_escapes_the_destination_with_dotdot(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path / "evil.zip", {"../../etc/evil.txt": b"charge utile"})
    destination = tmp_path / "extracted"
    destination.mkdir()

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination)

    assert not (tmp_path.parent / "etc" / "evil.txt").exists()
    assert list(destination.iterdir()) == []


def test_rejects_an_entry_with_an_absolute_path(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path / "evil.zip", {"/etc/evil.txt": b"charge utile"})
    destination = tmp_path / "extracted"
    destination.mkdir()

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination)

    assert not Path("/etc/evil.txt").exists()


def test_rejects_an_archive_with_too_many_entries(tmp_path: Path) -> None:
    zip_path = tmp_path / "many.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for i in range(10):
            archive.writestr(f"file-{i}.txt", b"x")
    destination = tmp_path / "extracted"

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination, max_entries=5)


def test_rejects_a_decompression_bomb_by_streamed_size(tmp_path: Path) -> None:
    """Une bombe classique : peu d'octets compressés, énormément une fois
    décompressés. La vérification porte sur les octets réellement produits
    pendant la décompression, pas seulement sur la taille déclarée dans les
    métadonnées de l'archive, qu'un attaquant contrôle entièrement."""
    zip_path = tmp_path / "bomb.zip"
    huge_but_compressible = b"\x00" * (5 * 1024 * 1024)  # 5 Mo de zéros
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.bin", huge_but_compressible)
    destination = tmp_path / "extracted"

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination, max_total_bytes=1024)


def test_does_not_leave_a_completed_forbidden_file_after_bomb_rejection(tmp_path: Path) -> None:
    zip_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.bin", b"\x00" * (2 * 1024 * 1024))
    destination = tmp_path / "extracted"

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination, max_total_bytes=1024)

    written = destination / "bomb.bin"
    if written.exists():
        assert written.stat().st_size <= 1024 + (1024 * 1024)  # au plus un bloc de plus
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_zip_safety.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.zip_safety'`

- [ ] **Step 3: Écrire l'implémentation**

Créer `backend/app/ingestion/zip_safety.py` :

```python
"""Garde-fous contre une archive ZIP malveillante.

Le ZIP importé est une entrée non fiable : il peut contenir des chemins qui
s'échappent du répertoire d'extraction (zip-slip) ou viser une bombe de
décompression (peu d'octets compressés, énormément une fois décompressés).
Le nombre d'entrées et les chemins sont vérifiés avant d'écrire le moindre
octet ; la taille décompressée est vérifiée en continu pendant l'extraction,
sur les octets réellement produits — jamais seulement sur la taille déclarée
dans les métadonnées de l'archive, qu'un attaquant contrôle entièrement.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.errors import ValidationError

# L'export réel fait 1,3 Go décompressé pour 88 093 fichiers : ces seuils
# laissent une large marge sans laisser passer une bombe.
MAX_TOTAL_UNCOMPRESSED_BYTES = 4 * 1024**3  # 4 Go
MAX_ENTRY_COUNT = 200_000

_CHUNK_SIZE = 1024 * 1024


def safe_extract(
    zip_path: Path,
    destination: Path,
    *,
    max_entries: int = MAX_ENTRY_COUNT,
    max_total_bytes: int = MAX_TOTAL_UNCOMPRESSED_BYTES,
) -> None:
    """Extrait zip_path sous destination après vérification complète.

    Lève ValidationError si l'archive tente une évasion de chemin, dépasse
    le nombre d'entrées autorisé, ou si le flux décompressé dépasse le
    volume autorisé en cours d'extraction.
    """
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > max_entries:
            raise ValidationError(
                f"Archive refusée : {len(infos)} entrées, "
                f"plus que le maximum autorisé ({max_entries})."
            )

        targets: list[tuple[zipfile.ZipInfo, Path]] = []
        for info in infos:
            target = (destination / info.filename).resolve()
            is_contained = target == destination or destination in target.parents
            if not is_contained:
                raise ValidationError(
                    f"Archive refusée : l'entrée '{info.filename}' sort du "
                    "répertoire d'extraction."
                )
            targets.append((info, target))

        written_total = 0
        for info, target in targets:
            if info.is_dir() or info.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as handle:
                while True:
                    chunk = source.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    written_total += len(chunk)
                    if written_total > max_total_bytes:
                        raise ValidationError(
                            "Archive refusée : volume décompressé au-delà de "
                            f"{max_total_bytes} octets."
                        )
                    handle.write(chunk)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_zip_safety.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/zip_safety.py backend/tests/unit/test_zip_safety.py
git commit -m "feat: guard zip extraction against slip and decompression bombs"
```

---

### Task 10: Réutilisation du pipeline et service d'import

Cette tâche étend `run_ingestion` de façon additive — tous les appels
existants (`scripts/migrate_legacy.py`, `tests/integration/test_pipeline.py`
du plan « Socle et ingestion ») continuent de fonctionner sans changement.

**Files:**
- Modify: `backend/app/ingestion/samsung/pipeline.py`
- Create: `backend/tests/integration/test_pipeline_reuses_run.py`
- Create: `backend/app/services/imports.py`
- Create: `backend/tests/integration/test_imports_service.py`
- Modify: `backend/app/db.py`

**Interfaces:**
- Consumes: `discover_source`, `SamsungSource` (existant) ;
  `app.ingestion.zip_safety.safe_extract` (tâche 9) ; `app.errors.
  ValidationError` (tâche 1) ; `app.models.{IngestionRun, IngestionStatus}`.
- Produces:
  - `run_ingestion(session, source, *, kind, source_name, run:
    IngestionRun | None = None) -> IngestionRun` (signature étendue,
    rétrocompatible).
  - `app.db.get_session_factory() -> async_sessionmaker[AsyncSession]`
  - `IMPORT_KIND: str`
  - `async create_pending_run(session, *, source_name: str) -> IngestionRun`
  - `validate_zip_signature(header: bytes) -> None`
  - `async run_zip_import(session_factory, *, run_id: int, zip_path: Path)
    -> None`

- [ ] **Step 1: Écrire le test qui échoue pour l'extension du pipeline**

Créer `backend/tests/integration/test_pipeline_reuses_run.py` :

```python
"""Vérifie que run_ingestion peut reprendre un IngestionRun déjà créé,
sans quoi l'import HTTP ne pourrait pas donner un identifiant au front avant
que l'ingestion, potentiellement longue, ne démarre."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.models import IngestionRun, IngestionStatus

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    shutil.copy(
        FIXTURES / "samsung" / "weight_sample.csv",
        tmp_path / "com.samsung.health.weight.20260831162666.csv",
    )
    return tmp_path


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(IngestionRun.__table__.delete())
    await session.commit()
    yield


async def test_run_ingestion_reuses_a_preexisting_run(
    session: AsyncSession, export_dir: Path
) -> None:
    preexisting = IngestionRun(
        kind="samsung_zip", source_name="export.zip", status=IngestionStatus.RUNNING
    )
    session.add(preexisting)
    await session.commit()
    await session.refresh(preexisting)

    result = await run_ingestion(
        session,
        discover_source(export_dir),
        kind="samsung_zip",
        source_name="export.zip",
        run=preexisting,
    )

    assert result.id == preexisting.id
    assert result.status is IngestionStatus.SUCCESS
    rows = (await session.execute(select(IngestionRun))).scalars().all()
    assert len(rows) == 1  # aucune ligne créée en plus de celle réutilisée


async def test_run_ingestion_without_run_still_creates_one(
    session: AsyncSession, export_dir: Path
) -> None:
    """Non-régression : le script de migration jetable appelle
    run_ingestion sans l'argument run et doit continuer à fonctionner."""
    result = await run_ingestion(
        session, discover_source(export_dir), kind="migration", source_name="fixture"
    )

    assert result.id is not None
    assert result.status is IngestionStatus.SUCCESS
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_pipeline_reuses_run.py -v`
Expected: FAIL avec `TypeError: run_ingestion() got an unexpected keyword argument 'run'`

- [ ] **Step 3: Étendre run_ingestion de façon additive**

Dans `backend/app/ingestion/samsung/pipeline.py`, remplacer la signature et
les trois premières lignes du corps de `run_ingestion` :

```python
async def run_ingestion(
    session: AsyncSession,
    source: SamsungSource,
    *,
    kind: str,
    source_name: str,
) -> IngestionRun:
    """Ingère un export et journalise le résultat.

    En cas d'échec le run est marqué FAILED avec son message avant que
    l'exception soit relancée : l'appelant décide quoi en faire, mais la
    trace en base ne se perd jamais.
    """
    run = IngestionRun(
        kind=kind, source_name=source_name, status=IngestionStatus.RUNNING
    )
    session.add(run)
    await session.commit()
```

par :

```python
async def run_ingestion(
    session: AsyncSession,
    source: SamsungSource,
    *,
    kind: str,
    source_name: str,
    run: IngestionRun | None = None,
) -> IngestionRun:
    """Ingère un export et journalise le résultat.

    En cas d'échec le run est marqué FAILED avec son message avant que
    l'exception soit relancée : l'appelant décide quoi en faire, mais la
    trace en base ne se perd jamais.

    run : une ligne IngestionRun déjà créée et committée à réutiliser plutôt
    que d'en créer une nouvelle. Sert l'import HTTP, où l'identifiant du run
    doit être connu avant que l'ingestion, potentiellement longue, ne
    démarre en tâche de fond.
    """
    if run is None:
        run = IngestionRun(
            kind=kind, source_name=source_name, status=IngestionStatus.RUNNING
        )
        session.add(run)
        await session.commit()
```

Le reste du corps de la fonction (bloc `try/except/finally`) référence déjà
la variable locale `run` sans connaître son origine : aucun autre
changement n'est nécessaire dans ce fichier.

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run:
```bash
cd backend && uv run pytest tests/integration/test_pipeline_reuses_run.py \
  tests/integration/test_pipeline.py -v
```
Expected: PASS, 2 + 3 tests — la suite existante du plan « Socle et
ingestion » n'est pas cassée par l'extension.

- [ ] **Step 5: Ajouter un fournisseur de fabrique de session testable**

Dans `backend/app/db.py`, ajouter à la fin du fichier :

```python
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Fournisseur pour Depends() : permet aux tests de substituer une
    fabrique liée à la base jetable plutôt qu'à settings.database_url."""
    return session_factory
```

Le fichier complet `backend/app/db.py` devient :

```python
"""Moteur et fabrique de sessions asynchrones."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)

session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Fournisseur pour Depends() : permet aux tests de substituer une
    fabrique liée à la base jetable plutôt qu'à settings.database_url."""
    return session_factory
```

- [ ] **Step 6: Écrire le test du service d'import qui échoue**

Créer `backend/tests/integration/test_imports_service.py` :

```python
"""Tests d'intégration du service d'import ZIP."""

import zipfile
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import ValidationError
from app.models import IngestionRun, IngestionStatus
from app.services.imports import create_pending_run, run_zip_import, validate_zip_signature

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(IngestionRun.__table__.delete())
    await session.commit()
    yield


def _zip_of(tmp_path: Path, name: str, contents: dict[str, bytes]) -> Path:
    zip_path = tmp_path / name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry_name, data in contents.items():
            archive.writestr(entry_name, data)
    return zip_path


async def test_create_pending_run_is_immediately_visible(session: AsyncSession) -> None:
    run = await create_pending_run(session, source_name="export.zip")

    assert run.id is not None
    assert run.status is IngestionStatus.RUNNING
    stored = (await session.execute(select(IngestionRun))).scalar_one()
    assert stored.id == run.id


def test_validate_zip_signature_accepts_a_real_zip_header() -> None:
    validate_zip_signature(b"PK\x03\x04reste-des-octets")


def test_validate_zip_signature_rejects_anything_else() -> None:
    with pytest.raises(ValidationError):
        validate_zip_signature(b"ceci n'est pas un zip")


async def test_run_zip_import_extracts_and_completes_the_run(
    session: AsyncSession, tmp_path: Path, engine
) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    zip_path = _zip_of(
        tmp_path, "export.zip", {"com.samsung.health.weight.20260831162666.csv": weight_csv}
    )
    run = await create_pending_run(session, source_name="export.zip")
    await session.commit()

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    await run_zip_import(factory, run_id=run.id, zip_path=zip_path)

    async with factory() as verification_session:
        completed = await verification_session.get(IngestionRun, run.id)
        assert completed.status is IngestionStatus.SUCCESS
        assert completed.counts["body_measurements"] == 2

    assert not zip_path.exists()  # nettoyé après usage


async def test_run_zip_import_marks_the_run_failed_on_a_malicious_archive(
    session: AsyncSession, tmp_path: Path, engine
) -> None:
    zip_path = _zip_of(tmp_path, "evil.zip", {"../evil.txt": b"charge utile"})
    run = await create_pending_run(session, source_name="evil.zip")
    await session.commit()

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    with pytest.raises(ValidationError):
        await run_zip_import(factory, run_id=run.id, zip_path=zip_path)

    async with factory() as verification_session:
        failed = await verification_session.get(IngestionRun, run.id)
        assert failed.status is IngestionStatus.FAILED
        assert "sort du" in failed.error
```

- [ ] **Step 7: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_imports_service.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.services.imports'`

- [ ] **Step 8: Écrire l'implémentation du service d'import**

Créer `backend/app/services/imports.py` :

```python
"""Orchestration de l'import ZIP Samsung Health.

Réutilise discover_source et run_ingestion du pipeline existant sans les
réécrire. Ce module gère ce qu'ils ne gèrent pas : la validation du fichier
reçu, l'extraction sûre dans un répertoire jetable, et la création précoce
du IngestionRun pour qu'un identifiant soit disponible dès la réponse HTTP,
avant que l'ingestion elle-même — potentiellement longue — ne démarre en
tâche de fond.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import ValidationError
from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.ingestion.zip_safety import safe_extract
from app.models import IngestionRun, IngestionStatus

IMPORT_KIND = "samsung_zip"

_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


async def create_pending_run(session: AsyncSession, *, source_name: str) -> IngestionRun:
    """Crée la ligne de suivi avant même l'extraction de l'archive.

    C'est ce qui permet au front d'obtenir un identifiant à interroger dès
    la réponse de POST /api/imports/samsung-zip.
    """
    run = IngestionRun(kind=IMPORT_KIND, source_name=source_name, status=IngestionStatus.RUNNING)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


def validate_zip_signature(header: bytes) -> None:
    """Vérifie que le fichier reçu commence par une signature ZIP connue,
    quel que soit le Content-Type ou le nom de fichier déclarés."""
    if not header.startswith(_ZIP_SIGNATURES):
        raise ValidationError("Le fichier envoyé n'est pas une archive ZIP valide.")


async def run_zip_import(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    run_id: int,
    zip_path: Path,
) -> None:
    """Tâche de fond : extrait l'archive puis délègue à run_ingestion.

    Exécutée avec sa propre session, indépendante de celle de la requête
    HTTP déjà répondue. Le répertoire d'extraction et le fichier ZIP
    temporaire sont nettoyés dans un finally, y compris en cas d'échec.
    """
    extract_dir = Path(tempfile.mkdtemp(prefix="ba-import-"))
    try:
        safe_extract(zip_path, extract_dir)
        source = discover_source(extract_dir)

        async with session_factory() as session:
            run = await session.get(IngestionRun, run_id)
            await run_ingestion(
                session,
                source,
                kind=IMPORT_KIND,
                source_name=run.source_name,
                run=run,
            )
    except Exception as error:
        async with session_factory() as session:
            run = await session.get(IngestionRun, run_id)
            if run is not None and run.status is not IngestionStatus.FAILED:
                run.status = IngestionStatus.FAILED
                run.error = f"{type(error).__name__}: {error}"
                await session.commit()
        raise
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
```

- [ ] **Step 9: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_imports_service.py -v`
Expected: PASS, 5 tests

- [ ] **Step 10: Lancer toute la suite**

Run: `cd backend && uv run ruff check . && uv run pytest -v`
Expected: aucune erreur ruff, tous les tests PASS ou SKIPPED

- [ ] **Step 11: Commiter**

```bash
git add backend/app/ingestion/samsung/pipeline.py backend/app/db.py \
  backend/app/services/imports.py backend/tests/integration/test_pipeline_reuses_run.py \
  backend/tests/integration/test_imports_service.py
git commit -m "feat: add zip import service reusing the ingestion pipeline"
```

---

### Task 11: Endpoints d'import ZIP

**Files:**
- Create: `backend/app/schemas/imports.py`
- Create: `backend/app/api/imports.py`
- Create: `backend/tests/integration/test_imports_api.py`
- Modify: `backend/tests/integration/conftest.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `app.db.get_session`, `get_session_factory` (tâche 10) ;
  `IMPORT_KIND`, `create_pending_run`, `run_zip_import`,
  `validate_zip_signature` (tâche 10) ; `app.errors.NotFoundError`
  (tâche 1).
- Produces: `router: APIRouter` monté sur `/api/imports`, inclus par
  `app.main.create_app`.

- [ ] **Step 1: Ajouter la fixture de fabrique de session de test**

Ajouter à `backend/tests/integration/conftest.py`, à la suite de la fixture
`session` existante :

```python
@pytest_asyncio.fixture(loop_scope="session")
async def test_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Fabrique liée à la base jetable, pour surcharger
    app.db.get_session_factory dans les tests d'API qui déclenchent une
    tâche de fond utilisant sa propre session."""
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 2: Écrire le test qui échoue**

Créer `backend/tests/integration/test_imports_api.py` :

```python
"""Tests d'intégration des endpoints /api/imports."""

import io
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import get_session, get_session_factory
from app.main import create_app
from app.models import IngestionRun

FIXTURES = Path(__file__).parents[1] / "fixtures"


def _zip_bytes(contents: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@pytest.fixture
async def client(
    session: AsyncSession, test_session_factory: async_sessionmaker[AsyncSession]
):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_session_factory] = lambda: test_session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as opened:
        yield opened


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(IngestionRun.__table__.delete())
    await session.commit()
    yield


async def test_post_samsung_zip_returns_202_with_a_pollable_id(client: AsyncClient) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    archive = _zip_bytes({"com.samsung.health.weight.20260831162666.csv": weight_csv})

    response = await client.post(
        "/api/imports/samsung-zip",
        files={"file": ("export.zip", archive, "application/zip")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["id"] is not None
    assert body["status"] in ("running", "success")


async def test_import_completes_and_is_reflected_by_get(client: AsyncClient) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    archive = _zip_bytes({"com.samsung.health.weight.20260831162666.csv": weight_csv})

    created = (
        await client.post(
            "/api/imports/samsung-zip",
            files={"file": ("export.zip", archive, "application/zip")},
        )
    ).json()

    response = await client.get(f"/api/imports/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["counts"]["body_measurements"] == 2


async def test_post_a_non_zip_file_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/imports/samsung-zip",
        files={"file": ("export.zip", b"pas un zip", "application/zip")},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_post_a_malicious_zip_ends_up_failed(client: AsyncClient) -> None:
    archive = _zip_bytes({"../evil.txt": b"charge utile"})

    created = (
        await client.post(
            "/api/imports/samsung-zip",
            files={"file": ("evil.zip", archive, "application/zip")},
        )
    ).json()

    response = await client.get(f"/api/imports/{created['id']}")

    assert response.json()["status"] == "failed"
    assert "sort du" in response.json()["error"]


async def test_get_imports_lists_every_run(client: AsyncClient) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    archive = _zip_bytes({"com.samsung.health.weight.20260831162666.csv": weight_csv})
    await client.post(
        "/api/imports/samsung-zip", files={"file": ("a.zip", archive, "application/zip")}
    )
    await client.post(
        "/api/imports/samsung-zip", files={"file": ("b.zip", archive, "application/zip")}
    )

    response = await client.get("/api/imports")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_unknown_import_is_404_problem_json(client: AsyncClient) -> None:
    response = await client.get("/api/imports/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
```

- [ ] **Step 3: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_imports_api.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.schemas.imports'`

- [ ] **Step 4: Écrire l'implémentation**

Créer `backend/app/schemas/imports.py` :

```python
"""Schémas Pydantic exposés par l'API imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import IngestionStatus


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    source_name: str
    status: IngestionStatus
    started_at: datetime
    finished_at: datetime | None
    counts: dict[str, Any] | None
    error: str | None
```

Créer `backend/app/api/imports.py` :

```python
"""Endpoints d'import : réception du ZIP, suivi de la progression.

L'upload est reçu en flux et écrit sur disque par blocs : une archive réelle
atteint 1,3 Go, jamais chargée entièrement en mémoire. Seule la validation
de la signature ZIP et la création de la ligne de suivi se font avant la
réponse ; l'extraction et l'ingestion tournent en tâche de fond, le front
interrogeant GET /api/imports/{id} pour suivre la progression.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import get_session, get_session_factory
from app.errors import NotFoundError
from app.models import IngestionRun
from app.schemas.imports import IngestionRunOut
from app.services.imports import create_pending_run, run_zip_import, validate_zip_signature

router = APIRouter(prefix="/api/imports", tags=["imports"])

UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 Mo : jamais l'archive entière en mémoire


@router.post("/samsung-zip", response_model=IngestionRunOut, status_code=202)
async def import_samsung_zip(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    session: AsyncSession = Depends(get_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> IngestionRunOut:
    first_chunk = await file.read(UPLOAD_CHUNK_SIZE)
    validate_zip_signature(first_chunk)

    fd, tmp_name = tempfile.mkstemp(prefix="ba-upload-", suffix=".zip")
    tmp_path = Path(tmp_name)
    with open(fd, "wb") as handle:
        handle.write(first_chunk)
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            handle.write(chunk)

    run = await create_pending_run(session, source_name=file.filename or "export.zip")

    background_tasks.add_task(
        run_zip_import, session_factory, run_id=run.id, zip_path=tmp_path
    )
    return IngestionRunOut.model_validate(run)


@router.get("", response_model=list[IngestionRunOut])
async def list_imports(
    session: AsyncSession = Depends(get_session),
) -> list[IngestionRunOut]:
    runs = (
        await session.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc()))
    ).scalars().all()
    return [IngestionRunOut.model_validate(run) for run in runs]


@router.get("/{run_id}", response_model=IngestionRunOut)
async def get_import(
    run_id: int, session: AsyncSession = Depends(get_session)
) -> IngestionRunOut:
    run = await session.get(IngestionRun, run_id)
    if run is None:
        raise NotFoundError(f"Import {run_id} introuvable")
    return IngestionRunOut.model_validate(run)
```

Remplacer entièrement `backend/app/main.py` par :

```python
"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI

from app.api.imports import router as imports_router
from app.api.phases import router as phases_router
from app.api.photos import router as photos_router
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(photos_router)
    app.include_router(phases_router)
    app.include_router(imports_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_imports_api.py -v`
Expected: PASS, 6 tests

- [ ] **Step 6: Lancer toute la suite du plan**

Run:
```bash
docker compose up -d db minio
cd backend && uv run ruff check . && uv run pytest -v
```
Expected: aucune erreur ruff, tous les tests PASS

- [ ] **Step 7: Vérification manuelle avec une archive réelle**

Run (attention : peut prendre plusieurs minutes, l'archive fait 1,3 Go) :
```bash
cd /home/sedelpeuch/migration_body-analysis && zip -r -X /tmp/export-test.zip \
  com.samsung.health.weight.*.csv phases.json
curl -s -X POST http://localhost:8000/api/imports/samsung-zip \
  -F "file=@/tmp/export-test.zip;type=application/zip"
```
Expected: `202` avec un JSON contenant `"status": "running"` (ou `"success"`
si l'extraction est très rapide) et un `id`.

Run (remplacer `<id>` par la valeur reçue) :
```bash
curl -s http://localhost:8000/api/imports/<id> | python3 -m json.tool
```
Expected: `"status": "success"` après quelques secondes, avec `counts`
peuplé.

- [ ] **Step 8: Commiter**

```bash
git add backend/app/schemas/imports.py backend/app/api/imports.py backend/app/main.py \
  backend/tests/integration/test_imports_api.py backend/tests/integration/conftest.py
git commit -m "feat: expose samsung zip import endpoint with progress polling"
```

---

## Definition of done du plan 3

- [ ] `docker compose ps` montre `db` et `minio` en `healthy`.
- [ ] `cd backend && uv run ruff check .` ne signale rien.
- [ ] `cd backend && uv run pytest` passe intégralement (les tests
  d'intégration MinIO/DB sont SKIPPED proprement si les services ne
  tournent pas, jamais en erreur).
- [ ] Les 85 photos réelles sont dans MinIO et en base via
  `scripts/seed_photos.py`, et un second passage ne duplique rien.
- [ ] `GET /api/photos/{id}/image?size=thumb` et `?size=medium&blur=true`
  renvoient toutes deux du `image/jpeg`, la seconde différente de la
  première.
- [ ] Une photo réellement paysage n'est jamais tournée par
  `normalize_orientation` (`test_normalize_orientation_does_not_rotate_a_true_landscape_photo`).
- [ ] `GET/POST /api/phases`, `GET/PATCH/DELETE /api/phases/{id}`
  fonctionnent, y compris sur deux phases qui se chevauchent d'un jour.
- [ ] `POST /api/imports/samsung-zip` renvoie `202` avec un `id`
  immédiatement interrogeable via `GET /api/imports/{id}`.
- [ ] Une archive contenant une entrée `../evil.txt` ou une bombe de
  décompression est rejetée sans écrire hors du répertoire d'extraction, et
  le run associé passe à `failed` avec un message d'erreur exploitable.
- [ ] Toute réponse d'erreur de l'API, y compris les 404 de routage et les
  erreurs de validation Pydantic, est `application/problem+json`.

## Auto-revue

**Couverture de la spec.** Ce plan couvre la section 3.3 (stockage des
photos), 4.3 (phase, chevauchement autorisé), 4.10 (photo), 4.11
(ingestion_run côté réutilisation), la totalité de la section 6 pour
« Phases », « Photos » et « Imports », et la section 7 pour le flux
d'import ZIP côté HTTP. Les incréments 5 (photos) et 7 (écritures : phases,
photos, import ZIP) de la section 10 sont entièrement couverts. Restent hors
périmètre, explicitement : les endpoints de lecture analytique (`/body/*`,
`/nutrition/*`, `/workouts/*`, `/analytics/*`, `/phases/{id}/report`,
`/phases/report`), qui relèvent du plan « Analytics et API de lecture », et
le front, qui relève du plan « Front ».

**Dépendance vers le plan de lecture.** Ce plan crée `app/api/`,
`app/services/`, `app/schemas/`, `app/storage/` et `app/errors.py` s'ils
n'existent pas encore — au moment de la rédaction, le plan « Analytics et
API de lecture » n'avait pas tourné. Si ce dernier s'exécute en premier,
son implémenteur doit poser ces mêmes paquets et `app.errors.
register_error_handlers` avec la même forme ; l'implémenteur de ce plan
fusionnera alors ses fichiers dans l'arborescence existante au lieu de la
recréer, et `app/main.py` accumulera les `include_router` des deux plans
plutôt que d'être écrasé.

**Décisions tranchées non explicitement données par le contexte.**
1. *Identifiant de run disponible avant l'ingestion.* Le contexte demande
   que le front puisse interroger `GET /imports/{id}` pendant qu'une tâche
   de fond ingère, mais `run_ingestion` (déjà écrit) crée sa propre ligne
   `IngestionRun` en tout début d'exécution — si cette exécution est
   elle-même la tâche de fond, son identifiant n'existe pas encore quand la
   réponse HTTP part. Plutôt que dupliquer la logique d'ingestion pour créer
   la ligne en avance (violant « ne pas réimplémenter »), la tâche 10 étend
   `run_ingestion` d'un paramètre additif `run: IngestionRun | None = None`,
   rétrocompatible avec `scripts/migrate_legacy.py` et les tests du plan
   « Socle et ingestion » (vérifié par
   `test_run_ingestion_without_run_still_creates_one`). Le service d'import
   crée la ligne avant l'extraction et la transmet.
2. *Clé des dérivés.* La spec dit « dérivés sous `derived/{size}/…} » sans
   préciser la suite. Choisie : `derived/{size}/{sha256}.jpg` (empreinte
   complète, indépendante de la date et du tag) — un dérivé dépend
   uniquement des octets sources, jamais de ses métadonnées, et la clé reste
   stable si une photo est déplacée d'un tag à l'autre par erreur puis
   corrigée.
3. *Format de sortie des dérivés et de l'image normalisée.* Toujours JPEG,
   y compris pour un envoi PNG d'origine : simplifie la mise en cache (un
   seul `Content-Type` à connaître) et n'a aucun impact perceptible sur des
   photos de suivi.
4. *Flou jamais mis en cache.* Le contexte dit que le flou est serveur et
   que l'image nette ne quitte jamais le back, mais ne dit pas si le rendu
   flouté est mis en cache. Choisi : non — le mode confidentiel est un
   bascule d'affichage, recalculer un flou sur une image déjà réduite est
   négligeable, et ne pas le cacher évite un jeu de clés MinIO
   supplémentaire par photo.
5. *Fixture MinIO de test.* Le contexte cite `BA_TEST_DATABASE_URL` comme
   modèle de "skip propre" ; en relisant `tests/integration/conftest.py` du
   plan « Socle et ingestion », le skip n'y est en réalité pas implémenté —
   la fixture `engine` se contente d'une valeur par défaut et échouerait
   (plutôt que d'être *skipped*) si PostgreSQL est injoignable. La tâche 2
   de ce plan implémente le skip réel pour MinIO
   (`MinioStorage.is_reachable()` + `pytest.skip`) sans modifier le
   comportement de la fixture `engine` existante, qui reste hors périmètre
   de ce plan.

**Cohérence des types entre tâches.** `MinioStorage` est produit en tâche 2
avec `.put/.get/.exists/.delete/.delete_prefix/.is_reachable`, et ces cinq
méthodes sont utilisées avec la même signature en tâches 4 (service photo)
et 9-10 (aucune, l'import ne touche pas MinIO directement). `NormalizedImage`
et `DERIVATIVE_SIZES` sont produits en tâche 3 et consommés tels quels en
tâche 4. `PhotoOut`, `PhaseCreate/Update/Out`, `IngestionRunOut` utilisent
`model_config = ConfigDict(from_attributes=True)` de façon uniforme pour se
construire depuis les modèles SQLAlchemy. `run_ingestion(..., run=None)` de
la tâche 10 est appelé avec `run=` explicite en tâche 10
(`test_pipeline_reuses_run.py`) et implicitement sans lui en tâche 14 du
plan « Socle et ingestion » (`scripts/migrate_legacy.py`, jamais modifié).
`get_session_factory` est ajouté à `app.db` en tâche 10 et surchargé de la
même façon (`app.dependency_overrides[get_session_factory] = lambda: ...`)
dans le seul test qui en a besoin, `test_imports_api.py` (tâche 11).

**Placeholders.** Aucun. Le seul répertoire créé sans contenu généré par le
code est `backend/tests/fixtures/photos/`, explicitement réservé et
documenté comme tel en tâche 4 ; il ne contient qu'un `.gitkeep`.
