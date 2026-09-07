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
  - Per-batch success is judged by the tool's `isError` flag, never by
    string-matching. Re-read tags afterwards to confirm counts.

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
                "clientInfo": {"name": "eagle-tag-governance", "version": "1.0.0"},
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", required=True, help="reviewed merge_plan.json")
    ap.add_argument("--proxy", default=None, help="path to mcp-proxy.js (auto-detected)")
    ap.add_argument("--batch", type=int, default=20, help="operations per call (default 20)")
    ap.add_argument("--merge-tool", default="tag_merge", help="MCP tool for merges")
    ap.add_argument("--rename-tool", default="tag_update", help="MCP tool for renames")
    ap.add_argument("--apply", action="store_true", help="actually perform writes (default: dry-run)")
    args = ap.parse_args()

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

    if ordered_merges:
        batches = [ordered_merges[i:i + args.batch] for i in range(0, len(ordered_merges), args.batch)]
        for bi, batch in enumerate(batches, 1):
            res = client.call_tool(args.merge_tool, {"operations": batch})
            if res is None:
                print(f"  merge batch {bi}/{len(batches)}: TIMEOUT")
                continue
            is_err = res.get("result", {}).get("isError", False)
            text = (res.get("result", {}).get("content") or [{}])[0].get("text", "")
            print(f"  merge batch {bi}/{len(batches)}: isError={is_err} | {text[:200]}")
            if not is_err:
                total_req += len(batch)
                total_ok += len(batch)

    if renames:
        batches = [renames[i:i + args.batch] for i in range(0, len(renames), args.batch)]
        for bi, batch in enumerate(batches, 1):
            res = client.call_tool(args.rename_tool, {"tags": batch})
            if res is None:
                print(f"  rename batch {bi}/{len(batches)}: TIMEOUT")
                continue
            is_err = res.get("result", {}).get("isError", False)
            text = (res.get("result", {}).get("content") or [{}])[0].get("text", "")
            print(f"  rename batch {bi}/{len(batches)}: isError={is_err} | {text[:200]}")
            if not is_err:
                total_req += len(batch)
                total_ok += len(batch)

    client.close()
    print(f"\nrequested={total_req} confirmed_ok={total_ok}")
    if total_ok != total_req:
        print("WARNING: confirmed != requested — re-read tags to find silently dropped ops.")
    if manual_retire:
        print("\nManual retire steps remain (not auto-applied):")
        for r in manual_retire:
            print(f"  - {r['tag']!r}: {r.get('note','strip via item_remove_tags or delete in Eagle UI')}")


if __name__ == "__main__":
    main()
