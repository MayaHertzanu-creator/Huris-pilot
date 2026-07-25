"""Data schemas for HuriS system."""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence levels for findings."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ValueType(str, Enum):
    """Value types for findings."""
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


class Evidence(BaseModel):
    """Single piece of evidence supporting a finding."""
    source_id: str = Field(..., description="Source document/interview ID")
    quote: Optional[str] = Field(None, description="Direct quote from source")
    page: Optional[int] = Field(None, description="Page number if applicable")
    timestamp: Optional[str] = Field(None, description="Interview timestamp if applicable")


class Finding(BaseModel):
    """A single psychological finding."""
    id: str = Field(..., description="Unique finding ID")
    construct: str = Field(..., description="Psychological construct (e.g., 'authority_conflict')")
    value: ValueType = Field(..., description="True/False/Unknown assessment")
    confidence: ConfidenceLevel = Field(..., description="Confidence in assessment")
    evidence: List[Evidence] = Field(default_factory=list)
    notes: Optional[str] = Field(None, description="Analyst notes")
    tagged: bool = Field(default=False, description="Whether finding is cross-checked")


class InterviewResponse(BaseModel):
    """Single interview response."""
    question_id: str
    question_text: str
    response_text: str
    tags: List[str] = Field(default_factory=list)
    timestamp: datetime


class Interview(BaseModel):
    """Interview data from Agent 2."""
    interview_id: str
    subject_id: str
    date: datetime
    responses: List[InterviewResponse]
    raw_transcript: Optional[str] = None
    completion_status: str = Field(default="completed", description="completed_normally | terminated_safety | terminated_other")


class Report(BaseModel):
    """Final psychological report from Agent 3."""
    report_id: str
    subject_id: str
    date_generated: datetime
    findings: List[Finding]
    analysis: str = Field(..., description="Narrative analysis")
    recommendations: Optional[str] = None
    guardrail_status: str = Field(default="passed", description="passed | needs_review | failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseFile(BaseModel):
    """Complete case file combining all agent outputs."""
    case_id: str
    subject_id: str
    created_at: datetime
    last_updated: datetime

    # Agent 1 outputs
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    source_documents: List[str] = Field(default_factory=list)

    # Agent 2 outputs
    interview: Optional[Interview] = None

    # Agent 3 outputs
    report: Optional[Report] = None

    # Metadata
    version: str = "0.1.0"
    status: str = Field(default="in_progress", description="in_progress | completed | archived")
