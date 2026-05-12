import pytest

from tools.translate_missing import (
    DEFAULT_CONCURRENCY,
    TranslationProviderError,
    TranslationBatch,
    TranslationBatchResult,
    TranslationRow,
    apply_translations_to_rows,
    make_batches,
    normalize_translation_text,
    normalize_translations,
    parse_json_array,
    parse_args,
    persist_batch_result,
    translate_batch_with_recovery,
    translate_batches,
    write_translation_rows,
)


def test_parse_json_array_accepts_fenced_response() -> None:
    response = '```json\n[{"term":"Button_GotIt","zh_cn":"知道了"}]\n```'

    assert parse_json_array(response) == [{"term": "Button_GotIt", "zh_cn": "知道了"}]


def test_normalize_translations_reports_placeholder_mismatch() -> None:
    batch = [TranslationRow(index=0, term="A", en="Collect {0} CAPS", zh_cn="")]

    translations, issues = normalize_translations(
        [{"term": "A", "zh_cn": "收集瓶盖"}], batch
    )

    assert translations == {"A": "收集瓶盖"}
    assert "A: placeholder mismatch: {0}" in issues


def test_normalize_translations_requires_all_terms() -> None:
    batch = [
        TranslationRow(index=0, term="A", en="Accept", zh_cn=""),
        TranslationRow(index=1, term="B", en="Cancel", zh_cn=""),
    ]

    _, issues = normalize_translations([{"term": "A", "zh_cn": "接受"}], batch)

    assert "missing term: B" in issues


def test_apply_translations_to_rows_updates_original_indexes() -> None:
    rows = [
        {"term": "A", "en": "Accept", "zh_cn": ""},
        {"term": "B", "en": "Cancel", "zh_cn": ""},
    ]
    batch = [TranslationRow(index=1, term="B", en="Cancel", zh_cn="")]

    apply_translations_to_rows(rows, {"B": "取消"}, batch)

    assert rows[0]["zh_cn"] == ""
    assert rows[1]["zh_cn"] == "取消"


def test_make_batches_numbers_chunks() -> None:
    pending = [
        TranslationRow(index=index, term=f"T{index}", en=f"Text {index}", zh_cn="")
        for index in range(5)
    ]

    batches = make_batches(pending, 2)

    assert [batch.number for batch in batches] == [1, 2, 3]
    assert [[row.term for row in batch.rows] for batch in batches] == [
        ["T0", "T1"],
        ["T2", "T3"],
        ["T4"],
    ]


def test_persist_batch_result_updates_csv_and_jsonl(tmp_path) -> None:
    rows = [
        {"term": "A", "en": "Accept", "zh_cn": ""},
        {"term": "B", "en": "Cancel", "zh_cn": ""},
    ]
    csv_path = tmp_path / "zh.csv"
    jsonl_path = tmp_path / "out.jsonl"
    result = TranslationBatchResult(
        batch=TranslationBatch(
            number=1,
            rows=[TranslationRow(index=1, term="B", en="Cancel", zh_cn="")],
        ),
        translations={"B": "取消"},
    )

    persist_batch_result(
        result=result,
        rows=rows,
        fieldnames=["term", "en", "zh_cn"],
        translations_path=csv_path,
        output_jsonl=jsonl_path,
    )

    assert "B,Cancel,取消" in csv_path.read_text(encoding="utf-8")
    assert jsonl_path.read_text(encoding="utf-8").strip() == '{"term": "B", "zh_cn": "取消"}'


