from __future__ import annotations

import sys
import winreg
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "SmartBidWatcher"


def executable_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    return f'"{sys.executable}" "{main_path}"'


def set_run_at_startup(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, executable_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
