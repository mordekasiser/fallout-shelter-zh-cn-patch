from tools.inspect_bundle import DEFAULT_BUNDLE, DEFAULT_GAME_DIR, clean_preview, container_path_for


def test_default_bundle_is_inside_default_game_dir() -> None:
    assert DEFAULT_BUNDLE == DEFAULT_GAME_DIR / "FalloutShelter_Data" / "data.unity3d"


def test_clean_preview_flattens_lines_and_limits_text() -> None:
    source = "  Vault\n\n Dweller \r\n Lunchbox  "

    assert clean_preview(source, limit=18) == "Vault Dweller Lunc"


def test_container_path_for_uses_unitypy_path_dict_shape() -> None:
    class Container:
        path_dict = {42: "assets/languages/en"}

    class Env:
        container = Container()

    assert container_path_for(Env(), 42) == "assets/languages/en"
    assert container_path_for(Env(), 7) == ""
