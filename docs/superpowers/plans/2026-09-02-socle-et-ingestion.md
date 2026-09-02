# Socle et ingestion — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mettre debout PostgreSQL et MinIO, créer le schéma complet, et
ingérer de façon idempotente les 535 Mo de l'export Samsung Health réel.

**Architecture:** Un backend FastAPI dont la couche d'ingestion se découpe en
quatre étages sans dépendance circulaire : des parseurs bas niveau sans
connaissance du domaine, un mapper qui produit des dataclasses de domaine à
partir des lignes brutes, un loader qui fait des upserts par lots sur les
`source_uuid`, et un pipeline qui orchestre le tout en journalisant un
`ingestion_run`. Les trois premiers étages sont testables sans base de
données.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 asynchrone, asyncpg,
Alembic, pydantic-settings, uv, pytest, Docker Compose, PostgreSQL 17,
MinIO.

**Spec:** `docs/superpowers/specs/2026-09-02-migration-fastapi-react-design.md`

## Global Constraints

- Python `>=3.13`. Aucun code compatible 3.11 requis.
- Planchers de dépendances : `fastapi>=0.115`, `sqlalchemy>=2.0.36`,
  `asyncpg>=0.30`, `alembic>=1.14`, `pydantic>=2.10`,
  `pydantic-settings>=2.7`, `minio>=7.2`, `pillow>=11.0`,
  `pytest>=8.3`, `pytest-asyncio>=0.24`, `httpx>=0.28`, `ruff>=0.8`.
  Ce sont des planchers, jamais des versions figées.
- **Aucun identifiant en dur dans le code.** `BA_DATABASE_URL`,
  `BA_MINIO_ACCESS_KEY` et `BA_MINIO_SECRET_KEY` sont obligatoires et sans
  valeur par défaut ; l'application refuse de démarrer sans eux.
- **Une valeur absente est `None`, jamais `0` ni `NaN`**, de la lecture du
  CSV jusqu'à la réponse HTTP. Une courbe trouée est honnête, une courbe qui
  plonge à zéro est un mensonge.
- **Tous les horodatages sont conservés avec leur fuseau.** L'export fournit
  une heure locale naïve dans `start_time` et son décalage dans
  `time_offset` ; les deux doivent être recombinés. Les colonnes sont en
  `TIMESTAMPTZ`.
- Toute table de faits porte un `source_uuid` unique et s'insère en
  `ON CONFLICT (source_uuid) DO UPDATE`. Un ré-import ne crée jamais de
  doublon.
- Le code, les noms de tables et de colonnes, les messages de commit sont en
  anglais. Les commentaires et la documentation sont en français, comme le
  reste du dépôt.
- Les données réelles de référence sont dans
  `/home/sedelpeuch/migration_body-analysis` et ne sont **jamais modifiées**
  par le code : elles sont lues seulement.

## Chiffres de référence des données réelles

Ces valeurs servent d'assertions à la tâche 13. Elles ont été mesurées sur
l'export réel.

| Grandeur | Valeur attendue |
| --- | --- |
| Mesures corporelles | 647 |
| Entrées alimentaires | 11 855 |
| Séances | 4 734 |
| Séances de natation (code 14001) | 330 |
| Séances avec séries de musculation | 1 531 |
| Séries de musculation | ~3 000 |
| Fichiers `live_data` référencés | 4 654 |
| Fichiers `location_data` référencés | 387 |
| Phases (depuis `phases.json`) | 8 |

## Structure des fichiers

```
compose.yaml                          services db et minio
backend/
  pyproject.toml                      dépendances, config ruff et pytest
  .python-version                     3.13
  .env.example                        variables attendues, sans secret réel
  alembic.ini
  app/
    config.py                         Settings pydantic, secrets obligatoires
    db.py                             engine et sessionmaker asynchrones
    main.py                           fabrique d'application, /api/health
    models/
      base.py                         Base declarative et mixin d'horodatage
      body.py                         BodyMeasurement
      nutrition.py                    NutritionEntry
      phase.py                        Phase et enum PhaseKind
      workout.py                      Workout et ses cinq tables filles
      photo.py                        Photo
      ingestion.py                    IngestionRun et enum IngestionStatus
    ingestion/
      phases.py                       lecture de phases.json
      refresh.py                      rafraîchissement des vues matérialisées
      samsung/
        parsers.py                    conversions bas niveau, lecture CSV
        sports.py                     résolution du sport depuis le code
        records.py                    dataclasses du domaine d'ingestion
        mapper.py                     lignes brutes -> dataclasses
        json_files.py                 résolution et lecture des JSON annexes
        assembler.py                  séance + JSON annexes -> WorkoutBundle
        loader.py                     upserts par lots
        pipeline.py                   orchestration d'un run
  migrations/                         Alembic
  scripts/migrate_legacy.py           migration one-shot, jetable
  tests/
    conftest.py
    unit/                             sans base de données
    integration/                      avec base de données jetable
    fixtures/samsung/                 extraits des données réelles
```

Découpage assumé : `models/workout.py` regroupe `Workout` et ses cinq tables
filles parce qu'elles ne changent jamais séparément — leur schéma est une
seule décision. À l'inverse `parsers.py`, `sports.py` et `mapper.py` sont
séparés parce que les deux premiers sont réutilisables et testables sans
connaître l'export, alors que le troisième connaît intimement ses colonnes.

---

### Task 1: Socle du backend et services d'infrastructure

**Files:**
- Create: `compose.yaml`
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/unit/__init__.py`
- Create: `backend/tests/unit/test_health.py`
- Modify: `.pre-commit-config.yaml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: rien, première tâche.
- Produces: `app.config.Settings` et l'instance `app.config.settings` ;
  `app.main.create_app() -> FastAPI`. Les tâches suivantes importent
  `settings.database_url`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_health.py` :

```python
"""Vérifie que l'application se construit et répond."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Créer `backend/tests/conftest.py` :

```python
"""Configuration commune aux tests.

Les secrets sont obligatoires dans Settings ; on les fournit ici avec des
valeurs de test pour que l'import de app.config n'échoue pas.
"""

import os

os.environ.setdefault(
    "BA_DATABASE_URL",
    "postgresql+asyncpg://body:test@localhost:5432/body_analysis_test",
)
os.environ.setdefault("BA_MINIO_ACCESS_KEY", "test-access-key")
os.environ.setdefault("BA_MINIO_SECRET_KEY", "test-secret-key")
```

Créer `backend/tests/__init__.py` et `backend/tests/unit/__init__.py` vides.

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_health.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Écrire le pyproject et la configuration**

Créer `backend/.python-version` :

```
3.13
```

Créer `backend/pyproject.toml` :

```toml
[project]
name = "body-analysis-api"
version = "0.1.0"
description = "API de suivi et d'analyse corporelle"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "python-multipart>=0.0.18",
    "minio>=7.2",
    "pillow>=11.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
    "ruff>=0.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra"

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
```

Créer `backend/app/__init__.py` vide.

Créer `backend/app/config.py` :

```python
"""Configuration de l'application, lue depuis l'environnement.

Les identifiants n'ont volontairement aucune valeur par défaut : mieux vaut
un démarrage qui échoue clairement qu'un secret en dur dans le dépôt.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BA_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "body-analysis-photos"
    minio_secure: bool = False


settings = Settings()  # type: ignore[call-arg]
```

Créer `backend/app/main.py` :

```python
"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

Créer `backend/.env.example` :

```
# Copier en .env et renseigner. Aucune de ces valeurs n'a de défaut.
BA_DATABASE_URL=postgresql+asyncpg://body:changeme@localhost:5432/body_analysis
BA_MINIO_ENDPOINT=localhost:9000
BA_MINIO_ACCESS_KEY=changeme
BA_MINIO_SECRET_KEY=changeme
BA_MINIO_BUCKET=body-analysis-photos
BA_MINIO_SECURE=false
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv sync && uv run pytest tests/unit/test_health.py -v`
Expected: PASS, 1 test

- [ ] **Step 5: Écrire le compose et le démarrer**

Créer `compose.yaml` à la racine du dépôt :

```yaml
name: body-analysis

services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: body_analysis
      POSTGRES_USER: body
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD est requis}
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U body -d body_analysis"]
      interval: 5s
      timeout: 5s
      retries: 10

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:?MINIO_ROOT_USER est requis}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD est requis}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  db_data:
  minio_data:
```

Créer un `.env` à la racine, non versionné, avec des valeurs locales :

```bash
cat > .env <<'EOF'
POSTGRES_PASSWORD=body-local-dev
MINIO_ROOT_USER=body
MINIO_ROOT_PASSWORD=body-local-dev-minio
EOF
```

Run: `docker compose up -d && docker compose ps`
Expected: `db` et `minio` en état `healthy`

- [ ] **Step 6: Mettre à jour le pre-commit et le gitignore**

Dans `.pre-commit-config.yaml`, remplacer les hooks `black` et `poetry` par
`ruff` — le backend n'utilise plus poetry :

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: "v5.0.0"
    hooks:
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-toml
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Ajouter à `.gitignore` :

```
.env
backend/.venv/
backend/.env
__pycache__/
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 7: Vérifier et commiter**

Run: `cd backend && uv run ruff check . && uv run pytest -v`
Expected: aucune erreur ruff, 1 test PASS

```bash
git add compose.yaml .gitignore .pre-commit-config.yaml backend/
git commit -m "feat: bootstrap FastAPI backend with postgres and minio services"
```

---

### Task 2: Parseurs bas niveau de l'export Samsung

**Files:**
- Create: `backend/app/ingestion/__init__.py`
- Create: `backend/app/ingestion/samsung/__init__.py`
- Create: `backend/app/ingestion/samsung/parsers.py`
- Create: `backend/tests/unit/test_parsers.py`
- Create: `backend/tests/fixtures/samsung/weight_sample.csv`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `parse_float(raw: object) -> float | None`
  - `parse_int(raw: object) -> int | None`
  - `parse_utc_offset(raw: object) -> timezone | None`
  - `parse_aware_datetime(raw_time: object, raw_offset: object) -> datetime | None`
  - `parse_epoch_millis(raw: object) -> datetime | None`
  - `read_samsung_csv(path: Path) -> Iterator[dict[str, str]]`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/weight_sample.csv` — trois lignes
extraites du format réel, la première étant la ligne de métadonnées que
Samsung place avant les en-têtes :

```csv
com.samsung.health.weight,7006003,12
start_time,weight,body_fat,skeletal_muscle_mass,time_offset,datauuid
2018-11-29 22:54:00.000,90.0,,,UTC+0100,a04ec306-ed98-460e-853f-629b404d0757
2026-08-31 06:29:10.346,65.6,10.8,37.7,UTC+0200,f631923e-bc08-404a-8d0c-9468aa4dee2b
```

Créer `backend/tests/unit/test_parsers.py` :

```python
"""Tests des conversions bas niveau de l'export Samsung."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.ingestion.samsung.parsers import (
    parse_aware_datetime,
    parse_epoch_millis,
    parse_float,
    parse_int,
    parse_utc_offset,
    read_samsung_csv,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("65.6", 65.6),
        ("1.4374734", 1.4374734),
        ("-0.002120687859132886", -0.002120687859132886),
        ("", None),
        ("   ", None),
        (None, None),
        ("abc", None),
    ],
)
def test_parse_float(raw: object, expected: float | None) -> None:
    assert parse_float(raw) == expected


def test_parse_float_never_returns_nan() -> None:
    """Une valeur absente doit être None, jamais NaN : le code Streamlit
    remplaçait les vides par math.nan, ce qui contaminait les moyennes."""
    assert parse_float("") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("100002", 100002), ("0", 0), ("-1", -1), ("", None), (None, None)],
)
def test_parse_int(raw: object, expected: int | None) -> None:
    assert parse_int(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("UTC+0200", timezone(timedelta(hours=2))),
        ("UTC+0100", timezone(timedelta(hours=1))),
        ("UTC-0500", timezone(timedelta(hours=-5))),
        ("UTC+0530", timezone(timedelta(hours=5, minutes=30))),
        ("", None),
        (None, None),
        ("Europe/Paris", None),
    ],
)
def test_parse_utc_offset(raw: object, expected: timezone | None) -> None:
    assert parse_utc_offset(raw) == expected


def test_parse_aware_datetime_combines_local_time_and_offset() -> None:
    result = parse_aware_datetime("2026-08-31 06:29:10.346", "UTC+0200")

    assert result == datetime(
        2026, 8, 31, 6, 29, 10, tzinfo=timezone(timedelta(hours=2))
    )


def test_parse_aware_datetime_without_offset_assumes_utc() -> None:
    """Sans décalage connu on ne peut pas inventer un fuseau ; on retient
    UTC pour rester déterministe et comparable."""
    result = parse_aware_datetime("2026-08-31 06:29:10.346", "")

    assert result == datetime(2026, 8, 31, 6, 29, 10, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "raw", ["", None, "pas une date", "2026-02-30 10:00:00", "2026-13-01 10:00:00"]
)
def test_parse_aware_datetime_rejects_invalid(raw: object) -> None:
    assert parse_aware_datetime(raw, "UTC+0200") is None


def test_parse_epoch_millis() -> None:
    result = parse_epoch_millis(1644085620000)

    assert result == datetime(2022, 2, 5, 18, 27, tzinfo=timezone.utc)


@pytest.mark.parametrize("raw", ["", None, "abc"])
def test_parse_epoch_millis_rejects_invalid(raw: object) -> None:
    assert parse_epoch_millis(raw) is None


def test_read_samsung_csv_skips_metadata_line() -> None:
    rows = list(read_samsung_csv(FIXTURES / "weight_sample.csv"))

    assert len(rows) == 2
    assert rows[0]["weight"] == "90.0"
    assert rows[1]["datauuid"] == "f631923e-bc08-404a-8d0c-9468aa4dee2b"


def test_read_samsung_csv_strips_bom_from_first_header() -> None:
    """Les exports sont en utf-8-sig ; sans traitement, la première colonne
    s'appellerait '﻿start_time' et serait introuvable."""
    rows = list(read_samsung_csv(FIXTURES / "weight_sample.csv"))

    assert "start_time" in rows[0]
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_parsers.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/__init__.py` et
`backend/app/ingestion/samsung/__init__.py` vides.

Créer `backend/app/ingestion/samsung/parsers.py` :

