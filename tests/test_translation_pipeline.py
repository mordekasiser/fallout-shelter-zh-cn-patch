from pathlib import Path

from tools.translation_pipeline import (
    contains_translatable_text,
    extract_braced_text,
    extract_localizable_braced_text,
    extract_placeholders,
    extract_strict_placeholders,
    merge_jsonl,
    read_existing_translations,
    validate_translation_csv,
    validate_translations_against_terms,
    validate_translation,
    write_batches,
)


def test_extract_placeholders_keeps_ui_tokens_and_format_values() -> None:
    text = "Press [RB] to heal {0} Dwellers by %d%.\n<size=12>OK</size>"

    assert extract_placeholders(text) == [
        "[RB]",
        "{0}",
        "%d",
        "\n",
        "<size=12>",
        "</size>",
    ]


def test_extract_placeholders_keeps_named_and_color_tokens() -> None:
    text = "Welcome {OVERSEER}. [ffff00]Redeem[-] [u]Unity[/u]"

    assert extract_placeholders(text) == [
        "{OVERSEER}",
        "[ffff00]",
        "[-]",
        "[u]",
        "[/u]",
    ]


def test_extract_strict_placeholders_allows_localized_braced_text() -> None:
    text = "Welcome {监督者}. [ffff00]Redeem[-] [u]Unity[/u] {0}"

    assert extract_strict_placeholders(text) == [
        "[ffff00]",
        "[-]",
        "[u]",
        "[/u]",
        "{0}",
    ]


def test_extract_braced_text_tracks_localizable_markers() -> None:
    assert extract_braced_text("{BUILD} a {ROOM}") == ["{BUILD}", "{ROOM}"]


def test_extract_localizable_braced_text_excludes_numbered_placeholders() -> None:
    assert extract_localizable_braced_text("{0} {BUILD}") == ["{BUILD}"]


def test_extract_placeholders_does_not_treat_dialogue_angle_text_as_tag() -> None:
    assert extract_placeholders("<Hack the machine>") == []


def test_validate_translation_allows_translated_dialogue_angle_text() -> None:
    assert validate_translation("<Hack the machine>", "<骇入机器>") == []


def test_validate_translation_reports_missing_placeholder() -> None:
    issues = validate_translation("Collect {0} CAPS", "收集瓶盖")

    assert "placeholder mismatch: {0}" in issues


def test_validate_translation_reports_replacement_characters() -> None:
    issues = validate_translation("Hello", "????")

    assert "translation contains replacement characters" in issues


def test_validate_translation_csv_uses_embedded_english_text(tmp_path: Path) -> None:
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text(
        "term,en,zh_cn\nA,Collect {0} CAPS,收集瓶盖\n",
        encoding="utf-8",
    )

    assert validate_translation_csv(translations_csv) == [
        {
            "term": "A",
            "issue": "placeholder mismatch: {0}",
            "en": "Collect {0} CAPS",
        }
    ]


def test_validate_translation_csv_allows_public_csv_without_english_column(
    tmp_path: Path,
) -> None:
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text("term,zh_cn\nA,收集瓶盖\n", encoding="utf-8")

    assert validate_translation_csv(translations_csv) == []


def test_validate_translations_against_terms_uses_current_game_text() -> None:
    assert validate_translations_against_terms(
        {"A": "收集瓶盖"},
        {"A": "Collect {0} CAPS"},
    ) == [
        {
            "term": "A",
            "issue": "placeholder mismatch: {0}",
            "en": "Collect {0} CAPS",
        }
    ]


def test_validate_translation_reports_extra_placeholder() -> None:
    issues = validate_translation("Hello there.", "你好。\n")

    assert "placeholder mismatch: \n" in issues


def test_validate_translation_allows_localized_named_braced_text() -> None:
    issues = validate_translation("Hello {OVERSEER}", "你好 {监督者}")

    assert issues == []


def test_validate_translation_reports_missing_localized_braced_marker() -> None:
    issues = validate_translation("{PRESS} [A] to confirm.", "按 [A] 确认。")

    assert "braced marker count mismatch" in issues


def test_validate_translation_reports_color_tag_mismatch() -> None:
    issues = validate_translation("[ffff00]Redeem[-]", "[ffff00]兑换")

    assert "placeholder mismatch: [-]" in issues


