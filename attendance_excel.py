"""
קורא דוח נוכחות באקסל. עיקרון: לא מנחשים. כל עמודה שלא זוהתה, כל תא שלא נקרא וכל פער מול שורת הסיכום נכנסים ל-warnings.
זיהוי עמודות: לפי כותרות מוכרות (ALIASES), או לפי מיפוי מפורש שהחשבת נותנת (mapping: שדה -> טקסט הכותרת או אות העמודה).
שעות בדוח: hh:mm, שעה של אקסל, או שבר יום. כולן מומרות לדקות שלמות ללא עיגול.
נבדק רק על קבצי בדיקה שנבנו כאן; לא על דוח נוכחות אמיתי של לקוח. לכן הפלט הוא תצוגה מקדימה בלבד, והחשבת מאשרת.
"""
import datetime
import io
import re
from decimal import Decimal

FIELDS = ("date", "entry", "exit", "total", "regular", "ot100", "ot125", "ot150", "ot200", "id", "name")
ALIASES = {
    "date": ("תאריך",),
    "entry": ("כניסה", "שעת כניסה"),
    "exit": ("יציאה", "שעת יציאה"),
    "total": ("סה\"כ", "סה\"כ שעות", "שעות נוכחות", "נוכחות", "סהכ"),
    "regular": ("שעות רגילות", "ש.רגילות", "רגילות", "שעות 100%", "100%"),
    "ot100": (),
    "ot125": ("שעות 125%", "125%"),
    "ot150": ("שעות 150%", "150%"),
    "ot200": ("שעות 200%", "200%"),
    "id": ("תעודת זהות", "ת.ז", "ת.ז.", "מספר זהות"),
    "name": ("שם עובד", "שם"),
}
KNOWN_IGNORED = ("יום", "יום בשבוע", "הערות", "הערה")           # כותרות שאינן נתוני שכר: לא מזהירים עליהן
SUMMARY_WORDS = ("סה\"כ", "סהכ", "סיכום", "סך הכל", "סה״כ")
TIME_RE = re.compile(r"^(\d{1,3}):(\d{2})(?::\d{2})?$")
DATE_RES = ((re.compile(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})$"), "dmy"), (re.compile(r"^(\d{4})-(\d{2})-(\d{2})"), "ymd"))


def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip().replace("״", '"').replace("”", '"'))


