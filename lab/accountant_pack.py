"""
חבילת 50 תלושים בדויים לרואת חשבון חיצונית (נתונים בדויים בלבד: ת.ז. נוצרות עם ספרת ביקורת, ללא קשר לאנשים אמיתיים).
לכל עובד: קלט מלא, תוצאות המערכת לחודש הנבחר (מצטבר מינואר), וחישוב בלתי תלוי שלנו של מס, ב"ל ובריאות (לא מקור רשמי).
הרצה: python3 lab/accountant_pack.py [חודש 1-12]  ->  lab/accountant_pack.xlsx
"""
import sys
sys.path.insert(0, ".")
from decimal import Decimal as D
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import engine as pe
from lab import synthetic_lab as S

N = 50
MONTH = 10
TOL_TAX = D(1)
TOL_NI = D("0.005")


def build(month=MONTH, n=N):
    rows, issues = [], []
    for e in S.gen_employees(n):
        pts, st, note, errs, val = S.points_via_101(e["idn"], e["gender"], e["married"], e["flag"], e["cust"], e["noncust"])
        if pts is None or errs:
            issues.append((e["idn"], f"נקודות זיכוי: {note[:70]} {errs}"))
            continue
        e["points"] = pts
        prev, cum_taxable, cum_dep, tax_sum = None, D(0), D(0), D(0)
        last, stopped = None, None
        for m in range(1, month + 1):
            p = S.payslip(e, m, prev)
            r = p["r"]
            items = r["items"]
            if any(v["value"] is None for v in items.values()):
                stopped = m
                break
            prev = r.get("cum") or r.get("cumulative")
            tax_prev = tax_sum
            tax_sum += D(str(items["income_tax"]["value"]))
            cum_taxable += p["gross"]
            cum_dep += D(str(items["pension_employee"]["value"]))
            last = (p, r, items, tax_prev, tax_sum, cum_taxable, cum_dep)
        if stopped or last is None:
            issues.append((e["idn"], f"חודש {stopped}: רכיב מחושב ידנית; עובד לא נכלל"))
            continue
        p, r, items, tax_prev, tax_sum, cum_taxable, cum_dep = last
        exp_cum = max(S.indep_tax(cum_taxable, month, pts, cum_dep), D(0))
        ni, h = S.indep_ni_health(p["gross"])
        sys_ni, sys_h = D(str(items["national_insurance"]["value"])), D(str(items["health"]["value"]))
        rows.append([
            e["idn"], "נקבה" if e["gender"] == "F" else "זכר", "נשוי/ה" if e["married"] else "לא נשוי/ה",
            ", ".join(map(str, e["cust"])) or "-", float(pts),
            float(e["base"]), e["ot125"], e["ot150"], float(p["bonus"]), float(e["phone"]), float(e["car_price"]),
            float(e["pen_rate"]), float(e["sf_rate"]), float(p["ded"]),
            float(pe.r2(p["gross"])), float(pe.r2(p["noncash"])), float(pe.r2(p["pbase"])),
            float(items["income_tax"]["value"]), float(sys_ni), float(sys_h), float(items["pension_employee"]["value"]),
            float(r["net"]),
            float(tax_sum), float(round(exp_cum)), float(tax_sum - D(round(exp_cum))),
            float(ni), float(sys_ni - ni), float(h), float(sys_h - h),
            r["overall_status"],
        ])
        if abs(tax_sum - D(round(exp_cum))) > TOL_TAX:
            issues.append((e["idn"], f"פער מס מצטבר {tax_sum} מול {round(exp_cum)}"))
        if abs(sys_ni - ni) > TOL_NI or abs(sys_h - h) > TOL_NI:
            issues.append((e["idn"], f"פער ב\"ל/בריאות {sys_ni}/{ni}, {sys_h}/{h}"))
    return rows, issues


