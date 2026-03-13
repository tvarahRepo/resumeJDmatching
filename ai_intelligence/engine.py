from __future__ import annotations

import json

from config import get_match_llm

from .models import HiringManagerInputs, MatchResult
from .orchestrator import run_matching_orchestration
from .prompts import MATCH_SYSTEM, MATCH_USER


def generate_match(resume_json: dict, jd_json: dict, hiring_manager_inputs: dict | None = None) -> dict:
    hmi = HiringManagerInputs(**(hiring_manager_inputs or {}))
    deterministic = run_matching_orchestration(resume_json, jd_json, hmi.model_dump())

    llm = get_match_llm()

    prompt = [
        ("system", MATCH_SYSTEM),
        ("human", MATCH_USER.format(
            resume_json=json.dumps(resume_json, ensure_ascii=False, indent=2),
            jd_json=json.dumps(jd_json, ensure_ascii=False, indent=2),
            hmi_json=json.dumps(hmi.model_dump(), ensure_ascii=False, indent=2),
            deterministic_json=json.dumps(deterministic, ensure_ascii=False, indent=2),
        ))
    ]

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        parsed = json.loads(content) if isinstance(content, str) and content.strip().startswith("{") else {
            "recruiter_summary": str(content),
            "strengths": deterministic["quick_view"]["top_strengths"],
            "risks": deterministic["quick_view"]["top_gaps"],
            "rationale": deterministic["quick_view"]["screening_questions"],
        }
    except Exception:
        parsed = {
            "recruiter_summary": "Deterministic semantic analysis returned. LLM explanation fallback applied.",
            "strengths": deterministic["quick_view"]["top_strengths"],
            "risks": deterministic["quick_view"]["top_gaps"],
            "rationale": deterministic["quick_view"]["screening_questions"],
        }

    final = {
        "overall_score": deterministic["overall_score"],
        "jd_alignment_score": deterministic["jd_alignment_score"],
        "skill_recency_score": deterministic["skill_recency_score"],
        "domain_score": deterministic["domain_score"],
        "qualitative_score": deterministic["qualitative_score"],
        "experience_gap_years": deterministic["experience_gap_years"],
        "skill_match_details": deterministic["skill_match_details"],
        "flags": deterministic["flags"],
        "client_weighted_breakdown": deterministic["client_weighted_breakdown"],
        "top_tiles": deterministic["top_tiles"],
        "tile_reasons": deterministic["tile_reasons"],
        "quick_view": deterministic["quick_view"],
        "semantic_skill_analysis": deterministic["semantic_skill_analysis"],
        "shortlist": deterministic["shortlist"],
        "recommendation": deterministic["recommendation"],
        "recruiter_summary": parsed.get("recruiter_summary", "Deterministic semantic analysis returned."),
        "strengths": parsed.get("strengths", deterministic["quick_view"]["top_strengths"]),
        "risks": parsed.get("risks", deterministic["quick_view"]["top_gaps"]),
        "rationale": parsed.get("rationale", deterministic["quick_view"]["screening_questions"]),
        "debug": deterministic["debug"],
    }

    return MatchResult(**final).model_dump()