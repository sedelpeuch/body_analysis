# Refonte body_analysis — architecture FastAPI + React

Date : 2026-09-02
Statut : validé, prêt pour planification

## 1. Objectif

Remplacer l'application Streamlit actuelle (~5 150 lignes, données en CSV et
fichiers plats) par une application front/back séparée : API FastAPI sur
PostgreSQL, front React, photos dans MinIO.

La refonte poursuit trois buts :

1. **Exploiter les données inutilisées.** L'export Samsung Health contient
   452 Mo de données intra-séance (fréquence cardiaque, vitesse, cadence, GPS,
   altitude seconde par seconde) que l'application actuelle ignore
   entièrement.
2. **Sortir du fichier plat.** Les CSV sont relus et reparsés à chaque
   affichage. Aucune requête transverse n'est possible.
3. **Repenser l'organisation de l'information.** Le dashboard actuel empile
   799 lignes de vues hétérogènes ; la nouvelle navigation part des questions
   que l'utilisateur se pose.

## 2. Contexte et contraintes

- **Mono-utilisateur, réseau local uniquement.** Aucune authentification.
- **Volumes** : 647 mesures corporelles, 11 855 entrées alimentaires,
  4 734 séances, ~2,8 M points de séries temporelles, ~590 k points GPS,
  85 photos.
- Données sources : `/home/sedelpeuch/migration_body-analysis`.
- Ces volumes ne justifient ni TimescaleDB, ni file d'attente, ni cache
  distribué. PostgreSQL nu avec des index corrects suffit largement.

## 3. Décisions d'architecture

### 3.1 Où vit la logique d'analyse

Approche retenue : **hybride**.

- Les vues analytiques sont servies par des endpoints d'agrégation dédiés qui
  renvoient des données prêtes à tracer. Le navigateur ne reçoit jamais
  2,8 M de points.
- Les écritures (phases, photos, imports) passent par des ressources REST
  classiques.
- Les agrégats quotidiens vivent dans des vues matérialisées PostgreSQL,
  rafraîchies à la fin de chaque ingestion.

Rejeté : une API REST générique avec agrégation côté front. Elle imposerait
de transférer des millions de points et dupliquerait la logique métier en
TypeScript, non testée.

### 3.2 Découpage du back

```
backend/app/
  analytics/    calculs PURS, sans I/O — entrée et sortie en dataclasses
  services/     orchestration : base de données + analytics
  api/          routers minces : HTTP -> service -> schéma Pydantic
  ingestion/    samsung/{reader,mapper,loader}.py, photos.py
  models/       SQLAlchemy 2.0, typé
  schemas/      Pydantic v2
  storage/      client MinIO
```

La frontière qui porte le plus de valeur est `analytics/` : ces modules ne
connaissent ni la base ni HTTP, ce qui les rend testables en TDD sans aucune
infrastructure. Toute l'intelligence métier y vit — deltas, vitesses
mensuelles, records, zones cardiaques, splits, SWOLF, atteinte des
objectifs. `services/` fait le pont avec la base, `api/` ne fait que
traduire des requêtes HTTP.

Techniquement : SQLAlchemy 2.0 en asynchrone avec asyncpg, Alembic pour les
migrations, pydantic-settings pour la configuration, `uv` pour les
dépendances.

### 3.3 Stockage des photos

Les images vivent dans MinIO ; le back les sert lui-même plutôt que par URL
présignée. Ce choix est ce qui permet :

- le flou serveur du mode confidentiel — l'image nette ne quitte jamais le
  back ;
- la génération de vignettes mises en cache ;
- un front qui ne connaît jamais l'existence de MinIO.

Clé d'objet : `photos/{YYYY-MM-DD}/{tag}-{sha256[:8]}.{ext}`, dérivés sous
`derived/{size}/…`.

## 4. Modèle de données

