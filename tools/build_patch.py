from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

import UnityPy
from UnityPy.enums.ClassIDType import ClassIDType
from UnityPy.helpers.Tpk import get_typetree_node
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryWriter

from tools.export_i2_language_source import find_language_source_objects, get_script_fullname
from tools.i2_language_source_parser import (
    LanguageSourceData,
    TermData,
    parse_language_source,
    serialize_language_source,
)
from tools.inspect_bundle import DEFAULT_BUNDLE, DEFAULT_GAME_DIR, attach_typetree_generator
from tools.translation_pipeline import (
    validate_file,
    validate_translations_against_terms,
)


DEFAULT_TRANSLATIONS = Path("translations/zh_cn_full.csv")
DEFAULT_OUTPUT_DIR = Path("dist/FalloutShelter_汉化补丁")
PATCH_BUNDLE_RELATIVE_PATH = Path("FalloutShelter_Data") / "data.unity3d"


@dataclass(frozen=True)
class PatchBuildResult:
    output_bundle: Path
    language_source_count: int
    patched_term_count: int
    matched_translation_count: int
    patched_font_count: int
    patched_ui_font_count: int
    forced_label_count: int
    assigned_label_font_count: int
    cleared_custom_font_count: int


def find_missing_translation_terms(
    sources: list[LanguageSourceData],
    translations: Mapping[str, str],
) -> list[str]:
    source_terms = {term.term for source in sources for term in source.terms}
    return sorted(set(translations) - source_terms)


def get_term_english_lookup(
    sources: list[LanguageSourceData],
    language_index: int = 0,
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for source in sources:
        for term in source.terms:
            if language_index < len(term.languages):
                lookup[term.term] = term.languages[language_index]
    return lookup


def load_translations(path: Path, column: str = "zh_cn") -> dict[str, str]:
    translations: dict[str, str] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = {"term", column} - fieldnames
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"translation CSV missing column(s): {missing_list}")

        for line_number, row in enumerate(reader, start=2):
            term = (row.get("term") or "").strip()
            translation = row.get(column) or ""
            if not term or not translation.strip():
                continue
            previous = translations.get(term)
            if previous is not None and previous != translation:
                raise ValueError(
                    f"conflicting translation for {term!r} at line {line_number}"
                )
            translations[term] = translation

    return translations


def _patch_term(
    term: TermData, translation: str, language_index: int
) -> TermData:
    languages = list(term.languages)
    languages_touch = list(term.languages_touch)

    if language_index >= len(languages):
        raise ValueError(
            f"term {term.term!r} has no language slot {language_index}"
        )

    languages[language_index] = translation
    if language_index < len(languages_touch):
        languages_touch[language_index] = translation

    return replace(term, languages=languages, languages_touch=languages_touch)


def patch_language_source(
    source: LanguageSourceData,
    translations: Mapping[str, str],
    language_index: int = 0,
) -> tuple[LanguageSourceData, int]:
    if language_index < 0 or language_index >= len(source.languages):
        raise ValueError(f"language index out of range: {language_index}")

    patched_count = 0
    patched_terms: list[TermData] = []
    for term in source.terms:
        translation = translations.get(term.term)
        if not translation:
            patched_terms.append(term)
            continue
        patched_terms.append(_patch_term(term, translation, language_index))
        patched_count += 1

    return replace(source, terms=patched_terms), patched_count


def patch_font_tree(tree: dict, font_data: bytes, font_name: str) -> bool:
    changed = False

    current_font_data = tree.get("m_FontData")
    if current_font_data != font_data:
        tree["m_FontData"] = font_data
        changed = True

    if tree.get("m_FontNames") != [font_name]:
        tree["m_FontNames"] = [font_name]
        changed = True

    return changed


