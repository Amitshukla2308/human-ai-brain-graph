#!/usr/bin/env python3
"""
Qwen3.6-35B-A3B extraction pipeline for OmniGraph.
Implements PIPELINE.md phases 1-5 against an LM Studio OpenAI-compatible endpoint.

Usage:
    python qwen_pipeline.py <session_id> [--provider <name>]
    python qwen_pipeline.py --all                     # run all 25 pilot sessions
    python qwen_pipeline.py --aggregate              # Stage 2 over pilot/qwen/*/
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import glob
import argparse
from pathlib import Path
from typing import Any, Optional

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None

BASE_URL = os.environ.get("QWEN_BASE_URL", "http://192.168.88.2:1234/v1")
MODEL = os.environ.get("QWEN_MODEL", "qwen/qwen3.6-35b-a3b")
TEMPERATURE = 0.3
# Budgets tuned per-phase. Phase 1a (enumerating all mentions) is heaviest;
# Phase 2/3 (verification + critique over a full extraction) also substantial.
# Qwen's thinking tokens count against max_tokens — undersized budgets cause
# finish_reason=length with content="".
MAX_TOKENS_DEFAULT = 16384
MAX_TOKENS_DENSE = 32768   # for 1a mentions + 2 verify + 3 critique (entire object graph in prompt)
REQUEST_TIMEOUT = 1200  # 20 min per call

PILOT = Path("/home/beast/projects/omnigraph/pilot")
NORM_DIR = PILOT / "normalized"
OUT_DIR = PILOT / "qwen"
LOG_DIR = PILOT / "qwen" / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# Qwen client
# ----------------------------------------------------------------------

def qwen_call(system: str, user: str, *, max_tokens: int = MAX_TOKENS_DEFAULT,
              temp: float = TEMPERATURE, retries: int = 2) -> dict:
    """One chat completion. Returns {content, reasoning, elapsed, tokens}."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temp,
        "max_tokens": max_tokens,
    }
    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            req = urllib.request.Request(
                f"{BASE_URL}/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                resp = json.loads(r.read())
            dt = time.time() - t0
            msg = resp["choices"][0]["message"]
            return {
                "content": (msg.get("content") or "").strip(),
                "reasoning": (msg.get("reasoning_content") or "").strip(),
                "elapsed_s": round(dt, 2),
                "usage": resp.get("usage", {}),
                "finish_reason": resp["choices"][0].get("finish_reason"),
            }
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(2)
                continue
            raise
    raise last_err  # unreachable


def parse_json_strict(text: str) -> Any:
    """Parse a model output expected to be JSON. Use json-repair if available."""
    if not text:
        return None
    # Strip common wrappers (```json fences etc.)
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    try:
        return json.loads(t)
    except Exception:
        if repair_json:
            try:
                return repair_json(t, return_objects=True)
            except Exception:
                return None
        return None


# ----------------------------------------------------------------------
# Prompt construction — few-shot exemplars + schema
# ----------------------------------------------------------------------

SYSTEM_BASE = """You are an extraction specialist for OmniGraph. You read canonical Turn[] transcripts of AI-assisted coding sessions and emit strictly-valid JSON per schema v0.2.1.

HARD RULES:
- Output ONLY JSON. No prose. No markdown fences.
- Every field you emit must have supporting evidence from the provided turns.
- If uncertain, err on the side of NOT emitting. False negatives are recoverable; false positives pollute the Vault.
- evidence_turn MUST be an integer matching a real turn index.
- evidence_quote MUST be ≤200 chars, copied verbatim from the turn body (text, thinking, or tool_calls).
- If a field is not applicable, set to null or omit; do not fabricate.
"""

EXEMPLARS_1A = '''Example GOOD MentionEvent (Tool, reference, reader):
{"target_id":"atelier-canvas-mcp","target_type":"Tool","mention_type":"reference","authorship":"reader","valence":"neutral","evidence_turn":1,"evidence_quote":"mcp_atelier_canvas_query","mentioned_as":"mcp_atelier_canvas_query","co_mentioned_with":[]}

Example GOOD MentionEvent (Tool, concern_raised, writer, frustrated):
{"target_id":"desktop-commander-read-file","target_type":"Tool","mention_type":"concern_raised","authorship":"writer","valence":"frustrated","evidence_turn":99,"evidence_quote":"The issue is with read_file not showing the content. Let me try a different approach","mentioned_as":"read_file","co_mentioned_with":["desktop-commander-mcp"]}

Example BAD (do NOT do this — implementation detail is not an Entity):
{"target_id":"5-bar-window","target_type":"Concept"}   // this is a threshold inside a rule, not a standalone target

SLUG RULES:
- lowercase, hyphen-separated
- strip version suffixes (-v2, -v6.2)
- strip stopwords like "the", "mcp"
- prefer short canonical forms ("kimi" not "kimi-2.5")
'''

EXEMPLARS_1B = '''Example GOOD Decision (delta-gated, authored this session):
{"proposition":"LLM temperature dropped from 0.6 → 0.3 for trading engine","status":"locked","why":"Trading decisions demand consistency over creativity","alternatives_considered":[],"decided_by":"user","related_entities":["engine-py"],"origin":"made_this_session","evidence_turn":5,"evidence_quote":"Before: temperature=0.6, After: temperature=0.3"}

Example BAD (this is context, not a delta — must go in MentionEvents with target_type=Decision):
"Fastbrick canvas has 12 approved nodes" — this was decided in a prior session. Session only references it. DO NOT emit as Decision.
'''

EXEMPLARS_1C = '''Example GOOD Drift (self_catch, with thinking-block evidence):
{"proposed":"Use the generalist MCP agent to read canvas graph.json directly","corrected_to":"Pivot to mcp_atelier_canvas_get_node + codebase_investigator","trigger":"self_catch","trigger_detail":"Assistant observed in thinking block that generalist faltered; pivoted to specialized tools","rule_generated":"When a generalist retrieval fails on structured data, pivot to domain-specific MCP tools","evidence_turn":4,"evidence_quote":"The initial generalist agent faltered on retrieving the raw JSON, so I will pivot"}

Example BAD (do NOT emit): simple tool swap without stated failure observation. Switching tools between turns is normal, not a drift. Drift requires: (a) proposed X, (b) corrected to ¬X, (c) reason given.
'''

EXEMPLARS_1D = '''Example GOOD MentalMove (generalizable, assistant-observed):
{"move":"Self-catch and pivot on tool-path failure","level":"generalizable","owner":"assistant","evidence_turn":4,"evidence_quote":"The initial generalist agent faltered on retrieving the raw JSON, so I will pivot","note":"Model named the failure in thinking block, not silently retried."}

Example GOOD MentalMove (user_specific):
{"move":"Numbered multi-step directive style — user pre-decomposes work, expects strict order","level":"user_specific","owner":"user","evidence_turn":0,"evidence_quote":"Please do the following: 1. Read the file 2. Search for 3. Show 4. Create 5. Report"}

Example GOOD Affect (explicit emotional language):
{"marker":"frustration","owner":"user","trigger":"WSL crashing","implication":"Infrastructure instability blocks work","evidence_quote":"Something is crashing wsl, quickly check and fix it","evidence_turn":0}

LEVEL TAGGING:
- axiom: user never states it as a rule but operates from it always (rare)
- generalizable: universal principle any thoughtful person would benefit from
- user_specific: personal style or preference
'''

EXEMPLARS_1E = '''Example GOOD Stance:
{"proposition":"Start development with Parse or Bodyguard — highest-risk data boundaries","stance":"lean_toward","target":"own_proposal","reason":"highest-risk data boundaries","evidence_turn":6,"evidence_quote":"My lean is starting with the Parse or Bodyguard port"}

Example GOOD Rule (from a verified Drift):
{"rule_text":"When a generalist retrieval fails on structured data, pivot to domain-specific MCP tools","applies_to":"principle","source":{"type":"drift","evidence_turn":4},"level":"generalizable"}

Example MetaMoment (rare — only if explicit):
{"observation":"We are demonstrating the target capability without the tool existing yet","evidence_turn":15}
'''


def build_turns_text(session: dict, max_chars: int = 120_000) -> str:
    """Render the normalized turns as text for injection into prompts.
    For artifact sessions, render artifacts instead."""
    if session.get("input_type") == "artifacts":
        out = []
        for a in session.get("artifacts", []):
            if a.get("filename", "").endswith(".md"):
                out.append(f"--- {a['filename']} ({a['size']} bytes) ---\n{a.get('content','')[:8000]}\n")
        text = "\n".join(out)
        return text[:max_chars]
    lines = []
    for t in session.get("turns", []):
        idx = t["index"]
        role = t["role"]
        ts_raw = t.get("timestamp")
        if isinstance(ts_raw, (int, float)):
            # Cline stores timestamp as ms-epoch integer; coerce to ISO-ish
            try:
                ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts_raw / 1000 if ts_raw > 1e12 else ts_raw))
            except Exception:
                ts = str(ts_raw)[:19]
        else:
            ts = (ts_raw or "")[:19]
        text = (t.get("text") or "").strip()
        think = (t.get("thinking") or "").strip()
        tc = t.get("tool_calls") or []
        parts = [f"[t{idx}] {role} @{ts}"]
        if text:
            parts.append(f"  text: {text[:1500]}")
        if think:
            parts.append(f"  thinking: {think[:1500]}")
        if tc:
            tc_str = "; ".join(f"{c.get('name','?')}({str(c.get('input',''))[:200]})" for c in tc[:3])
            parts.append(f"  tool_calls: {tc_str}")
        lines.append("\n".join(parts))
    full = "\n\n".join(lines)
    if len(full) > max_chars:
        # Keep first 70% and last 20% to preserve openings and closings
        head = full[: int(max_chars * 0.7)]
        tail = full[-int(max_chars * 0.2):]
        full = head + "\n\n[... middle truncated for context budget ...]\n\n" + tail
    return full


