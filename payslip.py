"""
הפקת תלוש שכר ב-PDF (עברית, ימין לשמאל) מתוצאת החישוב של המנוע.
רשימת השדות החובה נלקחה מכל-זכות (סיכום חוק הגנת השכר) ולא מנוסח החוק עצמו -
לפני שימוש מסחרי חובה לאמת אותה מול נוסח החוק והתקנות.
נוסח התוספת לחוק (נבו 07.11.2025) התקבל ונבדק ב-DATA_LEDGER.md סעיף ב11 - REQUIRED כאן חסר בו שדות; ממתין לסיום האימות.
"""
import io
import os
import unicodedata
from datetime import date
from engine import BY_LAW

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
pdfmetrics.registerFont(TTFont("HE", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("HE-B", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))


# ---------------------------------------------------------------------------
# סדר תצוגה ימין-לשמאל (אלגוריתם בסיסי: עברית + מספרים + לטינית + סימני פיסוק)
# ---------------------------------------------------------------------------
_MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "<": ">", ">": "<"}


def _kind(ch):
    b = unicodedata.bidirectional(ch)
    if b in ("R", "AL"):
        return "R"
    if b in ("L", "EN", "AN"):
        return "L"
    return "N"


def visual(text: str) -> str:
    """ממיר מחרוזת לוגית לסדר תצוגה (לציור משמאל לימין). מספרים ולטינית נשארים בכיוון שלהם."""
    text = str(text)
    if not text:
        return text
    kinds = [_kind(c) for c in text]
    if "R" not in kinds:
        return text  # אין עברית - נשאר כמו שהוא
    # סימנים ניטרליים בין שתי ריצות LTR (למשל 1,234.56 או 12/2025) נשארים חלק מהריצה
    for i, c in enumerate(text):
        if kinds[i] == "N" and c in ",.:/-+%" and 0 < i < len(text) - 1:
            if kinds[i - 1] == "L" and kinds[i + 1] == "L":
                kinds[i] = "L"
    # אחוז צמוד למספר שלפניו נשאר איתו
    for i, c in enumerate(text):
        if c == "%" and i > 0 and kinds[i - 1] == "L":
            kinds[i] = "L"
    # ניטרליים אחרים לוקחים את כיוון הבסיס (RTL)
    runs, cur, cur_k = [], "", None
    for c, k in zip(text, kinds):
        k = "R" if k == "N" else k
        if k != cur_k and cur:
            runs.append((cur_k, cur))
            cur = ""
        cur_k = k
        cur += c
    runs.append((cur_k, cur))
    out = []
    for k, s in reversed(runs):
        if k == "R":
            s = "".join(_MIRROR.get(ch, ch) for ch in reversed(s))
        out.append(s)
    return "".join(out)


# ---------------------------------------------------------------------------
# שכר מינימום (נגזר מתלושי משרד החינוך 2026). תקופות אחרות לא מאומתות -> חסר.
# ---------------------------------------------------------------------------
MIN_WAGE = [  # (מתחיל מ-(שנה, חודש), חודשי, שעתי)
    # ינואר-מרץ 2025 (בתוקף מ-1.4.2024): 5,880.02 חודשי; שעתי 32.30 ל-182 שעות (31.61 ל-186). מקור: דף שכר מינימום של הביטוח לאומי, נקרא במלואו 15.11.2026 (תוקן מ-32.31).
    ((2025, 1), "5880.02", "32.30"),
    # מ-1.4.2025: 6,247.67 חודשי; שעתי 34.32 (182 שעות; 33.58 ל-186). מקור: דף שכר מינימום של המוסד לביטוח לאומי (btl.gov.il), נבדק 12.11.2026.
    ((2025, 4), "6247.67", "34.32"),
    # חודשי 6,443.85 מאומת: ילקוט הפרסומים 14324, 4.3.2026, עמ' 4496 + דף ביטוח לאומי. שעתי 35.40 (182 שעות; 34.64 ל-186): דף ביטוח לאומי; תואם תלוש מעסיק 10/2026.
    ((2026, 4), "6443.85", "35.40"),
]
# הערה: חוק שכר מינימום §1 קובע שעתי = חודשי/186 (ב"ל מפרסם גם 186: 33.58 / 34.64). כאן בסיס 182 לפי תלוש המעסיק; הבסיס הנכון לתלוש (182 מול 186) טרם הוכרע - שאלה לחשב השכר.
MIN_WAGE_VERIFIED_FROM = (2025, 1)


def min_wage(year, month):
    if (year, month) < MIN_WAGE_VERIFIED_FROM:
        return None
    best = None
    for start, m, h in MIN_WAGE:
        if (year, month) >= start:
            best = (m, h)
    return best


