# Ingestion étendue — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingérer, de façon idempotente et dans de nouvelles tables portant
leur propre migration Alembic, les dimensions de l'export Samsung Health
réel que le plan 1 (socle et ingestion) laisse volontairement de côté :
macronutriments et micronutriments par repas, dépense énergétique
quotidienne détaillée, sommeil et ses phases, variabilité cardiaque,
fréquence cardiaque et stress continus, activité et pas quotidiens,
saturation en oxygène, fréquence respiratoire et température cutanée
nocturnes.

**Architecture:** Ce plan prolonge les quatre étages posés par le plan 1
sans les rouvrir : de nouveaux modules de mapping par famille de données
produisent des dataclasses de domaine, le loader existant les upserte par
lots sur `source_uuid`, et le pipeline existant (`discover_source`,
`run_ingestion`) est étendu pour les découvrir et les charger dans le même
run. Aucun endpoint, aucune couche d'analyse : ce plan s'arrête à la base de
données.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 asynchrone, asyncpg,
Alembic, pydantic-settings, uv, pytest, PostgreSQL 17.

**Spec:** `docs/superpowers/specs/2026-09-02-migration-fastapi-react-design.md`,
section 5.8.

## Global Constraints

- Python `>=3.13`. Aucun code compatible 3.11 requis.
- Planchers de dépendances, jamais de versions figées. Aucune nouvelle
  dépendance n'est nécessaire à ce plan : tout repose sur `sqlalchemy`,
  `alembic`, `asyncpg` déjà présents.
- **Aucun identifiant en dur dans le code.** `BA_DATABASE_URL`,
  `BA_MINIO_ACCESS_KEY` et `BA_MINIO_SECRET_KEY` restent obligatoires et
  sans valeur par défaut.
- **Une valeur absente est `None`, jamais `0` ni `NaN`**, de la lecture du
  CSV jusqu'en base. Une courbe trouée est honnête, une courbe qui plonge à
  zéro est un mensonge.
- **Tous les horodatages sont conservés avec leur fuseau** (`TIMESTAMPTZ`),
  sauf les trois colonnes `day` qui représentent un jour calendaire et non
  un instant (justifié tâche 3 et tâche 7 : ces exports Samsung n'ont pas de
  colonne `time_offset`, seul le composant date de `day_time` est fiable).
- Toute table de faits porte un `source_uuid` unique et non nul, inséré en
  `ON CONFLICT (source_uuid) DO UPDATE`. Un ré-import ne crée jamais de
  doublon.
- Le code, les noms de tables et de colonnes, les messages de commit sont en
  anglais. Les commentaires et la documentation sont en français.
- Les données réelles de référence sont dans
  `/home/sedelpeuch/Téléchargements/samsunghealth_sedelpeuch_20260831162666 (2)`
  et ne sont **jamais modifiées** par le code : elles sont lues seulement.
  Le chemin contient une espace et des parenthèses : toujours le citer.
- Piège Alembic : l'autogenerate n'émet jamais `DROP TYPE` pour les enums
  natifs ; ce plan n'introduit aucun enum, donc aucune migration ici n'a
  besoin de ce correctif.
- Les lignes filles d'un enregistrement ne sont remplacées que si l'import
  en apporte de nouvelles ; un fichier JSON absent ne déclenche jamais de
  suppression (même principe que `upsert_workout_bundle`, tâche 11 du
  plan 1).

## Chiffres de référence des données réelles

Mesurés directement sur l'export réel (§ ci-dessous, colonnes vérifiées en
lisant les en-têtes en `utf-8-sig`, deuxième ligne de chaque CSV).

| Source CSV | Lignes | Contenu ingéré |
| --- | --- | --- |
| `com.samsung.health.nutrition` | 3 637 (747 jours) | `protein`, `total_fat`, `saturated_fat`, `trans_fat`, `monosaturated_fat`, `polysaturated_fat`, `dietary_fiber`, `sugar`, `added_sugar`, `cholesterol`, `sodium`, `potassium`, `calcium`, `iron`, `vitamin_a`, `vitamin_c`, `vitamin_d`, `carbohydrate`, `calorie`, `meal_type`, `title`, `start_time`, `time_offset`, `datauuid` |
| `com.samsung.shealth.calories_burned.details` | 2 877 | `rest_calorie`, `active_calorie`, `tef_calorie`, `active_time`, `day_time`, `total_exercise_calories`, `datauuid` (colonnes préfixées `com.samsung.shealth.calories_burned.`, sauf `total_exercise_calories` et `extra_data`) |
| `com.samsung.shealth.sleep` | 1 087 nuits | `sleep_efficiency_with_latency`, `efficiency`, `physical_recovery`, `mental_recovery`, `deep_score`, `rem_score`, `wake_score`, `nap_score`, `latency_score`, `sleep_latency`, `total_rem_duration`, `total_light_duration`, `sleep_type`, `has_sleep_data`, `original_wake_up_time`, `sleep_score`, `sleep_duration` (colonnes `start_time`/`end_time`/`time_offset`/`datauuid` préfixées `com.samsung.health.sleep.`) |
| `com.samsung.health.sleep_stage` | 51 476 phases, 664 nuits distinctes | `sleep_id`, `stage`, `start_time`, `end_time`, `time_offset`, `datauuid` |
| `com.samsung.health.hrv` | 6 225 | `start_time`, `end_time`, `time_offset`, `binning_data`, `datauuid` — le fichier JSON est lu pour calculer `avg_sdnn`/`avg_rmssd` |
| `com.samsung.shealth.tracker.heart_rate` | 14 929 | `heart_rate`, `min`, `max`, `heart_beat_count`, `start_time`, `end_time`, `time_offset`, `datauuid` (préfixées `com.samsung.health.heart_rate.`), plus `tag_id` |
| `com.samsung.shealth.stress` | 8 678 | `score`, `min`, `max`, `start_time`, `end_time`, `time_offset`, `tag_id`, `datauuid` |
| `com.samsung.shealth.activity.day_summary` | 2 864 | `step_count`, `active_time`, `calorie`, `distance`, `floor_count`, `score`, `exercise_time`, `run_time`, `walk_time`, `longest_active_time`, `move_hourly_count`, `day_time`, `datauuid` |
| `com.samsung.shealth.step_daily_trend` | 6 318 | `count`, `distance`, `calorie`, `speed`, `source_type`, `day_time`, `datauuid` |
| `com.samsung.shealth.tracker.oxygen_saturation` | 664 | `spo2`, `heart_rate`, `start_time`, `end_time`, `time_offset`, `datauuid` (préfixées `com.samsung.health.oxygen_saturation.`) |
| `com.samsung.health.respiratory_rate` | 671 | `average`, `lower_limit`, `upper_limit`, `start_time`, `end_time`, `time_offset`, `datauuid` |
| `com.samsung.health.skin_temperature` | 664 | `temperature`, `min`, `max`, `baseline`, `start_time`, `end_time`, `time_offset`, `datauuid` |

**Écarts corrigés par rapport à l'inventaire de départ**, vérifiés colonne
par colonne sur l'export réel :

- `carbohydrate` est remplie à 100 % dans `nutrition` (3 637/3 637) alors
  qu'elle n'était pas listée : elle est ajoutée. À l'inverse, `magnesium`,
  `vitamin_b12`, `zinc`, `vitamin_e`, `vitamin_k`, `phosphorus`,
  `calories_from_fat`, `polyunsaturated_fat` (non abrégé, distincte de
  `polysaturated_fat` qui, elle, est la colonne réellement peuplée) et une
  douzaine d'autres micronutriments sont à 0 valeur sur 3 637 lignes : ils
  ne sont pas ingérés.
- La saturation en oxygène pertinente est `com.samsung.shealth.tracker.oxygen_saturation`
  (664 lignes, colonne `spo2` peuplée), **pas**
  `com.samsung.health.oxygen_saturation.raw` (38 lignes seulement, aucune
  colonne agrégée, valeurs de `binning_data` proches de zéro donc
  inexploitables). C'est la source retenue.
- `com.samsung.shealth.tracker.heart_rate` a 13 828 lignes avec
  `binning_data` renseigné, non 9 945 comme l'inventaire de départ
  l'indiquait. Sans conséquence sur ce plan puisque le binning n'est pas
  ingéré pour cette famille (cf. décisions ci-dessous).
- Sur les 51 476 segments de `sleep_stage`, seuls 664 nuits distinctes sur
  1 087 ont des segments, et 7 segments référencent un `sleep_id` absent de
  `sleep.csv`. `sleep_stage.sleep_source_uuid` n'est donc pas une clé
  étrangère stricte (cf. tâche 1).

## Décisions actées

**Binning JSON : ingéré seulement quand la ligne CSV ne porte aucun
agrégat.**

| Famille | Agrégat déjà dans le CSV ? | Décision |
| --- | --- | --- |
| HRV | Non — `sdnn`/`rmssd` n'existent que dans `binning_data` | Le fichier JSON est ouvert à l'ingestion pour calculer une moyenne `avg_sdnn`/`avg_rmssd` et un `sample_count` **par relevé** (6 225 lignes en sortie, pas d'explosion en séries) |
| Fréquence cardiaque continue | Oui — `heart_rate`, `min`, `max`, `heart_beat_count` | Binning ignoré : il ne détaille qu'en sous-fenêtres d'une minute à l'intérieur d'un relevé déjà fin (14 929 relevés sur 21 mois) |
| Stress | Oui — `score`, `min`, `max` | Binning ignoré, même raison |
| Pas quotidiens (`step_daily_trend`) | Oui — `count`, `distance`, `calorie`, `speed` par jour | Binning ignoré : il détaille en 24 tranches horaires, ce qui multiplierait le volume par 24 pour un profil intra-journée qui n'est demandé par aucune analyse de la spec section 5 ; à revisiter dans un plan dédié si besoin |
| Saturation en oxygène, fréquence respiratoire, température cutanée | Oui — `spo2`/`heart_rate`, `average`/`lower_limit`/`upper_limit`, `temperature`/`min`/`max`/`baseline` | Binning ignoré, l'agrégat du CSV suffit |

**Pas de fusion `nutrition` / `food_intake`.** Vérification faite sur les
en-têtes des deux CSV : `nutrition.csv` n'a ni `food_info_id` ni aucune
colonne en commun avec `food_intake.csv` autre que `start_time`/`meal_type`,
qui ne forment pas une clé fiable (plusieurs entrées de chaque fichier
partagent la même minute et le même repas). Les deux tables restent
distinctes, comme demandé, et ne sont reliées par aucune clé.

**Vues matérialisées ajoutées : trois, pas une par famille.**
`energy_expenditure`, `daily_activity` et `step_daily_trend` sont déjà à
grain quotidien (une ligne par jour) : leur ajouter une vue matérialisée ne
ferait qu'en dupliquer le contenu. Les familles qui ne sont pas à grain
quotidien reçoivent chacune leur vue :

- `mv_daily_nutrition_detail` — sommes de macro/micronutriments par jour,
  complète `mv_daily_nutrition` existante (qui ne compte que les calories de
  `food_intake`).
- `mv_daily_sleep` — une ligne par nuit, rattachée à la date du réveil
  (`ended_at`), avec efficacité et scores de récupération.
- `mv_daily_vitals` — moyenne journalière de fréquence cardiaque, de score
  de stress et de VFC (`avg_sdnn`), les trois partageant le même grain
  « relevé continu dans la journée ».

**`sleep_stage` sans contrainte de clé étrangère stricte.** 7 segments sur
51 476 référencent un `sleep_id` absent de `sleep.csv`. Une `ForeignKey`
ferait échouer leur insertion ; `sleep_source_uuid` reste un `Text` indexé,
non contraint, à l'image de la tolérance déjà pratiquée par
`upsert_workout_bundle` pour les données annexes optionnelles.

**Famille écartée : `com.samsung.health.oxygen_saturation.raw`.** 38
lignes, aucune colonne agrégée exploitable, valeurs de binning dégénérées
(proches de zéro). Le rapport coût/valeur est mauvais ; elle est
définitivement écartée au profit de `tracker.oxygen_saturation`.

**Unités non documentées conservées brutes.** `sleep_latency`,
`total_rem_duration`, `total_light_duration`, `sleep_duration` et
`has_sleep_data` n'ont pas d'unité ni de sémantique de type booléen
confirmée dans l'export (`has_sleep_data` prend les valeurs `0`, `-1` et
vide, pas `0`/`1`). Ils sont stockés en entier brut plutôt que sur une
hypothèse de conversion qui serait fausse ; leur interprétation revient à
l'analyse (plan 2).

## Structure des fichiers

```
backend/
  app/
    models/
      nutrition_detail.py           NutritionDetail
      energy.py                     EnergyExpenditure
      sleep.py                      SleepSession, SleepStage
      vitals.py                     HrvReading, HeartRateReading, StressReading,
                                     RespiratoryRateReading, SkinTemperatureReading,
                                     OxygenSaturationReading
      activity.py                   DailyActivity, StepDailyTrend
    ingestion/
      samsung/
        records.py                  étendu : une dataclass par nouvelle table
        nutrition_detail.py         map_nutrition_detail
        energy.py                   map_energy_expenditure
        sleep.py                    map_sleep_session, map_sleep_stage
        vitals.py                   map_hrv_reading (lit le binning), map_heart_rate_reading,
                                     map_stress_reading, map_respiratory_rate_reading,
                                     map_skin_temperature_reading, map_oxygen_saturation_reading
        activity.py                 map_daily_activity, map_step_daily_trend
        loader.py                   étendu : un upsert_* par nouvelle table
        pipeline.py                 étendu : SamsungSource et run_ingestion
      refresh.py                    étendu : DAILY_VIEWS à six entrées
  migrations/versions/              deux nouvelles révisions (tables, puis vues)
  tests/
    fixtures/samsung/               un CSV et un JSON de binning par nouvelle famille
    unit/                           un test par nouveau mapper
    integration/                    loader, pipeline étendu, vues
```

Découpage assumé : un module d'ingestion par famille de données, comme
demandé, parce que `mapper.py` (plan 1) est déjà à sa taille plafond et que
chaque famille a ses propres colonnes et sa propre logique de binning. Les
modèles suivent le même découpage plutôt que d'être regroupés dans un seul
fichier : contrairement à `workout.py` (plan 1), ces tables ne partagent
aucune décision de schéma commune, seulement le fait d'être de nouvelles
dimensions.