Toutes les tables de faits portent un `source_uuid` unique — les `datauuid`
de l'export Samsung. Les insertions se font en `ON CONFLICT (source_uuid) DO
UPDATE`, ce qui rend **tout ré-import idempotent** : réimporter un export
plus récent met à jour l'existant et ajoute le nouveau, sans jamais créer de
doublon.

### 4.1 body_measurement (647 lignes)

`id`, `source_uuid` unique, `measured_at timestamptz`, `weight_kg`,
`body_fat_pct`, `body_fat_mass_kg`, `skeletal_muscle_mass_kg`,
`skeletal_muscle_pct`, `fat_free_mass_kg`, `fat_free_pct`,
`total_body_water_kg`, `basal_metabolic_rate_kcal`, `height_cm`.

Samsung expose à la fois des masses et des pourcentages, renseignés par des
sous-ensembles différents de mesures (638 contre 387) : on stocke les deux
familles plutôt que d'en dériver une.

### 4.2 nutrition_entry (11 855 lignes)

`id`, `source_uuid` unique, `consumed_at`, `meal_type smallint`,
`food_name`, `amount`, `unit_code smallint`, `calories`.

Encodages relevés dans les données : `meal_type` 100001 à 100006,
`unit_code` 120001, 120002, 120004, 120005 et -1. La traduction en libellés
lisibles est une table de correspondance dans `analytics/`, pas en base.

### 4.3 phase (8 lignes)

`id`, `name`, `kind` (`free` | `bulk` | `cut` | `maintain`), `starts_on`,
`ends_on`, `weight_target_kg`, `body_fat_target_pct`,
`skeletal_muscle_target_kg`, `daily_calories_target`, `notes`.

Quatre colonnes d'objectifs nullables plutôt qu'une table dédiée : le jeu
d'objectifs est fixe et connu.

`ends_on` est inclusif. **Aucune contrainte d'exclusion de chevauchement** :
les données réelles contiennent un chevauchement d'un jour (une sèche finit
le 2026-09-01, un maintien commence le 2026-09-01). La « phase courante »
est résolue en prenant le `starts_on` le plus récent antérieur ou égal à la
date du jour.

### 4.4 workout (4 734 lignes)

Résumé de séance : `source_uuid` unique, `started_at`, `ended_at`,
`duration_ms`, `sport_type smallint` (code Samsung brut), `sport text`
(résolu à l'ingestion), `distance_m`, `calories_kcal`,
`mean/max/min_heart_rate`, `mean/max_speed_mps`, `mean/max_cadence`,
`min/max_altitude_m`, `altitude_gain_m`, `altitude_loss_m`,
`start_latitude`, `start_longitude`, `vo2_max`, `sweat_loss_ml`,
`pool_length_m`, plus les seuils issus de `sensing_status` :
`max_hr_custom`, `max_hr_auto`, `hr_aerobic_threshold`,
`hr_anaerobic_threshold`, `resting_hr`.

Trois drapeaux `has_samples`, `has_locations`, `has_swim_lengths` évitent des
sous-requêtes à l'affichage des listes.

**Résolution du sport — correction d'un bug existant.** Le code actuel teste
la présence de `reps` dans `subset_data` *avant* de consulter le code sport.
Conséquence mesurée : 69 séances de natation (code 14001, contenant bien un
`poolLength` dans leurs données annexes) sont classées « Musculation », soit
21 % des séances de natation, absentes de l'analyse natation et polluant les
statistiques de musculation.

La correction retire à `reps` son rôle de classificateur. Le code
`exercise_type` fait foi, selon une table explicite :

| Code | Sport | Séances |
| --- | --- | --- |
| 1001 | Marche | 2 104 |
| 1002 | Course à pied | 149 |
| 11007 | Vélo | 129 |
| 13001 | Randonnée | 15 |
| 14001 | Natation | 330 |
| 15004 | Rameur | 85 |
| 10025 | Poids du corps | 23 |
| 10004, 10005, 10011, 10013, 10019, 10020, 10022, 10023, 10024, 10026, 10027 | Musculation | 1 044 |
| 0 | ambigu — voir ci-dessous | 926 |

Le code 0 désigne une activité personnalisée et reste le seul cas
véritablement ambigu. Il se résout par la présence de séries : avec `reps`,
c'est « Musculation » (487 séances) ; sans, « Marche » (439 séances), ce qui
préserve la continuité avec les statistiques historiques.

Un code absent de cette table n'est pas écarté : il est exposé sous
l'intitulé « Type {code} », contrairement au filtre actuel qui le fait
disparaître silencieusement.

L'ingestion couvre **les 4 734 séances**, non seulement celles postérieures
au 12/08/2024 comme aujourd'hui : le filtrage temporel devient un choix
d'affichage, plus une perte de données.

### 4.5 workout_sample (~2,8 M lignes)

`workout_id`, `at timestamptz`, `elapsed_ms`, `heart_rate smallint`,
`speed_mps real`, `distance_m real`, `calories_kcal real`,
`cadence smallint`, `segment smallint`.

Clé primaire `(workout_id, at)`, ce qui déduplique naturellement à
l'ingestion. Index BRIN sur `at` (données strictement chronologiques, index
très compact).

### 4.6 workout_location (~590 k lignes)

`workout_id`, `at`, `latitude double`, `longitude double`, `altitude real`,
`accuracy real`. Clé primaire `(workout_id, at)`.

### 4.7 swim_length (~30 k lignes)

`workout_id`, `idx smallint`, `duration_ms`, `stroke_count smallint`,
`stroke_type text`, `resting_time_ms`. Clé primaire `(workout_id, idx)`.

C'est la granularité qui rend possibles le SWOLF et l'analyse par nage.

### 4.8 strength_set (~3 000 lignes)

`workout_id`, `idx smallint`, `duration_s`, `reps smallint`, `weight_kg`,
`weight_unit text`. Clé primaire `(workout_id, idx)`.

Ces séries proviennent de la colonne `subset_data` de l'export, renseignée
pour **1 531 séances**. L'application actuelle ne s'en sert que comme indice
de classification puis jette les valeurs. Les conserver donne accès au
volume par séance (répétitions et charge), au nombre de séries, et à leur
progression dans le temps — de la matière que la refonte débloque au même
titre que les données intra-séance.

### 4.9 workout_extra (150 lignes)

`workout_id`, `kind`, `payload jsonb`, unique `(workout_id, kind)`.

Accueille les métriques avancées Myotest (asymétrie de course, etc.) et les
formats annexes rares. Les modéliser en colonnes serait du travail perdu
pour 150 séances aux schémas hétérogènes.

### 4.10 photo (85 lignes)

`id`, `taken_on date`, `tag text`, `object_key`, `sha256` unique, `width`,
`height`, `byte_size`, `content_type`.

Contrainte unique `(taken_on, tag)` : une photo par tag et par date, ce qui
reproduit exactement la sémantique actuelle du système de fichiers
(`{date}/{tag}.jpg`) et rend le front plus simple. Un nouvel envoi remplace.

Tags relevés dans les données : `face`, `profil`, `dos`, `bras`, `epaule`.

### 4.11 ingestion_run

`id`, `kind`, `source_name`, `status` (`running` | `success` | `failed`),
`started_at`, `finished_at`, `counts jsonb`, `error text`.

### 4.12 Vues matérialisées

- `mv_daily_body` — par jour, la dernière mesure du jour pour chaque
  métrique (`DISTINCT ON`).
- `mv_daily_nutrition` — par jour, calories totales et nombre d'entrées.
- `mv_daily_training` — par jour, nombre de séances, durée, calories,
  distance.

Rafraîchies en `REFRESH MATERIALIZED VIEW CONCURRENTLY` à la fin de chaque
ingestion. Elles servent le tableau de bord et les heatmaps de calendrier,
qui seraient sinon les requêtes les plus coûteuses de l'application.

### 4.13 Valeurs manquantes

260 mesures antérieures à 2024 n'ont ni pourcentage de masse grasse ni masse
musculaire. Ces absences restent `null` de bout en bout — base, API, front —
et les courbes présentent un trou. **Jamais de zéro de substitution** : une
courbe trouée est honnête, une courbe qui plonge à zéro est un mensonge.

## 5. API

Toutes les routes sont préfixées `/api`. Les erreurs suivent la RFC 9457
(`application/problem+json`), produites par des handlers FastAPI qui
traduisent les exceptions du domaine.

### Corps

- `GET /body/measurements?from&to`
- `GET /body/timeseries?from&to&metrics=weight,body_fat,muscle&resolution=raw|daily`
- `GET /body/summary` — dernières valeurs, deltas 7 / 30 / 90 jours, phase en
  cours et progression
- `GET /body/calendar?metric&year` — cellules de heatmap

### Nutrition

- `GET /nutrition/daily?from&to`
- `GET /nutrition/entries?from&to&page`
- `GET /nutrition/breakdown?from&to` — par type de repas, aliments les plus
  fréquents

### Phases

- `GET /phases`, `POST /phases`, `GET|PATCH|DELETE /phases/{id}`
- `GET /phases/current`
- `GET /phases/{id}/report` — valeurs de début et de fin, deltas, vitesse
  mensuelle, variation en pourcentage, calories moyennes, et pour chaque
  objectif son état d'atteinte
- `GET /phases/report` — bilan transverse : taux de réussite par métrique
  (l'équivalent de la page Objectifs)

**Sens d'atteinte d'un objectif.** La comparaison à la cible dépend du type
de phase et de la métrique : en sèche, la cible de poids est un plancher à
atteindre en descendant ; en prise de masse, un plafond à atteindre en
montant ; la cible de masse musculaire s'atteint toujours vers le haut ;
celle de masse grasse toujours vers le bas. Cette règle vit dans
`analytics/` et est couverte par des tests explicites.

### Entraînement

- `GET /sports` — sports présents avec leurs compteurs
- `GET /workouts?sport&from&to&limit&cursor`
- `GET /workouts/{id}` — résumé complet
- `GET /workouts/{id}/samples?points=1000` — séries décimées
- `GET /workouts/{id}/track` — GeoJSON LineString
- `GET /workouts/{id}/splits?unit=km`
- `GET /workouts/{id}/hr-zones` — temps passé par zone
- `GET /workouts/{id}/swim` — longueurs agrégées par nage, SWOLF
- `GET /workouts/{id}/strength` — séries, répétitions, charge, volume total
- `GET /workouts/stats?sport&from&to`
- `GET /workouts/records?sport`
- `GET /workouts/calendar?year&metric`

**Décimation.** Les séances longues dépassent le millier de points, au-delà
de la résolution d'un écran. La réduction se fait en SQL par moyenne sur
buckets (`width_bucket`), paramètre `points` par défaut à 1 000 et plafonné
à 5 000.

### Photos

- `GET /photos?tag`
- `POST /photos` — multipart : fichier, `taken_on`, `tag`
- `DELETE /photos/{id}`
- `GET /photos/{id}/image?size=thumb|medium|full&blur=true`

**Correction d'un bug existant.** La rotation actuelle se déclenche sur
`width > height`, ce qui retourne à tort toute photo réellement prise en
paysage. La nouvelle implémentation lit l'orientation EXIF.

### Imports

- `POST /imports/samsung-zip` — multipart
- `GET /imports`, `GET /imports/{id}`

## 6. Flux d'ingestion

1. Réception du ZIP, création d'un `ingestion_run` en statut `running`.
2. `reader` localise les trois CSV et le dossier
   `com.samsung.shealth.exercise/`.
3. `mapper` transforme les lignes en dataclasses du domaine — fonctions
   pures, testées sur des extraits des données réelles.
4. `loader` fait les upserts par lots sur `source_uuid`.
5. Pour chaque séance, les fichiers JSON annexes sont résolus depuis ses
   colonnes `live_data`, `location_data` et `additional`, puis chargés en
   `workout_sample`, `workout_location`, `swim_length`, `workout_extra`. Les
   séries de musculation sont extraites de la colonne `subset_data` de la
   ligne de séance elle-même.
6. Rafraîchissement des vues matérialisées.
7. Clôture du `ingestion_run` avec ses compteurs.

Exécuté dans un `BackgroundTask` FastAPI, le front interrogeant
`GET /imports/{id}`. Pour un usage mono-utilisateur, Celery serait du
gâchis.

**Fichiers volontairement ignorés** : `live_data_internal` et
`location_data_internal`, soit 224 Mo qui ne contiennent que des
métadonnées d'intervalle (`elapsed_time`, `interval`, `segment`) sans valeur
analytique.

**Migration initiale.** La logique d'ingestion est un service partagé,
appelé aussi bien par l'endpoint d'upload que par un script jetable
`scripts/migrate_legacy.py` pointant sur
`/home/sedelpeuch/migration_body-analysis`. Ce script charge en plus
`phases.json` et l'arborescence `photos/`. Il n'est pas une surface produit à
maintenir.

## 7. Front

### Organisation de la navigation

| Route | Rôle |
| --- | --- |
| `/` | **Aujourd'hui** — phase en cours, progression vers les objectifs, dernières séances, dernière photo |
| `/corps` | courbes poids, masse grasse, masse musculaire, masse maigre, eau ; bandes de phases superposées |
| `/corps/photos` | timeline par tag, comparateur avant/après au curseur, mode confidentiel |
| `/phases` | liste et timeline |
| `/phases/:id` | objectifs contre réalisé, courbes et photos de la période |
| `/nutrition` | calories par jour, moyennes par phase, répartition par repas |
| `/entrainement` | calendrier, volume par sport, records |
| `/entrainement/:id` | **nouveau** — courbes FC, vitesse et altitude, trace GPS, temps par zone cardiaque, splits au kilomètre, longueurs et SWOLF en natation, séries et volume en musculation |
| `/reglages` | import ZIP, gestion des photos et des phases |

`Aujourd'hui` remplace le dashboard fourre-tout actuel. `/entrainement/:id`
est la vue que l'exploitation des données intra-séance débloque, et
n'existait pas.

