# 🔍 HuriS — מפת פערים בין שלושת הסוכנים

**תאריך:** 25 ביולי 2026
**בסיס:** INTERFACES v1.3 · RuleBook A v0.8 · RuleBook B v1.21 · Guardrails C v1.0 · AgentC_Output_Schema.json v1.0
**מטרה:** לזהות כל מקום שבו סוכן אחד מייצר משהו שסוכן אחר לא מצפה לו — לפני שכותבים קוד.

---

## סיכום מנהלים

נבדקו 41 קבצים בשלוש התיקיות. נמצאו **3 פערים חוסמים**, **2 בעיות שלמות מסמכים**, ו-**3 אי-התאמות קלות**.

הפער החמור ביותר: **מנגנון "רצפת האדום" של סוכן ג' נשען על ציר שאף סוכן לא מייצר.**

---

## 🔴 פערים חוסמים (חייבים הכרעה לפני קוד)

### פער 1 — סוכן ג' מצפה ל-9 קונסטרוקטים, סוכן א' מייצר 7

**מה שיש:**

| מקור | קונסטרוקטים |
|---|---|
| INTERFACES §2 + RuleBook A | 7 תגיות |
| AgentC_Output_Schema.json (enum) | 9 קונסטרוקטים |

**שני העודפים אצל סוכן ג':**

- `reliability_transparency`
- `personal_responsibility`

**למה זה חוסם:** Guardrails §3 מגדיר
`CORE_AXES = {authority_conflict, boundary_blurring, vulnerability_crisis, reliability_transparency}`

כלומר `reliability_transparency` הוא **ציר-ליבה** שקובע אם תיק יכול לקבל דירוג אדום (מעקה G3, "רצפת האדום"). אבל שום מסמך לא מגדיר מי מייצר אותו ואיך.

ב-Guardrails מופיע לידו הרמז `(הצלבה)` — כלומר הוא כנראה נגזר מהצלבת קובץ מול ראיון. אבל זו הערה, לא מפרט.

**מה שצריך להכריע:**

1. מי מייצר את `reliability_transparency` — סוכן א', סוכן ב', או שסוכן ג' גוזר אותו בעצמו?
2. אותה שאלה ל-`personal_responsibility`.
3. אם סוכן ג' גוזר אותם — לפי איזה כלל בדיוק?

---

### פער 2 — אין תרגום מוגדר בין פורמט סוכן א' לפורמט סוכן ג'

**סוכן א' מייצר** (INTERFACES §4b):

```
TAG: <שם>
value: True | False | Unknown
confidence: high | medium | low
```

**סוכן ג' מצפה ל-** (Output_Schema, findings[]):

```json
{
  "construct": "...",
  "relation_type": "confirm | contradict | single_source",
  "sources": ["file" | "interview" | "cross"],
  "strength": "weak | medium | strong",
  "blacklisted": bool,
  "statistical": bool,
  "explained": bool,
  "quote": "..."
}
```

**הבעיה:** אין שדה `value` אצל סוכן ג', ואין שדה `strength` אצל סוכן א'. הפונקציה שממירה
`(value, confidence)` → `(relation_type, strength)` **לא מוגדרת בשום מקום**.

**מה שצריך להכריע:** האם המיפוי הוא:

| סוכן א' | → סוכן ג' (הצעה לאישור) |
|---|---|
| value=True, confidence=high | strength=strong |
| value=True, confidence=medium | strength=medium |
| value=True, confidence=low | strength=weak |
| value=False | לא נוצר finding כלל |
| value=Unknown | לא נוצר finding; משפיע על `basis`/`force_analyze` |

זו הצעה שלי — **צריכה את אישורך**, כי היא משנה תוצאות.

---

### פער 3 — `quote` מילולי נדרש, אבל סוכן א' לא מחויב לשמור אותו

Output_Schema מגדיר `quote` כשדה **required** בכל finding: "Verbatim excerpt from source".

מעקה G0 בודק התאמה בין ה-`quote` למונחי ה-blacklist — כלומר ה-quote הוא בסיס לאכיפה, לא קישוט.

RuleBook A מגדיר `signs_found[{marker_id, ציטוט מילולי, שם_מקור}]` — כלומר הציטוט **כן** נשמר אצל סוכן א'. אבל INTERFACES §2 קובע במפורש שסוכן א' מעביר לסוכן ב' **רק T/F, בלי ציטוטים**.

**מה שצריך להכריע:** האם סוכן ג' מקבל את `signs_found` המלא מסוכן א' (כולל ציטוטים), או שהוא מחלץ ציטוטים מחדש מהתיק הגולמי? INTERFACES §4a אומר שהוא מקבל את התיק הגולמי — אז אולי הוא מחלץ בעצמו. אבל אז יכולים להיווצר ציטוטים שונים מאלה של סוכן א', והמערכת תסתור את עצמה.

