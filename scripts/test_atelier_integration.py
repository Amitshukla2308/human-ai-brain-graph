#!/usr/bin/env python3
"""End-to-end integration smoke test: OmniGraph ↔ Atelier file-drop contract.

Creates a throwaway scratch tree that matches Atelier's canonical layout,
copies one real pilot session into it, runs every OmniGraph CLI subcommand
that writes to the Atelier tree, and asserts that each output lands at the
contract-specified path with the right shape.

Purpose: catch path / schema / contract mistakes (like the v0.2 →
v0.3.1 user-root regression) BEFORE they hit real Atelier data.

Usage:
    python scripts/test_atelier_integration.py            # run + tear down
    python scripts/test_atelier_integration.py --keep     # leave tree for inspection
    python scripts/test_atelier_integration.py --atelier-root /tmp/my_test  # explicit dir

Exit code 0 iff every assertion passed. Prints per-step ✓/✗.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
PILOT = REPO / "pilot"

TEST_USER_ID = "test-uuid-integration"
TEST_PROJECT = "TestProject"


# ANSI (always safe — nothing parses stdout of this script)
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.steps: list[tuple[str, bool, str]] = []

    def check(self, label: str, ok: bool, detail: str = "") -> bool:
        mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {mark} {label}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
        self.passed += 1 if ok else 0
        self.failed += 0 if ok else 1
        self.steps.append((label, ok, detail))
        return ok

    def report(self) -> int:
        total = self.passed + self.failed
        banner = f"{GREEN}ALL GREEN ({self.passed}/{total}){RESET}" if self.failed == 0 else f"{RED}FAILURES ({self.failed}/{total}){RESET}"
        print(f"\n{banner}")
        return 0 if self.failed == 0 else 1


def _run(cmd: list[str], cwd: Path | None = None, capture: bool = False, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a subcommand. Prints the invocation dimmed."""
    print(f"  {DIM}$ {' '.join(cmd)}{RESET}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=True,
        env={**os.environ, **(env or {})},
    )


def _seed_atelier_tree(atelier: Path, chk: Checker) -> None:
    print(f"\n{YELLOW}Seeding fake Atelier tree at {atelier}{RESET}")
    # Canonical dirs per contract
    (atelier / "data" / "users" / TEST_USER_ID / ".claude").mkdir(parents=True, exist_ok=True)
    (atelier / "data" / "users" / TEST_USER_ID / "data" / "events").mkdir(parents=True, exist_ok=True)
    (atelier / "data" / "sessions").mkdir(parents=True, exist_ok=True)
    (atelier / "projects" / TEST_PROJECT / "sessions").mkdir(parents=True, exist_ok=True)
    (atelier / "projects" / TEST_PROJECT / "canvas" / "nodes").mkdir(parents=True, exist_ok=True)
    (atelier / "projects" / TEST_PROJECT / "domain_brain").mkdir(parents=True, exist_ok=True)

    # meta.json (mimics Atelier's project meta shape)
    (atelier / "projects" / TEST_PROJECT / "meta.json").write_text(
        json.dumps({
            "name": TEST_PROJECT,
            "description": "Integration test harness — not a real project.",
            "stage": "pre-mvp",
            "created_at": "2026-04-24T00:00:00Z",
        }, indent=2)
    )

    # Seed a fake canvas node with raw_title only (not yet canonicalized).
    (atelier / "projects" / TEST_PROJECT / "canvas" / "nodes" / "n1.json").write_text(
        json.dumps({
            "id": "n1",
            "raw_title": "ZeroClaw-MCP",   # should canonicalize to "zeroclaw"
            "slug_canonical": None,
            "canonicalized_at": None,
        }, indent=2)
    )

    # Seed one domain_brain artifact so audit has something real to score.
    (atelier / "projects" / TEST_PROJECT / "domain_brain" / "industry_map.md").write_text(
        "# Industry Map\n\nStub. Integration test only.\n\n## Players\n- Test\n"
    )
    # open_questions stub in founder voice so audit detects founder_authored
    (atelier / "projects" / TEST_PROJECT / "domain_brain" / "open_questions.md").write_text(
        "# Open Questions\n\nI don't yet know how MahaRERA API rate-limits scale.\n"
        "My concern is that we'll hit quotas in production.\n"
    )

    # Find one real pilot session to smoke-test reflect against
    pilot_session_src: Path | None = None
    for d in (PILOT / "qwen", PILOT / "full"):
        for p in d.glob("*/*.json"):
            if p.stem in ("global_profile",):
                continue
            if "_logs" in str(p) or "_run_summary" in p.stem:
                continue
            pilot_session_src = p
            break
        if pilot_session_src:
            break
    if pilot_session_src is None:
        chk.check("locate a pilot session for reflect test", False, "no sessions under pilot/")
        return

    sid = pilot_session_src.stem
    # Write a fake structured session.json under data/sessions/<sid>/
    sess_dir = atelier / "data" / "sessions" / sid
    sess_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(pilot_session_src.read_text())
    # Ensure it has an atelier_user_id field (Atelier now writes this)
    data.setdefault("atelier_user_id", TEST_USER_ID)
    (sess_dir / "session.json").write_text(json.dumps(data, indent=2))
    # Also touch a raw.log to make the fallback path discoverable if needed.
    (sess_dir / "raw.log").write_text("user: hi\nassistant: hello\n")

    # Stash the test sid for reflect invocation
    (atelier / "_test_sid").write_text(sid)

    chk.check("atelier tree seeded", True, f"user={TEST_USER_ID} project={TEST_PROJECT} sid={sid}")


