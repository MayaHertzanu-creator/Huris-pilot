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

## הערכת קריאוּת
בסוף, דווח איזה חלק מהעמוד הצלחת לקרוא בביטחון — מספר בין 0 ל-1.
היה שמרן: אם אתה מתלבט בין שני ערכים, בחר את הנמוך.

## פורמט הפלט
JSON בלבד:

{{"text": "התמלול המלא", "readable_ratio": 0.0, "notes": "מה הפריע לקריאה"}}"""


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


def infer_source_type(name: str) -> str:
    """Guess the document type from its name, defaulting to other.

    IngestionSpec 6 is explicit that a doubtful case takes 'other' with a
    descriptive name rather than a forced category, so a mislabelled document
    does not mislead Agent C about what kind of evidence it is holding.
    """
    lowered = name.lower()
    table = {
        "cv": ("cv", "resume", "קורות חיים", "קו\"ח"),
        "screening_test": ("integrity", "מהימנות", "אמינות", "מבדק", "שאלון"),
        "recruitment_interview": ("ראיון", "interview", "מיון"),
        "occupational_psych_opinion": ("אדם מילא", "הערכה תעסוקתית", "חוו\"ד", "פסיכולוג"),
    }
    for source_type, needles in table.items():
        if any(n.lower() in lowered for n in needles):
            return source_type
    return "other"


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

        import base64

        data = base64.standard_b64encode(image_path.read_bytes()).decode()
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8192,
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
        text, ratio, notes = parse_transcription(response.content[0].text)
        number = int(image_path.stem.rsplit("_p", 1)[-1])
        return PageText(number=number, text=text, readable_ratio=ratio, notes=notes)

    async def ingest_file(self, path: Path, name: Optional[str] = None) -> SourceDocument:
        """Read one file into a SourceDocument.

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

        def unreadable(note: str) -> SourceDocument:
            return SourceDocument(
                name=name,
                legibility=Legibility.LOW,
                source_type=infer_source_type(name),
                processed=False,
                text="",
                original_ref=str(path),
            )

        if kind in {"empty", "unsupported"}:
            return unreadable(kind)

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

        text = assemble_text(pages)
        legibility = grade_document(pages)

        if legibility is Legibility.LOW:
            return unreadable("nothing usable extracted")

        return SourceDocument(
            name=name,
            legibility=legibility,
            source_type=infer_source_type(name),
            processed=True,
            text=text,
            original_ref=str(path),
        )

    async def ingest_folder(self, folder: Path) -> List[SourceDocument]:
        """Read every file in a case folder, in a stable order.

        Unreadable files are kept in the result. Dropping them would turn a
        gap into a silence, and Agent A would then record False where the
        honest answer is Unknown.
        """
        folder = Path(folder)
        docs: List[SourceDocument] = []
        for path in sorted(p for p in folder.iterdir() if p.is_file()):
            docs.append(await self.ingest_file(path))
        return docs


def inventory(sources: Sequence[SourceDocument]) -> List[str]:
    """Distinct source types present, for INTERFACES 4c."""
    seen: List[str] = []
    for source in sources:
        if source.source_type not in seen:
            seen.append(source.source_type)
    return seen
