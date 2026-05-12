from pathlib import Path
from types import SimpleNamespace
import os

import pytest

from tools.build_patch import (
    DEFAULT_TRANSLATIONS,
    assign_missing_label_fonts,
    build_patch,
    clear_custom_font_tree,
    clear_font_manager_custom_fonts,
    find_missing_translation_terms,
    force_label_true_type_tree,
    force_labels_true_type,
    get_term_english_lookup,
    load_translations,
    patch_font_tree,
    patch_fonts,
    patch_labels_true_type,
    patch_language_source,
    patch_ui_font_tree,
    patch_ui_fonts_dynamic,
    save_typetree_fast,
)
from tools.export_i2_language_source import find_language_source_objects, get_script_fullname
from tools.i2_language_source_parser import LanguageData, LanguageSourceData, TermData
from tools.i2_language_source_parser import parse_language_source
from tools.inspect_bundle import DEFAULT_BUNDLE, DEFAULT_GAME_DIR, attach_typetree_generator


TEST_GAME_DIR = os.environ.get("FALLOUT_SHELTER_TEST_GAME_DIR")
CLEAN_GAME_DIR = Path(TEST_GAME_DIR) if TEST_GAME_DIR else DEFAULT_GAME_DIR
CLEAN_BUNDLE = CLEAN_GAME_DIR / "FalloutShelter_Data" / "data.unity3d"
SIMHEI_FONT = Path(r"C:\Windows\Fonts\simhei.ttf")


def make_source() -> LanguageSourceData:
    return LanguageSourceData(
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
                term="Button_Accept",
                term_type=0,
                description="",
                languages=["ACCEPT", "ACCEPT."],
                languages_touch=["ACCEPT", "ACCEPT."],
                flags=[0, 0],
            ),
            TermData(
                term="Button_Cancel",
                term_type=0,
                description="",
                languages=["CANCEL", "ANNULER"],
                languages_touch=["CANCEL", "ANNULER"],
                flags=[0, 0],
            ),
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


def test_load_translations_skips_empty_rows(tmp_path: Path) -> None:
    translations_csv = tmp_path / "zh_cn.csv"
    translations_csv.write_text(
        "term,en,zh_cn\n"
        "Button_Accept,ACCEPT,接受\n"
        "Button_Empty,EMPTY,\n"
        ",MISSING,缺少键\n",
        encoding="utf-8",
    )

    assert load_translations(translations_csv) == {"Button_Accept": "接受"}


def test_default_translation_table_is_full_csv() -> None:
    assert DEFAULT_TRANSLATIONS == Path("translations/zh_cn_full.csv")


def test_build_patch_validates_translations_before_loading_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_path = tmp_path / "data.unity3d"
    bundle_path.write_bytes(b"bundle")
    terms_csv = tmp_path / "terms.csv"
    terms_csv.write_text(
        "term,translations,description\n"
        'A,"[""Collect {0} CAPS""]",\n',
        encoding="utf-8",
    )
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text(
        "term,en,zh_cn\nA,Collect {0} CAPS,收集瓶盖\n",
        encoding="utf-8",
    )

    def fail_load(_path: str) -> None:
        raise AssertionError("Unity bundle should not load after validation fails")

    monkeypatch.setattr("tools.build_patch.UnityPy.load", fail_load)

    with pytest.raises(ValueError, match="translation validation failed"):
        build_patch(
            bundle_path=bundle_path,
            game_dir=tmp_path,
            translations_csv=translations_csv,
            output_dir=tmp_path / "dist",
            terms_csv=terms_csv,
        )


def test_find_missing_translation_terms_reports_unmatched_keys() -> None:
    missing = find_missing_translation_terms(
        [make_source()],
        {
            "Button_Accept": "接受",
            "Button_Missing": "缺失",
        },
    )

    assert missing == ["Button_Missing"]


def test_get_term_english_lookup_reads_current_language_source() -> None:
    assert get_term_english_lookup([make_source()]) == {
        "Button_Accept": "ACCEPT",
        "Button_Cancel": "CANCEL",
    }


def test_patch_font_tree_embeds_requested_font_data() -> None:
    tree = {
        "m_Name": "FuturaStd-CondensedBold",
        "m_FontData": [1, 2, 3],
        "m_FontNames": ["Futura Std"],
    }

    changed = patch_font_tree(tree, b"font-bytes", "SimHei")

    assert changed
    assert tree["m_Name"] == "FuturaStd-CondensedBold"
    assert tree["m_FontData"] == b"font-bytes"
    assert tree["m_FontNames"] == ["SimHei"]


