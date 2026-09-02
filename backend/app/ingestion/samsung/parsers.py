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
from datetime import UTC, datetime, timedelta, timezone
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
        tzinfo=parse_utc_offset(raw_offset) or UTC,
    )


def parse_epoch_millis(raw: object) -> datetime | None:
    millis = parse_int(raw)
    if millis is None:
        return None
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def read_samsung_csv(path: Path) -> Iterator[dict[str, str]]:
    """Itère les lignes d'un CSV Samsung.

    Le format place une ligne de métadonnées avant les en-têtes, et le
    fichier est encodé en utf-8-sig.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        next(handle, None)  # ligne de métadonnées
        yield from csv.DictReader(handle)
