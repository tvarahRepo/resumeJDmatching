from __future__ import annotations

from typing import Dict, List, Set

from .helpers import norm_skill
from .models import SemanticSkillEvidence


def _collect_resume_texts(resume_json: dict) -> List[str]:
    resume = resume_json.get("resume_data", resume_json)
    texts: List[str] = []

    for exp in resume.get("work_experience_info", []) or []:
        for key in ["job_title", "role_description", "experience_insights"]:
            value = exp.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value.lower())

    for proj in resume.get("projects", []) or []:
        if isinstance(proj, dict):
            for value in proj.values():
                if isinstance(value, str) and value.strip():
                    texts.append(value.lower())
                elif isinstance(value, list):
                    texts.extend([str(x).lower() for x in value])

    return texts


def _flatten_resume_skill_list(resume_json: dict) -> Set[str]:
    resume = resume_json.get("resume_data", resume_json)
    si = resume.get("skills_info", {}) or {}

    vals: List[str] = []
    for key in [
        "programming_languages",
        "frameworks_and_libraries",
        "tools_and_platforms",
        "databases",
        "cloud_and_infra",
        "soft_skills",
        "domain_skills",
        "certified_skills",
    ]:
        items = si.get(key, []) or []
        vals.extend([str(x) for x in items])

    return set(norm_skill(x) for x in vals if norm_skill(x))


def build_semantic_skill_analysis(
    resume_json: dict,
    candidate_skills: Set[str],
    target_skills: Set[str],
    synonym_map: Dict[str, List[str]],
) -> Dict[str, SemanticSkillEvidence]:
    texts = _collect_resume_texts(resume_json)
    flat_resume_skills = _flatten_resume_skill_list(resume_json)

    out: Dict[str, SemanticSkillEvidence] = {}

    for raw_skill in sorted(target_skills):
        skill = norm_skill(raw_skill)
        aliases = [norm_skill(a) for a in synonym_map.get(skill, [])]
        all_forms = [skill] + aliases

        matched = False
        evidence_sources: List[str] = []
        aliases_hit: List[str] = []

        if any(form in flat_resume_skills for form in all_forms):
            matched = True
            evidence_sources.append("skills")

        text_hits = 0
        for form in all_forms:
            for t in texts:
                if form and form in t:
                    text_hits += 1
                    matched = True
                    if form != skill:
                        aliases_hit.append(form)

        if text_hits > 0:
            evidence_sources.append("recent_experience")

        if not matched:
            depth = "none"
            confidence = 0
        elif "skills" in evidence_sources and "recent_experience" in evidence_sources and text_hits >= 2:
            depth = "high"
            confidence = 90
        elif matched and (text_hits >= 1 or "skills" in evidence_sources):
            depth = "medium"
            confidence = 70
        else:
            depth = "low"
            confidence = 45

        out[skill] = SemanticSkillEvidence(
            matched=matched,
            depth=depth,
            evidence_sources=list(dict.fromkeys(evidence_sources)),
            aliases_matched=list(dict.fromkeys(aliases_hit)),
            confidence=confidence,
        )

    return out