---

### Task 1: Modèles et migration des nouvelles tables

**Files:**
- Create: `backend/app/models/nutrition_detail.py`
- Create: `backend/app/models/energy.py`
- Create: `backend/app/models/sleep.py`
- Create: `backend/app/models/vitals.py`
- Create: `backend/app/models/activity.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/<hash>_extended_ingestion_tables.py`
- Create: `backend/tests/unit/test_extended_models_metadata.py`

**Interfaces:**
- Consumes: `app.models.base.Base`, `TimestampMixin` (plan 1, tâche 4).
- Produces : les classes `NutritionDetail`, `EnergyExpenditure`,
  `SleepSession`, `SleepStage`, `HrvReading`, `HeartRateReading`,
  `StressReading`, `RespiratoryRateReading`, `SkinTemperatureReading`,
  `OxygenSaturationReading`, `DailyActivity`, `StepDailyTrend`, toutes
  exportées par `app.models`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/unit/test_extended_models_metadata.py` :

```python
"""Vérifie la forme des tables de la couche ingestion étendue."""

from app.models import Base

NEW_TABLES = {
    "nutrition_detail",
    "energy_expenditure",
    "sleep_session",
    "sleep_stage",
    "hrv_reading",
    "heart_rate_reading",
    "stress_reading",
    "respiratory_rate_reading",
    "skin_temperature_reading",
    "oxygen_saturation_reading",
    "daily_activity",
    "step_daily_trend",
}


def test_new_tables_are_registered() -> None:
    assert NEW_TABLES.issubset(set(Base.metadata.tables))


def test_all_new_fact_tables_have_unique_source_uuid() -> None:
    for name in NEW_TABLES:
        column = Base.metadata.tables[name].c["source_uuid"]
        assert column.unique is True
        assert column.nullable is False


def test_instant_columns_are_timezone_aware() -> None:
    checks = [
        ("nutrition_detail", "consumed_at"),
        ("sleep_session", "started_at"),
        ("sleep_stage", "started_at"),
        ("hrv_reading", "started_at"),
        ("heart_rate_reading", "started_at"),
        ("stress_reading", "started_at"),
        ("respiratory_rate_reading", "started_at"),
        ("skin_temperature_reading", "started_at"),
        ("oxygen_saturation_reading", "started_at"),
    ]
    for table, column in checks:
        assert Base.metadata.tables[table].c[column].type.timezone is True


def test_day_columns_are_plain_dates() -> None:
    """day_time n'a pas de time_offset dans ces trois exports : seule la
    date est fiable, un TIMESTAMPTZ inventerait un fuseau."""
    for table in ("energy_expenditure", "daily_activity", "step_daily_trend"):
        column = Base.metadata.tables[table].c["day"]
        assert column.type.__class__.__name__ == "Date"


def test_sleep_stage_has_no_hard_foreign_key() -> None:
    """7 segments réels référencent une nuit absente de sleep_session."""
    column = Base.metadata.tables["sleep_stage"].c["sleep_source_uuid"]
    assert not column.foreign_keys
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/unit/test_extended_models_metadata.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.models.nutrition_detail'`

- [ ] **Step 3: Écrire les modèles**

Créer `backend/app/models/nutrition_detail.py` :

```python
"""Macronutriments et micronutriments par repas.

Source distincte de food_intake : aucune clé commune fiable ne relie les
deux (vérifié sur les en-têtes réelles), elles restent deux tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NutritionDetail(Base, TimestampMixin):
    __tablename__ = "nutrition_detail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    meal_type: Mapped[int | None] = mapped_column(SmallInteger, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")

    calories: Mapped[float | None] = mapped_column(Double)
    protein: Mapped[float | None] = mapped_column(Double)
    total_fat: Mapped[float | None] = mapped_column(Double)
    saturated_fat: Mapped[float | None] = mapped_column(Double)
    trans_fat: Mapped[float | None] = mapped_column(Double)
    monosaturated_fat: Mapped[float | None] = mapped_column(Double)
    polysaturated_fat: Mapped[float | None] = mapped_column(Double)
    carbohydrate: Mapped[float | None] = mapped_column(Double)
    dietary_fiber: Mapped[float | None] = mapped_column(Double)
    sugar: Mapped[float | None] = mapped_column(Double)
    added_sugar: Mapped[float | None] = mapped_column(Double)
    cholesterol: Mapped[float | None] = mapped_column(Double)
    sodium: Mapped[float | None] = mapped_column(Double)
    potassium: Mapped[float | None] = mapped_column(Double)
    calcium: Mapped[float | None] = mapped_column(Double)
    iron: Mapped[float | None] = mapped_column(Double)
    vitamin_a: Mapped[float | None] = mapped_column(Double)
    vitamin_c: Mapped[float | None] = mapped_column(Double)
    vitamin_d: Mapped[float | None] = mapped_column(Double)
```

Créer `backend/app/models/energy.py` :

```python
"""Décomposition quotidienne de la dépense énergétique.

day est une date calendaire, pas un instant : com.samsung.shealth.calories_
burned.details ne porte aucune colonne time_offset, seule sa partie date est
fiable.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Double, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EnergyExpenditure(Base, TimestampMixin):
    __tablename__ = "energy_expenditure"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    rest_calorie: Mapped[float | None] = mapped_column(Double)
    active_calorie: Mapped[float | None] = mapped_column(Double)
    tef_calorie: Mapped[float | None] = mapped_column(Double)
    active_time_ms: Mapped[int | None] = mapped_column(Integer)
    total_exercise_calories: Mapped[float | None] = mapped_column(Double)
```

Créer `backend/app/models/sleep.py` :

```python
"""Sommeil : résumé de nuit et détail par phase.

sleep_stage n'a pas de clé étrangère stricte vers sleep_session : 7
segments réels référencent une nuit absente de l'export sleep. sleep_
source_uuid reste un texte indexé, non contraint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SleepSession(Base, TimestampMixin):
    __tablename__ = "sleep_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_wake_up_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    efficiency: Mapped[float | None] = mapped_column(Double)
    efficiency_with_latency: Mapped[float | None] = mapped_column(Double)
    physical_recovery: Mapped[int | None] = mapped_column(Integer)
    mental_recovery: Mapped[int | None] = mapped_column(Integer)
    deep_score: Mapped[int | None] = mapped_column(Integer)
    rem_score: Mapped[int | None] = mapped_column(Integer)
    wake_score: Mapped[int | None] = mapped_column(Integer)
    nap_score: Mapped[int | None] = mapped_column(Integer)
    latency_score: Mapped[int | None] = mapped_column(Integer)
    sleep_latency: Mapped[int | None] = mapped_column(Integer)
    total_rem_duration: Mapped[int | None] = mapped_column(Integer)
    total_light_duration: Mapped[int | None] = mapped_column(Integer)
    sleep_duration: Mapped[int | None] = mapped_column(Integer)
    sleep_score: Mapped[int | None] = mapped_column(Integer)
    # Code brut Samsung, pas une valeur booléenne fiable : l'export porte
    # 0, -1 et vide, jamais 1/0 propre.
    has_sleep_data: Mapped[int | None] = mapped_column(SmallInteger)
    sleep_type: Mapped[int | None] = mapped_column(SmallInteger)


class SleepStage(Base, TimestampMixin):
    __tablename__ = "sleep_stage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    sleep_source_uuid: Mapped[str | None] = mapped_column(Text, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage: Mapped[int | None] = mapped_column(Integer)
```

Créer `backend/app/models/vitals.py` :

```python
"""Signaux continus ou nocturnes dont l'agrégat vit déjà dans la ligne CSV.

Seul hrv_reading dérive ses valeurs d'un fichier JSON annexe (avg_sdnn,
avg_rmssd) : la ligne CSV de com.samsung.health.hrv ne porte aucune mesure,
seulement une référence de fichier.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class HrvReading(Base, TimestampMixin):
    __tablename__ = "hrv_reading"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avg_sdnn: Mapped[float | None] = mapped_column(Double)
    avg_rmssd: Mapped[float | None] = mapped_column(Double)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class HeartRateReading(Base, TimestampMixin):
    __tablename__ = "heart_rate_reading"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mean_heart_rate: Mapped[float | None] = mapped_column(Double)
    min_heart_rate: Mapped[float | None] = mapped_column(Double)
    max_heart_rate: Mapped[float | None] = mapped_column(Double)
    heart_beat_count: Mapped[int | None] = mapped_column(Integer)
    tag_id: Mapped[int | None] = mapped_column(Integer)


class StressReading(Base, TimestampMixin):
    __tablename__ = "stress_reading"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[float | None] = mapped_column(Double)
    min_score: Mapped[float | None] = mapped_column(Double)
    max_score: Mapped[float | None] = mapped_column(Double)
    tag_id: Mapped[int | None] = mapped_column(Integer)


class RespiratoryRateReading(Base, TimestampMixin):
    __tablename__ = "respiratory_rate_reading"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    average: Mapped[float | None] = mapped_column(Double)
    lower_limit: Mapped[float | None] = mapped_column(Double)
    upper_limit: Mapped[float | None] = mapped_column(Double)


class SkinTemperatureReading(Base, TimestampMixin):
    __tablename__ = "skin_temperature_reading"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    temperature: Mapped[float | None] = mapped_column(Double)
    min_temperature: Mapped[float | None] = mapped_column(Double)
    max_temperature: Mapped[float | None] = mapped_column(Double)
    baseline: Mapped[float | None] = mapped_column(Double)


class OxygenSaturationReading(Base, TimestampMixin):
    __tablename__ = "oxygen_saturation_reading"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    spo2: Mapped[float | None] = mapped_column(Double)
    heart_rate: Mapped[float | None] = mapped_column(Double)
    tag_id: Mapped[int | None] = mapped_column(SmallInteger)
```

Créer `backend/app/models/activity.py` :

```python
"""Activité et pas quotidiens.

day est une date calendaire : ni activity.day_summary ni step_daily_trend
n'ont de colonne time_offset, day_time est déjà une minuit locale.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Double, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyActivity(Base, TimestampMixin):
    __tablename__ = "daily_activity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    step_count: Mapped[int | None] = mapped_column(Integer)
    active_time_ms: Mapped[int | None] = mapped_column(Integer)
    calorie: Mapped[float | None] = mapped_column(Double)
    distance_m: Mapped[float | None] = mapped_column(Double)
    floor_count: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer)
    exercise_time_ms: Mapped[int | None] = mapped_column(Integer)
    run_time_ms: Mapped[int | None] = mapped_column(Integer)
    walk_time_ms: Mapped[int | None] = mapped_column(Integer)
    longest_active_time_ms: Mapped[int | None] = mapped_column(Integer)
    move_hourly_count: Mapped[int | None] = mapped_column(Integer)


class StepDailyTrend(Base, TimestampMixin):
    __tablename__ = "step_daily_trend"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    count: Mapped[int | None] = mapped_column(Integer)
    distance_m: Mapped[float | None] = mapped_column(Double)
    calorie: Mapped[float | None] = mapped_column(Double)
    speed: Mapped[float | None] = mapped_column(Double)
    source_type: Mapped[int | None] = mapped_column(SmallInteger)
```

Mettre à jour `backend/app/models/__init__.py` :

```python
"""Import de tous les modèles pour peupler Base.metadata."""

from app.models.activity import DailyActivity, StepDailyTrend
from app.models.base import Base
from app.models.body import BodyMeasurement
from app.models.energy import EnergyExpenditure
from app.models.ingestion import IngestionRun, IngestionStatus
from app.models.nutrition import NutritionEntry
from app.models.nutrition_detail import NutritionDetail
from app.models.phase import Phase, PhaseKind
from app.models.photo import Photo
from app.models.sleep import SleepSession, SleepStage
from app.models.vitals import (
    HeartRateReading,
    HrvReading,
    OxygenSaturationReading,
    RespiratoryRateReading,
    SkinTemperatureReading,
    StressReading,
)
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
    "DailyActivity",
    "EnergyExpenditure",
    "HeartRateReading",
    "HrvReading",
    "IngestionRun",
    "IngestionStatus",
    "NutritionDetail",
    "NutritionEntry",
    "OxygenSaturationReading",
    "Phase",
    "PhaseKind",
    "Photo",
    "RespiratoryRateReading",
    "SkinTemperatureReading",
    "SleepSession",
    "SleepStage",
    "StepDailyTrend",
    "StrengthSet",
    "StressReading",
    "SwimLength",
    "Workout",
    "WorkoutExtra",
    "WorkoutLocation",
    "WorkoutSample",
]
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `cd backend && uv run pytest tests/unit/test_extended_models_metadata.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Générer et adapter la migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "extended ingestion tables"`
Expected: un fichier créé dans `migrations/versions/`, avec
`down_revision = "1717e96d7222"` (la révision des vues quotidiennes du
plan 1, tête actuelle).

Vérifier dans le fichier généré que les douze `op.create_table(...)`
correspondent aux douze modèles ci-dessus, avec leurs `UniqueConstraint`
sur `source_uuid`. Vérifier aussi que `downgrade()` fait bien les
`op.drop_table(...)` dans l'ordre inverse ; l'autogenerate de SQLAlchemy
2.0 le fait correctement pour des tables sans contrainte croisée entre
elles, ce qui est le cas ici (aucune `ForeignKey` dans ce plan).

- [ ] **Step 6: Appliquer la migration et vérifier le schéma**

Run: `cd backend && uv run alembic upgrade head`
Expected: `Running upgrade 1717e96d7222 -> <hash>, extended ingestion tables`

Run: `docker compose exec db psql -U body -d body_analysis -c "\dt"`
Expected: les 23 tables (11 du plan 1 + 12 de ce plan) plus
`alembic_version`.

- [ ] **Step 7: Vérifier la réversibilité**

Run: `cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head`
Expected: aucune erreur, les douze tables réapparaissent.

- [ ] **Step 8: Commiter**

```bash
git add backend/app/models backend/migrations/versions backend/tests/unit/test_extended_models_metadata.py
git commit -m "feat: add models and migration for extended ingestion tables"
```

---

### Task 2: Ingestion de la nutrition granulaire

**Files:**
- Modify: `backend/app/ingestion/samsung/records.py`
- Create: `backend/app/ingestion/samsung/nutrition_detail.py`
- Modify: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/fixtures/samsung/nutrition_sample.csv`
- Create: `backend/tests/unit/test_nutrition_detail_mapper.py`
- Create: `backend/tests/integration/test_extended_loader.py` (section
  nutrition ; les autres familles y ajoutent leurs tests dans les tâches
  suivantes)

