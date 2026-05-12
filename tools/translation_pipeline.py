from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_TERMS = Path("workspace/i2_terms.csv")
DEFAULT_BATCH_DIR = Path("workspace/translation_batches")
DEFAULT_TRANSLATIONS = Path("translations/zh_cn_full.csv")

RICH_TEXT_TAG_RE = (
    r"</?(?:b|i|u|s|sub|sup|color|size|quad|material|sprite|link)"
    r"(?:=[^>]+|\s+[^>]+)?>"
)
BRACED_TEXT_RE = r"\{[^}]+\}"
BRACED_TEXT_PATTERN = re.compile(BRACED_TEXT_RE)
LOCALIZABLE_BRACED_TEXT_PATTERN = re.compile(r"\{(?!\d+(?::[^}]+)?\})[^}]+\}")
STRICT_PLACEHOLDER_RE = re.compile(
    r"\{\d+(?::[^}]+)?\}|%[0-9.]*[sdif]|"
    + RICH_TEXT_TAG_RE
    + r"|\[[A-Z0-9_]+\]|\[[0-9A-Fa-f]{6}\]|\[[A-Za-z]\]|\[-\]|\[/[A-Za-z]+\]|\\n|\n",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(
    BRACED_TEXT_RE + r"|" + STRICT_PLACEHOLDER_RE.pattern,
    re.IGNORECASE,
)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
MAILTO_RE = re.compile(r"^mailto:[^\s@]+@[^\s@]+\.[^\s@]+$", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", re.IGNORECASE)
MARKED_EMAIL_RE = re.compile(
    r"^(?:\[\d+\])?(?:\[[a-z]+\])?[^\s@]+@[^\s@]+\.[^\s@\[]+(?:\[/[a-z]+\])?$",
    re.IGNORECASE,
)
DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/\S*)?$",
    re.IGNORECASE,
)
PRESERVED_ASCII_TERMS = {
    "HP",
    "SPECIAL",
    "V.A.T.S.",
    "VATs",
    "XP",
    "SOS!",
    "SOS！",
}


def contains_translatable_text(text: str) -> bool:
    without_placeholders = PLACEHOLDER_RE.sub("", text).strip()
    return bool(without_placeholders)


@dataclass(frozen=True)
class TermForTranslation:
    term: str
    en: str
    description: str


def iter_terms(path: Path = DEFAULT_TERMS) -> Iterable[TermForTranslation]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            translations = json.loads(row["translations"])
            en = translations[0] if translations else ""
            yield TermForTranslation(
                term=row["term"],
                en=en,
                description=row.get("description", ""),
            )


def read_existing_translations(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    translations: dict[str, str] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if "term" not in (reader.fieldnames or []) or "zh_cn" not in (
            reader.fieldnames or []
        ):
            raise ValueError(f"{path} must contain term and zh_cn columns")
        for row in reader:
            term = (row.get("term") or "").strip()
            zh_cn = row.get("zh_cn") or ""
            if term and zh_cn.strip():
                translations[term] = zh_cn
    return translations


def write_translation_csv(
    rows: Iterable[TermForTranslation],
    translations: dict[str, str],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["term", "en", "zh_cn"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "term": row.term,
                    "en": row.en,
                    "zh_cn": translations.get(row.term, ""),
                }
            )


def extract_placeholders(text: str) -> list[str]:
    return PLACEHOLDER_RE.findall(text)


def extract_braced_text(text: str) -> list[str]:
    return BRACED_TEXT_PATTERN.findall(text)


def extract_localizable_braced_text(text: str) -> list[str]:
    return LOCALIZABLE_BRACED_TEXT_PATTERN.findall(text)


def extract_strict_placeholders(text: str) -> list[str]:
    return STRICT_PLACEHOLDER_RE.findall(text)


def validate_translation(en: str, zh_cn: str) -> list[str]:
    issues: list[str] = []
    if en.strip() and not zh_cn.strip():
        issues.append("missing translation")
        return issues

    if "???" in zh_cn or "\ufffd" in zh_cn:
        issues.append("translation contains replacement characters")

    en_placeholders = extract_strict_placeholders(en)
    zh_placeholders = extract_strict_placeholders(zh_cn)
    en_placeholder_counts = Counter(en_placeholders)
    zh_placeholder_counts = Counter(zh_placeholders)
    for placeholder in sorted(set(en_placeholder_counts) | set(zh_placeholder_counts)):
        if zh_placeholder_counts[placeholder] != en_placeholder_counts[placeholder]:
            issues.append(f"placeholder mismatch: {placeholder}")

    if len(extract_localizable_braced_text(en)) != len(
        extract_localizable_braced_text(zh_cn)
    ):
        issues.append("braced marker count mismatch")

    if en.strip() and not CJK_RE.search(zh_cn):
        if not contains_translatable_text(en) and en_placeholders == zh_placeholders:
            return issues
        if URL_RE.match(zh_cn.strip()):
            return issues
        if MAILTO_RE.match(zh_cn.strip()):
            return issues
        if EMAIL_RE.match(zh_cn.strip()) or MARKED_EMAIL_RE.match(zh_cn.strip()):
            return issues
        if DOMAIN_RE.match(zh_cn.strip()):
            return issues
        if zh_cn.strip() in PRESERVED_ASCII_TERMS:
            return issues
        if re.search(r"[A-Za-z]{3,}", zh_cn):
            issues.append("translation appears to contain no Chinese")

    return issues


def validate_file(translations_csv: Path, terms_csv: Path = DEFAULT_TERMS) -> list[dict]:
    translations = read_existing_translations(translations_csv)
    issues = []
    for row in iter_terms(terms_csv):
        for issue in validate_translation(row.en, translations.get(row.term, "")):
            issues.append({"term": row.term, "issue": issue, "en": row.en})
    return issues


def validate_translation_csv(
    translations_csv: Path, translation_column: str = "zh_cn"
) -> list[dict]:
    issues = []
    with translations_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = {"term", translation_column} - fieldnames
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"translation CSV missing column(s): {missing_list}")
        if "en" not in fieldnames:
            return issues

        for row in reader:
            term = (row.get("term") or "").strip()
            en = row.get("en") or ""
            zh_cn = row.get(translation_column) or ""
            if not term:
                continue
            for issue in validate_translation(en, zh_cn):
                issues.append({"term": term, "issue": issue, "en": en})
    return issues


