from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import csv
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from tools.translation_pipeline import (
    DOMAIN_RE,
    EMAIL_RE,
    MAILTO_RE,
    MARKED_EMAIL_RE,
    URL_RE,
    extract_placeholders,
    validate_translation,
)


DEFAULT_TRANSLATIONS = Path("translations/zh_cn_full.csv")
DEFAULT_OUTPUT_JSONL = Path("workspace/translated_batches/deepseek_missing.jsonl")
DEFAULT_BACKUP_DIR = Path("workspace/backups")
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_CONCURRENCY = 500
FATAL_HTTP_STATUS_CODES = {400, 401, 403, 404}


class TranslationProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, fatal: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.fatal = fatal


@dataclass(frozen=True)
class TranslationRow:
    index: int
    term: str
    en: str
    zh_cn: str
    description: str = ""


@dataclass(frozen=True)
class TranslationBatch:
    number: int
    rows: list[TranslationRow]


@dataclass(frozen=True)
class TranslationBatchResult:
    batch: TranslationBatch
    translations: dict[str, str]


def read_translation_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        if "term" not in fieldnames or "en" not in fieldnames or "zh_cn" not in fieldnames:
            raise ValueError(f"{path} must contain term, en, and zh_cn columns")
        return [dict(row) for row in reader], fieldnames


def write_translation_rows(
    path: Path,
    rows: Iterable[dict[str, str]],
    fieldnames: list[str],
    retries: int = 20,
    retry_delay: float = 0.25,
) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    for attempt in range(1, retries + 1):
        try:
            temp_path.replace(path)
            return
        except PermissionError:
            if attempt == retries:
                raise
            time.sleep(retry_delay * attempt)


def iter_pending_rows(rows: list[dict[str, str]]) -> list[TranslationRow]:
    pending: list[TranslationRow] = []
    for index, row in enumerate(rows):
        term = (row.get("term") or "").strip()
        en = (row.get("en") or "").strip()
        zh_cn = (row.get("zh_cn") or "").strip()
        if term and en and not zh_cn:
            pending.append(
                TranslationRow(
                    index=index,
                    term=term,
                    en=en,
                    zh_cn=zh_cn,
                    description=(row.get("description") or "").strip(),
                )
            )
    return pending


def make_batches(pending: list[TranslationRow], batch_size: int) -> list[TranslationBatch]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    return [
        TranslationBatch(number=batch_index, rows=pending[start : start + batch_size])
        for batch_index, start in enumerate(range(0, len(pending), batch_size), start=1)
    ]


