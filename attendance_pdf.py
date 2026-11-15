"""
קורא דוח "כרטיס עובד" (דוח נוכחות, Stimulsoft) ב-PDF.
עיקרון: שום נתון לא נשמט בשקט. כל מילה בגוף השורות שלא זוהתה נכנסת ל-warnings, ושעות נבדקות מול שורת הסיכום של הדוח.
שעות בדוח הן hh:mm; כאן הן מומרות לדקות שלמות (ללא עיגול) ורק בסוף לשעות עשרוניות.
העמודות מזוהות לפי מיקום אופקי של כותרות הדוח (לא לפי מיקום קבוע), ולכן סטייה קלה בפריסה לא שוברת את הקריאה.
מוגבל: נבדק על פריסה אחת (דוח עם שעות רגילות בלבד). עמודות שעות נוספות והעדרות מזוהות לפי הכותרות אך לא נבדקו על נתונים אמיתיים.
"""
import re
from decimal import Decimal

TIME_RE = re.compile(r"^\d{1,3}:\d{2}$")
DATE_RE = re.compile(r"^(\d{2})/(\d{2})$")
FULL_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
ID_RE = re.compile(r"^\d{9}$")
OT_RATES = ("100", "125", "150", "200", "225", "250")


def to_minutes(t):
    h, m = t.split(":")
    if int(m) > 59:
        raise ValueError(f"דקות לא תקינות: {t}")
    return int(h) * 60 + int(m)


def hours_decimal(minutes):
    return (Decimal(minutes) / Decimal(60)).quantize(Decimal("0.0001"))


def _cx(w):
    return (w["x0"] + w["x1"]) / 2


def _nearest(columns, x, tol=18):
    best = min(columns.items(), key=lambda kv: abs(kv[1] - x))
    return best[0] if abs(best[1] - x) <= tol else None