def _write_typetree_value_fast(
    value,
    node,
    writer,
    config,
) -> None:
    align = TypeTreeHelper.metaflag_is_aligned(node.m_MetaFlag)

    func = TypeTreeHelper.FUNCTION_WRITE_MAP.get(node.m_Type)
    if func:
        func(writer, value)
    elif node.m_Type == "pair":
        _write_typetree_value_fast(value[0], node.m_Children[0], writer, config)
        _write_typetree_value_fast(value[1], node.m_Children[1], writer, config)
    elif node.m_Type == "ReferencedObject":
        for child in node.m_Children:
            if child.m_Type == "ReferencedObjectData":
                ref_type_nodes = TypeTreeHelper.get_ref_type_node(
                    value, config.assetsfile
                )
                _write_typetree_value_fast(
                    value[child.m_Name], ref_type_nodes, writer, config
                )
            else:
                _write_typetree_value_fast(
                    value[child.m_Name], child, writer, config
                )
    elif node.m_Children and node.m_Children[0].m_Type == "Array":
        array_node = node.m_Children[0]
        if TypeTreeHelper.metaflag_is_aligned(array_node.m_MetaFlag):
            align = True

        subtype = array_node.m_Children[1]
        if isinstance(value, bytes) and subtype.m_Type in {"char", "UInt8", "SInt8"}:
            writer.write_int(len(value))
            writer.write_bytes(value)
        else:
            writer.write_int(len(value))
            for sub_value in value:
                _write_typetree_value_fast(sub_value, subtype, writer, config)
    elif isinstance(value, dict):
        for child in node.m_Children:
            child_config = config
            if child.m_Type == "ManagedReferencesRegistry":
                if child_config.has_registry:
                    continue
                child_config = child_config.copy()
                child_config.has_registry = True
            _write_typetree_value_fast(value[child.m_Name], child, writer, child_config)
    else:
        for child in node.m_Children:
            child_config = config
            if child.m_Type == "ManagedReferencesRegistry":
                if child_config.has_registry:
                    continue
                child_config = child_config.copy()
                child_config.has_registry = True
            _write_typetree_value_fast(
                getattr(value, child._clean_name), child, writer, child_config
            )

    if align:
        writer.align_stream()


def save_typetree_fast(obj, tree: dict) -> bytes:
    if not hasattr(obj, "reader") or not hasattr(obj, "set_raw_data"):
        obj.save_typetree(tree)
        return b""

    writer = EndianBinaryWriter(endian=obj.reader.endian)
    node = obj._get_typetree_node(None)
    config = TypeTreeHelper.TypeTreeConfig(True, obj.assets_file, False)
    _write_typetree_value_fast(tree, node, writer, config)
    data = writer.bytes
    obj.set_raw_data(data)
    return data


def patch_fonts(env, font_file: Path, font_name: str = "SimHei") -> int:
    if not font_file.exists():
        raise FileNotFoundError(f"font file not found: {font_file}")

    font_data = font_file.read_bytes()
    if not font_data:
        raise ValueError(f"font file is empty: {font_file}")

    patched_count = 0
    for obj in env.objects:
        if obj.type.name != "Font":
            continue

        tree = obj.read_typetree()
        if patch_font_tree(tree, font_data, font_name):
            save_typetree_fast(obj, tree)
            patched_count += 1

    return patched_count


def force_label_true_type_tree(tree: dict) -> bool:
    if "mForceTrueTypeFont" not in tree:
        return False
    if tree.get("mForceTrueTypeFont") == 1:
        return False
    tree["mForceTrueTypeFont"] = 1
    return True


def force_labels_true_type(env) -> int:
    mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
    forced_count = 0

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            script_fullname = get_script_fullname(obj, mb_node)
        except Exception:
            continue
        if script_fullname != "UILabel":
            continue

        tree = obj.read_typetree()
        if force_label_true_type_tree(tree):
            obj.save_typetree(tree)
            forced_count += 1

    return forced_count


def has_missing_true_type_font(tree: dict) -> bool:
    font = tree.get("mTrueTypeFont")
    return not isinstance(font, dict) or font.get("m_PathID", 0) == 0


def has_missing_font_reference(font: object) -> bool:
    return not isinstance(font, dict) or font.get("m_PathID", 0) == 0


def get_font_reference_key(font: Mapping[str, int]) -> tuple[int, int]:
    return (font.get("m_FileID", 0), font.get("m_PathID", 0))


