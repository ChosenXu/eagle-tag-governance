"""Offline regression tests for apply_tag_governance guards (undo-map gate, dup baseline)."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ap = _load("apply_tag_governance", "scripts/apply_tag_governance.py")


class NewDuplicateTests(unittest.TestCase):
    def test_baseline_duplicates_not_flagged(self):
        self.assertEqual(ap._new_duplicates({"A": 5, "B": 4}, {"A": 5, "B": 4}), [])

    def test_new_duplicate_flagged(self):
        self.assertEqual(ap._new_duplicates({"A": 1}, {"A": 2}), ["A"])

    def test_new_name_single_not_flagged(self):
        self.assertEqual(ap._new_duplicates({"A": 1}, {"A": 1, "B": 1}), [])


class UndoGateTests(unittest.TestCase):
    def _run_apply(self, plan_path, undo_path, proxy):
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts/apply_tag_governance.py"),
             "--payload", plan_path, "--apply", "--undo-map", undo_path,
             "--proxy", proxy],
            capture_output=True, text=True)

    def _write_plan(self, d):
        plan = os.path.join(d, "plan.json")
        with open(plan, "w") as f:
            json.dump({"merges": [{"source": "a", "target": "b"}]}, f)
        return plan

    def test_empty_undo_map_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            plan = self._write_plan(d)
            empty = os.path.join(d, "empty.json")
            with open(empty, "w") as f:
                f.write("{}")
            r = self._run_apply(plan, empty, os.path.join(d, "nope.js"))
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("undo mapping verified", r.stdout)
            self.assertIn("not a valid undo mapping", r.stdout + r.stderr)

    def test_truncated_undo_map_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            plan = self._write_plan(d)
            trunc = os.path.join(d, "trunc.json")
            with open(trunc, "w") as f:
                f.write('{"meta": {"planSha')
            r = self._run_apply(plan, trunc, os.path.join(d, "nope.js"))
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("undo mapping verified", r.stdout)
            self.assertIn("not a valid undo mapping", r.stdout + r.stderr)

    def test_valid_map_passes_gate_then_stops_at_proxy(self):
        with tempfile.TemporaryDirectory() as d:
            plan = self._write_plan(d)
            undo = os.path.join(d, "undo.json")
            gen = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts/export_undo_mapping.py"),
                 "--plan", plan, "--output", undo],
                capture_output=True, text=True)
            self.assertEqual(gen.returncode, 0, gen.stderr)
            with open(undo) as f:
                self.assertIn("planSha256_16", json.load(f)["meta"])
            r = self._run_apply(plan, undo, os.path.join(d, "nope.js"))
            self.assertIn("undo mapping verified", r.stdout)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
