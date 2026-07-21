import os

from PySide6.QtGui import QGuiApplication

from modori.app import AppBootstrap


def _app() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


def test_app_bootstrap_exposes_copy_text_slot() -> None:
    bootstrap = AppBootstrap()

    assert hasattr(bootstrap, "copyText")
    assert bootstrap.copyText("") is False


def test_app_bootstrap_copy_text_writes_to_clipboard() -> None:
    app = _app()
    bootstrap = AppBootstrap()
    text = "modori-copy-text"

    assert bootstrap.copyText(text) is True
    assert app.clipboard().text() == text