### Stack

Vite, React, TypeScript. TanStack Query pour le cache et l'invalidation,
Tailwind v4, shadcn/ui comme base de composants, MapLibre GL pour les traces
GPS. Le build est servi en statique par nginx : aucun runtime Node en
production.

### Direction visuelle

Volontairement non figée dans cette spec. Elle sera traitée par la skill
`frontend-design` au moment de l'implémentation, pour éviter de livrer un
thème shadcn par défaut.

## 8. Tests

- `analytics/` — tests purs, sans infrastructure. C'est là que la TDD paie :
  deltas, vitesses mensuelles, sens d'atteinte des objectifs, zones
  cardiaques, splits, SWOLF, volume de musculation, records.
- `ingestion/mapper` — fixtures extraites des données réelles, dont un cas de
  natation avec `reps` dans `subset_data` pour verrouiller la correction de
  classification.
- `services/` et `api/` — tests d'intégration sur un PostgreSQL jetable.
- Front — Vitest sur les fonctions utilitaires. Pas de test de rendu
  exhaustif : mauvais rapport valeur/coût sur une application personnelle.

## 9. Ordre de mise en oeuvre

Le périmètre est large ; il se découpe en incréments dont chacun est
vérifiable de bout en bout. L'ordre est contraint par les dépendances
réelles, pas par les couches techniques.

