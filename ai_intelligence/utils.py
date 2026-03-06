from __future__ import annotations

import json
from typing import Any


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def safe_load_json(text: str) -> Any:
    """
    Loads JSON from LLM output. Handles accidental code fences.
    """
    t = (text or "").strip()

    # strip markdown fences if present
    if t.startswith("```"):
        # remove the first fence line and last fence line
        lines = t.splitlines()
        # remove first line like ```json
        lines = lines[1:]
        # remove last line ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()

    return json.loads(t)