# ----------------------------------------------------------------------
# Phase prompts
# ----------------------------------------------------------------------

def prompt_phase1a_mentions(turns_text: str) -> tuple[str, str]:
    sys = SYSTEM_BASE + "\n\nPHASE 1a — Extract all MentionEvents (Entity/Tool/Project/Concept/Artifact/Error/Decision references)."
    usr = f"""{EXEMPLARS_1A}

TASK: Read the following turns. Emit a JSON object with key "mention_events" whose value is a JSON array of MentionEvent objects for every referenced target. Include targets mentioned in text, thinking, or tool_calls. Each mention in a distinct turn is a separate event. Do not invent targets not present in the turns.

TURNS:
{turns_text}

Return ONLY: {{"mention_events": [...]}}"""
    return sys, usr


def prompt_phase1b_decisions(turns_text: str) -> tuple[str, str]:
    sys = SYSTEM_BASE + "\n\nPHASE 1b — Extract Decisions DELTA-GATED (only if authored, revisited, or overturned in THIS session)."
    usr = f"""{EXEMPLARS_1B}

TASK: Read the turns. Emit {{"decisions": [...]}} listing only decisions AUTHORED/REVISITED/OVERTURNED in this session. A decision that is merely mentioned as pre-existing context goes in Phase 1a mentions, NOT here. If no decisions were authored, return {{"decisions": []}}.

TURNS:
{turns_text}

Return ONLY: {{"decisions": [...]}}"""
    return sys, usr


