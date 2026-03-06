from __future__ import annotations

from .helpers import norm_skill, norm_text, parse_years_from_string
from .alignment import (
    extract_resume_skills,
    extract_jd_mandatory_skills,
    extract_jd_optional_skills,
    estimate_resume_experience_years,
    extract_resume_education_blob,
    most_recent_job_title,
    extract_resume_domain_set,
)
from .models import HiringManagerInputs, MatchFlags, SkillMatchDetails, ClientWeightedBreakdown


def score_jd_alignment(resume_skills, jd_mand, jd_opt):
    matched_m = sorted(jd_mand.intersection(resume_skills))
    missing_m = sorted(jd_mand.difference(resume_skills))
    matched_o = sorted(jd_opt.intersection(resume_skills))
    missing_o = sorted(jd_opt.difference(resume_skills))
    bonus = sorted(resume_skills.difference(jd_mand.union(jd_opt)))

    mand_cov = len(matched_m) / max(1, len(jd_mand)) if jd_mand else 0.6
    opt_cov = len(matched_o) / max(1, len(jd_opt)) if jd_opt else 0.5
    bonus_component = min(1.0, len(bonus) / 20.0)

    score = int(round(100 * (0.75 * mand_cov + 0.15 * opt_cov + 0.10 * bonus_component)))

    return score, SkillMatchDetails(
        matched_mandatory=matched_m,
        missing_mandatory=missing_m,
        matched_optional=matched_o,
        missing_optional=missing_o,
        bonus_skills=bonus[:80],
    )


def score_skill_recency(resume_json, required_skills):
    resume = resume_json.get("resume_data", resume_json)
    exps = resume.get("work_experience_info", []) or []
    if not exps or not required_skills:
        return 50

    weighted_hits = 0.0
    weighted_total = float(len(required_skills))

    for idx, exp in enumerate(exps):
        desc = ((exp.get("role_description") or "")).lower()
        weight = 1.0 if idx == 0 else 0.6 if idx == 1 else 0.3
        for skill in required_skills:
            if skill in desc:
                weighted_hits += weight

    score = int(round(min(100.0, 100.0 * weighted_hits / max(1.0, weighted_total))))
    return max(20, score)


def score_domain(resume_json, hmi):
    domains = extract_resume_domain_set(resume_json)
    if not domains:
        return 50

    required_domain = None
    for f in hmi.config.filters:
        if f.type == "required_domain" and f.value:
            required_domain = norm_text(f.value)
            break

    if not required_domain:
        return 60

    if any(required_domain in d for d in domains):
        return 85
    return 35


def score_qualitative(hmi):
    if not hmi.rubric:
        return 50
    total_w = sum(x.weight for x in hmi.rubric) or 1.0
    score = 0.0
    for item in hmi.rubric:
        unit = (item.score_1_to_5 - 1) / 4.0
        score += item.weight * unit * 100.0
    return int(round(score / total_w))


def apply_filters(resume_json, jd_json, hmi):
    flags = MatchFlags()
    years = estimate_resume_experience_years(resume_json)
    edu_blob = extract_resume_education_blob(resume_json)
    domains = extract_resume_domain_set(resume_json)

    for f in hmi.config.filters:
        action = (f.action or "flag").lower()

        if f.type == "min_experience":
            required = parse_years_from_string(f.value or "")
            if required is not None and (years is None or years < required):
                msg = f"{f.label or 'Minimum experience'} not met: candidate ~{years or 0:.2f} yrs vs required {required:.1f} yrs"
                if action == "auto_reject":
                    flags.auto_reject_reasons.append(msg)
                else:
                    flags.warning_flags.append(msg)

        elif f.type == "min_education":
            req = norm_text(f.value or "")
            if req and req not in edu_blob:
                msg = f"{f.label or 'Minimum education'} not met: required {f.value}"
                if action == "auto_reject":
                    flags.auto_reject_reasons.append(msg)
                else:
                    flags.warning_flags.append(msg)

        elif f.type == "required_domain":
            req = norm_text(f.value or "")
            if req and not any(req in d for d in domains):
                msg = f"{f.label or 'Required domain'} not met: {f.value}"
                if action == "auto_reject":
                    flags.auto_reject_reasons.append(msg)
                else:
                    flags.warning_flags.append(msg)

    return flags


