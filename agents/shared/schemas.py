"""Data contract between the three HuriS agents.

Source of truth: HuriS_INTERFACES_master_v1.3
Agent C output mirrors HuriS_AgentC_Output_Schema.json v1.0 field for field.

Three handoffs are modelled here:

    A -> B   seven booleans, nothing else          (AgentAToBPayload)
    B -> C   interview summary with clusters       (InterviewRecord)
    A -> C   raw case file plus tags with evidence (AgentAToCPayload)

The asymmetry is deliberate. Agent B is kept deliberately uninformed so its
questioning is not steered by Agent A's conclusions; Agent C sees everything
because it is the only agent authorised to integrate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .constants import AGENT_A_TAGS, STRENGTH_FROM_CONFIDENCE, confidence_for


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class TagValue(str, Enum):
    """Ternary truth value for a tag.

    UNKNOWN is not a weaker FALSE. FALSE means the sources were legible and
    carried no sign; UNKNOWN means there was nothing to read. Guardrail S2
    rejects any output that collapses the two.
    """

    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Legibility(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Color(str, Enum):
    GREEN = "green"
    YELLOW_COMPLEX = "yellow_complex"
    YELLOW_AMBIGUITY = "yellow_ambiguity"
    RED = "red"
    UNASSESSABLE = "unassessable"


class Recommendation(str, Enum):
    PROCEED = "proceed"
    PROCEED_CAUTION = "proceed_caution"
    INSUFFICIENT_INFO = "insufficient_info"
    EXTENDED_REVIEW = "extended_review"
    REDO_INTERVIEW = "redo_interview"


class InterviewStatus(str, Enum):
    COMPLETED = "completed_normally"
    TERMINATED_SAFETY = "terminated_safety"
    TERMINATED_OTHER = "terminated_other"


class Mode(str, Enum):
    WITH_INTERVIEW = "with_interview"
    NO_INTERVIEW = "no_interview"


class Basis(str, Enum):
    BOTH = "both"
    FILE_ONLY = "file_only"
    INTERVIEW_ONLY = "interview_only"


class RelationType(str, Enum):
    CONFIRM = "confirm"
    CONTRADICT = "contradict"
    SINGLE_SOURCE = "single_source"


class Strength(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


# ---------------------------------------------------------------------------
# Agent A
# ---------------------------------------------------------------------------


class Sign(BaseModel):
    """One marker hit, with the text that triggered it.

    The quote is verbatim by contract: guardrail G0 re-reads it to check the
    tag against the anti-overdiagnosis blacklist, so a paraphrase would let a
    blacklisted finding through undetected.
    """

    marker_id: str
    quote: str = Field(..., min_length=1)
    source_name: str


class SourceDocument(BaseModel):
    """One document in the case file: what it is, how readable, and its text.

    Name, legibility and content are deliberately kept together. Splitting an
    inventory from a single concatenated blob would let Agent C know that some
    source was illegible without knowing which passage came from it -- and it
    cannot attribute a quote it cannot locate.

    INTERFACES 4c: legibility describes the source, never the subject. A
    low-legibility source yields Unknown, never False.
    """

    name: str
    legibility: Legibility
    kind: Optional[str] = Field(
        default=None,
        description="CV, commander evaluation, psychometric, opinion, ... (RuleBook A D-9)",
    )
    text: str = ""

    @model_validator(mode="after")
    def _check_legible_has_text(self) -> "SourceDocument":
        if self.legibility is not Legibility.LOW and not self.text.strip():
            raise ValueError(
                f"{self.name!r}: marked {self.legibility.value} legibility but "
                f"carries no text. An empty source is low legibility."
            )
        return self


# Retained so existing spec references to "source inventory" keep resolving.
SourceRecord = SourceDocument


class Tag(BaseModel):
    """One of the seven constructs, as decided by Agent A.

    Invariants enforced below come from RuleBook A D-7:
        signs present            -> True
        no signs, coverage yes   -> False
        no signs, no coverage    -> Unknown
    """

    name: str
    value: TagValue
    confidence: Confidence
    coverage: bool = Field(
        ..., description="Whether any source could speak to this tag at all"
    )
    signs_found: List[Sign] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_decision_rule(self) -> "Tag":
        if self.name not in AGENT_A_TAGS:
            raise ValueError(
                f"{self.name!r} is not an Agent A tag. Agent C's derived "
                f"constructs must not appear in Agent A output."
            )

        if self.signs_found and self.value is not TagValue.TRUE:
            raise ValueError(
                f"{self.name}: {len(self.signs_found)} signs found but value "
                f"is {self.value.value}. Any sign forces True (D-7)."
            )

        if not self.signs_found:
            expected = TagValue.FALSE if self.coverage else TagValue.UNKNOWN
            if self.value is not expected:
                raise ValueError(
                    f"{self.name}: no signs with coverage={self.coverage} "
                    f"requires {expected.value}, got {self.value.value} (D-7)."
                )
            if self.confidence is not Confidence.LOW:
                raise ValueError(
                    f"{self.name}: {self.value.value} is always low confidence "
                    f"(D-6), got {self.confidence.value}."
                )
        else:
            expected_conf = confidence_for(len(self.signs_found))
            if self.confidence.value != expected_conf:
                raise ValueError(
                    f"{self.name}: {len(self.signs_found)} signs imply "
                    f"{expected_conf} confidence, got {self.confidence.value} (D-6)."
                )
        return self

    @property
    def strength(self) -> Optional[Strength]:
        """How Agent C should weigh this tag, or None if it carries no finding.

        False and Unknown deliberately return None: the decision of 2026-07-25
        is that negatives travel through coverage metadata, not findings.
        """
        if self.value is not TagValue.TRUE:
            return None
        return Strength(STRENGTH_FROM_CONFIDENCE[self.confidence.value])


class AgentAToBPayload(BaseModel):
    """What Agent B receives. Seven booleans and nothing more.

    INTERFACES 2 is explicit that confidence, quotes and Unknown are withheld,
    so the interviewer cannot be anchored by the file reader's certainty.
    Unknown is deliberately flattened to False here.
    """

    subject_id: str
    tags: Dict[str, bool]

    @model_validator(mode="after")
    def _check_tags(self) -> "AgentAToBPayload":
        missing = set(AGENT_A_TAGS) - set(self.tags)
        unexpected = set(self.tags) - set(AGENT_A_TAGS)
        if missing:
            raise ValueError(f"missing tags for Agent B: {sorted(missing)}")
        if unexpected:
            raise ValueError(f"tags Agent B must not receive: {sorted(unexpected)}")
        return self

    @classmethod
    def from_tags(cls, subject_id: str, tags: List[Tag]) -> "AgentAToBPayload":
        return cls(
            subject_id=subject_id,
            tags={t.name: t.value is TagValue.TRUE for t in tags},
        )


class AgentAToCPayload(BaseModel):
    """What Agent C receives: everything Agent A saw, plus what it concluded.

    Far richer than the Agent B payload by design. INTERFACES 4 makes Agent C
    the only integrator, so it needs the sources themselves and not merely the
    verdicts -- it re-reads them to derive its own constructs (decision 1) and
    to judge whether Agent A's reading holds up.
    """

    subject_id: str
    sources: List[SourceDocument]
    tags: List[Tag]

    @model_validator(mode="after")
    def _check_complete(self) -> "AgentAToCPayload":
        seen = {t.name for t in self.tags}
        missing = set(AGENT_A_TAGS) - seen
        if missing:
            raise ValueError(f"Agent C needs all seven tags, missing: {sorted(missing)}")

        known = {s.name for s in self.sources}
        for tag in self.tags:
            for sign in tag.signs_found:
                if sign.source_name not in known:
                    raise ValueError(
                        f"{tag.name}: sign cites source {sign.source_name!r}, "
                        f"which is not in the inventory. Every quote must be "
                        f"traceable to a source Agent C can open."
                    )
        return self

    @property
    def legible_sources(self) -> List[SourceDocument]:
        return [s for s in self.sources if s.legibility is not Legibility.LOW]

    @property
    def has_legible_source(self) -> bool:
        """False when every source was too degraded to read.

        Drives Agent C towards unassessable rather than green -- the
        difference between "nothing found" and "nothing readable".
        """
        return bool(self.legible_sources)

    def raw_case_text(self, legible_only: bool = True) -> str:
        """The case file as continuous text, with source headers retained.

        Headers are kept so a passage stays attributable after concatenation;
        Agent C needs to name a source when it quotes one.
        """
        docs = self.legible_sources if legible_only else self.sources
        return "\n\n".join(f"### {d.name}\n{d.text}" for d in docs)

    def coverage_summary(self) -> "CoverageSummary":
        """Coverage as Agent C should report it, derived from the tags.

        Computed here rather than restated downstream so the audit counts and
        the tag values cannot disagree.
        """
        return CoverageSummary(
            axes_checked=len(self.tags),
            axes_negative=sum(1 for t in self.tags if t.value is TagValue.FALSE),
            axes_unknown=[t.name for t in self.tags if t.value is TagValue.UNKNOWN],
            unreadable_sources=[
                s.name for s in self.sources if s.legibility is Legibility.LOW
            ],
        )


# ---------------------------------------------------------------------------
# Agent B
# ---------------------------------------------------------------------------


class Exchange(BaseModel):
    question_id: str
    question: str
    answer: str
    cluster: Literal["A", "B", "C"]
    asked_at: datetime
    is_followup: bool = False
    no_evidence: bool = Field(
        default=False,
        description="Candidate declined or gave nothing usable (RuleBook B 6)",
    )


class ClusterSummary(BaseModel):
    cluster: Literal["A", "B", "C"]
    narrative: str
    exchanges: List[Exchange] = Field(default_factory=list)


class InterviewRecord(BaseModel):
    """Agent B's handoff, shaped by INTERFACES 3.

    Agent B reports observations and inconsistencies. It never assigns a tag,
    a confidence or a verdict -- those belong to Agent A and C respectively.
    """

    interview_id: str
    subject_id: str
    conducted_at: datetime
    status: InterviewStatus
    tags_received: Dict[str, bool]
    clusters: List[ClusterSummary] = Field(default_factory=list)
    inconsistency_flags: List[str] = Field(default_factory=list)
    engagement_notes: List[str] = Field(default_factory=list)
    low_disclosure_profile: bool = False
    overall_raw: str = ""
    transcript: Optional[str] = None


# ---------------------------------------------------------------------------
# Agent C
# ---------------------------------------------------------------------------


class CoverageSummary(BaseModel):
    """What was checked, what came back clean, and what could not be reached.

    Exists because findings[] holds only positives, which leaves a clean file
    and an unreadable file looking identical. This is the field that tells
    them apart.

    Two registers, one source: the counts are for the audit log, the sentence
    is for the report. Generating the sentence here rather than letting the
    model phrase it freely means the prose cannot drift from the numbers.
    """

    axes_checked: int
    axes_negative: int
    axes_unknown: List[str] = Field(
        default_factory=list,
        description="Constructs with no legible source. Named, never counted only.",
    )
    unreadable_sources: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_arithmetic(self) -> "CoverageSummary":
        if self.axes_negative + len(self.axes_unknown) > self.axes_checked:
            raise ValueError(
                f"coverage arithmetic: {self.axes_negative} negative + "
                f"{len(self.axes_unknown)} unknown exceeds {self.axes_checked} checked."
            )
        return self

    @property
    def is_complete(self) -> bool:
        return not self.axes_unknown

    def audit_line(self) -> str:
        """Terse and countable. For the log, not the report."""
        return (
            f"coverage: checked={self.axes_checked} "
            f"negative={self.axes_negative} "
            f"unknown={len(self.axes_unknown)}"
            + (f" [{', '.join(self.axes_unknown)}]" if self.axes_unknown else "")
        )

    def limitations_text(self, labels: Optional[Dict[str, str]] = None) -> str:
        """The clinical paragraph, derived from the counts above.

        Negatives collapse into one sentence -- enumerating seven of them pads
        the report without adding information. Gaps are named individually,
        because a reader who cannot see which axis went unexamined cannot
        judge how much the assessment is worth.
        """
        labels = labels or {}
        lines: List[str] = []

        if self.axes_negative == self.axes_checked and self.axes_checked:
            lines.append(
                "החומר שהתקבל אפשר בדיקה של כלל צירי הסיכון, ולא נמצאה בהם "
                "אינדיקציה המצדיקה הסתייגות."
            )
        elif self.axes_negative:
            lines.append(
                "יתר הצירים נבדקו על בסיס החומר שהתקבל ולא עלתה בהם אינדיקציה "
                "המצדיקה הסתייגות."
            )

        if self.axes_unknown:
            named = ", ".join(labels.get(a, a) for a in self.axes_unknown)
            lines.append(
                f"לא ניתן היה להעריך את הצירים הבאים בהיעדר מקור קריא: {named}."
            )
            if self.unreadable_sources:
                lines.append(
                    "המקורות שלא ניתן היה לקרוא: "
                    f"{', '.join(self.unreadable_sources)}."
                )
            lines.append(
                "היעדר ממצא בצירים אלה אינו עדות לתקינותם, אלא להיעדר בסיס להערכה."
            )

        return " ".join(lines)


class Finding(BaseModel):
    """One cross-source finding. Mirrors findings[] in the JSON schema."""

    # Pydantic warns that this shadows the deprecated BaseModel.construct
    # classmethod. Keeping the name anyway: it is the field name in
    # AgentC_Output_Schema.json, and divergence between the schema and the
    # code is the exact class of bug this module exists to prevent.
    model_config = {"protected_namespaces": ()}

    construct: str
    relation_type: RelationType
    sources: List[Literal["file", "interview", "cross"]] = Field(..., min_length=1)
    strength: Strength
    blacklisted: bool
    statistical: bool
    explained: bool
    quote: str

    @model_validator(mode="after")
    def _check_statistical_explained(self) -> "Finding":
        if self.statistical and not self.explained:
            raise ValueError(
                f"{self.construct}: a statistical finding needs a clinical "
                f"mechanism before it can stand (guardrail G4)."
            )
        return self


class PatternNote(BaseModel):
    """Cross-construct risk pattern. Negative direction only.

    Green is the absence of a pattern, never the presence of a positive one --
    the system is not built to certify anyone as low risk.
    """

    present: bool
    direction: Literal["negative"] = "negative"
    axes: List[str] = Field(default_factory=list)
    span: Optional[Literal["within_cluster", "cross_cluster", "cross_source"]] = None


class StatisticalInfluence(BaseModel):
    finding_index: int
    base_rate_or_statistic: str
    direction: Literal["mitigating", "amplifying"]
    clinical_mechanism: Optional[str] = None


class GuardrailCorrection(BaseModel):
    guardrail: Literal[1, 2, 3, 4]
    action: str
    reason: str


class AgentCOutput(BaseModel):
    """Final assessment. Field-for-field mirror of AgentC_Output_Schema.json v1.0."""

    color: Color
    confidence: Confidence
    recommendation: Recommendation
    mode: Mode
    basis: Basis
    findings: List[Finding]

    coverage: CoverageSummary

    interview_status: Optional[InterviewStatus] = None
    force_analyze: bool = False
    primary_axes: List[str] = Field(default_factory=list)
    pattern_note: Optional[PatternNote] = None
    statistical_influences: List[StatisticalInfluence] = Field(default_factory=list)
    guardrail_corrections: List[GuardrailCorrection] = Field(default_factory=list)
    needs_review_notes: bool = False
    opinion: str = ""
    review_notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_output_integrity(self) -> "AgentCOutput":
        """Guardrail checks S8 and S9, plus the force_analyze cap.

        The remaining checks (S1-S7) need the upstream payload and live in
        agent_3.guardrails instead.
        """
        needs_notes = self.color in (
            Color.YELLOW_COMPLEX,
            Color.YELLOW_AMBIGUITY,
            Color.RED,
        )
        if needs_notes and not self.review_notes:
            raise ValueError(f"S8: {self.color.value} requires review_notes.")
        if not needs_notes and self.review_notes:
            raise ValueError(f"S8: {self.color.value} must not carry review_notes.")

        if (
            self.interview_status is InterviewStatus.TERMINATED_SAFETY
            and self.color is not Color.RED
        ):
            raise ValueError("S9: an interview terminated for safety is always red.")

        if self.force_analyze and self.confidence is not Confidence.LOW:
            raise ValueError(
                "force_analyze caps confidence at low; coverage was below floor."
            )

        # A green verdict on an incomplete file is the failure mode this whole
        # coverage apparatus exists to prevent: it reads as a clean bill of
        # health when the truth is that nobody looked.
        if self.color is Color.GREEN and not self.coverage.is_complete:
            raise ValueError(
                f"green requires full coverage; "
                f"{len(self.coverage.axes_unknown)} axes were unassessable "
                f"({', '.join(self.coverage.axes_unknown)}). "
                f"Use unassessable or yellow_ambiguity instead."
            )
        return self


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------


class CaseFile(BaseModel):
    """Everything known about one subject, across all three agents."""

    case_id: str
    subject_id: str
    created_at: datetime
    updated_at: datetime

    agent_a: Optional[AgentAToCPayload] = None
    agent_b: Optional[InterviewRecord] = None
    agent_c: Optional[AgentCOutput] = None

    spec_version: str = "INTERFACES v1.3"

    @property
    def basis(self) -> Basis:
        """Which sources actually contributed, for Agent C's confidence ceiling."""
        if self.agent_a and self.agent_b:
            return Basis.BOTH
        if self.agent_b:
            return Basis.INTERVIEW_ONLY
        return Basis.FILE_ONLY
