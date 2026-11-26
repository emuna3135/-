"""ייצוא פקודת יומן שכר להנהלת חשבונות. פונקציות טהורות, נבדקות ב-test_accounting_export.py.

המערכת לא יודעת את פורמט הייבוא של כל תוכנת הנהלת חשבונות. לכן יש כאן שלוש תבניות כלליות (אקסל, CSV, CSV בקידוד חלונות 1255)
ושדה 'שם התוכנה' שנכנס לקובץ ולשם שלו. תבנית מדויקת לתוכנה מסוימת (חשבשבת, פריוריטי, ועוד) תתווסף רק לפי מפרט ייבוא או קובץ
דוגמה רשמי של אותה תוכנה; לא מנחשים עמודות.
סכומים: שקלים עם אגורות, בלי עיגול ביניים. ביטוח לאומי ובריאות נשמרים ללא עיגול (תשובת רו"ח 11.11.2026), לכן סכום הקובץ מעוגל
פעם אחת לכל חשבון; הפרש עיגול של עד 2 אגורות נרשם בשורה נפרדת וגלויה, מעבר לזה הקובץ נחסם.
תלוש שיש בו סעיף 'נדרש טיפול ידני' (ערך חסר) לא נכנס לקובץ ומופיע ברשימת הבעיות."""
import csv
import io
from decimal import Decimal, ROUND_HALF_UP

D = Decimal
TEMPLATES = {
    "xlsx": ("אקסל כללי (פקודת יומן)", "xlsx"),
    "csv_utf8": ("CSV כללי (UTF-8)", "csv"),
    "csv_1255": ("CSV כללי (עברית חלונות 1255)", "csv"),
}
# שורות הפקודה: (מפתח, תיאור, צד). צד d = חובה (הוצאה), c = זכות (התחייבות)
LINES = [
    ("gross", "שכר ברוטו", "d"),
    ("er_pension", "הפרשת מעסיק לפנסיה", "d"),
    ("er_severance", "הפרשת מעסיק לפיצויים", "d"),
    ("er_study_fund", "הפרשת מעסיק להשתלמות", "d"),
    ("er_ni", "ביטוח לאומי מעסיק", "d"),
    ("income_tax", "מס הכנסה לשלם", "c"),
    ("ni", "ביטוח לאומי (ניכוי עובד) לשלם", "c"),
    ("health", "ביטוח בריאות (ניכוי עובד) לשלם", "c"),
    ("pension_employee", "פנסיה עובד לשלם", "c"),
    ("liab_er_pension", "פנסיה מעסיק לשלם", "c"),
    ("liab_er_severance", "פיצויים לשלם", "c"),
    ("liab_er_study_fund", "קרן השתלמות לשלם", "c"),
    ("liab_er_ni", "ביטוח לאומי מעסיק לשלם", "c"),
    ("other_deductions", "ניכויים אחרים והטבות לא כספיות", "c"),
    ("net", "שכר נטו לתשלום", "c"),
    ("rounding", "הפרשי עיגול", "x"),
]
LABEL = {k: t for k, t, _ in LINES}
SIDE = {k: s for k, _, s in LINES}


def _d(v):
    return D(str(v))


def stub_amounts(stub):
    """סכומי התלוש לפי שורות הפקודה. None אם חסר ערך (נדרש טיפול ידני)."""
    emp = stub.get("employer") or {}
    need = [stub.get("gross"), stub.get("income_tax"), stub.get("national_insurance"), stub.get("health"),
            stub.get("pension_employee"), stub.get("net")]
    if any(v is None for v in need):
        return None
    for k in ("pension", "severance", "study_fund", "national_insurance"):
        if emp.get(k) is None:
            return None
    gross = _d(stub["gross"])
    a = {"gross": gross, "income_tax": _d(stub["income_tax"]), "ni": _d(stub["national_insurance"]),
         "health": _d(stub["health"]), "pension_employee": _d(stub["pension_employee"]), "net": _d(stub["net"]),
         "er_pension": _d(emp["pension"]), "er_severance": _d(emp["severance"]),
         "er_study_fund": _d(emp["study_fund"]), "er_ni": _d(emp["national_insurance"])}
    a["liab_er_pension"], a["liab_er_severance"] = a["er_pension"], a["er_severance"]
    a["liab_er_study_fund"], a["liab_er_ni"] = a["er_study_fund"], a["er_ni"]
    # כל מה שנוכה מהברוטו ולא פורט למעלה (ניכויים קבועים, ביטוח חיים, הטבות לא כספיות) = ההפרש עד הנטו
    a["other_deductions"] = gross - a["income_tax"] - a["ni"] - a["health"] - a["pension_employee"] - a["net"]
    return a


