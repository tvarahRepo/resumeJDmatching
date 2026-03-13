from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional


class HiringRubricItem(BaseModel):
    name: str
    weight: float = Field(1.0, ge=0.0)
    score_1_to_5: int = Field(3, ge=1, le=5)
    description: str = ""


class MatchingWeights(BaseModel):
    jdAlignment: float = Field(35.0, ge=0.0)
    skillRecency: float = Field(12.0, ge=0.0)
    domain: float = Field(10.0, ge=0.0)
    skillDepth: float = Field(12.0, ge=0.0)
    evidence: float = Field(8.0, ge=0.0)
    leadership: float = Field(5.0, ge=0.0)
    educationPedigree: float = Field(8.0, ge=0.0)
    companyPedigree: float = Field(10.0, ge=0.0)


class MatchingFilter(BaseModel):
    type: str
    label: Optional[str] = None
    value: Optional[Any] = None
    action: str = "flag"
    description: str = ""


class MatchingSkillsConfig(BaseModel):
    mustHave: List[str] = Field(default_factory=list)
    goodToHave: List[str] = Field(default_factory=list)
    domainSpecific: List[str] = Field(default_factory=list)
    skillGroups: Dict[str, List[str]] = Field(default_factory=dict)
    semanticSynonyms: Dict[str, List[str]] = Field(default_factory=dict)


class MatchingThresholds(BaseModel):
    telephonic: int = 70
    backup: int = 50
    reject: int = 35


class EducationRules(BaseModel):
    minimum_degree: str = "bachelors"
    preferred_degrees: List[str] = Field(default_factory=list)
    tier_1_keywords: List[str] = Field(default_factory=list)
    tier_2_keywords: List[str] = Field(default_factory=list)
    tier_3_keywords: List[str] = Field(default_factory=list)


class CompanyRules(BaseModel):
    fortune_500_companies: List[str] = Field(default_factory=list)
    top_mncs: List[str] = Field(default_factory=list)
    strong_startups: List[str] = Field(default_factory=list)


class MatchingConfig(BaseModel):
    weights: MatchingWeights = Field(default_factory=MatchingWeights)
    filters: List[MatchingFilter] = Field(default_factory=list)
    skills: MatchingSkillsConfig = Field(default_factory=MatchingSkillsConfig)
    thresholds: MatchingThresholds = Field(default_factory=MatchingThresholds)
    education_rules: EducationRules = Field(default_factory=EducationRules)
    company_rules: CompanyRules = Field(default_factory=CompanyRules)
    notes: str = ""
    aiGenerated: bool = False


class HiringManagerInputs(BaseModel):
    config: MatchingConfig = Field(default_factory=MatchingConfig)
    rubric: List[HiringRubricItem] = Field(default_factory=list)
    use_config_must_have: bool = False
    notes: str = ""


class SkillMatchDetails(BaseModel):
    matched_mandatory: List[str] = Field(default_factory=list)
    missing_mandatory: List[str] = Field(default_factory=list)
    matched_optional: List[str] = Field(default_factory=list)
    missing_optional: List[str] = Field(default_factory=list)
    matched_config_must_have: List[str] = Field(default_factory=list)
    missing_config_must_have: List[str] = Field(default_factory=list)
    matched_good_to_have: List[str] = Field(default_factory=list)
    bonus_skills: List[str] = Field(default_factory=list)


class MatchFlags(BaseModel):
    auto_reject_reasons: List[str] = Field(default_factory=list)
    warning_flags: List[str] = Field(default_factory=list)


class ClientWeightedBreakdown(BaseModel):
    domain_fit: int = Field(..., ge=0, le=30)
    scale_match: int = Field(..., ge=0, le=30)
    skill_depth: int = Field(..., ge=0, le=30)
    dna_fit: int = Field(..., ge=0, le=30)
    evidence: int = Field(..., ge=0, le=30)
    leadership: int = Field(..., ge=0, le=30)

    domain_fit_reason: str = ""
    scale_match_reason: str = ""
    skill_depth_reason: str = ""
    dna_fit_reason: str = ""
    evidence_reason: str = ""
    leadership_reason: str = ""


class SemanticSkillEvidence(BaseModel):
    matched: bool
    depth: Literal["none", "low", "medium", "high"]
    evidence_sources: List[str] = Field(default_factory=list)
    aliases_matched: List[str] = Field(default_factory=list)
    confidence: int = Field(..., ge=0, le=100)


class TopTiles(BaseModel):
    must_have_coverage: int = Field(..., ge=0, le=100)
    skill_depth: int = Field(..., ge=0, le=100)
    recent_relevance: int = Field(..., ge=0, le=100)
    domain_fit: int = Field(..., ge=0, le=100)
    experience_fit: int = Field(..., ge=0, le=100)
    evidence_strength: int = Field(..., ge=0, le=100)
    education_pedigree: int = Field(..., ge=0, le=100)
    company_pedigree: int = Field(..., ge=0, le=100)


class TileReasons(BaseModel):
    must_have_coverage_reason: str = ""
    skill_depth_reason: str = ""
    recent_relevance_reason: str = ""
    domain_fit_reason: str = ""
    experience_fit_reason: str = ""
    evidence_strength_reason: str = ""
    education_pedigree_reason: str = ""
    company_pedigree_reason: str = ""


class QuickView(BaseModel):
    top_strengths: List[str] = Field(default_factory=list)
    top_gaps: List[str] = Field(default_factory=list)
    screening_questions: List[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    jd_alignment_score: int = Field(..., ge=0, le=100)
    skill_recency_score: int = Field(..., ge=0, le=100)
    domain_score: int = Field(..., ge=0, le=100)
    qualitative_score: int = Field(..., ge=0, le=100)

    experience_gap_years: float = 0.0
    skill_match_details: SkillMatchDetails
    flags: MatchFlags
    client_weighted_breakdown: ClientWeightedBreakdown

    top_tiles: TopTiles
    tile_reasons: TileReasons
    quick_view: QuickView
    semantic_skill_analysis: Dict[str, SemanticSkillEvidence] = Field(default_factory=dict)

    shortlist: bool
    recommendation: Literal["SHORTLIST", "SCREEN", "REJECT"]

    recruiter_summary: str
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)

    debug: Dict[str, Any] = Field(default_factory=dict)