**Interfaces:**
- Consumes: `parse_float`, `parse_int`, `parse_aware_datetime`,
  `read_samsung_csv` (plan 1, tâche 2) ; `NutritionDetail` (tâche 1).
- Produces:
  - `NutritionDetailRecord` (dataclass, `app.ingestion.samsung.records`)
  - `map_nutrition_detail(row: dict[str, str]) -> NutritionDetailRecord | None`
  - `upsert_nutrition_details(session, records: Sequence[NutritionDetailRecord]) -> int`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/nutrition_sample.csv` :

```csv
com.samsung.health.nutrition,7006003,6
protein,total_fat,saturated_fat,trans_fat,monosaturated_fat,polysaturated_fat,carbohydrate,dietary_fiber,sugar,added_sugar,cholesterol,sodium,potassium,calcium,iron,vitamin_a,vitamin_c,vitamin_d,calorie,meal_type,title,start_time,time_offset,datauuid
24.4,12.3,2.2,0.0,2.8,0.3,46.2,5.5,14.7,0.0,56.0,1975.0,39.0,23.8,,8.7,0.0,0.0,651.0,100002,Déjeuner,2024-08-14 15:35:32.249,UTC+0200,cc453be7-2248-423a-a4a9-3b7e2380a4d7
,,,,,,,,,,,,,,,,,,,100005,,2024-08-14 20:10:00.000,UTC+0200,
```

Créer `backend/tests/unit/test_nutrition_detail_mapper.py` :

```python
"""Tests du mapping des repas de com.samsung.health.nutrition."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ingestion.samsung.nutrition_detail import map_nutrition_detail
from app.ingestion.samsung.parsers import read_samsung_csv

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"


def test_maps_a_complete_row() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "nutrition_sample.csv")))

    record = map_nutrition_detail(row)

    assert record is not None
    assert record.source_uuid == "cc453be7-2248-423a-a4a9-3b7e2380a4d7"
    assert record.consumed_at == datetime(
        2024, 8, 14, 15, 35, 32, tzinfo=timezone(timedelta(hours=2))
    )
    assert record.meal_type == 100002
    assert record.title == "Déjeuner"
    assert record.protein == 24.4
    assert record.carbohydrate == 46.2
    assert record.vitamin_a is None
    assert record.calories == 651.0


def test_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "nutrition_sample.csv"))

    assert map_nutrition_detail(rows[1]) is None
```

Ajouter à `backend/tests/integration/test_extended_loader.py` :

```python
"""Tests d'intégration du loader pour les tables de l'ingestion étendue."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.loader import upsert_nutrition_details
from app.ingestion.samsung.records import NutritionDetailRecord
from app.models import NutritionDetail


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    await session.execute(NutritionDetail.__table__.delete())
    await session.commit()


async def _count(session: AsyncSession) -> int:
    return (
        await session.execute(select(func.count()).select_from(NutritionDetail))
    ).scalar_one()


async def test_upsert_nutrition_details_is_idempotent(session: AsyncSession) -> None:
    record = NutritionDetailRecord(
        source_uuid="meal-1",
        consumed_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
        title="Petit-déjeuner",
        protein=20.0,
    )

    await upsert_nutrition_details(session, [record])
    await upsert_nutrition_details(session, [record])

    assert await _count(session) == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_nutrition_detail_mapper.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.nutrition_detail'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/records.py`, après
`NutritionEntryRecord` :

```python
@dataclass(frozen=True, slots=True)
class NutritionDetailRecord:
    source_uuid: str
    consumed_at: datetime
    meal_type: int | None = None
    title: str = ""
    calories: float | None = None
    protein: float | None = None
    total_fat: float | None = None
    saturated_fat: float | None = None
    trans_fat: float | None = None
    monosaturated_fat: float | None = None
    polysaturated_fat: float | None = None
    carbohydrate: float | None = None
    dietary_fiber: float | None = None
    sugar: float | None = None
    added_sugar: float | None = None
    cholesterol: float | None = None
    sodium: float | None = None
    potassium: float | None = None
    calcium: float | None = None
    iron: float | None = None
    vitamin_a: float | None = None
    vitamin_c: float | None = None
    vitamin_d: float | None = None
```

Créer `backend/app/ingestion/samsung/nutrition_detail.py` :

```python
"""Mapping des repas de com.samsung.health.nutrition.

Distincte de food_intake (plan 1) : aucune clé commune fiable, cf. plan
« Décisions actées ». Ce module ne connaît que les colonnes de nutrition.csv.
"""

from __future__ import annotations

from app.ingestion.samsung.parsers import parse_aware_datetime, parse_float, parse_int
from app.ingestion.samsung.records import NutritionDetailRecord


def map_nutrition_detail(row: dict[str, str]) -> NutritionDetailRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    consumed_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if consumed_at is None:
        return None
    return NutritionDetailRecord(
        source_uuid=source_uuid,
        consumed_at=consumed_at,
        meal_type=parse_int(row.get("meal_type")),
        title=(row.get("title") or "").strip(),
        calories=parse_float(row.get("calorie")),
        protein=parse_float(row.get("protein")),
        total_fat=parse_float(row.get("total_fat")),
        saturated_fat=parse_float(row.get("saturated_fat")),
        trans_fat=parse_float(row.get("trans_fat")),
        monosaturated_fat=parse_float(row.get("monosaturated_fat")),
        polysaturated_fat=parse_float(row.get("polysaturated_fat")),
        carbohydrate=parse_float(row.get("carbohydrate")),
        dietary_fiber=parse_float(row.get("dietary_fiber")),
        sugar=parse_float(row.get("sugar")),
        added_sugar=parse_float(row.get("added_sugar")),
        cholesterol=parse_float(row.get("cholesterol")),
        sodium=parse_float(row.get("sodium")),
        potassium=parse_float(row.get("potassium")),
        calcium=parse_float(row.get("calcium")),
        iron=parse_float(row.get("iron")),
        vitamin_a=parse_float(row.get("vitamin_a")),
        vitamin_c=parse_float(row.get("vitamin_c")),
        vitamin_d=parse_float(row.get("vitamin_d")),
    )
```

Ajouter à `backend/app/ingestion/samsung/loader.py`, à la suite de
`upsert_nutrition_entries` :

```python
from app.ingestion.samsung.records import NutritionDetailRecord  # ajouté à l'import existant
from app.models import NutritionDetail  # ajouté à l'import existant


async def upsert_nutrition_details(
    session: AsyncSession, records: Sequence[NutritionDetailRecord]
) -> int:
    return await _upsert_on_source_uuid(session, NutritionDetail, records)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_nutrition_detail_mapper.py tests/integration/test_extended_loader.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/nutrition_detail.py backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/loader.py backend/tests
git commit -m "feat: ingest granular nutrition macros and micros"
```

---

### Task 3: Ingestion de la dépense énergétique quotidienne

**Files:**
- Modify: `backend/app/ingestion/samsung/records.py`
- Create: `backend/app/ingestion/samsung/energy.py`
- Modify: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/fixtures/samsung/calories_burned_sample.csv`
- Create: `backend/tests/unit/test_energy_mapper.py`
- Modify: `backend/tests/integration/test_extended_loader.py`

**Interfaces:**
- Consumes: `parse_float`, `parse_int`, `parse_aware_datetime`,
  `read_samsung_csv` (plan 1) ; `EnergyExpenditure` (tâche 1).
- Produces:
  - `EnergyExpenditureRecord`
  - `map_energy_expenditure(row: dict[str, str]) -> EnergyExpenditureRecord | None`
  - `upsert_energy_expenditures(session, records: Sequence[EnergyExpenditureRecord]) -> int`
  - `parse_local_day(raw: object) -> date | None` (utilitaire partagé avec
    la tâche 7, défini ici et réutilisé)

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/calories_burned_sample.csv` :

```csv
com.samsung.shealth.calories_burned.details,7006003,4
com.samsung.shealth.calories_burned.rest_calorie,com.samsung.shealth.calories_burned.active_calorie,com.samsung.shealth.calories_burned.tef_calorie,com.samsung.shealth.calories_burned.active_time,total_exercise_calories,com.samsung.shealth.calories_burned.day_time,com.samsung.shealth.calories_burned.datauuid
1814.15,90.01783,0.0,1632770,,2018-11-28 00:00:00.000,ebd0e5f6-7016-4446-b8a0-d57584762484
,,,,,2018-11-29 00:00:00.000,
```

Créer `backend/tests/unit/test_energy_mapper.py` :

```python
"""Tests du mapping de la dépense énergétique quotidienne."""

from datetime import date
from pathlib import Path

from app.ingestion.samsung.energy import map_energy_expenditure, parse_local_day
from app.ingestion.samsung.parsers import read_samsung_csv

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"


def test_maps_a_complete_row() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "calories_burned_sample.csv")))

    record = map_energy_expenditure(row)

    assert record is not None
    assert record.source_uuid == "ebd0e5f6-7016-4446-b8a0-d57584762484"
    assert record.day == date(2018, 11, 28)
    assert record.rest_calorie == 1814.15
    assert record.active_calorie == 90.01783
    assert record.active_time_ms == 1632770
    assert record.total_exercise_calories is None


def test_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "calories_burned_sample.csv"))

    assert map_energy_expenditure(rows[1]) is None


def test_parse_local_day_reads_the_date_part_only() -> None:
    """day_time n'a pas de time_offset dans cet export : on ne garde que la
    date, sans supposer de fuseau sur l'heure (toujours minuit)."""
    assert parse_local_day("2018-11-28 00:00:00.000") == date(2018, 11, 28)


def test_parse_local_day_rejects_invalid() -> None:
    assert parse_local_day("") is None
    assert parse_local_day(None) is None
```

Ajouter à `backend/tests/integration/test_extended_loader.py` :

```python
from app.ingestion.samsung.loader import upsert_energy_expenditures
from app.ingestion.samsung.records import EnergyExpenditureRecord
from app.models import EnergyExpenditure
from datetime import date as _date


@pytest.fixture(autouse=True)
async def _clean_energy(session: AsyncSession) -> None:
    await session.execute(EnergyExpenditure.__table__.delete())
    await session.commit()


async def test_upsert_energy_expenditures_is_idempotent(session: AsyncSession) -> None:
    record = EnergyExpenditureRecord(
        source_uuid="day-1", day=_date(2026, 1, 1), rest_calorie=1600.0
    )

    await upsert_energy_expenditures(session, [record])
    await upsert_energy_expenditures(session, [record])

    total = (
        await session.execute(
            select(func.count()).select_from(EnergyExpenditure)
        )
    ).scalar_one()
    assert total == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_energy_mapper.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.energy'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/records.py` :

```python
@dataclass(frozen=True, slots=True)
class EnergyExpenditureRecord:
    source_uuid: str
    day: date
    rest_calorie: float | None = None
    active_calorie: float | None = None
    tef_calorie: float | None = None
    active_time_ms: int | None = None
    total_exercise_calories: float | None = None
```

Créer `backend/app/ingestion/samsung/energy.py` :

```python
"""Mapping de la décomposition quotidienne de la dépense énergétique.

com.samsung.shealth.calories_burned.details ne porte pas de colonne time_
offset : day_time est une minuit locale sans fuseau exploitable. On n'en
retient que la date, jamais un TIMESTAMPTZ inventé.
"""

from __future__ import annotations

from datetime import date

from app.ingestion.samsung.parsers import _DATETIME_RE, parse_float, parse_int
from app.ingestion.samsung.records import EnergyExpenditureRecord

PREFIX = "com.samsung.shealth.calories_burned."


def parse_local_day(raw: object) -> date | None:
    text = "" if raw is None else str(raw).strip()
    match = _DATETIME_RE.search(text)
    if match is None:
        return None
    year, month, day = (int(match.group(i)) for i in (1, 2, 3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _prefixed(row: dict[str, str], name: str) -> str | None:
    return row.get(f"{PREFIX}{name}")


def map_energy_expenditure(row: dict[str, str]) -> EnergyExpenditureRecord | None:
    source_uuid = (_prefixed(row, "datauuid") or "").strip()
    if not source_uuid:
        return None
    day = parse_local_day(_prefixed(row, "day_time"))
    if day is None:
        return None
    return EnergyExpenditureRecord(
        source_uuid=source_uuid,
        day=day,
        rest_calorie=parse_float(_prefixed(row, "rest_calorie")),
        active_calorie=parse_float(_prefixed(row, "active_calorie")),
        tef_calorie=parse_float(_prefixed(row, "tef_calorie")),
        active_time_ms=parse_int(_prefixed(row, "active_time")),
        total_exercise_calories=parse_float(row.get("total_exercise_calories")),
    )
```

Note : `_DATETIME_RE` est un détail d'implémentation de `parsers.py`
(regex compilée module-level). L'importer directement évite de dupliquer le
motif ; si `parsers.py` le renomme, ce module doit être mis à jour en même
temps — signalé ici pour l'implémenteur de tâches futures sur `parsers.py`.

Ajouter à `backend/app/ingestion/samsung/loader.py` :

```python
from app.ingestion.samsung.records import EnergyExpenditureRecord  # ajouté à l'import
from app.models import EnergyExpenditure  # ajouté à l'import


async def upsert_energy_expenditures(
    session: AsyncSession, records: Sequence[EnergyExpenditureRecord]
) -> int:
    return await _upsert_on_source_uuid(session, EnergyExpenditure, records)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_energy_mapper.py tests/integration/test_extended_loader.py -v`
Expected: PASS, 8 tests (4 nouveaux + 4 de la tâche 2)

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/energy.py backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/loader.py backend/tests
git commit -m "feat: ingest daily energy expenditure breakdown"
```

---

### Task 4: Ingestion du sommeil et de ses phases

**Files:**
- Modify: `backend/app/ingestion/samsung/records.py`
- Create: `backend/app/ingestion/samsung/sleep.py`
- Modify: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/fixtures/samsung/sleep_sample.csv`
- Create: `backend/tests/fixtures/samsung/sleep_stage_sample.csv`
- Create: `backend/tests/unit/test_sleep_mapper.py`
- Modify: `backend/tests/integration/test_extended_loader.py`

