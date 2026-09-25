"""Headless BIM Validator server entry for the Tauri desktop app.

Runs the FastAPI/uvicorn server with no system tray and no browser launch.
The Tauri shell spawns this as a child process and manages its lifecycle.

This is the PyInstaller entry point for the embedded server bundle that ships
inside the Tauri desktop application (bim-validator-server.exe).
"""

import os
import sys
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000

# ---------------------------------------------------------------------------
# Frozen app bootstrap — must run before importing server modules
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _bundle_dir = Path(getattr(sys, "_MEIPASS", "."))

    # Database in user's local app data (not Program Files / install dir)
    _data_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "BIMValidator"
    _data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{_data_dir / 'bimvalidator.db'}",
    )

    # Spawned hidden (CREATE_NO_WINDOW) by the Tauri shell, so stdout/stderr
    # may be None; the logging module and uvicorn crash on first write.
    # Redirect stdio to a log file so the server can start and be diagnosed.
    if sys.stdout is None or sys.stderr is None:
        _log = open(_data_dir / "server.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = _log
        if sys.stderr is None:
            sys.stderr = _log

    # Ensure the bundled server package is importable
    sys.path.insert(0, str(_bundle_dir))


def main() -> None:
    """Run uvicorn in the foreground (the process is managed by Tauri)."""
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