```python
"""Conversions bas niveau de l'export Samsung Health.

Ces fonctions ne connaissent rien du domaine : elles transforment des
chaînes brutes en valeurs Python, et renvoient None pour tout ce qui est
absent ou illisible.
"""

from __future__ import annotations

import calendar
import csv
import re
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

_DATETIME_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})")
_OFFSET_RE = re.compile(r"\AUTC([+-])(\d{2})(\d{2})\Z")
_FLOAT_RE = re.compile(r"\A[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\Z")
_INT_RE = re.compile(r"\A[-+]?\d+\Z")


def _clean(raw: object) -> str:
    return "" if raw is None else str(raw).strip()


def parse_float(raw: object) -> float | None:
    text = _clean(raw)
    if not _FLOAT_RE.match(text):
        return None
    return float(text)


def parse_int(raw: object) -> int | None:
    text = _clean(raw)
    if not _INT_RE.match(text):
        return None
    return int(text)


def parse_utc_offset(raw: object) -> timezone | None:
    match = _OFFSET_RE.match(_clean(raw))
    if match is None:
        return None
    sign, hours, minutes = match.groups()
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-delta if sign == "-" else delta)


def parse_aware_datetime(raw_time: object, raw_offset: object) -> datetime | None:
    """Recombine l'heure locale naïve et son décalage.

    L'export stocke l'heure locale dans start_time et le décalage dans
    time_offset. Les traiter séparément fait perdre le fuseau ; les ignorer
    fait dériver toutes les agrégations par jour autour de minuit.
    """
    match = _DATETIME_RE.search(_clean(raw_time))
    if match is None:
        return None
    year, month, day, hour, minute, second = (int(g) for g in match.groups())
    if not 1 <= month <= 12:
        return None
    if not 1 <= day <= calendar.monthrange(year, month)[1]:
        return None
    if not (hour <= 23 and minute <= 59 and second <= 59):
        return None
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        tzinfo=parse_utc_offset(raw_offset) or timezone.utc,
    )


def parse_epoch_millis(raw: object) -> datetime | None:
    millis = parse_int(raw)
    if millis is None:
        return None
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc)


def read_samsung_csv(path: Path) -> Iterator[dict[str, str]]:
    """Itère les lignes d'un CSV Samsung.

    Le format place une ligne de métadonnées avant les en-têtes, et le
    fichier est encodé en utf-8-sig.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        next(handle, None)  # ligne de métadonnées
        yield from csv.DictReader(handle)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_parsers.py -v`
Expected: PASS, 30 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion backend/tests/unit/test_parsers.py backend/tests/fixtures
git commit -m "feat: add low-level parsers for samsung health export"
```

---

### Task 3: Résolution du sport

Cette tâche corrige le bug documenté en section 4.4 de la spec : 69 séances
de natation sont aujourd'hui classées en musculation.

**Files:**
- Create: `backend/app/ingestion/samsung/sports.py`
- Create: `backend/tests/unit/test_sports.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `resolve_sport(exercise_type: int | None, has_sets: bool) -> str`
  - `SPORT_BY_CODE: Mapping[int, str]`
  - `STRENGTH_CODES: frozenset[int]`
  - `CUSTOM_CODE: int`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/test_sports.py` :

```python
"""Tests de la résolution du sport depuis le code d'exercice Samsung."""

import pytest

from app.ingestion.samsung.sports import resolve_sport


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (1001, "Marche"),
        (1002, "Course à pied"),
        (11007, "Vélo"),
        (13001, "Randonnée"),
        (14001, "Natation"),
        (15004, "Rameur"),
        (10025, "Poids du corps"),
    ],
)
def test_known_codes_win_over_everything(code: int, expected: str) -> None:
    """Le code d'exercice fait foi, avec ou sans séries dans les données."""
    assert resolve_sport(code, has_sets=False) == expected
    assert resolve_sport(code, has_sets=True) == expected


def test_swimming_with_sets_stays_swimming() -> None:
    """Verrou de non-régression du bug corrigé.

    69 séances réelles portent le code 14001 tout en ayant des reps dans
    subset_data. L'ancienne heuristique testait les reps en premier et les
    classait en Musculation, soit 21 % des séances de natation perdues pour
    l'analyse natation et injectées dans les stats de musculation.
    """
    assert resolve_sport(14001, has_sets=True) == "Natation"


@pytest.mark.parametrize(
    "code",
    [10004, 10005, 10011, 10013, 10019, 10020, 10022, 10023, 10024, 10026, 10027],
)
def test_strength_codes_map_to_musculation(code: int) -> None:
    assert resolve_sport(code, has_sets=True) == "Musculation"
    assert resolve_sport(code, has_sets=False) == "Musculation"


def test_custom_code_with_sets_is_musculation() -> None:
    """Le code 0 désigne une activité personnalisée : seul cas où la
    présence de séries tranche. 487 séances réelles sont dans ce cas."""
    assert resolve_sport(0, has_sets=True) == "Musculation"


def test_custom_code_without_sets_is_walking() -> None:
    """439 séances réelles. On conserve Marche pour ne pas casser la
    continuité des statistiques historiques."""
    assert resolve_sport(0, has_sets=False) == "Marche"


def test_unknown_code_is_labelled_not_dropped() -> None:
    """L'application Streamlit filtrait silencieusement les codes inconnus."""
    assert resolve_sport(99999, has_sets=False) == "Type 99999"


def test_missing_code_is_unknown() -> None:
    assert resolve_sport(None, has_sets=False) == "Inconnu"
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_sports.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.sports'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/samsung/sports.py` :

```python
"""Résolution du sport à partir du code d'exercice Samsung.

Ordre de résolution, cf. spec section 4.4. Le code fait foi ; la présence de
séries ne tranche que pour le code 0, seul code réellement ambigu.
"""

from __future__ import annotations

from types import MappingProxyType

CUSTOM_CODE = 0

SPORT_BY_CODE = MappingProxyType(
    {
        1001: "Marche",
        1002: "Course à pied",
        11007: "Vélo",
        13001: "Randonnée",
        14001: "Natation",
        15004: "Rameur",
        10025: "Poids du corps",
    }
)

STRENGTH_CODES = frozenset(
    {10004, 10005, 10011, 10013, 10019, 10020, 10022, 10023, 10024, 10026, 10027}
)

MUSCULATION = "Musculation"
WALKING = "Marche"
UNKNOWN = "Inconnu"


def resolve_sport(exercise_type: int | None, *, has_sets: bool) -> str:
    if exercise_type is None:
        return UNKNOWN
    known = SPORT_BY_CODE.get(exercise_type)
    if known is not None:
        return known
    if exercise_type in STRENGTH_CODES:
        return MUSCULATION
    if exercise_type == CUSTOM_CODE:
        return MUSCULATION if has_sets else WALKING
    return f"Type {exercise_type}"
```

Note : `has_sets` est un argument nommé obligatoire. Les tests l'appellent
déjà ainsi ; un booléen positionnel à un appel de résolution serait
illisible.

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_sports.py -v`
Expected: PASS, 23 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/sports.py backend/tests/unit/test_sports.py
git commit -m "fix: resolve sport from exercise code before set heuristic"
```

---

### Task 4: Modèles SQLAlchemy et migration initiale

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/body.py`
- Create: `backend/app/models/nutrition.py`
- Create: `backend/app/models/phase.py`
- Create: `backend/app/models/workout.py`
- Create: `backend/app/models/photo.py`
- Create: `backend/app/models/ingestion.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/` (répertoire)
- Create: `backend/tests/unit/test_models_metadata.py`

**Interfaces:**
- Consumes: `app.config.settings` (tâche 1).
- Produces: `app.models.base.Base` avec `Base.metadata` peuplé ;
  les classes `BodyMeasurement`, `NutritionEntry`, `Phase`, `PhaseKind`,
  `Workout`, `WorkoutSample`, `WorkoutLocation`, `SwimLength`,
  `StrengthSet`, `WorkoutExtra`, `Photo`, `IngestionRun`,
  `IngestionStatus` ; `app.db.engine`, `app.db.session_factory`.

Choix de type assumé : les grandeurs physiques sont en `Double` et non en
`Numeric`. `Numeric` renvoie des `Decimal`, qui obligeraient toute la couche
analytique à convertir avant chaque calcul, pour une précision dont un suivi
corporel personnel n'a aucun besoin.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_models_metadata.py` :

```python
"""Vérifie la forme du schéma sans avoir besoin d'une base de données."""

from app.models.base import Base

EXPECTED_TABLES = {
    "body_measurement",
    "nutrition_entry",
    "phase",
    "workout",
    "workout_sample",
    "workout_location",
    "swim_length",
    "strength_set",
    "workout_extra",
    "photo",
    "ingestion_run",
}


def test_all_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_fact_tables_have_unique_source_uuid() -> None:
    """L'idempotence du ré-import repose entièrement sur cette contrainte."""
    for name in ("body_measurement", "nutrition_entry", "workout"):
        column = Base.metadata.tables[name].c["source_uuid"]
        assert column.unique is True
        assert column.nullable is False


def test_timestamps_are_timezone_aware() -> None:
    """Un TIMESTAMP sans fuseau ferait dériver les agrégations par jour."""
    checks = [
        ("body_measurement", "measured_at"),
        ("nutrition_entry", "consumed_at"),
        ("workout", "started_at"),
        ("workout_sample", "at"),
        ("workout_location", "at"),
    ]
    for table, column in checks:
        assert Base.metadata.tables[table].c[column].type.timezone is True


def test_child_tables_cascade_from_workout() -> None:
    """Réingérer une séance doit pouvoir remplacer ses séries filles."""
    for name in (
        "workout_sample",
        "workout_location",
        "swim_length",
        "strength_set",
        "workout_extra",
    ):
        fk = next(iter(Base.metadata.tables[name].c["workout_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"


def test_photo_is_unique_per_date_and_tag() -> None:
    constraints = {
        tuple(sorted(c.name for c in uc.columns))
        for uc in Base.metadata.tables["photo"].constraints
        if hasattr(uc, "columns") and len(uc.columns) == 2
    }
    assert ("tag", "taken_on") in constraints
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_models_metadata.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Écrire les modèles**

Créer `backend/app/models/base.py` :

```python
"""Base declarative et mixin d'horodatage technique."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Horodatage technique, distinct des dates métier."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Créer `backend/app/models/body.py` :

```python
"""Mesures de composition corporelle."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BodyMeasurement(Base, TimestampMixin):
    __tablename__ = "body_measurement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    weight_kg: Mapped[float | None] = mapped_column(Double)
    body_fat_pct: Mapped[float | None] = mapped_column(Double)
    body_fat_mass_kg: Mapped[float | None] = mapped_column(Double)
    skeletal_muscle_mass_kg: Mapped[float | None] = mapped_column(Double)
    skeletal_muscle_pct: Mapped[float | None] = mapped_column(Double)
    fat_free_mass_kg: Mapped[float | None] = mapped_column(Double)
    fat_free_pct: Mapped[float | None] = mapped_column(Double)
    total_body_water_kg: Mapped[float | None] = mapped_column(Double)
    basal_metabolic_rate_kcal: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Double)
```

Créer `backend/app/models/nutrition.py` :

```python
"""Entrées du journal alimentaire."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NutritionEntry(Base, TimestampMixin):
    __tablename__ = "nutrition_entry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    meal_type: Mapped[int | None] = mapped_column(SmallInteger, index=True)
    food_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    amount: Mapped[float | None] = mapped_column(Double)
    unit_code: Mapped[int | None] = mapped_column(SmallInteger)
    calories: Mapped[float | None] = mapped_column(Double)
```

Créer `backend/app/models/phase.py` :

```python
"""Phases de suivi et leurs objectifs."""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import CheckConstraint, Date, Double, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PhaseKind(enum.StrEnum):
    FREE = "free"
    BULK = "bulk"
    CUT = "cut"
    MAINTAIN = "maintain"


class Phase(Base, TimestampMixin):
    """Une période de suivi.

    ends_on est inclusif. Aucune contrainte d'exclusion de chevauchement :
    les données réelles contiennent un chevauchement d'un jour entre une
    sèche et le maintien qui la suit.
    """

    __tablename__ = "phase"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="ck_phase_dates_ordered"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[PhaseKind] = mapped_column(
        Enum(PhaseKind, name="phase_kind", native_enum=True), nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    weight_target_kg: Mapped[float | None] = mapped_column(Double)
    body_fat_target_pct: Mapped[float | None] = mapped_column(Double)
    skeletal_muscle_target_kg: Mapped[float | None] = mapped_column(Double)
    daily_calories_target: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
```

Créer `backend/app/models/workout.py` :

```python
"""Séances et leurs séries filles.

Les cinq tables filles vivent ici avec Workout : leur schéma est une seule
décision et elles ne changent jamais séparément.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Workout(Base, TimestampMixin):
    __tablename__ = "workout"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)

    sport_type: Mapped[int | None] = mapped_column(Integer, index=True)
    sport: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    distance_m: Mapped[float | None] = mapped_column(Double)
    calories_kcal: Mapped[float | None] = mapped_column(Double)
    mean_heart_rate: Mapped[float | None] = mapped_column(Double)
    max_heart_rate: Mapped[float | None] = mapped_column(Double)
    min_heart_rate: Mapped[float | None] = mapped_column(Double)
    mean_speed_mps: Mapped[float | None] = mapped_column(Double)
    max_speed_mps: Mapped[float | None] = mapped_column(Double)
    mean_cadence: Mapped[float | None] = mapped_column(Double)
    max_cadence: Mapped[float | None] = mapped_column(Double)
    min_altitude_m: Mapped[float | None] = mapped_column(Double)
    max_altitude_m: Mapped[float | None] = mapped_column(Double)
    altitude_gain_m: Mapped[float | None] = mapped_column(Double)
    altitude_loss_m: Mapped[float | None] = mapped_column(Double)
    start_latitude: Mapped[float | None] = mapped_column(Double)
    start_longitude: Mapped[float | None] = mapped_column(Double)

    # Conservés pour fidélité à la source, mais vides dans les données
    # réelles : aucune vue ne doit les exposer (cf. spec 4.4).
    vo2_max: Mapped[float | None] = mapped_column(Double)
    sweat_loss_ml: Mapped[float | None] = mapped_column(Double)

    pool_length_m: Mapped[float | None] = mapped_column(Double)
    max_hr_custom: Mapped[int | None] = mapped_column(SmallInteger)
    max_hr_auto: Mapped[int | None] = mapped_column(SmallInteger)
    hr_aerobic_threshold: Mapped[int | None] = mapped_column(SmallInteger)
    hr_anaerobic_threshold: Mapped[int | None] = mapped_column(SmallInteger)
    resting_hr: Mapped[int | None] = mapped_column(SmallInteger)

    # Évitent une sous-requête à l'affichage des listes de séances.
    has_samples: Mapped[bool] = mapped_column(nullable=False, default=False)
    has_locations: Mapped[bool] = mapped_column(nullable=False, default=False)
    has_swim_lengths: Mapped[bool] = mapped_column(nullable=False, default=False)
    has_strength_sets: Mapped[bool] = mapped_column(nullable=False, default=False)


class WorkoutSample(Base):
    """Échantillon intra-séance. ~2,8 M lignes sur les données réelles."""

    __tablename__ = "workout_sample"
    __table_args__ = (
        Index("ix_workout_sample_at_brin", "at", postgresql_using="brin"),
    )

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    elapsed_ms: Mapped[int | None] = mapped_column(BigInteger)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger)
    speed_mps: Mapped[float | None] = mapped_column(Double)
    distance_m: Mapped[float | None] = mapped_column(Double)
    calories_kcal: Mapped[float | None] = mapped_column(Double)
    cadence: Mapped[int | None] = mapped_column(SmallInteger)
    segment: Mapped[int | None] = mapped_column(SmallInteger)


