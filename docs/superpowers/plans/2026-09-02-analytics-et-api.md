# Analytics et API de lecture — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans pour exécuter ce plan tâche par tâche. Les étapes utilisent la syntaxe case à cocher (`- [ ]`) pour le suivi.

**Goal:** Construire l'intelligence de l'application — les modules d'analyse
purs et l'ensemble des endpoints de lecture de la spec section 6 — sur les
données déjà en base (plan 1 terminé : 647 mesures, 11 855 entrées
alimentaires, 4 734 séances, ~2,8 M échantillons, ~590 k positions, ~3 000
séries de musculation, 8 phases, trois vues matérialisées quotidiennes).

**Architecture:** Trois étages sans dépendance circulaire :
`analytics/` calcule, sans jamais toucher une base de données ni HTTP — entrée
et sortie en dataclasses ; `services/` orchestre la base de données et
`analytics/` ; `api/` traduit HTTP vers `services/` et retourne des schémas
Pydantic. Aucun endpoint ne contient de calcul métier, aucun module
`analytics/` n'importe SQLAlchemy ou FastAPI.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 asynchrone, asyncpg,
Pydantic v2, pytest, httpx (`ASGITransport`), PostgreSQL 17.

**Spec:** `docs/superpowers/specs/2026-09-02-migration-fastapi-react-design.md`
(sections 5 et 6 principalement).

## Global Constraints

- Python `>=3.13`. Planchers de dépendances, jamais de versions figées :
  `fastapi>=0.115`, `sqlalchemy[asyncio]>=2.0.36`, `asyncpg>=0.30`,
  `pydantic>=2.10`, `pydantic-settings>=2.7`, `pytest>=8.3`,
  `pytest-asyncio>=0.24`, `httpx>=0.28`, `ruff>=0.8`. Ces dépendances sont
  déjà dans `backend/pyproject.toml` (plan 1) ; aucune n'est à ajouter pour
  ce plan.
- **Aucun identifiant en dur.** Ce plan n'ajoute aucun secret ; il consomme
  `app.config.settings` déjà en place.
- **Une valeur absente est `None`, jamais `0` ni `NaN`**, de la base à la
  réponse HTTP. Une agrégation sur une fenêtre sans donnée renvoie `null`,
  jamais une moyenne calculée sur des trous silencieusement comblés à zéro.
  Exception assumée et documentée au cas par cas : l'absence de séance un
  jour donné vaut *zéro calorie brûlée à l'effort ce jour-là*, ce n'est pas
  une mesure manquante.
- **Tous les horodatages gardent leur fuseau** (`TIMESTAMPTZ`), déjà garanti
  par les modèles du plan 1. Les agrégations par jour utilisent la frontière
  `Europe/Paris`, comme les vues matérialisées.
- Code, tables, colonnes, commits en **anglais** ; commentaires et
  documentation en **français**.
- Les données réelles ne sont jamais modifiées : ce plan ne lit qu'une base
  déjà peuplée.
- **Frontière `analytics/` stricte.** Aucun module sous `app/analytics/`
  n'importe `sqlalchemy`, `fastapi`, ni `app.db`. Chaque fonction publique y
  prend des dataclasses ou des types primitifs en entrée et renvoie des
  dataclasses. C'est ce qui permet de les tester sans base de données ni
  serveur HTTP.
- **Erreurs RFC 9457.** Toute erreur de domaine hérite de
  `app.errors.DomainError` et traverse `services/` et `api/` sans être
  attrapée ailleurs que par les handlers globaux (tâche 1).
- **Dégradation, pas d'échec, sur une facette absente d'une séance.** Une
  séance sans fréquence cardiaque, sans longueurs de nage ou sans séries de
  musculation existe : ses endpoints de détail (`/hr-zones`, `/swim`,
  `/strength`) renvoient `200` avec `available: false` et une raison, jamais
  `404` — le `404` est réservé à une séance qui n'existe pas du tout.
- Tests : `analytics/` en tests unitaires purs (aucune fixture de base) ;
  `services/` et `api/` en tests d'intégration sur PostgreSQL jetable
  (`BA_TEST_DATABASE_URL`, skip si absent, fixtures déjà en place dans
  `tests/integration/conftest.py`). Les tests d'API utilisent
  `httpx.ASGITransport` contre `app.main.app`.

## Chiffres de référence des données réelles

Ces valeurs bornent les assertions des tests d'intégration et justifient les
garde-fous de validité codés dans `analytics/`.

| Grandeur | Valeur |
| --- | --- |
| Mesures corporelles | 647, dont 260 sans masse grasse/muscle (avant 2024) |
| Mesures avec masse grasse en kg / masse maigre en kg | 638 / 387 |
| Entrées alimentaires | 11 855, couvrant 100 % des 747 jours (2024-08-14 → 2026-08-30) |
| Jours avec au moins une pesée | 84 % |
| Séances | 4 734 |
| Séances avec échantillons (`has_samples`) | 2 314 avec fréquence cardiaque |
| Séances de natation / avec séries de musculation | 330 / 1 531 |
| Zones cardiaques valides en base (`sensing_status`) | 7 séances seulement — **toujours recalculer** |
| Relevés de FC de repos (`resting_hr`) | 2 509, 47 à 70 bpm sur 21 mois |
| Dépense estimée (TDEE), sèches 1 → 3 | ~2 840 → ~2 410 kcal/jour |
| Métabolisme de base observé | 1 548 à 1 729 kcal |
| Phases | 8 |

## Structure des fichiers

```
backend/app/
  errors.py                       hiérarchie d'exceptions de domaine
  analytics/
    __init__.py
    labels.py                     libellés meal_type / unit_code
    deltas.py                     deltas génériques sur série temporelle
    composition.py                recomposition corporelle en kilogrammes
    objectives.py                 sens d'atteinte des objectifs de phase
    energy.py                     TDEE, bilan énergétique quotidien
    hr_zones.py                   zones cardiaques calculées
    splits.py                     splits au kilomètre par interpolation
    swim.py                       SWOLF agrégé par type de nage
    strength.py                   volume et progression musculation
    records.py                    records par sport
    training_load.py              charge TRIMP, aiguë/chronique, dérive cardiaque
    nutrition.py                  fenêtre alimentaire, aliments récurrents
  schemas/
    __init__.py
    common.py                     Page, CursorPage génériques
    body.py
    nutrition.py
    phases.py
    workouts.py
    analytics.py                  schémas des analyses transverses
  services/
    __init__.py
    body.py
    nutrition.py
    phases.py
    workouts.py
    energy.py
    training_load.py
  api/
    __init__.py
    deps.py                       DateRange, DbSession, dépendances communes
    problem.py                    handlers RFC 9457
    router.py                     assemble tous les routers sous /api
    body.py
    nutrition.py
    phases.py
    workouts.py
    analytics.py
```

Découpage assumé : `analytics/` compte onze modules à raison d'une
préoccupation chacun — c'est délibérément plus de fichiers que de tâches
« naturelles », car chaque calcul (zones cardiaques, SWOLF, TRIMP...) a sa
propre logique de bord et mérite son propre test sans dépendre d'un autre.
`services/energy.py` et `services/training_load.py` sont séparés de
`services/workouts.py` et `services/body.py` parce qu'ils orchestrent
plusieurs tables à la fois (mesures, nutrition, séances) et appartiennent
aux analyses transverses de la spec section 5, pas à une seule ressource.

---

### Task 1: Hiérarchie d'exceptions de domaine et handlers RFC 9457

**Files:**
- Create: `backend/app/errors.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/problem.py`
- Create: `backend/tests/unit/test_problem.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: rien, première tâche du plan.
- Produces: `app.errors.DomainError` et ses sous-classes
  `NotFoundError`, `ValidationError`, `ConflictError` ;
  `app.api.problem.register_exception_handlers(app: FastAPI) -> None`.
  Toutes les tâches de service et d'API suivantes lèvent ces exceptions au
  lieu de retourner des codes HTTP directement.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_problem.py` :

```python
"""Vérifie que les exceptions de domaine deviennent du problem+json."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.problem import register_exception_handlers
from app.errors import NotFoundError, ValidationError


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/not-found")
    async def not_found() -> None:
        raise NotFoundError("séance 42 introuvable")

    @app.get("/boom/invalid")
    async def invalid() -> None:
        raise ValidationError("points doit être entre 1 et 5000")

    return app


def test_domain_error_becomes_problem_json() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["title"] == "Ressource introuvable"
    assert body["status"] == 404
    assert body["detail"] == "séance 42 introuvable"


def test_validation_error_is_422() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/invalid")

    assert response.status_code == 422
    assert response.json()["detail"] == "points doit être entre 1 et 5000"


def test_request_validation_error_is_also_problem_json() -> None:
    """Une requête mal formée (query param invalide) doit aussi produire du
    problem+json, pas le format d'erreur par défaut de FastAPI."""
    app = _build_app()

    @app.get("/boom/query")
    async def with_query(points: int) -> dict[str, int]:
        return {"points": points}

    client = TestClient(app)
    response = client.get("/boom/query", params={"points": "pas-un-entier"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Paramètres invalides"
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_problem.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.errors'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/errors.py` :

```python
"""Hiérarchie d'exceptions de domaine.

Ces exceptions traversent services/ et api/ sans être attrapées ailleurs
que par les handlers globaux de app.api.problem, qui les traduisent en
réponses RFC 9457 (application/problem+json).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base de toute erreur métier. Ne jamais lever directement."""

    status_code: int = 500
    title: str = "Erreur interne"


class NotFoundError(DomainError):
    status_code = 404
    title = "Ressource introuvable"


class ValidationError(DomainError):
    status_code = 422
    title = "Requête invalide"


class ConflictError(DomainError):
    status_code = 409
    title = "Conflit"
```

Créer `backend/app/api/__init__.py` vide.

Créer `backend/app/api/problem.py` :

```python
"""Handlers FastAPI traduisant les exceptions en RFC 9457.

application/problem+json, cf. spec section 6 : « Les erreurs suivent la RFC
9457, produites par des handlers FastAPI qui traduisent les exceptions du
domaine. »
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import DomainError

PROBLEM_CONTENT_TYPE = "application/problem+json"


def _problem_response(
    *, status_code: int, title: str, detail: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type=PROBLEM_CONTENT_TYPE,
        content={"type": "about:blank", "title": title, "status": status_code, "detail": detail},
    )


async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return _problem_response(status_code=exc.status_code, title=exc.title, detail=str(exc))


async def _request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    return _problem_response(
        status_code=422, title="Paramètres invalides", detail=detail or "requête invalide"
    )


def register_exception_handlers(app: FastAPI) -> None:
    """À appeler une fois depuis create_app()."""
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(RequestValidationError, _request_validation_handler)
```

Modifier `backend/app/main.py` :

```python
"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI

from app.api.problem import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")
    register_exception_handlers(app)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_problem.py tests/unit/test_health.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/errors.py backend/app/api backend/app/main.py backend/tests/unit/test_problem.py
git commit -m "feat: add domain exception hierarchy and RFC 9457 handlers"
```

---

### Task 2: Échafaudage des routers et dépendances communes

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/tests/unit/test_deps.py`
- Create: `backend/tests/unit/test_schemas_common.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `app.api.problem.register_exception_handlers` (tâche 1) ;
  `app.db.get_session` (plan 1, `app/db.py`).
- Produces: `app.api.deps.DateRange` (dataclasse `start: date | None`,
  `end: date | None`), `app.api.deps.date_range` (dépendance FastAPI),
  `app.api.deps.DbSession` (alias `Annotated[AsyncSession, Depends(get_session)]`),
  `app.api.deps.DateRangeDep` (alias `Annotated[DateRange, Depends(date_range)]`) ;
  `app.api.router.api_router` (`APIRouter(prefix="/api")`, vide au départ,
  chaque tâche d'endpoint y ajoute son routeur) ;
  `app.schemas.common.Page[T]`, `app.schemas.common.CursorPage[T]`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/test_deps.py` :

```python
"""Tests des dépendances communes aux routers de lecture."""

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import date_range


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/range")
    async def range_endpoint(r=None):  # noqa: ANN001
        from fastapi import Depends

        async def handler(r=Depends(date_range)):  # noqa: ANN001
            return {"start": r.start, "end": r.end}

        return await handler()

    return app


def test_date_range_parses_from_and_to() -> None:
    app = FastAPI()

    @app.get("/range")
    async def endpoint(r=__import__("fastapi").Depends(date_range)):  # noqa: ANN001
        return {"start": r.start, "end": r.end}

    client = TestClient(app)
    response = client.get("/range", params={"from": "2026-01-01", "to": "2026-01-31"})

    assert response.status_code == 200
    assert response.json() == {"start": "2026-01-01", "end": "2026-01-31"}


def test_date_range_defaults_to_none() -> None:
    app = FastAPI()

    @app.get("/range")
    async def endpoint(r=__import__("fastapi").Depends(date_range)):  # noqa: ANN001
        return {"start": r.start, "end": r.end}

    client = TestClient(app)
    response = client.get("/range")

    assert response.json() == {"start": None, "end": None}


def test_date_range_dataclass_fields() -> None:
    from app.api.deps import DateRange

    r = DateRange(start=date(2026, 1, 1), end=None)
    assert r.start == date(2026, 1, 1)
    assert r.end is None
```

Note : le premier test avorté `_build_app` ci-dessus n'est pas utilisé ; le
supprimer avant de finaliser le fichier — seules les trois fonctions `test_*`
comptent. Version finale simplifiée du fichier :

```python
"""Tests des dépendances communes aux routers de lecture."""

from datetime import date

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import DateRange, date_range


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/range")
    async def endpoint(r: DateRange = Depends(date_range)) -> dict[str, str | None]:
        return {
            "start": r.start.isoformat() if r.start else None,
            "end": r.end.isoformat() if r.end else None,
        }

    return app


def test_date_range_parses_from_and_to() -> None:
    client = TestClient(_build_app())

    response = client.get("/range", params={"from": "2026-01-01", "to": "2026-01-31"})

    assert response.status_code == 200
    assert response.json() == {"start": "2026-01-01", "end": "2026-01-31"}


def test_date_range_defaults_to_none() -> None:
    client = TestClient(_build_app())

    response = client.get("/range")

    assert response.json() == {"start": None, "end": None}


def test_date_range_dataclass_fields() -> None:
    r = DateRange(start=date(2026, 1, 1), end=None)

    assert r.start == date(2026, 1, 1)
    assert r.end is None
```

Créer `backend/tests/unit/test_schemas_common.py` :

```python
"""Tests des schémas Pydantic génériques partagés."""

from app.schemas.common import CursorPage, Page


def test_page_serializes_with_total() -> None:
    page = Page[int](items=[1, 2, 3], page=1, page_size=50, total=120)

    assert page.model_dump() == {
        "items": [1, 2, 3],
        "page": 1,
        "page_size": 50,
        "total": 120,
    }


def test_cursor_page_defaults_next_cursor_to_none() -> None:
    page = CursorPage[int](items=[1, 2, 3])

    assert page.next_cursor is None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_deps.py tests/unit/test_schemas_common.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.schemas'` (et
`app.api.deps` absent).

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/api/deps.py` :

```python
"""Dépendances communes aux routers de lecture."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date | None
    end: date | None


def date_range(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
) -> DateRange:
    return DateRange(start=from_, end=to)


DbSession = Annotated[AsyncSession, Depends(get_session)]
DateRangeDep = Annotated[DateRange, Depends(date_range)]
```

Créer `backend/app/api/router.py` :

```python
"""Assemble tous les routers de lecture sous le préfixe /api.

Chaque tâche d'endpoint ajoute ici l'inclusion de son propre routeur ; ce
fichier ne définit jamais de route lui-même.
"""

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")
```

Créer `backend/app/schemas/__init__.py` vide.

Créer `backend/app/schemas/common.py` :

```python
"""Schémas Pydantic génériques, réutilisés par toutes les familles."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Pagination par numéro de page (utilisée par /nutrition/entries)."""

    items: list[T]
    page: int
    page_size: int
    total: int


class CursorPage(BaseModel, Generic[T]):
    """Pagination par curseur opaque (utilisée par /workouts)."""

    items: list[T]
    next_cursor: str | None = None
```

Modifier `backend/app/main.py` pour inclure le routeur :

```python
"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI

from app.api.problem import register_exception_handlers
from app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_deps.py tests/unit/test_schemas_common.py tests/unit/test_health.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/api/deps.py backend/app/api/router.py backend/app/schemas backend/app/main.py backend/tests/unit/test_deps.py backend/tests/unit/test_schemas_common.py
git commit -m "feat: add shared api dependencies and generic pagination schemas"
```

---

### Task 3: Libellés nutrition (`analytics/labels.py`)

Traduit les codes bruts de l'export en libellés lisibles. Reste en
`analytics/` et non en base, comme précisé en spec section 4.2.

**Files:**
- Create: `backend/app/analytics/__init__.py`
- Create: `backend/app/analytics/labels.py`
- Create: `backend/tests/unit/analytics/__init__.py`
- Create: `backend/tests/unit/analytics/test_labels.py`

**Interfaces:**
- Consumes: rien.
- Produces: `meal_type_label(code: int | None) -> str`,
  `unit_label(code: int | None) -> str`, `MEAL_TYPE_LABELS: Mapping[int, str]`,
  `UNIT_LABELS: Mapping[int, str]`. Consommé par `services/nutrition.py`
  (tâches 17-18).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_labels.py` :