def prompt_phase1c_drifts(turns_text: str) -> tuple[str, str]:
    sys = SYSTEM_BASE + "\n\nPHASE 1c — Extract Drifts (only genuine course-corrections with observed failure reason)."
    usr = f"""{EXEMPLARS_1C}

TASK: Read the turns. A Drift requires: (a) a proposed path X, (b) correction to ¬X, (c) reason stated (in text, thinking, or a failing tool_result). Emit {{"drifts": [...]}}. Empty list if none. Do not emit normal tool sequences as drifts.

TURNS:
{turns_text}

Return ONLY: {{"drifts": [...]}}"""
    return sys, usr


def prompt_phase1d_moves_affect(turns_text: str) -> tuple[str, str]:
    sys = SYSTEM_BASE + "\n\nPHASE 1d — Extract MentalMoves (observed reasoning patterns) and Affect (explicit emotional markers)."
    usr = f"""{EXEMPLARS_1D}

TASK: Read the turns. Emit {{"mental_moves": [...], "affect": [...]}}. MentalMove requires a level tag (axiom|generalizable|user_specific). Affect requires explicit emotional language. Empty arrays if none.

TURNS:
{turns_text}

Return ONLY: {{"mental_moves": [...], "affect": [...]}}"""
    return sys, usr


def prompt_phase1e_stances_rules_meta(turns_text: str, drifts: list) -> tuple[str, str]:
    sys = SYSTEM_BASE + "\n\nPHASE 1e — Extract Stances, Rule candidates (from verified Drifts/MentalMoves), and MetaMoments."
    drifts_json = json.dumps(drifts, ensure_ascii=False)[:4000]
    usr = f"""{EXEMPLARS_1E}

Verified drifts from Phase 1c (use as sources for Rule candidates):
{drifts_json}

TASK: Read the turns. Emit {{"stances": [...], "rules": [...], "meta_moments": [...], "artifacts": [...], "unresolved": [...]}}. Rules should derive from the provided drifts or from mental moves. MetaMoments are rare (only if the session explicitly reflects on itself). Artifacts are files CREATED this session. Unresolved are open questions/items flagged at session end.

TURNS:
{turns_text}

Return ONLY: {{"stances": [...], "rules": [...], "meta_moments": [...], "artifacts": [...], "unresolved": [...]}}"""
    return sys, usr