def make_backup(path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def build_messages(batch: list[TranslationRow], previous_error: str | None = None) -> list[dict[str, str]]:
    payload = [
        {
            "term": item.term,
            "en": item.en,
            "description": item.description,
            "placeholders": extract_placeholders(item.en),
        }
        for item in batch
    ]
    system_prompt = """你是《辐射：避难所》(Fallout Shelter) 的专业简体中文本地化译者。

输出要求：
- 只输出 JSON 数组，不要 Markdown、代码块或解释。
- 数组中每个对象必须是 {"term":"原 term","zh_cn":"简体中文译文"}。
- 必须保留输入中的 term，不能改名、遗漏或新增条目。
- 译文必须完整保留英文里的占位符、富文本标签、控制器按键和换行，例如 {0}、%d、[RB]、<color=...>、\\n。
- 如果英文包含实际换行，也必须在译文中用相同数量的实际换行保留段落结构。
- 如果英文是 URL、域名、电子邮箱、mailto 或法律/帮助链接，zh_cn 直接保留原文。
- 平台商店和网络服务名需要自然中文化，例如 NINTENDO ESHOP=任天堂 eShop，PlayStation™Network=PlayStation™Network 网络。
- UI 按钮要短，任务、成就和对白要自然。
- 专有名词按《辐射》系列习惯：Vault=避难所，Dweller=居民，Wasteland=废土，Caps=瓶盖，RadAway=消辐宁，Stimpak=治疗针，Mr. Handy=巧手先生，Lunchbox=午餐盒，Quest=任务，Outfit=服装，Weapon=武器，Junk=垃圾，SPECIAL=SPECIAL。
- 不要把中文标点误写进占位符、标签或按键标记内部。
"""
    user_prompt = "请翻译以下条目：\n" + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )
    if previous_error:
        user_prompt += "\n\n上一次输出未通过校验，请修正这些问题：\n" + previous_error
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_chat_completion(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise TranslationProviderError(
            f"HTTP {error.code}: {detail}",
            status_code=error.code,
            fatal=error.code in FATAL_HTTP_STATUS_CODES,
        ) from error

    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise TranslationProviderError(f"unexpected API response: {payload!r}") from error


def parse_json_array(content: str) -> list[dict[str, str]]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end < start:
            raise
        value = json.loads(text[start : end + 1])

    if isinstance(value, dict) and isinstance(value.get("translations"), list):
        value = value["translations"]
    if not isinstance(value, list):
        raise ValueError("response must be a JSON array")
    return value


def normalize_translation_text(en: str, zh_cn: str) -> str:
    value = zh_cn.strip()
    en_value = en.strip()
    if (
        URL_RE.match(en_value)
        or DOMAIN_RE.match(en_value)
        or MAILTO_RE.match(en_value)
        or EMAIL_RE.match(en_value)
        or MARKED_EMAIL_RE.match(en_value)
    ):
        return en_value
    if en_value.upper() == "NINTENDO ESHOP":
        return "任天堂 eShop"
    if en_value == "PlayStation™Network" or en_value == "PlayStation Network":
        return f"{en_value} 网络"
    if "\n" in en and "\\n" in value and "\n" not in value:
        value = value.replace("\\n", "\n")

    leading_newlines = len(en) - len(en.lstrip("\n"))
    trailing_newlines = len(en) - len(en.rstrip("\n"))
    return "\n" * leading_newlines + value + "\n" * trailing_newlines


def normalize_translations(
    response_items: list[dict[str, str]], batch: list[TranslationRow]
) -> tuple[dict[str, str], list[str]]:
    expected = {item.term: item for item in batch}
    translations: dict[str, str] = {}
    issues: list[str] = []

    for item in response_items:
        if not isinstance(item, dict):
            issues.append(f"invalid response item: {item!r}")
            continue
        term = str(item.get("term", "")).strip()
        zh_cn = str(item.get("zh_cn", "")).strip()
        if term not in expected:
            issues.append(f"unexpected term: {term!r}")
            continue
        if term in translations:
            issues.append(f"duplicate term: {term}")
            continue
        if not zh_cn:
            issues.append(f"empty translation: {term}")
            continue
        translations[term] = normalize_translation_text(expected[term].en, zh_cn)

    missing_terms = sorted(set(expected) - set(translations))
    for term in missing_terms:
        issues.append(f"missing term: {term}")

    for term, zh_cn in translations.items():
        item = expected[term]
        for issue in validate_translation(item.en, zh_cn):
            issues.append(f"{term}: {issue}")

    return translations, issues


def append_jsonl(path: Path, translations: dict[str, str], batch: list[TranslationRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered_terms = [item.term for item in batch]
    with path.open("a", encoding="utf-8") as handle:
        for term in ordered_terms:
            handle.write(
                json.dumps({"term": term, "zh_cn": translations[term]}, ensure_ascii=False)
                + "\n"
            )


def write_jsonl_atomic(path: Path, translations: dict[str, str], batch: list[TranslationRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    ordered_terms = [item.term for item in batch]
    appended = "".join(
        json.dumps({"term": term, "zh_cn": translations[term]}, ensure_ascii=False) + "\n"
        for term in ordered_terms
    )
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(existing + appended, encoding="utf-8")
    temp_path.replace(path)


def apply_translations_to_rows(
    rows: list[dict[str, str]],
    translations: dict[str, str],
    batch: list[TranslationRow],
) -> None:
    for item in batch:
        rows[item.index]["zh_cn"] = translations[item.term]


def translate_batch_with_recovery(
    *,
    batch: list[TranslationRow],
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    max_retries: int,
    min_batch_size: int,
    batch_label: str,
) -> dict[str, str]:
    previous_error: str | None = None

    for attempt in range(1, max_retries + 1):
        try:
            content = call_chat_completion(
                api_key=api_key,
                base_url=base_url,
                model=model,
                messages=build_messages(batch, previous_error),
                timeout=timeout,
            )
            response_items = parse_json_array(content)
            translations, issues = normalize_translations(response_items, batch)
            if not issues:
                return translations
            previous_error = "\n".join(issues[:30])
            print(f"{batch_label} attempt {attempt} failed validation: {previous_error}")
        except TranslationProviderError as error:
            previous_error = str(error)
            print(f"{batch_label} attempt {attempt} failed: {previous_error}")
            if error.fatal:
                raise
        except Exception as error:  # noqa: BLE001 - surface provider/network failures clearly.
            previous_error = str(error)
            print(f"{batch_label} attempt {attempt} failed: {previous_error}")
        time.sleep(min(2**attempt, 10))

    if len(batch) <= min_batch_size:
        raise RuntimeError(f"{batch_label} failed: {previous_error}")

    midpoint = len(batch) // 2
    print(f"{batch_label} failed as a group; splitting into {midpoint} and {len(batch) - midpoint}")
    left = translate_batch_with_recovery(
        batch=batch[:midpoint],
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        min_batch_size=min_batch_size,
        batch_label=f"{batch_label}.1",
    )
    right = translate_batch_with_recovery(
        batch=batch[midpoint:],
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        min_batch_size=min_batch_size,
        batch_label=f"{batch_label}.2",
    )
    return {**left, **right}


def translate_batch(
    *,
    batch: TranslationBatch,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    max_retries: int,
    min_batch_size: int,
) -> TranslationBatchResult:
    translations = translate_batch_with_recovery(
        batch=batch.rows,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        min_batch_size=min_batch_size,
        batch_label=f"Batch {batch.number}",
    )
    return TranslationBatchResult(batch=batch, translations=translations)


def persist_batch_result(
    *,
    result: TranslationBatchResult,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    translations_path: Path,
    output_jsonl: Path,
    write_retries: int = 20,
    write_retry_delay: float = 0.25,
) -> None:
    write_jsonl_atomic(output_jsonl, result.translations, result.batch.rows)
    apply_translations_to_rows(rows, result.translations, result.batch.rows)
    write_translation_rows(
        translations_path,
        rows,
        fieldnames,
        retries=write_retries,
        retry_delay=write_retry_delay,
    )


def translate_batches(
    *,
    batches: list[TranslationBatch],
    rows: list[dict[str, str]],
    fieldnames: list[str],
    translations_path: Path,
    output_jsonl: Path,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    max_retries: int,
    min_batch_size: int,
    concurrency: int,
    sleep_seconds: float,
    write_retries: int,
    write_retry_delay: float,
) -> int:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")

    translated_count = 0
    total_count = sum(len(batch.rows) for batch in batches)

    def persist(result: TranslationBatchResult) -> None:
        nonlocal translated_count
        persist_batch_result(
            result=result,
            rows=rows,
            fieldnames=fieldnames,
            translations_path=translations_path,
            output_jsonl=output_jsonl,
            write_retries=write_retries,
            write_retry_delay=write_retry_delay,
        )
        translated_count += len(result.batch.rows)
        print(
            f"Translated {translated_count}/{total_count} rows "
            f"(finished batch {result.batch.number}/{len(batches)})",
            flush=True,
        )
        if sleep_seconds:
            time.sleep(sleep_seconds)

    if concurrency == 1:
        for batch in batches:
            persist(
                translate_batch(
                    batch=batch,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    timeout=timeout,
                    max_retries=max_retries,
                    min_batch_size=min_batch_size,
                )
            )
        return translated_count

    print(f"Submitting {len(batches)} batches with concurrency {concurrency}", flush=True)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        batch_iter = iter(batches)
        futures: dict[Future[TranslationBatchResult], TranslationBatch] = {}

        def submit_next() -> bool:
            try:
                batch = next(batch_iter)
            except StopIteration:
                return False
            future = executor.submit(
                translate_batch,
                batch=batch,
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout,
                max_retries=max_retries,
                min_batch_size=min_batch_size,
            )
            futures[future] = batch
            return True

        for _ in range(min(concurrency, len(batches))):
            submit_next()

        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                batch = futures.pop(future)
                try:
                    persist(future.result())
                except Exception as error:
                    for pending_future in futures:
                        pending_future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise RuntimeError(f"batch {batch.number} failed") from error
                submit_next()

    return translated_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate missing zh_cn values in the Fallout Shelter CSV via a chat-completions API."
    )
    parser.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Maximum translation batches to request concurrently. File writes remain serialized.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to translate in this run. 0 means all.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to sleep between successful batches.")
    parser.add_argument("--write-retries", type=int, default=20)
    parser.add_argument("--write-retry-delay", type=float, default=0.25)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--min-batch-size",
        type=int,
        default=1,
        help="Smallest batch size to retry after automatic splitting.",
    )
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument(
        "--api-key-env",
        default="VITE_DEFAULT_API_KEY",
        help="Environment variable containing the API key.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("VITE_DEFAULT_API_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("VITE_DEFAULT_MODEL_ENDPOINT", DEFAULT_MODEL),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing API key environment variable: {args.api_key_env}")

    rows, fieldnames = read_translation_rows(args.translations)
    pending = iter_pending_rows(rows)
    if args.limit > 0:
        pending = pending[: args.limit]

    print(f"Pending rows: {len(pending)}")
    if not pending:
        return 0

    if not args.no_backup:
        backup_path = make_backup(args.translations, args.backup_dir)
        print(f"Backup: {backup_path}")

    batches = make_batches(pending, args.batch_size)
    translate_batches(
        batches=batches,
        rows=rows,
        fieldnames=fieldnames,
        translations_path=args.translations,
        output_jsonl=args.output_jsonl,
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
        max_retries=args.max_retries,
        min_batch_size=args.min_batch_size,
        concurrency=args.concurrency,
        sleep_seconds=args.sleep,
        write_retries=args.write_retries,
        write_retry_delay=args.write_retry_delay,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
