"""Sync the plugin's skills from the latest fruxon release on PyPI.

The skills are authored in the fruxon SDK, where they ship inside the
wheel under ``fruxon/skills/<name>/SKILL.md``. Pulling them from the
published wheel keeps this repo in lockstep with what users can
``pip install``, without needing access to the SDK's source repo.

Usage:
    python scripts/sync_skills.py            # latest release
    python scripts/sync_skills.py 0.14.0     # a specific release

Rewrites plugins/fruxon/skills/ and sets plugin.json's version to the
fruxon release. Standard library only.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "fruxon"
SKILLS = PLUGIN / "skills"
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"
PREFIX = "fruxon/skills/"


def fetch_wheel(version: str | None) -> tuple[str, bytes]:
    url = f"https://pypi.org/pypi/fruxon/{version}/json" if version else "https://pypi.org/pypi/fruxon/json"
    with urllib.request.urlopen(url) as resp:
        meta = json.load(resp)
    release = meta["info"]["version"]
    wheel = next((f for f in meta["urls"] if f["packagetype"] == "bdist_wheel"), None)
    if wheel is None:
        sys.exit(f"fruxon {release} has no wheel on PyPI")
    with urllib.request.urlopen(wheel["url"]) as resp:
        return release, resp.read()


def main() -> None:
    release, data = fetch_wheel(sys.argv[1] if len(sys.argv) > 1 else None)
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        members = [n for n in wheel.namelist() if n.startswith(PREFIX) and n.endswith("/SKILL.md")]
        if not members:
            sys.exit(f"fruxon {release} wheel contains no skills under {PREFIX}")
        shutil.rmtree(SKILLS, ignore_errors=True)
        for name in members:
            dest = SKILLS / name.removeprefix(PREFIX)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(wheel.read(name))

    manifest = json.loads(MANIFEST.read_text())
    manifest["version"] = release
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"synced {len(members)} skills from fruxon {release}")


if __name__ == "__main__":
    main()