def test_patch_font_tree_preserves_original_asset_name() -> None:
    tree = {"m_Name": "FuturaStd-CondensedBold"}

    patch_font_tree(tree, b"font-bytes", "SimHei")
    patch_font_tree(tree, b"font-bytes", "SimHei")

    assert tree["m_Name"] == "FuturaStd-CondensedBold"


def test_save_typetree_fast_falls_back_for_fake_objects() -> None:
    obj = FakeObject("Font", {"m_FontData": []})

    assert save_typetree_fast(obj, {"m_FontData": b"abc"}) == b""
    assert obj.saved_tree == {"m_FontData": b"abc"}


def test_force_label_true_type_tree_enables_existing_field() -> None:
    tree = {"mForceTrueTypeFont": 0, "mText": "GOT IT"}

    assert force_label_true_type_tree(tree)
    assert tree["mForceTrueTypeFont"] == 1


def test_patch_fonts_updates_only_font_objects(tmp_path: Path) -> None:
    font_file = tmp_path / "simhei.ttf"
    font_file.write_bytes(b"abc")

    font_obj = FakeObject("Font", {"m_Name": "Futura", "m_FontData": []})
    text_obj = FakeObject("TextAsset", {"m_Name": "NotAFont"})
    env = SimpleNamespace(objects=[font_obj, text_obj])

    assert patch_fonts(env, font_file, "SimHei") == 1
    assert font_obj.saved_tree["m_FontData"] == b"abc"
    assert text_obj.saved_tree is None


def test_force_labels_true_type_updates_only_uilabel_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label_obj = FakeObject("MonoBehaviour", {"mForceTrueTypeFont": 0})
    other_behaviour = FakeObject("MonoBehaviour", {"mForceTrueTypeFont": 0})
    font_obj = FakeObject("Font", {"mForceTrueTypeFont": 0})
    env = SimpleNamespace(
        assets=[SimpleNamespace(version="6000.0f2")],
        objects=[label_obj, other_behaviour, font_obj],
    )

    monkeypatch.setattr("tools.build_patch.get_typetree_node", lambda *_args: object())
    monkeypatch.setattr(
        "tools.build_patch.get_script_fullname",
        lambda obj, _node: "UILabel" if obj is label_obj else "OtherBehaviour",
    )

    assert force_labels_true_type(env) == 1
    assert label_obj.saved_tree["mForceTrueTypeFont"] == 1
    assert other_behaviour.saved_tree is None
    assert font_obj.saved_tree is None


def test_assign_missing_label_fonts_uses_dominant_font_in_same_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_label = FakeObject(
        "MonoBehaviour",
        {"mTrueTypeFont": {"m_FileID": 4, "m_PathID": 1658}},
        asset_name="level254",
    )
    secondary_label = FakeObject(
        "MonoBehaviour",
        {"mTrueTypeFont": {"m_FileID": 4, "m_PathID": 1658}},
        asset_name="level254",
    )
    different_label = FakeObject(
        "MonoBehaviour",
        {"mTrueTypeFont": {"m_FileID": 4, "m_PathID": 1663}},
        asset_name="level254",
    )
    missing_label = FakeObject(
        "MonoBehaviour",
        {"mTrueTypeFont": {"m_FileID": 0, "m_PathID": 0}},
        asset_name="level254",
    )
    other_asset_missing = FakeObject(
        "MonoBehaviour",
        {"mTrueTypeFont": {"m_FileID": 0, "m_PathID": 0}},
        asset_name="level999",
    )
    env = SimpleNamespace(
        assets=[SimpleNamespace(version="6000.0f2")],
        objects=[
            primary_label,
            secondary_label,
            different_label,
            missing_label,
            other_asset_missing,
        ],
    )

    monkeypatch.setattr("tools.build_patch.get_typetree_node", lambda *_args: object())
    monkeypatch.setattr("tools.build_patch.get_script_fullname", lambda *_args: "UILabel")

    assert assign_missing_label_fonts(env) == 1
    assert missing_label.saved_tree["mTrueTypeFont"] == {
        "m_FileID": 4,
        "m_PathID": 1658,
    }
    assert other_asset_missing.saved_tree is None


def test_patch_labels_true_type_combines_font_assignment_and_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_label = FakeObject(
        "MonoBehaviour",
        {
            "mTrueTypeFont": {"m_FileID": 4, "m_PathID": 1658},
            "mForceTrueTypeFont": 0,
        },
        asset_name="level254",
    )
    missing_label = FakeObject(
        "MonoBehaviour",
        {
            "mTrueTypeFont": {"m_FileID": 0, "m_PathID": 0},
            "mForceTrueTypeFont": 0,
        },
        asset_name="level254",
    )
    env = SimpleNamespace(
        assets=[SimpleNamespace(version="6000.0f2")],
        objects=[primary_label, missing_label],
    )

    monkeypatch.setattr("tools.build_patch.get_typetree_node", lambda *_args: object())
    monkeypatch.setattr("tools.build_patch.get_script_fullname", lambda *_args: "UILabel")

    assigned_count, forced_count = patch_labels_true_type(env)

    assert assigned_count == 1
    assert forced_count == 2
    assert missing_label.saved_tree == {
        "mTrueTypeFont": {"m_FileID": 4, "m_PathID": 1658},
        "mForceTrueTypeFont": 1,
    }


