#!/usr/bin/env python3
"""Export a `tag_undo_mapping.json` from a reviewed merge_plan.json.

Run this BEFORE the first `tag_merge` / `tag_update` (Hard Constraint #5). It
records, for every planned operation, how to recover if something goes wrong.

What is actually reversible:
  - Rename (`oldName` -> `newName`): fully reversible via `tag_update` with the
    direction flipped (`newName` -> `oldName`). The mapping records both the
    forward and the reverse call so you can paste it straight into a recovery run.
  - Merge (`source` -> `target`): NOT reversible through MCP. Once merged, the
    source tag is gone and its items carry `target`. The mapping keeps the
    source->target audit record and an explicit `reversible: false` flag; true
    recovery requires re-tagging the affected items by hand (or a pre-merge
    snapshot, which this skill does not capture).

Retire entries:
  - With a `target`: treated as a merge (source=tag -> target), same rules.
  - Without a `target`: recorded as irreversible (MCP has no `tag_delete`).

The file is a local safety artifact only — this script never writes to Eagle.

Usage:
    python3 export_undo_mapping.py --plan merge_plan.json --output tag_undo_mapping.json
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys


def _skill_version():
    """Read the version from the skill's SKILL.md (single source of truth)."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md")
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r"^version:\s*(\S+)", f.read(), re.MULTILINE)
        if m:
            return m.group(1)
    except OSError:
        pass
    return "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="reviewed merge_plan.json")
    ap.add_argument("--output", default="tag_undo_mapping.json", help="path to write the undo map")
    ap.add_argument("--skill-version", default=None,
                    help="skill version for the record (default: read from SKILL.md)")
    args = ap.parse_args()

    # Read the plan file ONCE; the digest comes from the same text.
    with open(args.plan, encoding="utf-8") as f:
        plan_text = f.read()
    plan = json.loads(plan_text)
    digest = hashlib.sha256(plan_text.encode("utf-8")).hexdigest()[:16]

    renames = list(plan.get("renames", []) or [])
    retire = list(plan.get("retire", []) or [])
    merges = list(plan.get("merges", []) or [])

    # Validate before building the audit — friendly errors, no raw KeyError.
    for r in renames:
        if not isinstance(r, dict) or not r.get("oldName") or not r.get("newName"):
            sys.exit(f"error: rename entry missing oldName/newName: {r!r}")
    for r in retire:
        if not isinstance(r, dict) or not r.get("tag"):
            sys.exit(f"error: retire entry missing 'tag': {r!r}")

    # Fold retire-with-target into merges for a complete audit.
    for r in retire:
        if r.get("target"):
            merges.append({"source": r["tag"], "target": r["target"]})
    for m in merges:
        if not isinstance(m, dict) or not m.get("source") or not m.get("target"):
            sys.exit(f"error: merge entry missing source/target: {m!r}")

    rename_undo = []
    for r in renames:
        rename_undo.append({
            "forward": {"oldName": r["oldName"], "newName": r["newName"]},
            "reverse": {"oldName": r["newName"], "newName": r["oldName"]},
            "reversible": True,
        })

    merge_audit = []
    for m in merges:
        merge_audit.append({
            "source": m["source"],
            "target": m["target"],
            "reversible": False,
            "note": "irreversible via MCP; recover by manually re-tagging affected items",
        })

    manual_retire = [
        {"tag": r["tag"], "reversible": False,
         "note": r.get("note", "no target — strip via item_remove_tags or delete in Eagle UI")}
        for r in retire if not r.get("target")
    ]

    undo = {
        "meta": {
            "source": "export_undo_mapping.py",
            "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
            "skillVersion": args.skill_version or _skill_version(),
            "planSha256_16": digest,
            "warning": "tag_merge is irreversible; merges are audit-only and cannot be auto-undone.",
        },
        "renames": rename_undo,
        "merges": merge_audit,
        "manualRetire": manual_retire,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(undo, f, ensure_ascii=False, indent=2)

    print(f"wrote {args.output}")
    print(f"  plan sha256[:16] : {digest}")
    print(f"  renames (undoable): {len(rename_undo)}")
    print(f"  merges  (audit only): {len(merge_audit)}")
    print(f"  manual retire       : {len(manual_retire)}")
    print("keep this file; if a rename must be reverted, run apply_tag_governance.py")
    print("with a plan built from the `reverse` entries above.")


if __name__ == "__main__":
    main()
