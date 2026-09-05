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