def parse_words(words):
    """words: רשימת dict עם text, x0, x1, top (כמו pdfplumber.extract_words). מחזיר מבנה מפורש + warnings."""
    warnings = []
    # --- כותרות עמודות (אזור הכותרת: בין שורת "מיון" לשורת הנתונים הראשונה)
    first_date = min((w["top"] for w in words if DATE_RE.match(w["text"]) and w["x0"] > 540), default=None)
    if first_date is None:
        raise ValueError("לא נמצאו שורות תאריך בדוח: זה לא דוח כרטיס עובד בפריסה הנתמכת")
    header = [w for w in words if 80 <= w["top"] < first_date - 3]
    cols = {}
    for w in header:
        m = re.match(r"^\.?(\d{3})%\.?$", w["text"])
        if m and m.group(1) in OT_RATES:
            cols["ot" + m.group(1)] = _cx(w)
    # עמודות לפי טקסט הכותרת (העברית נשלפת הפוכה מה-PDF: משווים לשני הכיוונים)
    def hdr(*labels):
        for w in header:
            t = w["text"]
            if t in labels or t[::-1] in labels:
                return _cx(w)
        return None
    for key, labels in (("regular", ("ש.רגילו", "ש.רגילות")), ("total", ('סה"כ',)),
                        ("exit", ("יציאה",)), ("entry", ("כניסה",)), ("code", ("קוד",))):
        x = hdr(*labels)
        if x is None:
            raise ValueError(f"לא נמצאה כותרת העמודה '{labels[0]}'")
        cols[key] = x
    # --- פרטי כרטיס
    top = [w for w in words if w["top"] < first_date - 3]
    ids = [w["text"] for w in top if ID_RE.match(w["text"])]
    # תאריך ההדפסה בראש הדף (top<30) אינו תקופת הדוח
    dates = [w["text"] for w in sorted(top, key=lambda w: w["top"]) if FULL_DATE_RE.match(w["text"]) and w["top"] > 30]
    pct = [w for w in top if w["text"].isdigit() and len(w["text"]) <= 3 and 60 < w["top"] < 70]
    id_number = ids[0] if ids else None
    period = (dates[0], dates[1]) if len(dates) >= 2 else (None, None)
    # --- שורות לפי תאריך
    date_words = sorted((w for w in words if DATE_RE.match(w["text"]) and w["x0"] > 540 and w["top"] >= first_date - 1),
                        key=lambda w: w["top"])
    # גבול גוף הטבלה: שורת "סיכום" נמצאת מתחת לתאריך האחרון, ושם לא נחפש ימים
    last_row = date_words[-1]["top"]
    body_bottom = last_row + 12
    days = {}
    order = []
    claimed = set()
    for dw in date_words:
        key = dw["text"]
        rowwords = [w for w in words if abs(w["top"] - dw["top"]) <= 4 and w is not dw and w["x0"] < dw["x0"]]
        rec = days.setdefault(key, {"date": key, "total_min": 0, "regular_min": 0, "entries": [], "exits": [],
                                    "overtime_min": {r: 0 for r in OT_RATES}, "other": [], "day_type": None})
        if key not in order:
            order.append(key)
        for w in rowwords:
            claimed.add(id(w))
            t = w["text"]
            if TIME_RE.match(t):
                c = _nearest({k: v for k, v in cols.items() if k not in ("code",)}, _cx(w))
                if c == "total":
                    rec["total_min"] += to_minutes(t)
                elif c == "regular":
                    rec["regular_min"] += to_minutes(t)
                elif c == "entry":
                    rec["entries"].append(t)
                elif c == "exit":
                    rec["exits"].append(t)
                elif c and c.startswith("ot"):
                    rec["overtime_min"][c[2:]] += to_minutes(t)
                else:
                    rec["other"].append(t)
                    warnings.append(f"{key}: שעה {t} בעמודה שלא זוהתה ולא נספרה")
            elif _nearest(cols, _cx(w), 30) == "code" and re.match(r"^\d+$", t):
                rec["other"].append(t)
                warnings.append(f"{key}: קוד העדרות/חריג '{t}' אינו מטופל: נדרשת בדיקה ידנית")
            else:
                if rec["day_type"] is None and w["x0"] > 480:
                    rec["day_type"] = t[::-1] if any("֐" <= ch <= "׿" for ch in t) else t
    # --- בדיקה פנימית: מ-כניסה ליציאה מול סה"כ נוכחות (הדוח עוטף משמרת על פני שתי שורות)
    out_days = []
    for key in order:
        d = days[key]
        ent = sorted(d["entries"], key=to_minutes)
        ext = sorted(d["exits"], key=to_minutes)
        check = None
        if ent and ext and d["total_min"]:
            span = to_minutes(ext[-1]) - to_minutes(ent[0])
            check = span == d["total_min"]
            if not check:
                warnings.append(f"{key}: יציאה פחות כניסה ({span} דק') שונה מסה\"כ נוכחות ({d['total_min']} דק'): נדרשת בדיקה")
        if bool(ent) != bool(ext) or (ent and ext and not d["total_min"]):
            warnings.append(f"{key}: כניסה/יציאה חסרה או יום פתוח, ללא סה\"כ נוכחות: לא נספר, נדרשת בדיקה")
        if d["total_min"] and not d["regular_min"] and not any(d["overtime_min"].values()):
            warnings.append(f"{key}: נוכחות ללא שעות רגילות או נוספות בעמודות: נדרשת בדיקה")
        out_days.append({"date": key, "day_type": d["day_type"], "first_in": ent[0] if ent else None,
                         "last_out": ext[-1] if ext else None, "presence_min": d["total_min"],
                         "regular_min": d["regular_min"], "overtime_min": d["overtime_min"],
                         "span_matches_presence": check})
    # --- מילים בגוף הטבלה שלא נקלטו בשום שדה מוכר
    for w in words:
        if first_date - 1 <= w["top"] <= body_bottom and id(w) not in claimed and not DATE_RE.match(w["text"]):
            warnings.append(f"מילה בגוף הטבלה שלא נקלטה: '{w['text']}'")
    # --- סיכום הדוח מול סכום הימים
    sum_row = [w for w in words if body_bottom < w["top"] < body_bottom + 60 and TIME_RE.match(w["text"])]
    rep_regular = sorted((w for w in sum_row if _nearest(cols, _cx(w)) == "regular"), key=lambda w: w["top"])
    rep_total = sorted((w for w in sum_row if _nearest(cols, _cx(w)) == "total"), key=lambda w: w["top"])
    got_regular = sum(d["regular_min"] for d in out_days)
    got_total = sum(d["presence_min"] for d in out_days)
    rep = {"regular_min": to_minutes(rep_regular[0]["text"]) if rep_regular else None,
           "presence_min": to_minutes(rep_total[0]["text"]) if rep_total else None}
    status = "מאומת מול סיכום הדוח"
    if rep["regular_min"] is None or rep["presence_min"] is None:
        status = "לא נמצאה שורת סיכום: אין אימות"
        warnings.append(status)
    elif rep["regular_min"] != got_regular or rep["presence_min"] != got_total:
        status = "סכום הימים שונה מסיכום הדוח"
        warnings.append(f"{status}: ימים {got_regular}/{got_total} דק' מול דוח {rep['regular_min']}/{rep['presence_min']}")
    return {"id_number": id_number, "period_from": period[0], "period_to": period[1],
            "job_percent": pct[0]["text"] if pct else None,
            "days": out_days, "working_days": sum(1 for d in out_days if d["presence_min"]),
            "totals": {"regular_min": got_regular, "presence_min": got_total,
                       "overtime_min": {r: sum(d["overtime_min"][r] for d in out_days) for r in OT_RATES},
                       "regular_hours": str(hours_decimal(got_regular))},
            "report_totals": rep, "verification": status, "warnings": warnings}


def parse_pdf(content: bytes):
    import io
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError("נתמך כרגע דוח של עמוד אחד (עובד אחד); בדוח רב-עמודי נדרשת בדיקה ידנית")
        return parse_words(pdf.pages[0].extract_words())