```python
"""Tests des libellés nutrition — codes relevés en spec section 4.2."""

import pytest

from app.analytics.labels import meal_type_label, unit_label


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (100001, "Petit-déjeuner"),
        (100002, "Déjeuner"),
        (100003, "Dîner"),
        (100004, "Collation"),
        (100005, "Collation matin"),
        (100006, "Collation soir"),
    ],
)
def test_known_meal_types(code: int, expected: str) -> None:
    assert meal_type_label(code) == expected


def test_unknown_meal_type_is_labelled_not_dropped() -> None:
    assert meal_type_label(999999) == "Autre"


def test_missing_meal_type_is_explicit() -> None:
    assert meal_type_label(None) == "Non renseigné"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (120001, "Grammes"),
        (120002, "Millilitres"),
        (120004, "Portion"),
        (120005, "Unité"),
        (-1, "Non spécifié"),
    ],
)
def test_known_units(code: int, expected: str) -> None:
    assert unit_label(code) == expected


def test_unknown_unit_is_labelled_not_dropped() -> None:
    assert unit_label(424242) == "Autre"


def test_missing_unit_is_explicit() -> None:
    assert unit_label(None) == "Non renseigné"
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_labels.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/__init__.py` vide.
Créer `backend/tests/unit/analytics/__init__.py` vide.

Créer `backend/app/analytics/labels.py` :

```python
"""Libellés lisibles pour les codes bruts de l'export nutrition.

Cette table de correspondance vit ici plutôt qu'en base (spec 4.2) : les
codes sont un détail du format Samsung, pas une donnée métier stable.
"""

from __future__ import annotations

from types import MappingProxyType

MEAL_TYPE_LABELS = MappingProxyType(
    {
        100001: "Petit-déjeuner",
        100002: "Déjeuner",
        100003: "Dîner",
        100004: "Collation",
        100005: "Collation matin",
        100006: "Collation soir",
    }
)

UNIT_LABELS = MappingProxyType(
    {
        120001: "Grammes",
        120002: "Millilitres",
        120004: "Portion",
        120005: "Unité",
        -1: "Non spécifié",
    }
)

UNKNOWN = "Autre"
MISSING = "Non renseigné"


def meal_type_label(code: int | None) -> str:
    if code is None:
        return MISSING
    return MEAL_TYPE_LABELS.get(code, UNKNOWN)


def unit_label(code: int | None) -> str:
    if code is None:
        return MISSING
    return UNIT_LABELS.get(code, UNKNOWN)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_labels.py -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics backend/tests/unit/analytics
git commit -m "feat: add nutrition code label lookups"
```

---

### Task 4: Deltas génériques sur série temporelle (`analytics/deltas.py`)

**Files:**
- Create: `backend/app/analytics/deltas.py`
- Create: `backend/tests/unit/analytics/test_deltas.py`

**Interfaces:**
- Consumes: rien.
- Produces: `TimePoint(at: date, value: float | None)`,
  `Delta(window_days: int, start_value: float | None, end_value: float | None, change: float | None)`,
  `find_nearest_at_or_before(points: Sequence[TimePoint], target: date) -> TimePoint | None`,
  `compute_delta(points: Sequence[TimePoint], *, reference: date, window_days: int) -> Delta`,
  `compute_change_between(points: Sequence[TimePoint], *, start: date, end: date) -> Delta`.
  Consommé par `services/body.py` (résumé, tâche 19) et
  `analytics/objectives.py` (tâche 6, rapport de phase).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_deltas.py` :

```python
"""Tests des deltas génériques sur série temporelle à trous."""

from datetime import date

from app.analytics.deltas import (
    TimePoint,
    compute_change_between,
    compute_delta,
    find_nearest_at_or_before,
)

POINTS = [
    TimePoint(at=date(2026, 1, 1), value=80.0),
    TimePoint(at=date(2026, 1, 10), value=None),  # trou : jamais de zéro de substitution
    TimePoint(at=date(2026, 1, 15), value=78.5),
    TimePoint(at=date(2026, 1, 31), value=77.0),
]


def test_find_nearest_at_or_before_exact_match() -> None:
    result = find_nearest_at_or_before(POINTS, date(2026, 1, 15))

    assert result == TimePoint(at=date(2026, 1, 15), value=78.5)


def test_find_nearest_at_or_before_skips_null_values() -> None:
    """Le point du 10 janvier existe mais sa valeur est None : on ne doit
    jamais le retenir, sous peine de propager un trou comme s'il valait 0."""
    result = find_nearest_at_or_before(POINTS, date(2026, 1, 12))

    assert result == TimePoint(at=date(2026, 1, 1), value=80.0)


def test_find_nearest_at_or_before_returns_none_when_too_early() -> None:
    result = find_nearest_at_or_before(POINTS, date(2025, 12, 31))

    assert result is None


def test_compute_delta_over_window() -> None:
    delta = compute_delta(POINTS, reference=date(2026, 1, 31), window_days=30)

    assert delta.window_days == 30
    assert delta.start_value == 80.0
    assert delta.end_value == 77.0
    assert delta.change == -3.0


def test_compute_delta_is_none_when_window_predates_data() -> None:
    delta = compute_delta(POINTS, reference=date(2026, 1, 5), window_days=90)

    assert delta.start_value is None
    assert delta.end_value == 80.0
    assert delta.change is None


def test_compute_change_between_explicit_dates() -> None:
    delta = compute_change_between(POINTS, start=date(2026, 1, 1), end=date(2026, 1, 15))

    assert delta.window_days == 14
    assert delta.start_value == 80.0
    assert delta.end_value == 78.5
    assert delta.change == -1.5


def test_compute_change_between_empty_series_is_all_none() -> None:
    delta = compute_change_between([], start=date(2026, 1, 1), end=date(2026, 1, 15))

    assert delta.start_value is None
    assert delta.end_value is None
    assert delta.change is None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_deltas.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.deltas'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/deltas.py` :

```python
"""Deltas génériques sur une série temporelle pouvant contenir des trous.

Une valeur absente (None) n'est jamais traitée comme zéro : chercher « le
point le plus proche » ignore les points sans valeur plutôt que de les
retenir comme s'ils valaient 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TimePoint:
    at: date
    value: float | None


@dataclass(frozen=True, slots=True)
class Delta:
    window_days: int
    start_value: float | None
    end_value: float | None
    change: float | None


def find_nearest_at_or_before(
    points: Sequence[TimePoint], target: date
) -> TimePoint | None:
    candidates = [p for p in points if p.value is not None and p.at <= target]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.at)


def _delta_between(
    points: Sequence[TimePoint], *, start: date, end: date, window_days: int
) -> Delta:
    start_point = find_nearest_at_or_before(points, start)
    end_point = find_nearest_at_or_before(points, end)
    change = None
    if start_point is not None and end_point is not None:
        change = end_point.value - start_point.value
    return Delta(
        window_days=window_days,
        start_value=start_point.value if start_point else None,
        end_value=end_point.value if end_point else None,
        change=change,
    )


def compute_delta(
    points: Sequence[TimePoint], *, reference: date, window_days: int
) -> Delta:
    start = reference - timedelta(days=window_days)
    return _delta_between(points, start=start, end=reference, window_days=window_days)


def compute_change_between(
    points: Sequence[TimePoint], *, start: date, end: date
) -> Delta:
    return _delta_between(points, start=start, end=end, window_days=(end - start).days)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_deltas.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/deltas.py backend/tests/unit/analytics/test_deltas.py
git commit -m "feat: add generic time series delta computation"
```

---

### Task 5: Recomposition corporelle en kilogrammes (`analytics/composition.py`)

Répond à la spec 5.2 : exposer les deltas en kilos de masse grasse et de
masse maigre, pas seulement le pourcentage.

**Files:**
- Create: `backend/app/analytics/composition.py`
- Create: `backend/tests/unit/analytics/test_composition.py`

**Interfaces:**
- Consumes: rien (dataclasses propres, structure proche de `TimePoint` mais
  à deux valeurs).
- Produces: `CompositionPoint(at: date, fat_mass_kg: float | None, lean_mass_kg: float | None)`,
  `RecompositionResult(fat_mass_delta_kg: float | None, lean_mass_delta_kg: float | None)`,
  `compute_recomposition(points: Sequence[CompositionPoint], *, start: date, end: date) -> RecompositionResult`.
  Consommé par `services/body.py` (`/body/composition`, tâche 32) et
  `services/phases.py` (rapport de phase, tâche 20).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_composition.py` :

```python
"""Tests de la recomposition corporelle — spec 5.2.

La grandeur qui compte pendant une sèche n'est pas le pourcentage de masse
grasse (ambigu, il bouge aussi quand la masse maigre bouge) mais les deltas
en kilos des deux masses.
"""

from datetime import date

from app.analytics.composition import CompositionPoint, compute_recomposition

POINTS = [
    CompositionPoint(at=date(2026, 1, 1), fat_mass_kg=18.0, lean_mass_kg=62.0),
    CompositionPoint(at=date(2026, 1, 15), fat_mass_kg=None, lean_mass_kg=None),
    CompositionPoint(at=date(2026, 2, 1), fat_mass_kg=15.5, lean_mass_kg=61.2),
]


def test_recomposition_reports_fat_and_lean_deltas_in_kg() -> None:
    result = compute_recomposition(POINTS, start=date(2026, 1, 1), end=date(2026, 2, 1))

    assert result.fat_mass_delta_kg == -2.5
    assert result.lean_mass_delta_kg == -0.8


def test_recomposition_is_none_without_data_at_either_end() -> None:
    result = compute_recomposition(POINTS, start=date(2025, 1, 1), end=date(2025, 2, 1))

    assert result.fat_mass_delta_kg is None
    assert result.lean_mass_delta_kg is None


def test_recomposition_never_substitutes_zero_for_missing_side() -> None:
    """Si seule la masse grasse est connue à une date, le delta de masse
    maigre reste None : jamais de zéro inventé."""
    points = [
        CompositionPoint(at=date(2026, 1, 1), fat_mass_kg=18.0, lean_mass_kg=None),
        CompositionPoint(at=date(2026, 2, 1), fat_mass_kg=15.5, lean_mass_kg=61.2),
    ]

    result = compute_recomposition(points, start=date(2026, 1, 1), end=date(2026, 2, 1))

    assert result.fat_mass_delta_kg == -2.5
    assert result.lean_mass_delta_kg is None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_composition.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.composition'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/composition.py` :

```python
"""Recomposition corporelle en kilogrammes — spec 5.2.

L'application historique n'affichait que le pourcentage de masse grasse.
Exposer les deltas en kilos de masse grasse et de masse maigre répond à la
seule question qui compte pendant une sèche : la perte vient-elle du gras
ou du muscle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True, slots=True)
class CompositionPoint:
    at: date
    fat_mass_kg: float | None
    lean_mass_kg: float | None


@dataclass(frozen=True, slots=True)
class RecompositionResult:
    fat_mass_delta_kg: float | None
    lean_mass_delta_kg: float | None


def _nearest_value(
    points: Sequence[CompositionPoint], target: date, field: str
) -> float | None:
    candidates = [
        p for p in points if getattr(p, field) is not None and p.at <= target
    ]
    if not candidates:
        return None
    return getattr(max(candidates, key=lambda p: p.at), field)


def compute_recomposition(
    points: Sequence[CompositionPoint], *, start: date, end: date
) -> RecompositionResult:
    fat_start = _nearest_value(points, start, "fat_mass_kg")
    fat_end = _nearest_value(points, end, "fat_mass_kg")
    lean_start = _nearest_value(points, start, "lean_mass_kg")
    lean_end = _nearest_value(points, end, "lean_mass_kg")

    fat_delta = fat_end - fat_start if fat_start is not None and fat_end is not None else None
    lean_delta = (
        lean_end - lean_start if lean_start is not None and lean_end is not None else None
    )
    return RecompositionResult(fat_mass_delta_kg=fat_delta, lean_mass_delta_kg=lean_delta)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_composition.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/composition.py backend/tests/unit/analytics/test_composition.py
git commit -m "feat: add body recomposition deltas in kilograms"
```

---

### Task 6: Sens d'atteinte des objectifs de phase (`analytics/objectives.py`)

Tâche la plus sensible du plan (spec 6, « Sens d'atteinte d'un objectif ») :
une inversion silencieuse fausserait tous les verdicts de la page Objectifs.

**Files:**
- Create: `backend/app/analytics/objectives.py`
- Create: `backend/tests/unit/analytics/test_objectives.py`

**Interfaces:**
- Consumes: `app.models.phase.PhaseKind` (plan 1) ; `Delta` (tâche 4, pour
  `build_phase_metric_report`).
- Produces: `Metric` (enum `WEIGHT`, `BODY_FAT`, `MUSCLE`), `Direction`
  (enum `UP`, `DOWN`), `achievement_direction(phase_kind: PhaseKind, metric: Metric) -> Direction`,
  `ObjectiveCheck(metric: Metric, target: float, current: float | None, direction: Direction, achieved: bool | None, remaining: float | None)`,
  `evaluate_objective(*, phase_kind: PhaseKind, metric: Metric, target: float, current: float | None) -> ObjectiveCheck`,
  `PhaseMetricReport(metric, start_value, end_value, change, change_pct, monthly_rate, objective)`,
  `build_phase_metric_report(*, metric: Metric, delta: Delta, days_elapsed: int, phase_kind: PhaseKind, target: float | None) -> PhaseMetricReport`.
  Consommé par `services/phases.py` (tâches 20-21) et `services/body.py`
  (résumé, tâche 19).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_objectives.py` :

```python
"""Tests du sens d'atteinte des objectifs — spec 6.

Règle : en sèche, le poids cible est un plancher atteint en descendant ; en
prise de masse, un plafond atteint en montant ; la masse musculaire
s'atteint toujours vers le haut ; la masse grasse toujours vers le bas.
"""

import pytest

from app.analytics.deltas import Delta
from app.analytics.objectives import (
    Direction,
    Metric,
    achievement_direction,
    build_phase_metric_report,
    evaluate_objective,
)
from app.models.phase import PhaseKind


@pytest.mark.parametrize(
    ("phase_kind", "expected"),
    [(PhaseKind.CUT, Direction.DOWN), (PhaseKind.BULK, Direction.UP)],
)
def test_weight_direction_depends_on_phase_kind(
    phase_kind: PhaseKind, expected: Direction
) -> None:
    assert achievement_direction(phase_kind, Metric.WEIGHT) is expected


@pytest.mark.parametrize("phase_kind", list(PhaseKind))
def test_muscle_direction_is_always_up(phase_kind: PhaseKind) -> None:
    assert achievement_direction(phase_kind, Metric.MUSCLE) is Direction.UP


@pytest.mark.parametrize("phase_kind", list(PhaseKind))
def test_body_fat_direction_is_always_down(phase_kind: PhaseKind) -> None:
    assert achievement_direction(phase_kind, Metric.BODY_FAT) is Direction.DOWN


def test_cut_weight_target_achieved_when_current_at_or_below_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.CUT, metric=Metric.WEIGHT, target=75.0, current=74.5
    )

    assert check.direction is Direction.DOWN
    assert check.achieved is True


def test_cut_weight_target_not_achieved_when_current_above_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.CUT, metric=Metric.WEIGHT, target=75.0, current=76.2
    )

    assert check.achieved is False


def test_bulk_weight_target_achieved_when_current_at_or_above_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.BULK, metric=Metric.WEIGHT, target=85.0, current=85.3
    )

    assert check.achieved is True


def test_bulk_weight_target_not_achieved_when_current_below_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.BULK, metric=Metric.WEIGHT, target=85.0, current=83.0
    )

    assert check.achieved is False


@pytest.mark.parametrize("phase_kind", [PhaseKind.CUT, PhaseKind.BULK])
def test_muscle_target_achieved_upward_regardless_of_phase_kind(
    phase_kind: PhaseKind,
) -> None:
    """Verrou explicite de la règle : la sèche inverse le sens du poids mais
    jamais celui du muscle."""
    achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.MUSCLE, target=35.0, current=35.4
    )
    not_achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.MUSCLE, target=35.0, current=34.1
    )

    assert achieved.achieved is True
    assert not_achieved.achieved is False


@pytest.mark.parametrize("phase_kind", [PhaseKind.CUT, PhaseKind.BULK])
def test_body_fat_target_achieved_downward_regardless_of_phase_kind(
    phase_kind: PhaseKind,
) -> None:
    achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.BODY_FAT, target=12.0, current=11.5
    )
    not_achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.BODY_FAT, target=12.0, current=13.0
    )

    assert achieved.achieved is True
    assert not_achieved.achieved is False


