#!/usr/bin/env python3
"""Phase 4 — scale Qwen extraction to full corpus (beyond 25-session pilot).

Normalizes any session not already normalized, then runs qwen_pipeline.py on each.
Output: pilot/full/<provider>/<session_id>.json

Usage:
    python phase4_scale.py claude_desktop      # process all CD sessions not in pilot
    python phase4_scale.py gemini_cli
    python phase4_scale.py cline
    python phase4_scale.py antigravity         # artifact-based
    python phase4_scale.py claude_code         # largest — partial run if time constrained
"""
import json
import os
import sys
import glob
import time
import subprocess
from pathlib import Path

ROOT = Path("/home/beast/projects/omnigraph")
AI_CONV = Path("/home/beast/ai_conversations")
PILOT = ROOT / "pilot"
NORM_FULL = PILOT / "normalized_full"
OUT_FULL = PILOT / "full"
LOG_FULL = PILOT / "full" / "_logs"

# Re-use normalizer logic from the pilot normalization run
import sys
sys.path.insert(0, str(ROOT / "src"))


def flatten_content(c):
    if isinstance(c, str): return {'text': c, 'thinking': '', 'tool_calls': []}
    text_parts, thinking_parts, tool_calls = [], [], []
    if isinstance(c, list):
        for block in c:
            if not isinstance(block, dict): continue
            t = block.get('type')
            if t == 'text': text_parts.append(block.get('text', ''))
            elif t == 'thinking': thinking_parts.append(block.get('thinking', block.get('text', '')))
            elif t == 'tool_use':
                tool_calls.append({'name': block.get('name'), 'input': str(block.get('input', ''))[:500]})
            elif t == 'tool_result':
                text_parts.append(f"[tool_result:{block.get('tool_use_id', '?')[:8]}] {str(block.get('content', ''))[:400]}")
    return {'text': '\n'.join(text_parts).strip(),
            'thinking': '\n'.join(thinking_parts).strip(),
            'tool_calls': tool_calls}


def normalize_claude_desktop(session_dir_name):
    audit = AI_CONV / 'Anthropic_ClaudeDesktop' / 'data' / session_dir_name / 'audit.jsonl'
    if not audit.exists(): return None
    turns, idx = [], 0
    for line in audit.open():
        try: o = json.loads(line)
        except: continue
        t = o.get('type')
        if t not in ('user', 'assistant'): continue
        msg = o.get('message', {})
        fc = flatten_content(msg.get('content', ''))
        if not (fc['text'] or fc['thinking'] or fc['tool_calls']): continue
        turns.append({
            'index': idx, 'role': msg.get('role', t),
            'timestamp': o.get('_audit_timestamp') or o.get('timestamp'),
            'text': fc['text'], 'thinking': fc['thinking'], 'tool_calls': fc['tool_calls'],
        })
        idx += 1
    return turns, str(audit)


def normalize_claude_code(fname):
    src = AI_CONV / 'Anthropic_ClaudeCode' / 'conversations' / fname
    if not src.exists(): return None
    turns, idx = [], 0
    for line in src.open():
        try: o = json.loads(line)
        except: continue
        t = o.get('type')
        if t not in ('user', 'assistant'): continue
        msg = o.get('message', {})
        fc = flatten_content(msg.get('content', ''))
        if not (fc['text'] or fc['thinking'] or fc['tool_calls']): continue
        turns.append({
            'index': idx, 'role': msg.get('role', t),
            'timestamp': o.get('timestamp'),
            'text': fc['text'], 'thinking': fc['thinking'], 'tool_calls': fc['tool_calls'],
        })
        idx += 1
    return turns, str(src)


def normalize_gemini(fname):
    src = AI_CONV / 'Google_GeminiCLI' / 'conversations' / fname
    if not src.exists(): return None
    d = json.load(src.open())
    turns, idx = [], 0
    for m in d.get('messages', []):
        t = m.get('type')
        if t not in ('user', 'gemini'): continue
        role = 'user' if t == 'user' else 'assistant'
        content = m.get('content', '')
        text_parts = []
        if isinstance(content, str) and content: text_parts.append(content)
        elif isinstance(content, list):
            for blk in content:
                if isinstance(blk, dict) and blk.get('text'): text_parts.append(blk['text'])
        text = '\n'.join(text_parts).strip()
        thoughts = m.get('thoughts', '')
        if isinstance(thoughts, list):
            thoughts = '\n'.join(t.get('text', str(t)) if isinstance(t, dict) else str(t) for t in thoughts)
        thoughts = str(thoughts).strip()
        tool_calls = []
        tc = m.get('toolCalls') or []
        for t_ in tc if isinstance(tc, list) else []:
            if isinstance(t_, dict):
                tool_calls.append({
                    'name': t_.get('name') or t_.get('tool') or t_.get('functionName', '?'),
                    'input': str(t_.get('args') or t_.get('input') or t_.get('arguments', ''))[:500],
                })
        if not (text or thoughts or tool_calls): continue
        turns.append({
            'index': idx, 'role': role, 'timestamp': m.get('timestamp'),
            'text': text, 'thinking': thoughts, 'tool_calls': tool_calls,
            'tokens': m.get('tokens'),
        })
        idx += 1
    return turns, str(src)


