from __future__ import annotations

import sys

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from .ui import MainWindow
from .ui.styles import APP_STYLE


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Bid Watcher")
    app.setOrganizationName("SmartBidWatcher")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(APP_STYLE)

    lock_path = QStandardPaths.writableLocation(QStandardPaths.TempLocation) + "/smart-bid-watcher.lock"
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Smart Bid Watcher", "앱이 이미 실행 중입니다. 시스템 트레이를 확인해 주세요.")
        return 0

    window = MainWindow()
    window.show_initial()
    result = app.exec()
    lock.unlock()
    return result
