from __future__ import annotations

from .helpers import norm_skill, norm_text, parse_years_from_string
from .alignment import (
    extract_resume_skills,
    extract_jd_mandatory_skills,
    extract_jd_optional_skills,
    estimate_resume_experience_years,
    extract_resume_education_blob,
    extract_resume_company_blob,
    most_recent_job_title,
    extract_resume_domain_set,
)
from .models import (
    HiringManagerInputs,
    MatchFlags,
    SkillMatchDetails,
    ClientWeightedBreakdown,
    TopTiles,
    TileReasons,
    QuickView,
)
from .semantic import build_semantic_skill_analysis


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
        desc = ((exp.get("role_description") or "") + " " + (exp.get("experience_insights") or "")).lower()
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
            required_domain = norm_text(str(f.value))
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


def score_education_pedigree(resume_json, hmi):
    edu_blob = extract_resume_education_blob(resume_json)
    rules = hmi.config.education_rules

    t1 = [x.lower() for x in rules.tier_1_keywords]
    t2 = [x.lower() for x in rules.tier_2_keywords]
    t3 = [x.lower() for x in rules.tier_3_keywords]

    if any(k in edu_blob for k in t1):
        return 90, "Institution matches Tier-1 keyword set"
    if any(k in edu_blob for k in t2):
        return 75, "Institution matches Tier-2 keyword set"
    if any(k in edu_blob for k in t3):
        return 60, "Institution matches Tier-3 keyword set"
    return 55, "Institution tier not confidently identified"


def score_company_pedigree(resume_json, hmi):
    companies = extract_resume_company_blob(resume_json)
    rules = hmi.config.company_rules

    fortune = [x.lower() for x in rules.fortune_500_companies]
    mncs = [x.lower() for x in rules.top_mncs]
    startups = [x.lower() for x in rules.strong_startups]

    if any(c in companies for c in fortune):
        return 90, "Previous employer matches Fortune 500 / elite company set"
    if any(c in companies for c in mncs):
        return 80, "Previous employer matches strong MNC set"
    if any(c in companies for c in startups):
        return 78, "Previous employer matches strong startup/scale-up set"
    if companies.strip():
        return 60, "Employer identified but not in premium pedigree list"
    return 50, "Company pedigree could not be established"


def apply_filters(resume_json, jd_json, hmi):
    flags = MatchFlags()
    years = estimate_resume_experience_years(resume_json)
    edu_blob = extract_resume_education_blob(resume_json)
    domains = extract_resume_domain_set(resume_json)

    for f in hmi.config.filters:
        action = (f.action or "flag").lower()

        if f.type == "min_experience":
            required = parse_years_from_string(str(f.value or ""))
            if required is not None and (years is None or years < required):
                msg = f"{f.label or 'Minimum experience'} not met: candidate ~{years or 0:.2f} yrs vs required {required:.1f} yrs"
                if action == "auto_reject":
                    flags.auto_reject_reasons.append(msg)
                else:
                    flags.warning_flags.append(msg)

        elif f.type == "min_education":
            req = norm_text(str(f.value or ""))
            if req and req not in edu_blob:
                msg = f"{f.label or 'Minimum education'} not met: required {f.value}"
                if action == "auto_reject":
                    flags.auto_reject_reasons.append(msg)
                else:
                    flags.warning_flags.append(msg)

        elif f.type == "required_domain":
            req = norm_text(str(f.value or ""))
            if req and not any(req in d for d in domains):
                msg = f"{f.label or 'Required domain'} not met: {f.value}"
                if action == "auto_reject":
                    flags.auto_reject_reasons.append(msg)
                else:
                    flags.warning_flags.append(msg)

    return flags


