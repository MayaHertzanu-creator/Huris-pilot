"""Turning a case file into readable text.

Implements HuriS_AgentA_IngestionSpec v0.1. This is the front door of the whole
system: everything Agent C reasons about passes through here, so a mistake at
this layer is invisible downstream and uncorrectable.

The governing rule is that this layer never interprets. It transcribes what is
there and marks what it could not read. Summarising is Agent C's job, and a
plausible guess at an illegible line is indistinguishable from evidence.

    detect -> extract -> grade legibility -> emit SourceDocument

The extraction step uses a vision model rather than classical OCR. The sources
in practice are Hebrew scans, often skewed, sometimes with the margin cropped
and identifying details blacked out -- conditions under which a character-level
OCR engine degrades quietly, which is the worst failure mode available here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from ..shared.schemas import Legibility, SourceDocument

# IngestionSpec 5. Indicative and meant to move to Config once real
# distributions are known.
LEGIBILITY_HIGH_MIN = 0.95
LEGIBILITY_MEDIUM_MIN = 0.60

UNREADABLE = "[לא קריא]"
REDACTED = "[מוסתר]"

SOURCE_TYPES = (
    "cv",
    "screening_test",
    "recruitment_interview",
    "occupational_psych_opinion",
    "other",
)

RENDER_SCALE = 1.7
MODEL = "claude-sonnet-5"

# A dense page of Hebrew runs long once transcribed verbatim. Too low a
# ceiling truncates the reply mid-JSON, which parses as nothing and marks
# the page unreadable -- so a page would fail precisely because it carried
# the most content.
MAX_TRANSCRIPTION_TOKENS = 16000

# Two runs over one report cleared different pages, so the evidence reaching
# the assessment changed while the document did not. Pinning temperature was
# the obvious remedy and the model does not accept it, so the variance has to
# be worked with instead of removed: a page that fails is attempted again,
# and the best attempt is kept and cached. Repeated reading converges upward
# rather than rerolling, which is what makes a re-run safe.
TRANSCRIPTION_ATTEMPTS = 3


class IngestionError(Exception):
    """Raised only for conditions the caller must act on, never for bad input.

    Unreadable input is a result, not an error: it becomes a low-legibility
    source so the gap stays visible in the assessment.
    """


@dataclass
class PageText:
    """One page's transcription, and how much of it was actually readable."""

    number: int
    text: str
    readable_ratio: float
    notes: str = ""

    @property
    def legibility(self) -> Legibility:
        if self.readable_ratio >= LEGIBILITY_HIGH_MIN:
            return Legibility.HIGH
        if self.readable_ratio >= LEGIBILITY_MEDIUM_MIN:
            return Legibility.MEDIUM
        return Legibility.LOW


def detect_format(path: Path) -> str:
    """Classify a file before trying to read it.

    Returns one of: native_text, scanned_image, mixed, image, plain_text,
    unsupported, empty.
    """
    if not path.exists() or path.stat().st_size == 0:
        return "empty"

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return "plain_text"
    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return "image"
    if suffix in {".docx", ".doc"}:
        return "native_text"
    if suffix != ".pdf":
        return "unsupported"

    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise IngestionError("pdfplumber is required to read PDFs") from exc

    with pdfplumber.open(str(path)) as pdf:
        with_text = sum(1 for page in pdf.pages if (page.extract_text() or "").strip())
        total = len(pdf.pages)

    if total == 0:
        return "empty"
    if with_text == total:
        return "native_text"
    if with_text == 0:
        return "scanned_image"
    return "mixed"


def extract_native_text(path: Path) -> List[PageText]:
    """Read a PDF that already carries a text layer.

    Digital text is taken as fully readable: there was no transcription step
    that could have lost anything.
    """
    import pdfplumber

    pages: List[PageText] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append(
                PageText(
                    number=i,
                    text=text,
                    readable_ratio=1.0 if text else 0.0,
                    notes="" if text else "עמוד ללא שכבת טקסט",
                )
            )
    return pages


