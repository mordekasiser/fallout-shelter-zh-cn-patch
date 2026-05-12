from tools.find_bundle_members import DEFAULT_NEEDLES


def test_default_needles_include_language_marker() -> None:
    assert b"languages" in DEFAULT_NEEDLES