def normalize_cline(fname):
    src = AI_CONV / 'Cline' / 'conversations' / fname
    if not src.exists(): return None
    d = json.load(src.open())
    turns, idx = [], 0
    if 'ui_messages' in fname:
        for m in d:
            if not isinstance(m, dict): continue
            text = m.get('text', '') or ''
            typ = m.get('type') or m.get('say') or m.get('ask') or 'msg'
            role = 'user' if typ in ('ask', 'text') else 'assistant'
            if not text.strip(): continue
            turns.append({
                'index': idx, 'role': role, 'timestamp': m.get('ts'),
                'text': text[:5000], 'thinking': '', 'tool_calls': [], 'raw_type': typ,
            })
            idx += 1
    else:
        for m in d:
            if not isinstance(m, dict): continue
            role = m.get('role', '?')
            fc = flatten_content(m.get('content', ''))
            if not fc['text'] and not fc['tool_calls']: continue
            turns.append({
                'index': idx, 'role': role, 'timestamp': None,
                'text': fc['text'][:5000], 'thinking': fc['thinking'], 'tool_calls': fc['tool_calls'],
            })
            idx += 1
    return turns, str(src)


def normalize_antigravity(session_uuid):
    brain = AI_CONV / 'Google_Antigravity' / 'brain' / session_uuid
    if not brain.exists() or not brain.is_dir(): return None
    artifacts = []
    for p in sorted(brain.iterdir()):
        if p.suffix == '.md':
            artifacts.append({'filename': p.name, 'content': p.read_text(errors='replace')[:15000], 'size': p.stat().st_size})
    if not artifacts: return None
    return artifacts, str(brain)


def list_sessions(provider):
    """Return list of (session_id, norm_fn) tuples for a provider."""
    if provider == 'claude_desktop':
        return [(p.name, normalize_claude_desktop) for p in (AI_CONV / 'Anthropic_ClaudeDesktop' / 'data').iterdir()
                if p.is_dir() and (p / 'audit.jsonl').exists()]
    elif provider == 'claude_code':
        files = sorted(glob.glob(str(AI_CONV / 'Anthropic_ClaudeCode' / 'conversations' / '*.jsonl')))
        return [(Path(f).name, normalize_claude_code) for f in files]
    elif provider == 'gemini_cli':
        files = sorted(glob.glob(str(AI_CONV / 'Google_GeminiCLI' / 'conversations' / '*.json')))
        return [(Path(f).name, normalize_gemini) for f in files]
    elif provider == 'cline':
        files = sorted(glob.glob(str(AI_CONV / 'Cline' / 'conversations' / '*.json')))
        return [(Path(f).name, normalize_cline) for f in files]
    elif provider == 'antigravity':
        return [(p.name, normalize_antigravity) for p in (AI_CONV / 'Google_Antigravity' / 'brain').iterdir() if p.is_dir()]
    else:
        raise ValueError(f"unknown provider: {provider}")


def clean_sid(raw_name):
    return raw_name.replace('.jsonl', '').replace('.json', '').replace('local_', '')


def already_done(sid, provider):
    """Check if session was already extracted (pilot or full)."""
    pilot_path = PILOT / 'qwen' / provider / f'{sid}.json'
    full_path = OUT_FULL / provider / f'{sid}.json'
    return pilot_path.exists() or full_path.exists()


def run_session_via_pipeline(sid, provider, normalized_path):
    """Invoke the qwen_pipeline.py on one already-normalized session."""
    # Temporarily symlink in the normalized dir structure the pipeline expects
    target_dir = PILOT / 'normalized' / provider
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f'{sid}.json'
    if not target_path.exists():
        target_path.symlink_to(normalized_path)
    # Run pipeline; it writes to pilot/qwen/<provider>/<sid>.json by convention
    out_dir = OUT_FULL / provider
    out_dir.mkdir(parents=True, exist_ok=True)
    # Piggyback: pipeline writes to pilot/qwen — we move it after
    cmd = ['/home/beast/miniconda3/bin/python', str(ROOT / 'src' / 'qwen_pipeline.py'), sid]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=1800)
    dt = time.time() - t0
    # Pipeline wrote to pilot/qwen/<provider>/<sid>.json; move to full/
    src_pq = PILOT / 'qwen' / provider / f'{sid}.json'
    dst = out_dir / f'{sid}.json'
    if src_pq.exists():
        src_pq.rename(dst)
    return {'sid': sid, 'elapsed_s': dt, 'ok': dst.exists(), 'stdout_tail': r.stdout[-500:] if r.stdout else '', 'stderr_tail': r.stderr[-500:] if r.stderr else ''}


