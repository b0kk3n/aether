#!/usr/bin/env python3
"""Bump the version across all files and prepend a CHANGELOG entry.

Usage (local):
    python3 scripts/bump_version.py 0.4.2 "Fix login timeout" "- Fixed session expiry bug\\n- Improved error messages"

Usage (GitHub Actions — pass values via env vars):
    RELEASE_VERSION=0.4.2 RELEASE_TITLE="..." RELEASE_DESCRIPTION="..." python3 scripts/bump_version.py
"""

import json
import os
import re
import sys


VERSION_FILES = [
    ("config.yaml",           r'^version: "[^"]*"',       'version: "{version}"'),
    ("pyproject.toml",        r'^version = "[^"]*"',       'version = "{version}"'),
    ("aether/__init__.py",    r'^__version__ = "[^"]*"',   '__version__ = "{version}"'),
]

MANIFEST = "homeassistant/custom_components/aether/manifest.json"


def set_version_in_text_file(path, pattern, replacement, version):
    with open(path) as f:
        content = f.read()
    new_content = re.sub(pattern, replacement.format(version=version), content, count=1, flags=re.MULTILINE)
    if new_content == content:
        raise ValueError(f"Pattern not matched in {path}: {pattern!r}")
    with open(path, "w") as f:
        f.write(new_content)


def set_version_in_manifest(version):
    with open(MANIFEST) as f:
        data = json.load(f)
    data["version"] = version
    with open(MANIFEST, "w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def prepend_changelog(version, title, description):
    with open("CHANGELOG.md") as f:
        lines = f.readlines()

    new_entry = [
        f"## {version}\n",
        "\n",
        f"### {title}\n",
        "\n",
        *[f"{line}\n" for line in description.splitlines()],
        "\n",
    ]

    # Insert before the first existing ## entry
    insert_at = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    lines = lines[:insert_at] + new_entry + lines[insert_at:]

    with open("CHANGELOG.md", "w") as f:
        f.writelines(lines)


def main():
    if len(sys.argv) == 4:
        version, title, description = sys.argv[1], sys.argv[2], sys.argv[3]
    else:
        version = os.environ.get("RELEASE_VERSION", "")
        title = os.environ.get("RELEASE_TITLE", "")
        description = os.environ.get("RELEASE_DESCRIPTION", "")

    if not version or not title or not description:
        print(__doc__)
        sys.exit(1)

    for path, pattern, replacement in VERSION_FILES:
        set_version_in_text_file(path, pattern, replacement, version)
        print(f"  updated {path}")

    set_version_in_manifest(version)
    print(f"  updated {MANIFEST}")

    prepend_changelog(version, title, description)
    print(f"  updated CHANGELOG.md")

    print(f"\nDone — version is now {version}")


if __name__ == "__main__":
    main()
