"""Synthetic regression tests; no model, account data, GUI or network calls."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "hopper-documentation-openai-pt-br/skills/hopper-documentation-openai/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))
import hopper_documentation as h
import history
from redaction import mask

spec = importlib.util.spec_from_file_location("plugin_build", ROOT / "scripts/build.py")
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


def answer(quote="primeiro", ref="S1"):
    return {"changed": True, "summary": "Synthetic record", "state": "Synthetic state [S1]",
            "topics": "P1", "decisions": "No external actions", "pending": "None",
            "gaps": "Synthetic evaluation", "sources": [{"ref": ref, "quote": quote}]}


def snapshot(cwd, texts=("primeiro",), thread="synthetic-thread"):
    return {"thread_id": thread, "cwd": str(cwd), "coverage": "Synthetic complete collection",
            "entries": [{"id": "item-" + str(i), "turn_id": "turn-1", "role": "user",
                         "text": text} for i, text in enumerate(texts)]}


class Citations(unittest.TestCase):
    def test_whitespace_normalization_preserves_literal_words(self):
        h.validate(answer("primeiro segundo"), {"S1": {"text": "primeiro\n  segundo"}})

    def test_json_compaction_and_escape_are_not_literal(self):
        sources = {"S1": {"text": '{"files": 7, "collections": 2}'}}
        for quote in ('{"files":7,"collections":2}', r'\"files\": 7'):
            with self.subTest(quote=quote), self.assertRaises(h.CitationFailure) as caught:
                h.validate(answer(quote), sources)
            self.assertEqual(caught.exception.details[0]["reason"], "quote_mismatch")
        h.validate(answer('{"files": 7, "collections": 2}'), sources)

    def test_unknown_and_empty_citations_fail(self):
        for content, reason in ((answer(ref="S99"), "unknown_ref"), (answer(" "), "empty_quote")):
            with self.subTest(reason=reason), self.assertRaises(h.CitationFailure) as caught:
                h.validate(content, {"S1": {"text": "primeiro"}})
            self.assertEqual(caught.exception.details[0]["reason"], reason)

    def test_repair_only_changes_rejected_citations(self):
        content = answer("wrong")
        content["sources"].append({"ref": "S2", "quote": "valid"})
        original = copy.deepcopy(content)
        sources = {"S1": {"text": "primeiro"}, "S2": {"text": "valid"}}
        repairs = {"repairs": [{"position": 0, "ref": "S1", "quote": "primeiro"},
                                {"position": 1, "ref": "S2", "quote": "wrong"}]}
        result = h.repair_sources(content, repairs, sources, [0])
        h.validate(result, sources)
        self.assertEqual(content, original)
        self.assertEqual(result["sources"][1], original["sources"][1])
        for field in h.FIELDS:
            self.assertEqual(result[field], original[field])


class Continuity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.folder = self.cwd / h.FOLDER
        self.config = dict(h.DEFAULTS, part_chars=8, item_chars=8)

    def test_identity_and_cwd_rejected_before_writer(self):
        for data in (snapshot(self.cwd, thread="other"), snapshot(self.cwd / "other")):
            with patch.object(h, "call_writer") as writer, self.assertRaises(h.Failure):
                h.run(lambda: data, self.folder, "synthetic-thread", self.config, writer=writer)
            writer.assert_not_called()

    def test_partial_publication_resumes_and_no_new_items_skip_writer(self):
        data = snapshot(self.cwd, ("primeiro", "segundo"))
        replies = iter((answer("primeiro"), answer("invented"), {"repairs": []}))
        with patch.object(h.Path, "home", return_value=self.cwd), self.assertRaises(h.Partial):
            h.run(lambda: data, self.folder, "synthetic-thread", self.config,
                  writer=lambda *_: next(replies))
        first = list(self.folder.glob("handoff-*.md"))
        self.assertEqual(len(first), 1)
        state = h.load_state(self.folder, "synthetic-thread")
        self.assertEqual(set(state["processed"]), {"item-0"})
        self.assertIn(first[0].name, (self.folder / "index.md").read_text())
        resumed = h.run(lambda: data, self.folder, "synthetic-thread", self.config,
                        writer=lambda *_: answer("segundo"))
        self.assertEqual(resumed["status"], "done")
        self.assertEqual(len(list(self.folder.glob("handoff-*.md"))), 2)
        with patch.object(h, "call_writer") as writer:
            result = h.run(lambda: data, self.folder, "synthetic-thread", self.config, writer=writer)
        self.assertEqual(result["status"], "nothing_new")
        writer.assert_not_called()

    def test_interrupted_cursor_and_missing_index_recovered_without_duplication(self):
        data = snapshot(self.cwd)
        with patch.object(h, "save_state", side_effect=OSError("synthetic interruption")), \
                patch.object(h.Path, "home", return_value=self.cwd), self.assertRaises(h.Partial):
            h.run(lambda: data, self.folder, "synthetic-thread", self.config,
                  writer=lambda *_: answer())
        files = list(self.folder.glob("handoff-*.md"))
        (self.folder / "index.md").unlink()
        with patch.object(h, "call_writer") as writer:
            result = h.run(lambda: data, self.folder, "synthetic-thread", self.config, writer=writer)
        self.assertEqual(result["status"], "nothing_new")
        writer.assert_not_called()
        self.assertEqual(list(self.folder.glob("handoff-*.md")), files)
        self.assertIn(files[0].name, (self.folder / "index.md").read_text())

    def test_history_loss_and_duplicate_identifiers_rejected(self):
        state = {"processed": {"missing": "digest"}}
        with self.assertRaises(h.Failure):
            h.delta(snapshot(self.cwd), state, self.config)
        data = snapshot(self.cwd)
        data["entries"].append(copy.deepcopy(data["entries"][0]))
        with self.assertRaises(h.Failure):
            h.delta(data, {"processed": {}}, self.config)

    def test_concurrent_recording_rejected(self):
        target = self.folder / ".state/thread.lock"
        with h.lock(target), self.assertRaises(h.Busy):
            with h.lock(target):
                pass

    def test_private_diagnostics_mask_and_permissions(self):
        with patch.object(h.Path, "home", return_value=self.cwd):
            result = Path(h.private_diagnostics({"prompt": 'password="synthetic-value"'}, h.Failure("test")))
        content = (result / "failure.json").read_text()
        self.assertNotIn("synthetic-value", content)
        self.assertEqual(result.stat().st_mode & 0o777, 0o700)
        self.assertEqual((result / "failure.json").stat().st_mode & 0o777, 0o600)


class NativeHistory(unittest.TestCase):
    def test_paginated_collection_and_repeated_cursor(self):
        class Server:
            duplicate_cursor = False
            def __init__(self, *args, **kwargs):
                self.pages = 0
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def call(self, method, params):
                if method == "thread/read":
                    return {"thread": {"id": "synthetic", "cwd": "/tmp"}}
                self.pages += 1
                return {"data": [{"id": "turn-" + str(self.pages), "items": [
                    {"id": "msg-" + str(self.pages), "type": "agentMessage", "text": "Observed"}]}],
                    "nextCursor": "page-2" if self.pages == 1 or self.duplicate_cursor else None}
        with patch.object(history, "AppServer", Server):
            result = history.collect("synthetic", "/tmp")
            self.assertEqual(len(result["entries"]), 2)
            Server.duplicate_cursor = True
            with self.assertRaises(history.HistoryError):
                history.collect("synthetic", "/tmp")

    def test_injected_context_excluded_and_ordinary_user_kept(self):
        turn = {"id": "turn"}
        for text in ("# AGENTS.md instructions\nInjected", "<environment_context>Injected"):
            self.assertIsNone(history.normalize_item({"id": "x", "type": "userMessage",
                            "content": [{"type": "text", "text": text}]}, turn))
        ordinary = history.normalize_item({"id": "x", "type": "userMessage",
                    "content": [{"type": "text", "text": "Please document this decision"}]}, turn)
        self.assertEqual(ordinary["role"], "user")
        self.assertIsNone(history.normalize_item({"id": "r", "type": "reasoning", "text": "private"}, turn))

    def test_writer_isolation_must_be_confirmed(self):
        class Server:
            keep_enabled = False
            def __init__(self, *args, **kwargs):
                self.disabled = any("enabled=false" in arg for arg in kwargs["arguments"])
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def call(self, *args):
                return {"data": [{"errors": [], "skills": [{"path": "/synthetic/SKILL.md",
                    "enabled": self.keep_enabled or not self.disabled}]}]}
        with patch.object(h, "AppServer", Server):
            self.assertIn("enabled=false", h.isolated_skills("codex", "/tmp"))
            Server.keep_enabled = True
            with self.assertRaises(h.Failure):
                h.isolated_skills("codex", "/tmp")


class Packaging(unittest.TestCase):
    def test_packages_are_reproducible_and_match_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / "a", Path(temporary) / "b"
            names = packaging.build(a)
            packaging.build(b)
            self.assertEqual((a / "SHA256SUMS").read_bytes(), (b / "SHA256SUMS").read_bytes())
            for language, name in zip(packaging.LANGUAGES, names):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
                source = ROOT / ("hopper-documentation-openai-" + language)
                with zipfile.ZipFile(a / name) as archive:
                    self.assertIn(".codex-plugin/plugin.json", archive.namelist())
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


if __name__ == "__main__":
    unittest.main()