**Interfaces:**
- Consumes: `parse_float`, `parse_int`, `parse_aware_datetime`,
  `read_samsung_csv` (plan 1) ; `SleepSession`, `SleepStage` (tâche 1).
- Produces:
  - `SleepSessionRecord`, `SleepStageRecord`
  - `map_sleep_session(row: dict[str, str]) -> SleepSessionRecord | None`
  - `map_sleep_stage(row: dict[str, str]) -> SleepStageRecord | None`
  - `upsert_sleep_sessions(session, records) -> int`
  - `upsert_sleep_stages(session, records) -> int`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/sleep_sample.csv` :

```csv
com.samsung.shealth.sleep,7006003,11
sleep_efficiency_with_latency,efficiency,physical_recovery,mental_recovery,deep_score,rem_score,wake_score,nap_score,latency_score,sleep_latency,total_rem_duration,total_light_duration,sleep_type,has_sleep_data,sleep_score,sleep_duration,com.samsung.health.sleep.start_time,com.samsung.health.sleep.end_time,com.samsung.health.sleep.time_offset,original_wake_up_time,com.samsung.health.sleep.datauuid
78.0,82.0,64.0,58.0,20.0,15.0,90.0,,70.0,600,5400,10800,-1,0,72.0,25200,2024-12-22 23:00:00.000,2024-12-23 07:00:00.000,UTC+0100,2024-12-23 07:24:00.000,2ca56115-6553-45f1-bfa7-eb37c4c77ac9
,,,,,,,,,,,,,,,,2024-12-24 23:00:00.000,,UTC+0100,,
```

Créer `backend/tests/fixtures/samsung/sleep_stage_sample.csv` :

```csv
com.samsung.health.sleep_stage,7006003,7
start_time,sleep_id,stage,time_offset,end_time,datauuid
2024-12-22 23:00:00.000,2ca56115-6553-45f1-bfa7-eb37c4c77ac9,40001,UTC+0100,2024-12-22 23:20:00.000,27c5a75c-cc02-49c1-9a01-084e1e0cbd65
,,,,,
```

Créer `backend/tests/unit/test_sleep_mapper.py` :

```python
"""Tests du mapping du sommeil et de ses phases."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ingestion.samsung.parsers import read_samsung_csv
from app.ingestion.samsung.sleep import map_sleep_session, map_sleep_stage

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"
PARIS_WINTER = timezone(timedelta(hours=1))


def test_maps_a_complete_sleep_session() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "sleep_sample.csv")))

    record = map_sleep_session(row)

    assert record is not None
    assert record.source_uuid == "2ca56115-6553-45f1-bfa7-eb37c4c77ac9"
    assert record.started_at == datetime(2024, 12, 22, 23, 0, tzinfo=PARIS_WINTER)
    assert record.ended_at == datetime(2024, 12, 23, 7, 0, tzinfo=PARIS_WINTER)
    assert record.original_wake_up_time == datetime(
        2024, 12, 23, 7, 24, tzinfo=PARIS_WINTER
    )
    assert record.efficiency_with_latency == 78.0
    assert record.sleep_type == -1
    assert record.has_sleep_data == 0
    assert record.nap_score is None


def test_sleep_session_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "sleep_sample.csv"))

    assert map_sleep_session(rows[1]) is None


def test_maps_a_sleep_stage() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "sleep_stage_sample.csv")))

    record = map_sleep_stage(row)

    assert record is not None
    assert record.source_uuid == "27c5a75c-cc02-49c1-9a01-084e1e0cbd65"
    assert record.sleep_source_uuid == "2ca56115-6553-45f1-bfa7-eb37c4c77ac9"
    assert record.stage == 40001
    assert record.started_at == datetime(2024, 12, 22, 23, 0, tzinfo=PARIS_WINTER)


def test_sleep_stage_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "sleep_stage_sample.csv"))

    assert map_sleep_stage(rows[1]) is None
```

Ajouter à `backend/tests/integration/test_extended_loader.py` :

```python
from app.ingestion.samsung.loader import upsert_sleep_sessions, upsert_sleep_stages
from app.ingestion.samsung.records import SleepSessionRecord, SleepStageRecord
from app.models import SleepSession, SleepStage


@pytest.fixture(autouse=True)
async def _clean_sleep(session: AsyncSession) -> None:
    for model in (SleepStage, SleepSession):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_upsert_sleep_is_idempotent(session: AsyncSession) -> None:
    session_record = SleepSessionRecord(
        source_uuid="night-1",
        started_at=datetime(2026, 1, 1, 23, tzinfo=UTC),
        efficiency=80.0,
    )
    stage_record = SleepStageRecord(
        source_uuid="stage-1",
        sleep_source_uuid="night-1",
        started_at=datetime(2026, 1, 1, 23, tzinfo=UTC),
        stage=40001,
    )

    await upsert_sleep_sessions(session, [session_record])
    await upsert_sleep_stages(session, [stage_record])
    await upsert_sleep_sessions(session, [session_record])
    await upsert_sleep_stages(session, [stage_record])

    sessions_total = (
        await session.execute(select(func.count()).select_from(SleepSession))
    ).scalar_one()
    stages_total = (
        await session.execute(select(func.count()).select_from(SleepStage))
    ).scalar_one()
    assert sessions_total == 1
    assert stages_total == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_sleep_mapper.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.sleep'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/records.py` :

```python
@dataclass(frozen=True, slots=True)
class SleepSessionRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    original_wake_up_time: datetime | None = None
    efficiency: float | None = None
    efficiency_with_latency: float | None = None
    physical_recovery: int | None = None
    mental_recovery: int | None = None
    deep_score: int | None = None
    rem_score: int | None = None
    wake_score: int | None = None
    nap_score: int | None = None
    latency_score: int | None = None
    sleep_latency: int | None = None
    total_rem_duration: int | None = None
    total_light_duration: int | None = None
    sleep_duration: int | None = None
    sleep_score: int | None = None
    has_sleep_data: int | None = None
    sleep_type: int | None = None


@dataclass(frozen=True, slots=True)
class SleepStageRecord:
    source_uuid: str
    started_at: datetime
    sleep_source_uuid: str | None = None
    ended_at: datetime | None = None
    stage: int | None = None
```

Créer `backend/app/ingestion/samsung/sleep.py` :

```python
"""Mapping du sommeil : résumé de nuit (préfixé) et phases (non préfixées).

sleep_stage.sleep_id n'est volontairement pas vérifié contre sleep.csv :
7 segments réels référencent une nuit absente de l'export, et la contrainte
d'unicité de sleep_stage ne doit jamais dépendre de l'ordre d'ingestion des
deux fichiers.
"""

from __future__ import annotations

from app.ingestion.samsung.parsers import parse_aware_datetime, parse_float, parse_int
from app.ingestion.samsung.records import SleepSessionRecord, SleepStageRecord

PREFIX = "com.samsung.health.sleep."


def _prefixed(row: dict[str, str], name: str) -> str | None:
    return row.get(f"{PREFIX}{name}")


def map_sleep_session(row: dict[str, str]) -> SleepSessionRecord | None:
    source_uuid = (_prefixed(row, "datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = _prefixed(row, "time_offset")
    started_at = parse_aware_datetime(_prefixed(row, "start_time"), offset)
    if started_at is None:
        return None
    return SleepSessionRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(_prefixed(row, "end_time"), offset),
        original_wake_up_time=parse_aware_datetime(
            row.get("original_wake_up_time"), offset
        ),
        efficiency=parse_float(row.get("efficiency")),
        efficiency_with_latency=parse_float(row.get("sleep_efficiency_with_latency")),
        physical_recovery=parse_int(row.get("physical_recovery")),
        mental_recovery=parse_int(row.get("mental_recovery")),
        deep_score=parse_int(row.get("deep_score")),
        rem_score=parse_int(row.get("rem_score")),
        wake_score=parse_int(row.get("wake_score")),
        nap_score=parse_int(row.get("nap_score")),
        latency_score=parse_int(row.get("latency_score")),
        sleep_latency=parse_int(row.get("sleep_latency")),
        total_rem_duration=parse_int(row.get("total_rem_duration")),
        total_light_duration=parse_int(row.get("total_light_duration")),
        sleep_duration=parse_int(row.get("sleep_duration")),
        sleep_score=parse_int(row.get("sleep_score")),
        has_sleep_data=parse_int(row.get("has_sleep_data")),
        sleep_type=parse_int(row.get("sleep_type")),
    )


def map_sleep_stage(row: dict[str, str]) -> SleepStageRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    started_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if started_at is None:
        return None
    return SleepStageRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        sleep_source_uuid=(row.get("sleep_id") or "").strip() or None,
        ended_at=parse_aware_datetime(row.get("end_time"), row.get("time_offset")),
        stage=parse_int(row.get("stage")),
    )
```

Ajouter à `backend/app/ingestion/samsung/loader.py` :

```python
from app.ingestion.samsung.records import (  # complète l'import existant
    SleepSessionRecord,
    SleepStageRecord,
)
from app.models import SleepSession, SleepStage  # complète l'import existant


async def upsert_sleep_sessions(
    session: AsyncSession, records: Sequence[SleepSessionRecord]
) -> int:
    return await _upsert_on_source_uuid(session, SleepSession, records)


async def upsert_sleep_stages(
    session: AsyncSession, records: Sequence[SleepStageRecord]
) -> int:
    return await _upsert_on_source_uuid(session, SleepStage, records)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_sleep_mapper.py tests/integration/test_extended_loader.py -v`
Expected: PASS, 13 tests (5 nouveaux + 8 des tâches 2-3)

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/sleep.py backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/loader.py backend/tests
git commit -m "feat: ingest sleep sessions and sleep stages"
```

---

### Task 5: Ingestion de la VFC, de la fréquence cardiaque et du stress

**Files:**
- Modify: `backend/app/ingestion/samsung/records.py`
- Create: `backend/app/ingestion/samsung/vitals.py`
- Modify: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/fixtures/samsung/hrv_sample.csv`
- Create: `backend/tests/fixtures/samsung/hrv/a/aaaaaaaa-0000-0000-0000-000000000001.binning_data.json`
- Create: `backend/tests/fixtures/samsung/heart_rate_sample.csv`
- Create: `backend/tests/fixtures/samsung/stress_sample.csv`
- Create: `backend/tests/unit/test_vitals_mapper.py`
- Modify: `backend/tests/integration/test_extended_loader.py`

**Interfaces:**
- Consumes: `parse_float`, `parse_int`, `parse_aware_datetime` (plan 1) ;
  `resolve_json_path`, `load_json` (`app.ingestion.samsung.json_files`,
  plan 1, tâche 8 — génériques, réutilisables tels quels sur n'importe quel
  répertoire à premier caractère hexadécimal) ; `HrvReading`,
  `HeartRateReading`, `StressReading` (tâche 1).
- Produces:
  - `HrvReadingRecord`, `HeartRateReadingRecord`, `StressReadingRecord`
  - `map_hrv_reading(row: dict[str, str], hrv_dir: Path) -> HrvReadingRecord | None`
  - `map_heart_rate_reading(row: dict[str, str]) -> HeartRateReadingRecord | None`
  - `map_stress_reading(row: dict[str, str]) -> StressReadingRecord | None`
  - `upsert_hrv_readings`, `upsert_heart_rate_readings`, `upsert_stress_readings`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/hrv_sample.csv` :

```csv
com.samsung.health.hrv,7006003,1
start_time,end_time,binning_data,time_offset,datauuid
2024-11-20 22:00:00.000,2024-11-20 23:00:00.000,aaaaaaaa-0000-0000-0000-000000000001.binning_data.json,UTC+0100,a057c257-f289-4bb6-8672-5dc197c624b7
2024-11-21 22:00:00.000,2024-11-21 23:00:00.000,fichier-absent.binning_data.json,UTC+0100,b057c257-f289-4bb6-8672-5dc197c624b8
,,,,
```

Créer `backend/tests/fixtures/samsung/hrv/a/aaaaaaaa-0000-0000-0000-000000000001.binning_data.json` :

```json
[
  {"start_time": 1736992826593, "end_time": 1736993128301, "sdnn": 91.826126, "rmssd": 55.307346},
  {"start_time": 1736992856593, "end_time": 1736993158301, "sdnn": 98.977875, "rmssd": 55.69922}
]
```

Créer `backend/tests/fixtures/samsung/heart_rate_sample.csv` :

```csv
com.samsung.shealth.tracker.heart_rate,7006003,3
tag_id,com.samsung.health.heart_rate.heart_rate,com.samsung.health.heart_rate.min,com.samsung.health.heart_rate.max,com.samsung.health.heart_rate.heart_beat_count,com.samsung.health.heart_rate.start_time,com.samsung.health.heart_rate.end_time,com.samsung.health.heart_rate.time_offset,com.samsung.health.heart_rate.datauuid
21313,80.0,67.0,108.0,1,2024-11-20 12:00:00.000,2024-11-20 12:59:59.999,UTC+0100,3d65d015-817a-447b-9452-443f3a8dbff2
,,,,,,,,
```

Créer `backend/tests/fixtures/samsung/stress_sample.csv` :

```csv
com.samsung.shealth.stress,7006003,9
tag_id,max,min,score,start_time,end_time,time_offset,datauuid
10000,,,44.0,2024-11-20 20:38:29.362,2024-11-20 20:38:29.362,UTC+0100,5d67d93d-d7a8-42e7-814d-2c649d850409
,,,,,,,
```

Créer `backend/tests/unit/test_vitals_mapper.py` :

```python
"""Tests des mappers VFC, fréquence cardiaque et stress."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ingestion.samsung.parsers import read_samsung_csv
from app.ingestion.samsung.vitals import (
    map_heart_rate_reading,
    map_hrv_reading,
    map_stress_reading,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"
PARIS_WINTER = timezone(timedelta(hours=1))


def test_maps_hrv_reading_by_averaging_the_binning_file() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "hrv_sample.csv")))

    record = map_hrv_reading(row, FIXTURES / "hrv")

    assert record is not None
    assert record.source_uuid == "a057c257-f289-4bb6-8672-5dc197c624b7"
    assert record.sample_count == 2
    assert record.avg_sdnn == (91.826126 + 98.977875) / 2
    assert record.avg_rmssd == (55.307346 + 55.69922) / 2


