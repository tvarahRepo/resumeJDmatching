from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, List, Optional


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def norm_skill(s: str) -> str:
    s = norm_text(s)
    replacements = {
        "ipython": "jupyter",
        "jupyter notebook": "jupyter",
        "sklearn": "scikit-learn",
        "scikit learn": "scikit-learn",
        "spark sql": "apache spark",
        "amazon web services": "aws",
        "aws cloud": "aws",
    }
    return replacements.get(s, s)


def unique_norm(items: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        n = norm_skill(item)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def parse_years_from_string(s: str) -> Optional[float]:
    if not s:
        return None
    m = re.search(r"(\d+(\.\d+)?)", s)
    if m:
        return float(m.group(1))
    return None


def parse_ym(s: Optional[str]) -> Optional[datetime]:
    if not s or not isinstance(s, str):
        return None
    s = s.strip().replace("/", "-")
    try:
        return datetime.strptime(s[:7], "%Y-%m")
    except Exception:
        return None


def months_between(start: datetime, end: datetime) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))