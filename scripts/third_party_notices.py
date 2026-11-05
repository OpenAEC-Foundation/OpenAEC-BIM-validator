"""Report installed distributions and their bundled license notices."""

import sys
from importlib.metadata import distributions
from pathlib import Path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("THIRD-PARTY SOFTWARE NOTICES\n")
    print(
        "Generated from the installed runtime. Original licenses apply to dependencies.\n"
    )
    root = Path(__file__).resolve().parents[1]
    print((root / "THIRD-PARTY-NOTICES.txt").read_text(encoding="utf-8"))
    for license_file in sorted((root / "viewer/vendor").rglob("*")):
        if license_file.is_file() and (
            license_file.name == "LICENSE" or "OFL" in license_file.name
        ):
            print(
                f"\n--- {license_file.relative_to(root)} ---\n{license_file.read_text(encoding='utf-8')}"
            )
    for dist in sorted(
        distributions(), key=lambda d: d.metadata.get("Name", "").lower()
    ):
        name = dist.metadata.get("Name", "Unknown")
        if name == "ifc-validator":
            continue
        license_name = dist.metadata.get("License-Expression") or dist.metadata.get(
            "License"
        )
        if not license_name:
            license_name = "; ".join(
                c
                for c in dist.metadata.get_all("Classifier", [])
                if c.startswith("License ::")
            )
        print(
            f"{name} {dist.version}\nLicense: {license_name or 'See distribution notices'}"
        )
        for url in dist.metadata.get_all("Project-URL", []):
            print(url)
        for file in dist.files or []:
            if ".dist-info/" in str(file) and any(
                part.lower().startswith(("license", "copying", "notice"))
                for part in file.parts
            ):
                path = dist.locate_file(file)
                if path.is_file():
                    print(
                        f"\n--- {file} ---\n{path.read_text(encoding='utf-8', errors='replace')}"
                    )
        print("\n" + "=" * 72 + "\n")


if __name__ == "__main__":
    main()