def validate_translations_against_terms(
    translations: Mapping[str, str],
    term_english: Mapping[str, str],
) -> list[dict]:
    issues = []
    for term, zh_cn in translations.items():
        en = term_english.get(term)
        if en is None:
            continue
        for issue in validate_translation(en, zh_cn):
            issues.append({"term": term, "issue": issue, "en": en})
    return issues


def write_batches(
    terms_csv: Path,
    translations_csv: Path,
    output_dir: Path,
    batch_size: int,
) -> int:
    existing = read_existing_translations(translations_csv)
    pending = [
        row
        for row in iter_terms(terms_csv)
        if row.en.strip() and not existing.get(row.term, "").strip()
    ]
    output_dir.mkdir(parents=True, exist_ok=True)

    for batch_index, start in enumerate(range(0, len(pending), batch_size), start=1):
        chunk = pending[start : start + batch_size]
        payload = [
            {"term": row.term, "en": row.en, "description": row.description}
            for row in chunk
        ]
        output_path = output_dir / f"batch_{batch_index:04d}.json"
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return len(pending)


def merge_jsonl(
    translations_csv: Path,
    output_csv: Path,
    jsonl_paths: list[Path],
    terms_csv: Path = DEFAULT_TERMS,
) -> int:
    translations = read_existing_translations(translations_csv)
    changed = 0
    for jsonl_path in jsonl_paths:
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                term = item.get("term", "").strip()
                zh_cn = item.get("zh_cn", "")
                if not term or not zh_cn.strip():
                    raise ValueError(f"invalid row in {jsonl_path}:{line_number}")
                if translations.get(term) != zh_cn:
                    translations[term] = zh_cn
                    changed += 1

    write_translation_csv(iter_terms(terms_csv), translations, output_csv)
    return changed


def make_csv(terms_csv: Path, seed_csv: Path | None, output_csv: Path) -> int:
    seed = read_existing_translations(seed_csv) if seed_csv else {}
    rows = list(iter_terms(terms_csv))
    write_translation_csv(rows, seed, output_csv)
    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Fallout Shelter zh_CN text translation files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    make_parser = subparsers.add_parser("make-csv")
    make_parser.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    make_parser.add_argument("--seed", type=Path, default=Path("translations/zh_cn.csv"))
    make_parser.add_argument("--output", type=Path, default=DEFAULT_TRANSLATIONS)

    batch_parser = subparsers.add_parser("write-batches")
    batch_parser.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    batch_parser.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS)
    batch_parser.add_argument("--output-dir", type=Path, default=DEFAULT_BATCH_DIR)
    batch_parser.add_argument("--batch-size", type=int, default=80)

    merge_parser = subparsers.add_parser("merge-jsonl")
    merge_parser.add_argument("jsonl", type=Path, nargs="+")
    merge_parser.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    merge_parser.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS)
    merge_parser.add_argument("--output", type=Path, default=DEFAULT_TRANSLATIONS)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    validate_parser.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS)
    validate_parser.add_argument("--output", type=Path, default=Path("workspace/translation_issues.json"))

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "make-csv":
        count = make_csv(args.terms, args.seed, args.output)
        print(f"Wrote translation CSV: {args.output}")
        print(f"Rows: {count}")
        return 0
    if args.command == "write-batches":
        pending_count = write_batches(
            args.terms, args.translations, args.output_dir, args.batch_size
        )
        print(f"Wrote batches to: {args.output_dir}")
        print(f"Pending rows: {pending_count}")
        return 0
    if args.command == "merge-jsonl":
        changed = merge_jsonl(args.translations, args.output, args.jsonl, args.terms)
        print(f"Merged translations: {changed}")
        print(f"Wrote translation CSV: {args.output}")
        return 0
    if args.command == "validate":
        issues = validate_file(args.translations, args.terms)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote issues: {args.output}")
        print(f"Issues: {len(issues)}")
        return 1 if issues else 0
    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
