"""Small helpers kept from the original framework."""

from __future__ import annotations

import secrets
import string
from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath


def run_id(now: datetime | None = None) -> str:
    """Folder-friendly id for one test run, e.g. 2026_09_25_14_03_11."""
    return (now or datetime.now()).strftime("%Y_%m_%d_%H_%M_%S")


def today(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%d-%m-%Y")


def random_string(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def split_path(file_path: str) -> tuple[str, str]:
    """('folder', 'file.ext') for POSIX or Windows paths; ('', '') for empty input."""
    if not file_path or not isinstance(file_path, str):
        return "", ""
    path = PureWindowsPath(file_path) if "\\" in file_path else PurePosixPath(file_path.rstrip("/"))
    folder = "" if str(path.parent) == "." else str(path.parent)
    return folder, path.name
