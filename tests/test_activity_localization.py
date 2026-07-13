from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT_ROOT = ROOT / "activity" / "client" / "src"
LOCALES_ROOT = CLIENT_ROOT / "i18n" / "locales"
TRANSLATION_CALL = re.compile(r"(?:\$t|\bt)\(\s*[\"']([^\"']+)[\"']")
PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
TEXT_SUFFIXES = {".css", ".html", ".json", ".ts", ".vue"}


def load_locale(locale: str) -> dict[str, str]:
    path = LOCALES_ROOT / f"{locale}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_locale_dictionaries_have_matching_keys_and_placeholders() -> None:
    english = load_locale("en")
    russian = load_locale("ru")

    assert english.keys() == russian.keys()
    assert len(english) >= 250
    assert all(value.strip() for value in english.values())
    assert all(value.strip() for value in russian.values())

    for key, english_message in english.items():
        assert set(PLACEHOLDER.findall(english_message)) == set(PLACEHOLDER.findall(russian[key])), key


def test_literal_translation_keys_exist_in_both_locales() -> None:
    english = load_locale("en")
    russian = load_locale("ru")
    missing: dict[str, list[str]] = {}

    for path in CLIENT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".ts", ".vue"}:
            continue
        for key in TRANSLATION_CALL.findall(path.read_text(encoding="utf-8")):
            if key not in english or key not in russian:
                missing.setdefault(path.relative_to(ROOT).as_posix(), []).append(key)

    assert missing == {}


def test_activity_sources_are_valid_utf8_without_mojibake() -> None:
    forbidden_fragments = ("\ufffd", "Ã", "Â", "Ð", "Ñ")

    for path in CLIENT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_bytes().decode("utf-8", errors="strict")
        assert "\x00" not in text, path
        for fragment in forbidden_fragments:
            assert fragment not in text, f"{path}: found possible mojibake fragment {fragment!r}"


def test_language_switcher_is_available_in_public_and_panel_headers() -> None:
    switcher = (CLIENT_ROOT / "components" / "common" / "LanguageSwitcher.vue").read_text(encoding="utf-8")
    public_header = (CLIENT_ROOT / "components" / "common" / "AppHeader.vue").read_text(encoding="utf-8")
    panel_header = (CLIENT_ROOT / "components" / "panel" / "PanelTopbar.vue").read_text(encoding="utf-8")
    i18n_module = (CLIENT_ROOT / "i18n" / "index.ts").read_text(encoding="utf-8")

    assert "Languages" in switcher
    assert "toggleLocale" in switcher
    assert "<LanguageSwitcher />" in public_header
    assert "<LanguageSwitcher />" in panel_header
    assert '"omnibot.activity.locale"' in i18n_module
    assert 'export type Locale = "en" | "ru"' in i18n_module
