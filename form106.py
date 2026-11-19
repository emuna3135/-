"""טופס 106 (אישור שנתי לעובד על שכר וניכויים) כסיכום מהתלושים השמורים. המערכת רק יוצרת קובץ PDF; לא שולחת דבר לאיש.

מקור המבנה: דף השירות הרשמי של רשות המסים, "טופס 106" (gov.il/BlobFolder/service/itc-106/he/Service_Pages_Income_tax_itc106-acc.pdf),
עדכון ינואר 2026. הדף עצמו מציין שהטופס אינו חל על מעסיק שמחשב שכר במערכת ממוחשבת, ולכן אין מבנה חובה למערכת:
כאן נשמרים מספרי הסעיפים והשדות של הטופס הרשמי ורק הסכומים שהמערכת מחשבת מהתלושים.
סכום שאין לו מקור בתלושים לא מומצא: הוא נרשם ברשימת "נדרש טיפול ידני".
פונקציות טהורות, נבדקות בלי FastAPI.
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import payslip as ps
from payslip import visual, _text_r, _text_l, MUTED, LINE, HEAD, INK, W, H, MARGIN, RIGHT, LEFT

SOURCE_URL = "https://www.gov.il/BlobFolder/service/itc-106/he/Service_Pages_Income_tax_itc106-acc.pdf"

# סעיפים בטופס הרשמי שהמערכת אינה קולטת ולכן אינה ממלאת (נדרש טיפול ידני אם קיימים אצל העובד).
NOT_CAPTURED = [
    "חבר קיבוץ/מושב שיתופי",
    "1.5 החזר הוצאות",
    "1.6 שעות נוספות ותשלום על מאמץ מיוחד",
    "1.8–1.9 הטבת סעיף 102",
    "1.10 ביטוח אובדן כושר עבודה",
    "1.11 שכר חייל מיוחד; 1.12 תושבי אילת",
    "2. שכר משמרות בתעשייה",
    "3–5. קצבאות, מענקי פרישה/מוות",
    "6–11. הכנסות לאחר מוות, פטורים לפי סעיף 9(5), ניירות ערך והון",
    "12. תחום עיסוק של עובד זר",
    "14. ניכויים שאושרו על ידי פקיד השומה",
    "15. ביטוח חיים, קצבת שאירים, פנסיה כעצמאי, ניכוי דמי חבר/טיפול",
    "זיכויים נוספים שנתן המעביד, זיכויים שאושרו על ידי פקיד השומה (סעיפים 17–18)",
    "חלק ד: הוצאות ששילם המעביד",
]


def _v(x):
    return x.get("value") if isinstance(x, dict) else x


def _sum(vals):
    """סכום; None אם אחד החודשים חסר (נדרש טיפול ידני) - לא משלימים בניחוש."""
    if any(v is None for v in vals):
        return None
    return round(sum(float(v) for v in vals), 2)


def _latest_by_month(year: int, stubs: list[dict], idn: str) -> dict[int, dict]:
    out = {}
    for s in stubs:                              # תלוש מאוחר באותו חודש דורס (חישוב חוזר)
        if s.get("year") == year and s.get("month") and str(s.get("emp_id_number")) == idn:
            out[int(s["month"])] = s
    return out


def collect(year: int, profile: dict, employees: list[dict], stubs: list[dict]):
    """מחזיר (רשומות לעובד, issues). issue: {level: block|warn, scope, text}."""
    issues = []
    for key, label in (("name", "שם המעביד"), ("file_no", "תיק ניכויים")):
        if not (profile or {}).get(key):
            issues.append({"level": "block", "scope": "מעביד", "text": f"חסר {label}"})
    records = []
    for e in employees:
        idn = str(e["id_number"])
        months = _latest_by_month(year, stubs, idn)
        if not months:
            continue
        ms = [months[m] for m in sorted(months)]
        name = f'{e.get("first_name") or ""} {e.get("family_name") or ""}'.strip() or idn
        scope = f'ת"ז {idn.zfill(9)}'
        taxable = _sum([s.get("taxable") for s in ms])
        gross = _sum([s.get("gross") for s in ms])
        exempt = None if taxable is None or gross is None else round(gross - taxable, 2)
        pts = [s.get("points") for s in ms]
        last_pts = pts[-1] if isinstance(pts[-1], (int, float)) else None
        car = _sum([(s.get("benefits") or {}).get("שווי שימוש ברכב", 0) for s in ms])
        emp = lambda k: _sum([_v((s.get("employer") or {}).get(k)) if (s.get("employer") or {}).get(k) is not None else None
                              for s in ms])
        rec = {
            "id_number": idn.zfill(9), "name": name,
            "address": " ".join(x for x in (e.get("street"), e.get("city")) if x),
            "months": len(months), "months_list": sorted(months),
            "salary": taxable, "exempt": exempt, "car": car or None,
            "study_fund_employer": emp("study_fund"), "pension_employer": emp("pension"),
            "severance_employer": emp("severance"),
            "tax": _sum([s.get("income_tax") for s in ms]),
            "ni": _sum([s.get("national_insurance") for s in ms]),
            "health": _sum([s.get("health") for s in ms]),
            "pension_employee": _sum([s.get("pension_employee") for s in ms]),
            "points": last_pts, "points_varies": len({p for p in pts}) > 1,
        }
        records.append(rec)
        for k, label in (("salary", "משכורת"), ("tax", "מס הכנסה שנוכה"), ("ni", "ביטוח לאומי"),
                         ("health", "מס בריאות"), ("pension_employee", "פנסיה (חלק העובד)")):
            if rec[k] is None:
                issues.append({"level": "block", "scope": scope,
                               "text": f"{label}: בחודש אחד לפחות נדרש טיפול ידני בתלוש; הסכום השנתי לא מחושב"})
        if last_pts is None:
            issues.append({"level": "warn", "scope": scope, "text": "מספר נקודות הזיכוי לא נקבע בתלושים (נדרש טיפול ידני)"})
        elif rec["points_varies"]:
            issues.append({"level": "warn", "scope": scope,
                           "text": "מספר נקודות הזיכוי השתנה במהלך השנה; מוצג הערך של התלוש האחרון"})
        if exempt:
            issues.append({"level": "warn", "scope": scope,
                           "text": f"בתלושים סכום פטור ממס של {exempt:,.2f} ₪ שאינו נכלל במשכורת החייבת; לסווג לסעיף המתאים בטופס (נדרש טיפול ידני)"})
        if not rec["address"]:
            issues.append({"level": "warn", "scope": scope, "text": "חסרה כתובת העובד"})
    if not records:
        issues.append({"level": "block", "scope": "", "text": f"אין תלושים שמורים לשנת {year}"})
    return records, issues


def submittable(issues) -> bool:
    return not any(i["level"] == "block" for i in issues)


def _n(x):
    return "נדרש טיפול ידני" if x is None else f"{float(x):,.2f}"


def _rows(r):
    """(סעיף, תיאור, מספרי שדות בטופס הרשמי, סכום, הערת מקור)"""
    return [
        ("חלק א", "תשלומים", "", None, ""),
        ("1", "משכורת חייבת", "172/158", r["salary"], "סכום השכר החייב במס בתלושים"),
        ("1.1", "הפקדת מעביד לקרן השתלמות", "219/218", r["study_fund_employer"], "לפי התלושים"),
        ("1.2", "הפקדת מעביד לקצבה (פנסיה)", "", r["pension_employer"], "לפי התלושים"),
        ("1.3", "הפקדת מעביד לפיצויים", "", r["severance_employer"], "לפי התלושים"),
        ("1.7", "שווי שימוש ברכב", "", r["car"] if r["car"] else 0.0, "לפי התלושים"),
        ("חלק ב", "ניכויים וזיכויים", "", None, ""),
        ("13", "מס הכנסה שנוכה", "042", r["tax"], "סכום המס בתלושים"),
        ("15", "פנסיה כחבר שכיר (חלק העובד)", "086/045", r["pension_employee"], "לפי התלושים"),
        ("", "ביטוח לאומי שנוכה מהעובד (ללא מס בריאות)", "089/030", r["ni"], "לפי התלושים"),
        ("", "מס בריאות שנוכה", "", r["health"], "לפי התלושים"),
        ("חלק ג", "זיכויים", "", None, ""),
        ("16", "מספר נקודות זיכוי שניתנו", "", r["points"], "נקודות התלוש האחרון בשנה"),
    ]


def _fmt(v):
    if v is None:
        return "נדרש טיפול ידני"
    return f"{float(v):,.2f}"


def render(company: dict, year: int, records: list[dict], draft: bool) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"טופס 106 - {year}")
    for r in records:
        y = H - MARGIN
        _text_r(c, RIGHT, y - 4 * mm, f"טופס 106 - אישור שנתי על שכר וניכויים לשנת המס {year}", "HE-B", 13)
        if draft:
            _text_l(c, LEFT, y - 4 * mm, "טיוטה - חסרים נתונים", "HE-B", 10, MUTED)
        y -= 11 * mm
        c.setFillColor(HEAD)
        c.rect(LEFT, y - 22 * mm, RIGHT - LEFT, 23 * mm, stroke=0, fill=1)
        pairs = [("מעביד", company.get("name")), ("תיק ניכויים", company.get("file_no")),
                 ("עובד", r["name"]), ('ת"ז', r["id_number"]), ("כתובת העובד", r["address"] or "-"),
                 ("חודשי עבודה בשנת המס", str(r["months"]))]
        yy = y - 3 * mm
        for i, (k, v) in enumerate(pairs):
            col = i % 2
            x2 = RIGHT - 2 * mm - col * (RIGHT - LEFT) / 2
            row = i // 2
            _text_r(c, x2, yy - row * 7 * mm, k, "HE", 8, MUTED)
            _text_r(c, x2 - 30 * mm, yy - row * 7 * mm, str(v or "-"), "HE-B", 8.5)
        y -= 26 * mm
        # כותרת עמודות
        cols = [RIGHT, RIGHT - 14 * mm, RIGHT - 92 * mm, RIGHT - 118 * mm, RIGHT - 150 * mm]
        for x, t in zip(cols, ["סעיף", "תיאור", "שדה", "סכום", "מקור"]):
            _text_r(c, x - 2 * mm, y - 3 * mm, t, "HE-B", 7.5, MUTED)
        y -= 5 * mm
        c.setStrokeColor(LINE)
        c.line(LEFT, y + 1 * mm, RIGHT, y + 1 * mm)
        for sec, label, fields, amount, note in _rows(r):
            header = amount is None and note == ""
            if header:
                c.setFillColor(HEAD)
                c.rect(LEFT, y - 4.2 * mm, RIGHT - LEFT, 5.6 * mm, stroke=0, fill=1)
                _text_r(c, cols[0] - 2 * mm, y - 2.6 * mm, sec, "HE-B", 8.5)
                _text_r(c, cols[1] - 2 * mm, y - 2.6 * mm, label, "HE-B", 8.5)
                y -= 7 * mm
                continue
            _text_r(c, cols[0] - 2 * mm, y - 3 * mm, sec, "HE", 8.5)
            _text_r(c, cols[1] - 2 * mm, y - 3 * mm, label, "HE", 8.5)
            _text_r(c, cols[2] - 2 * mm, y - 3 * mm, fields or "-", "HE", 8.5, MUTED)
            val = _fmt(amount) if not (sec == "16") else ("נדרש טיפול ידני" if amount is None else f"{amount:g}")
            _text_r(c, cols[3] - 2 * mm, y - 3 * mm, val, "HE-B", 8.5)
            _text_r(c, cols[4] - 2 * mm, y - 3 * mm, note, "HE", 7.5, MUTED)
            y -= 5.5 * mm
            c.line(LEFT, y + 1.5 * mm, RIGHT, y + 1.5 * mm)
        y -= 4 * mm
        _text_r(c, RIGHT, y, "סעיפים בטופס הרשמי שהמערכת אינה מחשבת (נדרש טיפול ידני אם קיימים אצל העובד):", "HE-B", 8)
        y -= 5 * mm
        for t in NOT_CAPTURED:
            _text_r(c, RIGHT - 3 * mm, y, "• " + t, "HE", 7.5, MUTED)
            y -= 4.2 * mm
        y -= 6 * mm
        _text_r(c, RIGHT, y, "הצהרת המעביד: שם ___________   תפקיד ___________   תאריך ___________   חתימה וחותמת ___________", "HE", 8)
        y -= 7 * mm
        _text_r(c, RIGHT, y, "הצהרת העובד: תאריך ___________   חתימה ___________", "HE", 8)
        _text_r(c, RIGHT, MARGIN, "הופק אוטומטית מהתלושים לבדיקת חשבת השכר. המערכת אינה שולחת דבר לרשות המסים. מבנה הסעיפים לפי טופס 106 של רשות המסים (עדכון 1/2026).",
                "HE", 6.5, MUTED)
        c.showPage()
    c.save()
    return buf.getvalue()


def run(profile: dict, year: int, employees: list[dict], stubs: list[dict]):
    """מחזיר (pdf בייטים, issues, מספר עובדים, submittable). מסתיר ת"ז מלאה בהודעות."""
    records, issues = collect(year, profile, employees, stubs)
    data = render(profile or {}, year, records, draft=not submittable(issues)) if records else b""
    import re
    safe = [{**i, "scope": re.sub(r"ת\"ז (\d{5})(\d{4})", r'ת"ז *****\2', i["scope"])} for i in issues]
    return data, safe, len(records), submittable(issues)