def test_maps_hrv_reading_with_missing_binning_file_keeps_the_reading() -> None:
    """Un fichier absent ne doit pas faire disparaître le relevé : seules
    les moyennes restent None."""
    rows = list(read_samsung_csv(FIXTURES / "hrv_sample.csv"))

    record = map_hrv_reading(rows[1], FIXTURES / "hrv")

    assert record is not None
    assert record.sample_count == 0
    assert record.avg_sdnn is None
    assert record.avg_rmssd is None


def test_hrv_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "hrv_sample.csv"))

    assert map_hrv_reading(rows[2], FIXTURES / "hrv") is None


def test_maps_heart_rate_reading() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "heart_rate_sample.csv")))

    record = map_heart_rate_reading(row)

    assert record is not None
    assert record.source_uuid == "3d65d015-817a-447b-9452-443f3a8dbff2"
    assert record.mean_heart_rate == 80.0
    assert record.min_heart_rate == 67.0
    assert record.max_heart_rate == 108.0
    assert record.heart_beat_count == 1
    assert record.tag_id == 21313
    assert record.started_at == datetime(2024, 11, 20, 12, 0, tzinfo=PARIS_WINTER)


def test_heart_rate_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "heart_rate_sample.csv"))

    assert map_heart_rate_reading(rows[1]) is None


def test_maps_stress_reading() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "stress_sample.csv")))

    record = map_stress_reading(row)

    assert record is not None
    assert record.source_uuid == "5d67d93d-d7a8-42e7-814d-2c649d850409"
    assert record.score == 44.0
    assert record.min_score is None
    assert record.tag_id == 10000


def test_stress_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "stress_sample.csv"))

    assert map_stress_reading(rows[1]) is None
```

Ajouter à `backend/tests/integration/test_extended_loader.py` :

```python
from app.ingestion.samsung.loader import (
    upsert_heart_rate_readings,
    upsert_hrv_readings,
    upsert_stress_readings,
)
from app.ingestion.samsung.records import (
    HeartRateReadingRecord,
    HrvReadingRecord,
    StressReadingRecord,
)
from app.models import HeartRateReading, HrvReading, StressReading


@pytest.fixture(autouse=True)
async def _clean_vitals(session: AsyncSession) -> None:
    for model in (HrvReading, HeartRateReading, StressReading):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_upsert_vitals_is_idempotent(session: AsyncSession) -> None:
    hrv = HrvReadingRecord(
        source_uuid="hrv-1", started_at=datetime(2026, 1, 1, tzinfo=UTC), sample_count=2
    )
    heart_rate = HeartRateReadingRecord(
        source_uuid="hr-1", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    stress = StressReadingRecord(
        source_uuid="stress-1", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    await upsert_hrv_readings(session, [hrv])
    await upsert_heart_rate_readings(session, [heart_rate])
    await upsert_stress_readings(session, [stress])
    await upsert_hrv_readings(session, [hrv])
    await upsert_heart_rate_readings(session, [heart_rate])
    await upsert_stress_readings(session, [stress])

    for model in (HrvReading, HeartRateReading, StressReading):
        total = (
            await session.execute(select(func.count()).select_from(model))
        ).scalar_one()
        assert total == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_vitals_mapper.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.vitals'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/records.py` :

```python
@dataclass(frozen=True, slots=True)
class HrvReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    avg_sdnn: float | None = None
    avg_rmssd: float | None = None
    sample_count: int = 0


@dataclass(frozen=True, slots=True)
class HeartRateReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    mean_heart_rate: float | None = None
    min_heart_rate: float | None = None
    max_heart_rate: float | None = None
    heart_beat_count: int | None = None
    tag_id: int | None = None


@dataclass(frozen=True, slots=True)
class StressReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    score: float | None = None
    min_score: float | None = None
    max_score: float | None = None
    tag_id: int | None = None
```

Créer `backend/app/ingestion/samsung/vitals.py` :

```python
"""Mapping des signaux continus : VFC, fréquence cardiaque, stress.

Seule la VFC ouvre un fichier JSON annexe : sa ligne CSV ne porte aucune
mesure, uniquement une référence de binning (cf. plan « Décisions actées »).
Fréquence cardiaque et stress ont leur agrégat directement dans la ligne
CSV ; leur binning n'est pas ouvert.
"""

from __future__ import annotations

from pathlib import Path

from app.ingestion.samsung.json_files import load_json, resolve_json_path
from app.ingestion.samsung.parsers import parse_aware_datetime, parse_float, parse_int
from app.ingestion.samsung.records import (
    HeartRateReadingRecord,
    HrvReadingRecord,
    StressReadingRecord,
)

HEART_RATE_PREFIX = "com.samsung.health.heart_rate."


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def map_hrv_reading(row: dict[str, str], hrv_dir: Path) -> HrvReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    started_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if started_at is None:
        return None

    payload = load_json(resolve_json_path(hrv_dir, row.get("binning_data")))
    items = payload if isinstance(payload, list) else []
    sdnn_values = [
        v for item in items if isinstance(item, dict)
        for v in [parse_float(item.get("sdnn"))] if v is not None
    ]
    rmssd_values = [
        v for item in items if isinstance(item, dict)
        for v in [parse_float(item.get("rmssd"))] if v is not None
    ]

    return HrvReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), row.get("time_offset")),
        avg_sdnn=_average(sdnn_values),
        avg_rmssd=_average(rmssd_values),
        sample_count=len(items) if isinstance(payload, list) else 0,
    )


def map_heart_rate_reading(row: dict[str, str]) -> HeartRateReadingRecord | None:
    source_uuid = (row.get(f"{HEART_RATE_PREFIX}datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get(f"{HEART_RATE_PREFIX}time_offset")
    started_at = parse_aware_datetime(row.get(f"{HEART_RATE_PREFIX}start_time"), offset)
    if started_at is None:
        return None
    return HeartRateReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get(f"{HEART_RATE_PREFIX}end_time"), offset),
        mean_heart_rate=parse_float(row.get(f"{HEART_RATE_PREFIX}heart_rate")),
        min_heart_rate=parse_float(row.get(f"{HEART_RATE_PREFIX}min")),
        max_heart_rate=parse_float(row.get(f"{HEART_RATE_PREFIX}max")),
        heart_beat_count=parse_int(row.get(f"{HEART_RATE_PREFIX}heart_beat_count")),
        tag_id=parse_int(row.get("tag_id")),
    )


def map_stress_reading(row: dict[str, str]) -> StressReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    started_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if started_at is None:
        return None
    return StressReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), row.get("time_offset")),
        score=parse_float(row.get("score")),
        min_score=parse_float(row.get("min")),
        max_score=parse_float(row.get("max")),
        tag_id=parse_int(row.get("tag_id")),
    )
```

Ajouter à `backend/app/ingestion/samsung/loader.py` :

```python
from app.ingestion.samsung.records import (  # complète l'import existant
    HeartRateReadingRecord,
    HrvReadingRecord,
    StressReadingRecord,
)
from app.models import (  # complète l'import existant
    HeartRateReading,
    HrvReading,
    StressReading,
)


async def upsert_hrv_readings(
    session: AsyncSession, records: Sequence[HrvReadingRecord]
) -> int:
    return await _upsert_on_source_uuid(session, HrvReading, records)


async def upsert_heart_rate_readings(
    session: AsyncSession, records: Sequence[HeartRateReadingRecord]
) -> int:
    return await _upsert_on_source_uuid(session, HeartRateReading, records)


async def upsert_stress_readings(
    session: AsyncSession, records: Sequence[StressReadingRecord]
) -> int:
    return await _upsert_on_source_uuid(session, StressReading, records)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_vitals_mapper.py tests/integration/test_extended_loader.py -v`
Expected: PASS, 21 tests (8 nouveaux + 13 des tâches 2-4)

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/vitals.py backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/loader.py backend/tests
git commit -m "feat: ingest hrv, continuous heart rate and stress readings"
```

---

### Task 6: Ingestion des marqueurs nocturnes (SpO2, respiration, température)

**Files:**
- Modify: `backend/app/ingestion/samsung/records.py`
- Modify: `backend/app/ingestion/samsung/vitals.py`
- Modify: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/fixtures/samsung/oxygen_saturation_sample.csv`
- Create: `backend/tests/fixtures/samsung/respiratory_rate_sample.csv`
- Create: `backend/tests/fixtures/samsung/skin_temperature_sample.csv`
- Modify: `backend/tests/unit/test_vitals_mapper.py`
- Modify: `backend/tests/integration/test_extended_loader.py`

**Interfaces:**
- Consumes: le module `vitals.py` de la tâche 5 (mêmes conventions de
  préfixe et de gestion de `datauuid`) ; `RespiratoryRateReading`,
  `SkinTemperatureReading`, `OxygenSaturationReading` (tâche 1).
- Produces:
  - `RespiratoryRateReadingRecord`, `SkinTemperatureReadingRecord`,
    `OxygenSaturationReadingRecord`
  - `map_respiratory_rate_reading(row) -> RespiratoryRateReadingRecord | None`
  - `map_skin_temperature_reading(row) -> SkinTemperatureReadingRecord | None`
  - `map_oxygen_saturation_reading(row) -> OxygenSaturationReadingRecord | None`
  - `upsert_respiratory_rate_readings`, `upsert_skin_temperature_readings`,
    `upsert_oxygen_saturation_readings`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/oxygen_saturation_sample.csv` :

```csv
com.samsung.shealth.tracker.oxygen_saturation,7006003,2
tag_id,com.samsung.health.oxygen_saturation.spo2,com.samsung.health.oxygen_saturation.heart_rate,com.samsung.health.oxygen_saturation.start_time,com.samsung.health.oxygen_saturation.end_time,com.samsung.health.oxygen_saturation.time_offset,com.samsung.health.oxygen_saturation.datauuid
31000,95.0,88.0,2024-11-20 12:46:04.258,2024-11-20 12:46:04.258,UTC+0100,a3753d39-778c-42c7-8f09-d49a890d7995
,,,,,,
```

Créer `backend/tests/fixtures/samsung/respiratory_rate_sample.csv` :

```csv
com.samsung.health.respiratory_rate,7006003,2
average,lower_limit,upper_limit,start_time,end_time,time_offset,datauuid
15.049458,0.0,0.0,2024-11-20 22:09:00.000,2024-11-21 06:30:00.000,UTC+0100,392466c5-9ac6-4a79-a5d8-13b2512930e8
,,,,,,
```

Créer `backend/tests/fixtures/samsung/skin_temperature_sample.csv` :

```csv
com.samsung.health.skin_temperature,7006003,4
temperature,min,max,baseline,start_time,end_time,time_offset,datauuid
32.95659,28.886059,34.99363,,2024-11-20 22:09:00.000,2024-11-21 06:30:00.000,UTC+0100,7df792cf-3ce2-4307-8d12-5858c0f32489
,,,,,,,
```

Ajouter à `backend/tests/unit/test_vitals_mapper.py` :

```python
from app.ingestion.samsung.vitals import (
    map_oxygen_saturation_reading,
    map_respiratory_rate_reading,
    map_skin_temperature_reading,
)


def test_maps_oxygen_saturation_reading() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "oxygen_saturation_sample.csv")))

    record = map_oxygen_saturation_reading(row)

    assert record is not None
    assert record.source_uuid == "a3753d39-778c-42c7-8f09-d49a890d7995"
    assert record.spo2 == 95.0
    assert record.heart_rate == 88.0
    assert record.tag_id == 31000


def test_oxygen_saturation_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "oxygen_saturation_sample.csv"))

    assert map_oxygen_saturation_reading(rows[1]) is None


def test_maps_respiratory_rate_reading() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "respiratory_rate_sample.csv")))

    record = map_respiratory_rate_reading(row)

    assert record is not None
    assert record.source_uuid == "392466c5-9ac6-4a79-a5d8-13b2512930e8"
    assert record.average == 15.049458


def test_respiratory_rate_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "respiratory_rate_sample.csv"))

    assert map_respiratory_rate_reading(rows[1]) is None


def test_maps_skin_temperature_reading() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "skin_temperature_sample.csv")))

    record = map_skin_temperature_reading(row)

    assert record is not None
    assert record.source_uuid == "7df792cf-3ce2-4307-8d12-5858c0f32489"
    assert record.temperature == 32.95659
    assert record.min_temperature == 28.886059
    assert record.baseline is None


def test_skin_temperature_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "skin_temperature_sample.csv"))

    assert map_skin_temperature_reading(rows[1]) is None
```

Ajouter à `backend/tests/integration/test_extended_loader.py` :

```python
from app.ingestion.samsung.loader import (
    upsert_oxygen_saturation_readings,
    upsert_respiratory_rate_readings,
    upsert_skin_temperature_readings,
)
from app.ingestion.samsung.records import (
    OxygenSaturationReadingRecord,
    RespiratoryRateReadingRecord,
    SkinTemperatureReadingRecord,
)
from app.models import (
    OxygenSaturationReading,
    RespiratoryRateReading,
    SkinTemperatureReading,
)


