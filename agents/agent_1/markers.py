"""The marker registry: what Agent A looks for, and under what id.

Transcribed from Appendix_A_QuickReference_for_AgentA v1.16. This module is
data, not logic -- the decision rules live in decision.py and the reading
layer in extractor.py, per RuleBook A D-1.

Two entries here differ from what a reasonable reading of the tag names would
suggest, and both are deliberate. They are flagged in place.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Marker:
    """One observable sign that a construct may be present.

    A marker is a reading instruction, not a verdict. Whether the text
    matches is judged by the extraction layer; what that match means is
    decided by decision.py.
    """

    id: str
    construct: str
    description: str
    cues: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def index(self) -> int:
        return int(self.id.rsplit(".", 1)[1])


MARKERS: Tuple[Marker, ...] = (
    # -- authority_conflict (weight 2) ------------------------------------
    # Repeated friction with command, hierarchy or discipline.
    Marker(
        "authority_conflict.1",
        "authority_conflict",
        "הערות על מנהל שלא הוקיר או על ציוות שלא תמך",
        ("מנהל שלא הוקיר", "צוות שלא תמך"),
    ),
    Marker(
        "authority_conflict.2",
        "authority_conflict",
        "היסטוריית תלונות חוזרות על חוסר הוגנות",
        ("חוסר הוגנות", "תלונה חוזרת"),
    ),
    Marker(
        "authority_conflict.3",
        "authority_conflict",
        "ביטויים על צורך לעשות דברים בדרכי שלי",
        ("בדרכי שלי", "לעשות דברים אחרת"),
    ),
    Marker(
        "authority_conflict.4",
        "authority_conflict",
        "פעולות מתועדות של עקיפת סמכות",
        ("דיווח מעל הראש", "פנייה בעד צד"),
    ),
    # -- boundary_blurring (weight 2) --------------------------------------
    # Difficulty holding a line between the personal and the professional.
    Marker(
        "boundary_blurring.1",
        "boundary_blurring",
        "אזכור הנחיה שלא עקבתי או דרך שלי",
        ("הנחיה שלא עקבתי", "דרך שלי"),
    ),
    Marker(
        "boundary_blurring.2",
        "boundary_blurring",
        "הצדקות מסוג הגיוני לי יותר או זה עבד",
        ("הגיוני לי יותר", "זה עבד"),
    ),
    Marker(
        "boundary_blurring.3",
        "boundary_blurring",
        "היסטוריית קיצורי דרך בהקשרים שונים",
        ("קיצור דרך",),
    ),
    Marker(
        "boundary_blurring.4",
        "boundary_blurring",
        "מודעות: לא בדיוק לפי הספר אבל עבד",
        ("לא בדיוק לפי הספר",),
    ),
    # -- vulnerability_crisis (weight 2) -----------------------------------
    # Appendix A defines a single marker here on purpose: one crisis event is
    # itself the indication, so no convergence is required to raise the tag.
    # Confidence still lands low, which is the intended shape -- the tag
    # fires, but it does not carry the case on its own.
    #
    # Crisis detail must never reach Agent B (INTERFACES 2 and the note in
    # Appendix A). The type system already prevents it: AgentAToBPayload
    # carries booleans only.
    Marker(
        "vulnerability_crisis.1",
        "vulnerability_crisis",
        "עדות לרצף משברי משמעותי בשנה האחרונה: אובדן עבודה או משבר כלכלי, "
        "בעיה בריאותית חמורה, קריסת משפחה או גירושין, אובדן אדם קרוב, "
        "וגם אינדיקציה שעדיין בתהליך התמודדות",
        ("אובדן עבודה", "משבר כלכלי", "גירושין", "אובדן", "עדיין מתמודד"),
    ),
    # -- career_instability (weight 1) -------------------------------------
    Marker(
        "career_instability.1",
        "career_instability",
        "שינויי תעסוקה תכופים בתקופה קצרה: ארבעה ומעלה בארבע שנים",
        ("החלפת תפקיד", "מעבר מקום עבודה"),
    ),
    Marker(
        "career_instability.2",
        "career_instability",
        "שינויים בלא סיבה ברורה: מעברים צדדיים או ירידות",
        ("מעבר צדדי", "ירידה בדרגה"),
    ),
    Marker(
        "career_instability.3",
        "career_instability",
        "הערות חוזרות על משעמם או שגרה או צריך חדש",
        ("משעמם", "צריך משהו חדש"),
    ),
    Marker(
        "career_instability.4",
        "career_instability",
        "דפוס הרגשתי בלחץ וקמתי לעזוב: היעדר סבילות",
        ("קמתי לעזוב", "לא יכולתי יותר"),
    ),
    # -- discretion_leak_risk (weight 1) -----------------------------------
    Marker(
        "discretion_leak_risk.1",
        "discretion_leak_risk",
        "אזכור שיתוף מידע או דיבור עם חברים בהקשרים שונים",
        ("שיתפתי", "דיברתי עם חברים"),
    ),
    Marker(
        "discretion_leak_risk.2",
        "discretion_leak_risk",
        "ביטויים: קשה להחזיק את זה בתוכי",
        ("קשה להחזיק בתוכי",),
    ),
    Marker(
        "discretion_leak_risk.3",
        "discretion_leak_risk",
        "דפוס שיתוף מידע אישי או רגיש עם קולגות",
        ("סיפרתי לקולגה",),
    ),
    Marker(
        "discretion_leak_risk.4",
        "discretion_leak_risk",
        "חברות או שיתוף כערך חוזר בהקשר מקצועי",
        ("חברות מעל הכל",),
    ),
    # -- peer_loyalty_bias (weight 1) --------------------------------------
    Marker(
        "peer_loyalty_bias.1",
        "peer_loyalty_bias",
        "אזכור כיסוי על חבר או לא דיווחתי על שגיאה",
        ("כיסיתי על", "לא דיווחתי"),
    ),
    Marker(
        "peer_loyalty_bias.2",
        "peer_loyalty_bias",
        "ביטויים: זו נאמנות או הוא ידיד שלי",
        ("זו נאמנות", "ידיד שלי"),
    ),
    Marker(
        "peer_loyalty_bias.3",
        "peer_loyalty_bias",
        "דפוס בחרתי בקרוב על פני הכלל בהקשרים שונים",
        ("בחרתי בקרוב",),
    ),
    Marker(
        "peer_loyalty_bias.4",
        "peer_loyalty_bias",
        "הערות על הלויאליות שלי לאנשים לא לדברים",
        ("לויאלי לאנשים",),
    ),
    # -- social_attribution_bias (weight 1) --------------------------------
    # Three markers, not four. Appendix A v1.16 removed the "low cognitive
    # flexibility" marker and moved it to Agent B's SJT: it is a reasoning
    # trait observable in response to a scenario, not something a file can
    # show. Adding a fourth marker here by analogy with the other tags would
    # silently reintroduce it.
    Marker(
        "social_attribution_bias.1",
        "social_attribution_bias",
        "שינויי מקומות עבודה תכופים במעברים צדדיים או ירידות בלא סיבה ברורה",
        ("מעבר בלא סיבה",),
    ),
    Marker(
        "social_attribution_bias.2",
        "social_attribution_bias",
        "ביטויי תוקפנות או דה-הומניזציה של סמכות או קולגות בהקשרים שונים",
        ("הם נגדי", "אי אפשר לסמוך על אף אחד"),
    ),
    Marker(
        "social_attribution_bias.3",
        "social_attribution_bias",
        "דפוס קשרים קצרי-חיים או עזיבות מהירות",
        ("קשר קצר", "עזיבה מהירה"),
    ),
)


BY_CONSTRUCT: Dict[str, List[Marker]] = {}
for _m in MARKERS:
    BY_CONSTRUCT.setdefault(_m.construct, []).append(_m)

BY_ID: Dict[str, Marker] = {m.id: m for m in MARKERS}


def markers_for(construct: str) -> List[Marker]:
    """Markers defined for a construct.

    Raises rather than returning empty: an unknown construct means a typo or
    an Agent C construct leaking into Agent A, and both should stop the run.
    """
    if construct not in BY_CONSTRUCT:
        raise KeyError(
            f"{construct!r} has no markers. Agent A covers "
            f"{sorted(BY_CONSTRUCT)}; derived constructs belong to Agent C."
        )
    return BY_CONSTRUCT[construct]
