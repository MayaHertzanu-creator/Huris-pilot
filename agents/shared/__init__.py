"""Shared contract between the three HuriS agents.

Import from here rather than from the submodules directly, so the surface
that agents depend on stays explicit and reviewable.
"""

from .constants import (
    AGENT_A_TAGS,
    AGENT_C_DERIVED,
    ALL_CONSTRUCTS,
    CORE_AXES,
    STRENGTH_FROM_CONFIDENCE,
    confidence_for,
    effective_weight,
)
from .schemas import (
    AgentAToBPayload,
    AgentAToCPayload,
    AgentCOutput,
    Basis,
    CaseFile,
    ClusterSummary,
    Color,
    Confidence,
    CoverageSummary,
    Exchange,
    Finding,
    GuardrailCorrection,
    InterviewRecord,
    InterviewStatus,
    Legibility,
    Mode,
    PatternNote,
    Recommendation,
    RelationType,
    Sign,
    SourceRecord,
    StatisticalInfluence,
    Strength,
    Tag,
    TagValue,
)

__all__ = [
    # constants
    "AGENT_A_TAGS",
    "AGENT_C_DERIVED",
    "ALL_CONSTRUCTS",
    "CORE_AXES",
    "STRENGTH_FROM_CONFIDENCE",
    "confidence_for",
    "effective_weight",
    # agent A
    "Sign",
    "SourceRecord",
    "Tag",
    "TagValue",
    "Legibility",
    "AgentAToBPayload",
    "AgentAToCPayload",
    # agent B
    "Exchange",
    "ClusterSummary",
    "InterviewRecord",
    "InterviewStatus",
    # agent C
    "AgentCOutput",
    "CoverageSummary",
    "Finding",
    "PatternNote",
    "StatisticalInfluence",
    "GuardrailCorrection",
    "Color",
    "Confidence",
    "Recommendation",
    "Mode",
    "Basis",
    "RelationType",
    "Strength",
    # case
    "CaseFile",
]
