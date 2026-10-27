"""Builds games.json, the index EscApp downloads, from modules/ and shared/.

    python -m tools.build_index [--output games.json]

The index holds every module whole, so EscApp finds the player's games on the Mac without asking for any one of
them. `generated` and `commit` name the newest commit that changed a module, not the build, so building twice gives
the same file and CI commits it only when a module changed. A file of the `files` action gets its SHA-256 and size
here.
"""

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tools.check import ROOT, load_modules, problems

FORMAT = 1


def last_change(paths, root=ROOT):
    """(ISO time in UTC, hash) of the newest commit touching `paths`, or None outside git."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct %H", "--", *map(str, paths)], cwd=root,
                             capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None
    if len(out) != 2:
        return None
    time = datetime.datetime.fromtimestamp(int(out[0]), datetime.timezone.utc)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ"), out[1]


def with_file_pins(module, root=ROOT):
    for group in module["fixes"]:
        for entry in group.get("files", []):
            data = (root / "files" / entry["from"]).read_bytes()
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["size"] = len(data)
    return module


def build(found, commit, generated, root=ROOT):
    def entry(module):
        module = dict(module)
        module.pop("$schema", None)
        return with_file_pins(module, root)

    return {
        "format": FORMAT,
        "generated": generated,
        "commit": commit,
        "modules": [entry(m) for kind, _, m in found if kind == "modules"],
        "shared": [entry(m) for kind, _, m in found if kind == "shared"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "games.json"))
    args = parser.parse_args()

    found = load_modules()
    lines = problems(found)
    if lines:
        print("\n".join(lines), file=sys.stderr)
        return 1
    paths = [path for _, path, _ in found] + [ROOT / "files"]
    generated, commit = last_change(paths) or ("1970-01-01T00:00:00Z", "")
    index = build(found, commit, generated)
    Path(args.output).write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.output}: {len(index['modules'])} modules, {len(index['shared'])} shared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
