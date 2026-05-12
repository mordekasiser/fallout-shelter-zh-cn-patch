from tools.export_i2_language_source import summarize_language_source


def test_summarize_language_source_counts_languages_and_terms() -> None:
    tree = {
        "m_Name": "I2Languages",
        "mLanguages": [{"Name": "English"}, {"Name": "French"}],
        "mTerms": [{"Term": "UI/Start"}],
        "z": 1,
    }

    summary = summarize_language_source(tree)

    assert summary["name"] == "I2Languages"
    assert summary["language_count"] == 2
    assert summary["term_count"] == 1
    assert summary["keys"] == ["mLanguages", "mTerms", "m_Name", "z"]
