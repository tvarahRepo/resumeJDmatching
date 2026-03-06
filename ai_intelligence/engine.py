from __future__ import annotations

import json

from src.config import get_match_llm

from .models import HiringManagerInputs, MatchResult
from .scoring import compute_match
from .prompts import MATCH_SYSTEM, MATCH_USER


def generate_match(resume_json: dict, jd_json: dict, hiring_manager_inputs: dict | None = None) -> dict:
    hmi = HiringManagerInputs(**(hiring_manager_inputs or {}))
    deterministic = compute_match(resume_json, jd_json, hmi)

    llm = get_match_llm()

    prompt = [
        ("system", MATCH_SYSTEM),
        ("human", MATCH_USER.format(
            resume_json=json.dumps(resume_json, ensure_ascii=False, indent=2),
            jd_json=json.dumps(jd_json, ensure_ascii=False, indent=2),
            hmi_json=json.dumps(hmi.model_dump(), ensure_ascii=False, indent=2),
            deterministic_json=json.dumps({
                "overall_score": deterministic["overall_score"],
                "jd_alignment_score": deterministic["jd_alignment_score"],
                "skill_recency_score": deterministic["skill_recency_score"],
                "domain_score": deterministic["domain_score"],
                "qualitative_score": deterministic["qualitative_score"],
                "experience_gap_years": deterministic["experience_gap_years"],
                "skill_match_details": deterministic["skill_match_details"].model_dump(),
                "flags": deterministic["flags"].model_dump(),
                "client_weighted_breakdown": deterministic["client_weighted_breakdown"].model_dump(),
                "recommendation": deterministic["recommendation"],
                "shortlist": deterministic["shortlist"],
                "debug": deterministic["debug"],
            }, ensure_ascii=False, indent=2),
        ))
    ]

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        parsed = json.loads(content) if isinstance(content, str) and content.strip().startswith("{") else {
            "recruiter_summary": str(content),
            "strengths": [],
            "risks": [],
            "rationale": [],
        }
    except Exception as e:
        parsed = {
            "recruiter_summary": "LLM reasoning could not be generated cleanly; returning deterministic analysis.",
            "strengths": [],
            "risks": [str(e)],
            "rationale": [],
        }

    final = {
        "overall_score": deterministic["overall_score"],
        "jd_alignment_score": deterministic["jd_alignment_score"],
        "skill_recency_score": deterministic["skill_recency_score"],
        "domain_score": deterministic["domain_score"],
        "qualitative_score": deterministic["qualitative_score"],
        "experience_gap_years": deterministic["experience_gap_years"],
        "skill_match_details": deterministic["skill_match_details"].model_dump(),
        "flags": deterministic["flags"].model_dump(),
        "client_weighted_breakdown": deterministic["client_weighted_breakdown"].model_dump(),
        "shortlist": deterministic["shortlist"],
        "recommendation": deterministic["recommendation"],
        "recruiter_summary": parsed.get("recruiter_summary", "Deterministic analysis returned."),
        "strengths": parsed.get("strengths", []),
        "risks": parsed.get("risks", []),
        "rationale": parsed.get("rationale", []),
        "debug": deterministic["debug"],
    }

    return MatchResult(**final).model_dump()