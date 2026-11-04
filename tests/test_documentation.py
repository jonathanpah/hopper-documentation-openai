"""Synthetic packaging tests; no model, account data, GUI or network calls."""

import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plugin_build", ROOT / "scripts/build.py")
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


class Packaging(unittest.TestCase):
    def test_packages_are_reproducible_and_match_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / "a", Path(temporary) / "b"
            names = packaging.build(a)
            packaging.build(b)
            self.assertEqual(set(names), {
                "hopper-documentation-openai-2.0.0-pt-br.zip",
                "hopper-documentation-openai-2.0.0-en.zip",
            })
            self.assertEqual((a / "SHA256SUMS").read_bytes(), (b / "SHA256SUMS").read_bytes())
            for language, name in zip(packaging.LANGUAGES, names):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
                source = ROOT / ("hopper-documentation-openai-" + language)
                expected_files = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
                with zipfile.ZipFile(a / name) as archive:
                    self.assertIn(".codex-plugin/plugin.json", archive.namelist())
                    self.assertIn(".agents/plugins/marketplace.json", archive.namelist())
                    self.assertEqual(set(archive.namelist()), expected_files)
                    self.assertEqual(len(archive.namelist()), len(expected_files))
                    self.assertIsNone(archive.testzip())
                    for item in archive.namelist():
                        self.assertFalse(Path(item).is_absolute())
                        self.assertNotIn("..", Path(item).parts)
                        self.assertEqual(archive.read(item), (source / item).read_bytes())
                expected = hashlib.sha256((a / name).read_bytes()).hexdigest()
                self.assertIn(expected + "  " + name, (a / "SHA256SUMS").read_text())

    def test_symlink_is_not_packaged(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "outside").write_text("synthetic")
            (folder / "linked").symlink_to(folder / "outside")
            with self.assertRaises(ValueError):
                packaging.package_files(folder)

    def test_changes_beyond_language_and_wrong_selector_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for language in packaging.LANGUAGES:
                name = "hopper-documentation-openai-" + language
                shutil.copytree(ROOT / name, root / name)
            program = root / "hopper-documentation-openai-en" / packaging.PROGRAM
            original = program.read_bytes()
            program.write_bytes(original + b"\n# Synthetic implementation difference.\n")
            with self.assertRaisesRegex(ValueError, "beyond the LANGUAGE line"):
                packaging.build(root / "output", root=root)
            program.write_bytes(original.replace(b'LANGUAGE = "en"', b'LANGUAGE = "pt-br"', 1))
            with self.assertRaisesRegex(ValueError, "Invalid LANGUAGE selector"):
                packaging.build(root / "output", root=root)
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