def main():
    if len(sys.argv) < 2:
        print("usage: phase4_scale.py <provider> [max_sessions]"); sys.exit(2)
    provider = sys.argv[1]
    max_n = int(sys.argv[2]) if len(sys.argv) > 2 else None

    NORM_FULL.mkdir(parents=True, exist_ok=True)
    (NORM_FULL / provider).mkdir(exist_ok=True)
    OUT_FULL.mkdir(parents=True, exist_ok=True)
    (OUT_FULL / provider).mkdir(exist_ok=True)
    LOG_FULL.mkdir(parents=True, exist_ok=True)

    sessions = list_sessions(provider)
    # Filter to NOT-yet-done
    pending = []
    for raw_name, norm_fn in sessions:
        sid = clean_sid(raw_name)
        if already_done(sid, provider):
            continue
        pending.append((raw_name, norm_fn, sid))

    if max_n:
        pending = pending[:max_n]

    print(f"[{provider}] {len(pending)} sessions pending (of {len(sessions)} total).")

    # Failure cap: max(50, 10% of pending). Consecutive cap kept at 3 to catch hard stalls.
    total_failure_cap = max(50, len(pending) // 10)
    consecutive_cap = 3
    progress_path = LOG_FULL / f'{provider}.progress.jsonl'
    print(f"[{provider}] total_failure_cap={total_failure_cap}, progress_log={progress_path}")

    def append_progress(rec):
        rec['iso'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with progress_path.open('a') as fh:
            fh.write(json.dumps(rec) + '\n')

    consecutive_failures = 0
    total_failures = 0
    results = []
    for i, (raw_name, norm_fn, sid) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {provider}/{sid}")
        # Normalize
        try:
            result = norm_fn(raw_name if provider != 'antigravity' else sid)
            if result is None:
                print(f"  skip: normalizer returned None")
                append_progress({'sid': sid, 'provider': provider, 'stage': 'normalize', 'status': 'skip_null'})
                continue
            if provider == 'antigravity':
                artifacts, src = result
                norm_obj = {'session_id': sid, 'provider': provider, 'source_path': src, 'input_type': 'artifacts', 'artifacts': artifacts}
            else:
                turns, src = result
                norm_obj = {'session_id': sid, 'provider': provider, 'source_path': src, 'input_type': 'dialog', 'turns': turns}
            norm_path = NORM_FULL / provider / f'{sid}.json'
            norm_path.write_text(json.dumps(norm_obj, indent=2))
        except Exception as e:
            print(f"  ❌ normalization failed: {e}")
            append_progress({'sid': sid, 'provider': provider, 'stage': 'normalize', 'status': 'fail', 'error': str(e)})
            total_failures += 1
            consecutive_failures += 1
            if consecutive_failures >= consecutive_cap:
                print(f"  halting: {consecutive_cap} consecutive failures")
                break
            continue

        # Run pipeline
        try:
            r = run_session_via_pipeline(sid, provider, norm_path)
            results.append(r)
            if r['ok']:
                print(f"  ✅ done in {r['elapsed_s']:.0f}s")
                append_progress({'sid': sid, 'provider': provider, 'stage': 'pipeline', 'status': 'ok', 'elapsed_s': r['elapsed_s']})
                consecutive_failures = 0
            else:
                print(f"  ❌ pipeline failed")
                print(f"  stderr tail: {r['stderr_tail'][-300:]}")
                append_progress({'sid': sid, 'provider': provider, 'stage': 'pipeline', 'status': 'fail', 'elapsed_s': r.get('elapsed_s'), 'stderr_tail': r.get('stderr_tail', '')[-300:]})
                total_failures += 1
                consecutive_failures += 1
        except subprocess.TimeoutExpired:
            print(f"  ⏱ timeout")
            append_progress({'sid': sid, 'provider': provider, 'stage': 'pipeline', 'status': 'timeout'})
            total_failures += 1
            consecutive_failures += 1
        except Exception as e:
            print(f"  ❌ pipeline exception: {e}")
            append_progress({'sid': sid, 'provider': provider, 'stage': 'pipeline', 'status': 'exception', 'error': str(e)})
            total_failures += 1
            consecutive_failures += 1

        if consecutive_failures >= consecutive_cap:
            print(f"  halting: {consecutive_cap} consecutive failures")
            break
        if total_failures >= total_failure_cap:
            print(f"  halting: {total_failure_cap} total failures for this provider")
            break

    # Write summary
    summary = {
        'provider': provider, 'attempted': len(results),
        'succeeded': sum(1 for r in results if r.get('ok')),
        'total_failures': total_failures,
        'finished_at': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    sp = LOG_FULL / f'{provider}.summary.json'
    sp.write_text(json.dumps(summary, indent=2))
    print(f"\n{summary}")


if __name__ == '__main__':
    main()