def prompt_phase2_verify(phase1_out: dict, turns_text: str) -> tuple[str, str]:
    sys = SYSTEM_BASE + "\n\nPHASE 2 — VERIFICATION. Check each extracted object against the cited evidence turn."
    objs_json = json.dumps(phase1_out, ensure_ascii=False)[:30000]
    usr = f"""TASK: For each object below (in any of mention_events, decisions, drifts, mental_moves, stances, affect, rules, meta_moments, artifacts, unresolved):
- Re-read the cited evidence_turn in the TURNS section below (plus ±1 adjacent turns for context).
- Classify each object as exactly one of: "supported" | "over_claimed" | "unsupported".

Return the same JSON structure but with an added "_verdict" field on each object. Do not remove any objects; the next step will filter.

OBJECTS:
{objs_json}

TURNS:
{turns_text}

Return ONLY the JSON structure with _verdict added."""
    return sys, usr


def prompt_phase3_critique(supported: dict) -> tuple[str, str]:
    sys = """You are a skeptical editor reviewing an OmniGraph extraction for publication. Your job is to flag extraction errors. Output ONLY JSON.

Flag any item that is:
- Missing evidence (evidence_turn or evidence_quote empty/implausible)
- Over-interpretation of routine exchanges as Drifts
- Generic rules that don't specify a behavior ("be careful", "think first" etc.)
- Entity mentions that are actually implementation details (specific numbers, field names inside a concept)
- Hallucinated content not in the evidence_quote
"""
    objs_json = json.dumps(supported, ensure_ascii=False)[:25000]
    usr = f"""Review these extracted objects. For each, add "_critique_verdict": "keep" | "drop" with a short "_critique_reason" (<50 chars).

OBJECTS:
{objs_json}

Return ONLY the same JSON structure with _critique_verdict and _critique_reason added."""
    return sys, usr


# ----------------------------------------------------------------------
# Pipeline runner
# ----------------------------------------------------------------------

