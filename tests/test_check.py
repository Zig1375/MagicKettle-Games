import json
import tempfile
import unittest
from pathlib import Path

from tools.build_index import build
from tools.check import load_modules, problems


def module(id_, **match):
    return {
        "id": id_, "revision": 1, "format": 1, "name": id_, "note": "Why.",
        "match": match or {"steam": ["1"]},
        "fixes": [{"launch": {"prefer": {"backend": ["dxmt"]}}}],
    }


class Repository(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for folder in ("modules", "shared", "files"):
            (self.root / folder).mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, kind, name, content):
        (self.root / kind / name).write_text(json.dumps(content), encoding="utf-8")

    def check(self):
        return problems(load_modules(self.root), self.root)

    def test_good_modules_pass(self):
        self.write("modules", "one.json", module("one", steam=["1"]))
        self.write("modules", "two.json", module("two", exe=[{"name": "Two.exe"}]))
        self.assertEqual(self.check(), [])

    def test_file_named_after_its_id(self):
        self.write("modules", "other.json", module("one"))
        self.assertTrue(any("named after its id" in line for line in self.check()))

    def test_two_modules_for_one_game(self):
        self.write("modules", "one.json", module("one", epic=["a:b:c"]))
        self.write("modules", "two.json", module("two", epic=["a:b:c"]))
        self.assertTrue(any("is also in" in line for line in self.check()))

    def test_common_exe_name_needs_more(self):
        self.write("modules", "one.json", module("one", exe=[{"name": "Game.exe"}]))
        self.assertTrue(any("too common" in line for line in self.check()))
        self.write("modules", "one.json", module("one", exe=[{"name": "Game.exe", "product": "One"}]))
        self.assertEqual(self.check(), [])

    def test_missing_shared_module(self):
        broken = module("one")
        broken["requires"] = {"modules": ["unity"]}
        self.write("modules", "one.json", broken)
        self.assertTrue(any("doesn't exist" in line for line in self.check()))

    def test_schema_errors_are_reported(self):
        broken = module("one")
        broken["format"] = 2
        self.write("modules", "one.json", broken)
        self.assertTrue(any(line.startswith("modules/one.json: format") for line in self.check()))

    def test_index_holds_modules_without_schema_key(self):
        content = module("one")
        content["$schema"] = "../schema/module.schema.json"
        self.write("modules", "one.json", content)
        index = build(load_modules(self.root), "abc", "2026-10-27T00:00:00Z", self.root)
        self.assertEqual(index["format"], 1)
        self.assertEqual([m["id"] for m in index["modules"]], ["one"])
        self.assertNotIn("$schema", index["modules"][0])
        self.assertEqual(index["shared"], [])


if __name__ == "__main__":
    unittest.main()