---

## 🟡 בעיות שלמות מסמכים

### בעיה 4 — INTERFACES v1.3 בתיקיית סוכן ג' ריק

המסמך עצמו מזהיר: *"כל סנכרון קריטי... אם מסמך זה בתיקייה אחת שונה מהאחרות — יש drift."*

| תיקייה | מצב |
|---|---|
| סוכן א' | ✅ מלא (6 פרקים) |
| סוכן ב' | ✅ מלא — זהה בייט-לבייט לסוכן א' |
| סוכן ג' | ❌ **רק כותרת ושורת גרסה. כל הגוף חסר.** |

**המשמעות:** סוכן ג' — הצרכן של שני האחרים — עובד ללא החוזה שמגדיר מה הוא מקבל.

**תיקון:** להעתיק את הגרסה המלאה לתיקיית סוכן ג'.

### בעיה 5 — `DecisionSpec_AgentC_schema.md` ריק גם הוא

מכיל רק: *"גרסה: v0.1 (סכמה נקייה מ-DecisionSpec) מטרה: תיאור מובנה של הקלט, העיבוד, והפלט של סוכן ג'."*

בפועל התוכן האמיתי נמצא ב-`HuriS_AgentC_Output_Schema.json` — שהוא **מצוין ומלא**. הקובץ ה-MD מיותר או שצריך למלא אותו.

---

## 🟢 אי-התאמות קלות

### 6 — הגדרת PATTERN_NOTE שונה בין המסמכים

| מקור | תנאי |
|---|---|
| INTERFACES §5 | ≥3 עוגנים מתכנסים |
| Output_Schema | "≥3 anchors converge **או** 2+ on core axes" |

התנאי השני רחב יותר. צריך לבחור אחד.

### 7 — קבצים במיקום שגוי

בתיקיית **סוכן א'** יושבים שני קבצים של סוכן ג':

- `HuriS_AgentC_Kickoff.md`
- `HuriS_AgentC_existing_draft.md`

שניהם קיימים גם בתיקיית סוכן ג'. הכפילות עלולה ליצור עריכה של העותק הלא-נכון.

### 8 — גרסאות מיושנות שכדאי לארכב

| קובץ | סטטוס |
|---|---|
| `HuriS_INTERFACES_master_v1_2.md` | מוחלף ע"י v1.3 |
| `HuriS_RuleBook_AgentA_v0_7.md` | מוחלף ע"י v0.8 |
| `HuriS_RuleBook_AgentB_v1_1.md` | מוחלף ע"י v1.21 |
| `Appendix_A_QuickReference_for_AgentA.md` (בתיקיית ב') | מוחלף ע"י v1.16 |

---

## מה שנבדק ונמצא תקין ✅

- **מנגנון confidence אחיד** — סוכן א' ו-INTERFACES מסכימים: True: 1/2/≥3 → low/med/high; False ו-Unknown → low.
- **הפרדת confidence מ-color** — Guardrails S3 אוכף שהם בלתי-תלויים. עקבי עם INTERFACES §4b.
- **Unknown ≠ False** — מוגדר זהה בשלושת המסמכים. סוכן א' מבחין; סוכן ב' ממפה Unknown ל-False במכוון; סוכן ג' מקבל את ההבחנה המלאה.
- **`terminated_safety` → תמיד אדום** — עקבי בין Output_Schema, Guardrails S9 ו-RuleBook B.
- **טבלת המשקלים** — זהה בין INTERFACES §2 ל-RuleBook B: `effective_weight = base_weight × (2.0 אם True, 0.5 אם False)`.

---

## החלטות שממתינות לך

| # | ההחלטה | חוסם את |
|---|---|---|
| 1 | מי מייצר `reliability_transparency` ו-`personal_responsibility`? | קוד סוכן ג' (מעקה G3) |
| 2 | אישור טבלת המיפוי (value, confidence) → strength | קוד האינטגרציה |
| 3 | האם סוכן ג' מקבל ציטוטים מסוכן א' או מחלץ בעצמו? | קוד סוכן א' + ג' |
| 4 | PATTERN_NOTE — ≥3 בלבד, או גם 2+ על צירי ליבה? | קוד סוכן ג' |

**עד שיוכרעו 1–3, אפשר להתקדם עם:** נעילת הסכמות המשותפות, קוד סוכן א' (עצמאי לחלוטין), ומעקות G0/G1/G2/G4 של סוכן ג' (לא תלויים בפערים).

---

*הופק אוטומטית מקריאת המקורות בדרייב. כל טענה כאן ניתנת לאימות מול הקובץ שצוין.*