1. **Socle** — Compose (`db`, `minio`), modèles SQLAlchemy, migration
   Alembic initiale, application FastAPI qui démarre et répond.
2. **Ingestion des données tabulaires** — lecture des trois CSV, mapping,
   upserts idempotents, `ingestion_run`. Vérifiable : le script de migration
   charge les 647 mesures, 11 855 entrées et 4 734 séances, et un second
   passage ne crée aucun doublon.
3. **Ingestion des données intra-séance** — les JSON annexes, `swim_length`,
   `strength_set`, `workout_extra`, puis les vues matérialisées. Vérifiable :
   ~2,8 M points et ~590 k positions en base.
4. **Analytics et API de lecture** — les modules purs et les endpoints
   corps, nutrition, phases, entraînement. C'est le gros du travail testé.
5. **Photos** — MinIO, dérivés, flou, orientation EXIF, CRUD.
6. **Front** — socle Vite et direction visuelle, puis les vues dans l'ordre
   `/`, `/corps`, `/entrainement` et `/entrainement/:id`, `/phases`,
   `/nutrition`, `/corps/photos`, `/reglages`.
7. **Écritures** — CRUD phases, envoi de photos, import ZIP avec suivi de
   progression.
8. **Bascule** — comparaison des chiffres avec l'application Streamlit sur
   quelques phases connues, puis retrait de Streamlit.

L'étape 8 est la garantie de non-régression : les valeurs affichées par la
nouvelle application doivent correspondre à celles de l'ancienne, aux
corrections de bugs documentées près (classification de la natation,
orientation EXIF, séances antérieures à août 2024 désormais incluses).

## 10. Déploiement

Docker Compose, quatre services : `db` (PostgreSQL 17), `minio`, `api`
(uvicorn), `web` (nginx servant le build et proxifiant `/api`). Réseau local
uniquement, sans authentification. Sauvegarde par `pg_dump` et `mc mirror`.

## 11. Hors périmètre, volontairement

- Authentification et multi-utilisateur.
- Celery, Redis, file d'attente.
- TimescaleDB — 3,4 M de lignes ne le justifient pas.
- Une CLI comme fonctionnalité produit.
- `live_data_internal` et `location_data_internal`.
