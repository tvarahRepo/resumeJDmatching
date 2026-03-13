from __future__ import annotations

from datetime import datetime
from typing import Optional, Set

from .helpers import norm_text, unique_norm, parse_ym, months_between


def _resume_root(resume_json: dict) -> dict:
    return resume_json.get("resume_data", resume_json)


def _jd_root(jd_json: dict) -> dict:
    return jd_json.get("jd_data", jd_json)


def extract_resume_skills(resume_json: dict) -> Set[str]:
    resume = _resume_root(resume_json)
    skills_info = resume.get("skills_info", {}) or {}

    buckets = []
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
        values = skills_info.get(key, []) or []
        if isinstance(values, list):
            buckets.extend([v for v in values if isinstance(v, str)])

    for exp in resume.get("work_experience_info", []) or []:
        desc = norm_text((exp.get("role_description") or "") + " " + (exp.get("experience_insights") or ""))
        inferred = []
        for token in [
            "pyspark", "pandas", "numpy", "scipy", "scikit-learn", "jupyter",
            "linux", "aws", "apache spark", "spark", "etl", "eda",
            "machine learning", "statistics", "hypothesis testing",
            "feature engineering", "model monitoring", "docker", "airflow", "mlflow"
        ]:
            if token in desc:
                inferred.append(token)
        buckets.extend(inferred)

    return set(unique_norm(buckets))


def extract_jd_mandatory_skills(jd_json: dict) -> Set[str]:
    jd = _jd_root(jd_json)
    ms = jd.get("mandatory_skills", {}) or {}
    buckets = []
    for key in ["programming_languages", "frameworks_and_libraries", "tools", "databases", "cloud_and_infra"]:
        values = ms.get(key, []) or []
        if isinstance(values, list):
            buckets.extend([v for v in values if isinstance(v, str)])
    return set(unique_norm(buckets))


def extract_jd_optional_skills(jd_json: dict) -> Set[str]:
    jd = _jd_root(jd_json)
    values = jd.get("optional_skills", []) or []
    return set(unique_norm([v for v in values if isinstance(v, str)]))


def estimate_resume_experience_years(resume_json: dict) -> Optional[float]:
    resume = _resume_root(resume_json)
    total_months = 0
    ok = False
    for exp in resume.get("work_experience_info", []) or []:
        start = parse_ym(exp.get("start_date"))
        end = parse_ym(exp.get("end_date")) if exp.get("end_date") else datetime.now()
        if start and end and end >= start:
            total_months += months_between(start, end)
            ok = True
    if not ok:
        return None
    return round(total_months / 12.0, 2)


def most_recent_job_title(resume_json: dict) -> Optional[str]:
    resume = _resume_root(resume_json)
    for exp in resume.get("work_experience_info", []) or []:
        title = exp.get("job_title")
        if title:
            return str(title)
    return None


def extract_resume_education_blob(resume_json: dict) -> str:
    resume = _resume_root(resume_json)
    parts = []
    for edu in resume.get("education_info", []) or []:
        for key in ["degree", "field_of_study", "education_level", "institution_name", "institution_type"]:
            value = edu.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip().lower())
    return " ".join(parts)


def extract_resume_company_blob(resume_json: dict) -> str:
    resume = _resume_root(resume_json)
    parts = []
    for exp in resume.get("work_experience_info", []) or []:
        value = exp.get("company_name")
        if isinstance(value, str) and value.strip():
            parts.append(value.strip().lower())
    return " ".join(parts)


def extract_resume_domain_set(resume_json: dict) -> Set[str]:
    root = _resume_root(resume_json)
    domain_data = resume_json.get("domain_data", {}) or root.get("domain_data", {}) or {}
    values = domain_data.get("overall_candidate_domain", []) or []
    return set(unique_norm([v for v in values if isinstance(v, str)]))