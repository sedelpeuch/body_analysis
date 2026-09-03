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
                print(
                    f"  {taken_on} / {tag:<8} -> photo #{photo.id} ({image_path.name})"
                )

    print(f"\n{uploaded} photo(s) traitée(s), {ignored} ignorée(s).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        type=Path,
        help="répertoire racine des photos (arborescence YYYY-MM-DD/tag.jpg)",
    )
    raise SystemExit(asyncio.run(main(parser.parse_args().root)))