def test_persist_batch_result_writes_jsonl_before_csv(tmp_path, monkeypatch) -> None:
    rows = [{"term": "A", "en": "Accept", "zh_cn": ""}]
    csv_path = tmp_path / "zh.csv"
    jsonl_path = tmp_path / "out.jsonl"
    result = TranslationBatchResult(
        batch=TranslationBatch(
            number=1,
            rows=[TranslationRow(index=0, term="A", en="Accept", zh_cn="")],
        ),
        translations={"A": "接受"},
    )

    def fail_csv_write(*args, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr("tools.translate_missing.write_translation_rows", fail_csv_write)

    with pytest.raises(PermissionError, match="locked"):
        persist_batch_result(
            result=result,
            rows=rows,
            fieldnames=["term", "en", "zh_cn"],
            translations_path=csv_path,
            output_jsonl=jsonl_path,
        )

    assert jsonl_path.read_text(encoding="utf-8").strip() == '{"term": "A", "zh_cn": "接受"}'
    assert not csv_path.exists()


def test_write_translation_rows_retries_permission_error(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "zh.csv"
    calls = {"count": 0}
    original_replace = type(csv_path).replace

    def flaky_replace(self, target):
        if self.name == "zh.csv.tmp":
            calls["count"] += 1
            if calls["count"] == 1:
                raise PermissionError("locked")
        return original_replace(self, target)

    monkeypatch.setattr(type(csv_path), "replace", flaky_replace)

    write_translation_rows(
        csv_path,
        [{"term": "A", "en": "Accept", "zh_cn": "接受"}],
        ["term", "en", "zh_cn"],
        retries=2,
        retry_delay=0,
    )

    assert calls["count"] == 2
    assert "A,Accept,接受" in csv_path.read_text(encoding="utf-8")


def test_translate_batches_keeps_submissions_bounded(tmp_path, monkeypatch) -> None:
    rows = [
        {"term": f"T{index}", "en": f"Text {index}", "zh_cn": ""}
        for index in range(5)
    ]
    batches = [
        TranslationBatch(
            number=index + 1,
            rows=[
                TranslationRow(
                    index=index,
                    term=f"T{index}",
                    en=f"Text {index}",
                    zh_cn="",
                )
            ],
        )
        for index in range(5)
    ]
    in_flight = {"count": 0, "max": 0}

    def fake_translate_batch(**kwargs):
        in_flight["count"] += 1
        in_flight["max"] = max(in_flight["max"], in_flight["count"])
        batch = kwargs["batch"]
        in_flight["count"] -= 1
        return TranslationBatchResult(
            batch=batch,
            translations={batch.rows[0].term: f"译文 {batch.number}"},
        )

    monkeypatch.setattr("tools.translate_missing.translate_batch", fake_translate_batch)

    translated = translate_batches(
        batches=batches,
        rows=rows,
        fieldnames=["term", "en", "zh_cn"],
        translations_path=tmp_path / "zh.csv",
        output_jsonl=tmp_path / "out.jsonl",
        api_key="key",
        base_url="https://example.test/v1",
        model="model",
        timeout=1,
        max_retries=1,
        min_batch_size=1,
        concurrency=2,
        sleep_seconds=0,
        write_retries=1,
        write_retry_delay=0,
    )

    assert translated == 5
    assert in_flight["max"] <= 2
    assert rows[-1]["zh_cn"] == "译文 5"


def test_translate_batch_with_recovery_does_not_split_fatal_provider_errors(
    monkeypatch,
) -> None:
    calls = {"count": 0}

    def fail_provider(**kwargs):
        calls["count"] += 1
        raise TranslationProviderError("HTTP 401: invalid key", status_code=401, fatal=True)

    monkeypatch.setattr("tools.translate_missing.call_chat_completion", fail_provider)

    with pytest.raises(TranslationProviderError, match="HTTP 401"):
        translate_batch_with_recovery(
            batch=[
                TranslationRow(index=index, term=f"T{index}", en=f"Text {index}", zh_cn="")
                for index in range(4)
            ],
            api_key="key",
            base_url="https://example.test/v1",
            model="model",
            timeout=1,
            max_retries=3,
            min_batch_size=1,
            batch_label="Batch 1",
        )

    assert calls["count"] == 1


def test_parse_args_defaults_to_500_concurrency(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["translate_missing"])

    assert parse_args().concurrency == DEFAULT_CONCURRENCY


def test_normalize_translation_text_preserves_domains() -> None:
    assert normalize_translation_text("help.bethesda.net", "帮助.bethesda.net") == "help.bethesda.net"


def test_normalize_translation_text_preserves_email_markup() -> None:
    assert (
        normalize_translation_text(
            "[365136][u]privacy@support.zenimax.com[/u]",
            "privacy@support.zenimax.com",
        )
        == "[365136][u]privacy@support.zenimax.com[/u]"
    )


def test_normalize_translation_text_converts_escaped_newlines() -> None:
    assert normalize_translation_text("A\nB", "甲\\n乙") == "甲\n乙"


def test_normalize_translation_text_restores_edge_newlines() -> None:
    assert normalize_translation_text("\nA\n", "甲") == "\n甲\n"


def test_normalize_translation_text_localizes_nintendo_eshop() -> None:
    assert normalize_translation_text("NINTENDO ESHOP", "NINTENDO ESHOP") == "任天堂 eShop"


def test_parse_json_array_rejects_non_array() -> None:
    with pytest.raises(ValueError, match="JSON array"):
        parse_json_array('{"term":"A","zh_cn":"甲"}')