def test_clear_custom_font_tree_removes_bitmap_font_overrides() -> None:
    tree = {
        "m_fontsLists": [
            {
                "m_customFonts": [
                    {"m_FileID": 0, "m_PathID": 19102},
                    {"m_FileID": 0, "m_PathID": 0},
                    {"m_FileID": 0, "m_PathID": 19180},
                ]
            },
            {"m_customFonts": []},
        ]
    }

    assert clear_custom_font_tree(tree) == 2
    assert tree["m_fontsLists"][0]["m_customFonts"] == []
    assert tree["m_fontsLists"][1]["m_customFonts"] == []


def test_clear_font_manager_custom_fonts_updates_only_font_managers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = FakeObject(
        "MonoBehaviour",
        {
            "m_fontsLists": [
                {"m_customFonts": [{"m_FileID": 0, "m_PathID": 19102}]}
            ]
        },
    )
    other = FakeObject(
        "MonoBehaviour",
        {
            "m_fontsLists": [
                {"m_customFonts": [{"m_FileID": 0, "m_PathID": 19102}]}
            ]
        },
    )
    env = SimpleNamespace(
        assets=[SimpleNamespace(version="6000.0f2")],
        objects=[manager, other],
    )

    monkeypatch.setattr("tools.build_patch.get_typetree_node", lambda *_args: object())
    monkeypatch.setattr(
        "tools.build_patch.get_script_fullname",
        lambda obj, _node: "FontManager" if obj is manager else "OtherBehaviour",
    )

    assert clear_font_manager_custom_fonts(env) == 1
    assert manager.saved_tree["m_fontsLists"][0]["m_customFonts"] == []
    assert other.saved_tree is None


def test_patch_ui_font_tree_assigns_dynamic_font() -> None:
    tree = {
        "mDynamicFont": {"m_FileID": 0, "m_PathID": 0},
        "mDynamicFontSize": 16,
        "mFont": {"mSize": 76, "mSaved": [{"index": 65}]},
    }

    assert patch_ui_font_tree(tree, {"m_FileID": 0, "m_PathID": 1658})
    assert tree["mDynamicFont"] == {"m_FileID": 0, "m_PathID": 1658}
    assert tree["mDynamicFontSize"] == 76