def test_unknown_current_value_leaves_achieved_undetermined() -> None:
    """260 mesures réelles n'ont ni masse grasse ni muscle : l'objectif ne
    doit jamais se déclarer manqué faute de donnée, il doit rester None."""
    check = evaluate_objective(
        phase_kind=PhaseKind.CUT, metric=Metric.BODY_FAT, target=12.0, current=None
    )

    assert check.achieved is None
    assert check.remaining is None


def test_build_phase_metric_report_computes_rate_and_pct() -> None:
    delta = Delta(window_days=61, start_value=80.0, end_value=77.0, change=-3.0)

    report = build_phase_metric_report(
        metric=Metric.WEIGHT,
        delta=delta,
        days_elapsed=61,
        phase_kind=PhaseKind.CUT,
        target=75.0,
    )

    assert report.change == -3.0
    assert report.change_pct == pytest.approx(-3.75, rel=1e-3)
    assert report.monthly_rate == pytest.approx(-1.4967, rel=1e-3)
    assert report.objective is not None
    assert report.objective.achieved is False


def test_build_phase_metric_report_without_target_has_no_objective() -> None:
    delta = Delta(window_days=30, start_value=80.0, end_value=79.0, change=-1.0)

    report = build_phase_metric_report(
        metric=Metric.WEIGHT,
        delta=delta,
        days_elapsed=30,
        phase_kind=PhaseKind.CUT,
        target=None,
    )

    assert report.objective is None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_objectives.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.objectives'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/objectives.py` :

```python
"""Sens d'atteinte des objectifs de phase — spec section 6.

La comparaison à la cible dépend du type de phase ET de la métrique : en
sèche le poids est un plancher atteint en descendant, en prise de masse un
plafond atteint en montant. La masse musculaire s'atteint toujours vers le
haut, la masse grasse toujours vers le bas, quel que soit le type de phase.

La spec ne tranche explicitement que sèche et prise de masse pour le poids.
Décision pour maintien et libre (silence de la spec) : même convention que
la sèche (plancher, descendant) — un maintien fait suite à une sèche dans
les données réelles et vise à ne pas remonter au-delà du poids atteint.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from app.analytics.deltas import Delta
from app.models.phase import PhaseKind


class Metric(enum.StrEnum):
    WEIGHT = "weight"
    BODY_FAT = "body_fat"
    MUSCLE = "muscle"


class Direction(enum.StrEnum):
    UP = "up"
    DOWN = "down"


_WEIGHT_DIRECTION_BY_KIND: dict[PhaseKind, Direction] = {
    PhaseKind.CUT: Direction.DOWN,
    PhaseKind.BULK: Direction.UP,
    PhaseKind.MAINTAIN: Direction.DOWN,
    PhaseKind.FREE: Direction.DOWN,
}


def achievement_direction(phase_kind: PhaseKind, metric: Metric) -> Direction:
    if metric is Metric.MUSCLE:
        return Direction.UP
    if metric is Metric.BODY_FAT:
        return Direction.DOWN
    return _WEIGHT_DIRECTION_BY_KIND[phase_kind]


@dataclass(frozen=True, slots=True)
class ObjectiveCheck:
    metric: Metric
    target: float
    current: float | None
    direction: Direction
    achieved: bool | None
    remaining: float | None


def evaluate_objective(
    *, phase_kind: PhaseKind, metric: Metric, target: float, current: float | None
) -> ObjectiveCheck:
    direction = achievement_direction(phase_kind, metric)
    if current is None:
        return ObjectiveCheck(
            metric=metric,
            target=target,
            current=None,
            direction=direction,
            achieved=None,
            remaining=None,
        )
    achieved = current <= target if direction is Direction.DOWN else current >= target
    remaining = target - current
    return ObjectiveCheck(
        metric=metric,
        target=target,
        current=current,
        direction=direction,
        achieved=achieved,
        remaining=remaining,
    )


@dataclass(frozen=True, slots=True)
class PhaseMetricReport:
    metric: Metric
    start_value: float | None
    end_value: float | None
    change: float | None
    change_pct: float | None
    monthly_rate: float | None
    objective: ObjectiveCheck | None


_DAYS_PER_MONTH = 30.44


def build_phase_metric_report(
    *,
    metric: Metric,
    delta: Delta,
    days_elapsed: int,
    phase_kind: PhaseKind,
    target: float | None,
) -> PhaseMetricReport:
    change_pct = None
    if delta.change is not None and delta.start_value not in (None, 0):
        change_pct = delta.change / delta.start_value * 100

    monthly_rate = None
    if delta.change is not None and days_elapsed > 0:
        monthly_rate = delta.change / days_elapsed * _DAYS_PER_MONTH

    objective = None
    if target is not None:
        objective = evaluate_objective(
            phase_kind=phase_kind, metric=metric, target=target, current=delta.end_value
        )

    return PhaseMetricReport(
        metric=metric,
        start_value=delta.start_value,
        end_value=delta.end_value,
        change=delta.change,
        change_pct=change_pct,
        monthly_rate=monthly_rate,
        objective=objective,
    )
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_objectives.py -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/objectives.py backend/tests/unit/analytics/test_objectives.py
git commit -m "feat: add phase objective achievement direction rules"
```

---

### Task 7: Dépense énergétique estimée (`analytics/energy.py`)

Répond à la spec 5.1 : `TDEE ≈ apport moyen − pente(kg/jour) × 7700`, avec
garde-fous de validité et incertitude affichée explicitement. Contient aussi
la composition du bilan énergétique quotidien (apport contre dépense)
consommée par `/analytics/energy-balance` (tâche 33).

**Files:**
- Create: `backend/app/analytics/energy.py`
- Create: `backend/tests/unit/analytics/test_energy.py`

**Interfaces:**
- Consumes: rien.
- Produces: `KCAL_PER_KG = 7700`, `MIN_LOGGED_DAYS = 21`, `MIN_WEIGH_INS = 10`,
  `DailyIntake(day: date, calories: float | None)`,
  `WeighIn(day: date, weight_kg: float | None)`,
  `TdeeEstimate(tdee_kcal, mean_intake_kcal, weight_slope_kg_per_day, is_valid: bool, reason: str | None, uncertainty_note: str)`,
  `estimate_tdee(intakes: Sequence[DailyIntake], weigh_ins: Sequence[WeighIn]) -> TdeeEstimate`,
  `DailyBmr(day: date, bmr_kcal: float | None)`,
  `forward_fill_bmr(points: Sequence[DailyBmr]) -> dict[date, float | None]`,
  `EnergyBalanceDay(day: date, intake_kcal: float | None, expenditure_kcal: float | None, balance_kcal: float | None)`,
  `compute_energy_balance(intakes: Sequence[DailyIntake], bmr_points: Sequence[DailyBmr], workout_kcal_by_day: Mapping[date, float]) -> list[EnergyBalanceDay]`.
  Consommé par `services/energy.py` (tâche 33).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_energy.py` :

```python
"""Tests de l'estimation de dépense énergétique — spec 5.1.

TDEE ≈ apport moyen − pente(kg/jour) × 7700. Les séries synthétiques sont
construites pour que le résultat se calcule à la main.
"""

from datetime import date, timedelta

import pytest

from app.analytics.energy import (
    KCAL_PER_KG,
    MIN_LOGGED_DAYS,
    MIN_WEIGH_INS,
    DailyBmr,
    DailyIntake,
    WeighIn,
    compute_energy_balance,
    estimate_tdee,
    forward_fill_bmr,
)


def _daily_series(start: date, n: int, value_at: "callable") -> list:
    return [start + timedelta(days=i) for i in range(n)]


def test_estimate_tdee_on_hand_computed_linear_series() -> None:
    """30 jours, poids décroissant de pile 0.1 kg/jour, apport constant à
    2000 kcal. Pente = -0.1 kg/jour, donc TDEE = 2000 - (-0.1 * 7700)
    = 2000 + 770 = 2770 kcal/jour."""
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0) for i in range(30)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0 - 0.1 * i)
        for i in range(30)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.is_valid is True
    assert result.mean_intake_kcal == pytest.approx(2000.0)
    assert result.weight_slope_kg_per_day == pytest.approx(-0.1, abs=1e-9)
    assert result.tdee_kcal == pytest.approx(2770.0, abs=1e-6)
    assert result.reason is None
    assert "7700" in result.uncertainty_note


def test_estimate_tdee_invalid_below_minimum_logged_days() -> None:
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0)
        for i in range(MIN_LOGGED_DAYS - 1)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0 - 0.1 * i)
        for i in range(MIN_WEIGH_INS + 5)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.is_valid is False
    assert result.tdee_kcal is None
    assert "journalisé" in result.reason or "pesée" in result.reason


def test_estimate_tdee_invalid_below_minimum_weigh_ins() -> None:
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0)
        for i in range(MIN_LOGGED_DAYS + 5)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0)
        for i in range(MIN_WEIGH_INS - 1)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.is_valid is False
    assert result.tdee_kcal is None


def test_estimate_tdee_ignores_null_intake_days_in_mean() -> None:
    """Un jour non journalisé doit sortir de la moyenne, pas y entrer comme
    zéro calorie — sinon la moyenne s'effondre artificiellement."""
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0 if i % 2 == 0 else None)
        for i in range(40)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0) for i in range(MIN_WEIGH_INS + 2)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.mean_intake_kcal == pytest.approx(2000.0)


def test_forward_fill_bmr_propagates_last_known_value() -> None:
    points = [
        DailyBmr(day=date(2026, 1, 1), bmr_kcal=1600.0),
        DailyBmr(day=date(2026, 1, 2), bmr_kcal=None),
        DailyBmr(day=date(2026, 1, 3), bmr_kcal=1580.0),
    ]

    filled = forward_fill_bmr(points)

    assert filled[date(2026, 1, 1)] == 1600.0
    assert filled[date(2026, 1, 2)] == 1600.0
    assert filled[date(2026, 1, 3)] == 1580.0


def test_forward_fill_bmr_is_none_before_first_known_value() -> None:
    points = [
        DailyBmr(day=date(2026, 1, 1), bmr_kcal=None),
        DailyBmr(day=date(2026, 1, 2), bmr_kcal=1600.0),
    ]

    filled = forward_fill_bmr(points)

    assert filled[date(2026, 1, 1)] is None
    assert filled[date(2026, 1, 2)] == 1600.0


def test_compute_energy_balance_combines_intake_bmr_and_workout_calories() -> None:
    day = date(2026, 1, 1)
    intakes = [DailyIntake(day=day, calories=2200.0)]
    bmr_points = [DailyBmr(day=day, bmr_kcal=1600.0)]
    workout_kcal_by_day = {day: 400.0}

    balance = compute_energy_balance(intakes, bmr_points, workout_kcal_by_day)

    assert len(balance) == 1
    assert balance[0].intake_kcal == 2200.0
    assert balance[0].expenditure_kcal == 2000.0
    assert balance[0].balance_kcal == 200.0


def test_compute_energy_balance_defaults_missing_workout_calories_to_zero() -> None:
    """L'absence de séance un jour donné vaut 0 kcal d'exercice ce jour-là,
    ce n'est pas une mesure manquante — cf. contrainte globale du plan."""
    day = date(2026, 1, 1)
    balance = compute_energy_balance(
        [DailyIntake(day=day, calories=2000.0)], [DailyBmr(day=day, bmr_kcal=1500.0)], {}
    )

    assert balance[0].expenditure_kcal == 1500.0


def test_compute_energy_balance_expenditure_is_none_without_bmr() -> None:
    """Sans BMR connu (avant la première mesure exploitable), la dépense ne
    doit jamais être devinée : elle reste None."""
    day = date(2026, 1, 1)
    balance = compute_energy_balance(
        [DailyIntake(day=day, calories=2000.0)], [DailyBmr(day=day, bmr_kcal=None)], {}
    )

    assert balance[0].expenditure_kcal is None
    assert balance[0].balance_kcal is None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_energy.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.energy'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/energy.py` :

```python
"""Dépense énergétique estimée et bilan quotidien — spec section 5.1.

TDEE ≈ apport moyen − pente(kg/jour) × 7700. Le facteur 7700 kcal par kg est
une approximation : l'incertitude est retournée explicitement plutôt que
dissimulée derrière un chiffre unique.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

KCAL_PER_KG = 7700
MIN_LOGGED_DAYS = 21
MIN_WEIGH_INS = 10
UNCERTAINTY_NOTE = (
    "Estimation approximative : le facteur 7700 kcal/kg est une "
    "simplification, et les variations d'hydratation dominent le signal "
    "sur les fenêtres courtes."
)


@dataclass(frozen=True, slots=True)
class DailyIntake:
    day: date
    calories: float | None


@dataclass(frozen=True, slots=True)
class WeighIn:
    day: date
    weight_kg: float | None


@dataclass(frozen=True, slots=True)
class TdeeEstimate:
    tdee_kcal: float | None
    mean_intake_kcal: float | None
    weight_slope_kg_per_day: float | None
    is_valid: bool
    reason: str | None
    uncertainty_note: str


def _linear_regression_slope(points: Sequence[tuple[date, float]]) -> float:
    xs = [p[0].toordinal() for p in points]
    ys = [p[1] for p in points]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    return numerator / denominator if denominator else 0.0


def estimate_tdee(
    intakes: Sequence[DailyIntake], weigh_ins: Sequence[WeighIn]
) -> TdeeEstimate:
    logged = [i for i in intakes if i.calories is not None]
    weighed = [w for w in weigh_ins if w.weight_kg is not None]

    if len(logged) < MIN_LOGGED_DAYS or len(weighed) < MIN_WEIGH_INS:
        reason = (
            f"fenêtre insuffisante : {len(logged)} jours journalisés "
            f"(minimum {MIN_LOGGED_DAYS}) et {len(weighed)} pesées "
            f"(minimum {MIN_WEIGH_INS})"
        )
        return TdeeEstimate(None, None, None, False, reason, UNCERTAINTY_NOTE)

    mean_intake = sum(i.calories for i in logged) / len(logged)
    slope = _linear_regression_slope([(w.day, w.weight_kg) for w in weighed])
    tdee = mean_intake - slope * KCAL_PER_KG
    return TdeeEstimate(tdee, mean_intake, slope, True, None, UNCERTAINTY_NOTE)


@dataclass(frozen=True, slots=True)
class DailyBmr:
    day: date
    bmr_kcal: float | None


def forward_fill_bmr(points: Sequence[DailyBmr]) -> dict[date, float | None]:
    ordered = sorted(points, key=lambda p: p.day)
    filled: dict[date, float | None] = {}
    last_known: float | None = None
    for point in ordered:
        if point.bmr_kcal is not None:
            last_known = point.bmr_kcal
        filled[point.day] = last_known
    return filled


@dataclass(frozen=True, slots=True)
class EnergyBalanceDay:
    day: date
    intake_kcal: float | None
    expenditure_kcal: float | None
    balance_kcal: float | None


def compute_energy_balance(
    intakes: Sequence[DailyIntake],
    bmr_points: Sequence[DailyBmr],
    workout_kcal_by_day: Mapping[date, float],
) -> list[EnergyBalanceDay]:
    bmr_by_day = forward_fill_bmr(bmr_points)
    result = []
    for intake in intakes:
        bmr = bmr_by_day.get(intake.day)
        expenditure = None
        if bmr is not None:
            expenditure = bmr + workout_kcal_by_day.get(intake.day, 0.0)
        balance = None
        if intake.calories is not None and expenditure is not None:
            balance = intake.calories - expenditure
        result.append(
            EnergyBalanceDay(
                day=intake.day,
                intake_kcal=intake.calories,
                expenditure_kcal=expenditure,
                balance_kcal=balance,
            )
        )
    return result
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_energy.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/energy.py backend/tests/unit/analytics/test_energy.py
git commit -m "feat: add TDEE estimation and daily energy balance"
```

---

### Task 8: Zones cardiaques calculées (`analytics/hr_zones.py`)

Les zones stockées en base ne sont valides que sur 7 séances : ce module les
recalcule à partir de `max_hr` et des échantillons, ce qui les rend
disponibles sur les 2 314 séances porteuses de fréquence cardiaque.

**Files:**
- Create: `backend/app/analytics/hr_zones.py`
- Create: `backend/tests/unit/analytics/test_hr_zones.py`

**Interfaces:**
- Consumes: rien.
- Produces: `HrZoneBoundary(zone: int, label: str, lower_bpm: int, upper_bpm: int | None)`,
  `hr_zone_boundaries(max_hr: int) -> list[HrZoneBoundary]`,
  `HrZoneTime(zone: int, label: str, seconds: float)`,
  `compute_hr_zone_times(samples: Sequence[tuple[datetime, int | None]], *, max_hr: int) -> list[HrZoneTime]`.
  Consommé par `services/workouts.py` (`/workouts/{id}/hr-zones`, tâche 27).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_hr_zones.py` :

```python
"""Tests des zones cardiaques calculées — spec 4.4 et 6.

Modèle à cinq zones par pourcentage de FC max, standard d'entraînement.
max_hr=180 donne des bornes rondes : 108, 126, 144, 162.
"""