def assign_missing_label_fonts(env) -> int:
    mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
    label_entries = []
    dominant_fonts: dict[str, dict] = {}
    font_counts: dict[str, Counter] = defaultdict(Counter)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            script_fullname = get_script_fullname(obj, mb_node)
        except Exception:
            continue
        if script_fullname != "UILabel":
            continue

        tree = obj.read_typetree()
        asset_name = obj.assets_file.name
        label_entries.append((obj, tree, asset_name))

        font = tree.get("mTrueTypeFont")
        if not isinstance(font, dict) or font.get("m_PathID", 0) == 0:
            continue
        font_key = (font.get("m_FileID", 0), font["m_PathID"])
        font_counts[asset_name][font_key] += 1

    for asset_name, counts in font_counts.items():
        if not counts:
            continue
        file_id, path_id = counts.most_common(1)[0][0]
        dominant_fonts[asset_name] = {
            "m_FileID": file_id,
            "m_PathID": path_id,
        }

    assigned_count = 0
    for obj, tree, asset_name in label_entries:
        replacement = dominant_fonts.get(asset_name)
        if replacement is None or not has_missing_true_type_font(tree):
            continue
        tree["mTrueTypeFont"] = dict(replacement)
        obj.save_typetree(tree)
        assigned_count += 1

    return assigned_count


def patch_labels_true_type(env) -> tuple[int, int]:
    mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
    label_entries = []
    dominant_fonts: dict[str, dict] = {}
    font_counts: dict[str, Counter] = defaultdict(Counter)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            script_fullname = get_script_fullname(obj, mb_node)
        except Exception:
            continue
        if script_fullname != "UILabel":
            continue

        tree = obj.read_typetree()
        asset_name = obj.assets_file.name
        label_entries.append((obj, tree, asset_name))

        font = tree.get("mTrueTypeFont")
        if not isinstance(font, dict) or font.get("m_PathID", 0) == 0:
            continue
        font_key = (font.get("m_FileID", 0), font["m_PathID"])
        font_counts[asset_name][font_key] += 1

    for asset_name, counts in font_counts.items():
        if not counts:
            continue
        file_id, path_id = counts.most_common(1)[0][0]
        dominant_fonts[asset_name] = {
            "m_FileID": file_id,
            "m_PathID": path_id,
        }

    assigned_count = 0
    forced_count = 0
    for obj, tree, asset_name in label_entries:
        changed = False
        replacement = dominant_fonts.get(asset_name)
        if replacement is not None and has_missing_true_type_font(tree):
            tree["mTrueTypeFont"] = dict(replacement)
            assigned_count += 1
            changed = True
        if force_label_true_type_tree(tree):
            forced_count += 1
            changed = True
        if changed:
            obj.save_typetree(tree)

    return assigned_count, forced_count


def clear_custom_font_tree(tree: dict) -> int:
    cleared_count = 0
    for fonts_list in tree.get("m_fontsLists") or []:
        custom_fonts = fonts_list.get("m_customFonts")
        if not custom_fonts:
            continue
        cleared_count += sum(
            1
            for font in custom_fonts
            if isinstance(font, dict) and font.get("m_PathID", 0) != 0
        )
        fonts_list["m_customFonts"] = []
    return cleared_count


def clear_font_manager_custom_fonts(env) -> int:
    mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
    cleared_count = 0

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            script_fullname = get_script_fullname(obj, mb_node)
        except Exception:
            continue
        if script_fullname != "FontManager":
            continue

        tree = obj.read_typetree()
        object_cleared_count = clear_custom_font_tree(tree)
        if object_cleared_count:
            obj.save_typetree(tree)
            cleared_count += object_cleared_count

    return cleared_count


def find_primary_font_references(env, mb_node) -> dict[str, dict]:
    primary_fonts: dict[str, dict] = {}

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            script_fullname = get_script_fullname(obj, mb_node)
        except Exception:
            continue
        if script_fullname != "FontManager":
            continue

        tree = obj.read_typetree()
        for fonts_list in tree.get("m_fontsLists") or []:
            for font in fonts_list.get("m_fonts") or []:
                if has_missing_font_reference(font):
                    continue
                primary_fonts.setdefault(obj.assets_file.name, dict(font))
                break
            if obj.assets_file.name in primary_fonts:
                break

    for obj in env.objects:
        if obj.type.name != "Font":
            continue
        primary_fonts.setdefault(
            obj.assets_file.name,
            {"m_FileID": 0, "m_PathID": obj.path_id},
        )

    return primary_fonts