REQUIRED = [  # (מפתח, תיאור) - לפי כל-זכות. נבדק בפונקציה missing_fields
    ("employer_name", "שם המעסיק"),
    ("employer_id", "מספר חברה/ת.ז של המעסיק"),
    ("employer_address", "כתובת מקום העבודה/העסק"),
    ("employee_name", "שם העובד"),
    ("employee_id", "ת.ז העובד"),
    ("start_date", "תאריך תחילת עבודה"),
    ("seniority", "ותק מצטבר"),
    ("regular_hour_value", "ערך שעת עבודה רגילה"),
    ("cum_ni_base", "שכר חייב בביטוח לאומי מצטבר"),
    ("position_scope", "היקף משרה"),
    ("worked", "שעות/ימי עבודה בחודש"),
    ("vacation", "ימי חופשה: ניצול ויתרה"),
    ("sick", "ימי מחלה: ניצול ויתרה"),
    ("min_wage", "שכר מינימום לחודש ולשעה לתקופה"),
    ("payment", "אופן תשלום / פרטי חשבון בנק"),
]


def missing_fields(d: dict):
    miss = [label for key, label in REQUIRED if d.get(key) in (None, "", {})]
    return miss


def seniority(start_date, year, month):
    """ותק בחברה מתאריך תחילת העבודה ועד סוף חודש התלוש ('X שנים Y חודשים'). חסר/לא תקין -> None.
    הערה: סעיף 24 מחייב ותק מצטבר גם אצל מעסיק קודם באותו מקום עבודה; זה נמסר ב-seniority_override."""
    import datetime, calendar
    try:
        sd = start_date if isinstance(start_date, datetime.date) else datetime.date.fromisoformat(start_date)
    except (TypeError, ValueError):
        return None
    end = datetime.date(year, month, calendar.monthrange(year, month)[1])
    if sd > end:
        return None
    months = (end.year - sd.year) * 12 + (end.month - sd.month)
    if end.day < sd.day:
        months -= 1
    return f"{months // 12} שנים {months % 12} חודשים"


def n2(x):
    return f"{float(x):,.2f}"


# ---------------------------------------------------------------------------
# ציור
# ---------------------------------------------------------------------------
W, H = A4
MARGIN = 14 * mm
RIGHT = W - MARGIN
LEFT = MARGIN
INK = colors.HexColor("#1b2733")
MUTED = colors.HexColor("#5b6b7a")
LINE = colors.HexColor("#c9d3dc")
HEAD = colors.HexColor("#e8eef3")


def _text_r(c, x, y, s, font="HE", size=9, color=INK):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawRightString(x, y, visual(s))


def _text_l(c, x, y, s, font="HE", size=9, color=INK):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y, visual(s))


def _box_title(c, x1, x2, y, title):
    c.setFillColor(HEAD)
    c.rect(x1, y - 5.5 * mm, x2 - x1, 6 * mm, stroke=0, fill=1)
    _text_r(c, x2 - 2 * mm, y - 3.6 * mm, title, "HE-B", 9)
    return y - 7 * mm


def _kv(c, x1, x2, y, pairs):
    """שורות 'כותרת: ערך' בתוך תיבה. הכותרת בימין, הערך משמאלה."""
    y -= 1.5 * mm
    for k, v in pairs:
        _text_r(c, x2 - 2 * mm, y, k, "HE", 8, MUTED)
        _text_r(c, x2 - 38 * mm, y, v if v not in (None, "") else "-", "HE", 8.5)
        y -= 4.6 * mm
    return y


def _table(c, y, title, headers, rows, widths, total=None):
    """טבלה: העמודה הראשונה בימין. headers/rows לפי סדר קריאה (ימין לשמאל)."""
    x2 = RIGHT
    c.setFillColor(HEAD)
    c.rect(LEFT, y - 5.5 * mm, RIGHT - LEFT, 6 * mm, stroke=0, fill=1)
    _text_r(c, x2 - 2 * mm, y - 3.6 * mm, title, "HE-B", 9)
    y -= 7 * mm
    xs, x = [], x2
    for w in widths:
        xs.append(x)
        x -= w
    for hx, h in zip(xs, headers):
        _text_r(c, hx - 2 * mm, y - 3 * mm, h, "HE-B", 7.5, MUTED)
    y -= 5 * mm
    c.setStrokeColor(LINE)
    c.line(LEFT, y + 1 * mm, RIGHT, y + 1 * mm)
    for r in rows:
        for i, (hx, v) in enumerate(zip(xs, r)):
            if i == 0:
                _text_r(c, hx - 2 * mm, y - 3 * mm, v, "HE", 8.5)
            else:
                # מספרים מיושרים לקצה השמאלי של העמודה
                _text_r(c, hx - 2 * mm, y - 3 * mm, v, "HE", 8.5)
        y -= 5 * mm
    if total:
        c.setStrokeColor(INK)
        c.line(LEFT, y + 1.5 * mm, RIGHT, y + 1.5 * mm)
        for i, (hx, v) in enumerate(zip(xs, total)):
            _text_r(c, hx - 2 * mm, y - 3 * mm, v, "HE-B", 9)
        y -= 6 * mm
    return y - 3 * mm