from datetime import datetime, timedelta, timezone

from app.analytics.hr_zones import compute_hr_zone_times, hr_zone_boundaries

T0 = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def test_hr_zone_boundaries_for_max_180() -> None:
    boundaries = hr_zone_boundaries(180)

    assert [b.lower_bpm for b in boundaries] == [0, 108, 126, 144, 162]
    assert [b.upper_bpm for b in boundaries] == [108, 126, 144, 162, None]
    assert boundaries[0].label == "Récupération"
    assert boundaries[-1].label == "Maximal"


def test_compute_hr_zone_times_attributes_interval_to_starting_zone() -> None:
    """Quatre échantillons espacés de 60 s : 100 (zone 1), 115 (zone 2),
    135 (zone 3), 155 (zone 4). Chaque intervalle de 60 s est attribué à la
    zone de l'échantillon de départ ; le dernier échantillon ne clôt aucun
    intervalle."""
    samples = [
        (T0, 100),
        (T0 + timedelta(seconds=60), 115),
        (T0 + timedelta(seconds=120), 135),
        (T0 + timedelta(seconds=180), 155),
    ]

    zones = compute_hr_zone_times(samples, max_hr=180)
    seconds_by_zone = {z.zone: z.seconds for z in zones}

    assert seconds_by_zone[1] == 60.0
    assert seconds_by_zone[2] == 60.0
    assert seconds_by_zone[3] == 60.0
    assert seconds_by_zone[4] == 0.0
    assert seconds_by_zone[5] == 0.0


def test_compute_hr_zone_times_skips_samples_without_heart_rate() -> None:
    samples = [(T0, None), (T0 + timedelta(seconds=60), None)]

    zones = compute_hr_zone_times(samples, max_hr=180)

    assert all(z.seconds == 0.0 for z in zones)


def test_compute_hr_zone_times_returns_all_five_zones_even_when_unused() -> None:
    zones = compute_hr_zone_times([], max_hr=180)

    assert [z.zone for z in zones] == [1, 2, 3, 4, 5]
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_hr_zones.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.hr_zones'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/hr_zones.py` :

```python
"""Zones cardiaques calculées à partir de max_hr et des échantillons.

Les zones stockées dans sensing_status ne sont valides que sur 7 séances
réelles (spec 4.4) : on les recalcule systématiquement selon le modèle
standard à cinq zones par pourcentage de fréquence cardiaque maximale.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

_ZONE_DEFINITIONS = (
    (1, "Récupération", 0.0, 0.6),
    (2, "Endurance", 0.6, 0.7),
    (3, "Tempo", 0.7, 0.8),
    (4, "Seuil", 0.8, 0.9),
    (5, "Maximal", 0.9, None),
)


@dataclass(frozen=True, slots=True)
class HrZoneBoundary:
    zone: int
    label: str
    lower_bpm: int
    upper_bpm: int | None


def hr_zone_boundaries(max_hr: int) -> list[HrZoneBoundary]:
    boundaries = []
    for zone, label, lower_pct, upper_pct in _ZONE_DEFINITIONS:
        lower_bpm = round(lower_pct * max_hr)
        upper_bpm = round(upper_pct * max_hr) if upper_pct is not None else None
        boundaries.append(HrZoneBoundary(zone, label, lower_bpm, upper_bpm))
    return boundaries


def _zone_for(hr: int, boundaries: list[HrZoneBoundary]) -> int:
    for boundary in boundaries:
        if hr >= boundary.lower_bpm and (
            boundary.upper_bpm is None or hr < boundary.upper_bpm
        ):
            return boundary.zone
    return boundaries[0].zone


@dataclass(frozen=True, slots=True)
class HrZoneTime:
    zone: int
    label: str
    seconds: float


def compute_hr_zone_times(
    samples: Sequence[tuple[datetime, int | None]], *, max_hr: int
) -> list[HrZoneTime]:
    boundaries = hr_zone_boundaries(max_hr)
    seconds_by_zone = {b.zone: 0.0 for b in boundaries}

    valid = sorted((s for s in samples if s[1] is not None), key=lambda s: s[0])
    for (at0, hr0), (at1, _hr1) in zip(valid, valid[1:]):
        elapsed = (at1 - at0).total_seconds()
        if elapsed <= 0:
            continue
        seconds_by_zone[_zone_for(hr0, boundaries)] += elapsed

    return [
        HrZoneTime(zone=b.zone, label=b.label, seconds=seconds_by_zone[b.zone])
        for b in boundaries
    ]
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_hr_zones.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/hr_zones.py backend/tests/unit/analytics/test_hr_zones.py
git commit -m "feat: compute heart rate zones from max_hr and samples"
```

---

### Task 9: Splits au kilomètre par interpolation (`analytics/splits.py`)

**Files:**
- Create: `backend/app/analytics/splits.py`
- Create: `backend/tests/unit/analytics/test_splits.py`

