"""Synchronize release versions using the OpenAEC ISO-year.week.sequence scheme."""

import argparse
import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEME = re.compile(r"^(20\d{2})\.([1-9]|[1-4]\d|5[0-3])\.(0|[1-9]\d*)$")
FIELDS = {
    "pyproject.toml": r'(?m)^(version = ")([^"]+)(")',
    "viewer/src-tauri/Cargo.toml": r'(?m)^(version = ")([^"]+)(")',
    "viewer/src-tauri/Cargo.lock": r'(name = "openaec-bim-validator"\nversion = ")([^"]+)(")',
    "src/ifc_validator/__init__.py": r'(__version__ = ")([^"]+)(")',
    "installer/bim_validator.iss": r'(#define MyAppVersion ")([^"]+)(")',
    "viewer/src/version.ts": r'(APP_VERSION = ")([^"]+)(")',
}
JSON_FILES = [
    "viewer/package.json",
    "viewer/package-lock.json",
    "viewer/src-tauri/tauri.conf.json",
]


def valid(value):
    match = SCHEME.fullmatch(value)
    if not match:
        return False
    try:
        datetime.date.fromisocalendar(int(match[1]), int(match[2]), 1)
        return True
    except ValueError:
        return False


def versions():
    result = {}
    for name, pattern in FIELDS.items():
        match = re.search(pattern, (ROOT / name).read_text(encoding="utf-8"))
        result[name] = match[2] if match else None
    for name in JSON_FILES:
        data = json.loads((ROOT / name).read_text(encoding="utf-8"))
        result[name] = data["version"]
        if "packages" in data:
            result[name + ":root"] = data["packages"][""]["version"]
    return result


def next_version(today=None, now=None):
    year, week, _ = (today or datetime.date.today()).isocalendar()
    prefix = f"{year}.{week}."
    return prefix + str(
        int(now.split(".")[2]) + 1
        if now and valid(now) and now.startswith(prefix)
        else 0
    )


def write(value):
    if not valid(value):
        raise ValueError("Expected YYYY.W.N with a valid ISO week and no leading zeros")
    updates = {}
    for name, pattern in FIELDS.items():
        file = ROOT / name
        content, count = re.subn(
            pattern,
            lambda m: m[1] + value + m[3],
            file.read_text(encoding="utf-8"),
            count=1,
        )
        if count != 1:
            raise ValueError(f"Missing version field: {name}")
        updates[file] = content
    for name in JSON_FILES:
        file = ROOT / name
        data = json.loads(file.read_text(encoding="utf-8"))
        data["version"] = value
        if "packages" in data:
            data["packages"][""]["version"] = value
        updates[file] = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    for file, content in updates.items():
        file.write_text(content, encoding="utf-8", newline="")


def check(tag=None):
    found = versions()
    current = found["pyproject.toml"]
    if (
        not valid(current or "")
        or any(v != current for v in found.values())
        or (tag and tag != "v" + current)
    ):
        print(f"Release versions differ or are invalid: {found}; tag={tag}")
        return 1
    print(f"Version {current}: all {len(found)} fields agree")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--set")
    group.add_argument("--next", action="store_true")
    group.add_argument("--check", action="store_true")
    parser.add_argument("--tag")
    args = parser.parse_args()
    if args.set or args.next:
        value = args.set or next_version(now=versions()["pyproject.toml"])
        write(value)
    return check(args.tag)


if __name__ == "__main__":
    raise SystemExit(main())
