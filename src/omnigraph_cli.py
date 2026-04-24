#!/usr/bin/env python3
"""`omnigraph` — unified CLI over Phases 0-5a.

Subcommands:
  status       — summarize pilot/ state (sessions, events, vault, aggregate)
  ingest       — enumerate sessions available via source adapters
  extract      — run qwen pipeline on one session (by sid) or many
  events       — materialize pilot/events/*.jsonl + index.json
  vault        — materialize pilot/vault/*.md
  aggregate    — stage-2 aggregation (full or --incremental)
  compile      — run a projection compiler (light_ir / claude_md / ...)
  index        — export HR git_history + run applicable HR build stages
  query        — ask a natural-language question over the indexed corpus
                 (stub — requires HR serve; prints a helpful message)
  pipeline     — sugar: events → vault → aggregate (idempotent)

Each subcommand wraps an existing module so nothing is duplicated. The CLI
exists to make the surface unified and teachable.

Usage (from repo root):
  python src/omnigraph_cli.py status
  python src/omnigraph_cli.py extract <session_id>
  python src/omnigraph_cli.py pipeline --sessions pilot/qwen --sessions pilot/full
  python src/omnigraph_cli.py compile claude_md --state pilot/qwen --out CLAUDE.md
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PILOT = ROOT / "pilot"

# Ensure src/ is on path for direct-imports below.
sys.path.insert(0, str(SRC))


# ----------------------------------------------------------------------
# status
# ----------------------------------------------------------------------

def _count_session_files(d: Path) -> int:
    if not d.exists():
        return 0
    n = 0
    for p in d.glob("*/*.json"):
        if p.stem == "global_profile" or "_logs" in str(p):
            continue
        n += 1
    return n


def cmd_status(args) -> int:
    rows = []
    rows.append(("extracted (pilot/qwen)", _count_session_files(PILOT / "qwen")))
    rows.append(("extracted (pilot/full)", _count_session_files(PILOT / "full")))
    rows.append(("normalized_full", _count_session_files(PILOT / "normalized_full")))
    events_dir = PILOT / "events"
    n_events = 0
    months = 0
    if events_dir.exists():
        months = sum(1 for _ in events_dir.glob("*.jsonl"))
        for f in events_dir.glob("*.jsonl"):
            n_events += sum(1 for _ in open(f))
    rows.append(("events", n_events))
    rows.append(("event months", months))
    vault_dir = PILOT / "vault"
    rows.append(("vault entities", sum(1 for _ in vault_dir.glob("*.md")) if vault_dir.exists() else 0))
    state = PILOT / "_aggregate_state.json"
    rows.append(("aggregate state", "present" if state.exists() else "absent"))
    gp_qwen = PILOT / "qwen" / "global_profile.json"
    rows.append(("global_profile.json (qwen)", "present" if gp_qwen.exists() else "absent"))
    print("OmniGraph status")
    for k, v in rows:
        print(f"  {k:32s} {v}")
    return 0


# ----------------------------------------------------------------------
# ingest
# ----------------------------------------------------------------------

def cmd_ingest(args) -> int:
    from sources import get_adapter, list_adapters  # type: ignore
    names = [args.provider] if args.provider else list_adapters()
    for name in names:
        adapter = get_adapter(name)
        sessions = list(adapter.iter_sessions())
        print(f"[{name}] {len(sessions)} sessions available")
        if args.verbose:
            for s in sessions[: args.limit]:
                print(f"  {s.session_id}  turns={len(s.turns)} arts={len(s.artifacts)}")
    return 0


# ----------------------------------------------------------------------
# extract
# ----------------------------------------------------------------------

def cmd_extract(args) -> int:
    # Delegate to qwen_pipeline's CLI — it already knows how to look up the
    # normalized session by sid. No re-imports to avoid initializing the
    # LM Studio client in this process when we don't need it.
    py = sys.executable
    script = SRC / "qwen_pipeline.py"
    rc = 0
    for sid in args.session_id:
        r = subprocess.run([py, str(script), sid])
        rc |= r.returncode
    return rc


# ----------------------------------------------------------------------
# events / vault / aggregate / compile / index  (thin wrappers)
# ----------------------------------------------------------------------

def cmd_events(args) -> int:
    from build_events_stream import build as build_events  # type: ignore
    indirs = [Path(p) for p in (args.sessions or [PILOT / "qwen"])]
    meta = build_events(indirs, Path(args.out))
    print(f"✅ {meta['events_total']} events, {meta['distinct_targets']} targets")
    return 0


def cmd_vault(args) -> int:
    from build_vault import build as build_vault_fn  # type: ignore
    sessions_dirs = [Path(p) for p in (args.sessions or [PILOT / "qwen"])]
    r = build_vault_fn(Path(args.events), sessions_dirs, Path(args.out))
    print(f"✅ {r['entities_written']} entities")
    return 0


def cmd_aggregate(args) -> int:
    from stage2_aggregate import aggregate_full, aggregate_incremental, DEFAULT_STATE_PATH  # type: ignore
    indir = Path(args.indir)
    state_path = Path(args.state) if args.state else DEFAULT_STATE_PATH
    if args.full:
        gp = aggregate_full(indir)
        n_new = None
    else:
        gp, n_new = aggregate_incremental(indir, state_path)
    out = indir / "global_profile.json"
    out.write_text(json.dumps(gp, indent=2, ensure_ascii=False, default=str))
    print(f"✅ {out}  sessions={gp['scale']['sessions']}")
    if n_new is not None:
        print(f"   incremental: +{n_new}")
    return 0


def cmd_compile(args) -> int:
    from compiler import get_compiler, list_targets  # type: ignore
    from compiler.base import VaultState  # type: ignore
    from compiler.sanitize import sanitize_global_profile, VALID_LEVELS  # type: ignore
    if args.target not in list_targets():
        print(f"unknown target {args.target!r}; have {list_targets()}", file=sys.stderr)
        return 2
    state = VaultState.from_dir(Path(args.state))
    sanitize = getattr(args, "sanitize", "none") or "none"
    if sanitize not in VALID_LEVELS:
        print(f"bad --sanitize {sanitize!r}; have {VALID_LEVELS}", file=sys.stderr)
        return 2
    if sanitize != "none":
        state.global_profile = sanitize_global_profile(state.global_profile, sanitize)
    text = get_compiler(args.target).compile(state, max_tokens=args.max_tokens)
    if args.out:
        p = Path(args.out).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"✅ {args.target} → {p} ({len(text)} chars)")
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def cmd_index(args) -> int:
    """In-process HR build. No subprocess."""
    from hr import build_all, load_sessions_from_extractions  # type: ignore
    dirs = args.sessions or [str(PILOT / "qwen")]
    sessions = load_sessions_from_extractions(dirs)
    print(f"📦 loaded {len(sessions)} sessions")
    bundle = build_all(
        sessions,
        min_weight=args.min_weight,
        max_targets_per_session=args.max_targets,
    )
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "cochange.json").write_text(json.dumps(bundle.cochange, indent=2))
    (out / "communities.json").write_text(json.dumps(bundle.communities, indent=2))
    (out / "criticality.json").write_text(json.dumps(bundle.criticality, indent=2))
    (out / "index_bundle.json").write_text(json.dumps(bundle.to_json(), indent=2))
    m = bundle.meta
    print(f"✅ hr bundle → {out}")
    print(f"   sessions={m['sessions']} cochange_modules={m['cochange_modules']} "
          f"cochange_pairs={m['cochange_pairs']} communities={m['communities']} "
          f"critical={m['critical_modules']}")
    for e in bundle.criticality["meta"]["top_10"]:
        print(f"   [{e['score']:.3f}] {e['module']}")
    return 0


# ----------------------------------------------------------------------
# query (stub)
# ----------------------------------------------------------------------

def cmd_query(args) -> int:
    hr_serve = Path(os.environ.get("HR_ROOT", "/home/beast/projects/hyperretrieval")) / "serve"
    print(f"`omnigraph query` requires HyperRetrieval serve/ to be running.")
    print(f"HR serve dir: {hr_serve}")
    print("Stub for now. Once HR serve exposes an HTTP/MCP endpoint, this")
    print("subcommand will POST the question there with the HR index directory")
    print("produced by `omnigraph index`, then pretty-print results.")
    print(f"question: {args.question!r}")
    return 0


# ----------------------------------------------------------------------
# pipeline (sugar)
# ----------------------------------------------------------------------

def cmd_pipeline(args) -> int:
    # events → vault → aggregate (on the first --sessions dir by convention).
    sessions = args.sessions or [str(PILOT / "qwen")]
    events_dir = Path(args.events_dir)
    vault_dir = Path(args.vault_dir)
    aggregate_indir = Path(sessions[0])

    # 1. events
    from build_events_stream import build as build_events  # type: ignore
    m = build_events([Path(s) for s in sessions], events_dir)
    print(f"[events] {m['events_total']} events, {m['distinct_targets']} targets")

    # 2. vault
    from build_vault import build as build_vault_fn  # type: ignore
    r = build_vault_fn(events_dir, [Path(s) for s in sessions], vault_dir)
    print(f"[vault] {r['entities_written']} entities")

    # 3. aggregate (incremental against first sessions dir)
    from stage2_aggregate import aggregate_incremental, DEFAULT_STATE_PATH  # type: ignore
    gp, n_new = aggregate_incremental(aggregate_indir, DEFAULT_STATE_PATH)
    (aggregate_indir / "global_profile.json").write_text(
        json.dumps(gp, indent=2, ensure_ascii=False, default=str)
    )
    print(f"[aggregate] sessions={gp['scale']['sessions']} (+{n_new} new)")
    return 0


# ----------------------------------------------------------------------
# dispatch
# ----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="omnigraph")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Summarize pilot/ state")

    p = sub.add_parser("ingest", help="Enumerate sessions via source adapters")
    p.add_argument("--provider", default=None, help="Limit to one adapter")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("extract", help="Run qwen pipeline on session(s)")
    p.add_argument("session_id", nargs="+")

    p = sub.add_parser("events", help="Build event stream")
    p.add_argument("--sessions", action="append")
    p.add_argument("--out", default=str(PILOT / "events"))

    p = sub.add_parser("vault", help="Build per-entity Vault")
    p.add_argument("--events", default=str(PILOT / "events"))
    p.add_argument("--sessions", action="append")
    p.add_argument("--out", default=str(PILOT / "vault"))

    p = sub.add_parser("aggregate", help="Stage-2 aggregation")
    p.add_argument("--indir", default=str(PILOT / "qwen"))
    p.add_argument("--full", action="store_true")
    p.add_argument("--state", default=None)

    p = sub.add_parser("compile", help="Run a projection compiler")
    p.add_argument("target")
    p.add_argument("--state", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--sanitize", default="none",
                   help="Sugar ladder: none | named_stripped | entities_removed | aggregated")

    p = sub.add_parser("index", help="In-process cochange + communities + criticality")
    p.add_argument("--sessions", action="append")
    p.add_argument("--out", default=str(PILOT / "hr_out"))
    p.add_argument("--min-weight", type=int, default=None)
    p.add_argument("--max-targets", type=int, default=60)

    p = sub.add_parser("query", help="(stub) Query the indexed corpus via HR serve")
    p.add_argument("question")

    p = sub.add_parser("pipeline", help="events → vault → aggregate in one go")
    p.add_argument("--sessions", action="append")
    p.add_argument("--events-dir", default=str(PILOT / "events"))
    p.add_argument("--vault-dir", default=str(PILOT / "vault"))

    return ap


DISPATCH = {
    "status": cmd_status,
    "ingest": cmd_ingest,
    "extract": cmd_extract,
    "events": cmd_events,
    "vault": cmd_vault,
    "aggregate": cmd_aggregate,
    "compile": cmd_compile,
    "index": cmd_index,
    "query": cmd_query,
    "pipeline": cmd_pipeline,
}


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    fn = DISPATCH[args.cmd]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