**Interfaces:**
- Consumes: rien.
- Produces: `Split(index: int, distance_m: float, duration_s: float, pace_s_per_km: float | None, mean_heart_rate: float | None)`,
  `compute_splits(samples: Sequence[tuple[datetime, float | None, int | None]], *, unit_m: float = 1000.0) -> list[Split]`.
  Consommé par `services/workouts.py` (`/workouts/{id}/splits`, tâche 26).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_splits.py` :

```python
"""Tests des splits au kilomètre — interpolation entre échantillons.

Vitesse constante 3 m/s, échantillon toutes les 10 s : la distance cumulée
franchit 1000 m entre t=330 (990 m) et t=340 (1020 m). Le passage au km
s'interpole à t = 330 + 10*(1000-990)/(1020-990) = 333.333... s.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.splits import compute_splits

T0 = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def _constant_speed_samples(n: int, *, speed_mps: float, step_s: int):
    return [
        (T0 + timedelta(seconds=i * step_s), i * step_s * speed_mps, None)
        for i in range(n)
    ]


def test_compute_splits_interpolates_kilometer_crossing() -> None:
    samples = _constant_speed_samples(35, speed_mps=3.0, step_s=10)  # jusqu'à 1020 m

    splits = compute_splits(samples, unit_m=1000.0)

    assert len(splits) == 2  # un km complet + un segment partiel de 20 m
    first = splits[0]
    assert first.index == 1
    assert first.distance_m == pytest.approx(1000.0)
    assert first.duration_s == pytest.approx(333.333, abs=0.01)
    assert first.pace_s_per_km == pytest.approx(333.333, abs=0.01)


def test_compute_splits_final_partial_segment() -> None:
    samples = _constant_speed_samples(35, speed_mps=3.0, step_s=10)

    splits = compute_splits(samples, unit_m=1000.0)

    partial = splits[1]
    assert partial.index == 2
    assert partial.distance_m == pytest.approx(20.0, abs=0.01)
    assert partial.duration_s == pytest.approx(6.667, abs=0.01)


def test_compute_splits_averages_heart_rate_within_split() -> None:
    samples = [
        (T0, 0.0, 140),
        (T0 + timedelta(seconds=100), 500.0, 150),
        (T0 + timedelta(seconds=200), 1000.0, 160),
    ]

    splits = compute_splits(samples, unit_m=1000.0)

    assert splits[0].mean_heart_rate == pytest.approx((140 + 150) / 2)


def test_compute_splits_on_empty_samples_returns_empty_list() -> None:
    assert compute_splits([], unit_m=1000.0) == []


def test_compute_splits_ignores_samples_without_distance() -> None:
    samples = [(T0, None, 140), (T0 + timedelta(seconds=10), 30.0, 145)]

    splits = compute_splits(samples, unit_m=1000.0)

    assert len(splits) == 1
    assert splits[0].distance_m == pytest.approx(30.0)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_splits.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.splits'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/splits.py` :

```python
"""Splits au kilomètre (ou à l'unité choisie) par interpolation linéaire.

Une séance longue échantillonne rarement pile au passage du kilomètre : on
interpole le temps de passage entre les deux échantillons qui l'encadrent
plutôt que d'arrondir au sample le plus proche, ce qui biaiserait
systématiquement l'allure affichée.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True, slots=True)
class Split:
    index: int
    distance_m: float
    duration_s: float
    pace_s_per_km: float | None
    mean_heart_rate: float | None


def _mean(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def compute_splits(
    samples: Sequence[tuple[datetime, float | None, int | None]],
    *,
    unit_m: float = 1000.0,
) -> list[Split]:
    points = sorted(
        ((at, dist, hr) for at, dist, hr in samples if dist is not None),
        key=lambda p: p[0],
    )
    if not points:
        return []

    splits: list[Split] = []
    index = 1
    seg_start_t = points[0][0]
    seg_start_dist = points[0][1]
    hr_acc: list[int] = []
    target = unit_m

    for (at0, d0, hr0), (at1, d1, hr1) in zip(points, points[1:]):
        if hr0 is not None:
            hr_acc.append(hr0)
        while d1 >= target > d0:
            fraction = (target - d0) / (d1 - d0) if d1 != d0 else 0.0
            cross_t = at0 + (at1 - at0) * fraction
            duration_s = (cross_t - seg_start_t).total_seconds()
            distance_m = target - seg_start_dist
            pace = duration_s / (distance_m / 1000) if distance_m > 0 else None
            splits.append(
                Split(index, distance_m, duration_s, pace, _mean(hr_acc))
            )
            index += 1
            seg_start_t = cross_t
            seg_start_dist = target
            hr_acc = []
            target += unit_m

    last_at, last_dist, last_hr = points[-1]
    if last_hr is not None:
        hr_acc.append(last_hr)
    if last_dist > seg_start_dist:
        duration_s = (last_at - seg_start_t).total_seconds()
        distance_m = last_dist - seg_start_dist
        pace = duration_s / (distance_m / 1000) if distance_m > 0 else None
        splits.append(Split(index, distance_m, duration_s, pace, _mean(hr_acc)))

    return splits
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_splits.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/splits.py backend/tests/unit/analytics/test_splits.py
git commit -m "feat: compute kilometer splits by linear interpolation"
```

---

### Task 10: SWOLF agrégé par nage (`analytics/swim.py`)

Spec 5 : SWOLF = durée de la longueur en secondes + nombre de coups, par
longueur, agrégé par type de nage.

**Files:**
- Create: `backend/app/analytics/swim.py`
- Create: `backend/tests/unit/analytics/test_swim.py`

**Interfaces:**
- Consumes: rien.
- Produces: `SwimLengthInput(idx: int, duration_ms: int | None, stroke_count: int | None, stroke_type: str | None)`,
  `SwolfByStroke(stroke_type: str, length_count: int, mean_swolf: float | None, mean_duration_s: float | None)`,
  `compute_swolf(lengths: Sequence[SwimLengthInput]) -> list[SwolfByStroke]`.
  Consommé par `services/workouts.py` (`/workouts/{id}/swim`, tâche 28).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_swim.py` :

```python
"""Tests du SWOLF agrégé par type de nage — spec section 5."""

import pytest

from app.analytics.swim import SwimLengthInput, compute_swolf


def test_compute_swolf_groups_by_stroke_type() -> None:
    lengths = [
        SwimLengthInput(idx=0, duration_ms=30000, stroke_count=18, stroke_type="Crawl"),
        SwimLengthInput(idx=1, duration_ms=32000, stroke_count=20, stroke_type="Crawl"),
        SwimLengthInput(idx=2, duration_ms=40000, stroke_count=14, stroke_type="Brasse"),
    ]

    result = {r.stroke_type: r for r in compute_swolf(lengths)}

    # Longueur 0 : 30 s + 18 coups = 48. Longueur 1 : 32 s + 20 coups = 52.
    assert result["Crawl"].length_count == 2
    assert result["Crawl"].mean_swolf == pytest.approx(50.0)
    assert result["Crawl"].mean_duration_s == pytest.approx(31.0)

    # Longueur 2 : 40 s + 14 coups = 54.
    assert result["Brasse"].length_count == 1
    assert result["Brasse"].mean_swolf == pytest.approx(54.0)


def test_compute_swolf_skips_lengths_missing_duration_or_strokes() -> None:
    """Une longueur sans durée ou sans coups ne peut pas produire de SWOLF ;
    elle ne doit ni fausser la moyenne à zéro, ni faire planter le calcul."""
    lengths = [
        SwimLengthInput(idx=0, duration_ms=30000, stroke_count=None, stroke_type="Crawl"),
        SwimLengthInput(idx=1, duration_ms=None, stroke_count=20, stroke_type="Crawl"),
        SwimLengthInput(idx=2, duration_ms=30000, stroke_count=18, stroke_type="Crawl"),
    ]

    result = {r.stroke_type: r for r in compute_swolf(lengths)}

    assert result["Crawl"].length_count == 1
    assert result["Crawl"].mean_swolf == pytest.approx(48.0)


def test_compute_swolf_labels_missing_stroke_type_explicitly() -> None:
    lengths = [SwimLengthInput(idx=0, duration_ms=30000, stroke_count=18, stroke_type=None)]

    result = compute_swolf(lengths)

    assert result[0].stroke_type == "Inconnu"


def test_compute_swolf_on_empty_lengths_returns_empty_list() -> None:
    assert compute_swolf([]) == []
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_swim.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.swim'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/swim.py` :

```python
"""SWOLF agrégé par type de nage — spec section 5.

SWOLF d'une longueur = durée en secondes + nombre de coups. Agrégé (moyenne)
par type de nage, seule granularité qui a un sens : comparer le SWOLF du
crawl à celui de la brasse serait trompeur.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

UNKNOWN_STROKE = "Inconnu"


@dataclass(frozen=True, slots=True)
class SwimLengthInput:
    idx: int
    duration_ms: int | None
    stroke_count: int | None
    stroke_type: str | None


@dataclass(frozen=True, slots=True)
class SwolfByStroke:
    stroke_type: str
    length_count: int
    mean_swolf: float | None
    mean_duration_s: float | None


def compute_swolf(lengths: Sequence[SwimLengthInput]) -> list[SwolfByStroke]:
    swolf_by_stroke: dict[str, list[float]] = defaultdict(list)
    duration_by_stroke: dict[str, list[float]] = defaultdict(list)

    for length in lengths:
        if length.duration_ms is None or length.stroke_count is None:
            continue
        stroke = length.stroke_type or UNKNOWN_STROKE
        duration_s = length.duration_ms / 1000
        swolf_by_stroke[stroke].append(duration_s + length.stroke_count)
        duration_by_stroke[stroke].append(duration_s)

    return [
        SwolfByStroke(
            stroke_type=stroke,
            length_count=len(values),
            mean_swolf=sum(values) / len(values),
            mean_duration_s=sum(duration_by_stroke[stroke]) / len(duration_by_stroke[stroke]),
        )
        for stroke, values in swolf_by_stroke.items()
    ]
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_swim.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/swim.py backend/tests/unit/analytics/test_swim.py
git commit -m "feat: compute swolf aggregated by stroke type"
```

---

### Task 11: Volume et progression musculation (`analytics/strength.py`)

Spec section 5.7 / 4.8 : volume par séance (répétitions × charge), nombre de
séries, progression dans le temps.

**Files:**
- Create: `backend/app/analytics/strength.py`
- Create: `backend/tests/unit/analytics/test_strength.py`

**Interfaces:**
- Consumes: rien.
- Produces: `StrengthSetInput(idx: int, reps: int | None, weight_kg: float | None, duration_s: float | None)`,
  `StrengthSessionVolume(set_count: int, total_volume_kg: float | None, total_reps: int | None)`,
  `compute_session_volume(sets: Sequence[StrengthSetInput]) -> StrengthSessionVolume`,
  `ProgressionPoint(at: date, total_volume_kg: float | None)`,
  `compute_progression(sessions: Sequence[tuple[date, Sequence[StrengthSetInput]]]) -> list[ProgressionPoint]`.
  Consommé par `services/workouts.py` (`/workouts/{id}/strength`, tâche 29).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_strength.py` :

```python
"""Tests du volume et de la progression en musculation — spec 4.8."""

from datetime import date

import pytest

from app.analytics.strength import (
    ProgressionPoint,
    StrengthSetInput,
    compute_progression,
    compute_session_volume,
)


def test_compute_session_volume_sums_reps_times_weight() -> None:
    sets = [
        StrengthSetInput(idx=0, reps=10, weight_kg=50.0, duration_s=30.0),
        StrengthSetInput(idx=1, reps=8, weight_kg=55.0, duration_s=32.0),
    ]

    volume = compute_session_volume(sets)

    assert volume.set_count == 2
    assert volume.total_volume_kg == pytest.approx(10 * 50.0 + 8 * 55.0)
    assert volume.total_reps == 18


def test_compute_session_volume_skips_sets_missing_reps_or_weight() -> None:
    """Une série au poids du corps sans weight_kg renseigné ne doit pas
    faire écrouler le volume total à une valeur fausse : elle est exclue du
    total en kg mais comptée dans set_count."""
    sets = [
        StrengthSetInput(idx=0, reps=10, weight_kg=None, duration_s=30.0),
        StrengthSetInput(idx=1, reps=8, weight_kg=55.0, duration_s=32.0),
    ]

    volume = compute_session_volume(sets)

    assert volume.set_count == 2
    assert volume.total_volume_kg == pytest.approx(8 * 55.0)


def test_compute_session_volume_on_empty_sets() -> None:
    volume = compute_session_volume([])

    assert volume.set_count == 0
    assert volume.total_volume_kg is None
    assert volume.total_reps is None


def test_compute_progression_returns_one_point_per_session() -> None:
    sessions = [
        (date(2026, 1, 1), [StrengthSetInput(idx=0, reps=10, weight_kg=50.0, duration_s=30.0)]),
        (date(2026, 1, 8), [StrengthSetInput(idx=0, reps=10, weight_kg=55.0, duration_s=30.0)]),
    ]

    progression = compute_progression(sessions)

    assert progression == [
        ProgressionPoint(at=date(2026, 1, 1), total_volume_kg=500.0),
        ProgressionPoint(at=date(2026, 1, 8), total_volume_kg=550.0),
    ]
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_strength.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.strength'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/strength.py` :

```python
"""Volume et progression en musculation — spec 4.8.

Le volume (répétitions × charge) et le nombre de séries sont la matière que
l'ancienne application jetait après s'en être servie pour deviner le sport.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True, slots=True)
class StrengthSetInput:
    idx: int
    reps: int | None
    weight_kg: float | None
    duration_s: float | None


@dataclass(frozen=True, slots=True)
class StrengthSessionVolume:
    set_count: int
    total_volume_kg: float | None
    total_reps: int | None


def compute_session_volume(sets: Sequence[StrengthSetInput]) -> StrengthSessionVolume:
    if not sets:
        return StrengthSessionVolume(set_count=0, total_volume_kg=None, total_reps=None)

    usable = [s for s in sets if s.reps is not None and s.weight_kg is not None]
    reps_known = [s for s in sets if s.reps is not None]

    return StrengthSessionVolume(
        set_count=len(sets),
        total_volume_kg=sum(s.reps * s.weight_kg for s in usable) if usable else None,
        total_reps=sum(s.reps for s in reps_known) if reps_known else None,
    )


@dataclass(frozen=True, slots=True)
class ProgressionPoint:
    at: date
    total_volume_kg: float | None


def compute_progression(
    sessions: Sequence[tuple[date, Sequence[StrengthSetInput]]],
) -> list[ProgressionPoint]:
    return [
        ProgressionPoint(at=day, total_volume_kg=compute_session_volume(sets).total_volume_kg)
        for day, sets in sessions
    ]
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_strength.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/strength.py backend/tests/unit/analytics/test_strength.py
git commit -m "feat: compute strength training volume and progression"
```

---

### Task 12: Records par sport (`analytics/records.py`)

**Files:**
- Create: `backend/app/analytics/records.py`
- Create: `backend/tests/unit/analytics/test_records.py`

**Interfaces:**
- Consumes: rien.
- Produces: `WorkoutSummaryInput(id: int, started_at: datetime, distance_m: float | None, duration_ms: int | None, calories_kcal: float | None, mean_speed_mps: float | None)`,
  `RecordEntry(label: str, workout_id: int, value: float, at: datetime)`,
  `compute_records(workouts: Sequence[WorkoutSummaryInput]) -> list[RecordEntry]`.
  Le filtrage par sport est fait en amont par `services/workouts.py`
  (tâche 30) : cette fonction reçoit déjà les séances du sport voulu.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_records.py` :

```python
"""Tests des records par sport — le filtrage par sport est fait en amont."""

from datetime import datetime, timezone

from app.analytics.records import WorkoutSummaryInput, compute_records

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 2, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 3, 1, tzinfo=timezone.utc)


def test_compute_records_finds_longest_distance() -> None:
    workouts = [
        WorkoutSummaryInput(1, T0, distance_m=5000.0, duration_ms=1_800_000, calories_kcal=400.0, mean_speed_mps=2.8),
        WorkoutSummaryInput(2, T1, distance_m=10000.0, duration_ms=3_600_000, calories_kcal=750.0, mean_speed_mps=2.8),
    ]

    records = {r.label: r for r in compute_records(workouts)}

    assert records["Distance la plus longue"].workout_id == 2
    assert records["Distance la plus longue"].value == 10000.0


def test_compute_records_finds_longest_duration_and_highest_speed_and_calories() -> None:
    workouts = [
        WorkoutSummaryInput(1, T0, distance_m=5000.0, duration_ms=3_700_000, calories_kcal=900.0, mean_speed_mps=1.5),
        WorkoutSummaryInput(2, T1, distance_m=10000.0, duration_ms=3_600_000, calories_kcal=750.0, mean_speed_mps=3.0),
    ]

    records = {r.label: r for r in compute_records(workouts)}

    assert records["Durée la plus longue"].workout_id == 1
    assert records["Vitesse moyenne la plus élevée"].workout_id == 2
    assert records["Calories les plus élevées"].workout_id == 1


def test_compute_records_ignores_missing_values_per_category() -> None:
    """Une séance sans distance ne doit pas être éligible au record de
    distance, mais reste éligible aux autres catégories."""
    workouts = [
        WorkoutSummaryInput(1, T0, distance_m=None, duration_ms=1_800_000, calories_kcal=400.0, mean_speed_mps=None),
        WorkoutSummaryInput(2, T1, distance_m=8000.0, duration_ms=1_200_000, calories_kcal=300.0, mean_speed_mps=2.5),
    ]

    records = {r.label: r for r in compute_records(workouts)}

    assert records["Distance la plus longue"].workout_id == 2
    assert records["Durée la plus longue"].workout_id == 1


def test_compute_records_on_empty_workouts_returns_empty_list() -> None:
    assert compute_records([]) == []
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_records.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.records'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/records.py` :

```python
"""Records par sport. Le filtrage par sport est fait par l'appelant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True, slots=True)
class WorkoutSummaryInput:
    id: int
    started_at: datetime
    distance_m: float | None
    duration_ms: int | None
    calories_kcal: float | None
    mean_speed_mps: float | None


@dataclass(frozen=True, slots=True)
class RecordEntry:
    label: str
    workout_id: int
    value: float
    at: datetime


_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Distance la plus longue", "distance_m"),
    ("Durée la plus longue", "duration_ms"),
    ("Vitesse moyenne la plus élevée", "mean_speed_mps"),
    ("Calories les plus élevées", "calories_kcal"),
)


def compute_records(workouts: Sequence[WorkoutSummaryInput]) -> list[RecordEntry]:
    records = []
    for label, field in _CATEGORIES:
        eligible = [w for w in workouts if getattr(w, field) is not None]
        if not eligible:
            continue
        best = max(eligible, key=lambda w: getattr(w, field))
        records.append(RecordEntry(label, best.id, getattr(best, field), best.started_at))
    return records
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_records.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/records.py backend/tests/unit/analytics/test_records.py
git commit -m "feat: compute per-sport workout records"
```

---

### Task 13: Charge d'entraînement TRIMP (`analytics/training_load.py`)

Spec 5.4 : charge par séance de type TRIMP, charge aiguë (7 jours) contre
charge chronique (28 jours), dérive cardiaque intra-séance.

**Files:**
- Create: `backend/app/analytics/training_load.py`
- Create: `backend/tests/unit/analytics/test_training_load.py`

**Interfaces:**
- Consumes: rien.
- Produces: `SessionLoadInput(workout_id: int, started_at: datetime, samples: Sequence[tuple[datetime, int | None]], resting_hr: int | None, max_hr: int | None)`,
  `TrimpResult(workout_id: int, trimp: float | None)`,
  `compute_trimp(session: SessionLoadInput) -> TrimpResult`,
  `LoadPoint(day: date, load: float)`,
  `LoadBalance(day: date, acute_load: float | None, chronic_load: float | None, ratio: float | None)`,
  `compute_acute_chronic(daily_loads: Sequence[LoadPoint]) -> list[LoadBalance]`,
  `CardiacDrift(first_half_mean_hr: float | None, second_half_mean_hr: float | None, drift_pct: float | None)`,
  `compute_cardiac_drift(samples: Sequence[tuple[datetime, int | None]]) -> CardiacDrift`.
  Consommé par `services/training_load.py` (`/analytics/training-load`,
  tâche 34) et `services/workouts.py` (dérive cardiaque dans le détail d'une
  séance, tâche 23).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_training_load.py` :

```python
"""Tests de la charge d'entraînement — spec 5.4.

Formule TRIMP de Banister (coefficients hommes) : pour chaque intervalle
entre échantillons, durée en minutes × HRr × 0.64 × e^(1.92 × HRr), où
HRr = (FC moyenne de l'intervalle − FC repos) / (FC max − FC repos).

Cas de test à la main : un seul intervalle de 10 min à FC constante 150,
repos 50, max 190 → HRr = 100/140 ≈ 0.714286.
1.92 × 0.714286 ≈ 1.371429 ; e^1.371429 ≈ 3.9401.
0.714286 × 0.64 ≈ 0.457143 ; × 3.9401 ≈ 1.8011 ; × 10 min ≈ 18.01.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.analytics.training_load import (
    CardiacDrift,
    LoadPoint,
    SessionLoadInput,
    compute_acute_chronic,
    compute_cardiac_drift,
    compute_trimp,
)

T0 = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def test_compute_trimp_matches_hand_derived_value() -> None:
    session = SessionLoadInput(
        workout_id=1,
        started_at=T0,
        samples=[(T0, 150), (T0 + timedelta(minutes=10), 150)],
        resting_hr=50,
        max_hr=190,
    )

    result = compute_trimp(session)

    assert result.trimp == pytest.approx(18.01, abs=0.05)


def test_compute_trimp_is_none_without_resting_or_max_hr() -> None:
    session = SessionLoadInput(
        workout_id=1, started_at=T0, samples=[(T0, 150)], resting_hr=None, max_hr=190
    )

    assert compute_trimp(session).trimp is None


def test_compute_trimp_is_none_without_enough_samples() -> None:
    session = SessionLoadInput(
        workout_id=1, started_at=T0, samples=[(T0, 150)], resting_hr=50, max_hr=190
    )

    assert compute_trimp(session).trimp is None


def test_compute_acute_chronic_averages_over_7_and_28_days() -> None:
    start = date(2026, 1, 1)
    daily_loads = [LoadPoint(day=start + timedelta(days=i), load=100.0) for i in range(28)]

    balances = compute_acute_chronic(daily_loads)
    last = balances[-1]

    assert last.acute_load == pytest.approx(100.0)
    assert last.chronic_load == pytest.approx(100.0)
    assert last.ratio == pytest.approx(1.0)


def test_compute_acute_chronic_ratio_above_one_signals_spike() -> None:
    start = date(2026, 1, 1)
    daily_loads = [LoadPoint(day=start + timedelta(days=i), load=50.0) for i in range(21)]
    daily_loads += [LoadPoint(day=start + timedelta(days=i), load=150.0) for i in range(21, 28)]

    balances = {b.day: b for b in compute_acute_chronic(daily_loads)}
    last_day = start + timedelta(days=27)

    assert balances[last_day].ratio > 1.0


def test_compute_cardiac_drift_compares_first_and_second_half() -> None:
    samples = [
        (T0, 130),
        (T0 + timedelta(minutes=10), 130),
        (T0 + timedelta(minutes=20), 150),
        (T0 + timedelta(minutes=30), 150),
    ]

    drift = compute_cardiac_drift(samples)

    assert drift.first_half_mean_hr == pytest.approx(130.0)
    assert drift.second_half_mean_hr == pytest.approx(150.0)
    assert drift.drift_pct == pytest.approx((150.0 - 130.0) / 130.0 * 100)


def test_compute_cardiac_drift_on_empty_samples_is_none() -> None:
    drift = compute_cardiac_drift([])

    assert drift == CardiacDrift(None, None, None)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_training_load.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.training_load'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/training_load.py` :

```python
"""Charge d'entraînement — spec 5.4.

TRIMP (Banister, coefficients hommes) par séance, puis charge aiguë (moyenne
7 jours) comparée à la charge chronique (moyenne 28 jours), et dérive
cardiaque intra-séance (comparaison FC moyenne 1re/2e moitié).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Sequence

_TRIMP_SCALE = 0.64
_TRIMP_EXPONENT = 1.92
_ACUTE_WINDOW_DAYS = 7
_CHRONIC_WINDOW_DAYS = 28


@dataclass(frozen=True, slots=True)
class SessionLoadInput:
    workout_id: int
    started_at: datetime
    samples: Sequence[tuple[datetime, int | None]]
    resting_hr: int | None
    max_hr: int | None


@dataclass(frozen=True, slots=True)
class TrimpResult:
    workout_id: int
    trimp: float | None


def compute_trimp(session: SessionLoadInput) -> TrimpResult:
    if session.resting_hr is None or session.max_hr is None:
        return TrimpResult(session.workout_id, None)
    hr_range = session.max_hr - session.resting_hr
    if hr_range <= 0:
        return TrimpResult(session.workout_id, None)

    valid = sorted((s for s in session.samples if s[1] is not None), key=lambda s: s[0])
    if len(valid) < 2:
        return TrimpResult(session.workout_id, None)

    total = 0.0
    for (t0, hr0), (t1, hr1) in zip(valid, valid[1:]):
        minutes = (t1 - t0).total_seconds() / 60
        if minutes <= 0:
            continue
        mean_hr = (hr0 + hr1) / 2
        hrr = max(0.0, min(1.0, (mean_hr - session.resting_hr) / hr_range))
        total += minutes * hrr * _TRIMP_SCALE * math.exp(_TRIMP_EXPONENT * hrr)

    return TrimpResult(session.workout_id, round(total, 2))


@dataclass(frozen=True, slots=True)
class LoadPoint:
    day: date
    load: float


@dataclass(frozen=True, slots=True)
class LoadBalance:
    day: date
    acute_load: float | None
    chronic_load: float | None
    ratio: float | None


def compute_acute_chronic(daily_loads: Sequence[LoadPoint]) -> list[LoadBalance]:
    ordered = sorted(daily_loads, key=lambda p: p.day)
    load_by_day = {p.day: p.load for p in ordered}
    balances = []

    for point in ordered:
        acute_days = [point.day - timedelta(days=i) for i in range(_ACUTE_WINDOW_DAYS)]
        chronic_days = [point.day - timedelta(days=i) for i in range(_CHRONIC_WINDOW_DAYS)]
        acute = sum(load_by_day.get(d, 0.0) for d in acute_days) / _ACUTE_WINDOW_DAYS
        chronic = sum(load_by_day.get(d, 0.0) for d in chronic_days) / _CHRONIC_WINDOW_DAYS
        ratio = acute / chronic if chronic > 0 else None
        balances.append(LoadBalance(point.day, acute, chronic, ratio))

    return balances


@dataclass(frozen=True, slots=True)
class CardiacDrift:
    first_half_mean_hr: float | None
    second_half_mean_hr: float | None
    drift_pct: float | None


def compute_cardiac_drift(samples: Sequence[tuple[datetime, int | None]]) -> CardiacDrift:
    valid = sorted((s for s in samples if s[1] is not None), key=lambda s: s[0])
    if len(valid) < 2:
        return CardiacDrift(None, None, None)

    midpoint = len(valid) // 2
    first_half = [hr for _, hr in valid[:midpoint]]
    second_half = [hr for _, hr in valid[midpoint:]]
    if not first_half or not second_half:
        return CardiacDrift(None, None, None)

    first_mean = sum(first_half) / len(first_half)
    second_mean = sum(second_half) / len(second_half)
    drift_pct = (second_mean - first_mean) / first_mean * 100 if first_mean else None
    return CardiacDrift(first_mean, second_mean, drift_pct)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_training_load.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/analytics/training_load.py backend/tests/unit/analytics/test_training_load.py
git commit -m "feat: compute trimp training load and cardiac drift"
```

---

### Task 14: Fenêtre alimentaire et aliments récurrents (`analytics/nutrition.py`)

Spec 5.6 : les prises s'étalent de 5 h à 18 h avec un pic à 6 h, motif de
jeûne intermittent directement lisible dans les horodatages.

**Files:**
- Create: `backend/app/analytics/nutrition.py`
- Create: `backend/tests/unit/analytics/test_nutrition_analytics.py`

**Interfaces:**
- Consumes: rien.
- Produces: `NutritionEntryInput(consumed_at: datetime, food_name: str, calories: float | None)`,
  `HourlyBucket(hour: int, entry_count: int, total_calories: float | None)`,
  `compute_eating_window(entries: Sequence[NutritionEntryInput], *, tz: str = "Europe/Paris") -> list[HourlyBucket]`,
  `TopFood(food_name: str, entry_count: int, total_calories: float | None)`,
  `compute_top_foods(entries: Sequence[NutritionEntryInput], *, limit: int = 10) -> list[TopFood]`.
  Consommé par `services/nutrition.py` (tâches 18, 35).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/analytics/test_nutrition_analytics.py` :

```python
"""Tests de la fenêtre alimentaire et des aliments récurrents — spec 5.6."""

from datetime import datetime, timezone

import pytest

from app.analytics.nutrition import NutritionEntryInput, compute_eating_window, compute_top_foods


def test_compute_eating_window_buckets_by_local_hour() -> None:
    """06:00 UTC = 08:00 Europe/Paris en été (UTC+2)."""
    entries = [
        NutritionEntryInput(
            consumed_at=datetime(2026, 7, 1, 6, 0, tzinfo=timezone.utc),
            food_name="Avoine",
            calories=350.0,
        ),
        NutritionEntryInput(
            consumed_at=datetime(2026, 7, 1, 6, 30, tzinfo=timezone.utc),
            food_name="Café",
            calories=5.0,
        ),
    ]

    buckets = {b.hour: b for b in compute_eating_window(entries)}

    assert buckets[8].entry_count == 2
    assert buckets[8].total_calories == pytest.approx(355.0)
    assert len(buckets) == 24  # les 24 heures sont représentées, même vides


def test_compute_eating_window_on_empty_entries_still_returns_24_buckets() -> None:
    buckets = compute_eating_window([])

    assert len(buckets) == 24
    assert all(b.entry_count == 0 and b.total_calories is None for b in buckets)


def test_compute_top_foods_ranks_by_frequency() -> None:
    entries = [
        NutritionEntryInput(datetime(2026, 1, 1, tzinfo=timezone.utc), "Poulet", 200.0),
        NutritionEntryInput(datetime(2026, 1, 2, tzinfo=timezone.utc), "Poulet", 210.0),
        NutritionEntryInput(datetime(2026, 1, 3, tzinfo=timezone.utc), "Riz", 180.0),
    ]

    top = compute_top_foods(entries, limit=10)

    assert top[0].food_name == "Poulet"
    assert top[0].entry_count == 2
    assert top[0].total_calories == pytest.approx(410.0)
    assert top[1].food_name == "Riz"


def test_compute_top_foods_respects_limit() -> None:
    entries = [
        NutritionEntryInput(datetime(2026, 1, i + 1, tzinfo=timezone.utc), f"Aliment {i}", 100.0)
        for i in range(5)
    ]

    top = compute_top_foods(entries, limit=2)

    assert len(top) == 2
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_nutrition_analytics.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.analytics.nutrition'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/analytics/nutrition.py` :

```python
"""Fenêtre alimentaire et aliments récurrents — spec 5.6.

La fenêtre alimentaire se lit directement dans la distribution horaire des
prises, en heure locale : agréger en UTC ferait apparaître un pic à une
heure qui n'existe pas dans le vécu de l'utilisateur.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class NutritionEntryInput:
    consumed_at: datetime
    food_name: str
    calories: float | None


@dataclass(frozen=True, slots=True)
class HourlyBucket:
    hour: int
    entry_count: int
    total_calories: float | None


def compute_eating_window(
    entries: Sequence[NutritionEntryInput], *, tz: str = "Europe/Paris"
) -> list[HourlyBucket]:
    zone = ZoneInfo(tz)
    counts = [0] * 24
    totals: list[float | None] = [None] * 24

    for entry in entries:
        hour = entry.consumed_at.astimezone(zone).hour
        counts[hour] += 1
        if entry.calories is not None:
            totals[hour] = (totals[hour] or 0.0) + entry.calories

    return [
        HourlyBucket(hour=h, entry_count=counts[h], total_calories=totals[h])
        for h in range(24)
    ]


@dataclass(frozen=True, slots=True)
class TopFood:
    food_name: str
    entry_count: int
    total_calories: float | None


def compute_top_foods(
    entries: Sequence[NutritionEntryInput], *, limit: int = 10
) -> list[TopFood]:
    counts: Counter[str] = Counter()
    totals: dict[str, float] = defaultdict(float)
    has_calories: dict[str, bool] = defaultdict(bool)

    for entry in entries:
        counts[entry.food_name] += 1
        if entry.calories is not None:
            totals[entry.food_name] += entry.calories
            has_calories[entry.food_name] = True

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        TopFood(
            food_name=name,
            entry_count=count,
            total_calories=totals[name] if has_calories[name] else None,
        )
        for name, count in ranked[:limit]
    ]
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/analytics/test_nutrition_analytics.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Lancer toute la suite unitaire avant de passer aux services**

Run: `cd backend && uv run ruff check . && uv run pytest tests/unit -v`
Expected: aucune erreur ruff, tous les tests unitaires PASS (analytics et
échafaudage confondus)

- [ ] **Step 6: Commiter**

```bash
git add backend/app/analytics/nutrition.py backend/tests/unit/analytics/test_nutrition_analytics.py
git commit -m "feat: compute eating window and top foods"
```

---

### Task 15: Corps — mesures et séries temporelles

Premier endpoint connecté à la base. Introduit la convention suivie par
toutes les tâches suivantes : les services renvoient des dataclasses, l'API
les convertit en schémas Pydantic via `Schema.model_validate(dataclass,
from_attributes=True)`.

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/body.py`
- Create: `backend/app/schemas/body.py`
- Create: `backend/app/api/body.py`
- Create: `backend/tests/integration/test_service_body.py`
- Create: `backend/tests/integration/test_api_body.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Consumes: `app.db.get_session` (plan 1) ; `app.models.BodyMeasurement`
  (plan 1) ; `app.api.deps.DbSession`, `DateRangeDep` (tâche 2).
- Produces: `services.body.MeasurementRow(at: datetime, weight_kg, body_fat_pct, body_fat_mass_kg, skeletal_muscle_mass_kg, fat_free_mass_kg, total_body_water_kg, basal_metabolic_rate_kcal)`,
  `services.body.list_measurements(session, date_range: DateRange) -> list[MeasurementRow]`,
  `services.body.TimeseriesPoint(at: date, value: float | None)`,
  `services.body.METRIC_COLUMNS: Mapping[str, str]` (`"weight"`,
  `"body_fat"`, `"muscle"` → colonnes de `body_measurement` /
  `mv_daily_body`),
  `services.body.get_timeseries(session, date_range, metrics: list[str], resolution: str) -> dict[str, list[TimeseriesPoint]]`.
  Consommé par `app.api.body` (ce fichier) et réutilisé par
  `services.body.get_summary` (tâche 19) et `services.body.get_composition`
  (tâche 32).

- [ ] **Step 1: Écrire les tests d'intégration du service qui échouent**

Créer `backend/tests/integration/test_service_body.py` :

```python
"""Tests d'intégration du service corps, contre PostgreSQL jetable."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.models import BodyMeasurement
from app.services.body import get_timeseries, list_measurements

pytestmark = pytest.mark.asyncio


async def _insert_measurement(
    session: AsyncSession, *, source_uuid: str, at: datetime, weight_kg: float | None
) -> None:
    session.add(
        BodyMeasurement(source_uuid=source_uuid, measured_at=at, weight_kg=weight_kg)
    )
    await session.commit()


async def test_list_measurements_filters_by_date_range(session: AsyncSession) -> None:
    await _insert_measurement(
        session, source_uuid="body-1", at=datetime(2026, 1, 1, tzinfo=timezone.utc), weight_kg=80.0
    )
    await _insert_measurement(
        session, source_uuid="body-2", at=datetime(2026, 6, 1, tzinfo=timezone.utc), weight_kg=75.0
    )

    result = await list_measurements(
        session, DateRange(start=date(2026, 1, 1), end=date(2026, 2, 1))
    )

    assert [r.weight_kg for r in result] == [80.0]


async def test_list_measurements_preserves_null_body_fat(session: AsyncSession) -> None:
    """260 mesures réelles n'ont pas de masse grasse : la valeur doit rester
    None, jamais 0."""
    await _insert_measurement(
        session, source_uuid="body-3", at=datetime(2026, 1, 5, tzinfo=timezone.utc), weight_kg=80.0
    )

    result = await list_measurements(
        session, DateRange(start=date(2026, 1, 1), end=date(2026, 1, 31))
    )

    assert result[0].body_fat_pct is None


async def test_get_timeseries_raw_resolution_returns_selected_metrics(
    session: AsyncSession,
) -> None:
    await _insert_measurement(
        session, source_uuid="body-4", at=datetime(2026, 1, 1, tzinfo=timezone.utc), weight_kg=80.0
    )

    result = await get_timeseries(
        session,
        DateRange(start=date(2026, 1, 1), end=date(2026, 1, 31)),
        metrics=["weight"],
        resolution="raw",
    )

    assert "weight" in result
    assert result["weight"][0].value == 80.0
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_service_body.py -v`
Expected: skip si `BA_TEST_DATABASE_URL` absent, sinon FAIL avec
`ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 3: Écrire l'implémentation du service**

Créer `backend/app/services/__init__.py` vide.

Créer `backend/app/services/body.py` :

```python
"""Service corps : orchestre body_measurement et mv_daily_body."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.errors import ValidationError
from app.models import BodyMeasurement

METRIC_COLUMNS = {
    "weight": "weight_kg",
    "body_fat": "body_fat_pct",
    "muscle": "skeletal_muscle_mass_kg",
}


@dataclass(frozen=True, slots=True)
class MeasurementRow:
    at: datetime
    weight_kg: float | None
    body_fat_pct: float | None
    body_fat_mass_kg: float | None
    skeletal_muscle_mass_kg: float | None
    fat_free_mass_kg: float | None
    total_body_water_kg: float | None
    basal_metabolic_rate_kcal: float | None


def _measurement_query(date_range: DateRange):
    query = select(BodyMeasurement).order_by(BodyMeasurement.measured_at)
    if date_range.start is not None:
        query = query.where(BodyMeasurement.measured_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(BodyMeasurement.measured_at <= date_range.end)
    return query


async def list_measurements(
    session: AsyncSession, date_range: DateRange
) -> list[MeasurementRow]:
    rows = (await session.execute(_measurement_query(date_range))).scalars().all()
    return [
        MeasurementRow(
            at=r.measured_at,
            weight_kg=r.weight_kg,
            body_fat_pct=r.body_fat_pct,
            body_fat_mass_kg=r.body_fat_mass_kg,
            skeletal_muscle_mass_kg=r.skeletal_muscle_mass_kg,
            fat_free_mass_kg=r.fat_free_mass_kg,
            total_body_water_kg=r.total_body_water_kg,
            basal_metabolic_rate_kcal=r.basal_metabolic_rate_kcal,
        )
        for r in rows
    ]


@dataclass(frozen=True, slots=True)
class TimeseriesPoint:
    at: date
    value: float | None


async def _raw_series(
    session: AsyncSession, date_range: DateRange, column: str
) -> list[TimeseriesPoint]:
    query = select(BodyMeasurement.measured_at, getattr(BodyMeasurement, column)).order_by(
        BodyMeasurement.measured_at
    )
    if date_range.start is not None:
        query = query.where(BodyMeasurement.measured_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(BodyMeasurement.measured_at <= date_range.end)
    rows = (await session.execute(query)).all()
    return [TimeseriesPoint(at=at.date(), value=value) for at, value in rows]


async def _daily_series(
    session: AsyncSession, date_range: DateRange, column: str
) -> list[TimeseriesPoint]:
    sql = text(
        f"SELECT day, {column} FROM mv_daily_body "  # noqa: S608 - colonne whitelistée
        "WHERE (:start IS NULL OR day >= :start) AND (:end IS NULL OR day <= :end) "
        "ORDER BY day"
    )
    rows = (
        await session.execute(sql, {"start": date_range.start, "end": date_range.end})
    ).all()
    return [TimeseriesPoint(at=row.day, value=getattr(row, column)) for row in rows]


async def get_timeseries(
    session: AsyncSession,
    date_range: DateRange,
    metrics: list[str],
    resolution: str,
) -> dict[str, list[TimeseriesPoint]]:
    if resolution not in ("raw", "daily"):
        raise ValidationError(f"resolution inconnue : {resolution!r}")
    unknown = set(metrics) - set(METRIC_COLUMNS)
    if unknown:
        raise ValidationError(f"métriques inconnues : {sorted(unknown)}")

    result: dict[str, list[TimeseriesPoint]] = {}
    for metric in metrics:
        column = METRIC_COLUMNS[metric]
        if resolution == "raw":
            result[metric] = await _raw_series(session, date_range, column)
        else:
            result[metric] = await _daily_series(session, date_range, column)
    return result
```

`_daily_series` construit son SQL avec un nom de colonne interpolé, mais
celui-ci vient exclusivement de `METRIC_COLUMNS`, une table fermée validée
juste avant dans `get_timeseries` — aucune valeur utilisateur n'atteint la
chaîne de requête.

- [ ] **Step 4: Lancer les tests du service**

Run: `cd backend && uv run pytest tests/integration/test_service_body.py -v`
Expected: PASS (ou skip sans base de test), 3 tests

- [ ] **Step 5: Écrire les tests d'API qui échouent**

Créer `backend/tests/integration/test_api_body.py` :

```python
"""Tests d'intégration de l'API corps, via ASGITransport."""

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import BodyMeasurement

pytestmark = pytest.mark.asyncio


async def test_get_measurements_returns_json_with_null_gaps(session: AsyncSession) -> None:
    session.add(
        BodyMeasurement(
            source_uuid="body-api-1",
            measured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            weight_kg=80.0,
        )
    )
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/body/measurements",
            params={"from": "2026-01-01", "to": "2026-01-31"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["weight_kg"] == 80.0
    assert body[0]["body_fat_pct"] is None


async def test_get_timeseries_rejects_unknown_metric() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/body/timeseries", params={"metrics": "inconnu"}
        )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


async def test_get_timeseries_daily_resolution(session: AsyncSession) -> None:
    session.add(
        BodyMeasurement(
            source_uuid="body-api-2",
            measured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            weight_kg=79.0,
        )
    )
    await session.commit()
    await session.execute(__import__("sqlalchemy").text("REFRESH MATERIALIZED VIEW mv_daily_body"))
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/body/timeseries",
            params={"metrics": "weight", "resolution": "daily"},
        )

    assert response.status_code == 200
    assert "weight" in response.json()
```

Cette dernière assertion dépend de l'`AsyncSession` de la fixture
d'intégration et de celle utilisée en interne par `app.db.session_factory` :
comme les deux pointent vers `BA_TEST_DATABASE_URL`, le `REFRESH` est visible
de l'appel HTTP suivant.

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_api_body.py -v`
Expected: FAIL — pas de route `/api/body/*`

- [ ] **Step 7: Écrire les schémas et le routeur**

Créer `backend/app/schemas/body.py` :

```python
"""Schémas Pydantic de la famille corps."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    weight_kg: float | None
    body_fat_pct: float | None
    body_fat_mass_kg: float | None
    skeletal_muscle_mass_kg: float | None
    fat_free_mass_kg: float | None
    total_body_water_kg: float | None
    basal_metabolic_rate_kcal: float | None


class TimeseriesPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: date
    value: float | None
```

Créer `backend/app/api/body.py` :

```python
"""Routes de lecture de la famille corps."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.body import MeasurementOut, TimeseriesPointOut
from app.services import body as body_service

router = APIRouter(prefix="/body", tags=["corps"])


@router.get("/measurements", response_model=list[MeasurementOut])
async def get_measurements(session: DbSession, date_range: DateRangeDep):
    rows = await body_service.list_measurements(session, date_range)
    return [MeasurementOut.model_validate(r) for r in rows]


@router.get("/timeseries", response_model=dict[str, list[TimeseriesPointOut]])
async def get_timeseries(
    session: DbSession,
    date_range: DateRangeDep,
    metrics: str = Query(..., description="liste séparée par des virgules"),
    resolution: str = Query(default="raw"),
):
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    series = await body_service.get_timeseries(session, date_range, metric_list, resolution)
    return {
        metric: [TimeseriesPointOut.model_validate(p) for p in points]
        for metric, points in series.items()
    }
```

Modifier `backend/app/api/router.py` :

```python
"""Assemble tous les routers de lecture sous le préfixe /api.

Chaque tâche d'endpoint ajoute ici l'inclusion de son propre routeur ; ce
fichier ne définit jamais de route lui-même.
"""

from fastapi import APIRouter

from app.api.body import router as body_router

api_router = APIRouter(prefix="/api")
api_router.include_router(body_router)
```

- [ ] **Step 8: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_api_body.py tests/integration/test_service_body.py -v`
Expected: PASS (ou skip sans base de test), 6 tests

- [ ] **Step 9: Commiter**

```bash
git add backend/app/services backend/app/schemas/body.py backend/app/api/body.py backend/app/api/router.py backend/tests/integration/test_service_body.py backend/tests/integration/test_api_body.py
git commit -m "feat: add body measurements and timeseries endpoints"
```

---

### Task 16: Corps — calendrier (heatmap)

**Files:**
- Modify: `backend/app/services/body.py`
- Modify: `backend/app/schemas/body.py`
- Modify: `backend/app/api/body.py`
- Create: `backend/tests/integration/test_service_body_calendar.py`
- Create: `backend/tests/integration/test_api_body_calendar.py`

**Interfaces:**
- Consumes: `METRIC_COLUMNS` (tâche 15).
- Produces: `services.body.CalendarCell(day: date, value: float | None)`,
  `services.body.get_calendar(session, metric: str, year: int) -> list[CalendarCell]`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/integration/test_service_body_calendar.py` :

```python
"""Tests d'intégration du calendrier corps (mv_daily_body)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ValidationError
from app.models import BodyMeasurement
from app.services.body import get_calendar

pytestmark = pytest.mark.asyncio


async def test_get_calendar_returns_one_cell_per_day_with_data(
    session: AsyncSession,
) -> None:
    session.add(
        BodyMeasurement(
            source_uuid="cal-1",
            measured_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
            weight_kg=78.0,
        )
    )
    await session.commit()
    await session.execute(text("REFRESH MATERIALIZED VIEW mv_daily_body"))
    await session.commit()

    cells = await get_calendar(session, metric="weight", year=2026)

    matching = [c for c in cells if c.day.month == 3 and c.day.day == 15]
    assert matching[0].value == 78.0


async def test_get_calendar_rejects_unknown_metric(session: AsyncSession) -> None:
    with pytest.raises(ValidationError):
        await get_calendar(session, metric="inconnu", year=2026)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_service_body_calendar.py -v`
Expected: FAIL — `get_calendar` n'existe pas encore

- [ ] **Step 3: Étendre le service, le schéma et le routeur**

Ajouter à `backend/app/services/body.py`, à la fin du fichier :

```python
@dataclass(frozen=True, slots=True)
class CalendarCell:
    day: date
    value: float | None


async def get_calendar(session: AsyncSession, metric: str, year: int) -> list[CalendarCell]:
    if metric not in METRIC_COLUMNS:
        raise ValidationError(f"métrique inconnue : {metric!r}")
    column = METRIC_COLUMNS[metric]
    sql = text(
        f"SELECT day, {column} FROM mv_daily_body "  # noqa: S608 - colonne whitelistée
        "WHERE extract(year FROM day) = :year ORDER BY day"
    )
    rows = (await session.execute(sql, {"year": year})).all()
    return [CalendarCell(day=row.day, value=getattr(row, column)) for row in rows]
```

Ajouter à `backend/app/schemas/body.py` :

```python
class CalendarCellOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    value: float | None
```

Ajouter à `backend/app/api/body.py` :

```python
from app.schemas.body import CalendarCellOut  # à fusionner avec l'import existant


@router.get("/calendar", response_model=list[CalendarCellOut])
async def get_calendar(
    session: DbSession, metric: str = Query(...), year: int = Query(...)
):
    cells = await body_service.get_calendar(session, metric, year)
    return [CalendarCellOut.model_validate(c) for c in cells]
```

- [ ] **Step 4: Lancer les tests du service**

Run: `cd backend && uv run pytest tests/integration/test_service_body_calendar.py -v`
Expected: PASS, 2 tests

- [ ] **Step 5: Écrire et lancer le test d'API**

Créer `backend/tests/integration/test_api_body_calendar.py` :

```python
"""Test d'intégration de l'endpoint /api/body/calendar."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_get_calendar_endpoint_requires_metric_and_year() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/body/calendar", params={"metric": "weight", "year": 2026})

    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

Run: `cd backend && uv run pytest tests/integration/test_api_body_calendar.py -v`
Expected: PASS, 1 test

- [ ] **Step 6: Commiter**

```bash
git add backend/app/services/body.py backend/app/schemas/body.py backend/app/api/body.py backend/tests/integration/test_service_body_calendar.py backend/tests/integration/test_api_body_calendar.py
git commit -m "feat: add body calendar heatmap endpoint"
```

---

### Task 17: Nutrition — quotidien et entrées paginées

**Files:**
- Create: `backend/app/services/nutrition.py`
- Create: `backend/app/schemas/nutrition.py`
- Create: `backend/app/api/nutrition.py`
- Create: `backend/tests/integration/test_service_nutrition.py`
- Create: `backend/tests/integration/test_api_nutrition.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Consumes: `app.models.NutritionEntry` (plan 1) ;
  `app.analytics.labels.meal_type_label`, `unit_label` (tâche 3) ;
  `app.api.deps.DbSession`, `DateRangeDep` (tâche 2).
- Produces: `services.nutrition.DailyNutritionRow(day: date, calories: float | None, entry_count: int)`,
  `services.nutrition.get_daily(session, date_range) -> list[DailyNutritionRow]`,
  `services.nutrition.EntryRow(at: datetime, food_name: str, meal_type_label: str, amount: float | None, unit_label: str, calories: float | None)`,
  `services.nutrition.NUTRITION_PAGE_SIZE = 50`,
  `services.nutrition.list_entries(session, date_range, page: int) -> tuple[list[EntryRow], int]`
  (le second élément est le total pour la pagination).

- [ ] **Step 1: Écrire les tests d'intégration qui échouent**

Créer `backend/tests/integration/test_service_nutrition.py` :

```python
"""Tests d'intégration du service nutrition."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.models import NutritionEntry
from app.services.nutrition import NUTRITION_PAGE_SIZE, get_daily, list_entries

pytestmark = pytest.mark.asyncio


async def _entry(session: AsyncSession, *, uid: str, at: datetime, calories: float | None) -> None:
    session.add(
        NutritionEntry(
            source_uuid=uid,
            consumed_at=at,
            food_name="Poulet",
            meal_type=100002,
            unit_code=120001,
            calories=calories,
        )
    )
    await session.commit()


async def test_get_daily_uses_mv_daily_nutrition(session: AsyncSession) -> None:
    from sqlalchemy import text

    await _entry(session, uid="nut-1", at=datetime(2026, 4, 1, 12, tzinfo=timezone.utc), calories=500.0)
    await session.execute(text("REFRESH MATERIALIZED VIEW mv_daily_nutrition"))
    await session.commit()

    result = await get_daily(session, DateRange(start=date(2026, 4, 1), end=date(2026, 4, 30)))

    matching = [r for r in result if r.day == date(2026, 4, 1)]
    assert matching[0].calories == pytest.approx(500.0)
    assert matching[0].entry_count == 1


async def test_list_entries_translates_labels(session: AsyncSession) -> None:
    await _entry(session, uid="nut-2", at=datetime(2026, 4, 1, 8, tzinfo=timezone.utc), calories=300.0)

    entries, total = await list_entries(
        session, DateRange(start=date(2026, 4, 1), end=date(2026, 4, 2)), page=1
    )

    assert total == 1
    assert entries[0].meal_type_label == "Déjeuner"
    assert entries[0].unit_label == "Grammes"


async def test_list_entries_paginates_by_fixed_page_size(session: AsyncSession) -> None:
    for i in range(NUTRITION_PAGE_SIZE + 5):
        await _entry(
            session,
            uid=f"nut-page-{i}",
            at=datetime(2026, 5, 1, 8, tzinfo=timezone.utc),
            calories=100.0,
        )

    page1, total = await list_entries(
        session, DateRange(start=date(2026, 5, 1), end=date(2026, 5, 2)), page=1
    )
    page2, _ = await list_entries(
        session, DateRange(start=date(2026, 5, 1), end=date(2026, 5, 2)), page=2
    )

    assert total == NUTRITION_PAGE_SIZE + 5
    assert len(page1) == NUTRITION_PAGE_SIZE
    assert len(page2) == 5
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_service_nutrition.py -v`
Expected: FAIL — `app.services.nutrition` n'existe pas

- [ ] **Step 3: Écrire le service**

Créer `backend/app/services/nutrition.py` :

```python
"""Service nutrition : orchestre nutrition_entry et mv_daily_nutrition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.labels import meal_type_label, unit_label
from app.api.deps import DateRange
from app.models import NutritionEntry

NUTRITION_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class DailyNutritionRow:
    day: date
    calories: float | None
    entry_count: int


async def get_daily(session: AsyncSession, date_range: DateRange) -> list[DailyNutritionRow]:
    sql = text(
        "SELECT day, calories, entry_count FROM mv_daily_nutrition "
        "WHERE (:start IS NULL OR day >= :start) AND (:end IS NULL OR day <= :end) "
        "ORDER BY day"
    )
    rows = (
        await session.execute(sql, {"start": date_range.start, "end": date_range.end})
    ).all()
    return [
        DailyNutritionRow(day=r.day, calories=r.calories, entry_count=r.entry_count)
        for r in rows
    ]


@dataclass(frozen=True, slots=True)
class EntryRow:
    at: datetime
    food_name: str
    meal_type_label: str
    amount: float | None
    unit_label: str
    calories: float | None


def _entries_query(date_range: DateRange):
    query = select(NutritionEntry).order_by(NutritionEntry.consumed_at)
    if date_range.start is not None:
        query = query.where(NutritionEntry.consumed_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(NutritionEntry.consumed_at <= date_range.end)
    return query


async def list_entries(
    session: AsyncSession, date_range: DateRange, page: int
) -> tuple[list[EntryRow], int]:
    base_query = _entries_query(date_range)
    total = (
        await session.execute(select(func.count()).select_from(base_query.subquery()))
    ).scalar_one()

    offset = (page - 1) * NUTRITION_PAGE_SIZE
    rows = (
        await session.execute(base_query.limit(NUTRITION_PAGE_SIZE).offset(offset))
    ).scalars().all()

    entries = [
        EntryRow(
            at=r.consumed_at,
            food_name=r.food_name,
            meal_type_label=meal_type_label(r.meal_type),
            amount=r.amount,
            unit_label=unit_label(r.unit_code),
            calories=r.calories,
        )
        for r in rows
    ]
    return entries, total
```

- [ ] **Step 4: Lancer les tests du service**

Run: `cd backend && uv run pytest tests/integration/test_service_nutrition.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Écrire les tests d'API, les schémas et le routeur**

Créer `backend/tests/integration/test_api_nutrition.py` :

```python
"""Tests d'intégration de l'API nutrition."""

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import NutritionEntry

pytestmark = pytest.mark.asyncio


async def test_get_entries_paginates_with_page_param(session: AsyncSession) -> None:
    session.add(
        NutritionEntry(
            source_uuid="nut-api-1",
            consumed_at=datetime(2026, 4, 1, 8, tzinfo=timezone.utc),
            food_name="Riz",
            meal_type=100002,
            unit_code=120001,
            calories=200.0,
        )
    )
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/nutrition/entries",
            params={"from": "2026-04-01", "to": "2026-04-02", "page": 1},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["items"][0]["food_name"] == "Riz"


async def test_get_daily_endpoint_returns_list() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/nutrition/daily")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

Créer `backend/app/schemas/nutrition.py` :

```python
"""Schémas Pydantic de la famille nutrition."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailyNutritionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    calories: float | None
    entry_count: int


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    food_name: str
    meal_type_label: str
    amount: float | None
    unit_label: str
    calories: float | None
```

Créer `backend/app/api/nutrition.py` :

```python
"""Routes de lecture de la famille nutrition."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.common import Page
from app.schemas.nutrition import DailyNutritionOut, EntryOut
from app.services import nutrition as nutrition_service
from app.services.nutrition import NUTRITION_PAGE_SIZE

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/daily", response_model=list[DailyNutritionOut])
async def get_daily(session: DbSession, date_range: DateRangeDep):
    rows = await nutrition_service.get_daily(session, date_range)
    return [DailyNutritionOut.model_validate(r) for r in rows]


@router.get("/entries", response_model=Page[EntryOut])
async def get_entries(
    session: DbSession, date_range: DateRangeDep, page: int = Query(default=1, ge=1)
):
    entries, total = await nutrition_service.list_entries(session, date_range, page)
    return Page[EntryOut](
        items=[EntryOut.model_validate(e) for e in entries],
        page=page,
        page_size=NUTRITION_PAGE_SIZE,
        total=total,
    )
```

Modifier `backend/app/api/router.py` :

```python
"""Assemble tous les routers de lecture sous le préfixe /api.

Chaque tâche d'endpoint ajoute ici l'inclusion de son propre routeur ; ce
fichier ne définit jamais de route lui-même.
"""

from fastapi import APIRouter

from app.api.body import router as body_router
from app.api.nutrition import router as nutrition_router

api_router = APIRouter(prefix="/api")
api_router.include_router(body_router)
api_router.include_router(nutrition_router)
```

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_api_nutrition.py -v`
Expected: PASS, 2 tests

- [ ] **Step 7: Commiter**

```bash
git add backend/app/services/nutrition.py backend/app/schemas/nutrition.py backend/app/api/nutrition.py backend/app/api/router.py backend/tests/integration/test_service_nutrition.py backend/tests/integration/test_api_nutrition.py
git commit -m "feat: add nutrition daily and paginated entries endpoints"
```

---

### Task 18: Nutrition — répartition par repas et aliments récurrents

**Files:**
- Modify: `backend/app/services/nutrition.py`
- Modify: `backend/app/schemas/nutrition.py`
- Modify: `backend/app/api/nutrition.py`
- Create: `backend/tests/integration/test_service_nutrition_breakdown.py`
- Create: `backend/tests/integration/test_api_nutrition_breakdown.py`

**Interfaces:**
- Consumes: `app.analytics.nutrition.compute_top_foods`, `NutritionEntryInput`
  (tâche 14) ; `app.analytics.labels.meal_type_label` (tâche 3).
- Produces: `services.nutrition.MealTypeShare(meal_type_label: str, calories: float | None, entry_count: int)`,
  `services.nutrition.NutritionBreakdown(by_meal_type: list[MealTypeShare], top_foods: list[TopFood])`,
  `services.nutrition.get_breakdown(session, date_range) -> NutritionBreakdown`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/integration/test_service_nutrition_breakdown.py` :

```python
"""Tests d'intégration de la répartition nutrition par repas."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.models import NutritionEntry
from app.services.nutrition import get_breakdown

pytestmark = pytest.mark.asyncio


async def test_get_breakdown_groups_by_meal_type_and_ranks_foods(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            NutritionEntry(
                source_uuid="brk-1",
                consumed_at=datetime(2026, 4, 1, 8, tzinfo=timezone.utc),
                food_name="Avoine",
                meal_type=100001,
                unit_code=120001,
                calories=350.0,
            ),
            NutritionEntry(
                source_uuid="brk-2",
                consumed_at=datetime(2026, 4, 1, 12, tzinfo=timezone.utc),
                food_name="Poulet",
                meal_type=100002,
                unit_code=120001,
                calories=500.0,
            ),
            NutritionEntry(
                source_uuid="brk-3",
                consumed_at=datetime(2026, 4, 2, 12, tzinfo=timezone.utc),
                food_name="Poulet",
                meal_type=100002,
                unit_code=120001,
                calories=520.0,
            ),
        ]
    )
    await session.commit()

    breakdown = await get_breakdown(
        session, DateRange(start=date(2026, 4, 1), end=date(2026, 4, 30))
    )

    shares = {s.meal_type_label: s for s in breakdown.by_meal_type}
    assert shares["Petit-déjeuner"].calories == pytest.approx(350.0)
    assert shares["Déjeuner"].calories == pytest.approx(1020.0)
    assert breakdown.top_foods[0].food_name == "Poulet"
    assert breakdown.top_foods[0].entry_count == 2
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/integration/test_service_nutrition_breakdown.py -v`
Expected: FAIL — `get_breakdown` n'existe pas

- [ ] **Step 3: Étendre le service**

Ajouter à `backend/app/services/nutrition.py` :

```python
from app.analytics.nutrition import NutritionEntryInput, TopFood, compute_top_foods


@dataclass(frozen=True, slots=True)
class MealTypeShare:
    meal_type_label: str
    calories: float | None
    entry_count: int


@dataclass(frozen=True, slots=True)
class NutritionBreakdown:
    by_meal_type: list[MealTypeShare]
    top_foods: list[TopFood]


async def get_breakdown(session: AsyncSession, date_range: DateRange) -> NutritionBreakdown:
    rows = (await session.execute(_entries_query(date_range))).scalars().all()

    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    has_calories: dict[str, bool] = {}
    for row in rows:
        label = meal_type_label(row.meal_type)
        counts[label] = counts.get(label, 0) + 1
        if row.calories is not None:
            totals[label] = totals.get(label, 0.0) + row.calories
            has_calories[label] = True

    by_meal_type = [
        MealTypeShare(
            meal_type_label=label,
            calories=totals.get(label) if has_calories.get(label) else None,
            entry_count=count,
        )
        for label, count in counts.items()
    ]

    entries = [
        NutritionEntryInput(consumed_at=r.consumed_at, food_name=r.food_name, calories=r.calories)
        for r in rows
    ]
    top_foods = compute_top_foods(entries, limit=10)

    return NutritionBreakdown(by_meal_type=by_meal_type, top_foods=top_foods)
```

- [ ] **Step 4: Lancer le test du service**

Run: `cd backend && uv run pytest tests/integration/test_service_nutrition_breakdown.py -v`
Expected: PASS, 1 test

- [ ] **Step 5: Écrire le test d'API, les schémas et le routeur**

Créer `backend/tests/integration/test_api_nutrition_breakdown.py` :

```python
"""Test d'intégration de l'endpoint /api/nutrition/breakdown."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_get_breakdown_endpoint_returns_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/nutrition/breakdown")

    assert response.status_code == 200
    body = response.json()
    assert "by_meal_type" in body
    assert "top_foods" in body
```

Ajouter à `backend/app/schemas/nutrition.py` :

```python
class MealTypeShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_type_label: str
    calories: float | None
    entry_count: int


class TopFoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    food_name: str
    entry_count: int
    total_calories: float | None


class NutritionBreakdownOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    by_meal_type: list[MealTypeShareOut]
    top_foods: list[TopFoodOut]
```

Ajouter à `backend/app/api/nutrition.py` :

```python
from app.schemas.nutrition import NutritionBreakdownOut  # à fusionner avec les imports


@router.get("/breakdown", response_model=NutritionBreakdownOut)
async def get_breakdown(session: DbSession, date_range: DateRangeDep):
    breakdown = await nutrition_service.get_breakdown(session, date_range)
    return NutritionBreakdownOut.model_validate(breakdown)
```

- [ ] **Step 6: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/integration/test_api_nutrition_breakdown.py -v`
Expected: PASS, 1 test

- [ ] **Step 7: Commiter**

```bash
git add backend/app/services/nutrition.py backend/app/schemas/nutrition.py backend/app/api/nutrition.py backend/tests/integration/test_service_nutrition_breakdown.py backend/tests/integration/test_api_nutrition_breakdown.py
git commit -m "feat: add nutrition breakdown by meal type and top foods"
```

---

### Task 19: Phases — liste, phase courante, détail

Côté lecture uniquement : la création/modification/suppression des phases
est hors périmètre (plan 3).

**Files:**
- Create: `backend/app/services/phases.py`
- Create: `backend/app/schemas/phases.py`
- Create: `backend/app/api/phases.py`
- Create: `backend/tests/integration/test_service_phases.py`
- Create: `backend/tests/integration/test_api_phases.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Consumes: `app.models.Phase`, `PhaseKind` (plan 1) ;
  `app.errors.NotFoundError` (tâche 1).
- Produces: `services.phases.list_phases(session) -> list[Phase]`,
  `services.phases.get_current_phase(session, today: date) -> Phase | None`
  (résolution : `starts_on` le plus récent `<= today`, cf. spec 4.3),
  `services.phases.get_phase(session, phase_id: int) -> Phase` (lève
  `NotFoundError` si absent).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/integration/test_service_phases.py` :

```python
"""Tests d'intégration du service phases — résolution de la phase courante."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models import Phase, PhaseKind
from app.services.phases import get_current_phase, get_phase, list_phases

pytestmark = pytest.mark.asyncio


async def _phase(session: AsyncSession, **kwargs) -> Phase:
    phase = Phase(**kwargs)
    session.add(phase)
    await session.commit()
    await session.refresh(phase)
    return phase


async def test_get_current_phase_picks_most_recent_starts_on_at_or_before_today(
    session: AsyncSession,
) -> None:
    """Spec 4.3 : chevauchement d'un jour toléré, la phase courante est
    celle dont starts_on est le plus récent <= aujourd'hui."""
    await _phase(
        session, name="Sèche 1", kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1), ends_on=date(2026, 3, 1),
    )
    maintain = await _phase(
        session, name="Maintien", kind=PhaseKind.MAINTAIN,
        starts_on=date(2026, 3, 1), ends_on=date(2026, 4, 1),
    )

    result = await get_current_phase(session, today=date(2026, 3, 15))

    assert result.id == maintain.id


async def test_get_current_phase_is_none_before_any_phase(session: AsyncSession) -> None:
    await _phase(
        session, name="Sèche 1", kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1), ends_on=date(2026, 3, 1),
    )

    result = await get_current_phase(session, today=date(2025, 12, 1))

    assert result is None


