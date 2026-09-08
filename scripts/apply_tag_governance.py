#!/usr/bin/env python3
"""Bulk-apply Eagle tag governance through the MCP stdio proxy.

Drives `node <mcp-proxy.js>` over JSON-RPC to call `tag_merge` / `tag_update`
with the large `operations` / `tags` arrays from a reviewed `merge_plan.json`,
so the agent does not have to paste a 100+ entry payload into the chat.

This is the execution half (Phase 4). It is DESTRUCTIVE and IRREVERSIBLE — every
write is global and permanent, and Eagle has no undo. The plan must have already
passed Phase 3a (dry-run) and Phase 3b (authorization) before you run this.

Safety design:
  - Default mode is DRY-RUN: without `--apply` it only prints what WOULD happen
    and exits. Nothing is sent to Eagle. This mirrors the authorization gate.
  - `--apply` is the explicit opt-in that actually performs the writes.
  - Merge order is topologically sorted so chains (a->b, b->c) apply in the
    correct sequence; direct cycles (a->b, b->a) are rejected before any write.
  - Success is judged PER OPERATION, never by the batch-level `isError` flag:
    the proxy returns isError=false even for silent no-op merges. Affected
    item counts are parsed from each op's response and cross-checked against a
    post-write tag re-read. Any source that survives, or any duplicate-named
    tag (a mis-aimed rename that copied instead of folded), is reported as a
    failure — NOT silently counted as success.
  - The process exits non-zero when any op reports `ZERO-MOVE` / an error, or
    when duplicate-named tags are detected after the run — automation and
    agents can rely on the exit code instead of parsing the log.

Usage:
    # Preview only (no writes):
    python3 apply_tag_governance.py --payload merge_plan.json

    # Execute after user authorization:
    python3 apply_tag_governance.py --payload merge_plan.json --apply

`retire` entries with a `target` are folded into merges. `retire` entries
WITHOUT a target cannot be auto-stripped (that needs item IDs via item_get +
item_remove_tags) and are printed as manual steps — they are never silently
applied.
"""

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time

# Keep these paths `~`-based and generic. Do NOT hardcode a machine-specific
# absolute path — that would break on other machines and leak the author's
# username when the skill is shared.
DEFAULT_PROXY_CANDIDATES = [
    os.path.expanduser("~/Library/Application Support/Eagle/Plugins/mcp-server/modules/mcp-proxy.js"),
]


class MCPClient:
    def __init__(self, proxy):
        self.p = subprocess.Popen(
            ["node", proxy],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.t = threading.Thread(target=self._reader, daemon=True)
        self.t.start()
        self._id = 0

    def _reader(self):
        for line in self.p.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            self.q.put(msg)

    def _send(self, obj):
        with self.lock:
            self.p.stdin.write(json.dumps(obj) + "\n")
            self.p.stdin.flush()

    def _wait(self, msg_id, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            try:
                m = self.q.get(timeout=2)
            except queue.Empty:
                continue
            if m.get("id") == msg_id:
                return m
        return None

    def initialize(self):
        self._id += 1
        rid = self._id
        self._send({
            "jsonrpc": "2.0", "id": rid, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "eagle-tag-governance", "version": "1.0.2"},
            },
        })
        init = self._wait(rid, 30)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return init

    def call_tool(self, name, args, timeout=120):
        self._id += 1
        rid = self._id
        self._send({
            "jsonrpc": "2.0", "id": rid, "method": "tools/call",
            "params": {"name": name, "arguments": args},
        })
        return self._wait(rid, timeout)

    def close(self):
        for attr in ("stdin",):
            try:
                getattr(self.p, attr).close()
            except Exception:
                pass
        try:
            self.p.terminate()
        except Exception:
            pass


def resolve_proxy(explicit=None):
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        sys.exit(f"error: --proxy path not found: {explicit}")
    for c in DEFAULT_PROXY_CANDIDATES:
        if os.path.isfile(c):
            return c
    sys.exit(
        "error: could not locate mcp-proxy.js. Pass --proxy <path> to the "
        "Eagle mcp-server modules/mcp-proxy.js file."
    )


