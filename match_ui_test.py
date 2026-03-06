import streamlit as st
import json

from ai_intelligence.engine import generate_match

st.set_page_config(page_title="Resume JD Matching", layout="wide")

st.title("AI Resume ↔ JD Matching")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Resume JSON")

    resume_text = st.text_area(
        "Paste Resume JSON",
        height=300
    )

with col2:
    st.subheader("JD JSON")

    jd_text = st.text_area(
        "Paste JD JSON",
        height=300
    )

st.divider()

if st.button("Run Matching"):

    if not resume_text or not jd_text:
        st.error("Please paste both Resume JSON and JD JSON")
        st.stop()

    resume_json = json.loads(resume_text)
    jd_json = json.loads(jd_text)

    result = generate_match(resume_json, jd_json)

    st.success("Matching Complete")

    st.divider()

    score = result["overall_score"]

    st.metric("Overall Match Score", f"{score}%")

    st.subheader("Score Breakdown")

    cols = st.columns(3)

    cols[0].metric("Skills", result["skills_score"])
    cols[1].metric("Experience", result["experience_score"])
    cols[2].metric("Education", result["education_score"])

    st.divider()

    st.subheader("Skill Match")

    skills = result["skill_match_details"]

    colA, colB = st.columns(2)

    with colA:

        st.markdown("### ✅ Matched Mandatory Skills")

        for s in skills["matched_mandatory"]:
            st.success(s)

        st.markdown("### ❌ Missing Mandatory Skills")

        for s in skills["missing_mandatory"]:
            st.error(s)

    with colB:

        st.markdown("### ⭐ Optional Skills Found")

        for s in skills["matched_optional"]:
            st.info(s)

        st.markdown("### 💡 Extra Candidate Skills")

        for s in skills["bonus_skills"]:
            st.write(s)

    st.divider()

    st.subheader("Recruiter Recommendation")

    st.write(result["recruiter_recommendation"])

    if result["shortlist"]:
        st.success("Candidate should be SHORTLISTED")
    else:
        st.error("Candidate should NOT be shortlisted")