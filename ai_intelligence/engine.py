from __future__ import annotations

import json

from config import get_match_llm

from .models import HiringManagerInputs, MatchResult
from .orchestrator import run_matching_orchestration
from .prompts import MATCH_SYSTEM, MATCH_USER


def generate_screening_questions(
    resume_json: dict,
    jd_json: dict,
    deterministic: dict,
) -> list[dict]:
    """
    Generate up to 10 recruiter-grade first-round screening questions.
    These questions are driven by:
    - JD mandatory/optional skills
    - matched vs missing skills
    - experience gap
    - education pedigree
    - company pedigree
    - project / ownership signals
    """

    questions: list[dict] = []

    skill_details = deterministic.get("skill_match_details", {}) or {}
    debug = deterministic.get("debug", {}) or {}
    quick_view = deterministic.get("quick_view", {}) or {}
    tile_reasons = deterministic.get("tile_reasons", {}) or {}
    top_tiles = deterministic.get("top_tiles", {}) or {}

    matched_mandatory = skill_details.get("matched_mandatory", []) or []
    missing_mandatory = skill_details.get("missing_mandatory", []) or []
    matched_optional = skill_details.get("matched_optional", []) or []
    bonus_skills = skill_details.get("bonus_skills", []) or []

    jd_root = jd_json.get("jd_data", jd_json)
    resume_root = resume_json.get("resume_data", resume_json)

    jd_role = jd_root.get("role_title", "this role")
    jd_min_years = jd_root.get("min_years_experience", 0)
    experience_gap = deterministic.get("experience_gap_years", 0)

    projects = resume_root.get("projects", []) or []
    work_experience = resume_root.get("work_experience_info", []) or []
    education = resume_root.get("education_info", []) or []

    education_score = debug.get("education_pedigree_score", 0)
    company_score = debug.get("company_pedigree_score", 0)

    # 1. Validate strongest matched mandatory skill
    if matched_mandatory:
        skill = matched_mandatory[0]
        questions.append({
            "question": f"You seem to match strongly on {skill}. Can you walk me through one real-world use case where you applied it end-to-end for a role similar to {jd_role}?",
            "intent": "Validate actual depth on a core matched mandatory skill",
            "what_good_answer_looks_like": "Clear business problem, exact technical contribution, decisions taken, challenges faced, and measurable outcome."
        })

    # 2. Validate second strongest skill / optional skill
    if len(matched_mandatory) > 1:
        skill = matched_mandatory[1]
        questions.append({
            "question": f"How recent and hands-on is your work with {skill}, and what level of complexity did you handle?",
            "intent": "Check recency and complexity for another matched core skill",
            "what_good_answer_looks_like": "Recent usage, clear scale/complexity, and evidence beyond just listing the skill."
        })
    elif matched_optional:
        skill = matched_optional[0]
        questions.append({
            "question": f"I noticed exposure to {skill}. In what context did you use it, and was it production-grade or more exploratory?",
            "intent": "Differentiate superficial exposure from real implementation",
            "what_good_answer_looks_like": "Clear distinction between prototype, project, or production usage."
        })

    # 3. Probe missing mandatory skill
    if missing_mandatory:
        skill = missing_mandatory[0]
        questions.append({
            "question": f"{skill} appears important for this role but is not clearly evidenced in your resume. Have you used anything equivalent or adjacent, and how would you ramp up quickly if selected?",
            "intent": "Assess adaptability and adjacent-skill transfer for a gap area",
            "what_good_answer_looks_like": "Honest gap acknowledgement, adjacent experience, and a practical ramp-up plan."
        })

    # 4. Probe second missing mandatory skill if available
    if len(missing_mandatory) > 1:
        skill = missing_mandatory[1]
        questions.append({
            "question": f"Can you help me understand your exposure to {skill} or why it may not appear clearly in your profile?",
            "intent": "Check whether the skill is actually absent or just poorly reflected in the resume",
            "what_good_answer_looks_like": "Specific explanation with examples, not a vague claim."
        })

    # 5. Experience-fit question
    if jd_min_years:
        if experience_gap < 0:
            questions.append({
                "question": f"This role expects around {jd_min_years} years of experience, and your profile appears slightly below that. What makes you confident you can still perform at this level from day one?",
                "intent": "Validate readiness despite an experience gap",
                "what_good_answer_looks_like": "Strong examples of accelerated growth, ownership, complexity handled, and outcomes."
            })
        else:
            questions.append({
                "question": f"You seem to meet the experience baseline for this role. What kinds of responsibilities have you handled that map directly to the expectations of {jd_role}?",
                "intent": "Validate direct role-fit beyond years of experience",
                "what_good_answer_looks_like": "Direct mapping between prior responsibilities and the target JD."
            })

    # 6. Project ownership question
    if projects:
        questions.append({
            "question": "Pick one project from your resume that best represents your fit for this role. What exactly was your contribution, what decisions did you own, and what was the final impact?",
            "intent": "Check ownership, authenticity, and project relevance",
            "what_good_answer_looks_like": "Specific ownership, not team-level vagueness; includes trade-offs and measurable impact."
        })

    # 7. Problem solving / tradeoff question
    questions.append({
        "question": "Tell me about a complex problem you solved recently. How did you structure the problem, what trade-offs did you consider, and what would you improve if you did it again?",
        "intent": "Assess structured thinking, decision quality, and maturity",
        "what_good_answer_looks_like": "Structured problem framing, alternatives considered, trade-offs, and reflective learning."
    })

    # 8. College / fundamentals question
    if education:
        if education_score >= 75:
            questions.append({
                "question": "Your academic background appears strong. Which fundamental concept from your college education do you still apply in your work today, and how?",
                "intent": "Check whether strong academic pedigree translates into practical fundamentals",
                "what_good_answer_looks_like": "Strong concept explanation plus applied real-world usage."
            })
        else:
            questions.append({
                "question": "What core technical or analytical fundamentals do you rely on most in your work today, and how did you build them over time?",
                "intent": "Check fundamentals without over-indexing on college pedigree",
                "what_good_answer_looks_like": "Clear foundational thinking, even if not from a premium institution."
            })

    # 9. Company pedigree / scale question
    if work_experience:
        if company_score >= 75:
            questions.append({
                "question": "You have experience in what appears to be a strong company environment. What scale, quality standards, or decision-making rigor from that environment would you bring into this role?",
                "intent": "Translate company pedigree into role-relevant strength",
                "what_good_answer_looks_like": "Specific scale/process/quality lessons and how they apply here."
            })
        else:
            questions.append({
                "question": "What kind of scale, constraints, or cross-functional complexity have you worked with in your previous companies?",
                "intent": "Understand practical environment exposure regardless of brand pedigree",
                "what_good_answer_looks_like": "Specific operational complexity, scale, and stakeholder context."
            })

    # 10. Role-alignment closing question
    questions.append({
        "question": f"Why do you believe you are a strong fit for {jd_role}, and what part of the role would require the most ramp-up from your side?",
        "intent": "Test self-awareness, motivation, and role alignment",
        "what_good_answer_looks_like": "Clear mapping to the JD, honest self-assessment, and realistic ramp-up awareness."
    })

    # keep only top 10
    return questions[:10]


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

    screening_questions = generate_screening_questions(
        resume_json=resume_json,
        jd_json=jd_json,
        deterministic=deterministic,
    )

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
        "screening_questions": screening_questions,
        "debug": deterministic["debug"],
    }

    return MatchResult(**final).model_dump()