def to_minutes(v):
    """ממיר תא לדקות שלמות או מחזיר None אם ריק. ערך שאינו שעה: ValueError (לא מנחשים)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, datetime.timedelta):
        sec = round(v.total_seconds())
        return sec // 60
    if isinstance(v, datetime.datetime):
        return v.hour * 60 + v.minute
    if isinstance(v, datetime.time):
        return v.hour * 60 + v.minute
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if not 0 <= v < 1:                       # שבר יום בלבד; מספר אחר (כמו 8.5) אינו חד-משמעי
            raise ValueError(f"ערך מספרי {v} אינו שעה או שבר יום")
        return int(round(v * 1440))
    m = TIME_RE.match(str(v).strip())
    if not m:
        raise ValueError(f"'{v}' אינו שעה בפורמט hh:mm")
    h, mi = int(m.group(1)), int(m.group(2))
    if mi > 59:
        raise ValueError(f"דקות לא תקינות: {v}")
    return h * 60 + mi


def to_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v).strip() if v is not None else ""
    for rx, kind in DATE_RES:
        m = rx.match(s)
        if m:
            a, b, c = (int(x) for x in m.groups())
            try:
                return datetime.date(c, b, a) if kind == "dmy" else datetime.date(a, b, c)
            except ValueError:
                return None
    return None


def _letter_to_idx(s):
    s = s.strip().upper()
    if re.fullmatch(r"[A-Z]{1,2}", s):
        n = 0
        for ch in s:
            n = n * 26 + ord(ch) - 64
        return n - 1
    return None


def _find_header(rows, mapping):
    """שורת הכותרות: הראשונה (עד 20 שורות) שבה לפחות 3 כותרות מוכרות, או שכל שדות המיפוי נמצאים בה."""
    for i, row in enumerate(rows[:20]):
        cells = [_norm(c) if c is not None else "" for c in row]
        hits = sum(1 for c in cells if any(c == a for al in ALIASES.values() for a in al))
        if mapping:
            ok = all((_letter_to_idx(v) is not None) or (_norm(v) in cells) for v in mapping.values())
            if ok:
                return i, cells
        elif hits >= 3:
            return i, cells
    return None, None


def parse_workbook(content: bytes, mapping=None, sheet=None):
    """מחזיר {employees:[{id,name,days,totals,verification}], warnings, header_row, columns}. ValueError אם הקובץ אינו דוח נוכחות מזוהה."""
    import openpyxl
    mapping = {k: v for k, v in (mapping or {}).items() if k in FIELDS and v not in (None, "")}
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        raise ValueError("לא ניתן לקרוא את קובץ האקסל")
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hi, header = _find_header(rows, mapping)
    if hi is None:
        raise ValueError("לא נמצאה שורת כותרות של דוח נוכחות. אפשר לציין מיפוי עמודות (שדה: כותרת או אות עמודה).")
    warnings, cols = [], {}
    for f in FIELDS:
        if f in mapping:
            v = mapping[f]
            idx = _letter_to_idx(v)
            if idx is None:
                cands = [i for i, c in enumerate(header) if c == _norm(v)]
                idx = cands[0] if cands else None
            if idx is None:
                raise ValueError(f"העמודה '{v}' של השדה {f} לא נמצאה בשורת הכותרות")
            cols[f] = idx
        else:
            for a in ALIASES[f]:
                if a in header:
                    cols[f] = header.index(a)
                    break
    for need in ("date",):
        if need not in cols:
            raise ValueError("לא נמצאה עמודת תאריך")
    if "total" not in cols and not ("entry" in cols and "exit" in cols):
        raise ValueError("דרושה עמודת סה\"כ שעות, או שתי עמודות כניסה ויציאה")
    used = set(cols.values())
    for i, c in enumerate(header):
        if c and i not in used and c not in KNOWN_IGNORED:
            warnings.append(f"עמודה '{c}' לא זוהתה ולא נקראה: נדרשת בדיקה אם יש בה נתוני שכר")
    emps, order = {}, []
    summary_rows = []
    for r_no, row in enumerate(rows[hi + 1:], start=hi + 2):
        row = list(row) + [None] * (len(header) - len(row))
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in row):
            continue
        dcell = row[cols["date"]]
        d = to_date(dcell)
        if d is None:
            if isinstance(dcell, str) and any(_norm(dcell).startswith(w) for w in SUMMARY_WORDS):
                summary_rows.append((r_no, row))
            elif dcell is None and any(isinstance(row[cols[f]], (str, int, float)) for f in cols if f in ("total", "regular") and row[cols[f]] is not None):
                summary_rows.append((r_no, row))        # שורת סיכום בלי תווית
            else:
                warnings.append(f"שורה {r_no}: התאריך '{dcell}' לא זוהה, השורה לא נספרה")
            continue
        eid = str(row[cols["id"]]).strip() if "id" in cols and row[cols["id"]] is not None else None
        name = str(row[cols["name"]]).strip() if "name" in cols and row[cols["name"]] is not None else None
        key = eid or name or "_"
        if key not in emps:
            emps[key] = {"id": eid, "name": name, "days": {}, "summary": None}
            order.append(key)
        day = emps[key]["days"].setdefault(d.isoformat(), {"date": d.isoformat(), "span_min": 0, "total_min": 0, "regular_min": 0,
                                                            "overtime_min": {"100": 0, "125": 0, "150": 0, "200": 0}, "rows": 0})
        day["rows"] += 1
        vals = {}
        for f in ("entry", "exit", "total", "regular", "ot100", "ot125", "ot150", "ot200"):
            if f in cols:
                try:
                    vals[f] = to_minutes(row[cols[f]])
                except ValueError as e:
                    warnings.append(f"שורה {r_no} ({d.isoformat()}): {e}; התא לא נספר")
                    vals[f] = None
        if vals.get("entry") is not None and vals.get("exit") is not None:
            span = vals["exit"] - vals["entry"]
            if span < 0:
                span += 1440
                warnings.append(f"שורה {r_no} ({d.isoformat()}): יציאה לפני כניסה, חושב כמשמרת שחוצה חצות: נדרשת בדיקה")
            day["span_min"] += span
        elif (vals.get("entry") is None) != (vals.get("exit") is None):
            warnings.append(f"שורה {r_no} ({d.isoformat()}): כניסה או יציאה חסרה: לא נספר מרווח הזמן")
        if vals.get("total") is not None:
            day["total_min"] += vals["total"]
        elif day["span_min"] and "total" not in cols:
            day["total_min"] += day["span_min"] if vals.get("entry") is not None else 0
        day["regular_min"] += vals.get("regular") or 0
        for rate in ("100", "125", "150", "200"):
            day["overtime_min"][rate] += vals.get("ot" + rate) or 0
    out = []
    for key in order:
        e = emps[key]
        days = [e["days"][k] for k in sorted(e["days"])]
        for d in days:
            if "total" in cols and d["span_min"] and d["total_min"] and d["span_min"] != d["total_min"]:
                warnings.append(f"{d['date']}: יציאה פחות כניסה ({d['span_min']} דק') שונה מסה\"כ ({d['total_min']} דק'): נדרשת בדיקה (הפסקה?)")
            if d["rows"] > 1:
                warnings.append(f"{d['date']}: {d['rows']} שורות באותו תאריך, סוכמו")
        tot = {"presence_min": sum(d["total_min"] for d in days), "regular_min": sum(d["regular_min"] for d in days),
               "overtime_min": {r: sum(d["overtime_min"][r] for d in days) for r in ("100", "125", "150", "200")}}
        out.append({"id": e["id"], "name": e["name"], "days": days, "working_days": sum(1 for d in days if d["total_min"]),
                    "totals": {**tot, "presence_hours": str((Decimal(tot["presence_min"]) / 60).quantize(Decimal("0.0001")))}})
    verification = "לא נמצאה שורת סיכום: אין אימות"
    if summary_rows and len(out) == 1:
        _, srow = summary_rows[-1]
        rep = {}
        for f in ("total", "regular", "ot125", "ot150"):
            if f in cols:
                try:
                    rep[f] = to_minutes(srow[cols[f]])
                except ValueError:
                    rep[f] = None
        t = out[0]["totals"]
        mine = {"total": t["presence_min"], "regular": t["regular_min"], "ot125": t["overtime_min"]["125"], "ot150": t["overtime_min"]["150"]}
        diffs = [f"{f}: ימים {mine[f]} דק' מול סיכום {v} דק'" for f, v in rep.items() if v is not None and mine[f] != v]
        compared = [f for f, v in rep.items() if v is not None]
        if not compared:
            verification = "בשורת הסיכום אין ערכים להשוואה: אין אימות"
        elif diffs:
            verification = "סכום הימים שונה מסיכום הדוח"
            warnings.append(verification + ": " + "; ".join(diffs))
        else:
            verification = "מאומת מול שורת הסיכום של הדוח"
    elif summary_rows:
        verification = "יש שורת סיכום אך בקובץ כמה עובדים: אין אימות אוטומטי"
        warnings.append(verification)
    else:
        warnings.append(verification)
    if not out:
        raise ValueError("לא נמצאו שורות עם תאריך")
    return {"employees": out, "columns": {f: header[i] or f"עמודה {i + 1}" for f, i in cols.items()},
            "header_row": hi + 1, "verification": verification, "warnings": warnings}