async def test_get_phase_raises_not_found_for_unknown_id(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await get_phase(session, phase_id=999999)


async def test_list_phases_orders_by_starts_on(session: AsyncSession) -> None:
    await _phase(
        session, name="Sèche 2", kind=PhaseKind.CUT,
        starts_on=date(2026, 6, 1), ends_on=date(2026, 8, 1),
    )
    await _phase(
        session, name="Sèche 1", kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1), ends_on=date(2026, 3, 1),
    )

    phases = await list_phases(session)

    assert [p.name for p in phases[:2]] == ["Sèche 1", "Sèche 2"]
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_service_phases.py -v`
Expected: FAIL — `app.services.phases` n'existe pas

- [ ] **Step 3: Écrire le service**

Créer `backend/app/services/phases.py` :

```python
"""Service phases — lecture seule. CRUD hors périmètre de ce plan."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models import Phase


async def list_phases(session: AsyncSession) -> list[Phase]:
    result = await session.execute(select(Phase).order_by(Phase.starts_on))
    return list(result.scalars().all())


async def get_current_phase(session: AsyncSession, today: date) -> Phase | None:
    result = await session.execute(
        select(Phase)
        .where(Phase.starts_on <= today)
        .order_by(Phase.starts_on.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_phase(session: AsyncSession, phase_id: int) -> Phase:
    phase = await session.get(Phase, phase_id)
    if phase is None:
        raise NotFoundError(f"phase {phase_id} introuvable")
    return phase
```

- [ ] **Step 4: Lancer les tests du service**

Run: `cd backend && uv run pytest tests/integration/test_service_phases.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Écrire le test d'API, les schémas et le routeur**

Créer `backend/tests/integration/test_api_phases.py` :

```python
"""Tests d'intégration de l'API phases (lecture seule)."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import Phase, PhaseKind

