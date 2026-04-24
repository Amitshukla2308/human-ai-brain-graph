# Light-IR — OmniGraph's default prompt-injection format

_Written 2026-04-24 after benchmarking IR vs prose on loaded qwen3.6-35b-a3b._

## What it is (and isn't)

**Light-IR is a prompt-injection output format, not a compilation target.** It's what OmniGraph's compiler emits when the consumer is an LLM prompt (CLAUDE.md, system prompt block, Atelier boot context). Generated from the same JSON source as the human-readable Markdown projection; different target, different shape.

Distinct from Gemini's full "LLM-IR Compiler" thesis (vibe-prompt → local-compiled IR → cloud-execution) — that thesis requires per-task client-side compute (5090-class), which we deliberately park. See `01_READING_THE_GEMINI_CONVERSATION.md` for Gemini's original framing.

Light-IR borrows the **structural-tokens-over-prose principle** from Gemini's thesis without borrowing the runtime requirement. The compiler is deterministic text templating (Python, no local LLM).

## The format

XML-style tags with short attribute names. Universally-parsed by any modern LLM (HTML/JSX/SGML/XMPP training saturation), human-auditable, version-gated.

```xml
<user-profile v="0.2.1">
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
```

### Tag vocabulary (v0.1)

| Tag | Meaning | Attributes |
|---|---|---|
| `<user-profile>` | root wrapper | `v` = schema version |
| `<mm>` | mental-move | `l` = level (axiom / gen / usr), `o` = owner (user / assistant) |
| `<rule>` | standing rule synthesized from drifts/moves | — |
| `<concern>` | latent or recurring concern | `r` = recurrence (recurring / latent), inline `[t_last, n_raised]` |
| `<drift>` | genuine session-drift patterns (used sparingly — high-value only) | `t` = trigger class |
| `<ent-top>` | top-N entities by frequency | `n` = count |
| `<decision-active>` | currently-load-bearing decisions | — |

Version-gated: the `v` attribute on `<user-profile>` lets downstream consumers refuse to parse formats they don't support.

## Empirical validation (benchmark result, 2026-04-24)

Benchmark ran 3 natural-language user prompts × 2 system-prompt conditions (light-IR vs prose) on qwen3.6-35b-a3b, same semantic content, streamed to capture TTFT. Full results: `bench_ir_vs_prose.json` and `bench_ir_vs_prose.txt`.

**System prompt tokens:** IR ≈188 vs Prose ≈431 — **56% savings** on per-session injection cost. Compounds across sessions / tools.

**TTFT-to-first-content-token:** IR wins 2/3 (mcp_retry by 51%, new_project by 12%), Prose wins gut_check by 1s. Mixed on small n but no consistent prose advantage.

**Quality** (manual review of 6 responses):
- Both formats correctly applied the `state-of-reality-audit` mental-move on `gut_check` (identical opening framing).
- Both mirrored user's numbered-directive style in their own output.
- Both avoided suggesting `desktop-commander-read-file` (concern honored).
- Both classified retry errors into transient/permanent categories (rule applied).

**Attention-drift / intent-preservation:** no model drifted toward XML-format output. No model opened with a profile-summary monologue (the concern that motivated the benchmark). Both went straight to answering the user's actual question.

**Surprise:** on `mcp_retry`, the IR condition produced a 75% longer response (3496 vs 2002 chars) with a more complete 7-step checklist. Plausible interpretation: IR freed thinking-budget that the prose system prompt otherwise consumed. Would need more samples to confirm.

## Why not raw JSON compact, or Gemini's operator syntax

**Raw JSON compact** (`{"mm":[{"l":"gen","o":"user","v":"state..."}]}`) — token-efficient, but LLMs attend slightly less well to bare-object structure than to named-tag wrappers. Gap small enough that JSON would also work; XML-tag is marginal upgrade.

**Gemini's operator syntax** (`mut_schema(+col: subscription_tier, ...)`, `[TGT]`, `[ACT]`, `[CST]`) — denser still (~70-80% savings), but:
- Requires LLM familiarity with novel operators; less reliable without few-shot or fine-tuning.
- Designed for per-task compilation, not persistent-profile representation. Different domain.
- Premature when a light-IR already captures most of the benefit with near-zero LLM-adoption risk.

Light-IR is the sweet spot: 50-60% savings, near-100% parse reliability, no novel operator vocabulary, schema-versioned.

## Positioning in the OmniGraph build

Per `04_PROPOSED_BUILD_ORDER.md`:
- **Step 1 (IR contract)** — locks the abstract contract between Vault storage and projections.
- **Step 2 (Meta-Profile projection compiler)** — builds the first compiler. Light-IR is the default target format for LLM-consumer projections. Markdown remains the default for human-audit projections. JSON stays as the canonical storage.

No model-side dependencies. No 5090 required. `jinja2` or plain string templating in Python is sufficient.

## Open for revision

- Tag vocabulary is v0.1 — will evolve as more consumers exercise it. Additions are backward-compatible (unknown tags should be ignored, per spec); removals bump the `v` attribute.
- The concern-inline-bracket format (`[t_last: ..., n_raised: ...]`) is a shortcut we adopted mid-benchmark. Consider promoting those to real attributes (`t_last="..."` `n_raised="..."`) for cleaner parsing — minor cost.
- Empty-corpus behavior: when a user has no confirmed mental_moves yet, light-IR should emit a version-only wrapper rather than hallucinated placeholders.
