#!/usr/bin/env python3
"""Benchmark: natural-language user + prose system vs natural-language user + IR system.
Measures TTFT (reasoning + content), total time, tokens in/out, and captures output
for manual quality + intent-understanding review.

Single loaded model: qwen/qwen3.6-35b-a3b (DO NOT SWAP).
Streaming API to get accurate TTFT measurements.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://192.168.88.2:1234/v1"
MODEL = "qwen/qwen3.6-35b-a3b"
OUT = Path("/home/beast/projects/omnigraph/bench_ir_vs_prose.json")

# ----------------------------------------------------------------------
# System prompts — same semantic content, different format
# ----------------------------------------------------------------------

IR_SYS = """<user-profile v="0.2.1">
<mm l="gen" o="user">state-of-reality-audit-before-planning</mm>
<mm l="gen" o="user">hypothesis→test→pivot cycle</mm>
<mm l="usr" o="user">numbered-directive style on deterministic tasks</mm>
<rule>generalist-retrieval fails → pivot to domain MCP tool</rule>
<rule>local-inference unlimited → use self-consistency voting (N=3-5)</rule>
<concern r="recurring">desktop-commander-read-file [t_last: 2026-04-08, n_raised: 3]</concern>
<concern r="latent">wsl-instability [n_raised: 1]</concern>
<ent-top n="5">
  fastbrick:Proj atelier:Proj zeroclaw:Tool carlsbert:Proj kimi:Tool
</ent-top>
</user-profile>

You are a collaboration partner for this user. Use the profile above to calibrate your response style and recommendations."""

PROSE_SYS = """You are a collaboration partner for this user. The following profile describes how they work, based on extracted patterns across 208+ prior AI sessions. Use it to calibrate your response style and recommendations.

Mental moves observed as load-bearing (generalizable patterns):
1. State-of-reality audit before planning — the user always checks what actually exists before proposing changes. Start by surfacing current state first.
2. Hypothesis → test → pivot cycle — when something doesn't work, the user explicitly forms a new hypothesis, tests it, and pivots if needed rather than retrying the same approach.
3. Numbered-directive style (user-specific) — on deterministic tasks, the user prefers precise numbered multi-step instructions with explicit reporting clauses at the end.

Standing rules the user has established:
- When a generalist retrieval approach (generic agent, non-specific tool) fails on structured data, pivot to domain-specific MCP tools rather than retrying the same approach.
- Because local inference has effectively unlimited budget, use self-consistency voting (N=3-5 samples, majority vote) for hard classifications rather than single-shot extraction.

Known concerns the user has raised:
- desktop-commander-read-file is a recurring concern (last mentioned 2026-04-08, raised 3 separate times) — the tool sometimes returns metadata but empty content body. Do not assume file-reading via this tool will work; suggest alternatives.
- WSL instability was flagged once as a latent concern — infrastructure may crash under memory pressure.

Top entities in the user's world, ranked by mention frequency:
- fastbrick (project)
- atelier (project)
- zeroclaw (tool)
- carlsbert (project)
- kimi (tool)"""

# ----------------------------------------------------------------------
# User prompts — natural language, each probing a different profile axis
# ----------------------------------------------------------------------

PROMPTS = [
    ("new_project", "I want to start a new side project — a Telegram bot that helps track personal expenses. How do we kick this off?"),
    ("mcp_retry", "Having trouble getting one of my MCP tools to retry properly when it fails. What's the pattern I should follow?"),
    ("gut_check", "Quick gut-check: should I refactor the whole thing or just ship what I have?"),
]


def run_streaming(system: str, user: str, max_tokens: int = 4096) -> dict:
    """One call with streaming to capture TTFT for reasoning + content separately."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": True,
    }

    t0 = time.time()
    ttft_reasoning = None
    ttft_content = None
    reasoning_chunks = []
    content_chunks = []
    final_usage = None

    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=600) as r:
        for raw_line in r:
            line = raw_line.decode(errors="replace").strip()
            if not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                break
            try:
                chunk = json.loads(body)
            except Exception:
                continue
            if chunk.get("choices"):
                delta = chunk["choices"][0].get("delta", {}) or {}
                reasoning = delta.get("reasoning_content") or ""
                content = delta.get("content") or ""
                if reasoning and ttft_reasoning is None:
                    ttft_reasoning = round(time.time() - t0, 3)
                if content and ttft_content is None:
                    ttft_content = round(time.time() - t0, 3)
                if reasoning:
                    reasoning_chunks.append(reasoning)
                if content:
                    content_chunks.append(content)
            if chunk.get("usage"):
                final_usage = chunk["usage"]

    total_time = round(time.time() - t0, 3)
    full_content = "".join(content_chunks)
    full_reasoning = "".join(reasoning_chunks)
    return {
        "ttft_reasoning_s": ttft_reasoning,
        "ttft_content_s": ttft_content,
        "total_time_s": total_time,
        "usage": final_usage,
        "content": full_content,
        "reasoning": full_reasoning,
    }


def estimate_prompt_tokens(text: str) -> int:
    """Rough estimate — LM Studio will return the real number in usage."""
    return max(1, len(text) // 4)


def main():
    results = []
    # Order: interleave IR and prose for each prompt (same-prompt comparison closer in time)
    for pid, user in PROMPTS:
        for cond_name, sys_prompt in [("ir", IR_SYS), ("prose", PROSE_SYS)]:
            print(f"\n[{pid}] condition={cond_name}  sys_est_tokens≈{estimate_prompt_tokens(sys_prompt)}", flush=True)
            try:
                r = run_streaming(sys_prompt, user)
                r.update({"prompt_id": pid, "condition": cond_name,
                          "sys_est_tokens": estimate_prompt_tokens(sys_prompt),
                          "user_prompt": user})
                print(f"  ttft_reasoning={r['ttft_reasoning_s']}s  ttft_content={r['ttft_content_s']}s  total={r['total_time_s']}s")
                print(f"  usage={r.get('usage')}")
                print(f"  content_head: {r['content'][:200]}")
                results.append(r)
                OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"  FAILED: {e}")
                results.append({"prompt_id": pid, "condition": cond_name, "error": str(e)})
                OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    print(f"\nResults: {OUT}")


if __name__ == "__main__":
    main()
