"""HuriS — קליטת תיקי הנבדקים.

מריץ את שכבת הקליטה של סוכן א' על כל תיקיות הנבדקים:
פורס את קבצי ה-ZIP, מתמלל את הסריקות, מדרג קריאוּת, ומפיק תגיות.

הרצה:  python הרץ_קליטה.py

הסקריפט בודק את המפתח לפני שהוא מתחיל, ומדלג על תיקים שכבר נקלטו —
אפשר לעצור באמצע ולהריץ שוב בלי לשלם פעמיים.
"""

import asyncio
import os
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE / "huris-agents"
OUT = HERE / "_תוצאות"
WORK = HERE / "_extracted"

MODEL = "claude-sonnet-5"
KEY_PREFIX = "sk-ant-"


def say(text: str) -> None:
    """הדפסה שלא קורסת על מסוף שלא תומך בעברית."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode())


def load_key() -> str:
    """קורא את המפתח מקובץ .env ובודק שהוא סביר לפני שמנסים להשתמש בו."""
    env = HERE / ".env"

    if not env.exists():
        sys.exit(
            f"\nלא נמצא קובץ .env בתיקייה:\n  {HERE}\n\n"
            "צריך קובץ בשם .env ובתוכו שורה אחת:\n"
            "  ANTHROPIC_API_KEY=sk-ant-api03-...\n"
        )

    key = ""
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip().lstrip("﻿")
        if line.startswith("ANTHROPIC_API_KEY"):
            key = line.split("=", 1)[1].strip() if "=" in line else ""
            break

    # ציטוט או רווח נסתר הם הסיבה השכיחה ל"מפתח לא תקף"
    key = key.strip().strip('"').strip("'").strip()

    if not key:
        sys.exit(
            "\nהקובץ .env קיים אבל אין בו מפתח.\n"
            "השורה צריכה להיראות בדיוק כך, בלי גרשיים ובלי רווחים:\n"
            "  ANTHROPIC_API_KEY=sk-ant-api03-...\n"
        )

    if not key.startswith(KEY_PREFIX):
        sys.exit(
            f"\nהמפתח לא מתחיל ב-{KEY_PREFIX}\n"
            f"מה שנמצא מתחיל ב: {key[:12]}...\n"
            "כנראה הועתק משהו אחר, או שנשארה מילה מיותרת בשורה.\n"
        )

    if len(key) < 90:
        sys.exit(
            f"\nהמפתח קצר מדי ({len(key)} תווים; מצופה כ-100 ומעלה).\n"
            "כנראה ההעתקה נחתכה. השתמשי בכפתור ההעתקה שליד המפתח,\n"
            "ולא בסימון ידני עם העכבר.\n"
        )

    say(f"מפתח נטען: {key[:14]}...{key[-4:]}  ({len(key)} תווים)")
    return key


async def verify_key(client) -> None:
    """בדיקה זולה אחת לפני שמעבדים 85 עמודים."""
    say("בודק את המפתח מול Anthropic...")
    try:
        await client.messages.create(
            model=MODEL,
            max_tokens=4,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:
        text = str(exc)
        if "authentication" in text or "401" in text:
            sys.exit(
                "\nהמפתח נדחה על ידי Anthropic.\n\n"
                "שלוש סיבות אפשריות:\n"
                "  1. המפתח נמחק או הועתק חלקית — צרי חדש ב-console.anthropic.com\n"
                "  2. המפתח שייך לחשבון אחר\n"
                "  3. ההרשמה ל-Console לא הושלמה\n"
            )
        if "credit" in text.lower() or "billing" in text.lower():
            sys.exit(
                "\nאין יתרה בחשבון.\n"
                "היכנסי ל-console.anthropic.com → Billing → הוסיפי קרדיט.\n"
            )
        sys.exit(f"\nשגיאה בפנייה ל-Anthropic:\n{text}\n")
    say("המפתח תקין.\n")


def open_in_editor(path: Path) -> bool:
    """פותח קובץ בתוכנה שמוגדרת אצל המשתמש.

    התמלול הוא עברית ארוכה, והמסוף של Windows לא מציג אותה כראוי. פתיחה
    בחלון נפרד היא הדרך היחידה שבה אפשר באמת לקרוא את מה שיצא.
    """
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", str(path)], check=False)
        else:
            import subprocess
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except Exception:
        return False


def summarise(sources) -> None:
    """מדפיס סטטיסטיקה קצרה שאפשר לקרוא גם במסוף שלא תומך בעברית."""
    from agents.agent_1.ingestion import UNREADABLE

    total_gaps = sum(s.text.count(UNREADABLE) for s in sources)
    usable = sum(1 for s in sources if s.usable)
    say(f"   מקורות: {usable}/{len(sources)} שמישים · סימוני [לא קריא]: {total_gaps}")
    if total_gaps == 0 and usable:
        say("   שים לב: אפס פערים. כדאי לוודא מול המקור שלא הושלם טקסט.")


def ask_continue(case_name: str, remaining: int) -> str:
    """עצירה לאישור בין נבדקים.

    מחזיר: continue / all / stop.
    עצירה אינה מאבדת דבר — מה שנקלט כבר נשמר, והרצה חוזרת מדלגת עליו.
    """
    if remaining == 0:
        return "stop"
    say("")
    say(f"   סיימתי את {case_name}. נותרו {remaining}.")
    say("   [Enter] להמשיך · [a] להריץ הכל בלי לשאול · [n] לעצור")
    try:
        answer = input("   > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "stop"
    if answer.startswith("n"):
        return "stop"
    if answer.startswith("a"):
        return "all"
    return "continue"


def unpack() -> list:
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
                    say(f"  ! לא ניתן לפרוס: {archive.name}")
        if any(target.iterdir()):
            cases.append(target)
    return cases


async def run() -> None:
    sys.path.insert(0, str(REPO))
    try:
        from agents.agent_1 import Ingestor, build_payload, explain, inventory
    except ImportError as exc:
        sys.exit(
            f"\nלא נמצא קוד הפרויקט ב:\n  {REPO}\n\n"
            f"פרטים: {exc}\n"
        )

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        sys.exit(
            "\nחסרות ספריות. הריצי:\n"
            "  pip install anthropic pdfplumber pypdfium2 pydantic\n"
        )

    client = AsyncAnthropic(api_key=load_key())
    await verify_key(client)

    OUT.mkdir(exist_ok=True)
    cases = unpack()
    if not cases:
        sys.exit("לא נמצאו תיקי נבדקים.")

    pending = [c for c in cases if not (OUT / f"{c.name} — תמלול.md").exists()]
    done = len(cases) - len(pending)
    if done:
        say(f"{done} תיקים כבר נקלטו — מדלג עליהם.")
    if not pending:
        say(f"\nהכול כבר נקלט. התוצאות ב:\n  {OUT}")
        return

    say(f"נותרו {len(pending)} תיקים לעיבוד.")
    say("אחרי כל נבדק ייפתח התמלול לבדיקה, ותישאלי אם להמשיך.")
    say("(להרצה רצופה בלי עצירות: python הרץ_קליטה.py --all)\n")

    ask = "--all" not in sys.argv
    ingestor = Ingestor(client=client, model=MODEL, work_dir=WORK / "_render")

    for index, case in enumerate(pending):
        say(f"── {case.name}")
        try:
            sources = await ingestor.ingest_folder(case)
        except Exception as exc:
            say(f"   שגיאה: {exc}\n")
            continue

        for src in sources:
            mark = "V" if src.usable else "X"
            say(f"   {mark} {src.name}  [{src.source_type}]  קריאוּת: {src.legibility.value}")

        summarise(sources)

        lines = [f"# {case.name} — תמלול\n"]
        lines.append(f"סוגי מקורות: {', '.join(inventory(sources))}\n")
        lines.append(
            "> בדקי מול הסריקה המקורית: האם משהו **הומצא**? "
            "פער מסומן ב-[לא קריא] הוא תקין; טקסט סביר שלא כתוב במקור הוא כשל.\n"
        )
        for src in sources:
            lines.append(f"\n## {src.name}")
            lines.append(f"*סוג: {src.source_type} · קריאוּת: {src.legibility.value}*\n")
            lines.append(src.text if src.text else "_לא ניתן היה לקרוא_")
        transcript = OUT / f"{case.name} — תמלול.md"
        transcript.write_text("\n".join(lines), encoding="utf-8")

        if any(s.usable for s in sources):
            payload = build_payload(case.name, [], sources)
            tags = [f"# {case.name} — תגיות\n"]
            tags.append("> הופק ללא שכבת חילוץ הסימנים — כל התגיות שליליות.")
            tags.append("> משמש לאימות הצינור בלבד.\n")
            for tag in payload.tags:
                tags.append(explain(tag) + "\n")
            tags.append("\n" + payload.coverage_summary().audit_line())
            (OUT / f"{case.name} — תגיות.md").write_text("\n".join(tags), encoding="utf-8")

        if ask:
            if not open_in_editor(transcript):
                say(f"   (לא הצלחתי לפתוח אוטומטית. הקובץ: {transcript})")
            choice = ask_continue(case.name, len(pending) - index - 1)
            if choice == "stop":
                say(f"\nנעצר לבקשתך. {index + 1} תיקים הושלמו ונשמרו.")
                say("הרצה חוזרת תמשיך מהנקודה הזו בלי לחייב שוב.")
                return
            if choice == "all":
                ask = False
                say("   ממשיך ברצף עד הסוף.")
        say("")

    say(f"הסתיים. התוצאות ב:\n  {OUT}")


if __name__ == "__main__":
    asyncio.run(run())
