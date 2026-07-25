"""Constants for the HuriS system.

Single source of truth: HuriS_INTERFACES_master_v1.3
Derived from: RuleBook_AgentA v0.8, RuleBook_AgentB v1.21,
              AgentC_Guardrails v1.0, AgentC_Output_Schema.json v1.0

Every constant here is traceable to a spec section. Do not edit without
updating the corresponding spec first -- INTERFACES is the contract.
"""

from typing import Dict, Final

VERSION: Final = "0.2.0"
SPEC_VERSION: Final = "INTERFACES v1.3"


# ---------------------------------------------------------------------------
# Constructs
# ---------------------------------------------------------------------------
# INTERFACES section 2: Agent A emits exactly these 7 boolean tags.
# Nothing else. No confidence, no quotes -- those go to Agent C only.

AGENT_A_TAGS: Final[Dict[str, int]] = {
    "authority_conflict": 2,
    "boundary_blurring": 2,
    "vulnerability_crisis": 2,
    "career_instability": 1,
    "discretion_leak_risk": 1,
    "peer_loyalty_bias": 1,
    "social_attribution_bias": 1,
}

# AgentC_Output_Schema.json accepts 9 constructs: the 7 above plus these two.
# Neither is produced upstream -- Agent C derives them by cross-referencing
# the case file against the interview transcript.
# Decision 2026-07-25: Agent C is the producer.

AGENT_C_DERIVED: Final = (
    "reliability_transparency",
    "personal_responsibility",
)

ALL_CONSTRUCTS: Final = tuple(AGENT_A_TAGS) + AGENT_C_DERIVED

# Guardrails section 3: axes that can carry a red rating.
# Note reliability_transparency is here despite being derived -- this is why
# gap 1 was blocking.

CORE_AXES: Final = (
    "authority_conflict",
    "boundary_blurring",
    "vulnerability_crisis",
    "reliability_transparency",
)


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------
# INTERFACES section 2 and RuleBook B: identical formula in both.

WEIGHT_MULTIPLIER_TRUE: Final = 2.0
WEIGHT_MULTIPLIER_FALSE: Final = 0.5


def effective_weight(tag: str, value: bool) -> float:
    """Weight of a tag once its truth value is known.

    A False tag still carries weight -- it is dampened, not erased.
    Raises KeyError for unknown tags rather than defaulting, so typos
    surface immediately instead of silently scoring zero.
    """
    base = AGENT_A_TAGS[tag]
    return base * (WEIGHT_MULTIPLIER_TRUE if value else WEIGHT_MULTIPLIER_FALSE)


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------
# RuleBook A D-6, restated in INTERFACES section 4b.
# Confidence measures evidence density, not certainty of the verdict.

CONFIDENCE_BY_SIGN_COUNT: Final = {0: "low", 1: "low", 2: "medium"}
CONFIDENCE_HIGH_THRESHOLD: Final = 3


def confidence_for(sign_count: int) -> str:
    """Confidence for a True tag, from how many markers fired.

    False and Unknown always resolve to low and never reach this function.
    """
    if sign_count >= CONFIDENCE_HIGH_THRESHOLD:
        return "high"
    return CONFIDENCE_BY_SIGN_COUNT.get(sign_count, "low")


# ---------------------------------------------------------------------------
# A -> C translation
# ---------------------------------------------------------------------------
# Decision 2026-07-25. Agent A speaks value+confidence; Agent C speaks
# strength. False and Unknown produce no finding at all -- they travel
# through basis/confidence/coverage instead.
#
# Guardrail S2 forbids treating Unknown as False, so the two must stay
# distinguishable in coverage metadata even though neither is reported.

STRENGTH_FROM_CONFIDENCE: Final = {
    "high": "strong",
    "medium": "medium",
    "low": "weak",
}


# ---------------------------------------------------------------------------
# Guardrail thresholds
# ---------------------------------------------------------------------------
# Guardrails section 2, checks G2 and G3.

RED_FLOOR_MEDIUM_COUNT: Final = 2
PATTERN_NOTE_MIN_ANCHORS: Final = 3

# INTERFACES section 5 requires 3 converging anchors. Output_Schema also
# allows "2+ on core axes". Unresolved -- see GAP_MAP.md item 6.
PATTERN_NOTE_ALLOW_CORE_AXIS_SHORTCUT: Final = False


# ---------------------------------------------------------------------------
# Enumerations from AgentC_Output_Schema.json v1.0
# ---------------------------------------------------------------------------

COLORS: Final = ("green", "yellow_complex", "yellow_ambiguity", "red", "unassessable")
CONFIDENCE_LEVELS: Final = ("high", "medium", "low")
RECOMMENDATIONS: Final = (
    "proceed",
    "proceed_caution",
    "insufficient_info",
    "extended_review",
    "redo_interview",
)
INTERVIEW_STATUSES: Final = ("completed_normally", "terminated_safety", "terminated_other")
MODES: Final = ("with_interview", "no_interview")
BASES: Final = ("both", "file_only", "interview_only")
RELATION_TYPES: Final = ("confirm", "contradict", "single_source")
SOURCE_KINDS: Final = ("file", "interview", "cross")
STRENGTHS: Final = ("weak", "medium", "strong")
LEGIBILITY_LEVELS: Final = ("high", "medium", "low")

# Colors that oblige Agent C to write clinical notes (guardrail S8).
COLORS_REQUIRING_REVIEW_NOTES: Final = ("yellow_complex", "yellow_ambiguity", "red")


# ---------------------------------------------------------------------------
# Interview structure
# ---------------------------------------------------------------------------
# RuleBook B v1.21, section D.

CLUSTERS: Final = {
    "A": "biographical",
    "B": "normative_understanding",
    "C": "integrity_under_temptation",
}

CLUSTER_A_QUESTION_QUOTA: Final = 3
FOLLOWUP_QUOTA_BY_WEIGHT: Final = {4: 3, 2: 2}
FOLLOWUP_QUOTA_DEFAULT: Final = 1

# Section 7: interviewer must offer a break every 1.5-3 questions.
CLARITY_CHECK_MIN_INTERVAL: Final = 1.5
CLARITY_CHECK_MAX_INTERVAL: Final = 3

# Section 5: 3+ non-disclosures flag the transcript rather than guessing.
LOW_DISCLOSURE_THRESHOLD: Final = 3
