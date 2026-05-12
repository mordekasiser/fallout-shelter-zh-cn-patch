from dataclasses import replace

from tools.i2_language_source_parser import (
    LanguageData,
    LanguageSourceData,
    TermData,
    UnityBinaryReader,
    UnityBinaryWriter,
    parse_language_source,
    serialize_language_source,
)


def test_unity_binary_reader_reads_aligned_strings() -> None:
    reader = UnityBinaryReader(b"\x05\x00\x00\x00Vault\x00\x00\x00")

    assert reader.read_aligned_string() == "Vault"
    assert reader.offset == 12


def test_unity_binary_reader_reads_string_arrays() -> None:
    raw = (
        b"\x02\x00\x00\x00"
        b"\x02\x00\x00\x00en\x00\x00"
        b"\x02\x00\x00\x00fr\x00\x00"
    )

    assert UnityBinaryReader(raw).read_string_array() == ["en", "fr"]


def test_unity_binary_writer_writes_aligned_strings() -> None:
    writer = UnityBinaryWriter()

    writer.write_aligned_string("Vault")

    assert writer.to_bytes() == b"\x05\x00\x00\x00Vault\x00\x00\x00"


def test_language_source_roundtrips_without_losing_metadata() -> None:
    source = LanguageSourceData(
        game_object=(0, 1001),
        enabled=True,
        script=(1, 2002),
        name="I2Languages",
        google_web_service_url="https://example.invalid",
        google_spreadsheet_key="sheet-key",
        google_spreadsheet_name="sheet-name",
        google_last_updated_version="v1",
        google_update_frequency=2,
        terms=[
            TermData(
                term="Button_Accept",
                term_type=0,
                description="",
                languages=["ACCEPT", "ACCEPT."],
                languages_touch=["ACCEPT", "ACCEPT."],
                flags=[0, 0],
            )
        ],
        languages=[
            LanguageData(name="English", code="en"),
            LanguageData(name="French (France)", code="fr"),
        ],
        case_insensitive_terms=False,
        assets=[(0, 3003)],
        never_destroy=True,
        user_agrees_to_have_it_on_the_scene=True,
        trailing_data=b"\xaa\xbb",
    )

    raw = serialize_language_source(source)

    assert parse_language_source(raw) == source
    assert serialize_language_source(parse_language_source(raw)) == raw


def test_language_source_serializes_modified_translation_slot() -> None:
    source = LanguageSourceData(
        game_object=(0, 0),
        enabled=True,
        script=(1, 10),
        name="I2Languages",
        google_web_service_url="",
        google_spreadsheet_key="",
        google_spreadsheet_name="",
        google_last_updated_version="",
        google_update_frequency=0,
        terms=[
            TermData(
                term="Button_Cancel",
                term_type=0,
                description="",
                languages=["CANCEL", "ANNULER"],
                languages_touch=["CANCEL", "ANNULER"],
                flags=[0, 0],
            )
        ],
        languages=[
            LanguageData(name="English", code="en"),
            LanguageData(name="French (France)", code="fr"),
        ],
        case_insensitive_terms=False,
        assets=[],
        never_destroy=False,
        user_agrees_to_have_it_on_the_scene=True,
    )

    term = source.terms[0]
    patched = replace(
        source,
        terms=[
            replace(
                term,
                languages=["取消", term.languages[1]],
                languages_touch=["取消", term.languages_touch[1]],
            )
        ],
    )

    reparsed = parse_language_source(serialize_language_source(patched))

    assert reparsed.terms[0].languages == ["取消", "ANNULER"]
    assert reparsed.terms[0].languages_touch == ["取消", "ANNULER"]