@pytest.fixture(autouse=True)
async def _clean_night_markers(session: AsyncSession) -> None:
    for model in (
        OxygenSaturationReading,
        RespiratoryRateReading,
        SkinTemperatureReading,
    ):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_upsert_night_markers_is_idempotent(session: AsyncSession) -> None:
    spo2 = OxygenSaturationReadingRecord(
        source_uuid="spo2-1", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    resp = RespiratoryRateReadingRecord(
        source_uuid="resp-1", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    skin = SkinTemperatureReadingRecord(
        source_uuid="skin-1", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    await upsert_oxygen_saturation_readings(session, [spo2])
    await upsert_respiratory_rate_readings(session, [resp])
    await upsert_skin_temperature_readings(session, [skin])
    await upsert_oxygen_saturation_readings(session, [spo2])
    await upsert_respiratory_rate_readings(session, [resp])
    await upsert_skin_temperature_readings(session, [skin])

    for model in (
        OxygenSaturationReading,
        RespiratoryRateReading,
        SkinTemperatureReading,
    ):
        total = (
            await session.execute(select(func.count()).select_from(model))
        ).scalar_one()
        assert total == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_vitals_mapper.py -v`
Expected: FAIL avec `ImportError: cannot import name 'map_oxygen_saturation_reading'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/records.py` :

```python
@dataclass(frozen=True, slots=True)
class RespiratoryRateReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    average: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None


@dataclass(frozen=True, slots=True)
class SkinTemperatureReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    temperature: float | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    baseline: float | None = None


@dataclass(frozen=True, slots=True)
class OxygenSaturationReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    spo2: float | None = None
    heart_rate: float | None = None
    tag_id: int | None = None
```

Ajouter à `backend/app/ingestion/samsung/vitals.py` :

```python
from app.ingestion.samsung.records import (  # complète l'import existant
    OxygenSaturationReadingRecord,
    RespiratoryRateReadingRecord,
    SkinTemperatureReadingRecord,
)

OXYGEN_SATURATION_PREFIX = "com.samsung.health.oxygen_saturation."


def map_respiratory_rate_reading(
    row: dict[str, str],
) -> RespiratoryRateReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    started_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if started_at is None:
        return None
    return RespiratoryRateReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), row.get("time_offset")),
        average=parse_float(row.get("average")),
        lower_limit=parse_float(row.get("lower_limit")),
        upper_limit=parse_float(row.get("upper_limit")),
    )


def map_skin_temperature_reading(
    row: dict[str, str],
) -> SkinTemperatureReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    started_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if started_at is None:
        return None
    return SkinTemperatureReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), row.get("time_offset")),
        temperature=parse_float(row.get("temperature")),
        min_temperature=parse_float(row.get("min")),
        max_temperature=parse_float(row.get("max")),
        baseline=parse_float(row.get("baseline")),
    )


def map_oxygen_saturation_reading(
    row: dict[str, str],
) -> OxygenSaturationReadingRecord | None:
    source_uuid = (row.get(f"{OXYGEN_SATURATION_PREFIX}datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get(f"{OXYGEN_SATURATION_PREFIX}time_offset")
    started_at = parse_aware_datetime(
        row.get(f"{OXYGEN_SATURATION_PREFIX}start_time"), offset
    )
    if started_at is None:
        return None
    return OxygenSaturationReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(
            row.get(f"{OXYGEN_SATURATION_PREFIX}end_time"), offset
        ),
        spo2=parse_float(row.get(f"{OXYGEN_SATURATION_PREFIX}spo2")),
        heart_rate=parse_float(row.get(f"{OXYGEN_SATURATION_PREFIX}heart_rate")),
        tag_id=parse_int(row.get("tag_id")),
    )
```

Ajouter à `backend/app/ingestion/samsung/loader.py` :

```python
from app.ingestion.samsung.records import (  # complète l'import existant
    OxygenSaturationReadingRecord,
    RespiratoryRateReadingRecord,
    SkinTemperatureReadingRecord,
)
from app.models import (  # complète l'import existant
    OxygenSaturationReading,
    RespiratoryRateReading,
    SkinTemperatureReading,
)


async def upsert_respiratory_rate_readings(
    session: AsyncSession, records: Sequence[RespiratoryRateReadingRecord]
) -> int:
    return await _upsert_on_source_uuid(session, RespiratoryRateReading, records)


async def upsert_skin_temperature_readings(
    session: AsyncSession, records: Sequence[SkinTemperatureReadingRecord]
) -> int:
    return await _upsert_on_source_uuid(session, SkinTemperatureReading, records)


async def upsert_oxygen_saturation_readings(
    session: AsyncSession, records: Sequence[OxygenSaturationReadingRecord]
) -> int:
    return await _upsert_on_source_uuid(session, OxygenSaturationReading, records)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_vitals_mapper.py tests/integration/test_extended_loader.py -v`
Expected: PASS, 30 tests (9 nouveaux + 21 des tâches 2-5)

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/vitals.py backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/loader.py backend/tests
git commit -m "feat: ingest oxygen saturation, respiratory rate and skin temperature"
```

---

### Task 7: Ingestion de l'activité et des pas quotidiens

**Files:**
- Modify: `backend/app/ingestion/samsung/records.py`
- Create: `backend/app/ingestion/samsung/activity.py`
- Modify: `backend/app/ingestion/samsung/loader.py`
- Create: `backend/tests/fixtures/samsung/day_summary_sample.csv`
- Create: `backend/tests/fixtures/samsung/step_daily_trend_sample.csv`
- Create: `backend/tests/unit/test_activity_mapper.py`
- Modify: `backend/tests/integration/test_extended_loader.py`

**Interfaces:**
- Consumes: `parse_float`, `parse_int` (plan 1) ; `parse_local_day`
  (tâche 3) ; `DailyActivity`, `StepDailyTrend` (tâche 1).
- Produces:
  - `DailyActivityRecord`, `StepDailyTrendRecord`
  - `map_daily_activity(row) -> DailyActivityRecord | None`
  - `map_step_daily_trend(row) -> StepDailyTrendRecord | None`
  - `upsert_daily_activities`, `upsert_step_daily_trends`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/fixtures/samsung/day_summary_sample.csv` :

```csv
com.samsung.shealth.activity.day_summary,7006003,6
step_count,active_time,calorie,distance,floor_count,score,exercise_time,run_time,walk_time,longest_active_time,move_hourly_count,day_time,datauuid
2803,1632770,90.01783,2265.3936,,45,60,1400,1631370,71940000,786303,2018-11-28 00:00:00.000,15174bf6-8bb9-43c1-b7e4-d55330724957
,,,,,,,,,,,2018-11-29 00:00:00.000,
```

Créer `backend/tests/fixtures/samsung/step_daily_trend_sample.csv` :

```csv
com.samsung.shealth.step_daily_trend,7006003,6
source_type,count,distance,speed,calorie,day_time,datauuid
0,2803,2212.2998,5.61111,87.73999,2018-11-28 00:00:00.000,6d2ec360-1ca3-4596-a6ac-38f070e78d4f
,,,,,2018-11-29 00:00:00.000,
```

Créer `backend/tests/unit/test_activity_mapper.py` :

```python
"""Tests des mappers d'activité et de pas quotidiens."""

from datetime import date
from pathlib import Path

from app.ingestion.samsung.activity import map_daily_activity, map_step_daily_trend
from app.ingestion.samsung.parsers import read_samsung_csv

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"


def test_maps_daily_activity() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "day_summary_sample.csv")))

    record = map_daily_activity(row)

    assert record is not None
    assert record.source_uuid == "15174bf6-8bb9-43c1-b7e4-d55330724957"
    assert record.day == date(2018, 11, 28)
    assert record.step_count == 2803
    assert record.distance_m == 2265.3936
    assert record.floor_count is None
    assert record.walk_time_ms == 1400


def test_daily_activity_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "day_summary_sample.csv"))

    assert map_daily_activity(rows[1]) is None


def test_maps_step_daily_trend() -> None:
    row = next(iter(read_samsung_csv(FIXTURES / "step_daily_trend_sample.csv")))

    record = map_step_daily_trend(row)

    assert record is not None
    assert record.source_uuid == "6d2ec360-1ca3-4596-a6ac-38f070e78d4f"
    assert record.day == date(2018, 11, 28)
    assert record.count == 2803
    assert record.source_type == 0


def test_step_daily_trend_row_without_datauuid_is_none() -> None:
    rows = list(read_samsung_csv(FIXTURES / "step_daily_trend_sample.csv"))

    assert map_step_daily_trend(rows[1]) is None
```

Ajouter à `backend/tests/integration/test_extended_loader.py` :

```python
from app.ingestion.samsung.loader import upsert_daily_activities, upsert_step_daily_trends
from app.ingestion.samsung.records import DailyActivityRecord, StepDailyTrendRecord
from app.models import DailyActivity, StepDailyTrend


@pytest.fixture(autouse=True)
async def _clean_activity(session: AsyncSession) -> None:
    for model in (DailyActivity, StepDailyTrend):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_upsert_activity_is_idempotent(session: AsyncSession) -> None:
    activity = DailyActivityRecord(source_uuid="day-1", day=_date(2026, 1, 1))
    steps = StepDailyTrendRecord(source_uuid="steps-1", day=_date(2026, 1, 1))

    await upsert_daily_activities(session, [activity])
    await upsert_step_daily_trends(session, [steps])
    await upsert_daily_activities(session, [activity])
    await upsert_step_daily_trends(session, [steps])

    for model in (DailyActivity, StepDailyTrend):
        total = (
            await session.execute(select(func.count()).select_from(model))
        ).scalar_one()
        assert total == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_activity_mapper.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'app.ingestion.samsung.activity'`

- [ ] **Step 3: Écrire l'implémentation minimale**

Ajouter à `backend/app/ingestion/samsung/records.py` :

```python
@dataclass(frozen=True, slots=True)
class DailyActivityRecord:
    source_uuid: str
    day: date
    step_count: int | None = None
    active_time_ms: int | None = None
    calorie: float | None = None
    distance_m: float | None = None
    floor_count: int | None = None
    score: int | None = None
    exercise_time_ms: int | None = None
    run_time_ms: int | None = None
    walk_time_ms: int | None = None
    longest_active_time_ms: int | None = None
    move_hourly_count: int | None = None


@dataclass(frozen=True, slots=True)
class StepDailyTrendRecord:
    source_uuid: str
    day: date
    count: int | None = None
    distance_m: float | None = None
    calorie: float | None = None
    speed: float | None = None
    source_type: int | None = None
```

Créer `backend/app/ingestion/samsung/activity.py` :

```python
"""Mapping de l'activité et des pas quotidiens.

Ni activity.day_summary ni step_daily_trend n'ont de colonne time_offset :
day_time est une minuit locale, seule sa date est retenue (parse_local_day,
défini dans energy.py et réutilisé ici).
"""

from __future__ import annotations

from app.ingestion.samsung.energy import parse_local_day
from app.ingestion.samsung.parsers import parse_float, parse_int
from app.ingestion.samsung.records import DailyActivityRecord, StepDailyTrendRecord


def map_daily_activity(row: dict[str, str]) -> DailyActivityRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    day = parse_local_day(row.get("day_time"))
    if day is None:
        return None
    return DailyActivityRecord(
        source_uuid=source_uuid,
        day=day,
        step_count=parse_int(row.get("step_count")),
        active_time_ms=parse_int(row.get("active_time")),
        calorie=parse_float(row.get("calorie")),
        distance_m=parse_float(row.get("distance")),
        floor_count=parse_int(row.get("floor_count")),
        score=parse_int(row.get("score")),
        exercise_time_ms=parse_int(row.get("exercise_time")),
        run_time_ms=parse_int(row.get("run_time")),
        walk_time_ms=parse_int(row.get("walk_time")),
        longest_active_time_ms=parse_int(row.get("longest_active_time")),
        move_hourly_count=parse_int(row.get("move_hourly_count")),
    )


def map_step_daily_trend(row: dict[str, str]) -> StepDailyTrendRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    day = parse_local_day(row.get("day_time"))
    if day is None:
        return None
    return StepDailyTrendRecord(
        source_uuid=source_uuid,
        day=day,
        count=parse_int(row.get("count")),
        distance_m=parse_float(row.get("distance")),
        calorie=parse_float(row.get("calorie")),
        speed=parse_float(row.get("speed")),
        source_type=parse_int(row.get("source_type")),
    )
```

Ajouter à `backend/app/ingestion/samsung/loader.py` :

```python
from app.ingestion.samsung.records import (  # complète l'import existant
    DailyActivityRecord,
    StepDailyTrendRecord,
)
from app.models import DailyActivity, StepDailyTrend  # complète l'import existant


async def upsert_daily_activities(
    session: AsyncSession, records: Sequence[DailyActivityRecord]
) -> int:
    return await _upsert_on_source_uuid(session, DailyActivity, records)


async def upsert_step_daily_trends(
    session: AsyncSession, records: Sequence[StepDailyTrendRecord]
) -> int:
    return await _upsert_on_source_uuid(session, StepDailyTrend, records)
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_activity_mapper.py tests/integration/test_extended_loader.py -v`
Expected: PASS, 38 tests (8 nouveaux + 30 des tâches 2-6)

- [ ] **Step 5: Commiter**

```bash
git add backend/app/ingestion/samsung/activity.py backend/app/ingestion/samsung/records.py backend/app/ingestion/samsung/loader.py backend/tests
git commit -m "feat: ingest daily activity and step trend"
```

---

### Task 8: Extension du pipeline — découverte et orchestration

**Files:**
- Modify: `backend/app/ingestion/samsung/pipeline.py`
- Modify: `backend/tests/unit/test_discover_source.py`
- Create: `backend/tests/integration/test_extended_pipeline.py`

**Interfaces:**
- Consumes: tous les `map_*` (tâches 2-7) et `upsert_*` (tâches 2-7) ;
  `SamsungSource`, `discover_source`, `run_ingestion` (plan 1, tâche 13,
  signatures inchangées).
- Produces: `SamsungSource` enrichie de douze champs `Path | None` ;
  `discover_source` et `run_ingestion` étendus sans changement de
  signature.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `backend/tests/unit/test_discover_source.py` :

```python
def test_finds_extended_sources(tmp_path: Path) -> None:
    for name in (
        "com.samsung.health.nutrition.20260831162666.csv",
        "com.samsung.shealth.calories_burned.details.20260831162666.csv",
        "com.samsung.shealth.sleep.20260831162666.csv",
        "com.samsung.health.sleep_stage.20260831162666.csv",
        "com.samsung.health.hrv.20260831162666.csv",
        "com.samsung.shealth.tracker.heart_rate.20260831162666.csv",
        "com.samsung.shealth.stress.20260831162666.csv",
        "com.samsung.shealth.activity.day_summary.20260831162666.csv",
        "com.samsung.shealth.step_daily_trend.20260831162666.csv",
        "com.samsung.shealth.tracker.oxygen_saturation.20260831162666.csv",
        "com.samsung.health.respiratory_rate.20260831162666.csv",
        "com.samsung.health.skin_temperature.20260831162666.csv",
    ):
        _touch(tmp_path / name)
    _touch(tmp_path / "jsons" / "com.samsung.health.hrv" / "a" / "a.json")

    source = discover_source(tmp_path)

    assert source.nutrition_csv is not None
    assert source.calories_burned_csv is not None
    assert source.sleep_csv is not None
    assert source.sleep_stage_csv is not None
    assert source.hrv_csv is not None
    assert source.hrv_dir == tmp_path / "jsons" / "com.samsung.health.hrv"
    assert source.heart_rate_csv is not None
    assert source.stress_csv is not None
    assert source.day_summary_csv is not None
    assert source.step_daily_trend_csv is not None
    assert source.oxygen_saturation_csv is not None
    assert source.respiratory_rate_csv is not None
    assert source.skin_temperature_csv is not None