def build_client_weighted_breakdown(resume_json, jd_json, details, hmi):
    years = estimate_resume_experience_years(resume_json) or 0.0
    jd_min = jd_json.get("jd_data", jd_json).get("min_years_experience") or 0

    domain_score = 26 if extract_resume_domain_set(resume_json) else 18
    scale_score = 22 if years >= jd_min else 16
    skill_depth_score = min(30, max(8, 8 + 6 * len(details.matched_mandatory)))
    dna_score = 20 + (4 if hmi.rubric else 0)
    evidence_score = min(30, 14 + 2 * len(details.matched_mandatory) + min(6, len(details.bonus_skills)))
    leadership_score = 8 if "lead" not in (most_recent_job_title(resume_json) or "").lower() else 20

    return ClientWeightedBreakdown(
        domain_fit=domain_score,
        scale_match=scale_score,
        skill_depth=skill_depth_score,
        dna_fit=dna_score,
        evidence=evidence_score,
        leadership=leadership_score,

        domain_fit_reason="Resume domain enrichment aligns with target domain" if domain_score >= 22 else "Domain alignment is partial",
        scale_match_reason=f"{years:.1f} years vs JD baseline {jd_min}",
        skill_depth_reason=f"{len(details.matched_mandatory)}/{max(1, len(details.matched_mandatory)+len(details.missing_mandatory))} must-haves evidenced",
        dna_fit_reason="Hiring manager rubric and role profile indicate moderate fit",
        evidence_reason="Evidence derived from explicit skills + role descriptions",
        leadership_reason="IC-style profile; leadership not strongly evidenced",
    )


def compute_match(resume_json, jd_json, hmi):
    resume_skills = extract_resume_skills(resume_json)
    jd_mand = extract_jd_mandatory_skills(jd_json)
    jd_opt = extract_jd_optional_skills(jd_json)

    jd_alignment_score, details = score_jd_alignment(resume_skills, jd_mand, jd_opt)

    config_must = set(norm_skill(x) for x in hmi.config.skills.mustHave)
    config_good = set(norm_skill(x) for x in hmi.config.skills.goodToHave)

    if hmi.use_config_must_have:
        details.matched_config_must_have = sorted(config_must.intersection(resume_skills))
        details.missing_config_must_have = sorted(config_must.difference(resume_skills))
    else:
        details.matched_config_must_have = []
        details.missing_config_must_have = []

    details.matched_good_to_have = sorted(config_good.intersection(resume_skills))

    skill_recency_score = score_skill_recency(resume_json, jd_mand.union(config_must if hmi.use_config_must_have else set()))
    domain_score = score_domain(resume_json, hmi)
    qualitative_score = score_qualitative(hmi)

    weights = hmi.config.weights
    total_w = (weights.jdAlignment + weights.skillRecency + weights.domain) or 100.0
    quantitative_score = (
        weights.jdAlignment * jd_alignment_score +
        weights.skillRecency * skill_recency_score +
        weights.domain * domain_score
    ) / total_w

    overall_score = int(round(0.85 * quantitative_score + 0.15 * qualitative_score))

    years = estimate_resume_experience_years(resume_json)
    jd_min = jd_json.get("jd_data", jd_json).get("min_years_experience")
    exp_gap = 0.0
    if years is not None and isinstance(jd_min, int):
        exp_gap = round(years - jd_min, 2)

    flags = apply_filters(resume_json, jd_json, hmi)

    thresholds = hmi.config.thresholds
    if flags.auto_reject_reasons:
        recommendation = "REJECT"
        shortlist = False
    elif overall_score >= thresholds.telephonic:
        recommendation = "SHORTLIST"
        shortlist = True
    elif overall_score >= thresholds.backup:
        recommendation = "SCREEN"
        shortlist = False
    else:
        recommendation = "REJECT"
        shortlist = False

    breakdown = build_client_weighted_breakdown(resume_json, jd_json, details, hmi)

    return {
        "overall_score": overall_score,
        "jd_alignment_score": jd_alignment_score,
        "skill_recency_score": skill_recency_score,
        "domain_score": domain_score,
        "qualitative_score": qualitative_score,
        "experience_gap_years": exp_gap,
        "skill_match_details": details,
        "flags": flags,
        "client_weighted_breakdown": breakdown,
        "shortlist": shortlist,
        "recommendation": recommendation,
        "debug": {
            "resume_skills": sorted(resume_skills),
            "jd_mandatory": sorted(jd_mand),
            "jd_optional": sorted(jd_opt),
            "resume_years_estimate": years,
            "jd_min_years": jd_min,
            "config_used_for_must_have": hmi.use_config_must_have,
        }
    }