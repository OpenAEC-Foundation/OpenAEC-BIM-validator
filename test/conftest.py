"""Pytest configuration for ifc_validator test suite.

This conftest.py ensures tests use the local src directory only,
preventing cross-contamination from other worktrees.
"""

import sys
from pathlib import Path

# Get the test directory and project root
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent

# Clear any existing ifc_validator paths from sys.path
sys.path = [p for p in sys.path if "ifc_validator" not in p and "worktrees" not in p]

# Insert our project's src at the beginning
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Insert the project root
project_path = str(PROJECT_ROOT)
if project_path not in sys.path:
    sys.path.insert(0, project_path)
