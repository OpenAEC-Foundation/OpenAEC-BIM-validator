"""Report installed distributions and their bundled license notices."""

import sys
from importlib.metadata import distributions


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("THIRD-PARTY SOFTWARE NOTICES\n")
    print(
        "Generated from the installed runtime. Original licenses apply to dependencies.\n"
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
