from tools.find_strings import iter_string_values, looks_like_translatable_text


def test_iter_string_values_reports_nested_paths() -> None:
    value = {"root": [{"name": "Vault"}, {"name": "Dweller"}]}

    assert list(iter_string_values(value)) == [
        ("root[0].name", "Vault"),
        ("root[1].name", "Dweller"),
    ]


def test_looks_like_translatable_text_filters_asset_paths() -> None:
    assert looks_like_translatable_text("Collect 100 food")
    assert not looks_like_translatable_text("Assets/GUI/texture.png")


def test_looks_like_translatable_text_keeps_placeholder_text() -> None:
    assert looks_like_translatable_text("Collect {0} caps")
