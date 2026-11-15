from types import SimpleNamespace
from bot.handlers.start import detect_user_language


def test_detect_supported_language():
    for code in ("en", "ru", "uk"):
        detected = detect_user_language(
            SimpleNamespace(from_user=SimpleNamespace(language_code=code))
        )
        assert detected in {"en", "ru", "ua"}


def test_unknown_language_uses_default():
    assert (
        detect_user_language(SimpleNamespace(from_user=SimpleNamespace(language_code="fr"))) == "en"
    )