def test_patch_ui_fonts_dynamic_uses_font_manager_primary_font(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = FakeObject(
        "MonoBehaviour",
        {
            "m_fontsLists": [
                {
                    "m_fonts": [
                        {"m_FileID": 0, "m_PathID": 1658},
                        {"m_FileID": 0, "m_PathID": 1661},
                    ]
                }
            ]
        },
    )
    ui_font = FakeObject(
        "MonoBehaviour",
        {
            "mDynamicFont": {"m_FileID": 0, "m_PathID": 0},
            "mDynamicFontSize": 16,
            "mFont": {"mSize": 38},
        },
    )
    env = SimpleNamespace(
        assets=[SimpleNamespace(version="6000.0f2")],
        objects=[manager, ui_font],
    )

    monkeypatch.setattr("tools.build_patch.get_typetree_node", lambda *_args: object())
    monkeypatch.setattr(
        "tools.build_patch.get_script_fullname",
        lambda obj, _node: "FontManager" if obj is manager else "UIFont",
    )

    assert patch_ui_fonts_dynamic(env) == 1
    assert ui_font.saved_tree["mDynamicFont"] == {"m_FileID": 0, "m_PathID": 1658}
    assert ui_font.saved_tree["mDynamicFontSize"] == 38


def test_build_patch_writes_readable_bundle_from_real_game_data(tmp_path: Path) -> None:
    if not TEST_GAME_DIR:
        pytest.skip("set FALLOUT_SHELTER_TEST_GAME_DIR to run real game data test")

    bundle_path = CLEAN_BUNDLE if CLEAN_BUNDLE.exists() else DEFAULT_BUNDLE
    game_dir = CLEAN_GAME_DIR if CLEAN_BUNDLE.exists() else DEFAULT_GAME_DIR
    if not bundle_path.exists():
        pytest.skip(f"game bundle not found: {bundle_path}")

    terms_csv = tmp_path / "terms.csv"
    terms_csv.write_text(
        "term,translations,description\n"
        'Button_Accept,"[""ACCEPT""]",\n'
        'Button_GotIt,"[""GOT IT""]",\n',
        encoding="utf-8",
    )
    translations_csv = tmp_path / "zh.csv"
    translations_csv.write_text(
        "term,en,zh_cn\n"
        "Button_Accept,ACCEPT,接受\n"
        "Button_GotIt,GOT IT,知道了\n",
        encoding="utf-8",
    )

    result = build_patch(
        bundle_path=bundle_path,
        game_dir=game_dir,
        translations_csv=translations_csv,
        output_dir=tmp_path / "patch",
        terms_csv=terms_csv,
        font_file=SIMHEI_FONT if SIMHEI_FONT.exists() else None,
    )

    import UnityPy

    env = UnityPy.load(str(result.output_bundle))
    assert env.assets
    assert env.objects
    attach_typetree_generator(env, game_dir)
    language_sources = find_language_source_objects(env)
    source = parse_language_source(language_sources[0].get_raw_data())
    lookup = {term.term: term.languages[0] for term in source.terms}

    assert result.patched_term_count == 2
    assert result.matched_translation_count == 2
    assert lookup["Button_Accept"] == "接受"
    assert lookup["Button_GotIt"] == "知道了"
    if SIMHEI_FONT.exists():
        font_data_size = SIMHEI_FONT.stat().st_size
        fonts = [
            obj.read_typetree()
            for obj in env.objects
            if obj.type.name == "Font"
        ]
        assert result.patched_font_count == len(fonts)
        assert {font["m_FontNames"][0] for font in fonts} == {"SimHei"}
        assert {len(font["m_FontData"]) for font in fonts} == {font_data_size}
        assert result.forced_label_count > 0
        assert result.assigned_label_font_count >= 0
        assert result.cleared_custom_font_count >= 0
        assert result.patched_ui_font_count > 0

        from UnityPy.enums.ClassIDType import ClassIDType
        from UnityPy.helpers.Tpk import get_typetree_node

        mb_node = get_typetree_node(ClassIDType.MonoBehaviour, env.assets[0].version)
        ui_fonts = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                script_fullname = get_script_fullname(obj, mb_node)
            except FileNotFoundError:
                continue
            if script_fullname == "UIFont":
                ui_fonts.append(obj.read_typetree())
        assert ui_fonts
        assert all(font["mDynamicFont"]["m_PathID"] != 0 for font in ui_fonts)


def test_load_translations_preserves_edge_newlines(tmp_path: Path) -> None:
    translations_csv = tmp_path / "zh_cn.csv"
    translations_csv.write_text(
        'term,en,zh_cn\nA,"Line","\n译文\n"\n',
        encoding="utf-8",
    )

    assert load_translations(translations_csv)["A"].replace("\r\n", "\n") == "\n译文\n"


def test_load_translations_accepts_public_csv_without_english_column(
    tmp_path: Path,
) -> None:
    translations_csv = tmp_path / "zh_cn.csv"
    translations_csv.write_text("term,zh_cn\nButton_Accept,接受\n", encoding="utf-8")

    assert load_translations(translations_csv) == {"Button_Accept": "接受"}


def test_load_translations_rejects_conflicts(tmp_path: Path) -> None:
    translations_csv = tmp_path / "zh_cn.csv"
    translations_csv.write_text(
        "term,zh_cn\n"
        "Button_Accept,接受\n"
        "Button_Accept,同意\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="conflicting translation"):
        load_translations(translations_csv)


def test_patch_language_source_overwrites_english_slot_only() -> None:
    patched, count = patch_language_source(
        make_source(),
        {"Button_Accept": "接受", "Button_Missing": "不存在"},
        language_index=0,
    )

    assert count == 1
    assert patched.terms[0].languages == ["接受", "ACCEPT."]
    assert patched.terms[0].languages_touch == ["接受", "ACCEPT."]
    assert patched.terms[1].languages == ["CANCEL", "ANNULER"]


class FakeObject:
    def __init__(
        self,
        type_name: str,
        tree: dict,
        asset_name: str = "resources.assets",
        path_id: int = 1,
    ) -> None:
        self.type = SimpleNamespace(name=type_name)
        self.assets_file = SimpleNamespace(name=asset_name)
        self.path_id = path_id
        self._tree = dict(tree)
        self.saved_tree = None

    def read_typetree(self) -> dict:
        return dict(self._tree)

    def save_typetree(self, tree: dict) -> None:
        self.saved_tree = dict(tree)
        self._tree = dict(tree)