def patch_ui_font_tree(tree: dict, font: Mapping[str, int]) -> bool:
    if "mDynamicFont" not in tree:
        return False

    changed = False
    replacement = {
        "m_FileID": font.get("m_FileID", 0),
        "m_PathID": font["m_PathID"],
    }
    if tree.get("mDynamicFont") != replacement:
        tree["mDynamicFont"] = replacement
        changed = True

    if "mDynamicFontSize" in tree:
        bitmap_font = tree.get("mFont") or {}
        bitmap_size = bitmap_font.get("mSize") if isinstance(bitmap_font, dict) else None
        if isinstance(bitmap_size, int) and bitmap_size > 0:
            if tree.get("mDynamicFontSize") != bitmap_size:
                tree["mDynamicFontSize"] = bitmap_size
                changed = True

    return changed


def patch_ui_fonts_dynamic(env) -> int:
    mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
    primary_fonts = find_primary_font_references(env, mb_node)
    patched_count = 0

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            script_fullname = get_script_fullname(obj, mb_node)
        except Exception:
            continue
        if script_fullname != "UIFont":
            continue

        replacement = primary_fonts.get(obj.assets_file.name)
        if replacement is None:
            continue

        tree = obj.read_typetree()
        if patch_ui_font_tree(tree, replacement):
            obj.save_typetree(tree)
            patched_count += 1

    return patched_count