def build_client_weighted_breakdown(resume_json, jd_json, details, hmi, semantic_analysis):
    years = estimate_resume_experience_years(resume_json) or 0.0
    jd_min = jd_json.get("jd_data", jd_json).get("min_years_experience") or 0

    domain_score = 26 if extract_resume_domain_set(resume_json) else 18
    scale_score = 22 if years >= jd_min else 16

    high_depth = sum(1 for v in semantic_analysis.values() if v.depth == "high")
    med_depth = sum(1 for v in semantic_analysis.values() if v.depth == "medium")
    evidence_count = sum(1 for v in semantic_analysis.values() if v.matched)

    skill_depth_score = min(30, 8 + high_depth * 6 + med_depth * 3)
    dna_score = 20 + (4 if hmi.rubric else 0)
    evidence_score = min(30, 12 + evidence_count * 2)
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
        skill_depth_reason=f"{high_depth} high-depth and {med_depth} medium-depth skills evidenced",
        dna_fit_reason="Hiring manager rubric and role profile indicate moderate fit",
        evidence_reason="Evidence derived from explicit skills, recent role descriptions, and semantic aliases",
        leadership_reason="IC-style profile; leadership not strongly evidenced",
    )


def build_top_tiles(details, semantic_analysis, domain_score, skill_recency_score, experience_gap_years, education_pedigree, company_pedigree):
    total_mand = max(1, len(details.matched_mandatory) + len(details.missing_mandatory))
    must_have_coverage = int(round(100 * len(details.matched_mandatory) / total_mand))

    high_depth = sum(1 for v in semantic_analysis.values() if v.depth == "high")
    med_depth = sum(1 for v in semantic_analysis.values() if v.depth == "medium")
    total_semantic = max(1, len(semantic_analysis))
    skill_depth = int(round(min(100, ((high_depth * 1.0 + med_depth * 0.6) / total_semantic) * 100)))

    experience_fit = 100 if experience_gap_years >= 0 else max(20, int(round(100 + experience_gap_years * 20)))
    evidence_strength = int(round(sum(v.confidence for v in semantic_analysis.values()) / max(1, len(semantic_analysis))))

    return TopTiles(
        must_have_coverage=must_have_coverage,
        skill_depth=skill_depth,
        recent_relevance=skill_recency_score,
        domain_fit=domain_score,
        experience_fit=experience_fit,
        evidence_strength=evidence_strength,
        education_pedigree=education_pedigree,
        company_pedigree=company_pedigree,
    )


def build_tile_reasons(details, semantic_analysis, domain_score, skill_recency_score, years, jd_min, education_reason, company_reason):
    total_mand = max(1, len(details.matched_mandatory) + len(details.missing_mandatory))
    high_depth = sum(1 for v in semantic_analysis.values() if v.depth == "high")
    med_depth = sum(1 for v in semantic_analysis.values() if v.depth == "medium")
    avg_conf = int(round(sum(v.confidence for v in semantic_analysis.values()) / max(1, len(semantic_analysis))))

    return TileReasons(
        must_have_coverage_reason=f"Matched {len(details.matched_mandatory)} of {total_mand} mandatory skills",
        skill_depth_reason=f"{high_depth} high-depth and {med_depth} medium-depth skills evidenced",
        recent_relevance_reason=f"Recent experience relevance score derived from role descriptions: {skill_recency_score}%",
        domain_fit_reason=f"Domain fit derived from candidate domain enrichment and filters: {domain_score}%",
        experience_fit_reason=f"{years or 0:.1f} years vs JD baseline {jd_min or 0}",
        evidence_strength_reason=f"Average semantic evidence confidence: {avg_conf}%",
        education_pedigree_reason=education_reason,
        company_pedigree_reason=company_reason,
    )