def render_pages(path: Path, out_dir: Path, scale: float = RENDER_SCALE) -> List[Path]:
    """Rasterise a PDF so a vision model can read it."""
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover
        raise IngestionError("pypdfium2 is required to render scans") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(path))
    written: List[Path] = []
    for i in range(len(doc)):
        target = out_dir / f"{path.stem}_p{i + 1}.png"
        doc[i].render(scale=scale).to_pil().save(target)
        written.append(target)
    return written


TRANSCRIPTION_PROMPT = f"""אתה מתמלל עמוד סרוק מתוך תיק מועמד.

## תפקידך
לתמלל **מילה במילה** את מה שכתוב. לא לסכם, לא לנסח מחדש, לא לפרש.
הסיכום נעשה בשלב אחר. תפקידך הוא שכבת ההעתקה בלבד.

## כללים מחייבים
1. **העתק מדויק.** שמור על הניסוח המקורי, כולל שגיאות כתיב וקיצורים.
2. **מה שלא ברור — סמן {UNREADABLE}.** אל תנחש. אל תשלים מהקשר.
   מוטב פער מסומן מאשר טקסט סביר שלא נכתב שם.
3. **פרטים מושחרים — סמן {REDACTED}.** אלה הוסתרו בכוונה, לא נעלמו.
4. **שוליים חתוכים — סמן {UNREADABLE} במקום החיתוך.**
   אם מילה נחתכה באמצע, אל תשלים אותה.
5. שמור על מבנה: כותרות, סעיפים ממוספרים, טבלאות.
6. אל תוסיף הערות משלך לתוך התמלול.

## שחזור מהקשר — אסור
מילה שלא ראית בבירור אינה מילה שקראת, גם אם ברור מה היא אמורה להיות.
המסמך הזה משמש להערכת אדם, ומילה ששוחזרה נראית בהמשך הדרך זהה למילה
שנקראה — אין דרך להבדיל ביניהן בשלב מאוחר יותר.

אם אתה מוצא את עצמך כותב "שוחזר מהקשר", "ניחוש הקשרי" או "ייתכן שיש
טעות" — עצור וכתוב {UNREADABLE} במקום. זו התשובה הנכונה, לא כישלון.

## הערכת קריאוּת
דווח איזה חלק מהעמוד **קראת בפועל**, בין 0 ל-1.
אל תספור בתוך זה מילים ששיערת. טקסט משוחזר מוריד את המספר, לא מעלה אותו.
פרטים מושחרים אינם פוגעים בקריאוּת — הם הוסתרו בכוונה וסימונם הוא קריאה
נכונה של העמוד.
במקרה של התלבטות בין שני ערכים — בחר את הנמוך.

## פורמט הפלט
JSON בלבד:

{{"text": "התמלול המלא", "readable_ratio": 0.0, "notes": "מה הפריע לקריאה"}}"""


