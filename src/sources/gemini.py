"""Gemini CLI — JSON conversations with structured messages."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Iterator

from . import register
from .base import NormalizedSession, SourceAdapter, coerce_ts

AI_CONV = Path(os.environ.get("OMNIGRAPH_AI_CONV", "/home/beast/ai_conversations"))
SRC_ROOT = AI_CONV / "Google_GeminiCLI" / "conversations"


@register("gemini_cli")
class GeminiAdapter(SourceAdapter):
    name = "gemini_cli"

    def iter_sessions(self) -> Iterator[NormalizedSession]:
        if not SRC_ROOT.exists():
            return
        for src in sorted(SRC_ROOT.glob("*.json")):
            sid = src.stem
            try:
                d = json.load(src.open())
            except Exception:
                continue
            turns: list[dict] = []
            idx = 0
            for m in d.get("messages", []) or []:
                t = m.get("type")
                if t not in ("user", "gemini"):
                    continue
                role = "user" if t == "user" else "assistant"
                content = m.get("content", "")
                text_parts: list[str] = []
                if isinstance(content, str) and content:
                    text_parts.append(content)
                elif isinstance(content, list):
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("text"):
                            text_parts.append(blk["text"])
                text = "\n".join(text_parts).strip()
                thoughts = m.get("thoughts", "")
                if isinstance(thoughts, list):
                    thoughts = "\n".join(
                        tt.get("text", str(tt)) if isinstance(tt, dict) else str(tt)
                        for tt in thoughts
                    )
                thoughts = str(thoughts).strip()
                tool_calls: list[dict] = []
                tc = m.get("toolCalls") or []
                if isinstance(tc, list):
                    for t_ in tc:
                        if not isinstance(t_, dict):
                            continue
                        tool_calls.append({
                            "name": t_.get("name") or t_.get("tool") or t_.get("functionName", "?"),
                            "input": str(t_.get("args") or t_.get("input") or t_.get("arguments", ""))[:500],
                        })
                if not (text or thoughts or tool_calls):
                    continue
                turns.append({
                    "index": idx,
                    "role": role,
                    "timestamp": coerce_ts(m.get("timestamp")),
                    "text": text,
                    "thinking": thoughts,
                    "tool_calls": tool_calls,
                    "tokens": m.get("tokens"),
                })
                idx += 1
            if not turns:
                continue
            yield NormalizedSession(
                session_id=sid,
                provider=self.name,
                source_path=str(src),
                input_type="dialog",
                turns=turns,
            )

    def session_id(self, raw_handle) -> str:
        if isinstance(raw_handle, Path):
            return raw_handle.stem
        return str(raw_handle)