def test_validate_translation_reports_inline_style_tag_mismatch() -> None:
    issues = validate_translation("[u]Privacy[/u]", "[u]隐私")

    assert "placeholder mismatch: [/u]" in issues


def test_validate_translation_allows_localized_bracketed_dialogue() -> None:
    assert (
        validate_translation(
            "[High-pitched guttural shriek]",
            "[高亢的喉部尖啸]",
        )
        == []
    )


def test_validate_translation_allows_preserved_urls() -> None:
    issues = validate_translation(
        "https://documents.bethesda.net/en/code-of-conduct",
        "https://documents.bethesda.net/en/code-of-conduct",
    )

    assert issues == []


def test_validate_translation_allows_preserved_domains() -> None:
    issues = validate_translation("help.bethesda.net", "help.bethesda.net")

    assert issues == []


def test_validate_translation_allows_preserved_email_markup() -> None:
    issues = validate_translation(
        "[365136][u]privacy@support.zenimax.com[/u]",
        "[365136][u]privacy@support.zenimax.com[/u]",
    )

    assert issues == []


def test_validate_translation_allows_preserved_mailto() -> None:
    assert validate_translation("mailto:privacy@example.com", "mailto:privacy@example.com") == []


def test_validate_translation_allows_preserved_ascii_terms() -> None:
    assert validate_translation("XP", "XP") == []
    assert validate_translation("SOS!", "SOS！") == []


def test_validate_translation_allows_placeholder_only_text() -> None:
    assert validate_translation("[REDACTED]", "[REDACTED]") == []


def test_contains_translatable_text_ignores_placeholders() -> None:
    assert not contains_translatable_text("[REDACTED]")
    assert contains_translatable_text("<Hack the machine>")


def test_read_existing_translations_preserves_edge_newlines(tmp_path: Path) -> None:
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text(
        'term,en,zh_cn\nA,"Line","\n译文\n"\n',
        encoding="utf-8",
    )

    assert read_existing_translations(translations_csv)["A"].replace("\r\n", "\n") == "\n译文\n"


def test_write_batches_skips_existing_translations(tmp_path: Path) -> None:
    terms_csv = tmp_path / "terms.csv"
    terms_csv.write_text(
        "term,translations,description\n"
        'A,"[""Alpha""]",\n'
        'B,"[""Beta""]",\n',
        encoding="utf-8",
    )
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text("term,en,zh_cn\nA,Alpha,阿尔法\n", encoding="utf-8")

    pending = write_batches(terms_csv, translations_csv, tmp_path / "batches", 1)

    assert pending == 1
    assert (tmp_path / "batches" / "batch_0001.json").exists()


def test_merge_jsonl_updates_translation_csv(tmp_path: Path) -> None:
    terms_csv = tmp_path / "terms.csv"
    terms_csv.write_text(
        "term,translations,description\n"
        'A,"[""Alpha""]",\n',
        encoding="utf-8",
    )
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text("term,en,zh_cn\nA,Alpha,\n", encoding="utf-8")
    jsonl = tmp_path / "batch.jsonl"
    jsonl.write_text('{"term":"A","zh_cn":"阿尔法"}\n', encoding="utf-8")

    changed = merge_jsonl(translations_csv, translations_csv, [jsonl], terms_csv)

    assert changed == 1
    assert "阿尔法" in translations_csv.read_text(encoding="utf-8")


def test_merge_jsonl_preserves_edge_newlines(tmp_path: Path) -> None:
    terms_csv = tmp_path / "terms.csv"
    terms_csv.write_text(
        "term,translations,description\n"
        'A,"[""Alpha""]",\n',
        encoding="utf-8",
    )
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text("term,en,zh_cn\nA,Alpha,\n", encoding="utf-8")
    jsonl = tmp_path / "batch.jsonl"
    jsonl.write_text(
        '{"term":"A","zh_cn":"\\n阿尔法\\n"}\n',
        encoding="utf-8",
    )

    merge_jsonl(translations_csv, translations_csv, [jsonl], terms_csv)

    assert read_existing_translations(translations_csv)["A"] == "\n阿尔法\n"