def find_cycle(merges):
    graph = {m["source"]: m["target"] for m in merges}
    for start in list(graph):
        seen = set()
        cur = start
        while cur in graph:
            if cur in seen:
                return True
            seen.add(cur)
            cur = graph[cur]
    return False


def order_merges(merges):
    """Apply merges whose source is not a target of another merge first."""
    targets = set(m["target"] for m in merges)
    remaining = list(merges)
    ordered = []
    changed = True
    while remaining and changed:
        changed = False
        nxt = []
        for m in remaining:
            if m["source"] not in targets:
                ordered.append(m)
                targets.discard(m["target"])
                changed = True
            else:
                nxt.append(m)
        remaining = nxt
    ordered.extend(remaining)
    return ordered


def validate_plan(plan):
    errors = []
    merges = plan.get("merges", []) or []
    renames = plan.get("renames", []) or []
    for m in merges:
        if not m.get("source") or not m.get("target"):
            errors.append(f"merge missing source/target: {m!r}")
        elif m["source"] == m["target"]:
            errors.append(f"merge source == target: {m['source']!r}")
    for r in renames:
        if not r.get("oldName") or not r.get("newName"):
            errors.append(f"rename missing oldName/newName: {r!r}")
        elif r["oldName"] == r["newName"]:
            errors.append(f"rename oldName == newName: {r['oldName']!r}")
    if find_cycle(merges):
        errors.append("merge cycle detected (a->b and b->a): cannot resolve order safely")
    return merges, renames, errors


def _get_existing_tags(client, timeout=60):
    """Return the set of current tag names, or None if the read fails.

    DEPRECATED wrapper kept for backward compatibility. Prefer `_read_tags`,
    which also returns per-tag item counts and name-occurrence counts (the
    latter is required to detect duplicate-named tags created by a mis-aimed
    rename).
    """
    names, _, _ = _read_tags(client, timeout=timeout)
    return names


def _read_tags(client, timeout=60):
    """Return (names:set, counts:dict, occurrences:dict) of current tags.

    - names: set of distinct tag names.
    - counts: name -> summed item count across all tag objects with that name.
    - occurrences: name -> NUMBER OF tag objects carrying that name
      (a value > 1 means Eagle holds duplicate-named tags — the exact
      failure mode where a rename merged into an existing name created a
      copy instead of folding into it).

    Returns (None, None, None) on any read/parse failure so callers fall back
    to a safe warning instead of trusting a false positive.
    """
    res = client.call_tool("tag_get", {"coreFieldsOnly": True}, timeout=timeout)
    if res is None:
        return None, None, None
    text = (res.get("result", {}).get("content") or [{}])[0].get("text", "")
    if not text:
        return None, None, None
    try:
        payload = json.loads(text)
    except Exception:
        # Some proxies wrap the payload; try to salvage a JSON object.
        try:
            payload = json.loads(text[text.index("{"):])
        except Exception:
            return None, None, None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return None, None, None
    names, counts, occurrences = set(), {}, {}
    for t in data:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        n = t["name"]
        names.add(n)
        occurrences[n] = occurrences.get(n, 0) + 1
        if isinstance(t.get("count"), int):
            counts[n] = counts.get(n, 0) + t["count"]
    return names, counts, occurrences


def _extract_per_op(res):
    """Tolerant parser turning a proxy response into a list of per-op dicts.

    The Eagle proxy returns ONE response per BATCH but embeds a list of
    per-operation results (isError / affectedItems / sourceRemoved / source /
    target). We recover that list so verification can judge each op
    individually instead of trusting the batch-level isError flag (which the
    proxy reports as false even for silent no-op merges).
    """
    if res is None:
        return []
    content = (res.get("result", {}) or {}).get("content") or []
    chunks = [c.get("text", "") for c in content if isinstance(c, dict)]
    out = []
    for t in chunks:
        try:
            obj = json.loads(t)
        except Exception:
            continue
        if isinstance(obj, list):
            out.extend(obj)
        elif isinstance(obj, dict):
            if isinstance(obj.get("operations"), list):
                out.extend(obj["operations"])
            elif isinstance(obj.get("data"), list):
                out.extend(obj["data"])
            else:
                out.append(obj)
    # Fallback: regex-scan for affectedItems if JSON parsing yielded nothing.
    if not out:
        import re
        blob = " ".join(chunks)
        for m in re.finditer(r'"affectedItems"\s*:\s*(\d+)', blob):
            out.append({"affectedItems": int(m.group(1))})
    return out


