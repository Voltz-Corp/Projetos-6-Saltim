from app.smtp_mailer import get_smtp_settings


SMTP_ENV_VARS = (
    "SMTP_ENABLED",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
    "SMTP_FROM_NAME",
    "SMTP_USE_TLS",
    "SMTP_TIMEOUT_SECONDS",
)


def test_smtp_settings_default_to_local_mailpit(monkeypatch):
    for variable in SMTP_ENV_VARS:
        monkeypatch.delenv(variable, raising=False)

    settings = get_smtp_settings()

    assert settings is not None
    assert settings.host == "localhost"
    assert settings.port == 1025
    assert settings.from_email == "pedidos@saltim.local"
    assert settings.use_tls is False


def test_smtp_can_be_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("SMTP_ENABLED", "0")

    assert get_smtp_settings() is None


def test_smtp_accepts_username_alias(monkeypatch):
    monkeypatch.setenv("SMTP_USERNAME", "mailer")
    monkeypatch.delenv("SMTP_USER", raising=False)

    settings = get_smtp_settings()

    assert settings is not None
    assert settings.username == "mailer"
