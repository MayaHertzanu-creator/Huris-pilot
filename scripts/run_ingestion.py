"""HuriS — קליטת תיקי הנבדקים.

מריץ את שכבת הקליטה של סוכן א' על כל תיקיות הנבדקים:
פורס את קבצי ה-ZIP, מתמלל את הסריקות, מדרג קריאוּת, ומפיק תגיות.

הוראות הרצה מלאות: קובץ הוראות_הרצה.md באותה תיקייה.
"""

import asyncio
import os
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE / "huris-agents"       # ניתן לשנות אם שמת את הקוד במקום אחר
OUT = HERE / "_תוצאות"
WORK = HERE / "_extracted"

MODEL = "claude-sonnet-5"


def load_key() -> str:
    """קורא את המפתח מקובץ .env, או ממשתנה סביבה."""
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        sys.exit(
            "לא נמצא מפתח.\n"
            f"צרי קובץ בשם .env בתיקייה {HERE}\n"
            "ובתוכו שורה אחת:  ANTHROPIC_API_KEY=sk-ant-..."
        )
    return key


def unpack() -> list[Path]:
    """פורס את קבצי ה-ZIP של כל נבדק. מדלג על מה שכבר נפרס."""
    WORK.mkdir(exist_ok=True)
    cases = []
    for folder in sorted(HERE.glob("נבדק *")):
        if not folder.is_dir():
            continue
        target = WORK / folder.name
        target.mkdir(parents=True, exist_ok=True)
        if not any(target.iterdir()):
            for archive in folder.glob("*.zip"):
                try:
                    with zipfile.ZipFile(archive) as zf:
                        zf.extractall(target)
                except zipfile.BadZipFile:
                    print(f"  ! לא ניתן לפרוס: {archive.name}")
        if any(target.iterdir()):
            cases.append(target)
    return cases


async def run() -> None:
    sys.path.insert(0, str(REPO))
    try:
        from agents.agent_1 import Ingestor, build_payload, explain, inventory
        from agents.shared import AgentAToBPayload
    except ImportError:
        sys.exit(
            f"לא נמצא קוד הפרויקט ב-{REPO}\n"
            "הורידי אותו מ-github.com/MayaHertzanu-creator/Huris-pilot\n"
            "ושימי את תיקיית huris-agents כאן."
        )

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        sys.exit("חסרות ספריות. הריצי:  pip install anthropic pdfplumber pypdfium2 pydantic")

    client = AsyncAnthropic(api_key=load_key())
    OUT.mkdir(exist_ok=True)

    cases = unpack()
    if not cases:
        sys.exit("לא נמצאו תיקי נבדקים.")

    print(f"נמצאו {len(cases)} תיקים.\n")
    ingestor = Ingestor(client=client, model=MODEL, work_dir=WORK / "_render")

    for case in cases:
        print(f"── {case.name}")
        try:
            sources = await ingestor.ingest_folder(case)
        except Exception as exc:
            print(f"   שגיאה: {exc}\n")
            continue

        for src in sources:
            mark = "✓" if src.usable else "✗"
            print(f"   {mark} {src.name}  [{src.source_type}]  קריאוּת: {src.legibility.value}")

        # התמלול המלא — זה מה שסוכן ג' יקבל
        lines = [f"# {case.name} — תמלול\n"]
        lines.append(f"סוגי מקורות: {', '.join(inventory(sources))}\n")
        for src in sources:
            lines.append(f"\n## {src.name}")
            lines.append(f"*סוג: {src.source_type} · קריאוּת: {src.legibility.value}*\n")
            lines.append(src.text if src.text else "_לא ניתן היה לקרוא_")
        (OUT / f"{case.name} — תמלול.md").write_text("\n".join(lines), encoding="utf-8")

        # תגיות: דורשות שכבת החילוץ, שאינה חלק מהקליטה
        usable = [s for s in sources if s.usable]
        if usable:
            payload = build_payload(case.name, [], sources)
            tag_lines = [f"# {case.name} — תגיות\n"]
            tag_lines.append("> הופק ללא שכבת חילוץ הסימנים — כל התגיות שליליות.")
            tag_lines.append("> משמש לאימות הצינור בלבד.\n")
            for tag in payload.tags:
                tag_lines.append(explain(tag) + "\n")
            tag_lines.append("\n" + payload.coverage_summary().audit_line())
            (OUT / f"{case.name} — תגיות.md").write_text(
                "\n".join(tag_lines), encoding="utf-8"
            )
        print()

    print(f"הסתיים. התוצאות ב: {OUT}")


if __name__ == "__main__":
    asyncio.run(run())
