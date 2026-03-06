from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional


class HiringRubricItem(BaseModel):
    name: str
    weight: float = Field(1.0, ge=0.0)
    score_1_to_5: int = Field(3, ge=1, le=5)


class MatchingWeights(BaseModel):
    jdAlignment: float = Field(60.0, ge=0.0)
    skillRecency: float = Field(25.0, ge=0.0)
    domain: float = Field(15.0, ge=0.0)


class MatchingFilter(BaseModel):
    type: str
    label: Optional[str] = None
    value: Optional[str] = None
    action: str = "flag"


class MatchingSkillsConfig(BaseModel):
    mustHave: List[str] = Field(default_factory=list)
    goodToHave: List[str] = Field(default_factory=list)


class MatchingThresholds(BaseModel):
    telephonic: int = 65
    backup: int = 45
    reject: int = 30


class MatchingConfig(BaseModel):
    weights: MatchingWeights = Field(default_factory=MatchingWeights)
    filters: List[MatchingFilter] = Field(default_factory=list)
    skills: MatchingSkillsConfig = Field(default_factory=MatchingSkillsConfig)
    thresholds: MatchingThresholds = Field(default_factory=MatchingThresholds)
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

    shortlist: bool
    recommendation: Literal["SHORTLIST", "SCREEN", "REJECT"]

    recruiter_summary: str
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)

    debug: Dict[str, Any] = Field(default_factory=dict)