def build(d: dict, draft: bool) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("תלוש שכר")
    y = H - MARGIN

    _text_r(c, RIGHT, y - 4 * mm, f"תלוש שכר לחודש {d['month']:02d}/{d['year']}", "HE-B", 15)
    _text_l(c, LEFT, y - 4 * mm, "הופק בחשבות בקליק", "HE", 7, MUTED)
    y -= 12 * mm

    # שתי תיבות: מעסיק (ימין) ועובד (שמאל)
    mid = (LEFT + RIGHT) / 2
    top = y
    yy = _box_title(c, mid + 2 * mm, RIGHT, top, "פרטי המעסיק")
    _kv(c, mid, RIGHT, yy, [("שם", d.get("employer_name")), ("מספר חברה/ת.ז", d.get("employer_id")),
                            ("כתובת", d.get("employer_address"))])
    yy = _box_title(c, LEFT, mid - 2 * mm, top, "פרטי העובד")
    _kv(c, LEFT, mid - 2 * mm, yy, [("שם", d.get("employee_name")), ("ת.ז", d.get("employee_id_masked")),
                                    ("תחילת עבודה", d.get("start_date"))])
    y = top - 24 * mm

    # פרטי העסקה ונוכחות
    mw = d.get("min_wage")
    rhv = d.get("regular_hour_value")
    work = [("היקף משרה", d.get("position_scope")), ("עבודה בחודש", d.get("worked")),
            ("ותק", d.get("seniority")), ("ערך שעת עבודה רגילה", n2(rhv) if rhv else None),
            ("שכר מינימום (חודשי/שעתי)", f"{n2(mw[0])} / {n2(mw[1])}" if mw else None)]
    leave = [("חופשה (ניצול/יתרה)", d.get("vacation")), ("מחלה (ניצול/יתרה)", d.get("sick")),
             ("אופן תשלום", d.get("payment"))]
    top = y
    yy = _box_title(c, mid + 2 * mm, RIGHT, top, "פרטי העסקה")
    _kv(c, mid, RIGHT, yy, work)
    yy = _box_title(c, LEFT, mid - 2 * mm, top, "חופשה ותשלום")
    _kv(c, LEFT, mid - 2 * mm, yy, leave)
    y = top - 34 * mm

    # תשלומים
    pay_rows = []
    for label, amount in d["payments"]:
        pay_rows.append((label, n2(amount)))
    y = _table(c, y, "תשלומים", ["תיאור", "סכום"], pay_rows, [120 * mm, 62 * mm],
               total=("סה\"כ ברוטו", n2(d["gross"])))

    # נתונים מצטברים
    y = _table(c, y, "נתוני מס", ["תיאור", "החודש", "מצטבר מתחילת השנה"],
               [("הכנסה חייבת במס", n2(d["taxable"]), n2(d["cum_taxable"])),
                ("מס הכנסה שנוכה", n2(d["tax"]), n2(d["cum_tax"])),
                ("שכר חייב בביטוח לאומי", n2(d["ni_base"]),
                 n2(d["cum_ni_base"]) if d.get("cum_ni_base") is not None else "-"),
                ("נקודות זיכוי", f"{d['points']}", "-")],
               [70 * mm, 52 * mm, 60 * mm])

    # ניכויים
    ded_rows = [(label, rate, n2(amount)) for label, rate, amount in d["deductions"]]
    y = _table(c, y, "ניכויי חובה ורשות", ["תיאור", "שיעור", "סכום"], ded_rows,
               [90 * mm, 40 * mm, 52 * mm], total=("סה\"כ ניכויים", "", n2(d["total_deductions"])))

    # הפרשות מעסיק
    if d["employer"]:
        er = [(label, base, n2(amount)) for label, base, amount in d["employer"]]
        y = _table(c, y, "הפרשות המעסיק", ["תיאור", "על שכר של", "סכום"], er,
                   [90 * mm, 40 * mm, 52 * mm])

    # נטו
    c.setFillColor(INK)
    c.rect(LEFT, y - 11 * mm, RIGHT - LEFT, 11 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("HE-B", 12)
    c.drawRightString(RIGHT - 3 * mm, y - 7.5 * mm, visual("נטו לתשלום"))
    c.drawString(LEFT + 3 * mm, y - 7.5 * mm, n2(d["net"]))
    y -= 16 * mm

    for note in d.get("notes", []):
        _text_r(c, RIGHT, y, note, "HE", 7, MUTED)
        y -= 3.6 * mm

    if draft:
        c.saveState()
        c.setFillColor(colors.Color(0.85, 0.1, 0.1, alpha=0.16))
        c.setFont("HE-B", 44)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, visual("טיוטה - לא לחלוקה"))
        c.restoreState()
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# מתוצאת החישוב + פרטים נוספים -> נתוני תלוש
# ---------------------------------------------------------------------------
def prepare(res: dict, extras: dict, employee: dict, company: dict):
    """
    res: מה ש-compute() החזיר ונשמר (כולל items/employer).
    employee: כרטיס העובד המפוענח. company: {'name','tax_id'}.
    מחזיר (data, missing, draft_reasons).
    """
    year, month = res["year"], res["month"]
    mw = min_wage(year, month)
    d = {
        "year": year, "month": month,
        "employer_name": company.get("name"), "employer_id": company.get("tax_id"),
        "employer_address": extras.get("employer_address"),
        "employee_name": employee["full_name"],
        "employee_id_masked": "*****" + employee["id_number"][-4:],
        "employee_id": employee["id_number"],
        "start_date": employee.get("start_date"),
        "position_scope": f"{employee.get('position_scope_percent', 100):g}%",
        "worked": extras.get("worked"),
        "vacation": extras.get("vacation"), "sick": extras.get("sick"),
        "min_wage": mw,
        "payment": extras.get("payment") or ("העברה בנקאית" if employee.get("bank_account") else None),
        "gross": res["gross"], "taxable": res.get("taxable", res["gross"]),
        "cum_taxable": res.get("cumulative_taxable", 0), "cum_tax": res.get("cumulative_tax", 0),
        "points": extras.get("points_display", res.get("points", "-")), "tax": res["income_tax"] or 0,
        "ni_base": res["gross"], "cum_ni_base": res.get("cumulative_ni_base"),
        "regular_hour_value": extras.get("regular_hour_value"),
        "seniority": extras.get("seniority_override") or seniority(employee.get("start_date"), year, month),
    }
    benefits = res.get("benefits", {})
    noncash = sum(benefits.values())
    pay = [("שכר יסוד", res["gross"] - noncash - res.get("overtime_pay", 0) - extras.get("bonus", 0))]
    for label, value in benefits.items():
        pay.append((label + " (זקיפה, לא משולם)", value))
    if res.get("overtime_pay"):
        pay.append(("שעות נוספות", res["overtime_pay"]))
    if extras.get("bonus"):
        pay.append(("בונוס", extras["bonus"]))
    d["payments"] = pay
    items = res["items"]
    ded = []
    for key, label in [("income_tax", "מס הכנסה"), ("national_insurance", "ביטוח לאומי"),
                       ("health", "ביטוח בריאות"), ("pension_employee", "פנסיה - עובד"),
                       ("study_fund_employee", "קרן השתלמות - עובד")]:
        v = items[key]["value"]
        # מס הכנסה, ביטוח לאומי ובריאות מוצגים תמיד (חובה לפרט), השאר רק אם יש סכום
        if v or key in ("income_tax", "national_insurance", "health"):
            ded.append((label, "", v or 0))
    if noncash:
        ded.append(("ניכוי זקיפת שווי הטבות", "", noncash))
    total = sum(x[2] for x in ded)
    d["deductions"] = ded
    d["total_deductions"] = total
    d["net"] = res["net"] if res["net"] is not None else res["gross"] - total
    base = res.get("pension_base", res["gross"])
    d["employer"] = [(lbl, n2(base), res["employer"][k]) for k, lbl in
                     [("pension", "פנסיה - מעסיק"), ("severance", "פיצויים - מעסיק"),
                      ("study_fund", "קרן השתלמות - מעסיק")] if res.get("employer", {}).get(k)]
    d["notes"] = ["התלוש הופק במערכת. בכל שאלה יש לפנות למעסיק או לחשב השכר."]
    miss = missing_fields(d)
    reasons = []
    if res["overall_status"] != BY_LAW:
        reasons.append(f"סטטוס החישוב: {res['overall_status']}")
    if res.get("unresolved"):
        reasons.append("חסרים רכיבי חישוב")
    return d, miss, reasons


def render(res, extras, employee, company, approved=False):
    d, miss, reasons = prepare(res, extras, employee, company)
    draft = bool(miss or reasons) and not (approved and not miss and res.get("net") is not None)
    return build(d, draft), miss, reasons, draft