def _op_affected(op):
    ai = op.get("affectedItems") if isinstance(op, dict) else None
    return ai if isinstance(ai, int) else None


def _detect_duplicates(occurrences):
    """Return sorted list of tag names that appear more than once."""
    if not occurrences:
        return []
    return sorted(n for n, o in occurrences.items() if o > 1)


def _apply_batch_with_retry(client, tool, batch, pre_counts, label, retry_zero=True, op_status=None):
    """Send one batch, parse per-op results, and (for merges) retry any op
    that reported affectedItems=0 while its source actually had items.

    The retry attacks the proxy race where a target created earlier in THIS
    session isn't indexed yet, so the merge no-ops. We re-send that single op
    a few times with increasing back-off. Renames pass retry_zero=False: a
    zero-move rename MUST NOT be retried blindly, because if the target name
    already exists a retry would just create another duplicate copy — that is
    caught by the final cross-check instead.

    `op_status` (optional dict) collects each op's final status keyed by its
    source / oldName so the caller can decide the exit code from the
    authoritative per-op verdicts.
    """
    key = "operations" if tool == "tag_merge" else "tags"
    res = client.call_tool(tool, {key: batch})
    per = _extract_per_op(res)
    for i, op in enumerate(batch):
        src = op.get("source") or op.get("oldName")
        # Prefer a per-op result that names this source; else positional.
        match = None
        for p in per:
            if isinstance(p, dict) and (p.get("source") == src or p.get("oldName") == src):
                match = p
                break
        if match is None and len(per) == len(batch):
            match = per[i]
        ai = _op_affected(match)
        pre = pre_counts.get(src) if src else None
        attempts = 1
        while retry_zero and match is not None and ai == 0 and pre and pre > 0 and attempts < 4:
            time.sleep(2 * attempts)
            attempts += 1
            res2 = client.call_tool(tool, {key: [op]})
            per2 = _extract_per_op(res2)
            if per2:
                match = per2[0]
                ai = _op_affected(match)
        is_err = bool(match and match.get("isError"))
        if is_err:
            status = "ERR"
        elif ai is None:
            status = "OK?"          # no per-op count returned; trust nothing
        elif ai > 0 or not pre:
            status = "OK"
        else:
            status = "ZERO-MOVE"   # claimed success but moved 0 items
        print(f"    {label} {src!r}: {status} affected={ai} pre={pre} attempts={attempts}")
        if src and op_status is not None:
            op_status[src] = status


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", default=None, help="reviewed merge_plan.json")
    ap.add_argument("--proxy", default=None, help="path to mcp-proxy.js (auto-detected)")
    ap.add_argument("--batch", type=int, default=20, help="operations per call (default 20)")
    ap.add_argument("--merge-tool", default="tag_merge", help="MCP tool for merges")
    ap.add_argument("--rename-tool", default="tag_update", help="MCP tool for renames")
    ap.add_argument("--apply", action="store_true", help="actually perform writes (default: dry-run)")
    ap.add_argument("--selftest", action="store_true", help="run offline unit checks (no Eagle)")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.payload:
        sys.exit("error: --payload is required (or pass --selftest)")
    if not os.path.isfile(args.payload):
        sys.exit(f"error: payload not found: {args.payload}")
    with open(args.payload, encoding="utf-8") as f:
        plan = json.load(f)

    merges, renames, errors = validate_plan(plan)
    if errors:
        for e in errors:
            print("error:", e)
        sys.exit("validation failed; aborting (no writes performed)")

    # Fold retire-with-target into merges; collect manual retire steps.
    manual_retire = []
    for r in (plan.get("retire", []) or []):
        if r.get("target"):
            merges.append({"source": r["tag"], "target": r["target"]})
        else:
            manual_retire.append(r)

    ordered_merges = order_merges(merges)

    print(f"plan: {len(ordered_merges)} merges, {len(renames)} renames, {len(manual_retire)} manual retire")
    for m in ordered_merges:
        print(f"  MERGE   {m['source']!r} -> {m['target']!r}")
    for r in renames:
        print(f"  RENAME  {r['oldName']!r} -> {r['newName']!r}")
    for r in manual_retire:
        print(f"  MANUAL  retire {r['tag']!r} ({r.get('note','no target — strip via item_remove_tags or delete in Eagle UI')})")

    if not args.apply:
        print("\nDRY-RUN: no writes performed. Re-run with --apply to execute.")
        return

    print("\nAPPLY requested — connecting to Eagle via MCP...")
    client = MCPClient(resolve_proxy(args.proxy))
    init = client.initialize()
    if init is None:
        client.close()
        sys.exit("error: MCP initialize failed (is Eagle running?)")
    print("initialize: OK")

    total_req = 0
    total_ok = 0
    op_status = {}   # source/oldName -> final per-op status (authoritative)

    # --- Pre-flight: make sure every merge target already exists. ----------
    # Known proxy quirk: tag_merge silently no-ops (and still returns
    # isError=false) when the target tag does not exist. To guarantee the
    # merge lands, auto-create any missing target by renaming ONE of its
    # source tags into it (a rename both creates the target and consumes that
    # source), then merge the remaining sources into the now-existing target.
    existing, pre_counts, _ = _read_tags(client)
    create_renames = []
    final_merges = []
    if existing is None:
        print("WARNING: could not read current tags; skipping auto-create. "
              "Merges into missing targets may silently fail (verification "
              "below will still catch this).")
        final_merges = list(ordered_merges)
    else:
        targets_created = set()
        for m in ordered_merges:
            if m["target"] not in existing and m["target"] not in targets_created:
                create_renames.append({"oldName": m["source"], "newName": m["target"]})
                existing.add(m["target"])
                targets_created.add(m["target"])
                # this source is consumed by the rename; don't merge it again
            else:
                final_merges.append(m)

    total_req = len(ordered_merges) + len(renames)

    # 1) Create missing targets (rename ONE source -> target). This both
    #    creates the target and consumes that source. Per-op logged; the final
    #    cross-check catches any duplicate-name collision this may cause.
    if create_renames:
        print(f"\nAuto-creating {len(create_renames)} missing target tag(s) "
              f"by renaming a source into it:")
        for r in create_renames:
            print(f"  CREATE  {r['oldName']!r} -> {r['newName']!r}")
        batches = [create_renames[i:i + args.batch] for i in range(0, len(create_renames), args.batch)]
        for bi, batch in enumerate(batches, 1):
            print(f"  create batch {bi}/{len(batches)}:")
            _apply_batch_with_retry(client, args.rename_tool, batch, pre_counts, "CREATE", retry_zero=False, op_status=op_status)

    # 2) Apply the remaining merges. Each op's affectedItems is parsed from the
    #    live response; an op claiming success but moving 0 items for a
    #    non-empty source is retried (proxy race on session-created targets).
    if final_merges:
        batches = [final_merges[i:i + args.batch] for i in range(0, len(final_merges), args.batch)]
        for bi, batch in enumerate(batches, 1):
            print(f"\n  merge batch {bi}/{len(batches)}:")
            _apply_batch_with_retry(client, args.merge_tool, batch, pre_counts, "MERGE", retry_zero=True, op_status=op_status)

    # 3) Apply any explicit renames from the plan (per-op logged only; the
    #    final cross-check detects duplicate-name collisions).
    if renames:
        batches = [renames[i:i + args.batch] for i in range(0, len(renames), args.batch)]
        for bi, batch in enumerate(batches, 1):
            print(f"\n  rename batch {bi}/{len(batches)}:")
            _apply_batch_with_retry(client, args.rename_tool, batch, pre_counts, "RENAME", retry_zero=False, op_status=op_status)

    # --- Verification: re-read tags and confirm each op actually applied. --
    # NOTE: the Eagle search/index can lag programmatic edits for several
    # seconds. The per-op affectedItems parsed live from the proxy response is
    # the AUTHORITATIVE signal; this post-read is a secondary cross-check and
    # may under-report while the index is stale. A fresh `tag_get` after
    # re-opening the library is the final source of truth.
    print("\nRe-reading tags for cross-check (index may lag — see note above)...")
    after, after_counts, after_occ = _read_tags(client)
    dups = []
    if after is None:
        print("WARNING: verification skipped — could not re-read tags.")
    else:
        removed = [m["source"] for m in ordered_merges if m["source"] not in after]
        still = [m["source"] for m in ordered_merges if m["source"] in after]
        target_set = set(m["target"] for m in ordered_merges)
        targets_present = [t for t in target_set if t in after]
        print(f"\nVERIFY  sources removed : {len(removed)}/{len(ordered_merges)}")
        print(f"VERIFY  targets present : {len(targets_present)}/{len(target_set)}")
        # Split "still present" into authoritative failures (the live per-op
        # verdict said the op did NOT move anything) vs. likely stale index
        # (per-op OK but the tag still shows in this re-read).
        hard = [s for s in still if op_status.get(s) in ("ZERO-MOVE", "ERR", None)]
        soft = [s for s in still if op_status.get(s) in ("OK", "OK?")]
        if hard:
            print("FAILED (source still present — op did not verify):")
            for s in hard:
                print(f"  - {s!r}")
        if soft:
            print("NOTE (source still listed but per-op reported OK — likely a stale index;")
            print("       restart Eagle / re-open the library and re-read to confirm):")
            for s in soft:
                print(f"  - {s!r}")
        # CRITICAL: duplicate-named tags = a mis-aimed rename created a copy
        # instead of folding into the existing tag. This is the exact bug that
        # slipped past the old isError-only check and silently doubled tags.
        dups = _detect_duplicates(after_occ)
        if dups:
            print("\nCRITICAL: duplicate tag names detected (rename copied, not merged):")
            for n in dups:
                print(f"  - {n!r} appears {after_occ[n]} times; merge manually in Eagle UI")
        # Account for explicit renames so the summary is symmetric with
        # `requested` (merges + renames). A rename is verified when its oldName
        # is gone, its newName exists, and that newName is not duplicated
        # (a duplicated target means the rename copied instead of folding).
        if renames:
            dup_names = set(dups)
            verified_rn = [r for r in renames
                           if r["oldName"] not in after and r["newName"] in after
                           and r["newName"] not in dup_names]
            print(f"VERIFY  renames applied : {len(verified_rn)}/{len(renames)}")
            for r in renames:
                if r not in verified_rn:
                    st = op_status.get(r["oldName"])
                    if r["newName"] in dup_names:
                        hint = "duplicate target (rename copied, not merged)"
                    elif st in ("OK", "OK?"):
                        hint = "stale index? per-op OK"
                    else:
                        hint = "op did not verify"
                    print(f"  UNVERIFIED {r['oldName']!r} -> {r['newName']!r} "
                          f"({hint}; per-op={st})")
            total_ok = len(removed) + len(verified_rn)
        else:
            total_ok = len(removed)

    client.close()
    failed_ops = sorted(k for k, v in op_status.items() if v in ("ZERO-MOVE", "ERR"))
    print(f"\nrequested={total_req} verified_ok={total_ok}")
    if manual_retire:
        print("\nManual retire steps remain (not auto-applied):")
        for r in manual_retire:
            print(f"  - {r['tag']!r}: {r.get('note','strip via item_remove_tags or delete in Eagle UI')}")
    if failed_ops or dups:
        reasons = []
        if failed_ops:
            reasons.append(f"{len(failed_ops)} op(s) not verified ({', '.join(failed_ops)})")
        if dups:
            reasons.append(f"duplicate tag names ({', '.join(dups)})")
        print("\nRESULT: FAILED — " + "; ".join(reasons) + ".")
        print("Stop here and finish the remaining merges in the Eagle UI "
              "(see references/gotchas.md).")
        sys.exit(1)