def test_extended_sources_default_to_none(tmp_path: Path) -> None:
    source = discover_source(tmp_path)

    assert source.nutrition_csv is None
    assert source.hrv_dir is None
```

Créer `backend/tests/integration/test_extended_pipeline.py` :

```python
"""Tests d'intégration de bout en bout pour l'ingestion étendue."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.models import HrvReading, IngestionRun, NutritionDetail

FIXTURES = Path(__file__).parents[1] / "fixtures" / "samsung"


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    shutil.copy(
        FIXTURES / "nutrition_sample.csv",
        tmp_path / "com.samsung.health.nutrition.20260831162666.csv",
    )
    shutil.copy(
        FIXTURES / "hrv_sample.csv",
        tmp_path / "com.samsung.health.hrv.20260831162666.csv",
    )
    shutil.copytree(FIXTURES / "hrv", tmp_path / "com.samsung.health.hrv")
    return tmp_path


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (NutritionDetail, HrvReading, IngestionRun):
        await session.execute(model.__table__.delete())
    await session.commit()


async def _count(session: AsyncSession, model: type) -> int:
    return (
        await session.execute(select(func.count()).select_from(model))
    ).scalar_one()


async def test_run_ingests_extended_families(
    session: AsyncSession, export_dir: Path
) -> None:
    run = await run_ingestion(
        session, discover_source(export_dir), kind="test", source_name="fixture"
    )

    assert run.counts["nutrition_details"] == 1
    assert run.counts["hrv_readings"] == 2
    assert await _count(session, NutritionDetail) == 1
    assert await _count(session, HrvReading) == 2


async def test_second_run_creates_no_duplicates(
    session: AsyncSession, export_dir: Path
) -> None:
    source = discover_source(export_dir)

    await run_ingestion(session, source, kind="test", source_name="fixture")
    await run_ingestion(session, source, kind="test", source_name="fixture")

    assert await _count(session, NutritionDetail) == 1
    assert await _count(session, HrvReading) == 2
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/unit/test_discover_source.py tests/integration/test_extended_pipeline.py -v`
Expected: FAIL — `AttributeError: 'SamsungSource' object has no attribute 'nutrition_csv'`

- [ ] **Step 3: Étendre le pipeline**

Modifier `backend/app/ingestion/samsung/pipeline.py`. Le dataclass
`SamsungSource` gagne douze champs, tous `Path | None = None`, ajoutés
après les champs existants pour ne rien casser côté positionnel :

```python
@dataclass(frozen=True, slots=True)
class SamsungSource:
    weight_csv: Path | None = None
    food_csv: Path | None = None
    exercise_csv: Path | None = None
    exercise_dir: Path | None = None
    phases_json: Path | None = None
    nutrition_csv: Path | None = None
    calories_burned_csv: Path | None = None
    sleep_csv: Path | None = None
    sleep_stage_csv: Path | None = None
    hrv_csv: Path | None = None
    hrv_dir: Path | None = None
    heart_rate_csv: Path | None = None
    stress_csv: Path | None = None
    day_summary_csv: Path | None = None
    step_daily_trend_csv: Path | None = None
    oxygen_saturation_csv: Path | None = None
    respiratory_rate_csv: Path | None = None
    skin_temperature_csv: Path | None = None
```

Généraliser `_exercise_dir` en une fonction réutilisable pour n'importe
quel répertoire de données, sans changer son comportement pour
`com.samsung.shealth.exercise` :

```python
def _data_dir(root: Path, name: str) -> Path | None:
    """jsons/<name> est la disposition de l'export réel ; <name> à la
    racine est celle du dossier de travail historique remonté."""
    for parts in (("jsons", name), (name,)):
        candidate = root.joinpath(*parts)
        if candidate.is_dir():
            return candidate
    return None


def _exercise_dir(root: Path) -> Path | None:
    return _data_dir(root, EXERCISE_DIR_NAME)
```

Étendre `discover_source` :

```python
HRV_DIR_NAME = "com.samsung.health.hrv"


def discover_source(root: Path) -> SamsungSource:
    exercise_candidates = sorted(
        path
        for path in root.glob("com.samsung.shealth.exercise.*.csv")
        if path.is_file() and _EXERCISE_CSV_RE.match(path.name)
    )
    phases_json = root / "phases.json"
    return SamsungSource(
        weight_csv=_latest(root, "com.samsung.health.weight.*.csv"),
        food_csv=_latest(root, "com.samsung.health.food_intake.*.csv"),
        exercise_csv=exercise_candidates[-1] if exercise_candidates else None,
        exercise_dir=_exercise_dir(root),
        phases_json=phases_json if phases_json.is_file() else None,
        nutrition_csv=_latest(root, "com.samsung.health.nutrition.*.csv"),
        calories_burned_csv=_latest(
            root, "com.samsung.shealth.calories_burned.details.*.csv"
        ),
        sleep_csv=_latest(root, "com.samsung.shealth.sleep.*.csv"),
        sleep_stage_csv=_latest(root, "com.samsung.health.sleep_stage.*.csv"),
        hrv_csv=_latest(root, "com.samsung.health.hrv.*.csv"),
        hrv_dir=_data_dir(root, HRV_DIR_NAME),
        heart_rate_csv=_latest(root, "com.samsung.shealth.tracker.heart_rate.*.csv"),
        stress_csv=_latest(root, "com.samsung.shealth.stress.*.csv"),
        day_summary_csv=_latest(
            root, "com.samsung.shealth.activity.day_summary.*.csv"
        ),
        step_daily_trend_csv=_latest(
            root, "com.samsung.shealth.step_daily_trend.*.csv"
        ),
        oxygen_saturation_csv=_latest(
            root, "com.samsung.shealth.tracker.oxygen_saturation.*.csv"
        ),
        respiratory_rate_csv=_latest(root, "com.samsung.health.respiratory_rate.*.csv"),
        skin_temperature_csv=_latest(
            root, "com.samsung.health.skin_temperature.*.csv"
        ),
    )
```

`_latest` filtre déjà sur `.glob(...).is_file()` sans exiger un horodatage
à 14 chiffres pour ces nouveaux CSV : contrairement à `exercise_csv`, aucun
autre fichier de l'export ne partage leur préfixe (vérifié sur les 87 CSV
racine), le motif `_EXERCISE_CSV_RE` ne s'applique donc qu'à l'exercice.

Étendre `run_ingestion`, dans le bloc `try` après la section
`exercise_csv` et avant `phases_json` :

```python
from app.ingestion.samsung.activity import map_daily_activity, map_step_daily_trend
from app.ingestion.samsung.energy import map_energy_expenditure
from app.ingestion.samsung.loader import (  # complète l'import existant
    upsert_daily_activities,
    upsert_energy_expenditures,
    upsert_heart_rate_readings,
    upsert_hrv_readings,
    upsert_nutrition_details,
    upsert_oxygen_saturation_readings,
    upsert_respiratory_rate_readings,
    upsert_skin_temperature_readings,
    upsert_sleep_sessions,
    upsert_sleep_stages,
    upsert_step_daily_trends,
    upsert_stress_readings,
)
from app.ingestion.samsung.nutrition_detail import map_nutrition_detail
from app.ingestion.samsung.sleep import map_sleep_session, map_sleep_stage
from app.ingestion.samsung.vitals import (
    map_heart_rate_reading,
    map_hrv_reading,
    map_oxygen_saturation_reading,
    map_respiratory_rate_reading,
    map_skin_temperature_reading,
    map_stress_reading,
)


def _mapped(csv_path: Path | None, mapper) -> list:
    if csv_path is None:
        return []
    return [
        record
        for record in (mapper(row) for row in read_samsung_csv(csv_path))
        if record is not None
    ]


async def _ingest_extended_families(
    session: AsyncSession, source: SamsungSource
) -> dict[str, int]:
    """Charge les douze familles de ce plan. Chaque famille est indépendante
    des autres : l'absence d'un CSV dans l'export ne bloque pas les autres."""
    counts: dict[str, int] = {}

    counts["nutrition_details"] = await upsert_nutrition_details(
        session, _mapped(source.nutrition_csv, map_nutrition_detail)
    )
    counts["energy_expenditures"] = await upsert_energy_expenditures(
        session, _mapped(source.calories_burned_csv, map_energy_expenditure)
    )
    counts["sleep_sessions"] = await upsert_sleep_sessions(
        session, _mapped(source.sleep_csv, map_sleep_session)
    )
    counts["sleep_stages"] = await upsert_sleep_stages(
        session, _mapped(source.sleep_stage_csv, map_sleep_stage)
    )

    if source.hrv_csv is not None and source.hrv_dir is not None:
        hrv_records = [
            record
            for record in (
                map_hrv_reading(row, source.hrv_dir)
                for row in read_samsung_csv(source.hrv_csv)
            )
            if record is not None
        ]
        counts["hrv_readings"] = await upsert_hrv_readings(session, hrv_records)

    counts["heart_rate_readings"] = await upsert_heart_rate_readings(
        session, _mapped(source.heart_rate_csv, map_heart_rate_reading)
    )
    counts["stress_readings"] = await upsert_stress_readings(
        session, _mapped(source.stress_csv, map_stress_reading)
    )
    counts["daily_activities"] = await upsert_daily_activities(
        session, _mapped(source.day_summary_csv, map_daily_activity)
    )
    counts["step_daily_trends"] = await upsert_step_daily_trends(
        session, _mapped(source.step_daily_trend_csv, map_step_daily_trend)
    )
    counts["oxygen_saturation_readings"] = await upsert_oxygen_saturation_readings(
        session, _mapped(source.oxygen_saturation_csv, map_oxygen_saturation_reading)
    )
    counts["respiratory_rate_readings"] = await upsert_respiratory_rate_readings(
        session, _mapped(source.respiratory_rate_csv, map_respiratory_rate_reading)
    )
    counts["skin_temperature_readings"] = await upsert_skin_temperature_readings(
        session, _mapped(source.skin_temperature_csv, map_skin_temperature_reading)
    )
    await session.commit()
    return counts
```

Dans `run_ingestion`, ajouter l'appel juste avant
`if source.phases_json is not None:` :

```python
        counts.update(await _ingest_extended_families(session, source))
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/unit/test_discover_source.py tests/integration/test_extended_pipeline.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Lancer toute la suite**

Run: `cd backend && uv run ruff check . && uv run pytest -v`
Expected: aucune erreur ruff, tous les tests PASS

- [ ] **Step 6: Commiter**

```bash
git add backend/app/ingestion/samsung/pipeline.py backend/tests
git commit -m "feat: wire extended ingestion families into the pipeline"
```

---

### Task 9: Vues matérialisées quotidiennes des nouvelles familles

**Files:**
- Modify: `backend/app/ingestion/refresh.py`
- Create: `backend/migrations/versions/<hash>_extended_daily_views.py`
- Create: `backend/tests/integration/test_extended_daily_views.py`

**Interfaces:**
- Consumes: le schéma de la tâche 1 ; `refresh_materialized_views`
  (plan 1, tâche 12, signature inchangée).
- Produces: `DAILY_VIEWS` porté à six entrées.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/integration/test_extended_daily_views.py` :

```python
"""Tests des vues matérialisées des familles ajoutées par ce plan."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.refresh import refresh_materialized_views
from app.ingestion.samsung.loader import (
    upsert_heart_rate_readings,
    upsert_hrv_readings,
    upsert_nutrition_details,
    upsert_sleep_sessions,
    upsert_stress_readings,
)
from app.ingestion.samsung.records import (
    HeartRateReadingRecord,
    HrvReadingRecord,
    NutritionDetailRecord,
    SleepSessionRecord,
    StressReadingRecord,
)
from app.models import (
    HeartRateReading,
    HrvReading,
    NutritionDetail,
    SleepSession,
    StressReading,
)


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (
        NutritionDetail,
        SleepSession,
        HrvReading,
        HeartRateReading,
        StressReading,
    ):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_daily_nutrition_detail_sums_macros(session: AsyncSession) -> None:
    await upsert_nutrition_details(
        session,
        [
            NutritionDetailRecord(
                source_uuid=f"meal-{i}",
                consumed_at=datetime(2026, 8, 31, 12, i, tzinfo=UTC),
                protein=10.0,
                calories=200.0,
            )
            for i in range(3)
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (
        await session.execute(
            text("SELECT protein, calories FROM mv_daily_nutrition_detail")
        )
    ).one()
    assert row.protein == 30.0
    assert row.calories == 600.0


async def test_daily_sleep_attributes_the_night_to_the_wake_day(
    session: AsyncSession,
) -> None:
    """Une nuit commencée le 31 août à 23 h et finie le 1er septembre à
    7 h doit compter pour le 1er septembre, jour du réveil."""
    await upsert_sleep_sessions(
        session,
        [
            SleepSessionRecord(
                source_uuid="night-1",
                started_at=datetime(2026, 8, 31, 21, tzinfo=UTC),
                ended_at=datetime(2026, 9, 1, 5, tzinfo=UTC),
                efficiency=80.0,
            )
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (
        await session.execute(text("SELECT day, efficiency FROM mv_daily_sleep"))
    ).one()
    assert str(row.day) == "2026-09-01"
    assert row.efficiency == 80.0


async def test_daily_vitals_averages_across_families(session: AsyncSession) -> None:
    await upsert_heart_rate_readings(
        session,
        [
            HeartRateReadingRecord(
                source_uuid="hr-1",
                started_at=datetime(2026, 8, 31, 8, tzinfo=UTC),
                mean_heart_rate=60.0,
            ),
            HeartRateReadingRecord(
                source_uuid="hr-2",
                started_at=datetime(2026, 8, 31, 20, tzinfo=UTC),
                mean_heart_rate=80.0,
            ),
        ],
    )
    await upsert_stress_readings(
        session,
        [
            StressReadingRecord(
                source_uuid="stress-1",
                started_at=datetime(2026, 8, 31, 8, tzinfo=UTC),
                score=20.0,
            )
        ],
    )
    await upsert_hrv_readings(
        session,
        [
            HrvReadingRecord(
                source_uuid="hrv-1",
                started_at=datetime(2026, 8, 31, 8, tzinfo=UTC),
                avg_sdnn=90.0,
                sample_count=2,
            )
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (
        await session.execute(
            text(
                "SELECT avg_heart_rate, avg_stress_score, avg_sdnn "
                "FROM mv_daily_vitals"
            )
        )
    ).one()
    assert row.avg_heart_rate == 70.0
    assert row.avg_stress_score == 20.0
    assert row.avg_sdnn == 90.0


async def test_concurrent_refresh_works(session: AsyncSession) -> None:
    await refresh_materialized_views(session, concurrently=False)

    await refresh_materialized_views(session, concurrently=True)
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/integration/test_extended_daily_views.py -v`
Expected: FAIL — `UndefinedTable: relation "mv_daily_nutrition_detail" does not exist`

- [ ] **Step 3: Écrire la migration des vues**

Run: `cd backend && uv run alembic revision -m "extended daily views"`

Le fichier créé a `down_revision` égal au hash de la migration de la
tâche 1. Remplacer son corps par :

```python
"""extended daily views