def build_quick_view(details, flags, experience_gap_years, education_pedigree, company_pedigree):
    strengths = []
    gaps = []
    screening = []

    if details.matched_mandatory:
        strengths.append(f"Matched {len(details.matched_mandatory)} mandatory skills")
    if education_pedigree >= 75:
        strengths.append("College pedigree is a positive signal")
    if company_pedigree >= 75:
        strengths.append("Company pedigree is a positive signal")

    if details.missing_mandatory:
        gaps.append(f"Missing mandatory skills: {', '.join(details.missing_mandatory[:4])}")
    if experience_gap_years < 0:
        gaps.append(f"Experience below baseline by ~{abs(experience_gap_years):.1f} years")
    if flags.warning_flags:
        gaps.extend(flags.warning_flags[:2])

    screening.append("Which missing mandatory skills does the candidate actually have but failed to highlight in the resume?")
    screening.append("How deep and recent is the candidate’s hands-on usage of the critical JD stack?")
    screening.append("What role outcomes can the candidate demonstrate beyond listing tools and technologies?")

    return QuickView(
        top_strengths=strengths[:3],
        top_gaps=gaps[:3],
        screening_questions=screening[:3]
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

    synonym_map = {norm_skill(k): [norm_skill(x) for x in v] for k, v in hmi.config.skills.semanticSynonyms.items()}
    semantic_analysis = build_semantic_skill_analysis(
        resume_json=resume_json,
        candidate_skills=resume_skills,
        target_skills=jd_mand.union(jd_opt).union(config_good),
        synonym_map=synonym_map
    )

    skill_recency_score = score_skill_recency(resume_json, jd_mand.union(config_must if hmi.use_config_must_have else set()))
    domain_score = score_domain(resume_json, hmi)
    qualitative_score = score_qualitative(hmi)
    education_pedigree_score, education_pedigree_reason = score_education_pedigree(resume_json, hmi)
    company_pedigree_score, company_pedigree_reason = score_company_pedigree(resume_json, hmi)

    breakdown = build_client_weighted_breakdown(resume_json, jd_json, details, hmi, semantic_analysis)

    weights = hmi.config.weights
    total_w = (
        weights.jdAlignment
        + weights.skillRecency
        + weights.domain
        + weights.skillDepth
        + weights.evidence
        + weights.leadership
        + weights.educationPedigree
        + weights.companyPedigree
    ) or 100.0

    leadership_norm = min(100, breakdown.leadership * (100 / 30))
    skill_depth_norm = min(100, breakdown.skill_depth * (100 / 30))
    evidence_norm = min(100, breakdown.evidence * (100 / 30))

    quantitative_score = (
        weights.jdAlignment * jd_alignment_score +
        weights.skillRecency * skill_recency_score +
        weights.domain * domain_score +
        weights.skillDepth * skill_depth_norm +
        weights.evidence * evidence_norm +
        weights.leadership * leadership_norm +
        weights.educationPedigree * education_pedigree_score +
        weights.companyPedigree * company_pedigree_score
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

    top_tiles = build_top_tiles(
        details, semantic_analysis, domain_score, skill_recency_score, exp_gap,
        education_pedigree_score, company_pedigree_score
    )
    tile_reasons = build_tile_reasons(
        details, semantic_analysis, domain_score, skill_recency_score, years, jd_min,
        education_pedigree_reason, company_pedigree_reason
    )
    quick_view = build_quick_view(details, flags, exp_gap, education_pedigree_score, company_pedigree_score)

    return {
        "overall_score": overall_score,
        "jd_alignment_score": jd_alignment_score,
        "skill_recency_score": skill_recency_score,
        "domain_score": domain_score,
        "qualitative_score": qualitative_score,
        "experience_gap_years": exp_gap,
        "skill_match_details": details.model_dump(),
        "flags": flags.model_dump(),
        "client_weighted_breakdown": breakdown.model_dump(),
        "top_tiles": top_tiles.model_dump(),
        "tile_reasons": tile_reasons.model_dump(),
        "quick_view": quick_view.model_dump(),
        "semantic_skill_analysis": {k: v.model_dump() for k, v in semantic_analysis.items()},
        "shortlist": shortlist,
        "recommendation": recommendation,
        "debug": {
            "resume_skills": sorted(resume_skills),
            "jd_mandatory": sorted(jd_mand),
            "jd_optional": sorted(jd_opt),
            "resume_years_estimate": years,
            "jd_min_years": jd_min,
            "config_used_for_must_have": hmi.use_config_must_have,
            "education_pedigree_score": education_pedigree_score,
            "company_pedigree_score": company_pedigree_score,
        }
    }