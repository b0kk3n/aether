#!/usr/bin/env python3
"""Validate that all version files are in sync and CHANGELOG has an entry."""

import json
import re
import sys


def get_config_version():
    with open("config.yaml") as f:
        for line in f:
            m = re.match(r'^version:\s*"([^"]+)"', line)
            if m:
                return m.group(1)
    raise ValueError("version not found in config.yaml")


def get_pyproject_version():
    with open("pyproject.toml") as f:
        for line in f:
            m = re.match(r'^version\s*=\s*"([^"]+)"', line)
            if m:
                return m.group(1)
    raise ValueError("version not found in pyproject.toml")


def get_init_version():
    with open("aether/__init__.py") as f:
        for line in f:
            m = re.match(r'^__version__\s*=\s*"([^"]+)"', line)
            if m:
                return m.group(1)
    raise ValueError("version not found in aether/__init__.py")


def get_manifest_version():
    with open("homeassistant/custom_components/aether/manifest.json") as f:
        return json.load(f)["version"]


def get_changelog_versions():
    versions = set()
    with open("CHANGELOG.md") as f:
        for line in f:
            m = re.match(r"^## (\S+)", line)
            if m:
                versions.add(m.group(1))
    return versions


def main():
    sources = {
        "config.yaml": get_config_version(),
        "pyproject.toml": get_pyproject_version(),
        "aether/__init__.py": get_init_version(),
        "homeassistant/custom_components/aether/manifest.json": get_manifest_version(),
    }

    print("Version check:")
    for path, version in sources.items():
        print(f"  {path}: {version}")

    unique = set(sources.values())
    if len(unique) > 1:
        print("\nFAIL: version mismatch across files!")
        sys.exit(1)

    current = next(iter(unique))

    if current not in get_changelog_versions():
        print(f"\nFAIL: CHANGELOG.md has no entry for version {current}")
        print("Add one or run: python3 scripts/bump_version.py <version> <title> <description>")
        sys.exit(1)

    print(f"\nOK: all files agree on version {current} and CHANGELOG has an entry.")


if __name__ == "__main__":
    main()
