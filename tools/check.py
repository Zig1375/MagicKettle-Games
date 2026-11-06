"""Checks every module beyond its schema: what tools/schemas.py can't say about one file alone.

    python -m tools.check            # prints every problem, exits 1 if there is one

Magic Kettle checks the index it downloads by the same rules and skips a module that breaks one, so what passes here is
what the app applies.
"""

import json
import sys
from pathlib import Path

from tools.schemas import errors

ROOT = Path(__file__).resolve().parent.parent

# Names too many games share to tell one from another without its ProductName or SHA-256: Unity's and RPG Maker's
# stock players, DOSBox, and the usual launcher names.
COMMON_EXE_NAMES = {
    "game.exe", "launcher.exe", "start.exe", "play.exe", "setup.exe", "dosbox.exe", "rpg_rt.exe", "nw.exe",
    "unityplayer.exe", "main.exe", "app.exe", "run.exe",
}

# ProductNames that name an engine, a wrapper or nothing in particular, not one program: `match.product` alone would
# take every game made with it.
COMMON_PRODUCTS = {
    "game", "launcher", "setup", "installer", "unity", "unityplayer", "electron", "nw.js", "godot engine",
    "rpg maker", "dosbox", "renpy", "ren'py", "shockwave flash", "adobe flash player",
}

# A cover is a picture the app shows: PNG or JPEG by its first bytes, whatever the extension says, and small.
PICTURE_HEADERS = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")
MAX_COVER_SIZE = 1024 * 1024


def load_modules(root=ROOT):
    """Every module file, as (kind, path, parsed JSON or None when it isn't JSON)."""
    found = []
    for kind in ("modules", "shared"):
        for path in sorted((root / kind).glob("*.json")):
            try:
                found.append((kind, path, json.loads(path.read_text(encoding="utf-8"))))
            except json.JSONDecodeError as error:
                found.append((kind, path, None))
                print(f"{path.relative_to(root)}: not JSON: {error}", file=sys.stderr)
    return found


def problems(found, root=ROOT):
    """Everything wrong with the modules, as "file: problem" lines."""
    lines = []
    keys = {}
    shared_ids = {module["id"] for kind, _, module in found if kind == "shared" and isinstance(module, dict)}
    for kind, path, module in found:
        name = path.relative_to(root).as_posix()
        if module is None:
            lines.append(f"{name}: not JSON")
            continue
        schema_errors = errors(kind, module)
        lines += [f"{name}: {line}" for line in schema_errors]
        if schema_errors:
            continue
        if path.stem != module["id"]:
            lines.append(f"{name}: the file must be named after its id ({module['id']}.json)")
        for store in ("steam", "gog", "epic"):
            for value in module.get("match", {}).get(store, []):
                key = (store, value)
                if key in keys:
                    lines.append(f"{name}: match.{store} {value} is also in {keys[key]}")
                keys[key] = name
        for product in module.get("match", {}).get("product", []):
            if product.strip().lower() in COMMON_PRODUCTS:
                lines.append(f"{name}: product {product} is too common to match a program by itself")
            key = ("product", product.strip().lower())
            if key in keys:
                lines.append(f"{name}: match.product {product} is also in {keys[key]}")
            keys[key] = name
        for exe in module.get("match", {}).get("exe", []):
            if exe["name"].lower() in COMMON_EXE_NAMES and "product" not in exe and "sha256" not in exe:
                lines.append(f"{name}: {exe['name']} is too common a name without product or sha256")
            key = ("exe", exe["name"].lower(), exe.get("product", "").lower(), tuple(sorted(exe.get("sha256", []))))
            if key in keys:
                lines.append(f"{name}: match.exe {exe['name']} is also in {keys[key]}")
            keys[key] = name
        for required in module.get("requires", {}).get("modules", []):
            if required not in shared_ids:
                lines.append(f"{name}: requires shared/{required}.json, which doesn't exist")
        sources = {credit["what"] for credit in module.get("credits", [])}
        lines += cover_problems(name, module, sources, root)
        for group in module.get("fixes", []):
            for entry in group.get("files", []):
                source = root / "files" / entry["from"]
                if not source.is_file():
                    lines.append(f"{name}: files/{entry['from']} doesn't exist")
                if not sources:
                    lines.append(f"{name}: files/{entry['from']} needs a credits entry with its license")
    return lines


def cover_problems(name, module, sources, root=ROOT):
    """The module's cover must be there, a PNG or JPEG, at most MAX_COVER_SIZE, and credited."""
    if "cover" not in module:
        return []
    path = module["cover"]["from"]
    source = root / "files" / path
    if not source.is_file():
        return [f"{name}: files/{path} doesn't exist"]
    lines = []
    data = source.read_bytes()
    if not data.startswith(PICTURE_HEADERS):
        lines.append(f"{name}: files/{path} isn't a PNG or JPEG")
    if len(data) > MAX_COVER_SIZE:
        lines.append(f"{name}: files/{path} is larger than {MAX_COVER_SIZE // 1024} KB")
    if not sources:
        lines.append(f"{name}: files/{path} needs a credits entry with its license")
    return lines


def main():
    lines = problems(load_modules())
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
