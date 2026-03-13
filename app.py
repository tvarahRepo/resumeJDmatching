import json
import streamlit as st

from ai_intelligence.engine import generate_match

st.set_page_config(page_title="Resume ↔ JD Semantic Matcher", layout="wide")
st.title("Resume ↔ JD Semantic Matcher")

st.sidebar.header("Inputs")

resume_file = st.sidebar.file_uploader("Upload Resume JSON", type=["json"])
jd_file = st.sidebar.file_uploader("Upload JD JSON", type=["json"])
config_file = st.sidebar.file_uploader("Upload Matching Config JSON (optional)", type=["json"])

default_match_config = {
    "config": {
        "weights": {
            "jdAlignment": 35,
            "skillRecency": 12,
            "domain": 10,
            "skillDepth": 12,
            "evidence": 8,
            "leadership": 5,
            "educationPedigree": 8,
            "companyPedigree": 10
        },
        "filters": [],
        "skills": {
            "mustHave": [],
            "goodToHave": [],
            "domainSpecific": [],
            "skillGroups": {},
            "semanticSynonyms": {
                "scikit-learn": ["sklearn", "scikit learn"],
                "jupyter": ["jupyter notebook", "ipython"],
                "aws": ["amazon web services", "aws cloud"],
                "apache spark": ["spark", "spark sql"]
            }
        },
        "thresholds": {"telephonic": 70, "backup": 50, "reject": 35},
        "education_rules": {
            "minimum_degree": "bachelors",
            "preferred_degrees": ["computer science", "data science", "statistics", "mathematics", "information technology"],
            "tier_1_keywords": ["iit", "iim", "nit", "iiit", "bits pilani", "tier-1"],
            "tier_2_keywords": ["state university", "tier-2", "reputed private college"],
            "tier_3_keywords": ["tier-3"]
        },
        "company_rules": {
            "fortune_500_companies": ["google", "microsoft", "amazon", "ibm", "accenture"],
            "top_mncs": ["tcs", "infosys", "wipro", "capgemini", "deloitte", "pwc"],
            "strong_startups": ["razorpay", "cred", "meesho", "swiggy", "zomato", "freshworks"]
        },
        "notes": "Default standalone matching config",
        "aiGenerated": False
    },
    "rubric": [
        {"name": "Problem Solving", "weight": 2.0, "score_1_to_5": 4},
        {"name": "Communication", "weight": 1.0, "score_1_to_5": 4},
        {"name": "Ownership", "weight": 1.5, "score_1_to_5": 4}
    ],
    "use_config_must_have": False,
    "notes": "Use JD mandatory skills primarily."
}

run = st.sidebar.button("Run Matching", use_container_width=True)

st.markdown("""
<style>
.tile {
    border: 1px solid #e8e8e8;
    border-radius: 16px;
    padding: 16px;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 10px;
}
.tile-label {
    font-size: 14px;
    color: #666;
    margin-bottom: 8px;
}
.tile-value {
    font-size: 28px;
    font-weight: 700;
    color: #111;
}
.badge {
    padding: 8px 14px;
    border-radius: 999px;
    display: inline-block;
    font-weight: 700;
}
.good { background: #e8f7ee; color: #177245; }
.mid { background: #fff4e5; color: #9a5b00; }
.bad { background: #fdeaea; color: #b42318; }
</style>
""", unsafe_allow_html=True)

