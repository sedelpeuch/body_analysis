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
