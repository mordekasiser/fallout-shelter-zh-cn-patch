from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import UnityPy


DEFAULT_STEAM_ROOT = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam"
DEFAULT_GAME_DIR = Path(
    os.environ.get(
        "FALLOUT_SHELTER_DIR",
        str(DEFAULT_STEAM_ROOT / "steamapps" / "common" / "Fallout Shelter"),
    )
)
DEFAULT_BUNDLE = DEFAULT_GAME_DIR / "FalloutShelter_Data" / "data.unity3d"


def attach_typetree_generator(env, game_dir: Path) -> None:
    from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

    generator = TypeTreeGenerator("6000.0.58f2")
    generator.load_local_game(str(game_dir))
    env.typetree_generator = generator


@dataclass(frozen=True)
class AssetSummary:
    type_name: str
    path_id: int
    name: str
    container: str
    text_size: int
    preview: str


def clean_preview(text: str, limit: int = 160) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(part.strip() for part in text.splitlines() if part.strip())
    return text[:limit]


def read_text_asset(obj) -> tuple[str, int, str]:
    data = obj.read()
    name = getattr(data, "name", "") or ""
    raw = getattr(data, "script", b"")
    if isinstance(raw, str):
        text = raw
    else:
        text = raw.decode("utf-8", errors="replace")
    return name, len(text), clean_preview(text)


def container_path_for(env, path_id: int) -> str:
    container = getattr(env, "container", None)
    if container is None:
        return ""

    path_dict = getattr(container, "path_dict", None)
    if path_dict is not None:
        return str(path_dict.get(path_id, ""))

    return ""


def iter_asset_summaries(
    bundle_path: Path, type_filter: str | None = None
) -> Iterable[AssetSummary]:
    env = UnityPy.load(str(bundle_path))
    for obj in env.objects:
        type_name = obj.type.name
        if type_filter is not None and type_name != type_filter:
            continue

        name = ""
        text_size = 0
        preview = ""

        if type_name == "TextAsset":
            name, text_size, preview = read_text_asset(obj)
        else:
            try:
                data = obj.read()
                name = getattr(data, "name", "") or ""
            except Exception:
                name = ""

        container = container_path_for(env, obj.path_id)
        yield AssetSummary(
            type_name=type_name,
            path_id=obj.path_id,
            name=name,
            container=str(container),
            text_size=text_size,
            preview=preview,
        )


def write_csv(rows: Iterable[AssetSummary], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "type_name",
                "path_id",
                "name",
                "container",
                "text_size",
                "preview",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "type_name": row.type_name,
                    "path_id": row.path_id,
                    "name": row.name,
                    "container": row.container,
                    "text_size": row.text_size,
                    "preview": row.preview,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect Fallout Shelter Unity bundle assets without modifying files."
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=DEFAULT_BUNDLE,
        help="Path to FalloutShelter_Data/data.unity3d.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("workspace/asset_inventory.csv"),
        help="CSV output path for the asset inventory.",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Only output TextAsset rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = args.bundle
    if not bundle_path.exists():
        raise SystemExit(f"Bundle not found: {bundle_path}")

    rows = iter_asset_summaries(
        bundle_path, type_filter="TextAsset" if args.text_only else None
    )

    write_csv(rows, args.output)
    print(f"Wrote asset inventory: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