pytestmark = pytest.mark.asyncio


async def test_get_phase_returns_404_problem_json_when_missing() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/phases/999999")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


async def test_get_phase_by_id_returns_kind_and_targets(session: AsyncSession) -> None:
    phase = Phase(
        name="Sèche test",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 1),
        weight_target_kg=75.0,
    )
    session.add(phase)
    await session.commit()
    await session.refresh(phase)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/phases/{phase.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "cut"
    assert body["weight_target_kg"] == 75.0


async def test_get_current_phase_can_be_null() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/phases/current", params={"today": "1999-01-01"}
        )

    assert response.status_code == 200
    assert response.json() is None
```

Créer `backend/app/schemas/phases.py` :

```python
"""Schémas Pydantic de la famille phases."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.phase import PhaseKind


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

Créer `backend/app/api/phases.py` :

```python
"""Routes de lecture de la famille phases."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.phases import PhaseOut
from app.services import phases as phases_service

router = APIRouter(prefix="/phases", tags=["phases"])


@router.get("", response_model=list[PhaseOut])
async def get_phases(session: DbSession):
    phases = await phases_service.list_phases(session)
    return [PhaseOut.model_validate(p) for p in phases]


@router.get("/current", response_model=PhaseOut | None)
async def get_current_phase(
    session: DbSession, today: date = Query(default_factory=date.today)
):
    phase = await phases_service.get_current_phase(session, today)
    return PhaseOut.model_validate(phase) if phase is not None else None


