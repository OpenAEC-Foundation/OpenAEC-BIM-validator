"""Keep integration tests separate from developer databases and uploads."""

import os
import tempfile
from pathlib import Path

_runtime = tempfile.TemporaryDirectory(prefix="bim-validator-tests-")
_root = Path(_runtime.name)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_root / 'test.db').as_posix()}"
os.environ["PROJECT_FILES_DIR"] = str(_root / "projects")