def _test_canonicalize(atelier: Path, chk: Checker) -> None:
    print(f"\n{YELLOW}Test: omnigraph canonicalize (Canvas slug reconciliation){RESET}")
    r = _run(
        [sys.executable, str(SRC / "omnigraph_cli.py"), "canonicalize",
         "--atelier-root", str(atelier), "--project", TEST_PROJECT],
    )
    chk.check("canonicalize exits 0", r.returncode == 0)
    node = json.loads((atelier / "projects" / TEST_PROJECT / "canvas" / "nodes" / "n1.json").read_text())
    chk.check("node slug_canonical filled", node.get("slug_canonical") == "zeroclaw",
              f"got {node.get('slug_canonical')!r}")
    chk.check("node canonicalized_at populated", bool(node.get("canonicalized_at")))


def _test_migrate(atelier: Path, chk: Checker) -> None:
    print(f"\n{YELLOW}Test: omnigraph migrate (no-op on empty legacy){RESET}")
    r = _run(
        [sys.executable, str(SRC / "omnigraph_cli.py"), "migrate",
         "--atelier-root", str(atelier), "--user-id", TEST_USER_ID, "--dry-run"],
    )
    chk.check("migrate --dry-run exits 0", r.returncode == 0)


def _test_domain_brain(atelier: Path, chk: Checker) -> None:
    print(f"\n{YELLOW}Test: omnigraph domain-brain audit{RESET}")
    r = _run(
        [sys.executable, str(SRC / "omnigraph_cli.py"), "domain-brain",
         "--project-root", str(atelier / "projects" / TEST_PROJECT), "--json"],
        capture=True,
    )
    chk.check("domain-brain exits 0", r.returncode == 0)
    try:
        report = json.loads(r.stdout)
    except Exception as e:
        chk.check("domain-brain emits JSON", False, f"{e}")
        return
    chk.check("domain-brain reports project name", report.get("project") == TEST_PROJECT)
    chk.check("domain-brain has gaps for missing artifacts", len(report.get("gaps") or []) >= 1)
    # open_questions was seeded in founder voice → must show founder_authored
    art = next((a for a in report.get("artifacts") or [] if a.get("kind") == "open_questions"), None)
    chk.check("founder voice detected in open_questions.md", bool(art and art.get("founder_authored")))