class WorkoutLocation(Base):
    """Point GPS. ~590 k lignes sur les données réelles."""

    __tablename__ = "workout_location"
    __table_args__ = (
        Index("ix_workout_location_at_brin", "at", postgresql_using="brin"),
    )

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    altitude_m: Mapped[float | None] = mapped_column(Double)
    accuracy_m: Mapped[float | None] = mapped_column(Double)


class SwimLength(Base):
    """Une longueur de bassin. Permet le SWOLF et l'analyse par nage."""

    __tablename__ = "swim_length"

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    idx: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer)
    stroke_count: Mapped[int | None] = mapped_column(SmallInteger)
    stroke_type: Mapped[str | None] = mapped_column(Text, index=True)
    resting_time_ms: Mapped[int | None] = mapped_column(Integer)


class StrengthSet(Base):
    """Une série de musculation, issue de subset_data.

    1 531 séances réelles en portent ; l'application Streamlit s'en servait
    seulement pour deviner le sport puis jetait les valeurs.
    """

    __tablename__ = "strength_set"

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    idx: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    duration_s: Mapped[float | None] = mapped_column(Double)
    reps: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[float | None] = mapped_column(Double)
    weight_unit: Mapped[str | None] = mapped_column(Text)


class WorkoutExtra(Base):
    """Charges utiles annexes hétérogènes, conservées en JSONB.

    Les modéliser en colonnes serait du travail perdu pour 150 séances aux
    schémas disparates (métriques Myotest, notamment).
    """

    __tablename__ = "workout_extra"
    __table_args__ = (
        UniqueConstraint("workout_id", "kind", name="uq_workout_extra_kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
```

Créer `backend/app/models/photo.py` :

```python
"""Photos de suivi. La logique de stockage arrive au plan 3."""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Photo(Base, TimestampMixin):
    """Une photo par tag et par date.

    Reproduit la sémantique de l'arborescence actuelle ({date}/{tag}.jpg) et
    simplifie le front : un nouvel envoi remplace.
    """

    __tablename__ = "photo"
    __table_args__ = (UniqueConstraint("taken_on", "tag", name="uq_photo_date_tag"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    taken_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tag: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    content_type: Mapped[str | None] = mapped_column(Text)
```

Créer `backend/app/models/ingestion.py` :

```python
"""Traçabilité des ingestions."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IngestionStatus(enum.StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class IngestionRun(Base):
    __tablename__ = "ingestion_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="ingestion_status", native_enum=True),
        nullable=False,
        default=IngestionStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counts: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
```

Créer `backend/app/models/__init__.py` — il doit importer tous les modules
pour que `Base.metadata` soit peuplé quand Alembic n'importe que ce paquet :

```python
"""Import de tous les modèles pour peupler Base.metadata."""

from app.models.base import Base
from app.models.body import BodyMeasurement
from app.models.ingestion import IngestionRun, IngestionStatus
from app.models.nutrition import NutritionEntry
from app.models.phase import Phase, PhaseKind
from app.models.photo import Photo
from app.models.workout import (
    StrengthSet,
    SwimLength,
    Workout,
    WorkoutExtra,
    WorkoutLocation,
    WorkoutSample,
)

__all__ = [
    "Base",
    "BodyMeasurement",
    "IngestionRun",
    "IngestionStatus",
    "NutritionEntry",
    "Phase",
    "PhaseKind",
    "Photo",
    "StrengthSet",
    "SwimLength",
    "Workout",
    "WorkoutExtra",
    "WorkoutLocation",
    "WorkoutSample",
]
```

Le test importe `app.models.base` ; ajouter en tête de
`backend/tests/unit/test_models_metadata.py` un `import app.models  # noqa: F401`
juste après les imports existants n'est pas nécessaire si le test importe
`app.models` plutôt que `app.models.base`. Corriger le test pour importer
depuis `app.models` :

```python
from app.models import Base
```

Créer `backend/app/db.py` :

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
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_models_metadata.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Initialiser Alembic et générer la migration**

Run: `cd backend && uv run alembic init -t async migrations`

Modifier `backend/alembic.ini` pour retirer la ligne `sqlalchemy.url` (elle
sera fournie par la configuration) :

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
```

Remplacer le corps de `backend/migrations/env.py` par :

```python
"""Environnement Alembic, branché sur la configuration de l'application."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.engine import Connection
from sqlalchemy import pool

from app.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
```

Créer un `backend/.env` local (non versionné) :

```bash
cd backend && cat > .env <<'EOF'
BA_DATABASE_URL=postgresql+asyncpg://body:body-local-dev@localhost:5432/body_analysis
BA_MINIO_ACCESS_KEY=body
BA_MINIO_SECRET_KEY=body-local-dev-minio
EOF
```

Run: `cd backend && uv run alembic revision --autogenerate -m "initial schema"`
Expected: un fichier créé dans `migrations/versions/`

- [ ] **Step 6: Appliquer et vérifier le schéma en base**

Run: `cd backend && uv run alembic upgrade head`
Expected: `Running upgrade -> <hash>, initial schema`

Run: `docker compose exec db psql -U body -d body_analysis -c "\dt"`
Expected: les 11 tables plus `alembic_version`

Run: `docker compose exec db psql -U body -d body_analysis -c "\d workout_sample"`
Expected: clé primaire `(workout_id, at)` et un index `brin` sur `at`

- [ ] **Step 7: Commiter**

```bash
git add backend/app/models backend/app/db.py backend/alembic.ini backend/migrations backend/tests/unit/test_models_metadata.py
git commit -m "feat: add sqlalchemy models and initial alembic migration"
```

---

### Task 5: Dataclasses de domaine et mapping des mesures corporelles

**Files:**
- Create: `backend/app/ingestion/samsung/records.py`
- Create: `backend/app/ingestion/samsung/mapper.py`
- Create: `backend/tests/unit/test_mapper_body.py`

**Interfaces:**
- Consumes: `parse_aware_datetime`, `parse_float`, `parse_int` (tâche 2).
- Produces:
  - `records.BodyMeasurementRecord`, `records.NutritionEntryRecord`,
    `records.WorkoutRecord`, `records.SampleRecord`,
    `records.LocationRecord`, `records.SwimLengthRecord`,
    `records.StrengthSetRecord`, `records.ExtraRecord`,
    `records.WorkoutBundle`, `records.PhaseRecord`
  - `mapper.map_body_measurement(row: dict[str, str]) -> BodyMeasurementRecord | None`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_mapper_body.py` :

```python
"""Tests du mapping des mesures corporelles."""

from datetime import datetime, timedelta, timezone

from app.ingestion.samsung.mapper import map_body_measurement

FULL_ROW = {
    "datauuid": "f631923e-bc08-404a-8d0c-9468aa4dee2b",
    "start_time": "2026-08-31 06:29:10.346",
    "time_offset": "UTC+0200",
    "weight": "65.6",
    "body_fat": "10.8",
    "body_fat_mass": "7.0848002",
    "skeletal_muscle_mass": "37.7",
    "skeletal_muscle": "45.72513",
    "fat_free_mass": "57.272385",
    "fat_free": "84.10042",
    "total_body_water": "42.833126",
    "basal_metabolic_rate": "1633",
    "height": "180.0",
}

SPARSE_ROW = {
    "datauuid": "a04ec306-ed98-460e-853f-629b404d0757",
    "start_time": "2018-11-29 22:54:00.000",
    "time_offset": "UTC+0100",
    "weight": "90.0",
    "body_fat": "",
    "body_fat_mass": "",
    "skeletal_muscle_mass": "",
    "skeletal_muscle": "",
    "fat_free_mass": "",
    "fat_free": "",
    "total_body_water": "",
    "basal_metabolic_rate": "",
    "height": "180.0",
}


def test_maps_every_metric() -> None:
    record = map_body_measurement(FULL_ROW)

    assert record is not None
    assert record.source_uuid == "f631923e-bc08-404a-8d0c-9468aa4dee2b"
    assert record.measured_at == datetime(
        2026, 8, 31, 6, 29, 10, tzinfo=timezone(timedelta(hours=2))
    )
    assert record.weight_kg == 65.6
    assert record.body_fat_pct == 10.8
    assert record.body_fat_mass_kg == 7.0848002
    assert record.skeletal_muscle_mass_kg == 37.7
    assert record.skeletal_muscle_pct == 45.72513
    assert record.fat_free_mass_kg == 57.272385
    assert record.fat_free_pct == 84.10042
    assert record.total_body_water_kg == 42.833126
    assert record.basal_metabolic_rate_kcal == 1633
    assert record.height_cm == 180.0


def test_missing_metrics_stay_none() -> None:
    """260 mesures réelles antérieures à 2024 n'ont ni masse grasse ni
    muscle. Les remplacer par 0 ferait plonger les courbes."""
    record = map_body_measurement(SPARSE_ROW)

    assert record is not None
    assert record.weight_kg == 90.0
    assert record.body_fat_pct is None
    assert record.skeletal_muscle_mass_kg is None
    assert record.basal_metabolic_rate_kcal is None


def test_row_without_uuid_is_rejected() -> None:
    """Sans source_uuid, l'idempotence du ré-import est impossible."""
    assert map_body_measurement({**FULL_ROW, "datauuid": ""}) is None


def test_row_with_unreadable_date_is_rejected() -> None:
    assert map_body_measurement({**FULL_ROW, "start_time": "n/a"}) is None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_mapper_body.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.mapper'`

- [ ] **Step 3: Écrire les dataclasses et le mapper**

Créer `backend/app/ingestion/samsung/records.py` :

```python
"""Dataclasses du domaine d'ingestion.

Ces types sont la frontière entre le mapper, qui connaît le format Samsung,
et le loader, qui connaît la base. Aucun des deux n'a besoin de l'autre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BodyMeasurementRecord:
    source_uuid: str
    measured_at: datetime
    weight_kg: float | None = None
    body_fat_pct: float | None = None
    body_fat_mass_kg: float | None = None
    skeletal_muscle_mass_kg: float | None = None
    skeletal_muscle_pct: float | None = None
    fat_free_mass_kg: float | None = None
    fat_free_pct: float | None = None
    total_body_water_kg: float | None = None
    basal_metabolic_rate_kcal: int | None = None
    height_cm: float | None = None


@dataclass(frozen=True, slots=True)
class NutritionEntryRecord:
    source_uuid: str
    consumed_at: datetime
    food_name: str = ""
    meal_type: int | None = None
    amount: float | None = None
    unit_code: int | None = None
    calories: float | None = None


@dataclass(frozen=True, slots=True)
class SampleRecord:
    at: datetime
    elapsed_ms: int | None = None
    heart_rate: int | None = None
    speed_mps: float | None = None
    distance_m: float | None = None
    calories_kcal: float | None = None
    cadence: int | None = None
    segment: int | None = None


@dataclass(frozen=True, slots=True)
class LocationRecord:
    at: datetime
    latitude: float
    longitude: float
    altitude_m: float | None = None
    accuracy_m: float | None = None


@dataclass(frozen=True, slots=True)
class SwimLengthRecord:
    idx: int
    duration_ms: int | None = None
    stroke_count: int | None = None
    stroke_type: str | None = None
    resting_time_ms: int | None = None


@dataclass(frozen=True, slots=True)
class StrengthSetRecord:
    idx: int
    duration_s: float | None = None
    reps: int | None = None
    weight_kg: float | None = None
    weight_unit: str | None = None


@dataclass(frozen=True, slots=True)
class ExtraRecord:
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WorkoutRecord:
    source_uuid: str
    started_at: datetime
    sport: str
    sport_type: int | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    distance_m: float | None = None
    calories_kcal: float | None = None
    mean_heart_rate: float | None = None
    max_heart_rate: float | None = None
    min_heart_rate: float | None = None
    mean_speed_mps: float | None = None
    max_speed_mps: float | None = None
    mean_cadence: float | None = None
    max_cadence: float | None = None
    min_altitude_m: float | None = None
    max_altitude_m: float | None = None
    altitude_gain_m: float | None = None
    altitude_loss_m: float | None = None
    start_latitude: float | None = None
    start_longitude: float | None = None
    vo2_max: float | None = None
    sweat_loss_ml: float | None = None
    pool_length_m: float | None = None
    max_hr_custom: int | None = None
    max_hr_auto: int | None = None
    hr_aerobic_threshold: int | None = None
    hr_anaerobic_threshold: int | None = None
    resting_hr: int | None = None


@dataclass(frozen=True, slots=True)
class WorkoutBundle:
    """Une séance et tout ce qui en dépend."""

    workout: WorkoutRecord
    samples: list[SampleRecord] = field(default_factory=list)
    locations: list[LocationRecord] = field(default_factory=list)
    swim_lengths: list[SwimLengthRecord] = field(default_factory=list)
    strength_sets: list[StrengthSetRecord] = field(default_factory=list)
    extras: list[ExtraRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PhaseRecord:
    name: str
    kind: str
    starts_on: date
    ends_on: date
    weight_target_kg: float | None = None
    body_fat_target_pct: float | None = None
    skeletal_muscle_target_kg: float | None = None
    daily_calories_target: int | None = None
```

Créer `backend/app/ingestion/samsung/mapper.py` :

```python
"""Transformation des lignes brutes de l'export en dataclasses de domaine.

Ce module est le seul à connaître les noms de colonnes de Samsung Health.
"""

from __future__ import annotations

from app.ingestion.samsung.parsers import (
    parse_aware_datetime,
    parse_float,
    parse_int,
)
from app.ingestion.samsung.records import BodyMeasurementRecord


def map_body_measurement(row: dict[str, str]) -> BodyMeasurementRecord | None:
    """Renvoie None si la ligne n'est pas exploitable.

    Une ligne sans identifiant source ne peut pas être réingérée sans
    doublon ; une ligne sans date n'est situable sur aucune courbe.
    """
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    measured_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if measured_at is None:
        return None
    return BodyMeasurementRecord(
        source_uuid=source_uuid,
        measured_at=measured_at,
        weight_kg=parse_float(row.get("weight")),
        body_fat_pct=parse_float(row.get("body_fat")),
        body_fat_mass_kg=parse_float(row.get("body_fat_mass")),
        skeletal_muscle_mass_kg=parse_float(row.get("skeletal_muscle_mass")),
        skeletal_muscle_pct=parse_float(row.get("skeletal_muscle")),
        fat_free_mass_kg=parse_float(row.get("fat_free_mass")),
        fat_free_pct=parse_float(row.get("fat_free")),
        total_body_water_kg=parse_float(row.get("total_body_water")),
        basal_metabolic_rate_kcal=parse_int(row.get("basal_metabolic_rate")),
        height_cm=parse_float(row.get("height")),
    )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_mapper_body.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/mapper.py backend/tests/unit/test_mapper_body.py
git commit -m "feat: map samsung weight rows to body measurement records"
```

---

### Task 6: Mapping du journal alimentaire

**Files:**
- Modify: `backend/app/ingestion/samsung/mapper.py`
- Create: `backend/tests/unit/test_mapper_nutrition.py`

**Interfaces:**
- Consumes: `parse_aware_datetime`, `parse_float`, `parse_int` (tâche 2) ;
  `NutritionEntryRecord` (tâche 5).
- Produces: `mapper.map_nutrition_entry(row: dict[str, str]) -> NutritionEntryRecord | None`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_mapper_nutrition.py` :

```python
"""Tests du mapping du journal alimentaire."""

from datetime import datetime, timedelta, timezone

from app.ingestion.samsung.mapper import map_nutrition_entry

ROW = {
    "datauuid": "18b7fde3-ec6e-40d7-b9c4-a55bdcbedb10",
    "start_time": "2024-08-14 11:56:40.973",
    "time_offset": "UTC+0200",
    "name": "Gazpacho(Alvalle)",
    "meal_type": "100002",
    "amount": "333.0",
    "unit": "120005",
    "calorie": "134.865",
}


def test_maps_all_fields() -> None:
    record = map_nutrition_entry(ROW)

    assert record is not None
    assert record.source_uuid == "18b7fde3-ec6e-40d7-b9c4-a55bdcbedb10"
    assert record.consumed_at == datetime(
        2024, 8, 14, 11, 56, 40, tzinfo=timezone(timedelta(hours=2))
    )
    assert record.food_name == "Gazpacho(Alvalle)"
    assert record.meal_type == 100002
    assert record.amount == 333.0
    assert record.unit_code == 120005
    assert record.calories == 134.865


def test_food_name_is_stripped_and_defaults_to_empty() -> None:
    assert map_nutrition_entry({**ROW, "name": "  Oeuf  "}).food_name == "Oeuf"
    assert map_nutrition_entry({**ROW, "name": ""}).food_name == ""


def test_negative_unit_code_is_kept() -> None:
    """33 entrées réelles portent l'unité -1. C'est une valeur, pas une
    absence : on la conserve telle quelle plutôt que de la masquer."""
    assert map_nutrition_entry({**ROW, "unit": "-1"}).unit_code == -1


def test_missing_calories_stay_none() -> None:
    assert map_nutrition_entry({**ROW, "calorie": ""}).calories is None


def test_row_without_uuid_or_date_is_rejected() -> None:
    assert map_nutrition_entry({**ROW, "datauuid": ""}) is None
    assert map_nutrition_entry({**ROW, "start_time": ""}) is None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_mapper_nutrition.py -v`
Expected: FAIL avec `ImportError: cannot import name 'map_nutrition_entry'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/mapper.py` — compléter l'import de
`records` puis ajouter la fonction :

```python
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
)


def map_nutrition_entry(row: dict[str, str]) -> NutritionEntryRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    consumed_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if consumed_at is None:
        return None
    return NutritionEntryRecord(
        source_uuid=source_uuid,
        consumed_at=consumed_at,
        food_name=(row.get("name") or "").strip(),
        meal_type=parse_int(row.get("meal_type")),
        amount=parse_float(row.get("amount")),
        unit_code=parse_int(row.get("unit")),
        calories=parse_float(row.get("calorie")),
    )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_mapper_nutrition.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/mapper.py backend/tests/unit/test_mapper_nutrition.py
git commit -m "feat: map samsung food intake rows to nutrition records"
```

---

### Task 7: Mapping des séances et des séries de musculation

**Files:**
- Modify: `backend/app/ingestion/samsung/mapper.py`
- Create: `backend/tests/unit/test_mapper_workout.py`

**Interfaces:**
- Consumes: `parse_aware_datetime`, `parse_float`, `parse_int` (tâche 2) ;
  `resolve_sport` (tâche 3) ; `WorkoutRecord`, `StrengthSetRecord`
  (tâche 5).
- Produces:
  - `mapper.has_sets(row: dict[str, str]) -> bool`
  - `mapper.map_workout(row: dict[str, str]) -> WorkoutRecord | None`
  - `mapper.map_strength_sets(row: dict[str, str], sport: str) -> list[StrengthSetRecord]`
  - `mapper.JsonReferences` (dataclass : `live_data`, `location_data`,
    `additional`, `sensing_status`, chacun `str | None`)
  - `mapper.map_json_references(row: dict[str, str]) -> JsonReferences`

Le préfixe `com.samsung.health.exercise.` s'applique à la plupart des
colonnes, mais pas à `start_latitude`, `start_longitude`, `subset_data` ni
`sensing_status`. Le code doit distinguer les deux familles.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_mapper_workout.py` :

```python
"""Tests du mapping des séances."""

import json
from datetime import datetime, timedelta, timezone

from app.ingestion.samsung.mapper import (
    has_sets,
    map_json_references,
    map_strength_sets,
    map_workout,
)

P = "com.samsung.health.exercise."

STRENGTH_SUBSET = json.dumps(
    [
        {"duration": 42, "reps": 10, "weight": 0.0, "weight_unit": "kg"},
        {"duration": 35, "reps": 10, "weight": 20.5, "weight_unit": "kg"},
    ]
)

SWIM_SUBSET = json.dumps(
    [
        {
            "duration": 1800,
            "distance": 0,
            "reps": 20,
            "extra_data": '{"poolLength":1,"poolLengthUnit":"m"}',
        }
    ]
)

RUN_ROW = {
    f"{P}datauuid": "185e928e-af99-46fd-9dad-35f114d5b32d",
    f"{P}start_time": "2026-02-05 19:02:05.000",
    f"{P}end_time": "2026-02-05 19:13:24.000",
    f"{P}time_offset": "UTC+0100",
    f"{P}duration": "678496",
    f"{P}exercise_type": "1002",
    f"{P}distance": "975.32",
    f"{P}calorie": "37.27",
    f"{P}mean_heart_rate": "148.5",
    f"{P}max_heart_rate": "171",
    f"{P}min_heart_rate": "96",
    f"{P}mean_speed": "1.4374734",
    f"{P}max_speed": "1.75",
    f"{P}mean_cadence": "160",
    f"{P}max_cadence": "178",
    f"{P}min_altitude": "12.0",
    f"{P}max_altitude": "48.5",
    f"{P}altitude_gain": "36.5",
    f"{P}altitude_loss": "30.0",
    f"{P}vo2_max": "",
    f"{P}sweat_loss": "",
    f"{P}live_data": "185e928e-af99-46fd-9dad-35f114d5b32d.com.samsung.health.exercise.live_data.json",
    f"{P}location_data": "",
    f"{P}additional": "",
    "start_latitude": "44.8010456",
    "start_longitude": "-0.5758588",
    "subset_data": "",
    "sensing_status": "",
}


def test_maps_run_summary() -> None:
    record = map_workout(RUN_ROW)

    assert record is not None
    assert record.source_uuid == "185e928e-af99-46fd-9dad-35f114d5b32d"
    assert record.started_at == datetime(
        2026, 2, 5, 19, 2, 5, tzinfo=timezone(timedelta(hours=1))
    )
    assert record.ended_at == datetime(
        2026, 2, 5, 19, 13, 24, tzinfo=timezone(timedelta(hours=1))
    )
    assert record.duration_ms == 678496
    assert record.sport_type == 1002
    assert record.sport == "Course à pied"
    assert record.distance_m == 975.32
    assert record.calories_kcal == 37.27
    assert record.mean_heart_rate == 148.5
    assert record.max_heart_rate == 171.0
    assert record.min_heart_rate == 96.0
    assert record.mean_speed_mps == 1.4374734
    assert record.altitude_gain_m == 36.5
    assert record.start_latitude == 44.8010456
    assert record.start_longitude == -0.5758588


def test_empty_vo2_and_sweat_stay_none() -> None:
    """Colonnes présentes mais vides dans les données réelles."""
    record = map_workout(RUN_ROW)

    assert record.vo2_max is None
    assert record.sweat_loss_ml is None


def test_swimming_with_sets_is_still_swimming() -> None:
    """Verrou de non-régression du bug corrigé en tâche 3, au niveau du
    mapper cette fois : la séance porte des reps ET le code natation."""
    row = {**RUN_ROW, f"{P}exercise_type": "14001", "subset_data": SWIM_SUBSET}

    assert map_workout(row).sport == "Natation"


def test_custom_code_uses_sets_to_disambiguate() -> None:
    with_sets = {**RUN_ROW, f"{P}exercise_type": "0", "subset_data": STRENGTH_SUBSET}
    without_sets = {**RUN_ROW, f"{P}exercise_type": "0", "subset_data": ""}

    assert map_workout(with_sets).sport == "Musculation"
    assert map_workout(without_sets).sport == "Marche"


def test_has_sets_detects_reps() -> None:
    assert has_sets({"subset_data": STRENGTH_SUBSET}) is True
    assert has_sets({"subset_data": ""}) is False
    assert has_sets({"subset_data": "pas du json"}) is False
    assert has_sets({"subset_data": "[]"}) is False
    assert has_sets({"subset_data": '[{"duration": 42}]'}) is False


def test_maps_strength_sets_for_strength_sports() -> None:
    sets = map_strength_sets({"subset_data": STRENGTH_SUBSET}, "Musculation")

    assert len(sets) == 2
    assert sets[0].idx == 0
    assert sets[0].duration_s == 42.0
    assert sets[0].reps == 10
    assert sets[0].weight_kg == 0.0
    assert sets[0].weight_unit == "kg"
    assert sets[1].idx == 1
    assert sets[1].weight_kg == 20.5


def test_does_not_map_swim_subset_as_strength_sets() -> None:
    """Les reps d'une séance de natation ne sont pas des séries de charge ;
    les stocker comme telles polluerait le volume de musculation."""
    assert map_strength_sets({"subset_data": SWIM_SUBSET}, "Natation") == []


def test_maps_json_references() -> None:
    refs = map_json_references(RUN_ROW)

    assert refs.live_data == (
        "185e928e-af99-46fd-9dad-35f114d5b32d"
        ".com.samsung.health.exercise.live_data.json"
    )
    assert refs.location_data is None
    assert refs.additional is None
    assert refs.sensing_status is None


def test_row_without_uuid_or_date_is_rejected() -> None:
    assert map_workout({**RUN_ROW, f"{P}datauuid": ""}) is None
    assert map_workout({**RUN_ROW, f"{P}start_time": ""}) is None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_mapper_workout.py -v`
Expected: FAIL avec `ImportError: cannot import name 'has_sets'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/mapper.py` :

```python
import json
from dataclasses import dataclass

from app.ingestion.samsung.sports import resolve_sport
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
    StrengthSetRecord,
    WorkoutRecord,
)

EXERCISE_PREFIX = "com.samsung.health.exercise."

# Sports dont subset_data porte de vraies séries de charge. Les séances de
# natation ont aussi des reps, mais elles comptent des longueurs.
STRENGTH_SPORTS = frozenset({"Musculation", "Poids du corps"})


@dataclass(frozen=True, slots=True)
class JsonReferences:
    """Noms des fichiers JSON annexes référencés par une ligne de séance."""

    live_data: str | None = None
    location_data: str | None = None
    additional: str | None = None
    sensing_status: str | None = None


def _exercise(row: dict[str, str], field: str) -> str | None:
    return row.get(f"{EXERCISE_PREFIX}{field}")


def _subset_items(row: dict[str, str]) -> list[dict[str, object]]:
    raw = (row.get("subset_data") or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def has_sets(row: dict[str, str]) -> bool:
    return any("reps" in item for item in _subset_items(row))


def map_workout(row: dict[str, str]) -> WorkoutRecord | None:
    source_uuid = (_exercise(row, "datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = _exercise(row, "time_offset")
    started_at = parse_aware_datetime(_exercise(row, "start_time"), offset)
    if started_at is None:
        return None
    sport_type = parse_int(_exercise(row, "exercise_type"))
    return WorkoutRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(_exercise(row, "end_time"), offset),
        duration_ms=parse_int(_exercise(row, "duration")),
        sport_type=sport_type,
        sport=resolve_sport(sport_type, has_sets=has_sets(row)),
        distance_m=parse_float(_exercise(row, "distance")),
        calories_kcal=parse_float(_exercise(row, "calorie")),
        mean_heart_rate=parse_float(_exercise(row, "mean_heart_rate")),
        max_heart_rate=parse_float(_exercise(row, "max_heart_rate")),
        min_heart_rate=parse_float(_exercise(row, "min_heart_rate")),
        mean_speed_mps=parse_float(_exercise(row, "mean_speed")),
        max_speed_mps=parse_float(_exercise(row, "max_speed")),
        mean_cadence=parse_float(_exercise(row, "mean_cadence")),
        max_cadence=parse_float(_exercise(row, "max_cadence")),
        min_altitude_m=parse_float(_exercise(row, "min_altitude")),
        max_altitude_m=parse_float(_exercise(row, "max_altitude")),
        altitude_gain_m=parse_float(_exercise(row, "altitude_gain")),
        altitude_loss_m=parse_float(_exercise(row, "altitude_loss")),
        start_latitude=parse_float(row.get("start_latitude")),
        start_longitude=parse_float(row.get("start_longitude")),
        vo2_max=parse_float(_exercise(row, "vo2_max")),
        sweat_loss_ml=parse_float(_exercise(row, "sweat_loss")),
    )


def map_strength_sets(row: dict[str, str], sport: str) -> list[StrengthSetRecord]:
    if sport not in STRENGTH_SPORTS:
        return []
    return [
        StrengthSetRecord(
            idx=index,
            duration_s=parse_float(item.get("duration")),
            reps=parse_int(item.get("reps")),
            weight_kg=parse_float(item.get("weight")),
            weight_unit=(str(item["weight_unit"]) if item.get("weight_unit") else None),
        )
        for index, item in enumerate(_subset_items(row))
        if "reps" in item
    ]


def _reference(raw: str | None) -> str | None:
    text = (raw or "").strip()
    return text or None


def map_json_references(row: dict[str, str]) -> JsonReferences:
    return JsonReferences(
        live_data=_reference(_exercise(row, "live_data")),
        location_data=_reference(_exercise(row, "location_data")),
        additional=_reference(_exercise(row, "additional")),
        sensing_status=_reference(row.get("sensing_status")),
    )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_mapper_workout.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/mapper.py backend/tests/unit/test_mapper_workout.py
git commit -m "feat: map samsung exercise rows and strength sets"
```

---

### Task 8: Lecture des fichiers JSON annexes

**Files:**
- Create: `backend/app/ingestion/samsung/json_files.py`
- Create: `backend/tests/unit/test_json_files.py`
- Create: `backend/tests/fixtures/samsung/exercise/1/11111111-1111-1111-1111-111111111111.com.samsung.health.exercise.live_data.json`
- Create: `backend/tests/fixtures/samsung/exercise/2/22222222-2222-2222-2222-222222222222.com.samsung.health.exercise.location_data.json`
- Create: `backend/tests/fixtures/samsung/exercise/3/33333333-3333-3333-3333-333333333333.com.samsung.health.exercise.additional.json`
- Create: `backend/tests/fixtures/samsung/exercise/4/44444444-4444-4444-4444-444444444444.sensing_status.json`

**Interfaces:**
- Consumes: `parse_epoch_millis`, `parse_float`, `parse_int` (tâche 2) ;
  `SampleRecord`, `LocationRecord`, `SwimLengthRecord`, `ExtraRecord`
  (tâche 5).
- Produces:
  - `resolve_json_path(exercise_dir: Path, filename: str | None) -> Path | None`
  - `load_json(path: Path) -> object | None`
  - `map_samples(payload: object) -> list[SampleRecord]`
  - `map_locations(payload: object) -> list[LocationRecord]`
  - `map_swim_lengths(payload: object) -> list[SwimLengthRecord]`
  - `map_pool_length(payload: object) -> float | None`
  - `HeartRateThresholds` (dataclass : `max_hr_custom`, `max_hr_auto`,
    `aerobic`, `anaerobic`, `resting`, tous `int | None`)
  - `map_heart_rate_thresholds(payload: object) -> HeartRateThresholds`

L'export répartit les fichiers dans des sous-répertoires nommés par le
premier caractère du nom de fichier : `com.samsung.shealth.exercise/1/1a2b...json`.

- [ ] **Step 1: Écrire les fixtures et le test qui échoue**

Créer les quatre fixtures.

`.../1/11111111-1111-1111-1111-111111111111.com.samsung.health.exercise.live_data.json` :

```json
[
  {"start_time": 1644085620000, "calorie": 5.65, "distance": 87.73, "speed": 1.4444444, "segment": 1, "heart_rate": 132, "cadence": 78},
  {"start_time": 1644085621000, "calorie": 5.7, "distance": 89.1, "speed": 1.5, "segment": 1, "heart_rate": 135},
  {"start_time": 1644085620000, "calorie": 9.99, "distance": 99.9, "speed": 9.9, "segment": 1, "heart_rate": 199}
]
```

La troisième entrée répète volontairement l'horodatage de la première : la
clé primaire `(workout_id, at)` impose de dédupliquer.

`.../2/22222222-...location_data.json` :

```json
[
  {"start_time": 1740755394813, "latitude": 44.8010456, "longitude": -0.5758588, "altitude": 16.653, "accuracy": 10.0},
  {"start_time": 1740755395813, "latitude": 44.8011, "longitude": -0.5759},
  {"start_time": 1740755396813, "latitude": null, "longitude": -0.576}
]
```

`.../3/33333333-...additional.json` :

```json
{
  "pool_length": 25,
  "pool_length_unit": "meter",
  "total_distance": 2500.0,
  "total_duration": 2542638,
  "lengths": [
    {"duration": 25379, "interval": 1, "resting_time": 0, "stroke_count": 8, "stroke_type": "Freestyle"},
    {"duration": 26555, "interval": 1, "resting_time": 1200, "stroke_count": 9, "stroke_type": "Breaststroke"}
  ]
}
```

`.../4/44444444-...sensing_status.json` :

```json
{
  "heart_rate": {"is_valid": true, "type": 1, "max_hr_custom": 200, "max_hr_auto": 188, "at": 135, "ant": 166, "rhr": 60},
  "heart_rate_zone": {"is_valid": false},
  "sampling_rate": 2000
}
```

Créer `backend/tests/unit/test_json_files.py` :

```python
"""Tests de la lecture des fichiers JSON annexes de l'export."""

from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.samsung.json_files import (
    load_json,
    map_heart_rate_thresholds,
    map_locations,
    map_pool_length,
    map_samples,
    map_swim_lengths,
    resolve_json_path,
)

EXERCISE_DIR = Path(__file__).parent.parent / "fixtures" / "samsung" / "exercise"

LIVE = (
    "11111111-1111-1111-1111-111111111111"
    ".com.samsung.health.exercise.live_data.json"
)
LOCATION = (
    "22222222-2222-2222-2222-222222222222"
    ".com.samsung.health.exercise.location_data.json"
)
ADDITIONAL = (
    "33333333-3333-3333-3333-333333333333"
    ".com.samsung.health.exercise.additional.json"
)
SENSING = "44444444-4444-4444-4444-444444444444.sensing_status.json"


def test_resolve_json_path_uses_first_character_subdirectory() -> None:
    path = resolve_json_path(EXERCISE_DIR, LIVE)

    assert path is not None
    assert path.parent.name == "1"
    assert path.exists()


def test_resolve_json_path_returns_none_for_missing_or_empty() -> None:
    assert resolve_json_path(EXERCISE_DIR, None) is None
    assert resolve_json_path(EXERCISE_DIR, "") is None
    assert resolve_json_path(EXERCISE_DIR, "nope.json") is None


def test_map_samples_reads_every_metric() -> None:
    samples = map_samples(load_json(resolve_json_path(EXERCISE_DIR, LIVE)))

    first = samples[0]
    assert first.at == datetime(2022, 2, 5, 18, 27, tzinfo=timezone.utc)
    assert first.heart_rate == 132
    assert first.speed_mps == 1.4444444
    assert first.distance_m == 87.73
    assert first.calories_kcal == 5.65
    assert first.cadence == 78
    assert first.segment == 1


def test_map_samples_deduplicates_on_timestamp_keeping_last() -> None:
    """La clé primaire est (workout_id, at) ; un doublon ferait échouer
    l'insertion par lot entière."""
    samples = map_samples(load_json(resolve_json_path(EXERCISE_DIR, LIVE)))

    assert len(samples) == 2
    assert [s.at for s in samples] == sorted(s.at for s in samples)
    duplicated = next(
        s for s in samples if s.at == datetime(2022, 2, 5, 18, 27, tzinfo=timezone.utc)
    )
    assert duplicated.heart_rate == 199


def test_map_samples_tolerates_absent_metrics() -> None:
    samples = map_samples(load_json(resolve_json_path(EXERCISE_DIR, LIVE)))
    later = max(samples, key=lambda s: s.at)

    assert later.cadence is None


def test_map_locations_requires_coordinates() -> None:
    """Un point sans latitude n'est pas plaçable ; il est écarté plutôt que
    stocké avec une coordonnée nulle."""
    locations = map_locations(load_json(resolve_json_path(EXERCISE_DIR, LOCATION)))

    assert len(locations) == 2
    assert locations[0].latitude == 44.8010456
    assert locations[0].altitude_m == 16.653
    assert locations[0].accuracy_m == 10.0
    assert locations[1].altitude_m is None


def test_map_swim_lengths() -> None:
    lengths = map_swim_lengths(load_json(resolve_json_path(EXERCISE_DIR, ADDITIONAL)))

    assert len(lengths) == 2
    assert lengths[0].idx == 0
    assert lengths[0].duration_ms == 25379
    assert lengths[0].stroke_count == 8
    assert lengths[0].stroke_type == "Freestyle"
    assert lengths[0].resting_time_ms == 0
    assert lengths[1].stroke_type == "Breaststroke"
    assert lengths[1].resting_time_ms == 1200


def test_map_pool_length() -> None:
    payload = load_json(resolve_json_path(EXERCISE_DIR, ADDITIONAL))

    assert map_pool_length(payload) == 25.0


def test_map_pool_length_ignores_non_metric_units() -> None:
    """Seuls les bassins en mètres sont convertibles sans hypothèse."""
    assert map_pool_length({"pool_length": 25, "pool_length_unit": "yard"}) is None


def test_map_swim_lengths_on_non_swim_payload_is_empty() -> None:
    assert map_swim_lengths({"exercise_type": 1002, "main_workout": {}}) == []


def test_map_heart_rate_thresholds() -> None:
    thresholds = map_heart_rate_thresholds(
        load_json(resolve_json_path(EXERCISE_DIR, SENSING))
    )

    assert thresholds.max_hr_custom == 200
    assert thresholds.max_hr_auto == 188
    assert thresholds.aerobic == 135
    assert thresholds.anaerobic == 166
    assert thresholds.resting == 60


def test_map_heart_rate_thresholds_on_empty_payload() -> None:
    empty = map_heart_rate_thresholds(None)

    assert empty.max_hr_custom is None
    assert empty.resting is None


def test_load_json_returns_none_on_unreadable_file(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{ pas du json", encoding="utf-8")

    assert load_json(broken) is None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_json_files.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.json_files'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/samsung/json_files.py` :

```python
"""Résolution et lecture des fichiers JSON annexes de l'export.

L'export place chaque fichier dans un sous-répertoire nommé par le premier
caractère de son nom.

Les fichiers live_data_internal et location_data_internal (224 Mo au total)
ne sont volontairement pas traités : ils ne contiennent que des métadonnées
d'intervalle sans valeur analytique (cf. spec section 7).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.samsung.parsers import (
    parse_epoch_millis,
    parse_float,
    parse_int,
)
from app.ingestion.samsung.records import (
    LocationRecord,
    SampleRecord,
    SwimLengthRecord,
)

METRIC_POOL_UNITS = frozenset({"meter", "meters", "m"})


@dataclass(frozen=True, slots=True)
class HeartRateThresholds:
    max_hr_custom: int | None = None
    max_hr_auto: int | None = None
    aerobic: int | None = None
    anaerobic: int | None = None
    resting: int | None = None


def resolve_json_path(exercise_dir: Path, filename: str | None) -> Path | None:
    name = (filename or "").strip()
    if not name:
        return None
    candidate = exercise_dir / name[0] / name
    return candidate if candidate.is_file() else None


def load_json(path: Path | None) -> object | None:
    if path is None:
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _items(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def map_samples(payload: object) -> list[SampleRecord]:
    """Déduplique sur l'horodatage, la dernière occurrence gagnant.

    La clé primaire est (workout_id, at) ; un doublon ferait échouer tout le
    lot d'insertion.
    """
    by_timestamp: dict[object, SampleRecord] = {}
    for item in _items(payload):
        at = parse_epoch_millis(item.get("start_time"))
        if at is None:
            continue
        by_timestamp[at] = SampleRecord(
            at=at,
            elapsed_ms=parse_int(item.get("elapsed_time")),
            heart_rate=parse_int(item.get("heart_rate")),
            speed_mps=parse_float(item.get("speed")),
            distance_m=parse_float(item.get("distance")),
            calories_kcal=parse_float(item.get("calorie")),
            cadence=parse_int(item.get("cadence")),
            segment=parse_int(item.get("segment")),
        )
    return sorted(by_timestamp.values(), key=lambda sample: sample.at)


def map_locations(payload: object) -> list[LocationRecord]:
    by_timestamp: dict[object, LocationRecord] = {}
    for item in _items(payload):
        at = parse_epoch_millis(item.get("start_time"))
        latitude = parse_float(item.get("latitude"))
        longitude = parse_float(item.get("longitude"))
        if at is None or latitude is None or longitude is None:
            continue
        by_timestamp[at] = LocationRecord(
            at=at,
            latitude=latitude,
            longitude=longitude,
            altitude_m=parse_float(item.get("altitude")),
            accuracy_m=parse_float(item.get("accuracy")),
        )
    return sorted(by_timestamp.values(), key=lambda point: point.at)


def map_swim_lengths(payload: object) -> list[SwimLengthRecord]:
    if not isinstance(payload, dict):
        return []
    lengths = payload.get("lengths")
    if not isinstance(lengths, list):
        return []
    records: list[SwimLengthRecord] = []
    for index, item in enumerate(lengths):
        if not isinstance(item, dict):
            continue
        stroke = item.get("stroke_type")
        records.append(
            SwimLengthRecord(
                idx=index,
                duration_ms=parse_int(item.get("duration")),
                stroke_count=parse_int(item.get("stroke_count")),
                stroke_type=str(stroke) if stroke else None,
                resting_time_ms=parse_int(item.get("resting_time")),
            )
        )
    return records


def map_pool_length(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    unit = str(payload.get("pool_length_unit") or "").strip().lower()
    if unit not in METRIC_POOL_UNITS:
        return None
    return parse_float(payload.get("pool_length"))


def map_heart_rate_thresholds(payload: object) -> HeartRateThresholds:
    if not isinstance(payload, dict):
        return HeartRateThresholds()
    heart_rate = payload.get("heart_rate")
    if not isinstance(heart_rate, dict):
        return HeartRateThresholds()
    return HeartRateThresholds(
        max_hr_custom=parse_int(heart_rate.get("max_hr_custom")),
        max_hr_auto=parse_int(heart_rate.get("max_hr_auto")),
        aerobic=parse_int(heart_rate.get("at")),
        anaerobic=parse_int(heart_rate.get("ant")),
        resting=parse_int(heart_rate.get("rhr")),
    )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_json_files.py -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/json_files.py backend/tests/unit/test_json_files.py backend/tests/fixtures/samsung/exercise
git commit -m "feat: read samsung per-workout json payloads"
```

---

### Task 9: Assemblage d'une séance complète

**Files:**
- Create: `backend/app/ingestion/samsung/assembler.py`
- Create: `backend/tests/unit/test_assembler.py`

**Interfaces:**
- Consumes: `map_workout`, `map_strength_sets`, `map_json_references`
  (tâche 7) ; tout `json_files` (tâche 8) ; `WorkoutBundle`, `ExtraRecord`
  (tâche 5).
- Produces: `build_workout_bundle(row: dict[str, str], exercise_dir: Path) -> WorkoutBundle | None`

C'est le seul module qui combine mapping et accès disque ; l'isoler garde
`mapper.py` et `json_files.py` testables séparément.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_assembler.py` :

```python
"""Tests de l'assemblage d'une séance et de ses dépendances."""

import json
from pathlib import Path

from app.ingestion.samsung.assembler import build_workout_bundle

EXERCISE_DIR = Path(__file__).parent.parent / "fixtures" / "samsung" / "exercise"
P = "com.samsung.health.exercise."

BASE_ROW = {
    f"{P}datauuid": "185e928e-af99-46fd-9dad-35f114d5b32d",
    f"{P}start_time": "2022-02-05 20:27:00.000",
    f"{P}time_offset": "UTC+0100",
    f"{P}exercise_type": "1002",
    f"{P}live_data": (
        "11111111-1111-1111-1111-111111111111"
        ".com.samsung.health.exercise.live_data.json"
    ),
    f"{P}location_data": (
        "22222222-2222-2222-2222-222222222222"
        ".com.samsung.health.exercise.location_data.json"
    ),
    f"{P}additional": "",
    "sensing_status": "44444444-4444-4444-4444-444444444444.sensing_status.json",
    "subset_data": "",
}

SWIM_ROW = {
    **BASE_ROW,
    f"{P}exercise_type": "14001",
    f"{P}live_data": "",
    f"{P}location_data": "",
    f"{P}additional": (
        "33333333-3333-3333-3333-333333333333"
        ".com.samsung.health.exercise.additional.json"
    ),
    "sensing_status": "",
}


def test_bundles_samples_and_locations() -> None:
    bundle = build_workout_bundle(BASE_ROW, EXERCISE_DIR)

    assert bundle is not None
    assert len(bundle.samples) == 2
    assert len(bundle.locations) == 2


def test_merges_heart_rate_thresholds_into_workout() -> None:
    """Les seuils vivent dans sensing_status, pas dans la ligne CSV."""
    bundle = build_workout_bundle(BASE_ROW, EXERCISE_DIR)

    assert bundle.workout.max_hr_custom == 200
    assert bundle.workout.max_hr_auto == 188
    assert bundle.workout.hr_aerobic_threshold == 135
    assert bundle.workout.hr_anaerobic_threshold == 166
    assert bundle.workout.resting_hr == 60


def test_bundles_swim_lengths_and_pool_length() -> None:
    bundle = build_workout_bundle(SWIM_ROW, EXERCISE_DIR)

    assert bundle.workout.sport == "Natation"
    assert bundle.workout.pool_length_m == 25.0
    assert len(bundle.swim_lengths) == 2
    assert bundle.swim_lengths[0].stroke_type == "Freestyle"


def test_bundles_strength_sets_for_musculation() -> None:
    row = {
        **BASE_ROW,
        f"{P}exercise_type": "10026",
        "subset_data": json.dumps(
            [{"duration": 42, "reps": 10, "weight": 20.0, "weight_unit": "kg"}]
        ),
    }

    bundle = build_workout_bundle(row, EXERCISE_DIR)

    assert bundle.workout.sport == "Musculation"
    assert len(bundle.strength_sets) == 1
    assert bundle.strength_sets[0].reps == 10


def test_keeps_additional_payload_as_extra() -> None:
    bundle = build_workout_bundle(SWIM_ROW, EXERCISE_DIR)

    kinds = {extra.kind for extra in bundle.extras}
    assert "additional" in kinds


def test_missing_json_files_yield_empty_lists() -> None:
    row = {
        **BASE_ROW,
        f"{P}live_data": "absent.json",
        f"{P}location_data": "",
        "sensing_status": "",
    }

    bundle = build_workout_bundle(row, EXERCISE_DIR)

    assert bundle is not None
    assert bundle.samples == []
    assert bundle.locations == []
    assert bundle.workout.resting_hr is None


def test_unmappable_row_yields_none() -> None:
    assert build_workout_bundle({**BASE_ROW, f"{P}datauuid": ""}, EXERCISE_DIR) is None
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_assembler.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.assembler'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/samsung/assembler.py` :

```python
"""Assemblage d'une séance complète à partir d'une ligne CSV et du disque."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from app.ingestion.samsung import json_files
from app.ingestion.samsung.mapper import (
    map_json_references,
    map_strength_sets,
    map_workout,
)
from app.ingestion.samsung.records import ExtraRecord, WorkoutBundle


def build_workout_bundle(
    row: dict[str, str], exercise_dir: Path
) -> WorkoutBundle | None:
    workout = map_workout(row)
    if workout is None:
        return None

    references = map_json_references(row)

    live = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.live_data)
    )
    location = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.location_data)
    )
    additional = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.additional)
    )
    sensing = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.sensing_status)
    )

    thresholds = json_files.map_heart_rate_thresholds(sensing)
    workout = dataclasses.replace(
        workout,
        pool_length_m=json_files.map_pool_length(additional),
        max_hr_custom=thresholds.max_hr_custom,
        max_hr_auto=thresholds.max_hr_auto,
        hr_aerobic_threshold=thresholds.aerobic,
        hr_anaerobic_threshold=thresholds.anaerobic,
        resting_hr=thresholds.resting,
    )

    extras: list[ExtraRecord] = []
    if isinstance(additional, dict):
        extras.append(ExtraRecord(kind="additional", payload=additional))
    if isinstance(sensing, dict):
        extras.append(ExtraRecord(kind="sensing_status", payload=sensing))

    return WorkoutBundle(
        workout=workout,
        samples=json_files.map_samples(live),
        locations=json_files.map_locations(location),
        swim_lengths=json_files.map_swim_lengths(additional),
        strength_sets=map_strength_sets(row, workout.sport),
        extras=extras,
    )
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_assembler.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/assembler.py backend/tests/unit/test_assembler.py
git commit -m "feat: assemble workout bundles from csv row and json payloads"
```

---

### Task 10: Lecture de phases.json

**Files:**
- Create: `backend/app/ingestion/phases.py`
- Create: `backend/tests/unit/test_phases_source.py`
- Create: `backend/tests/fixtures/phases.json`

**Interfaces:**
- Consumes: `PhaseRecord` (tâche 5).
- Produces: `read_phases(path: Path) -> list[PhaseRecord]`

`phases.json` nomme l'objectif musculaire `muscle_target` ; le modèle le
nomme `skeletal_muscle_target_kg`. La correspondance est explicite ici.

- [ ] **Step 1: Écrire la fixture et le test qui échoue**

Créer `backend/tests/fixtures/phases.json` :

```json
[
  {"name": "Phase libre", "type": "free", "start": "2023-01-01", "end": "2023-12-31"},
  {
    "name": "Première sèche",
    "type": "cut",
    "start": "2024-01-01",
    "end": "2025-03-31",
    "objectives": {
      "weight_target": 70,
      "body_fat_target": 20.0,
      "muscle_target": 30.0,
      "calories_target": 1900
    }
  },
  {"name": "Cassée", "type": "cut", "start": "pas une date", "end": "2025-04-30"},
  {"name": "Type inconnu", "type": "wat", "start": "2025-05-01", "end": "2025-05-31"}
]
```

Créer `backend/tests/unit/test_phases_source.py` :

```python
"""Tests de la lecture de phases.json."""

from datetime import date
from pathlib import Path

from app.ingestion.phases import read_phases

FIXTURE = Path(__file__).parent.parent / "fixtures" / "phases.json"


def test_reads_phase_without_objectives() -> None:
    phases = read_phases(FIXTURE)

    free = next(p for p in phases if p.name == "Phase libre")
    assert free.kind == "free"
    assert free.starts_on == date(2023, 1, 1)
    assert free.ends_on == date(2023, 12, 31)
    assert free.weight_target_kg is None
    assert free.daily_calories_target is None


def test_maps_objectives_including_renamed_muscle_target() -> None:
    phases = read_phases(FIXTURE)

    cut = next(p for p in phases if p.name == "Première sèche")
    assert cut.weight_target_kg == 70.0
    assert cut.body_fat_target_pct == 20.0
    assert cut.skeletal_muscle_target_kg == 30.0
    assert cut.daily_calories_target == 1900


def test_skips_entries_with_unreadable_dates() -> None:
    assert all(p.name != "Cassée" for p in read_phases(FIXTURE))


def test_unknown_kind_falls_back_to_free() -> None:
    phases = read_phases(FIXTURE)

    assert next(p for p in phases if p.name == "Type inconnu").kind == "free"


def test_result_is_sorted_by_start_date() -> None:
    phases = read_phases(FIXTURE)

    assert [p.starts_on for p in phases] == sorted(p.starts_on for p in phases)


def test_missing_file_yields_empty_list(tmp_path: Path) -> None:
    assert read_phases(tmp_path / "absent.json") == []
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_phases_source.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.phases'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/phases.py` :

```python
"""Lecture du fichier phases.json de l'application Streamlit."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.ingestion.samsung.parsers import parse_float, parse_int
from app.ingestion.samsung.records import PhaseRecord

VALID_KINDS = frozenset({"free", "bulk", "cut", "maintain"})
DEFAULT_KIND = "free"


def _parse_date(raw: object) -> date | None:
    try:
        return date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        return None


def read_phases(path: Path) -> list[PhaseRecord]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    if not isinstance(payload, list):
        return []

    records: list[PhaseRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        starts_on = _parse_date(item.get("start"))
        ends_on = _parse_date(item.get("end"))
        if starts_on is None or ends_on is None or ends_on < starts_on:
            continue
        kind = str(item.get("type") or "").strip().lower()
        objectives = item.get("objectives")
        objectives = objectives if isinstance(objectives, dict) else {}
        records.append(
            PhaseRecord(
                name=str(item.get("name") or "").strip(),
                kind=kind if kind in VALID_KINDS else DEFAULT_KIND,
                starts_on=starts_on,
                ends_on=ends_on,
                weight_target_kg=parse_float(objectives.get("weight_target")),
                body_fat_target_pct=parse_float(objectives.get("body_fat_target")),
                skeletal_muscle_target_kg=parse_float(objectives.get("muscle_target")),
                daily_calories_target=parse_int(objectives.get("calories_target")),
            )
        )
    return sorted(records, key=lambda record: record.starts_on)
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_phases_source.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/phases.py backend/tests/unit/test_phases_source.py backend/tests/fixtures/phases.json
git commit -m "feat: read phases from legacy phases.json"
```

---

### Task 11: Loader idempotent

**Files:**
- Create: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/conftest.py`
- Create: `backend/tests/integration/test_loader.py`

**Interfaces:**
- Consumes: les modèles (tâche 4) ; toutes les dataclasses (tâche 5).
- Produces:
  - `upsert_body_measurements(session, records) -> int`
  - `upsert_nutrition_entries(session, records) -> int`
  - `upsert_phases(session, records) -> int`
  - `upsert_workout_bundle(session, bundle) -> int` (renvoie l'id de séance)
  - `upsert_workout_bundles(session, bundles) -> int`

- [ ] **Step 1: Créer la base de test et le conftest d'intégration**

Run:
```bash
docker compose exec db psql -U body -d postgres \
  -c "CREATE DATABASE body_analysis_test OWNER body"
```
Expected: `CREATE DATABASE` (ou une erreur « existe déjà », sans gravité)

Créer `backend/tests/integration/__init__.py` vide.

Créer `backend/tests/integration/conftest.py` :

```python
"""Base de données jetable pour les tests d'intégration.

Nécessite le service db de compose. Le schéma est créé depuis les métadonnées
plutôt que par Alembic : c'est plus rapide, et la conformité de la migration
au modèle est vérifiée séparément par la tâche 4.
"""

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import Base

TEST_DATABASE_URL = os.environ.get(
    "BA_TEST_DATABASE_URL",
    "postgresql+asyncpg://body:body-local-dev@localhost:5432/body_analysis_test",
)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    created = create_async_engine(TEST_DATABASE_URL)
    async with created.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield created
    await created.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as opened:
        yield opened
```

Note : `loop_scope="session"` est obligatoire, sinon pytest-asyncio crée une
boucle par test et le moteur de portée session devient inutilisable.

- [ ] **Step 2: Écrire les tests qui échouent**

Créer `backend/tests/integration/test_loader.py` :

```python
"""Tests d'idempotence du loader."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_nutrition_entries,
    upsert_workout_bundle,
)
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
    SampleRecord,
    StrengthSetRecord,
    WorkoutBundle,
    WorkoutRecord,
)
from app.models import BodyMeasurement, NutritionEntry, StrengthSet, Workout, WorkoutSample

UUID = "11111111-1111-1111-1111-111111111111"


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (WorkoutSample, StrengthSet, Workout, BodyMeasurement, NutritionEntry):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_body_measurement_reimport_updates_instead_of_duplicating(
    session: AsyncSession,
) -> None:
    first = BodyMeasurementRecord(
        source_uuid=UUID,
        measured_at=datetime(2026, 8, 31, 6, 29, tzinfo=UTC),
        weight_kg=65.6,
    )
    await upsert_body_measurements(session, [first])

    corrected = BodyMeasurementRecord(
        source_uuid=UUID,
        measured_at=datetime(2026, 8, 31, 6, 29, tzinfo=UTC),
        weight_kg=66.1,
    )
    await upsert_body_measurements(session, [corrected])

    assert await _count(session, BodyMeasurement) == 1
    stored = (await session.execute(select(BodyMeasurement))).scalar_one()
    assert stored.weight_kg == 66.1


async def test_nutrition_reimport_is_idempotent(session: AsyncSession) -> None:
    record = NutritionEntryRecord(
        source_uuid=UUID,
        consumed_at=datetime(2024, 8, 14, 11, 56, tzinfo=UTC),
        food_name="Oeuf",
        calories=78.0,
    )

    await upsert_nutrition_entries(session, [record])
    await upsert_nutrition_entries(session, [record])

    assert await _count(session, NutritionEntry) == 1


async def test_workout_children_are_replaced_not_appended(
    session: AsyncSession,
) -> None:
    """Réingérer une séance dont les échantillons ont changé ne doit pas
    accumuler les anciens à côté des nouveaux."""
    workout = WorkoutRecord(
        source_uuid=UUID,
        started_at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC),
        sport="Course à pied",
    )
    three = [
        SampleRecord(at=datetime(2026, 2, 5, 19, 2, second, tzinfo=UTC), heart_rate=130)
        for second in (0, 1, 2)
    ]
    await upsert_workout_bundle(session, WorkoutBundle(workout=workout, samples=three))
    assert await _count(session, WorkoutSample) == 3

    one = [SampleRecord(at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC), heart_rate=140)]
    await upsert_workout_bundle(session, WorkoutBundle(workout=workout, samples=one))

    assert await _count(session, Workout) == 1
    assert await _count(session, WorkoutSample) == 1
    stored = (await session.execute(select(WorkoutSample))).scalar_one()
    assert stored.heart_rate == 140


async def test_reingest_without_payloads_preserves_existing_children(
    session: AsyncSession,
) -> None:
    """Régression : Samsung a cessé d'exporter les JSON par séance.

    Un nouvel export référence toujours les séances mais leurs fichiers
    live_data sont absents, donc le paquet arrive sans échantillon. Réingérer
    ne doit PAS détruire ce qui est déjà en base."""
    workout = WorkoutRecord(
        source_uuid=UUID,
        started_at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC),
        sport="Course à pied",
    )
    samples = [
        SampleRecord(at=datetime(2026, 2, 5, 19, 2, second, tzinfo=UTC), heart_rate=130)
        for second in (0, 1, 2)
    ]
    await upsert_workout_bundle(session, WorkoutBundle(workout=workout, samples=samples))
    assert await _count(session, WorkoutSample) == 3

    await upsert_workout_bundle(session, WorkoutBundle(workout=workout))

    assert await _count(session, WorkoutSample) == 3
    stored = (await session.execute(select(Workout))).scalar_one()
    assert stored.has_samples is True


async def test_workout_presence_flags_are_computed(session: AsyncSession) -> None:
    workout = WorkoutRecord(
        source_uuid=UUID,
        started_at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC),
        sport="Musculation",
    )
    bundle = WorkoutBundle(
        workout=workout,
        strength_sets=[StrengthSetRecord(idx=0, reps=10, weight_kg=20.0)],
    )

    await upsert_workout_bundle(session, bundle)

    stored = (await session.execute(select(Workout))).scalar_one()
    assert stored.has_strength_sets is True
    assert stored.has_samples is False
    assert stored.has_locations is False
    assert stored.has_swim_lengths is False
```

- [ ] **Step 3: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_loader.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.loader'`

- [ ] **Step 4: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/samsung/loader.py` :

```python
"""Écriture idempotente des dataclasses de domaine en base.

Toute insertion passe par ON CONFLICT DO UPDATE sur source_uuid. Les tables
filles d'une séance sont remplacées et non complétées : réingérer une séance
dont les échantillons ont changé ne doit pas accumuler les anciens.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
    PhaseRecord,
    WorkoutBundle,
)
from app.models import (
    BodyMeasurement,
    Phase,
    StrengthSet,
    SwimLength,
    Workout,
    WorkoutExtra,
    WorkoutLocation,
    WorkoutSample,
)
from app.models.nutrition import NutritionEntry

BATCH_SIZE = 1000

# Correspondance dataclass -> colonne, là où les noms diffèrent.
_PHASE_FIELD_MAP = {"kind": "kind"}


def _batches(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def _upsert_on_source_uuid(
    session: AsyncSession, model: type, records: Sequence[Any]
) -> int:
    if not records:
        return 0
    total = 0
    for batch in _batches(records):
        values = [dataclasses.asdict(record) for record in batch]
        statement = insert(model).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=["source_uuid"],
            set_={
                key: statement.excluded[key]
                for key in values[0]
                if key != "source_uuid"
            },
        )
        await session.execute(statement)
        total += len(batch)
    await session.commit()
    return total


async def upsert_body_measurements(
    session: AsyncSession, records: Sequence[BodyMeasurementRecord]
) -> int:
    return await _upsert_on_source_uuid(session, BodyMeasurement, records)


async def upsert_nutrition_entries(
    session: AsyncSession, records: Sequence[NutritionEntryRecord]
) -> int:
    return await _upsert_on_source_uuid(session, NutritionEntry, records)


async def upsert_phases(session: AsyncSession, records: Sequence[PhaseRecord]) -> int:
    """Les phases n'ont pas de source_uuid : la clé naturelle est le nom et
    la date de début. Le remplacement complet est plus simple et sans risque,
    il n'y en a que huit."""
    if not records:
        return 0
    await session.execute(delete(Phase))
    await session.execute(
        insert(Phase).values([dataclasses.asdict(record) for record in records])
    )
    await session.commit()
    return len(records)


async def upsert_workout_bundle(session: AsyncSession, bundle: WorkoutBundle) -> int:
    # Les drapeaux has_* ne figurent PAS ici : ils sont recalculés depuis la
    # base après l'écriture des lignes filles, sinon un export sans JSON les
    # remettrait à faux alors que les données restent présentes.
    values = dataclasses.asdict(bundle.workout)

    statement = insert(Workout).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=["source_uuid"],
        set_={key: statement.excluded[key] for key in values if key != "source_uuid"},
    ).returning(Workout.id)
    workout_id = (await session.execute(statement)).scalar_one()

    children = (
        (WorkoutSample, bundle.samples),
        (WorkoutLocation, bundle.locations),
        (SwimLength, bundle.swim_lengths),
        (StrengthSet, bundle.strength_sets),
        (WorkoutExtra, bundle.extras),
    )
    for model, records in children:
        if not records:
            # L'export courant n'apporte rien pour ce type : on PRÉSERVE
            # l'existant. Samsung a cessé d'exporter les JSON par séance ;
            # un remplacement inconditionnel détruirait les 2,8 M
            # d'échantillons déjà en base au premier import d'un nouvel
            # export.
            continue
        await session.execute(delete(model).where(model.workout_id == workout_id))
        rows = [
            {"workout_id": workout_id, **dataclasses.asdict(record)}
            for record in records
        ]
        for batch in _batches(rows):
            await session.execute(insert(model).values(list(batch)))

    await _refresh_presence_flags(session, workout_id)
    return workout_id


async def _refresh_presence_flags(session: AsyncSession, workout_id: int) -> None:
    """Recalcule les drapeaux depuis la base, jamais depuis le paquet.

    Les lignes filles peuvent préexister sans être dans le paquet courant ;
    déduire les drapeaux du seul paquet les remettrait à faux alors que les
    données sont bien là.
    """
    flags = {}
    for column, model in (
        ("has_samples", WorkoutSample),
        ("has_locations", WorkoutLocation),
        ("has_swim_lengths", SwimLength),
        ("has_strength_sets", StrengthSet),
    ):
        present = await session.scalar(
            select(exists().where(model.workout_id == workout_id))
        )
        flags[column] = bool(present)
    await session.execute(
        update(Workout).where(Workout.id == workout_id).values(**flags)
    )


async def upsert_workout_bundles(
    session: AsyncSession, bundles: Iterable[WorkoutBundle]
) -> int:
    """Commite tous les 100 paquets : garder 4 734 séances et leurs 2,8 M
    d'échantillons dans une seule transaction ferait exploser la mémoire."""
    total = 0
    for bundle in bundles:
        await upsert_workout_bundle(session, bundle)
        total += 1
        if total % 100 == 0:
            await session.commit()
    await session.commit()
    return total
```

Retirer la constante `_PHASE_FIELD_MAP`, inutilisée — les noms de champs de
`PhaseRecord` correspondent déjà aux colonnes de `Phase`.

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration/test_loader.py -v`
Expected: PASS, 4 tests

- [ ] **Step 6: Commiter**

```bash
git add backend/app/ingestion/samsung/loader.py backend/tests/integration
git commit -m "feat: add idempotent loader for ingestion records"
```

---

### Task 12: Vues matérialisées quotidiennes

**Files:**
- Create: `backend/app/ingestion/refresh.py`
- Create: `backend/migrations/versions/<hash>_daily_materialized_views.py`
- Create: `backend/tests/integration/test_daily_views.py`

**Interfaces:**
- Consumes: le schéma de la tâche 4.
- Produces:
  - `refresh_materialized_views(session, *, concurrently: bool = True) -> None`
  - `DAILY_VIEWS: tuple[str, ...]`

Décision documentée : **la frontière de journée est `Europe/Paris`.** Les
horodatages sont stockés avec leur fuseau ; les regrouper en UTC ferait
basculer dans la veille tout ce qui est consommé avant 2 h du matin en été.

Le rafraîchissement `CONCURRENTLY` exige un index unique sur chaque vue.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/integration/test_daily_views.py` :

```python
"""Tests des vues matérialisées quotidiennes."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.refresh import refresh_materialized_views
from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_nutrition_entries,
)
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
)
from app.models import BodyMeasurement, NutritionEntry


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (BodyMeasurement, NutritionEntry):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_daily_body_keeps_last_measurement_of_the_day(
    session: AsyncSession,
) -> None:
    await upsert_body_measurements(
        session,
        [
            BodyMeasurementRecord(
                source_uuid="morning",
                measured_at=datetime(2026, 8, 31, 6, 0, tzinfo=UTC),
                weight_kg=66.0,
            ),
            BodyMeasurementRecord(
                source_uuid="evening",
                measured_at=datetime(2026, 8, 31, 20, 0, tzinfo=UTC),
                weight_kg=65.4,
            ),
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    rows = (
        await session.execute(text("SELECT day, weight_kg FROM mv_daily_body"))
    ).all()
    assert len(rows) == 1
    assert rows[0].weight_kg == 65.4


async def test_daily_nutrition_sums_calories(session: AsyncSession) -> None:
    await upsert_nutrition_entries(
        session,
        [
            NutritionEntryRecord(
                source_uuid=f"entry-{index}",
                consumed_at=datetime(2026, 8, 31, 12, index, tzinfo=UTC),
                calories=100.0,
            )
            for index in range(3)
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (
        await session.execute(
            text("SELECT calories, entry_count FROM mv_daily_nutrition")
        )
    ).one()
    assert row.calories == 300.0
    assert row.entry_count == 3


async def test_day_boundary_uses_paris_time(session: AsyncSession) -> None:
    """Le 31 août à 23 h 30 UTC est déjà le 1er septembre à Paris."""
    await upsert_nutrition_entries(
        session,
        [
            NutritionEntryRecord(
                source_uuid="late",
                consumed_at=datetime(2026, 8, 31, 23, 30, tzinfo=UTC),
                calories=50.0,
            )
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (await session.execute(text("SELECT day FROM mv_daily_nutrition"))).one()
    assert str(row.day) == "2026-09-01"


async def test_concurrent_refresh_works(session: AsyncSession) -> None:
    """Vérifie que les index uniques requis par CONCURRENTLY existent."""
    await refresh_materialized_views(session, concurrently=False)

    await refresh_materialized_views(session, concurrently=True)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_daily_views.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.refresh'`

- [ ] **Step 3: Écrire la migration des vues**

Run: `cd backend && uv run alembic revision -m "daily materialized views"`

Remplacer le corps du fichier créé dans `migrations/versions/` par :

```python
"""daily materialized views

Les vues portent les agrégats quotidiens qui, sans elles, seraient les
requêtes les plus coûteuses de l'application (tableau de bord, heatmaps).

La frontière de journée est Europe/Paris : regrouper en UTC ferait basculer
dans la veille tout ce qui est consommé avant 2 h du matin en été.

Chaque vue reçoit un index unique sur day, sans lequel REFRESH ...
CONCURRENTLY est refusé par PostgreSQL.
"""

from alembic import op

revision = "<hash généré>"
down_revision = "<hash de la migration initiale>"
branch_labels = None
depends_on = None

DAY_TZ = "Europe/Paris"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_body AS
        SELECT DISTINCT ON (day)
            day,
            weight_kg,
            body_fat_pct,
            body_fat_mass_kg,
            skeletal_muscle_mass_kg,
            fat_free_mass_kg,
            total_body_water_kg,
            basal_metabolic_rate_kcal
        FROM (
            SELECT
                (measured_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                measured_at,
                weight_kg,
                body_fat_pct,
                body_fat_mass_kg,
                skeletal_muscle_mass_kg,
                fat_free_mass_kg,
                total_body_water_kg,
                basal_metabolic_rate_kcal
            FROM body_measurement
        ) AS daily
        ORDER BY day, measured_at DESC
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_body_day ON mv_daily_body (day)"
    )

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_nutrition AS
        SELECT
            (consumed_at AT TIME ZONE '{DAY_TZ}')::date AS day,
            SUM(calories) AS calories,
            COUNT(*) AS entry_count
        FROM nutrition_entry
        GROUP BY 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_nutrition_day ON mv_daily_nutrition (day)"
    )

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_training AS
        SELECT
            (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
            COUNT(*) AS session_count,
            SUM(duration_ms) AS duration_ms,
            SUM(calories_kcal) AS calories_kcal,
            SUM(distance_m) AS distance_m
        FROM workout
        GROUP BY 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_training_day ON mv_daily_training (day)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_training")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_nutrition")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_body")
```

Créer `backend/app/ingestion/refresh.py` :

```python
"""Rafraîchissement des vues matérialisées quotidiennes."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DAILY_VIEWS = ("mv_daily_body", "mv_daily_nutrition", "mv_daily_training")


async def refresh_materialized_views(
    session: AsyncSession, *, concurrently: bool = True
) -> None:
    """Rafraîchit les trois vues quotidiennes.

    concurrently=False est nécessaire au premier peuplement : PostgreSQL
    refuse un rafraîchissement concurrent sur une vue jamais peuplée.
    """
    mode = "CONCURRENTLY " if concurrently else ""
    for view in DAILY_VIEWS:
        await session.execute(text(f"REFRESH MATERIALIZED VIEW {mode}{view}"))
    await session.commit()
```

- [ ] **Step 4: Appliquer la migration sur les deux bases**

Run: `cd backend && uv run alembic upgrade head`
Expected: `Running upgrade <initial> -> <hash>, daily materialized views`

Les tests d'intégration créaient jusqu'ici leur schéma depuis
`Base.metadata`, qui ne connaît pas les vues matérialisées. Il faut donc les
faire passer par Alembic. Remplacer la fixture `engine` de
`tests/integration/conftest.py` par :

```python
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    """Applique les migrations Alembic sur la base de test.

    Passer par Alembic plutôt que par create_all est indispensable depuis
    l'introduction des vues matérialisées : Base.metadata ne les connaît pas.
    """
    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[2] / "migrations"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    await asyncio.to_thread(command.downgrade, config, "base")
    await asyncio.to_thread(command.upgrade, config, "head")

    created = create_async_engine(TEST_DATABASE_URL)
    yield created
    await created.dispose()
```

Ajouter en tête du conftest : `import asyncio` et `from pathlib import Path`,
et retirer l'import désormais inutile de `Base`.

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration -v`
Expected: PASS, 8 tests (4 du loader, 4 des vues)

- [ ] **Step 6: Commiter**

```bash
git add backend/app/ingestion/refresh.py backend/migrations/versions backend/tests/integration
git commit -m "feat: add daily materialized views with paris day boundary"
```

---

### Task 13: Pipeline d'ingestion et traçabilité

**Files:**
- Create: `backend/app/ingestion/samsung/pipeline.py`
- Create: `backend/tests/unit/test_discover_source.py`
- Create: `backend/tests/integration/test_pipeline.py`

**Interfaces:**
- Consumes: `read_samsung_csv` (tâche 2) ; `map_body_measurement`,
  `map_nutrition_entry` (tâches 5-6) ; `build_workout_bundle` (tâche 9) ;
  `read_phases` (tâche 10) ; tout `loader` (tâche 11) ;
  `refresh_materialized_views` (tâche 12).
- Produces:
  - `SamsungSource` (dataclass : `weight_csv`, `food_csv`, `exercise_csv`,
    `exercise_dir`, `phases_json`, tous `Path | None`)
  - `discover_source(root: Path) -> SamsungSource`
  - `run_ingestion(session, source, *, kind, source_name) -> IngestionRun`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/unit/test_discover_source.py` :

```python
"""Tests de la localisation des fichiers dans un export."""

from pathlib import Path

from app.ingestion.samsung.pipeline import discover_source


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_finds_every_component(tmp_path: Path) -> None:
    _touch(tmp_path / "com.samsung.health.weight.20260831162666.csv")
    _touch(tmp_path / "com.samsung.health.food_intake.20260831162666.csv")
    _touch(tmp_path / "com.samsung.shealth.exercise.20260831162666.csv")
    _touch(tmp_path / "com.samsung.shealth.exercise" / "1" / "a.json")
    _touch(tmp_path / "phases.json")

    source = discover_source(tmp_path)

    assert source.weight_csv is not None
    assert source.food_csv is not None
    assert source.exercise_csv is not None
    assert source.exercise_dir == tmp_path / "com.samsung.shealth.exercise"
    assert source.phases_json is not None


def test_keeps_the_most_recent_export_of_each_kind(tmp_path: Path) -> None:
    _touch(tmp_path / "com.samsung.health.weight.20250101000000.csv")
    _touch(tmp_path / "com.samsung.health.weight.20260831162666.csv")

    source = discover_source(tmp_path)

    assert source.weight_csv.name.endswith("20260831162666.csv")


def test_ignores_exercise_csv_without_timestamp(tmp_path: Path) -> None:
    """L'export contient d'autres CSV commençant pareil ; seul le format à
    14 chiffres est le fichier de séances."""
    _touch(tmp_path / "com.samsung.shealth.exercise.summary.csv")

    assert discover_source(tmp_path).exercise_csv is None


def test_empty_directory_yields_all_none(tmp_path: Path) -> None:
    source = discover_source(tmp_path)

    assert source.weight_csv is None
    assert source.exercise_dir is None
    assert source.phases_json is None
```

Créer `backend/tests/integration/test_pipeline.py` :

```python
"""Tests du pipeline d'ingestion de bout en bout."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.models import (
    BodyMeasurement,
    IngestionRun,
    IngestionStatus,
    NutritionEntry,
    Phase,
    Workout,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    """Construit un export minimal mais complet dans un répertoire jetable."""
    shutil.copy(
        FIXTURES / "samsung" / "weight_sample.csv",
        tmp_path / "com.samsung.health.weight.20260831162666.csv",
    )
    shutil.copy(FIXTURES / "phases.json", tmp_path / "phases.json")
    return tmp_path


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (Workout, BodyMeasurement, NutritionEntry, Phase, IngestionRun):
        await session.execute(model.__table__.delete())
    await session.commit()


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_run_ingests_and_records_success(
    session: AsyncSession, export_dir: Path
) -> None:
    run = await run_ingestion(
        session,
        discover_source(export_dir),
        kind="test",
        source_name="fixture",
    )

    assert run.status is IngestionStatus.SUCCESS
    assert run.finished_at is not None
    assert run.counts["body_measurements"] == 2
    assert run.counts["phases"] == 3
    assert await _count(session, BodyMeasurement) == 2
    assert await _count(session, Phase) == 3


async def test_second_run_creates_no_duplicates(
    session: AsyncSession, export_dir: Path
) -> None:
    """L'assertion centrale de tout ce plan."""
    source = discover_source(export_dir)

    await run_ingestion(session, source, kind="test", source_name="fixture")
    await run_ingestion(session, source, kind="test", source_name="fixture")

    assert await _count(session, BodyMeasurement) == 2
    assert await _count(session, Phase) == 3
    assert await _count(session, IngestionRun) == 2


async def test_failed_run_is_recorded_with_its_error(
    session: AsyncSession, tmp_path: Path
) -> None:
    broken = tmp_path / "com.samsung.health.weight.20260831162666.csv"
    broken.write_bytes(b"\xff\xfe pas de l'utf-8 valide")

    with pytest.raises(UnicodeError):
        await run_ingestion(
            session,
            discover_source(tmp_path),
            kind="test",
            source_name="cassé",
        )

    run = (await session.execute(select(IngestionRun))).scalars().one()
    assert run.status is IngestionStatus.FAILED
    assert run.error
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_discover_source.py tests/integration/test_pipeline.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.pipeline'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Créer `backend/app/ingestion/samsung/pipeline.py` :

```python
"""Orchestration d'une ingestion complète et journalisation du run."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.phases import read_phases
from app.ingestion.refresh import refresh_materialized_views
from app.ingestion.samsung.assembler import build_workout_bundle
from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_nutrition_entries,
    upsert_phases,
    upsert_workout_bundle,
)
from app.ingestion.samsung.mapper import map_body_measurement, map_nutrition_entry
from app.ingestion.samsung.parsers import read_samsung_csv
from app.models import IngestionRun, IngestionStatus

EXERCISE_DIR_NAME = "com.samsung.shealth.exercise"
_EXERCISE_CSV_RE = re.compile(r"\Acom\.samsung\.shealth\.exercise\.\d{14}\.csv\Z")

# Commiter tous les 100 paquets : 4 734 séances et leurs 2,8 M
# d'échantillons dans une seule transaction feraient exploser la mémoire.
COMMIT_EVERY = 100


@dataclass(frozen=True, slots=True)
class SamsungSource:
    weight_csv: Path | None = None
    food_csv: Path | None = None
    exercise_csv: Path | None = None
    exercise_dir: Path | None = None
    phases_json: Path | None = None


def _latest(root: Path, pattern: str) -> Path | None:
    """Le nom porte un horodatage à 14 chiffres, l'ordre lexicographique
    est donc l'ordre chronologique."""
    matches = sorted(path for path in root.glob(pattern) if path.is_file())
    return matches[-1] if matches else None


def discover_source(root: Path) -> SamsungSource:
    exercise_candidates = sorted(
        path
        for path in root.glob("com.samsung.shealth.exercise.*.csv")
        if path.is_file() and _EXERCISE_CSV_RE.match(path.name)
    )
    exercise_dir = root / EXERCISE_DIR_NAME
    phases_json = root / "phases.json"
    return SamsungSource(
        weight_csv=_latest(root, "com.samsung.health.weight.*.csv"),
        food_csv=_latest(root, "com.samsung.health.food_intake.*.csv"),
        exercise_csv=exercise_candidates[-1] if exercise_candidates else None,
        exercise_dir=exercise_dir if exercise_dir.is_dir() else None,
        phases_json=phases_json if phases_json.is_file() else None,
    )


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

    counts: dict[str, int] = {}
    try:
        if source.weight_csv is not None:
            records = [
                record
                for record in (
                    map_body_measurement(row)
                    for row in read_samsung_csv(source.weight_csv)
                )
                if record is not None
            ]
            counts["body_measurements"] = await upsert_body_measurements(
                session, records
            )

        if source.food_csv is not None:
            entries = [
                entry
                for entry in (
                    map_nutrition_entry(row)
                    for row in read_samsung_csv(source.food_csv)
                )
                if entry is not None
            ]
            counts["nutrition_entries"] = await upsert_nutrition_entries(
                session, entries
            )

        if source.exercise_csv is not None and source.exercise_dir is not None:
            counts.update(
                await _ingest_workouts(
                    session, source.exercise_csv, source.exercise_dir
                )
            )

        if source.phases_json is not None:
            counts["phases"] = await upsert_phases(
                session, read_phases(source.phases_json)
            )

        await refresh_materialized_views(session, concurrently=False)
        run.status = IngestionStatus.SUCCESS
    except Exception as error:
        await session.rollback()
        run = await session.get(IngestionRun, run.id)
        run.status = IngestionStatus.FAILED
        run.error = f"{type(error).__name__}: {error}"
        raise
    finally:
        run.counts = counts
        run.finished_at = datetime.now(UTC)
        session.add(run)
        await session.commit()

    return run


async def _ingest_workouts(
    session: AsyncSession, exercise_csv: Path, exercise_dir: Path
) -> dict[str, int]:
    """Traite les séances une par une pour ne jamais tenir les 2,8 M
    d'échantillons en mémoire simultanément."""
    counts = {
        "workouts": 0,
        "samples": 0,
        "locations": 0,
        "swim_lengths": 0,
        "strength_sets": 0,
    }
    for row in read_samsung_csv(exercise_csv):
        bundle = build_workout_bundle(row, exercise_dir)
        if bundle is None:
            continue
        await upsert_workout_bundle(session, bundle)
        counts["workouts"] += 1
        counts["samples"] += len(bundle.samples)
        counts["locations"] += len(bundle.locations)
        counts["swim_lengths"] += len(bundle.swim_lengths)
        counts["strength_sets"] += len(bundle.strength_sets)
        if counts["workouts"] % COMMIT_EVERY == 0:
            await session.commit()
    await session.commit()
    return counts
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_discover_source.py tests/integration/test_pipeline.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Lancer toute la suite**

Run: `cd backend && uv run ruff check . && uv run pytest -v`
Expected: aucune erreur ruff, tous les tests PASS

- [ ] **Step 6: Commiter**

```bash
git add backend/app/ingestion/samsung/pipeline.py backend/tests
git commit -m "feat: add samsung ingestion pipeline with run tracking"
```

---

### Task 14: Migration des données réelles

**Files:**
- Create: `backend/scripts/migrate_legacy.py`
- Create: `backend/scripts/README.md`

**Interfaces:**
- Consumes: `discover_source`, `run_ingestion` (tâche 13) ;
  `app.db.session_factory` (tâche 4).
- Produces: rien que d'autres tâches consomment. Script jetable, pas une
  surface produit à maintenir.

Cette tâche valide tout le plan contre les données réelles. Les valeurs
attendues sont celles du tableau « Chiffres de référence » en tête de
document.

- [ ] **Step 1: Écrire le script**

Créer `backend/scripts/migrate_legacy.py` :

```python
"""Migration one-shot de l'export Samsung Health et de phases.json.

Script jetable : il réutilise le pipeline d'ingestion sans rien ajouter, et
n'est pas une fonctionnalité de l'application. Les données sources ne sont
jamais modifiées.

Usage :
    uv run python -m scripts.migrate_legacy /chemin/vers/export
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.db import session_factory
from app.ingestion.samsung.pipeline import discover_source, run_ingestion


async def main(root: Path) -> int:
    if not root.is_dir():
        print(f"Répertoire introuvable : {root}", file=sys.stderr)
        return 2

    source = discover_source(root)
    print(f"Export détecté dans {root}")
    for label, path in (
        ("mesures", source.weight_csv),
        ("alimentation", source.food_csv),
        ("séances", source.exercise_csv),
        ("JSON de séances", source.exercise_dir),
        ("phases", source.phases_json),
    ):
        print(f"  {label:<18} {path.name if path else 'absent'}")

    async with session_factory() as session:
        run = await run_ingestion(
            session, source, kind="migration", source_name=root.name
        )

    print(f"\nRun #{run.id} — {run.status}")
    for key, value in sorted(run.counts.items()):
        print(f"  {key:<18} {value:>9}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="répertoire de l'export")
    raise SystemExit(asyncio.run(main(parser.parse_args().root)))
```

Créer `backend/scripts/README.md` :

```markdown
# Scripts

## migrate_legacy.py

Charge un export Samsung Health et un `phases.json` existants dans la base.
Jetable : conservé pour pouvoir rejouer la migration initiale, pas destiné à
évoluer. L'ingestion courante passe par l'API.

```bash
cd backend
uv run python -m scripts.migrate_legacy /home/sedelpeuch/migration_body-analysis
```

Le script est idempotent : le relancer met à jour sans dupliquer.
```

- [ ] **Step 2: Lancer la migration sur les données réelles**

Run:
```bash
cd backend && uv run python -m scripts.migrate_legacy \
  /home/sedelpeuch/migration_body-analysis
```

Expected: `status success`, et des compteurs proches de :
`body_measurements 647`, `nutrition_entries 11855`, `workouts 4734`,
`phases 8`, `samples` de l'ordre de 2,8 M, `locations` de l'ordre de 590 k,
`strength_sets` de l'ordre de 3 000.

L'opération lit 452 Mo de JSON : compter plusieurs minutes.

- [ ] **Step 3: Vérifier les chiffres en base**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT 'body_measurement' AS t, count(*) FROM body_measurement
UNION ALL SELECT 'nutrition_entry', count(*) FROM nutrition_entry
UNION ALL SELECT 'workout', count(*) FROM workout
UNION ALL SELECT 'workout_sample', count(*) FROM workout_sample
UNION ALL SELECT 'workout_location', count(*) FROM workout_location
UNION ALL SELECT 'swim_length', count(*) FROM swim_length
UNION ALL SELECT 'strength_set', count(*) FROM strength_set
UNION ALL SELECT 'phase', count(*) FROM phase;"
```
Expected: les ordres de grandeur du tableau de référence.

- [ ] **Step 4: Vérifier la correction du bug de classification**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT sport, count(*) FROM workout GROUP BY sport ORDER BY 2 DESC;"
```
Expected: **330 séances en Natation**, et non 261. C'est la preuve que les
69 séances autrefois classées en Musculation sont revenues au bon sport.

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT count(*) FROM workout WHERE sport_type = 14001 AND sport <> 'Natation';"
```
Expected: `0`

- [ ] **Step 5: Vérifier l'idempotence sur les données réelles**

Run:
```bash
cd backend && uv run python -m scripts.migrate_legacy \
  /home/sedelpeuch/migration_body-analysis
```

Puis relancer la requête de comptage de l'étape 3.
Expected: **exactement les mêmes nombres.** Un seul écart signale une faille
dans l'idempotence, à corriger avant de continuer.

- [ ] **Step 6: Vérifier les données jusqu'ici invisibles**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT
  count(*) FILTER (WHERE body_fat_mass_kg IS NOT NULL) AS masse_grasse_kg,
  count(*) FILTER (WHERE fat_free_mass_kg IS NOT NULL) AS masse_maigre_kg,
  count(*) FILTER (WHERE basal_metabolic_rate_kcal IS NOT NULL) AS metabolisme,
  count(*) FILTER (WHERE total_body_water_kg IS NOT NULL) AS eau
FROM body_measurement;"
```
Expected: 638, 387, 638, 638 — les colonnes que l'application Streamlit ne
lisait pas.

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT count(DISTINCT workout_id) FROM strength_set;"
```
Expected: de l'ordre de 1 531.

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT count(*) FROM workout WHERE resting_hr IS NOT NULL;"
```
Expected: de l'ordre de 2 509.

- [ ] **Step 7: Commiter**

```bash
git add backend/scripts
git commit -m "feat: add one-shot legacy migration script"
```

---

## Definition of done du plan 1

- [ ] `docker compose ps` montre `db` et `minio` en `healthy`.
- [ ] `cd backend && uv run ruff check .` ne signale rien.
- [ ] `cd backend && uv run pytest` passe intégralement.
- [ ] `uv run alembic upgrade head` puis `alembic downgrade base` puis
  `upgrade head` s'exécutent sans erreur — les migrations sont réversibles.
- [ ] Les données réelles sont en base, aux ordres de grandeur du tableau de
  référence.
- [ ] Une seconde migration ne change aucun compteur.
- [ ] `SELECT count(*) FROM workout WHERE sport_type = 14001 AND sport <> 'Natation'`
  renvoie `0`.

## Auto-revue

**Couverture de la spec.** Le plan couvre les sections 2 (contraintes),
4.1 à 4.13 (modèle de données complet, vues matérialisées, valeurs
manquantes) et 7 (flux d'ingestion, fichiers ignorés, migration initiale) de
la spec. Les sections 5 (analyses), 6 (API), 8 (front), 9 (tests de la
couche service) et 11 (déploiement de l'API et du web) sont hors périmètre
de ce plan et relèvent des plans 2 à 4. La table `photo` est créée ici pour
que le schéma tienne en une migration, mais sa logique de stockage appartient
au plan 3 — c'est délibéré et signalé dans le modèle.

**Placeholders.** Deux valeurs ne peuvent pas être connues à l'avance et
sont explicitement nommées comme telles : les identifiants de révision
Alembic (`<hash généré>`, `<hash de la migration initiale>`), qui sont
générés par `alembic revision`. Aucun autre TBD.

**Cohérence des types.** `resolve_sport` est déclarée avec `has_sets` en
argument nommé obligatoire en tâche 3 et appelée ainsi en tâche 7.
`WorkoutBundle` est produit en tâche 9 et consommé en tâches 11 et 13 avec
les mêmes noms de champs. `refresh_materialized_views` accepte
`concurrently` en tâche 12 et est appelée avec `concurrently=False` en
tâche 13, cohérent avec le fait qu'une vue jamais peuplée refuse le
rafraîchissement concurrent. La fixture `engine` des tests d'intégration est
définie en tâche 11 sur `create_all` puis remplacée en tâche 12 par Alembic ;
le remplacement est explicite et motivé par l'arrivée des vues.