def response_text(response) -> str:
    """Pull the answer out of a model response, ignoring other block types.

    A response is a list of blocks, and the text is not always first: models
    that reason before answering put a thinking block ahead of it, and tool
    or citation blocks can appear too. Indexing content[0] happens to work
    until the day it does not, and then it fails on every page at once.

    Blocks are joined rather than taking the first, since a long answer can
    be split across several.
    """
    blocks = getattr(response, "content", None) or []
    parts = [
        block.text
        for block in blocks
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    return "\n".join(parts).strip()


def parse_transcription(raw: str) -> Tuple[str, float, str]:
    """Read the model's transcription response.

    A malformed response yields a zero ratio rather than an exception, so the
    page becomes an acknowledged gap instead of stopping the run.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = text.rsplit("```", 1)[0]

    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        return "", 0.0, "תשובת המודל לא ניתנת לפירוק"

    body = (data.get("text") or "").strip()
    try:
        ratio = float(data.get("readable_ratio", 0.0))
    except (TypeError, ValueError):
        ratio = 0.0

    # Out of range means the model misunderstood the scale, so its own
    # estimate tells us nothing. Clamping upward would read a malfunction as
    # a perfectly legible page; treating it as unknown sends the page for
    # human review instead, which is where a confused transcription belongs.
    if not 0.0 <= ratio <= 1.0:
        return body, 0.0, "readable_ratio מחוץ לטווח — דורש בדיקה ידנית"

    if not body:
        ratio = 0.0
    return body, ratio, (data.get("notes") or "").strip()


def grade_document(pages: Sequence[PageText]) -> Legibility:
    """Legibility for a whole document.

    IngestionSpec 2 requires the lowest page value, not the average. A single
    unreadable page among nine readable ones still means a ninth of the
    document is missing, and averaging would hide exactly that.
    """
    if not pages:
        return Legibility.LOW
    order = {Legibility.LOW: 0, Legibility.MEDIUM: 1, Legibility.HIGH: 2}
    return min((p.legibility for p in pages), key=lambda lg: order[lg])


def assemble_text(pages: Sequence[PageText]) -> str:
    """Join pages, keeping page boundaries visible.

    Markers stay in so a later reader can tell a short document from a
    truncated one.
    """
    parts = []
    for page in pages:
        body = page.text if page.text else UNREADABLE
        parts.append(f"--- עמוד {page.number} ---\n{body}")
    return "\n\n".join(parts)


# Phrases that identify a document type. Chosen to be structural -- headings
# and field labels that belong to a form -- rather than topical, since topic
# words like "סמים" appear in every document type in a reliability file.
TYPE_SIGNALS = {
    "cv": (
        "קורות חיים", "ניסיון תעסוקתי", "השכלה", "curriculum", "resume",
    ),
    "screening_test": (
        "integritymeter", "integrity meter", "מבדק אמינות ממוחשב",
        "שאלון", "אחוזון", "ציון גולמי", "סולם", "פרופיל",
    ),
    "recruitment_interview": (
        "שם המתשאל", "שם המראיין", "סיכום והמלצה", "אופן זיהוי הנבדק",
        "כרונולוגיה תעסוקתית", "טופס ראיון", "תאריך ראיון",
    ),
    "occupational_psych_opinion": (
        "חוות דעת", "חוו\"ד", "פסיכולוג", "הערכה תעסוקתית", "אדם מילא",
    ),
}


def classify_source(text: str, name: str = "") -> str:
    """Decide what kind of document this is, from its content.

    Naming was the obvious first approach and it failed completely on the
    real cases: the files arrive as file_1, file_2, file_3, so every source
    classified as 'other' and the source-diversity signal that D-9 and
    INTERFACES 4c depend on was silently empty.

    Signals are counted rather than matched first-wins, because these
    documents quote each other -- an interview summary reports the score of
    a screening test, so a single keyword decides nothing. The type with the
    most distinct hits wins, and a tie or a blank falls to 'other', which
    IngestionSpec 6 prefers to a forced category.
    """
    haystack = f"{text}\n{name}".lower()
    scores = {
        source_type: sum(1 for needle in needles if needle.lower() in haystack)
        for source_type, needles in TYPE_SIGNALS.items()
    }
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "other"
    if sorted(scores.values())[-2:] == [scores[best], scores[best]]:
        return "other"  # two types tied; naming it would be a guess
    return best


def infer_source_type(name: str) -> str:
    """Classify from a filename alone, for sources with no readable text."""
    return classify_source("", name)


def _cache_path(image_path: Path) -> Path:
    return image_path.with_suffix(".transcript.json")


def load_cached_page(image_path: Path) -> Optional[PageText]:
    """Return a page transcribed on an earlier run, if there is one.

    Transcription of the same scan is not repeatable in practice: on two runs
    of one six-page report, different pages cleared the legibility threshold,
    so the evidence reaching the assessment changed while the input did not.
    Caching makes a re-run additive -- a page read once stays read -- instead
    of a fresh roll that can lose what the last run recovered.

    Delete the .transcript.json files to force a clean re-read.
    """
    path = _cache_path(image_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PageText(
            number=int(data["number"]),
            text=data.get("text", ""),
            readable_ratio=float(data.get("readable_ratio", 0.0)),
            notes=data.get("notes", ""),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None  # a damaged cache entry is simply re-read


def save_cached_page(image_path: Path, page: PageText) -> None:
    """Persist a page transcription beside its image."""
    try:
        _cache_path(image_path).write_text(
            json.dumps(
                {
                    "number": page.number,
                    "text": page.text,
                    "readable_ratio": page.readable_ratio,
                    "notes": page.notes,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass  # caching is an optimisation; failing to cache is not an error


def describe_failures(failed: Sequence[PageText], total: int) -> str:
    """Say why each page failed, not merely that it did.

    The reason was being computed and thrown away, which left no way to tell
    a genuinely illegible scan from a reply that was cut off or malformed.
    Those call for opposite responses -- rescan the document, or fix the
    request -- and without the reason recorded, both look like bad paper.
    """
    parts = []
    for page in failed:
        reason = page.notes or f"קריאוּת {page.readable_ratio:.0%}"
        parts.append(f"עמ' {page.number}: {reason}")
    return f"{len(failed)} מתוך {total} עמודים · " + " · ".join(parts)


def unreadable_source(
    label: str, origin_name: str, path: Path, note: str
) -> SourceDocument:
    """A source that could not be read, kept so the gap remains countable."""
    return SourceDocument(
        name=label,
        legibility=Legibility.LOW,
        source_type=infer_source_type(origin_name),
        processed=False,
        text="",
        original_ref=f"{path} · {note}",
    )

class Ingestor:
    """Reads case files into SourceDocuments.

    The client is only needed for scans. A folder of digital PDFs ingests with
    no model call at all, which keeps the deterministic path deterministic.
    """

    def __init__(self, client=None, model: str = MODEL, work_dir: Optional[Path] = None):
        self.client = client
        self.model = model
        self.work_dir = work_dir or Path("/tmp/huris_render")

    async def _transcribe_page(self, image_path: Path) -> PageText:
        if self.client is None:
            raise IngestionError(
                "a scanned source needs a vision client; pass one to Ingestor"
            )

        number = int(image_path.stem.rsplit("_p", 1)[-1])
        best = load_cached_page(image_path)

        # A cached page that read cleanly is final. One that failed is worth
        # another look, since the same scan can read differently on a second
        # attempt -- that variance is the whole reason for retrying.
        if best is not None and best.legibility is not Legibility.LOW:
            return best

        for _ in range(TRANSCRIPTION_ATTEMPTS):
            attempt = await self._transcribe_once(image_path, number)
            if best is None or attempt.readable_ratio > best.readable_ratio:
                best = attempt
                save_cached_page(image_path, best)
            if best.legibility is not Legibility.LOW:
                break

        return best or PageText(number, "", 0.0, "לא התקבלה תשובה")

    async def _transcribe_once(self, image_path: Path, number: int) -> PageText:
        """One attempt at one page."""
        import base64

        data = base64.standard_b64encode(image_path.read_bytes()).decode()
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TRANSCRIPTION_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": data,
                            },
                        },
                        {"type": "text", "text": TRANSCRIPTION_PROMPT},
                    ],
                }
            ],
        )
        raw = response_text(response)
        truncated = getattr(response, "stop_reason", None) == "max_tokens"

        if not raw:
            # No text block at all. Treated as an unread page rather than an
            # error, so one odd response does not abandon the other pages.
            return PageText(number=number, text="", readable_ratio=0.0,
                            notes="המודל לא החזיר טקסט")

        text, ratio, notes = parse_transcription(raw)

        # Truncation has to be named. A cut-off reply parses as nothing and
        # would otherwise be filed as an illegible page, sending someone to
        # re-scan a document that scanned perfectly well.
        if truncated:
            notes = (
                f"התשובה נחתכה בגבול {MAX_TRANSCRIPTION_TOKENS} טוקנים — "
                f"העמוד צפוף מדי, לא בלתי-קריא"
                + (f" · {notes}" if notes else "")
            )
        return PageText(number=number, text=text, readable_ratio=ratio, notes=notes)

    async def ingest_file(self, path: Path, name: Optional[str] = None) -> List[SourceDocument]:
        """Read one file into one or more SourceDocuments.

        Returns a list because a scan is often part legible and part not, and
        the two halves cannot share a legibility grade. The readable pages
        become a usable source; the rest become a recorded gap. Both are
        returned, so nothing readable is lost and nothing unreadable is
        passed off as evidence.

        Unreadable content never raises: it comes back as a low-legibility,
        unprocessed source, so the gap travels forward instead of vanishing.

        Misconfiguration does raise, and deliberately. A missing vision client
        would otherwise mark every scan unreadable, and a batch would return
        assessments that all read "no data" when the truth is that nobody
        supplied a key. A loud failure is recoverable; that one is not.
        """
        path = Path(path)
        name = name or path.stem

        kind = detect_format(path)
        if kind in {"empty", "unsupported"}:
            return [unreadable_source(name, name, path, kind)]

        if kind in {"scanned_image", "mixed", "image"} and self.client is None:
            raise IngestionError(
                f"{path.name} is a {kind} source and needs a vision client. "
                f"Pass one to Ingestor rather than letting the scan be "
                f"recorded as unreadable."
            )

        if kind == "plain_text":
            body = path.read_text(encoding="utf-8", errors="replace").strip()
            pages = [PageText(1, body, 1.0 if body else 0.0)]
        elif kind == "native_text":
            pages = extract_native_text(path)
        else:
            rendered = render_pages(path, self.work_dir / name)
            pages = [await self._transcribe_page(img) for img in rendered]

        return self._split_by_legibility(pages, name, path)

    def _split_by_legibility(
        self, pages: Sequence[PageText], name: str, path: Path
    ) -> List[SourceDocument]:
        """Separate the pages that were read from the pages that were not.

        Grading a whole document by its worst page is right (IngestionSpec 2)
        but discarding the document on that basis is not, and the first real
        run showed the cost: a six-page screening report was dropped whole
        over its blank pages, and the assessment lost the one document that
        described the candidate's risk areas. Absent evidence and unread
        evidence then look identical, which is the confusion this whole
        layer exists to prevent.

        So the grade still comes from the worst page, but only among pages
        that carry text. Pages that failed are reported separately, by
        number, so the gap stays countable.
        """
        readable = [p for p in pages if p.legibility is not Legibility.LOW]
        failed = [p for p in pages if p.legibility is Legibility.LOW]

        docs: List[SourceDocument] = []

        if readable:
            text = assemble_text(readable)
            docs.append(
                SourceDocument(
                    name=name,
                    legibility=grade_document(readable),
                    source_type=classify_source(text, name),
                    processed=True,
                    text=text,
                    original_ref=str(path),
                )
            )

        if failed:
            numbers = ", ".join(str(p.number) for p in failed)
            label = f"{name} — עמודים שלא נקראו ({numbers})" if readable else name
            docs.append(
                unreadable_source(label, name, path, describe_failures(failed, len(pages)))
            )

        return docs or [unreadable_source(name, name, path, "no pages")]

    async def ingest_folder(self, folder: Path) -> List[SourceDocument]:
        """Read every file in a case folder, in a stable order.

        Unreadable files are kept in the result. Dropping them would turn a
        gap into a silence, and Agent A would then record False where the
        honest answer is Unknown.
        """
        folder = Path(folder)
        docs: List[SourceDocument] = []
        for path in sorted(p for p in folder.iterdir() if p.is_file()):
            docs.extend(await self.ingest_file(path))
        return docs




def inventory(sources: Sequence[SourceDocument]) -> List[str]:
    """Distinct source types present, for INTERFACES 4c."""
    seen: List[str] = []
    for source in sources:
        if source.source_type not in seen:
            seen.append(source.source_type)
    return seen