def q2(x):
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def build_rows(stubs, codes, per_employee=False):
    """מחזיר (rows, issues). rows: dict(employee, id, key, label, account, debit, credit)."""
    issues, groups = [], {}
    for s in stubs:
        a = stub_amounts(s)
        who = f'{s.get("emp_name", "")} ({str(s.get("emp_id_number", ""))[-4:]})'
        if a is None:
            issues.append({"level": "block", "text": f"{who}: יש סעיף שדורש טיפול ידני; התלוש לא נכלל בקובץ"})
            continue
        if min(a["gross"], a["net"]) < 0 or a["other_deductions"] < D("-0.05"):
            issues.append({"level": "block", "text": f"{who}: הסכומים אינם מתיישבים (ניכויים אחרים שליליים); התלוש לא נכלל"})
            continue
        gkey = (s.get("emp_id_number"), s.get("emp_name")) if per_employee else ("", "סיכום")
        g = groups.setdefault(gkey, {k: D(0) for k, _, _ in LINES})
        for k, v in a.items():
            g[k] += v
    rows = []
    for (eid, name), g in groups.items():
        deb = {k: q2(g[k]) for k, _, side in LINES if side == "d"}
        cre = {k: q2(g[k]) for k, _, side in LINES if side == "c"}
        diff = sum(deb.values(), D(0)) - sum(cre.values(), D(0))
        if abs(diff) > D("0.02"):
            issues.append({"level": "block", "text": f"{name}: הפקודה לא מאוזנת (הפרש {diff} ש\"ח); הקובץ נחסם"})
            continue
        for k, _, side in LINES:
            if side == "x":
                continue
            amt = (deb if side == "d" else cre)[k]
            if amt == 0:
                continue
            rows.append({"employee": name if per_employee else "", "id": eid or "", "key": k, "label": LABEL[k],
                         "account": (codes or {}).get(k, ""), "debit": amt if side == "d" else D(0),
                         "credit": amt if side == "c" else D(0)})
        if diff != 0:
            rows.append({"employee": name if per_employee else "", "id": eid or "", "key": "rounding", "label": LABEL["rounding"],
                         "account": (codes or {}).get("rounding", ""),
                         "debit": D(0) if diff > 0 else -diff, "credit": diff if diff > 0 else D(0)})
            issues.append({"level": "warn", "text": f"{name}: הפרש עיגול {diff} ש\"ח נרשם בשורה נפרדת (ביטוח לאומי ובריאות לא מעוגלים בתלוש)"})
    missing = sorted({r["label"] for r in rows if not r["account"]})
    if missing:
        issues.append({"level": "warn", "text": "לא הוגדר מספר חשבון עבור: " + ", ".join(missing) + ". הקובץ ייצא עם עמודת חשבון ריקה"})
    return rows, issues


def build_file(rows, template, software, year, month, company_name=""):
    """מחזיר (bytes, filename, mime)."""
    if template not in TEMPLATES:
        raise ValueError("תבנית לא מוכרת")
    heads = ["תאריך", "אסמכתא", "חשבון", "תיאור", "עובד", "חובה", "זכות"]
    ref = f"שכר {month:02d}/{year}"
    import calendar
    date = f"{calendar.monthrange(year, month)[1]:02d}/{month:02d}/{year}"
    body = [[date, ref, r["account"], r["label"], r["employee"], f'{r["debit"]:.2f}', f'{r["credit"]:.2f}'] for r in rows]
    safe = "".join(c for c in (software or "") if c.isascii() and (c.isalnum() or c in "-_")) or "general"   # שם קובץ ב-ASCII בלבד (כותרת HTTP)
    base = f"journal-{safe}-{year}{month:02d}"
    if template == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "פקודת יומן"
        ws.sheet_view.rightToLeft = True
        ws.append([f"פקודת יומן שכר {month:02d}/{year} | {company_name} | תוכנה: {software or 'כללי'} | טיוטה לבדיקת חשבת השכר"])
        ws.append(heads)
        for r in rows:
            ws.append([date, ref, r["account"], r["label"], r["employee"], float(r["debit"]), float(r["credit"])])
        n = len(rows)
        ws.append(["", "", "", "סה\"כ", "", f"=SUM(F3:F{n + 2})", f"=SUM(G3:G{n + 2})"])
        for row in ws.iter_rows(min_row=3, min_col=6, max_col=7):
            for c in row:
                c.number_format = "#,##0.00"
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), base + ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(heads)
    w.writerows(body)
    text = out.getvalue()
    if template == "csv_1255":
        return text.encode("cp1255", errors="replace"), base + ".csv", "text/csv; charset=windows-1255"
    return text.encode("utf-8-sig"), base + ".csv", "text/csv; charset=utf-8"
