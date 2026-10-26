import copy
import json
import unittest
from pathlib import Path

from tools.schemas import errors

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def changed(module, edit):
    result = copy.deepcopy(module)
    edit(result)
    return result


class ValidModules(unittest.TestCase):
    def test_full_module(self):
        self.assertEqual(errors("modules", load("full-module.json")), [])

    def test_full_shared_module(self):
        self.assertEqual(errors("shared", load("full-shared.json")), [])

    def test_smallest_module(self):
        module = {
            "id": "tiny", "revision": 1, "format": 1, "name": "Tiny", "note": "Why.",
            "match": {"steam": ["1"]},
            "fixes": [{"launch": {"prefer": {"windows": "winxp"}}}],
        }
        self.assertEqual(errors("modules", module), [])

    def test_shared_module_without_match(self):
        shared = changed(load("full-shared.json"), lambda m: m.pop("match"))
        self.assertEqual(errors("shared", shared), [])


def group(module, index=1):
    return module["fixes"][index]


# Each edit breaks one rule of the full module; the schema must reject every one.
REJECTED = {
    "unknown top-level field": lambda m: m.update(extra=1),
    "no note": lambda m: m.pop("note"),
    "id with capitals": lambda m: m.update(id="Example"),
    "newer format": lambda m: m.update(format=2),
    "revision zero": lambda m: m.update(revision=0),
    "empty match": lambda m: m.update(match={}),
    "engine match in a game module": lambda m: m["match"].update(engine=["unity"]),
    "steam id with letters": lambda m: m["match"].update(steam=["abc"]),
    "epic id without three parts": lambda m: m["match"].update(epic=["namespace:item"]),
    "exe that isn't an exe": lambda m: m["match"]["exe"].append({"name": "game.dll"}),
    "exe with a folder": lambda m: m["match"]["exe"].append({"name": "bin/game.exe"}),
    "uppercase sha256": lambda m: m["match"]["exe"][1].update(sha256=["AB" * 32]),
    "unknown feature": lambda m: m["requires"].update(features=["esync"]),
    "wine version with letters": lambda m: m["requires"].update(wine={"from": "11.20-staging"}),
    "no fixes": lambda m: m.update(fixes=[]),
    "group without an action": lambda m: m["fixes"].append({"note": "Nothing."}),
    "unknown condition": lambda m: group(m, 0)["when"].update(gpu=["m1"]),
    "unknown store": lambda m: group(m, 0)["when"].update(store=["origin"]),
    "unknown backend": lambda m: group(m, 0)["launch"]["prefer"].update(backend=["d3dmetal"]),
    "required backend as a list": lambda m: group(m)["launch"]["require"].update(backend=["dxvk"]),
    "unknown windows version": lambda m: group(m)["launch"]["require"].update(windows="win98"),
    "DYLD variable": lambda m: group(m)["launch"]["environment"].update(DYLD_INSERT_LIBRARIES="x.dylib"),
    "WINE variable": lambda m: group(m)["launch"]["environment"].update(WINEDLLOVERRIDES="d3d11=n"),
    "PATH variable": lambda m: group(m)["launch"]["environment"].update(PATH="/tmp"),
    "non-string variable": lambda m: group(m)["launch"]["environment"].update(DXVK_HUD=1),
    "arguments as one string": lambda m: group(m)["launch"].update(arguments="-dx11 -windowed"),
    "backend DLL override": lambda m: group(m)["dllOverrides"].update(d3d11="native"),
    "DLL name with .dll": lambda m: group(m)["dllOverrides"].update(**{"foo.dll": "native"}),
    "DLL name with capitals": lambda m: group(m)["dllOverrides"].update(Foo="native"),
    "unknown override mode": lambda m: group(m)["dllOverrides"].update(xinput1_3="n"),
    "component with a path": lambda m: group(m)["components"].append("../vcrun"),
    "registry outside Software": lambda m: group(m)["registry"].append(
        {"key": "HKLM\\System\\CurrentControlSet", "name": "x", "dword": 1}),
    "registry in HKCR": lambda m: group(m)["registry"].append({"key": "HKCR\\Software\\x", "name": "x", "dword": 1}),
    "registry value with two types": lambda m: group(m)["registry"][0].update(string="0"),
    "registry value without a type": lambda m: group(m)["registry"][0].pop("dword"),
    "dword too big": lambda m: group(m)["registry"][0].update(dword=2**32),
    "absolute path": lambda m: group(m)["configEdits"][0].update(file="/etc/hosts"),
    "path climbing out": lambda m: group(m)["configEdits"][0].update(file="game:Config/../../x.ini"),
    "path starting with ..": lambda m: group(m)["configEdits"][0].update(file="game:../x.ini"),
    "path with a leading slash": lambda m: group(m)["configEdits"][0].update(file="game:/x.ini"),
    "Windows path": lambda m: group(m)["configEdits"][0].update(file="game:Config\\Engine.ini"),
    "unknown root": lambda m: group(m)["configEdits"][0].update(file="drive_c:x.ini"),
    "json edit in an ini file": lambda m: group(m)["configEdits"][0]["set"].append({"path": ["a"], "value": 1}),
    "ini edit in a json file": lambda m: group(m)["configEdits"][1]["set"].append(
        {"section": "a", "key": "b", "value": "c"}),
    "ini edit with value and delete": lambda m: group(m)["configEdits"][0]["set"][0].update(delete=True),
    "ini value that isn't text": lambda m: group(m)["configEdits"][0]["set"][0].update(value=1),
    "unknown config format": lambda m: group(m)["configEdits"][0].update(format="xml"),
    "add with expect": lambda m: group(m, 2)["files"][0].update(expect="ef" * 32),
    "replace without expect": lambda m: group(m, 2)["files"][1].pop("expect"),
    "file from outside files/": lambda m: group(m, 2)["files"][0].update(**{"from": "../secret"}),
    "file from without a module folder": lambda m: group(m, 2)["files"][0].update(**{"from": "dxvk.conf"}),
    "credit without a license": lambda m: m["credits"][0].pop("license"),
    "credit over http": lambda m: m["credits"][0].update(source="http://example.com"),
}


class RejectedModules(unittest.TestCase):
    def test_each_broken_rule_is_rejected(self):
        full = load("full-module.json")
        for name, edit in REJECTED.items():
            with self.subTest(name):
                self.assertNotEqual(errors("modules", changed(full, edit)), [])

    def test_shared_module_matching_a_game(self):
        shared = changed(load("full-shared.json"), lambda m: m.update(match={"steam": ["1"]}))
        self.assertNotEqual(errors("shared", shared), [])

    def test_unknown_engine(self):
        shared = changed(load("full-shared.json"), lambda m: m.update(match={"engine": ["godot"]}))
        self.assertNotEqual(errors("shared", shared), [])

    def test_errors_name_the_place(self):
        broken = changed(load("full-module.json"), REJECTED["DYLD variable"])
        self.assertTrue(any(line.startswith("fixes/1/launch/environment") for line in errors("modules", broken)))


if __name__ == "__main__":
    unittest.main()