@router.get("/{phase_id}", response_model=PhaseOut)
async def get_phase(session: DbSession, phase_id: int):
    phase = await phases_service.get_phase(session, phase_id)
    return PhaseOut.model_validate(phase)
```

**Attention à l'ordre des routes** : `/current` doit être déclaré avant
`/{phase_id}`, sinon FastAPI tente de convertir `"current"` en entier pour
la route paramétrée et renvoie 422 au lieu d'atteindre `/current`.

Modifier `backend/app/api/router.py` :

```python
"""Assemble tous les routers de lecture sous le préfixe /api.

Chaque tâche d'endpoint ajoute ici l'inclusion de son propre routeur ; ce
fichier ne définit jamais de route lui-même.
"""

from fastapi import APIRouter

from app.api.body import router as body_router
from app.api.nutrition import router as nutrition_router
from app.api.phases import router as phases_router

api_router = APIRouter(prefix="/api")
api_router.include_router(body_router)
api_router.include_router(nutrition_router)
api_router.include_router(phases_router)
```

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_api_phases.py -v`
Expected: PASS, 3 tests

- [ ] **Step 7: Commiter**

```bash
git add backend/app/services/phases.py backend/app/schemas/phases.py backend/app/api/phases.py backend/app/api/router.py backend/tests/integration/test_service_phases.py backend/tests/integration/test_api_phases.py
git commit -m "feat: add read-only phases list, current and detail endpoints"
```

---

### Task 20: Phases — rapport de phase

Spec 6 : « valeurs de début et de fin, deltas, vitesse mensuelle, variation
en pourcentage, calories moyennes, et pour chaque objectif son état
d'atteinte ». Assemble les tâches 4 (deltas), 5 (composition) et 6
(objectifs) autour d'une seule phase.

**Files:**
- Modify: `backend/app/services/phases.py`
- Modify: `backend/app/schemas/phases.py`
- Modify: `backend/app/api/phases.py`
- Create: `backend/tests/integration/test_service_phase_report.py`
- Create: `backend/tests/integration/test_api_phase_report.py`

**Interfaces:**
- Consumes: `TimePoint`, `compute_change_between` (tâche 4) ;
  `CompositionPoint`, `compute_recomposition` (tâche 5) ; `Metric`,
  `build_phase_metric_report` (tâche 6) ; `get_phase` (tâche 19).
- Produces: `services.phases.PhaseReport(phase: Phase, metrics: list[PhaseMetricReport], average_calories_kcal: float | None, recomposition: RecompositionResult)`,
  `services.phases.get_phase_report(session, phase_id: int, *, today: date) -> PhaseReport`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/integration/test_service_phase_report.py` :

```python
"""Tests d'intégration du rapport de phase — assemble deltas, composition
et objectifs autour de mesures et d'un journal alimentaire réels."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.objectives import Metric
from app.models import BodyMeasurement, NutritionEntry, Phase, PhaseKind
from app.services.phases import get_phase_report

pytestmark = pytest.mark.asyncio


async def test_get_phase_report_computes_metrics_and_objective_status(
    session: AsyncSession,
) -> None:
    phase = Phase(
        name="Sèche rapport",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 2),
        weight_target_kg=77.0,
    )
    session.add(phase)
    session.add_all(
        [
            BodyMeasurement(
                source_uuid="rpt-1",
                measured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                weight_kg=80.0,
            ),
            BodyMeasurement(
                source_uuid="rpt-2",
                measured_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                weight_kg=78.0,
            ),
            NutritionEntry(
                source_uuid="rpt-3",
                consumed_at=datetime(2026, 1, 15, 12, tzinfo=timezone.utc),
                food_name="Repas",
                calories=2200.0,
            ),
            NutritionEntry(
                source_uuid="rpt-4",
                consumed_at=datetime(2026, 2, 15, 12, tzinfo=timezone.utc),
                food_name="Repas",
                calories=2400.0,
            ),
        ]
    )
    await session.commit()
    await session.refresh(phase)
    await session.execute(text("REFRESH MATERIALIZED VIEW mv_daily_nutrition"))
    await session.commit()

    report = await get_phase_report(session, phase.id, today=date(2026, 3, 2))

    weight_metric = next(m for m in report.metrics if m.metric is Metric.WEIGHT)
    assert weight_metric.start_value == 80.0
    assert weight_metric.end_value == 78.0
    assert weight_metric.change == pytest.approx(-2.0)
    assert weight_metric.objective is not None
    assert weight_metric.objective.achieved is False  # 78 > 77, sèche non atteinte
    assert report.average_calories_kcal == pytest.approx(2300.0)
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/integration/test_service_phase_report.py -v`
Expected: FAIL — `get_phase_report` n'existe pas

- [ ] **Step 3: Étendre le service**

Ajouter à `backend/app/services/phases.py` :

```python
from dataclasses import dataclass

from sqlalchemy import text

from app.analytics.composition import (
    CompositionPoint,
    RecompositionResult,
    compute_recomposition,
)
from app.analytics.deltas import TimePoint, compute_change_between
from app.analytics.objectives import Metric, PhaseMetricReport, build_phase_metric_report
from app.models import BodyMeasurement


_METRIC_COLUMN = {
    Metric.WEIGHT: ("weight_kg", "weight_target_kg"),
    Metric.BODY_FAT: ("body_fat_pct", "body_fat_target_pct"),
    Metric.MUSCLE: ("skeletal_muscle_mass_kg", "skeletal_muscle_target_kg"),
}


async def _measurement_time_points(
    session: AsyncSession, column: str
) -> list[TimePoint]:
    rows = (
        await session.execute(
            select(BodyMeasurement.measured_at, getattr(BodyMeasurement, column)).order_by(
                BodyMeasurement.measured_at
            )
        )
    ).all()
    return [TimePoint(at=at.date(), value=value) for at, value in rows]


@dataclass(frozen=True, slots=True)
class PhaseReport:
    phase: Phase
    metrics: list[PhaseMetricReport]
    average_calories_kcal: float | None
    recomposition: RecompositionResult


async def get_phase_report(session: AsyncSession, phase_id: int, *, today: date) -> PhaseReport:
    phase = await get_phase(session, phase_id)
    end_date = min(phase.ends_on, today)
    days_elapsed = max((end_date - phase.starts_on).days, 0)

    metrics = []
    for metric, (column, target_attr) in _METRIC_COLUMN.items():
        points = await _measurement_time_points(session, column)
        delta = compute_change_between(points, start=phase.starts_on, end=end_date)
        metrics.append(
            build_phase_metric_report(
                metric=metric,
                delta=delta,
                days_elapsed=days_elapsed,
                phase_kind=phase.kind,
                target=getattr(phase, target_attr),
            )
        )

    calories_sql = text(
        "SELECT avg(calories) AS avg_calories FROM mv_daily_nutrition "
        "WHERE day >= :start AND day <= :end"
    )
    average_calories = (
        await session.execute(calories_sql, {"start": phase.starts_on, "end": end_date})
    ).scalar_one()

    fat_points_raw = await _measurement_time_points(session, "body_fat_mass_kg")
    lean_points_raw = await _measurement_time_points(session, "fat_free_mass_kg")
    lean_by_date = {p.at: p.value for p in lean_points_raw}
    composition_points = [
        CompositionPoint(at=p.at, fat_mass_kg=p.value, lean_mass_kg=lean_by_date.get(p.at))
        for p in fat_points_raw
    ]
    recomposition = compute_recomposition(composition_points, start=phase.starts_on, end=end_date)

    return PhaseReport(
        phase=phase,
        metrics=metrics,
        average_calories_kcal=average_calories,
        recomposition=recomposition,
    )
```

Ajouter en tête de `backend/app/services/phases.py` l'import manquant
`from sqlalchemy import select` (déjà présent depuis la tâche 19 — vérifier
qu'il n'est pas dupliqué).

- [ ] **Step 4: Lancer le test du service**

Run: `cd backend && uv run pytest tests/integration/test_service_phase_report.py -v`
Expected: PASS, 1 test

- [ ] **Step 5: Écrire le test d'API, le schéma et le routeur**

Créer `backend/tests/integration/test_api_phase_report.py` :

```python
"""Test d'intégration de l'endpoint /api/phases/{id}/report."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import Phase, PhaseKind

pytestmark = pytest.mark.asyncio


async def test_get_phase_report_endpoint(session: AsyncSession) -> None:
    phase = Phase(
        name="Sèche report api",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 2, 1),
    )
    session.add(phase)
    await session.commit()
    await session.refresh(phase)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/phases/{phase.id}/report")

    assert response.status_code == 200
    body = response.json()
    assert len(body["metrics"]) == 3
    assert {m["metric"] for m in body["metrics"]} == {"weight", "body_fat", "muscle"}
```

Ajouter à `backend/app/schemas/phases.py` :

```python
from app.analytics.objectives import Direction, Metric


class ObjectiveCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: Metric
    target: float
    current: float | None
    direction: Direction
    achieved: bool | None
    remaining: float | None


class PhaseMetricReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: Metric
    start_value: float | None
    end_value: float | None
    change: float | None
    change_pct: float | None
    monthly_rate: float | None
    objective: ObjectiveCheckOut | None


class RecompositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fat_mass_delta_kg: float | None
    lean_mass_delta_kg: float | None


class PhaseReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phase: PhaseOut
    metrics: list[PhaseMetricReportOut]
    average_calories_kcal: float | None
    recomposition: RecompositionOut
```

Ajouter à `backend/app/api/phases.py` :

```python
from datetime import date as date_type

from app.schemas.phases import PhaseReportOut  # à fusionner avec les imports


@router.get("/{phase_id}/report", response_model=PhaseReportOut)
async def get_phase_report(
    session: DbSession, phase_id: int, today: date_type = Query(default_factory=date_type.today)
):
    report = await phases_service.get_phase_report(session, phase_id, today=today)
    return PhaseReportOut.model_validate(report)
```

- [ ] **Step 6: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/integration/test_api_phase_report.py -v`
Expected: PASS, 1 test

- [ ] **Step 7: Commiter**

```bash
git add backend/app/services/phases.py backend/app/schemas/phases.py backend/app/api/phases.py backend/tests/integration/test_service_phase_report.py backend/tests/integration/test_api_phase_report.py
git commit -m "feat: add per-phase report combining deltas objectives and recomposition"
```

---
