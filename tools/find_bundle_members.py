from __future__ import annotations

import argparse
import csv
from pathlib import Path

import UnityPy

from tools.inspect_bundle import DEFAULT_BUNDLE


DEFAULT_NEEDLES = (
    b"languages",
    b"localization",
    b"Localization",
    b"Lunchbox",
    b"LunchBoxes",
    b"Dweller",
    b"Vault",
    b"Objective",
    b"Collect",
    b"de",
    b"en",
    b"fr",
    b"ru",
)


def asset_file_bytes(asset_file) -> bytes:
    reader = asset_file.reader
    position = reader.Position
    try:
        reader.seek(0)
        return reader.read_bytes(reader.Length)
    finally:
        reader.seek(position)


def scan_bundle_members(bundle_path: Path, needles: tuple[bytes, ...] = DEFAULT_NEEDLES):
    env = UnityPy.load(str(bundle_path))
    for asset_file in env.assets:
        data = asset_file_bytes(asset_file)
        matches = []
        for needle in needles:
            if needle in data:
                matches.append(needle.decode("ascii", errors="replace"))
        if matches:
            yield {
                "name": asset_file.name,
                "size": len(data),
                "matches": ";".join(matches),
            }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find internal Unity serialized files that contain language strings."
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument(
        "--output", type=Path, default=Path("workspace/bundle_member_matches.csv")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.bundle.exists():
        raise SystemExit(f"Bundle not found: {args.bundle}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "size", "matches"])
        writer.writeheader()
        writer.writerows(scan_bundle_members(args.bundle))
    print(f"Wrote bundle member matches: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
