"""Base SourceAdapter contract.

A SourceAdapter is responsible for:
  1. Enumerating raw sessions in a provider's dump directory.
  2. Normalizing each raw session into a canonical `NormalizedSession` dict.
  3. Reporting staleness (is this session already extracted?).

Adapters DO NOT call the extractor. They only produce the shape the
extractor expects to read off disk.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional


@dataclass
class NormalizedSession:
    """Canonical shape shared by all adapters.

    Output matches what `qwen_pipeline.run_session` expects when reading
    `<indir>/<provider>/<session_id>.json`. The extractor does NOT care
    which adapter produced it.
    """
    session_id: str
    provider: str
    source_path: str
    input_type: str = "dialog"          # or "artifacts"
    turns: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)
    # Optional per-source metadata.
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        out: dict[str, Any] = {
            "session_id": self.session_id,
            "provider": self.provider,
            "source_path": self.source_path,
            "input_type": self.input_type,
        }
        if self.input_type == "dialog":
            out["turns"] = self.turns
        elif self.input_type == "artifacts":
            out["artifacts"] = self.artifacts
        if self.meta:
            out["meta"] = self.meta
        return out


class SourceAdapter:
    """Concrete adapters subclass this."""

    name: str = "base"

    # ---- enumerate ----
    def iter_sessions(self) -> Iterator[NormalizedSession]:
        """Yield every session available from this source."""
        raise NotImplementedError

    # ---- identify ----
    def session_id(self, raw_handle: Any) -> str:
        """Return a stable session_id for a raw session handle."""
        raise NotImplementedError

    # ---- staleness ----
    def is_session_stale(self, sid: str, extracted_dir: Path) -> bool:
        """True if an extraction already exists for this sid under extracted_dir.

        Default: look for `<extracted_dir>/<provider>/<sid>.json`.
        """
        p = Path(extracted_dir) / self.name / f"{sid}.json"
        return p.exists()


# ----------------------------------------------------------------------
# Shared content-flattening helpers (used by multiple providers)
# ----------------------------------------------------------------------

import re

# Fenced code block pattern (```[lang]\n...```), non-greedy.
_FENCE_RE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)


def shrink_code_blocks(text: str, max_lines: int = 10, keep_fence: bool = True) -> str:
    """Compress long triple-backtick code blocks to a short preview.

    Mitigates the Gemini-flagged failure mode: cloud-agent conversations embed
    large code blocks that waste extraction-prompt budget without carrying
    the conceptual content we care about.
    """
    if not isinstance(text, str) or "```" not in text:
        return text or ""

    def _shrink(m: "re.Match") -> str:
        lang = (m.group(1) or "").strip()
        body = m.group(2) or ""
        lines = body.splitlines()
        if len(lines) <= max_lines:
            return m.group(0)
        head = "\n".join(lines[: max_lines // 2])
        tail = "\n".join(lines[-max_lines // 2:])
        omitted = len(lines) - max_lines
        preview = f"{head}\n… [{omitted} lines elided] …\n{tail}"
        if keep_fence:
            return f"```{lang}\n{preview}\n```"
        return f"[code:{lang or '?'} {len(lines)}L elided]"

    return _FENCE_RE.sub(_shrink, text)


def flatten_content(c: Any, shrink_code: bool = True) -> dict:
    """Flatten Anthropic-style content blocks into text / thinking / tool_calls.

    By default, long fenced code blocks are compressed (see shrink_code_blocks).
    Pass shrink_code=False to preserve raw content when verbatim bodies matter.
    """
    if isinstance(c, str):
        text = shrink_code_blocks(c) if shrink_code else c
        return {"text": text, "thinking": "", "tool_calls": []}
    text_parts: list[str] = []
    thinking_parts: list[str] = []
    tool_calls: list[dict] = []
    if isinstance(c, list):
        for block in c:
            if not isinstance(block, dict):
                continue
            t = block.get("type")
            if t == "text":
                raw = block.get("text", "")
                text_parts.append(shrink_code_blocks(raw) if shrink_code else raw)
            elif t == "thinking":
                raw = block.get("thinking", block.get("text", ""))
                thinking_parts.append(shrink_code_blocks(raw) if shrink_code else raw)
            elif t == "tool_use":
                tool_calls.append({
                    "name": block.get("name"),
                    "input": str(block.get("input", ""))[:500],
                })
            elif t == "tool_result":
                uid = (block.get("tool_use_id") or "?")[:8]
                tool_calls_txt = str(block.get("content", ""))[:400]
                text_parts.append(f"[tool_result:{uid}] {tool_calls_txt}")
    return {
        "text": "\n".join(text_parts).strip(),
        "thinking": "\n".join(thinking_parts).strip(),
        "tool_calls": tool_calls,
    }


def coerce_ts(ts: Any) -> Optional[str]:
    """Best-effort: return ISO-like string or None.

    Handles epoch-ms ints (cline), ISO strings, or None.
    """
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        try:
            import datetime as _dt
            # Heuristic: >1e12 is ms-epoch
            if ts > 1e12:
                return _dt.datetime.utcfromtimestamp(ts / 1000).isoformat() + "Z"
            return _dt.datetime.utcfromtimestamp(ts).isoformat() + "Z"
        except Exception:
            return str(ts)
    if isinstance(ts, str):
        return ts
    return str(ts)
