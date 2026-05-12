from __future__ import annotations

import argparse
import json
import csv
from dataclasses import asdict
from pathlib import Path
from typing import Any

import UnityPy
from UnityPy.enums.ClassIDType import ClassIDType
from UnityPy.helpers.Tpk import get_typetree_node

from tools.inspect_bundle import DEFAULT_BUNDLE, DEFAULT_GAME_DIR, attach_typetree_generator
from tools.i2_language_source_parser import parse_language_source


def get_script_fullname(obj, mb_node) -> str:
    mono_behaviour = obj.parse_monobehaviour_head(mb_node)
    script = mono_behaviour.m_Script.deref_parse_as_object()
    if script.m_Namespace:
        return f"{script.m_Namespace}.{script.m_ClassName}"
    return script.m_ClassName


def find_language_source_objects(env) -> list:
    mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
    found = []
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            if get_script_fullname(obj, mb_node) == "I2.Loc.LanguageSource":
                found.append(obj)
        except Exception:
            continue
    return found


def summarize_language_source(tree: dict[str, Any]) -> dict[str, Any]:
    languages = tree.get("mLanguages", [])
    terms = tree.get("mTerms", [])
    return {
        "name": tree.get("m_Name", ""),
        "language_count": len(languages),
        "term_count": len(terms),
        "languages": languages,
        "term_samples": terms[:20],
        "keys": sorted(tree.keys()),
    }


def export_language_source(bundle_path: Path, game_dir: Path) -> list[dict[str, Any]]:
    env = UnityPy.load(str(bundle_path))
    attach_typetree_generator(env, game_dir)
    rows = []
    for obj in find_language_source_objects(env):
        tree = obj.read_typetree()
        rows.append(
            {
                "asset_name": obj.assets_file.name,
                "path_id": obj.path_id,
                "summary": summarize_language_source(tree),
                "tree": tree,
            }
        )
    return rows


def export_language_source_terms(bundle_path: Path, game_dir: Path) -> list[dict[str, Any]]:
    env = UnityPy.load(str(bundle_path))
    attach_typetree_generator(env, game_dir)
    rows = []
    for obj in find_language_source_objects(env):
        source = parse_language_source(obj.get_raw_data())
        rows.append(
            {
                "asset_name": obj.assets_file.name,
                "path_id": obj.path_id,
                "language_source": source,
            }
        )
    return rows


def write_terms_csv(language_sources: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "asset_name",
            "path_id",
            "term",
            "term_type",
            "description",
            "languages",
            "translations",
            "flags",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in language_sources:
            source = item["language_source"]
            language_names = [language.name for language in source.languages]
            for term in source.terms:
                writer.writerow(
                    {
                        "asset_name": item["asset_name"],
                        "path_id": item["path_id"],
                        "term": term.term,
                        "term_type": term.term_type,
                        "description": term.description,
                        "languages": json.dumps(language_names, ensure_ascii=False),
                        "translations": json.dumps(term.languages, ensure_ascii=False),
                        "flags": json.dumps(term.flags, ensure_ascii=False),
                    }
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export I2 Localization LanguageSource.")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument(
        "--output", type=Path, default=Path("workspace/i2_language_source.json")
    )
    parser.add_argument(
        "--terms-csv",
        type=Path,
        default=None,
        help="Export parsed I2 terms as CSV instead of raw typetree JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.bundle.exists():
        raise SystemExit(f"Bundle not found: {args.bundle}")

    if args.terms_csv is not None:
        data = export_language_source_terms(args.bundle, args.game_dir)
        write_terms_csv(data, args.terms_csv)
        print(f"Wrote I2 terms CSV: {args.terms_csv}")
        print(f"Found LanguageSource objects: {len(data)}")
        print(f"Term count: {sum(len(item['language_source'].terms) for item in data)}")
        return 0

    data = export_language_source(args.bundle, args.game_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote I2 language source export: {args.output}")
    print(f"Found LanguageSource objects: {len(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
