"""Offline regression tests for build_tag_plan.build_plan (clustering + canonical steering)."""
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


btp = _load("build_tag_plan", "scripts/build_tag_plan.py")


class BuildPlanTests(unittest.TestCase):
    def plan(self, tags, canonical):
        return btp.build_plan(tags, set(canonical), low_count=1, min_cluster=2)

    def test_nfkc_fullwidth_space_clusters(self):
        merges, renames, retire = self.plan(
            [("海报", 10), ("海　报", 3)], {"海报"})
        self.assertIn({"source": "海　报", "target": "海报"}, merges)

    def test_case_space_variants_merge_to_canonical(self):
        merges, renames, retire = self.plan(
            [("Web UI", 8), ("WebUI", 2), ("webui", 1)], {"Web UI"})
        self.assertEqual({m["source"] for m in merges}, {"WebUI", "webui"})
        self.assertTrue(all(m["target"] == "Web UI" for m in merges))

    def test_canonical_absent_multi_member_steers_to_canonical(self):
        merges, renames, retire = self.plan(
            [("dashboard", 9), ("DashBoard", 1)], {"Dashboard"})
        targets = {m["target"] for m in merges} | {r["newName"] for r in renames}
        self.assertIn("Dashboard", targets)
        self.assertNotIn("dashboard", {m["target"] for m in merges})

    def test_singleton_canonical_casing_rename(self):
        merges, renames, retire = self.plan([("branding", 5)], {"Branding"})
        self.assertEqual(renames, [{"oldName": "branding", "newName": "Branding"}])

    def test_low_frequency_retire(self):
        merges, renames, retire = self.plan(
            [("keep", 5), ("noise", 0), ("one", 1)], {"keep"})
        retired = {r["tag"] for r in retire}
        self.assertIn("noise", retired)
        self.assertIn("one", retired)
        self.assertNotIn("keep", retired)


if __name__ == "__main__":
    unittest.main()