def run_session(norm_path: Path, out_path: Path, log_path: Path) -> dict:
    session = json.loads(norm_path.read_text())
    sid = session["session_id"]
    prov = session["provider"]
    turns_text = build_turns_text(session)

    log = {"session_id": sid, "provider": prov, "phases": [], "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "turns_text_chars": len(turns_text)}

    def run_phase(name: str, sys_p: str, usr_p: str, max_tokens: int = MAX_TOKENS_DEFAULT) -> dict:
        t0 = time.time()
        resp = qwen_call(sys_p, usr_p, max_tokens=max_tokens)
        parsed = parse_json_strict(resp["content"])
        # If content was empty due to thinking overrun, try once more with more budget
        if resp.get("finish_reason") == "length" and not resp["content"]:
            log.setdefault("retries", []).append({"phase": name, "reason": "length_overrun", "attempt_budget": max_tokens * 2})
            resp = qwen_call(sys_p, usr_p, max_tokens=min(max_tokens * 2, 65536))
            parsed = parse_json_strict(resp["content"])
        phase_record = {
            "phase": name, "elapsed_s": resp["elapsed_s"],
            "usage": resp.get("usage"),
            "content_len": len(resp["content"]),
            "reasoning_len": len(resp["reasoning"]),
            "parsed_ok": parsed is not None,
            "finish_reason": resp.get("finish_reason"),
        }
        log["phases"].append(phase_record)
        return {"raw": resp, "parsed": parsed}

    # Phase 1a — MentionEvents (heaviest phase — large budget)
    p = run_phase("1a_mentions", *prompt_phase1a_mentions(turns_text), max_tokens=MAX_TOKENS_DENSE)
    mention_events = (p["parsed"] or {}).get("mention_events", []) if isinstance(p["parsed"], dict) else []

    # Phase 1b — Decisions
    p = run_phase("1b_decisions", *prompt_phase1b_decisions(turns_text))
    decisions = (p["parsed"] or {}).get("decisions", []) if isinstance(p["parsed"], dict) else []

    # Phase 1c — Drifts
    p = run_phase("1c_drifts", *prompt_phase1c_drifts(turns_text))
    drifts = (p["parsed"] or {}).get("drifts", []) if isinstance(p["parsed"], dict) else []

    # Phase 1d — MentalMoves + Affect
    p = run_phase("1d_moves_affect", *prompt_phase1d_moves_affect(turns_text))
    parsed = p["parsed"] or {}
    mental_moves = parsed.get("mental_moves", []) if isinstance(parsed, dict) else []
    affect = parsed.get("affect", []) if isinstance(parsed, dict) else []

    # Phase 1e — Stances, Rules, MetaMoments, Artifacts, Unresolved
    p = run_phase("1e_stances_rules_meta", *prompt_phase1e_stances_rules_meta(turns_text, drifts))
    parsed = p["parsed"] or {}
    stances = parsed.get("stances", []) if isinstance(parsed, dict) else []
    rules = parsed.get("rules", []) if isinstance(parsed, dict) else []
    meta_moments = parsed.get("meta_moments", []) if isinstance(parsed, dict) else []
    artifacts = parsed.get("artifacts", []) if isinstance(parsed, dict) else []
    unresolved = parsed.get("unresolved", []) if isinstance(parsed, dict) else []

    phase1 = {
        "mention_events": mention_events, "decisions": decisions, "drifts": drifts,
        "mental_moves": mental_moves, "affect": affect, "stances": stances,
        "rules": rules, "meta_moments": meta_moments, "artifacts": artifacts, "unresolved": unresolved,
    }

    # Phase 2 — Verification (entire object graph + turns — dense budget)
    p = run_phase("2_verify", *prompt_phase2_verify(phase1, turns_text), max_tokens=MAX_TOKENS_DENSE)
    verified = p["parsed"] if isinstance(p["parsed"], dict) else phase1

    # Drop objects that failed verification — robust against malformed Qwen output
    def keep_supported(items):
        if not isinstance(items, list):
            return []
        kept = []
        for o in items:
            if not isinstance(o, dict):
                continue
            v = (o.get("_verdict") or "supported").lower()
            if v == "supported":
                o.pop("_verdict", None)
                kept.append(o)
        return kept
    after_verify = {k: keep_supported(verified.get(k) if isinstance(verified, dict) else None) for k in phase1}

    # Phase 3 — Adversarial critique (entire object graph — dense budget)
    p = run_phase("3_critique", *prompt_phase3_critique(after_verify), max_tokens=MAX_TOKENS_DENSE)
    critiqued = p["parsed"] if isinstance(p["parsed"], dict) else after_verify

    def keep_after_critique(items):
        if not isinstance(items, list):
            return []
        kept = []
        for o in items:
            if not isinstance(o, dict):
                continue
            v = (o.get("_critique_verdict") or "keep").lower()
            if v == "keep":
                o.pop("_critique_verdict", None); o.pop("_critique_reason", None)
                kept.append(o)
        return kept
    final = {k: keep_after_critique(critiqued.get(k) if isinstance(critiqued, dict) else None) for k in phase1}

    # Phase 5 — assemble
    output = {
        "session_id": sid,
        "provider": prov,
        "extractor": f"qwen_pipeline:{MODEL}",
        "schema_version": "0.2.1",
        "session_meta": {
            "input_type": session.get("input_type", "dialog"),
            "source_normalized": str(norm_path),
        },
        **final,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    log["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    log["total_elapsed_s"] = round(sum(p["elapsed_s"] for p in log["phases"]), 1)
    log["object_counts"] = {k: len(v) for k, v in final.items()}
    log_path.write_text(json.dumps(log, indent=2))

    return {"output_path": str(out_path), "log": log}


def resolve_session(sid: str) -> Path:
    for f in NORM_DIR.glob("*/*.json"):
        if f.stem == sid:
            return f
    raise FileNotFoundError(f"normalized session not found: {sid}")


def run_one(sid: str) -> dict:
    norm = resolve_session(sid)
    prov = norm.parent.name
    out = OUT_DIR / prov / f"{sid}.json"
    log = LOG_DIR / f"{sid}.log.json"
    print(f"\n>>> {prov}/{sid} — starting", flush=True)
    try:
        r = run_one_safe(norm, out, log)
        print(f"    ✅ {sid} → {r['output_path']}  ({r['log']['total_elapsed_s']}s, counts={r['log']['object_counts']})", flush=True)
        return r
    except Exception as e:
        err = {"error": str(e), "session_id": sid}
        log.write_text(json.dumps(err, indent=2))
        print(f"    ❌ {sid}: {e}", flush=True)
        return {"error": str(e)}


def run_one_safe(norm: Path, out: Path, log: Path) -> dict:
    return run_session(norm, out, log)


def run_all():
    manifest = json.loads((PILOT / "SAMPLE_MANIFEST.json").read_text())
    sessions = []
    for prov, rows in manifest.items():
        for entry in rows:
            sid = entry["file"].replace(".jsonl", "").replace(".json", "").replace("local_", "")
            sessions.append((prov, sid))
    print(f"Running {len(sessions)} sessions", flush=True)
    results = []
    for i, (prov, sid) in enumerate(sessions, 1):
        print(f"\n[{i}/{len(sessions)}] {prov}/{sid}", flush=True)
        r = run_one(sid)
        results.append({"session_id": sid, "provider": prov, **r})
    summary_path = OUT_DIR / "_run_summary.json"
    summary_path.write_text(json.dumps(results, indent=2))
    print(f"\n✅ Run summary written: {summary_path}")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("session_id", nargs="?")
    ap.add_argument("--all", action="store_true", help="run all 25 sessions")
    args = ap.parse_args()
    if args.all:
        run_all()
    elif args.session_id:
        run_one(args.session_id)
    else:
        ap.print_help()
        sys.exit(2)
