from __future__ import annotations

import argparse
import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import UnityPy

from tools.inspect_bundle import DEFAULT_BUNDLE, DEFAULT_GAME_DIR, attach_typetree_generator


def iter_string_values(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
        return

    if isinstance(value, dict):
        for key, nested in value.items():
            next_path = f"{path}.{key}" if path else str(key)
            yield from iter_string_values(nested, next_path)
        return

    if isinstance(value, list):
        for index, nested in enumerate(value):
            next_path = f"{path}[{index}]"
            yield from iter_string_values(nested, next_path)


def looks_like_translatable_text(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 3:
        return False
    if "\\" in stripped and "/" in stripped:
        return False
    if stripped.startswith(("Assets/", "GUI/", "UI/", "MSH_", "AM_", "FX_")):
        return False
    return any(ch.isalpha() for ch in stripped)


def iter_candidate_strings(
    bundle_path: Path,
    game_dir: Path | None = None,
    asset_names: set[str] | None = None,
) -> Iterator[dict[str, str | int]]:
    env = UnityPy.load(str(bundle_path))
    if game_dir is not None:
        attach_typetree_generator(env, game_dir)
    for obj in env.objects:
        if asset_names is not None and obj.assets_file.name not in asset_names:
            continue

        if obj.type.name not in {"MonoBehaviour", "GameObject", "Material"}:
            continue

        try:
            tree = obj.read_typetree()
        except Exception:
            continue

        object_name = tree.get("m_Name", "")
        for field_path, value in iter_string_values(tree):
            if not looks_like_translatable_text(value):
                continue
            yield {
                "type_name": obj.type.name,
                "path_id": obj.path_id,
                "object_name": object_name,
                "field_path": field_path,
                "value": value.replace("\r\n", "\\n").replace("\n", "\\n"),
            }


def write_csv(rows: Iterator[dict[str, str | int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["type_name", "path_id", "object_name", "field_path", "value"],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find candidate strings inside Unity typetrees without modifying files."
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=None,
        help="Optional game root. When provided, load Managed DLLs read-only to generate MonoBehaviour typetrees.",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("workspace/candidate_strings.csv")
    )
    parser.add_argument(
        "--asset-name",
        action="append",
        default=None,
        help="Limit scanning to an internal serialized file name. Can be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.bundle.exists():
        raise SystemExit(f"Bundle not found: {args.bundle}")

    asset_names = set(args.asset_name) if args.asset_name else None
    write_csv(iter_candidate_strings(args.bundle, args.game_dir, asset_names), args.output)
    print(f"Wrote candidate strings: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
