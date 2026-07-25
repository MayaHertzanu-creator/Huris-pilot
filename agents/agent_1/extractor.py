"""Agent A's reading layer.

The only probabilistic part of Agent A. It reads each source and reports which
markers it saw, with the sentence that triggered each one. It reaches no
conclusion: whether a tag ends up True, False or Unknown is decided afterwards
by decision.py, from fixed rules.

RuleBook A D-1 mandates this split. A model asked to both read and judge will
quietly trade one against the other -- lowering its reading threshold when it
suspects a case is serious. Separating them keeps the threshold fixed.
"""

import json
from typing import List, Optional, Sequence

from ..shared.schemas import Legibility, Sign, SourceDocument
from .markers import BY_ID, MARKERS

MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096


def build_prompt(source: SourceDocument) -> str:
    """The extraction prompt for one source.

    One source per call, on purpose. Batching invites the model to carry an
    impression from a commander's evaluation into a CV and cite it there,
    which would break the source attribution that guardrail G0 depends on.
    """
    catalogue = "\n".join(f"- {m.id}: {m.description}" for m in MARKERS)

    return f"""אתה קורא מסמך אחד מתוך תיק מועמד ומדווח אילו מרקרים מופיעים בו.

## תפקידך
לדווח מה כתוב. **לא** להעריך, לא להסיק, ולא להחליט.
ההכרעה נעשית בשלב אחר, בכללים קבועים. תפקידך הוא הקריאה בלבד.

## רשימת המרקרים
{catalogue}

## כללים
1. דווח על מרקר רק אם יש **ציטוט מילולי** מהטקסט שתומך בו.
   ציטוט מדויק, מילה במילה. לא פרפרזה, לא סיכום.
2. אל תמציא מזהי מרקרים. השתמש אך ורק במזהים שברשימה.
3. אותו מרקר יכול להופיע פעם אחת בלבד. אם יש כמה ציטוטים — בחר את המובהק ביותר.
4. **אם לא מצאת דבר, החזר רשימה ריקה.** זו תוצאה תקינה ושכיחה.
   אין שום העדפה למצוא משהו.
5. אל תדווח על מרקר על סמך היעדר: "לא הזכיר את משפחתו" אינו ממצא.
6. ברירת המחדל היא לא לדווח. דווח רק כשהטקסט אומר את הדבר במפורש.

## המסמך
שם: {source.name}
סוג: {source.kind or "לא צוין"}

---
{source.text}
---

## פורמט הפלט
JSON בלבד, ללא טקסט נוסף:

{{"signs": [{{"marker_id": "...", "quote": "ציטוט מילולי מדויק"}}]}}

אם אין ממצאים: {{"signs": []}}"""


def parse_response(raw: str, source: SourceDocument) -> List[Sign]:
    """Turn a model response into signs, discarding anything unverifiable.

    Three checks, all of which drop the sign rather than repairing it:

    - unknown marker id: the model invented a criterion
    - empty quote: nothing for guardrail G0 to inspect later
    - quote absent from the source: the model paraphrased or confabulated

    Dropping is the safe direction. A missed sign lowers confidence; a
    fabricated one raises a tag on evidence that does not exist.
    """
    try:
        payload = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return []

    signs: List[Sign] = []
    for entry in payload.get("signs", []):
        marker_id = entry.get("marker_id", "")
        quote = (entry.get("quote") or "").strip()

        if marker_id not in BY_ID or not quote:
            continue
        if _normalise(quote) not in _normalise(source.text):
            continue

        signs.append(
            Sign(marker_id=marker_id, quote=quote, source_name=source.name)
        )
    return signs


def _strip_fences(raw: str) -> str:
    """Unwrap a markdown code fence, if the model added one.

    Handles both the usual ```json\\n{...}\\n``` and the newline-less
    ```json{...}```. Dropping a well-formed response over its wrapper would
    silently lose real signs, which is the same failure as missing them.
    """
    text = raw.strip()
    if not text.startswith("```"):
        return text

    text = text[3:]
    for lang in ("json", "JSON"):
        if text.startswith(lang):
            text = text[len(lang) :]
            break
    if text.startswith("\n"):
        text = text[1:]
    return text.rsplit("```", 1)[0].strip()


def _normalise(text: str) -> str:
    """Collapse whitespace so a quote survives reflowing, but nothing more.

    Punctuation and wording are left intact: loosening the comparison further
    would start accepting paraphrase, which is the thing being guarded against.
    """
    return " ".join(text.split())


class SignExtractor:
    """Reads sources and reports observed markers.

    Sources marked low legibility are skipped rather than read. Guessing at
    an illegible scan produces plausible text and unfounded signs; skipping
    yields Unknown, which is the honest result.
    """

    def __init__(self, client, model: str = MODEL):
        self.client = client
        self.model = model

    async def extract_from_source(self, source: SourceDocument) -> List[Sign]:
        if source.legibility is Legibility.LOW or not source.text.strip():
            return []

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": build_prompt(source)}],
        )
        return parse_response(response.content[0].text, source)

    async def extract_signs(self, sources: Sequence[SourceDocument]) -> List[Sign]:
        """Read every legible source and pool the signs.

        decision.py deduplicates by marker, so the same marker seen in two
        sources still counts once -- convergence across documents is a
        question for Agent C, which is the agent allowed to weigh it.
        """
        collected: List[Sign] = []
        for source in sources:
            collected.extend(await self.extract_from_source(source))
        return collected
