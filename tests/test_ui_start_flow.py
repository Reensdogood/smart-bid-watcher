import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

from smart_bid_watcher.config import ConfigStore
from smart_bid_watcher.models import AppConfig
from smart_bid_watcher.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def prepare_window(monkeypatch, tmp_path, api_key="real-api-key-value"):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ConfigStore().save(
        AppConfig(
            keywords=["스마트 경로당"],
            notice_types=["bid_notice"],
            g2b_api_key=api_key,
            run_at_startup=True,
        )
    )
    monkeypatch.setattr(
        "smart_bid_watcher.ui.main_window.set_run_at_startup",
        lambda enabled: None,
    )
    return MainWindow()


def dispose_window(window, qapp):
    window.monitor.stop()
    window.tray.hide()
    window.hide()
    window.deleteLater()
    qapp.processEvents()


def test_launch_always_shows_settings_without_starting(monkeypatch, tmp_path, qapp):
    window = prepare_window(monkeypatch, tmp_path)
    window.show_initial()
    qapp.processEvents()

    assert window.isVisible()
    assert not window.monitor.is_running
    dispose_window(window, qapp)


def test_password_mask_contains_the_real_saved_key(monkeypatch, tmp_path, qapp):
    window = prepare_window(monkeypatch, tmp_path)

    assert window.g2b_key_edit.echoMode() == QLineEdit.Password
    assert window.g2b_key_edit.text() == "real-api-key-value"
    assert "저장된 인증키 있음" in window.g2b_key_state.text()
    assert "18자" in window.g2b_key_state.text()
    dispose_window(window, qapp)


def test_start_saves_then_hides_to_tray(monkeypatch, tmp_path, qapp):
    window = prepare_window(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(
        type(window.monitor),
        "start",
        lambda self, config, run_once=False: calls.append((config, run_once)),
    )
    window.show_initial()
    qapp.processEvents()

    window._start()
    qapp.processEvents()

    assert calls and calls[0][1] is False
    assert not window.isVisible()
    assert ConfigStore().load().g2b_api_key == "real-api-key-value"
    dispose_window(window, qapp)


def test_missing_key_does_not_hide_or_overwrite_saved_key(
    monkeypatch, tmp_path, qapp
):
    window = prepare_window(monkeypatch, tmp_path)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    window.g2b_key_edit.clear()
    window.show_initial()
    qapp.processEvents()

    window._start()
    qapp.processEvents()

    assert window.isVisible()
    assert ConfigStore().load().g2b_api_key == "real-api-key-value"
    dispose_window(window, qapp)