Trois vues, une par famille qui n'est pas déjà à grain quotidien :
nutrition_detail (par repas), sleep_session (par nuit), et les trois
signaux continus hrv/heart_rate/stress regroupés dans une seule vue
puisqu'ils partagent le même grain. energy_expenditure, daily_activity et
step_daily_trend sont déjà une ligne par jour : pas de vue pour elles.

La frontière de journée est Europe/Paris, comme les vues du plan 1.
mv_daily_sleep rattache la nuit à la date du réveil (ended_at) : une nuit
commencée avant minuit compte pour le jour où elle se termine.
"""

from alembic import op

revision = "<hash généré>"
down_revision = "<hash de la migration de tâche 1>"
branch_labels = None
depends_on = None

DAY_TZ = "Europe/Paris"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_nutrition_detail AS
        SELECT
            (consumed_at AT TIME ZONE '{DAY_TZ}')::date AS day,
            SUM(calories) AS calories,
            SUM(protein) AS protein,
            SUM(total_fat) AS total_fat,
            SUM(carbohydrate) AS carbohydrate,
            SUM(dietary_fiber) AS dietary_fiber,
            SUM(sugar) AS sugar,
            SUM(sodium) AS sodium,
            COUNT(*) AS entry_count
        FROM nutrition_detail
        GROUP BY 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_nutrition_detail_day "
        "ON mv_daily_nutrition_detail (day)"
    )

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_sleep AS
        SELECT DISTINCT ON (day)
            day,
            efficiency,
            efficiency_with_latency,
            physical_recovery,
            mental_recovery,
            deep_score,
            rem_score,
            sleep_duration
        FROM (
            SELECT
                (COALESCE(ended_at, started_at) AT TIME ZONE '{DAY_TZ}')::date AS day,
                started_at,
                efficiency,
                efficiency_with_latency,
                physical_recovery,
                mental_recovery,
                deep_score,
                rem_score,
                sleep_duration
            FROM sleep_session
        ) AS nightly
        ORDER BY day, started_at DESC
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_mv_daily_sleep_day ON mv_daily_sleep (day)")

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_vitals AS
        SELECT
            day,
            AVG(avg_heart_rate) AS avg_heart_rate,
            AVG(avg_stress_score) AS avg_stress_score,
            AVG(avg_sdnn) AS avg_sdnn
        FROM (
            SELECT
                (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                mean_heart_rate AS avg_heart_rate,
                NULL::double precision AS avg_stress_score,
                NULL::double precision AS avg_sdnn
            FROM heart_rate_reading
            UNION ALL
            SELECT
                (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                NULL::double precision,
                score,
                NULL::double precision
            FROM stress_reading
            UNION ALL
            SELECT
                (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                NULL::double precision,
                NULL::double precision,
                avg_sdnn
            FROM hrv_reading
        ) AS combined
        GROUP BY 1
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_mv_daily_vitals_day ON mv_daily_vitals (day)")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_vitals")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_sleep")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_nutrition_detail")
```

`AVG` ignore nativement les `NULL` par ligne source dans l'union : un jour
sans relevé de stress ne fait pas redescendre `avg_heart_rate` vers zéro,
conformément à la contrainte « une valeur absente est None, jamais 0 ».

- [ ] **Step 4: Appliquer la migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: `Running upgrade <hash tâche 1> -> <hash>, extended daily views`

- [ ] **Step 5: Étendre `refresh.py`**

Modifier `backend/app/ingestion/refresh.py` :

```python
DAILY_VIEWS = (
    "mv_daily_body",
    "mv_daily_nutrition",
    "mv_daily_training",
    "mv_daily_nutrition_detail",
    "mv_daily_sleep",
    "mv_daily_vitals",
)
```

Le reste du fichier (la fonction `refresh_materialized_views`) est
inchangé : elle itère déjà sur `DAILY_VIEWS`, allonger le tuple suffit.

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils passent**

Run: `cd backend && uv run pytest tests/integration -v`
Expected: PASS, toute la suite d'intégration, y compris les vues du plan 1
et de ce plan.

- [ ] **Step 7: Commiter**

```bash
git add backend/app/ingestion/refresh.py backend/migrations/versions backend/tests/integration/test_extended_daily_views.py
git commit -m "feat: add daily materialized views for extended ingestion families"
```

---

### Task 10: Migration des données réelles et vérification des chiffres de référence

**Files:**
- Modify: `backend/scripts/migrate_legacy.py`

**Interfaces:**
- Consumes: `discover_source`, `run_ingestion` (tâche 8) ;
  `app.db.session_factory` (plan 1).
- Produces: rien que d'autres tâches consomment.

Le script `migrate_legacy.py` du plan 1 pointe déjà sur
`discover_source`/`run_ingestion` : comme leurs signatures n'ont pas changé,
le script fonctionne sans modification de code une fois pointé sur l'export
complet. Cette tâche l'enrichit d'un affichage des nouveaux compteurs et
valide le résultat contre les chiffres de référence de ce plan.

- [ ] **Step 1: Étendre l'affichage du script**

Modifier la boucle d'affichage des chemins détectés dans
`backend/scripts/migrate_legacy.py`, après la ligne `("phases", ...)` :

```python
        ("nutrition détaillée", source.nutrition_csv),
        ("dépense énergétique", source.calories_burned_csv),
        ("sommeil", source.sleep_csv),
        ("phases de sommeil", source.sleep_stage_csv),
        ("VFC", source.hrv_csv),
        ("FC continue", source.heart_rate_csv),
        ("stress", source.stress_csv),
        ("activité quotidienne", source.day_summary_csv),
        ("tendance de pas", source.step_daily_trend_csv),
        ("saturation O2", source.oxygen_saturation_csv),
        ("fréquence respiratoire", source.respiratory_rate_csv),
        ("température cutanée", source.skin_temperature_csv),
```

- [ ] **Step 2: Lancer la migration sur les données réelles**

Run:
```bash
cd backend && uv run python -m scripts.migrate_legacy \
  "/home/sedelpeuch/Téléchargements/samsunghealth_sedelpeuch_20260831162666 (2)"
```
Expected: `status success`, avec des compteurs proches de :
`nutrition_details 3637`, `energy_expenditures 2877`, `sleep_sessions 1087`,
`sleep_stages 51476`, `hrv_readings 6225`, `heart_rate_readings 14929`,
`stress_readings 8678`, `daily_activities 2864`, `step_daily_trends 6318`,
`oxygen_saturation_readings 664`, `respiratory_rate_readings 671`,
`skin_temperature_readings 664`.

L'opération lit environ 20 000 fichiers JSON de binning HRV en plus des CSV
racine : compter plusieurs minutes de plus que la migration du plan 1.

- [ ] **Step 3: Vérifier les chiffres en base**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT 'nutrition_detail' AS t, count(*) FROM nutrition_detail
UNION ALL SELECT 'energy_expenditure', count(*) FROM energy_expenditure
UNION ALL SELECT 'sleep_session', count(*) FROM sleep_session
UNION ALL SELECT 'sleep_stage', count(*) FROM sleep_stage
UNION ALL SELECT 'hrv_reading', count(*) FROM hrv_reading
UNION ALL SELECT 'heart_rate_reading', count(*) FROM heart_rate_reading
UNION ALL SELECT 'stress_reading', count(*) FROM stress_reading
UNION ALL SELECT 'daily_activity', count(*) FROM daily_activity
UNION ALL SELECT 'step_daily_trend', count(*) FROM step_daily_trend
UNION ALL SELECT 'oxygen_saturation_reading', count(*) FROM oxygen_saturation_reading
UNION ALL SELECT 'respiratory_rate_reading', count(*) FROM respiratory_rate_reading
UNION ALL SELECT 'skin_temperature_reading', count(*) FROM skin_temperature_reading;"
```
Expected: les valeurs du tableau de référence, à l'unité près.

- [ ] **Step 4: Vérifier l'idempotence sur les données réelles**

Run la même commande de migration qu'à l'étape 2, puis relancer la requête
de comptage de l'étape 3.
Expected: **exactement les mêmes nombres**. Un seul écart signale une faille
d'idempotence à corriger avant de continuer.

- [ ] **Step 5: Vérifier que la VFC porte bien des agrégats**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT count(*) FILTER (WHERE avg_sdnn IS NOT NULL) AS avec_sdnn,
       count(*) FILTER (WHERE sample_count = 0) AS sans_binning
FROM hrv_reading;"
```
Expected: `avec_sdnn` proche de 6 225, `sans_binning` proche de 0 — la
quasi-totalité des relevés référencent un fichier de binning présent.

- [ ] **Step 6: Vérifier les vues quotidiennes**

Run:
```bash
docker compose exec db psql -U body -d body_analysis -c "
SELECT count(*) FROM mv_daily_nutrition_detail;
SELECT count(*) FROM mv_daily_sleep;
SELECT count(*) FROM mv_daily_vitals;"
```
Expected: des comptes de l'ordre de 747, 1 000 et 700 jours respectivement
(un jour par ligne, borné par l'étendue réelle des relevés de chaque
famille).

- [ ] **Step 7: Commiter**

```bash
git add backend/scripts/migrate_legacy.py
git commit -m "feat: extend legacy migration script with extended ingestion families"
```

---

## Definition of done du plan 1b

- [ ] `cd backend && uv run ruff check .` ne signale rien.
- [ ] `cd backend && uv run pytest` passe intégralement (tests du plan 1 et
  de ce plan).
- [ ] `uv run alembic upgrade head` puis `alembic downgrade -2` puis
  `upgrade head` s'exécutent sans erreur — les deux nouvelles migrations
  sont réversibles.
- [ ] Les douze nouvelles tables sont peuplées aux ordres de grandeur du
  tableau de référence, mesurés sur l'export réel.
- [ ] Une seconde migration ne change aucun compteur, pour chacune des
  douze tables.
- [ ] Les trois nouvelles vues matérialisées se rafraîchissent en
  `CONCURRENTLY` sans erreur.
- [ ] Aucun endpoint n'a été créé : `grep -r "APIRouter\|@app\." backend/app`
  ne référence que ce qui existait avant ce plan.

## Auto-revue

**Couverture de la spec.** Ce plan couvre entièrement la section 5.8 de la
spec (les douze sources listées y sont toutes ingérées, à l'exception
explicite et justifiée de `oxygen_saturation.raw`, remplacée par
`tracker.oxygen_saturation`) et prolonge la section 4.12 (vues
matérialisées) et 4.13 (valeurs manquantes) aux nouvelles tables. Les
sections 5.1 à 5.6 (analyses qui consomment ces données), 6 (API) et 8
(front) sont hors périmètre : elles relèvent du plan 2.

**Placeholders.** Deux valeurs ne peuvent être connues qu'à l'exécution et
sont nommées comme telles : les identifiants de révision Alembic
(`<hash généré>`, `<hash de la migration de tâche 1>`), générés par
`alembic revision`. La tâche 1 fixe déjà son `down_revision` à la valeur
connue `1717e96d7222`, tête réelle du plan 1 au moment de l'écriture de ce
plan. Aucun autre TBD.

**Cohérence des types et des signatures.** `parse_local_day` est défini en
tâche 3 (module `energy.py`) et importé tel quel en tâche 7 (module
`activity.py`) : mutualiser plutôt que dupliquer, les deux familles
partageant l'absence de `time_offset`. `resolve_json_path` et `load_json`
sont consommés en tâche 5 sans modification de signature : ils sont déjà
génériques sur n'importe quel répertoire à premier caractère hexadécimal,
pas seulement `com.samsung.shealth.exercise`, ce qui est vérifié par le
test `test_finds_extended_sources` de la tâche 8 (répertoire `hrv`,
disposition `jsons/`). `SamsungSource` gagne ses douze champs en position
finale, ce qui ne rompt aucune construction positionnelle existante dans le
plan 1 (`discover_source` est la seule à la construire, par mots-clés).
`run_ingestion` et `refresh_materialized_views` gardent exactement leurs
signatures du plan 1 ; seul le corps de `run_ingestion` et le tuple
`DAILY_VIEWS` changent.

**Où la spec s'est révélée incomplète ou imprécise**, corrigé par mesure
directe sur l'export réel plutôt que par supposition : la colonne
`carbohydrate` de `nutrition.csv`, absente de l'inventaire initial mais
remplie à 100 % ; la source correcte de la saturation en oxygène
(`tracker.oxygen_saturation`, 664 lignes avec agrégat, et non
`oxygen_saturation.raw`, 38 lignes sans agrégat exploitable) ; le nombre
réel de lignes de fréquence cardiaque avec binning (13 828, non 9 945) ;
l'absence de clé fiable entre `nutrition.csv` et `food_intake.csv`, que la
spec n'affirmait ni n'infirmait explicitement ; et les 7 segments de
`sleep_stage` orphelins, qui imposent de ne pas contraindre
`sleep_source_uuid` par une clé étrangère stricte.
