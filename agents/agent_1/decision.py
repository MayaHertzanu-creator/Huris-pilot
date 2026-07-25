"""The deterministic half of Agent A.

RuleBook A D-1 splits the agent in two: a model reads the sources and reports
what it saw, and fixed rules decide what that means. This module is the second
half. It contains no model call and no I/O, which is what makes Agent A's
behaviour reproducible and testable -- the same signs always yield the same
tag, today and in a year.

Implements D-5 (any marker raises the tag), D-6 (confidence from marker count)
and D-7 (False versus Unknown).
"""

from typing import Dict, Iterable, List, Sequence

from ..shared.constants import AGENT_A_TAGS, confidence_for
from ..shared.schemas import (
    AgentAToCPayload,
    Confidence,
    Legibility,
    Sign,
    SourceDocument,
    Tag,
    TagValue,
)
from .markers import BY_ID, markers_for


class UnknownMarkerError(ValueError):
    """A sign cites a marker id that is not in the registry.

    Usually means the extraction layer invented an id, which would let an
    unreviewed criterion into the assessment. Refused rather than dropped, so
    it surfaces instead of quietly shrinking the evidence.
    """


def _validate_signs(signs: Iterable[Sign]) -> List[Sign]:
    unknown = sorted({s.marker_id for s in signs if s.marker_id not in BY_ID})
    if unknown:
        raise UnknownMarkerError(
            f"unrecognised marker ids: {unknown}. Extraction may only cite "
            f"markers defined in Appendix A."
        )
    return list(signs)


def _dedupe(signs: Sequence[Sign]) -> List[Sign]:
    """Collapse repeat hits on the same marker.

    D-6 counts distinct markers, not quotes. One vivid passage that trips the
    same marker three times is one convergence, not three: counting it thrice
    would let a single sentence carry a tag to high confidence.
    """
    seen: Dict[str, Sign] = {}
    for sign in signs:
        seen.setdefault(sign.marker_id, sign)
    return list(seen.values())


def has_coverage(construct: str, sources: Sequence[SourceDocument]) -> bool:
    """Whether any source could speak to this construct at all.

    Deliberately coarse: a legible source counts as coverage for every
    construct. Appendix A warns against inferring absence from a source that
    merely did not mention something, but a readable file that never raises a
    theme is evidence of absence, whereas an unreadable one is evidence of
    nothing.

    Sharper per-construct coverage would need each marker to declare which
    document kinds can bear on it. Left coarse until the ValidationSet shows
    whether that distinction changes any outcome.
    """
    if construct not in AGENT_A_TAGS:
        raise KeyError(f"{construct!r} is not an Agent A construct.")
    return any(s.legibility is not Legibility.LOW for s in sources)


def decide_tag(
    construct: str,
    signs: Sequence[Sign],
    sources: Sequence[SourceDocument],
) -> Tag:
    """Turn observed signs into a decided tag.

    D-7, in order:
        any sign            -> True,    confidence from the count (D-6)
        no sign, coverage   -> False,   low confidence
        no sign, no coverage-> Unknown, low confidence

    The asymmetry is the point. False is a finding; Unknown is an admission.
    """
    relevant = _dedupe(
        [s for s in _validate_signs(signs) if BY_ID[s.marker_id].construct == construct]
    )

    if relevant:
        return Tag(
            name=construct,
            value=TagValue.TRUE,
            confidence=Confidence(confidence_for(len(relevant))),
            coverage=True,
            signs_found=relevant,
        )

    covered = has_coverage(construct, sources)
    return Tag(
        name=construct,
        value=TagValue.FALSE if covered else TagValue.UNKNOWN,
        confidence=Confidence.LOW,
        coverage=covered,
        signs_found=[],
    )


def decide_all(
    signs: Sequence[Sign],
    sources: Sequence[SourceDocument],
) -> List[Tag]:
    """Decide all seven tags.

    Always returns seven, in the order given by AGENT_A_TAGS. A construct that
    was never mentioned still gets a tag -- silence is a result that has to be
    recorded, not a reason to omit the row.
    """
    _validate_signs(signs)
    return [decide_tag(name, signs, sources) for name in AGENT_A_TAGS]


def build_payload(
    subject_id: str,
    signs: Sequence[Sign],
    sources: Sequence[SourceDocument],
) -> AgentAToCPayload:
    """Assemble the Agent C handoff.

    Validation lives in the schema, so a malformed payload cannot be built:
    every quote must name a source in the inventory, and all seven tags must
    be present.
    """
    return AgentAToCPayload(
        subject_id=subject_id,
        sources=list(sources),
        tags=decide_all(signs, sources),
    )


def explain(tag: Tag) -> str:
    """One human-readable line per tag, for the audit trail (D-8).

    D-8 requires every decision to be traceable to why it was made, so the
    marker description is spelled out rather than only its id -- a reader
    auditing a case a year from now should not have to hold the registry in
    their head.
    """
    if tag.value is not TagValue.TRUE:
        reason = (
            "נבדק, לא נמצאו סימנים"
            if tag.value is TagValue.FALSE
            else "אין מקור קריא, לא ניתן להעריך"
        )
        return f"{tag.name} = {tag.value.value} ({tag.confidence.value}) — {reason}"

    lines = [
        f"{tag.name} = True (confidence: {tag.confidence.value}, "
        f"{len(tag.signs_found)} סימנים)"
    ]
    for sign in tag.signs_found:
        lines.append(
            f'    {sign.marker_id}: "{sign.quote}" — מקור: {sign.source_name}'
        )
        lines.append(f"        [{BY_ID[sign.marker_id].description}]")
    return "\n".join(lines)


def coverage_report(construct: str) -> str:
    """The markers checked for a construct, for the report's method section."""
    ms = markers_for(construct)
    return f"{construct}: נבדקו {len(ms)} מרקרים ({', '.join(m.id for m in ms)})"