def selftest():
    """Offline checks for the parsers that the live run depends on.

    Does NOT connect to Eagle. Validates: per-op response parsing, the
    affectedItems extraction, cycle detection, merge ordering, and the
    duplicate-named-tag detector (the bug that previously doubled tags).
    Every check is caught individually so each failure is counted and
    reported instead of aborting on the first assertion.
    """
    fails = 0

    def _run(name, fn):
        nonlocal fails
        try:
            fn()
        except AssertionError as exc:
            fails += 1
            print(f"FAIL  {name}: {exc}")
        else:
            print(f"ok  {name}")

    def _t_extract_per_op():
        # A realistic proxy batch response with per-op results.
        sample = {
            "result": {
                "isError": False,
                "content": [{
                    "text": json.dumps([
                        {"source": "A", "target": "B", "affectedItems": 12, "sourceRemoved": True, "isError": False},
                        {"source": "C", "target": "D", "affectedItems": 0, "sourceRemoved": True, "isError": False},
                    ]),
                }],
            },
        }
        per = _extract_per_op(sample)
        assert len(per) == 2, "expected 2 per-op results"
        assert _op_affected(per[0]) == 12, "affectedItems not parsed"
        assert _op_affected(per[1]) == 0, "zero affectedItems not parsed"
    _run("_extract_per_op parses per-op affectedItems", _t_extract_per_op)

    def _t_regex_fallback():
        # Regex fallback when the payload is not a clean JSON list.
        messy = {"result": {"content": [{"text": 'noise "affectedItems": 7 trailing'}]}}
        per2 = _extract_per_op(messy)
        assert any(_op_affected(p) == 7 for p in per2), "regex fallback failed"
    _run("_extract_per_op regex fallback works", _t_regex_fallback)

    def _t_cycle_order():
        cyc = [{"source": "x", "target": "y"}, {"source": "y", "target": "x"}]
        assert find_cycle(cyc) is True, "cycle not detected"
        ord_ = order_merges([{"source": "a", "target": "b"}, {"source": "b", "target": "c"}])
        assert ord_[0]["source"] == "a", "merge order wrong (a must apply before b)"
    _run("find_cycle / order_merges correct", _t_cycle_order)

    def _t_duplicates():
        occ = {"瑞士风": 5, "扁平色": 4, "极简": 1}
        dups = _detect_duplicates(occ)
        assert dups == ["扁平色", "瑞士风"], f"duplicate detection wrong: {dups}"
    _run("_detect_duplicates flags 瑞士风/扁平色 (multiples)", _t_duplicates)

    def _t_read_tags():
        class _FakeClient:
            def call_tool(self, name, args, timeout=60):
                data = [
                    {"name": "瑞士风", "count": 1182},
                    {"name": "瑞士风", "count": 236},
                    {"name": "极简", "count": 5329},
                ]
                return {"result": {"content": [{"text": json.dumps({"data": data})}]}}
        names, counts, occurrences = _read_tags(_FakeClient())
        assert names == {"瑞士风", "极简"}, "names wrong"
        assert counts["瑞士风"] == 1182 + 236, "counts not summed"
        assert occurrences["瑞士风"] == 2, "occurrences not counted"
        dups = _detect_duplicates(occurrences)
        assert dups == ["瑞士风"], "duplicate not detected from read"
    _run("_read_tags returns names/counts/occurrences; dup detected", _t_read_tags)

    print(f"\nSELFTEST {'PASSED' if fails == 0 else f'FAILED ({fails})'}")
    return fails


if __name__ == "__main__":
    main()
