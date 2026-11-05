"""BIM Validator System Tray Application.

Manages the FastAPI/uvicorn web server as a background thread,
providing start/stop/open-browser controls via a system tray icon.

This script is the entry point for the PyInstaller-bundled server application.
It sets up paths for the frozen environment before importing server modules.
"""

import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen app bootstrap — must run before any server imports
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _bundle_dir = Path(getattr(sys, "_MEIPASS", "."))

    # Point server to bundled frontend assets
    os.environ.setdefault(
        "VIEWER_DIST_PATH", str(_bundle_dir / "viewer" / "dist")
    )

    # Database in user's local app data (not Program Files)
    _data_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "BIMValidator"
    _data_dir.mkdir(parents=True, exist_ok=True)

    # Windowed (console=False) frozen builds set sys.stdout/stderr to None.
    # uvicorn and the logging module crash on their first write, so the
    # server thread dies silently and the port never opens. Redirect stdio
    # to a log file so the server can start (and users get diagnostics).
    if sys.stdout is None or sys.stderr is None:
        _log_file = open(_data_dir / "server.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = _log_file
        if sys.stderr is None:
            sys.stderr = _log_file
    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{_data_dir / 'bimvalidator.db'}",
    )

    # Ensure server package is importable from bundle
    sys.path.insert(0, str(_bundle_dir))

# ---------------------------------------------------------------------------
# Imports after path setup
# ---------------------------------------------------------------------------
import pystray  # noqa: E402
from PIL import Image  # noqa: E402

logger = logging.getLogger("bim_validator.tray")

HOST = "127.0.0.1"
PORT = 8000

_server_thread: threading.Thread | None = None
_server_running = False
_shutdown_event = threading.Event()


def _get_icon_path() -> Path:
    """Get the path to the tray icon file."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", ".")) / "tray_icon.ico"
    return Path(__file__).parent / "tray_icon.ico"


def _run_server() -> None:
    """Run uvicorn in the current thread."""
    global _server_running
    import uvicorn

    _server_running = True
    logger.info("Starting server on %s:%s", HOST, PORT)

    config = uvicorn.Config(
        "server.main:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()
    _server_running = False
    logger.info("Server stopped")


def start_server(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    """Start the web server in a background thread."""
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        icon.notify("Server is al actief", "BIM Validator")
        return
    _server_thread = threading.Thread(target=_run_server, daemon=True, name="uvicorn")
    _server_thread.start()
    icon.notify("Server gestart op poort 8000", "BIM Validator")


def open_browser(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    """Open the web UI in the default browser."""
    webbrowser.open(f"http://{HOST}:{PORT}")


def on_quit(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    """Quit the tray application and stop the server."""
    logger.info("Quitting tray application")
    _shutdown_event.set()
    icon.stop()


def _create_icon() -> pystray.Icon:
    """Create and return the system tray icon with menu."""
    icon_path = _get_icon_path()
    if icon_path.exists():
        image = Image.open(icon_path)
    else:
        # Fallback: simple colored square
        image = Image.new("RGB", (64, 64), (53, 14, 53))

    menu = pystray.Menu(
        pystray.MenuItem(
            "Open BIM Validator",
            open_browser,
            default=True,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start Server", start_server),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Afsluiten", on_quit),
    )

    return pystray.Icon(
        name="bim_validator",
        icon=image,
        title="BIM Validator",
        menu=menu,
    )


def main() -> None:
    """Entry point: auto-start server and show tray icon."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("BIM Validator Tray App starting")

    # Auto-start server
    global _server_thread
    _server_thread = threading.Thread(target=_run_server, daemon=True, name="uvicorn")
    _server_thread.start()

    # Open browser after a short delay (give server time to boot)
    def _delayed_open() -> None:
        import time
        time.sleep(2)
        if _server_running:
            webbrowser.open(f"http://{HOST}:{PORT}")

    threading.Thread(target=_delayed_open, daemon=True).start()

    # Run tray icon (blocks until quit)
    icon = _create_icon()
    icon.run()


if __name__ == "__main__":
    main()
