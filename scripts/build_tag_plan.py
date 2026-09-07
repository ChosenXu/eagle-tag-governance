#!/usr/bin/env python3
"""Build an editable `merge_plan.json` from a raw Eagle tag dump.

This is the analysis half of the governance workflow (Phase 2→3a). It reads
the current tag vocabulary (exported by the agent via `tag_get`, optionally
`coreFieldsOnly: true`) plus an optional normative vocabulary, then proposes:

  - `merges`  : two existing tags -> combine (source removed, target kept)
  - `renames` : one existing tag -> rename in place to the canonical spelling
  - `retire`  : low-frequency / unused tags that should be stripped or deleted

The output is a plain JSON file the user reviews and prunes before any write
happens. Delete a line to skip that operation, or change `target` / `newName`
to redirect it.

Detection rules (all suggestions — the plan is human-editable):

1. **Spelling / case / space variants** — tags whose normalized form (lowercase,
   whitespace removed) matches are clustered. The canonical member (if present
   in the normative vocabulary) or the most-frequent member becomes the target.
   Other members are merged or renamed into it.
2. **Canonical casing deviation** — a singleton tag whose normalized form equals
   a normative tag but whose exact spelling differs is renamed to the normative
   spelling (e.g. `branding` -> `Branding`).
3. **Low-frequency noise** — tags with `count <= --low-count` that are not part
   of any merge/rename and not themselves normative become `retire` candidates.

This script NEVER writes to Eagle. It only reads local files and writes the
local plan.

Usage:
    python3 build_tag_plan.py \
        --tags tags.json \
        --vocab-md ../references/vocabulary-en.md \
        --low-count 1 \
        --output merge_plan.json

`--tags` accepts either a JSON array of `{name, count}` objects, or an object
with one of `{"tags":[...]}`, `{"data":[...]}`, `{"items":[...]}`. `count` may
be named `count`, `usageCount`, or `items` (number of items using the tag).
"""

import argparse
import datetime
import json
import re
import sys


def load_tags(path):
    """Return a list of (name, count) tuples, tolerant of several shapes."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        for key in ("tags", "data", "items"):
            if isinstance(data.get(key), list):
                raw = data[key]
                break
        else:
            raw = []
    else:
        raw = []

    out = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("tag")
        if not name:
            continue
        count = entry.get("count")
        if count is None:
            count = entry.get("usageCount")
        if count is None:
            c = entry.get("items")
            count = c if isinstance(c, (int, float)) else 0
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        out.append((str(name), count))
    return out


def load_canonical(args):
    """Build the canonical-name set from --vocab-md and/or --canonical."""
    canon = set()
    src = []
    if args.vocab_md:
        src.append(f"vocab-md:{args.vocab_md}")
        with open(args.vocab_md, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\s*-\s*`([^`]+)`", line)
                if m:
                    canon.add(m.group(1).strip())
    if args.canonical:
        src.append(f"canonical:{args.canonical}")
        with open(args.canonical, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            names = data
        elif isinstance(data, dict):
            names = data.get("canonical") or data.get("names") or []
        else:
            names = []
        for n in names:
            if n:
                canon.add(str(n).strip())
    return canon, src


def norm(name):
    """Normalize for variant clustering: lowercase, drop whitespace."""
    return name.lower().replace(" ", "").replace("\t", "")


def pick_target(members, counts, canonical_set):
    """Choose the canonical target name among cluster members."""
    canon_members = [m for m in members if m in canonical_set]
    pool = canon_members if canon_members else members
    # Most-frequent first; tie-break by shorter name, then alphabetical.
    return sorted(pool, key=lambda m: (-counts.get(m, 0), len(m), m))[0]


def build_plan(tags, canonical_set, low_count, min_cluster):
    counts = {name: c for name, c in tags}
    existing = {name for name, _ in tags}

    merges = []
    renames = []
    used = set()  # names consumed by a merge/rename (sources + targets + oldNames)

    # --- 1 & 2: cluster by normalized form ---
    clusters = {}
    for name in existing:
        clusters.setdefault(norm(name), []).append(name)

    for key, members in clusters.items():
        members = list(dict.fromkeys(members))  # dedupe, keep order
        if len(members) < min_cluster:
            continue
        target = pick_target(members, counts, canonical_set)
        existing_members = [m for m in members if m in existing]

        # Rename one existing member into target if target does not yet exist.
        rename_candidate = None
        if target not in existing:
            rename_candidate = sorted(
                existing_members, key=lambda m: (-counts.get(m, 0), len(m), m)
            )[0]
            renames.append({"oldName": rename_candidate, "newName": target})
            used.add(rename_candidate)
            used.add(target)

        for m in existing_members:
            if m == target or m == rename_candidate:
                continue
            merges.append({"source": m, "target": target})
            used.add(m)
            used.add(target)

    # --- 2b: singleton canonical-casing deviation ---
    for name in existing:
        if name in used:
            continue
        for c in canonical_set:
            if c != name and norm(c) == norm(name):
                renames.append({"oldName": name, "newName": c})
                used.add(name)
                used.add(c)
                break

    # --- 3: low-frequency retire candidates ---
    retire = []
    for name, c in tags:
        if name in used:
            continue
        if name in canonical_set:
            continue
        if c <= low_count:
            note = "count=0，建议剥离后手动删除" if c == 0 else f"count={c}（低频）"
            retire.append({"tag": name, "note": note})

    # Stable ordering: sort each list for readable diffs.
    merges.sort(key=lambda m: (m["target"], m["source"]))
    renames.sort(key=lambda r: (r["newName"], r["oldName"]))
    retire.sort(key=lambda r: r["tag"])

    return merges, renames, retire


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tags", required=True, help="raw tag dump JSON (from tag_get)")
    ap.add_argument("--vocab-md", default=None, help="normative vocabulary*.md to extract canonical names")
    ap.add_argument("--canonical", default=None, help="JSON file with canonical names (array or {canonical:[...]})")
    ap.add_argument("--low-count", type=int, default=1, help="tags with count <= N become retire candidates (default 1)")
    ap.add_argument("--min-cluster", type=int, default=2, help="min members to form a variant cluster (default 2)")
    ap.add_argument("--output", default="merge_plan.json", help="path to write the plan")
    args = ap.parse_args()

    tags = load_tags(args.tags)
    if not tags:
        sys.exit(f"error: no tags parsed from {args.tags}")
    canonical_set, canon_src = load_canonical(args)

    merges, renames, retire = build_plan(tags, canonical_set, args.low_count, args.min_cluster)

    plan = {
        "meta": {
            "source": "build_tag_plan.py",
            "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
            "tagCount": len(tags),
            "canonicalSource": canon_src or ["(none)"],
            "lowCountThreshold": args.low_count,
            "minCluster": args.min_cluster,
        },
        "merges": merges,
        "renames": renames,
        "retire": retire,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"wrote {args.output}")
    print(f"  tags parsed      : {len(tags)}")
    print(f"  canonical names  : {len(canonical_set)}")
    print(f"  merges proposed  : {len(merges)}")
    print(f"  renames proposed : {len(renames)}")
    print(f"  retire proposed  : {len(retire)}")
    print("review the file, delete/alter any entries, then run:")
    print(f"  python3 export_undo_mapping.py --plan {args.output} --output tag_undo_mapping.json")
    print(f"  python3 apply_tag_governance.py --payload {args.output} --apply")


if __name__ == "__main__":
    main()