def _test_reflect(atelier: Path, chk: Checker) -> None:
    print(f"\n{YELLOW}Test: omnigraph reflect (skip-extraction + skip-synthesis){RESET}")
    sid_file = atelier / "_test_sid"
    if not sid_file.exists():
        chk.check("test sid exists", False)
        return
    sid = sid_file.read_text().strip()
    # Feed the pilot JSON directly via --session-json so we don't re-extract.
    # Finds it in pilot/qwen or pilot/full.
    src = None
    for d in (PILOT / "qwen", PILOT / "full"):
        for p in d.glob("*/*.json"):
            if p.stem == sid:
                src = p
                break
        if src:
            break
    if not src:
        chk.check("pilot source for test sid", False, f"sid={sid}")
        return

    r = _run(
        [sys.executable, str(SRC / "omnigraph_cli.py"), "reflect",
         "--session-id", sid,
         "--session-json", str(src),
         "--atelier-root", str(atelier),
         "--user-id", TEST_USER_ID,
         "--project", TEST_PROJECT,
         "--skip-extraction", "--skip-synthesis"],
        capture=True,
    )
    chk.check("reflect exits 0", r.returncode == 0, f"stderr={r.stderr[:200]}")
    try:
        summary = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        chk.check("reflect emits JSON summary on stdout", False, f"{e}")
        return
    chk.check("reflect summary ok=true", summary.get("ok") is True)

    # Reflection artifact at canonical path
    refl_path = atelier / "projects" / TEST_PROJECT / "sessions" / f"{sid}.md"
    chk.check("reflection md at projects/<P>/sessions/<sid>.md", refl_path.exists(),
              str(refl_path))
    if refl_path.exists():
        body = refl_path.read_text()
        chk.check("reflection frontmatter carries atelier_user_id",
                  f"atelier_user_id: {TEST_USER_ID}" in body)
        chk.check("reflection frontmatter carries project",
                  f"project: {TEST_PROJECT}" in body)

    # Raw events at canonical user-scoped path
    events_dir = atelier / "data" / "users" / TEST_USER_ID / "data" / "events"
    chk.check("events/<YYYY-MM>.jsonl exists",
              any(events_dir.glob("*.jsonl")), str(events_dir))

    # Validate events-records carry project + atelier_user_id-independent tagging
    any_events = False
    for jl in events_dir.glob("*.jsonl"):
        for line in jl.open():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            any_events = True
            chk.check("event record carries project", rec.get("project") == TEST_PROJECT,
                      f"in {jl.name}")
            break
        if any_events:
            break
    if not any_events:
        chk.check("events jsonl has ≥1 record", False)


def _test_compile(atelier: Path, chk: Checker) -> None:
    print(f"\n{YELLOW}Test: omnigraph compile (atelier-aware output path){RESET}")
    # Seed a minimal global_profile so the compiler has something to write.
    gp_dir = atelier / "data" / "users" / TEST_USER_ID / "brain" / "personal"
    gp_dir.mkdir(parents=True, exist_ok=True)
    (gp_dir / "global_profile.json").write_text(json.dumps({
        "scale": {"sessions": 1, "providers": ["test"], "total_mention_events": 1, "total_deltas": 0},
        "confirmed_mental_moves": [{"move": "test move", "level": "gen", "owner": "user", "occurrences": 2}],
        "rules_collected": [{"rule_text": "test rule", "applies_to": "general", "level": "gen"}],
        "inference_p5_concern_lifecycle": [],
        "inference_p3_decision_load_bearing": [],
        "entity_frequency_top30": [],
        "drift_recurrence_by_trigger": [],
    }))

    for target in ("light_ir", "claude_md", "boot_context", "brain_view"):
        r = _run(
            [sys.executable, str(SRC / "omnigraph_cli.py"), "compile",
             target,
             "--atelier-root", str(atelier),
             "--user-id", TEST_USER_ID],
            capture=True,
        )
        chk.check(f"compile {target} exits 0", r.returncode == 0, r.stderr[:120])
        # Verify landed in canonical compiled/ dir
        compiled = atelier / "data" / "users" / TEST_USER_ID / "brain" / "personal" / "compiled"
        ext_map = {"light_ir": "light_ir.xml", "claude_md": "claude.md", "boot_context": "boot_context.json", "brain_view": "brain_view.json"}
        out_path = compiled / ext_map[target]
        chk.check(f"compile {target} landed at compiled/{ext_map[target]}", out_path.exists(),
                  str(out_path))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atelier-root", default=None, help="Use an explicit scratch dir instead of /tmp/...")
    ap.add_argument("--keep", action="store_true", help="Leave the scratch tree for inspection")
    args = ap.parse_args(argv)

    if args.atelier_root:
        atelier = Path(args.atelier_root).expanduser()
        if atelier.exists():
            shutil.rmtree(atelier)
        atelier.mkdir(parents=True, exist_ok=True)
        created_tmp = False
    else:
        atelier = Path(tempfile.mkdtemp(prefix="omnigraph_atelier_test_"))
        created_tmp = True

    print(f"{YELLOW}Test root: {atelier}{RESET}")
    chk = Checker()
    try:
        _seed_atelier_tree(atelier, chk)
        _test_canonicalize(atelier, chk)
        _test_migrate(atelier, chk)
        _test_domain_brain(atelier, chk)
        _test_compile(atelier, chk)
        _test_reflect(atelier, chk)
    finally:
        rc = chk.report()
        if not args.keep and created_tmp:
            shutil.rmtree(atelier, ignore_errors=True)
            print(f"{DIM}(tree torn down — pass --keep to inspect){RESET}")
        else:
            print(f"{DIM}Tree retained at {atelier}{RESET}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
