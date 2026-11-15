import logging
from app.config import settings
from app.utils.logger import SecretRedactingFormatter


def test_logs_redact_credentials_and_password_bearing_urls(monkeypatch):
    key = "unit-test-exchange-credential"
    monkeypatch.setattr(settings, "binance_api_key", key)
    record = logging.LogRecord(
        "security-test",
        logging.ERROR,
        __file__,
        1,
        "Failed with %s at postgresql://user:private-password@localhost/db",
        (key,),
        None,
    )
    output = SecretRedactingFormatter("%(message)s").format(record)
    assert key not in output
    assert "private-password" not in output
    assert "localhost/db" in output
    assert "[REDACTED]" in output