def render_tile(label: str, value: str, reason: str):
    st.markdown(
        f"""
        <div class="tile" title="{reason}">
            <div class="tile-label">{label}</div>
            <div class="tile-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if run:
    if not resume_file or not jd_file:
        st.error("Please upload both Resume JSON and JD JSON.")
        st.stop()

    try:
        resume_json = json.load(resume_file)
        jd_json = json.load(jd_file)
    except Exception as e:
        st.error(f"Invalid Resume/JD JSON: {e}")
        st.stop()

    if config_file:
        try:
            hmi = json.load(config_file)
        except Exception:
            config_file.seek(0)
            raw_text = config_file.read().decode("utf-8").strip()
            if not raw_text.startswith("{"):
                raw_text = "{\n" + raw_text + "\n}"
            try:
                hmi = json.loads(raw_text)
                st.warning("Config JSON was auto-wrapped because it was partially formatted.")
            except Exception as e:
                st.warning(f"Invalid config JSON uploaded. Using default config instead. Error: {e}")
                hmi = default_match_config
    else:
        hmi = default_match_config

    with st.spinner("Running semantic matching..."):
        result = generate_match(
            resume_json=resume_json,
            jd_json=jd_json,
            hiring_manager_inputs=hmi
        )

    recommendation = result.get("recommendation", "SCREEN")
    cls = "good" if recommendation == "SHORTLIST" else "mid" if recommendation == "SCREEN" else "bad"
    st.markdown(f'<div class="badge {cls}">{recommendation}</div>', unsafe_allow_html=True)

    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Score", f'{result["overall_score"]}%')
    c2.metric("Recommendation", result["recommendation"])
    c3.metric("Shortlist", str(result["shortlist"]))

    st.subheader("Top Recruiter Tiles")
    tiles = result["top_tiles"]
    reasons = result["tile_reasons"]

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        render_tile("Must Have Coverage", f'{tiles["must_have_coverage"]}%', reasons["must_have_coverage_reason"])
        render_tile("Domain Fit", f'{tiles["domain_fit"]}%', reasons["domain_fit_reason"])
    with r2:
        render_tile("Skill Depth", f'{tiles["skill_depth"]}%', reasons["skill_depth_reason"])
        render_tile("Experience Fit", f'{tiles["experience_fit"]}%', reasons["experience_fit_reason"])
    with r3:
        render_tile("Recent Relevance", f'{tiles["recent_relevance"]}%', reasons["recent_relevance_reason"])
        render_tile("Evidence Strength", f'{tiles["evidence_strength"]}%', reasons["evidence_strength_reason"])
    with r4:
        render_tile("Education Pedigree", f'{tiles["education_pedigree"]}%', reasons["education_pedigree_reason"])
        render_tile("Company Pedigree", f'{tiles["company_pedigree"]}%', reasons["company_pedigree_reason"])

    st.subheader("Recruiter Summary")
    st.info(result["recruiter_summary"])

    q1, q2 = st.columns(2)

    with q1:
        st.subheader("Top Strengths")
        for item in result["quick_view"]["top_strengths"]:
            st.success(item)
        st.subheader("Top Gaps")
        for item in result["quick_view"]["top_gaps"]:
            st.error(item)

    with q2:
        st.subheader("Screening Questions")
        for item in result["quick_view"]["screening_questions"]:
            st.info(item)

    st.subheader("Skill Match Details")
    s1, s2 = st.columns(2)
    details = result["skill_match_details"]
    flags = result["flags"]

    with s1:
        st.write("**Matched Mandatory**", details["matched_mandatory"])
        st.write("**Missing Mandatory**", details["missing_mandatory"])
        st.write("**Matched Optional**", details["matched_optional"])
        st.write("**Matched Good-to-Have**", details["matched_good_to_have"])

    with s2:
        st.write("**Bonus Skills**", details["bonus_skills"])
        st.write("**Warning Flags**", flags["warning_flags"])
        st.write("**Auto Reject Reasons**", flags["auto_reject_reasons"])
        st.write("**Experience Gap (Years)**", result["experience_gap_years"])

    st.subheader("Client Weighted Breakdown")
    cbd = result["client_weighted_breakdown"]
    for label, score_key, reason_key in [
        ("Domain Fit", "domain_fit", "domain_fit_reason"),
        ("Scale Match", "scale_match", "scale_match_reason"),
        ("Skill Depth", "skill_depth", "skill_depth_reason"),
        ("DNA Fit", "dna_fit", "dna_fit_reason"),
        ("Evidence", "evidence", "evidence_reason"),
        ("Leadership", "leadership", "leadership_reason"),
    ]:
        st.write(f"**{label}** — {cbd.get(score_key, 0)}/30 | {cbd.get(reason_key, '')}")

    st.subheader("Semantic Skill Analysis")
    st.json(result["semantic_skill_analysis"])

    with st.expander("Full Output JSON"):
        st.json(result)