def build_patch(
    bundle_path: Path,
    game_dir: Path,
    translations_csv: Path,
    output_dir: Path,
    language_index: int = 0,
    translation_column: str = "zh_cn",
    packer: str = "none",
    terms_csv: Path | None = None,
    validate_translations: bool = True,
    require_all_translations: bool = True,
    font_file: Path | None = None,
    font_name: str = "SimHei",
) -> PatchBuildResult:
    if not bundle_path.exists():
        raise FileNotFoundError(f"bundle not found: {bundle_path}")
    if not translations_csv.exists():
        raise FileNotFoundError(f"translations CSV not found: {translations_csv}")

    translations = load_translations(translations_csv, translation_column)
    if not translations:
        raise ValueError(f"no translations found in {translations_csv}")

    if validate_translations and terms_csv is not None:
        issues = validate_file(translations_csv, terms_csv)
        if issues:
            preview = "; ".join(
                f"{issue['term']}: {issue['issue']}" for issue in issues[:5]
            )
            if len(issues) > 5:
                preview += f"; ... {len(issues) - 5} more"
            raise ValueError(
                f"translation validation failed with {len(issues)} issue(s): {preview}"
            )

    env = UnityPy.load(str(bundle_path))
    attach_typetree_generator(env, game_dir)

    language_sources = find_language_source_objects(env)
    if not language_sources:
        raise ValueError("I2.Loc.LanguageSource object not found")

    parsed_sources = [
        (obj, parse_language_source(obj.get_raw_data()))
        for obj in language_sources
    ]
    source_data = [source for _obj, source in parsed_sources]

    missing_translation_terms = find_missing_translation_terms(
        source_data, translations
    )
    if require_all_translations and missing_translation_terms:
        preview = ", ".join(missing_translation_terms[:20])
        if len(missing_translation_terms) > 20:
            preview += f", ... {len(missing_translation_terms) - 20} more"
        raise ValueError(
            "translation table contains terms not found in the language source: "
            f"{preview}"
        )

    if validate_translations and terms_csv is None:
        term_english = get_term_english_lookup(source_data, language_index)
        issues = validate_translations_against_terms(translations, term_english)
        if issues:
            preview = "; ".join(
                f"{issue['term']}: {issue['issue']}" for issue in issues[:5]
            )
            if len(issues) > 5:
                preview += f"; ... {len(issues) - 5} more"
            raise ValueError(
                f"translation validation failed with {len(issues)} issue(s): {preview}"
            )

    matched_translation_count = len(translations) - len(missing_translation_terms)
    patched_term_count = 0
    for obj, source in parsed_sources:
        patched_source, patched_count = patch_language_source(
            source, translations, language_index=language_index
        )
        if patched_count:
            obj.set_raw_data(serialize_language_source(patched_source))
            patched_term_count += patched_count

    if patched_term_count == 0:
        raise ValueError("none of the provided terms matched the language source")

    patched_font_count = 0
    patched_ui_font_count = 0
    forced_label_count = 0
    assigned_label_font_count = 0
    cleared_custom_font_count = 0
    if font_file is not None:
        patched_font_count = patch_fonts(env, font_file, font_name)
        assigned_label_font_count, forced_label_count = patch_labels_true_type(env)
        cleared_custom_font_count = clear_font_manager_custom_fonts(env)
        patched_ui_font_count = patch_ui_fonts_dynamic(env)

    output_bundle = output_dir / PATCH_BUNDLE_RELATIVE_PATH
    output_bundle.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_bundle.write_bytes(env.file.save(packer=packer))
    except MemoryError as exc:
        raise MemoryError(
            "saving the patched bundle ran out of memory; retry with "
            "--packer none to write an uncompressed bundle"
        ) from exc

    return PatchBuildResult(
        output_bundle=output_bundle,
        language_source_count=len(language_sources),
        patched_term_count=patched_term_count,
        matched_translation_count=matched_translation_count,
        patched_font_count=patched_font_count,
        patched_ui_font_count=patched_ui_font_count,
        forced_label_count=forced_label_count,
        assigned_label_font_count=assigned_label_font_count,
        cleared_custom_font_count=cleared_custom_font_count,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a drag-and-replace Fallout Shelter Chinese localization patch "
            "without writing to the game directory."
        )
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS)
    parser.add_argument(
        "--terms",
        type=Path,
        default=None,
        help=(
            "Optional exported I2 terms CSV for full missing-row validation. "
            "When omitted, validate the en/zh_cn rows in the translation CSV."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--language-index",
        type=int,
        default=0,
        help="Language slot to overwrite. 0 is English.",
    )
    parser.add_argument("--translation-column", default="zh_cn")
    parser.add_argument(
        "--packer",
        default="none",
        choices=["original", "none", "lz4", "lzma"],
        help="Unity bundle packing mode for the generated copy.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip translation CSV validation before writing the bundle.",
    )
    parser.add_argument(
        "--allow-unmatched-translations",
        action="store_true",
        help=(
            "Allow non-empty translation rows that do not exist in the target "
            "LanguageSource. By default every translated term must match."
        ),
    )
    parser.add_argument(
        "--font-file",
        type=Path,
        default=None,
        help=(
            "Optional TrueType/OpenType font to embed into Unity Font assets. "
            "Use a CJK-capable font such as C:\\Windows\\Fonts\\simhei.ttf."
        ),
    )
    parser.add_argument(
        "--font-name",
        default="SimHei",
        help="Font family name to store in Unity Font metadata.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_patch(
        bundle_path=args.bundle,
        game_dir=args.game_dir,
        translations_csv=args.translations,
        output_dir=args.output_dir,
        language_index=args.language_index,
        translation_column=args.translation_column,
        packer=args.packer,
        terms_csv=args.terms,
        validate_translations=not args.skip_validation,
        require_all_translations=not args.allow_unmatched_translations,
        font_file=args.font_file,
        font_name=args.font_name,
    )
    print(f"Wrote patch bundle: {result.output_bundle}")
    print(f"LanguageSource objects: {result.language_source_count}")
    print(f"Matched translations: {result.matched_translation_count}")
    print(f"Patched terms: {result.patched_term_count}")
    print(f"Patched fonts: {result.patched_font_count}")
    print(f"Patched UIFont dynamic fonts: {result.patched_ui_font_count}")
    print(f"Assigned missing UILabel fonts: {result.assigned_label_font_count}")
    print(f"Forced UILabel TrueType: {result.forced_label_count}")
    print(f"Cleared FontManager custom fonts: {result.cleared_custom_font_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