HEAD = ["ת.ז. בדויה", "מין", "מצב משפחתי", "גילאי ילדים (בחזקה)", "נקודות זיכוי",
        "שכר יסוד", "שעות 125%", "שעות 150%", "בונוס החודש", "שווי טלפון", "מחיר רכב", "אחוז פנסיה עובד", "אחוז קה\"ש עובד", "ניכויי רשות החודש",
        "ברוטו (מערכת)", "שווי הטבות", "בסיס פנסיה",
        "מס הכנסה החודש (מערכת)", "ב\"ל (מערכת)", "בריאות (מערכת)", "פנסיה עובד (מערכת)", "נטו (מערכת)",
        "מס מצטבר (מערכת)", "מס מצטבר (חישוב בלתי תלוי)", "הפרש מס מצטבר",
        "ב\"ל (חישוב בלתי תלוי)", "הפרש ב\"ל", "בריאות (חישוב בלתי תלוי)", "הפרש בריאות", "סטטוס מערכת"]
INPUT_COLS = 14


def write(path="lab/accountant_pack.xlsx", month=MONTH, n=N):
    rows, issues = build(month, n)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "הוראות"
    ws.sheet_view.rightToLeft = True
    lines = [
        ("חבילת בדיקה: תלושים בדויים", True),
        (f"חודש הבדיקה: {month:02d}/2026. מצטבר מינואר. {len(rows)} עובדים בדויים. אין בקובץ נתונים אמיתיים.", False),
        ("מה מבקשים ממך: להזין כל שורה בתוכנת השכר שלך (עמודות A עד N הן הקלט) ולהשוות מס הכנסה, ביטוח לאומי, בריאות ונטו.", False),
        ("עמודות X עד AC הן חישוב בלתי תלוי שלנו. הוא לא מקור רשמי, ובא רק לבדוק את המערכת מול עצמה.", False),
        ("שעות נוספות: שכר יסוד לחלקי 182, כפול 1.25 או 1.5. פנסיית עובד על שכר היסוד (שעות נוספות ובונוס אינם בבסיס).", False),
        ("מה לדווח חזרה: כל הפרש מעל שקל במס, או מעל חצי אגורה בביטוח לאומי ובריאות, לצד התוכנה שבה בדקת.", False),
        ("ב\"ל ובריאות אינם מעוגלים בחישוב (כמו בחילן); הפרש של אגורה אחת בין הנטו לסכום השורות המוצגות הוא התנהגות מוסכמת.", False),
    ]
    for i, (t, b) in enumerate(lines, 1):
        c = ws.cell(i, 1, t)
        c.font = Font(name="Arial", bold=b, size=14 if b else 11)
        c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right")
    ws.column_dimensions["A"].width = 110
    ws2 = wb.create_sheet("תלושים")
    ws2.sheet_view.rightToLeft = True
    ws2.append(HEAD)
    fill_in = PatternFill("solid", fgColor="DDEBF7")
    fill_sys = PatternFill("solid", fgColor="E2EFDA")
    fill_ind = PatternFill("solid", fgColor="FFF2CC")
    for j, h in enumerate(HEAD, 1):
        c = ws2.cell(1, j)
        c.font = Font(name="Arial", bold=True)
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        c.fill = fill_in if j <= INPUT_COLS else (fill_sys if j <= 22 else fill_ind)
        ws2.column_dimensions[get_column_letter(j)].width = 16
    for r in rows:
        ws2.append(r)
    ws2.freeze_panes = "B2"
    ws2.row_dimensions[1].height = 48
    ws3 = wb.create_sheet("ממצאים")
    ws3.sheet_view.rightToLeft = True
    ws3.append(["ת.ז. בדויה", "ממצא"])
    for it in issues:
        ws3.append(list(it))
    if not issues:
        ws3.append(["-", "לא נמצאו פערים בין המערכת לחישוב הבלתי תלוי"])
    ws3.column_dimensions["A"].width = 16
    ws3.column_dimensions["B"].width = 90
    for w in (ws2, ws3):
        for row in w.iter_rows(min_row=2):
            for c in row:
                c.font = Font(name="Arial", size=10)
    wb.save(path)
    return rows, issues


if __name__ == "__main__":
    MONTH = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    rows, issues = write(month=MONTH)
    print(len(rows), "עובדים;", len(issues), "ממצאים")
    for i in issues[:15]:
        print(i)
