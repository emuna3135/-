"""חבילה חודשית אחרי אישור: קובץ סיכום (העברות לעובדים + תשלומים לרשויות) וקובץ הסבר. פונקציות טהורות, נבדקות בלי FastAPI.

המערכת לא שולחת ולא משלמת דבר. מועדים: רק מה שיש לו מקור ראשוני.
  ביטוח לאומי (102): 15 לחודש. מקור: אתר ביטוח לאומי (ראו payments_summary.BTL_DEADLINE_SOURCE).
  תשלום שכר חודשי: עד היום ה-9 לחודש העוקב. מקור: חוק הגנת השכר, התשי"ח-1958 (הגדרת 'היום הקובע', סעיפים 1 ו-9).
  מס הכנסה (ניכויים), פנסיה והשתלמות: אין מקור ראשוני שאומת -> 'נדרש טיפול ידני'.
קובץ העברה לבנק (מס"ב): לא נכלל. נדרשים פרטי חשבון בנק של העובדים והמפרט הרשמי; כאן רשימה בלבד.
"""
import io

import payments_summary

WAGE_LAW_SOURCE = "https://www.btl.gov.il/Laws1/00_0106_000000.pdf"
MANUAL = "נדרש טיפול ידני (אין מקור ראשוני במערכת)"


def wage_deadline(year: int, month: int) -> str:
    y, m = (year + 1, 1) if month == 12 else (year, month + 1)
    return f"{y:04d}-{m:02d}-09"


def build_workbook(year, month, stubs):
    """stubs: תלושים שמורים של החודש (אחד לעובד). מחזיר bytes של xlsx."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "העברות לעובדים"
    ws.sheet_view.rightToLeft = True
    hf, bf = Font(name="Arial", bold=True, color="FFFFFF"), Font(name="Arial")
    fill = PatternFill("solid", fgColor="1F4E79")

    def head(sheet, cols, widths):
        for c, (t, w) in enumerate(zip(cols, widths), 1):
            x = sheet.cell(1, c, t)
            x.font, x.fill = hf, fill
            x.alignment = Alignment(horizontal="center")
            sheet.column_dimensions[chr(64 + c)].width = w

    head(ws, ["שם עובד", "ת.ז (4 ספרות אחרונות)", "נטו לתשלום", "הערה"], [26, 20, 16, 50])
    total, manual = 0.0, 0
    for r, s in enumerate(sorted(stubs, key=lambda x: str(x.get("emp_name"))), 2):
        net = s.get("net")
        idn = str(s.get("emp_id_number") or "")
        vals = [s.get("emp_name"), idn[-4:], net if net is not None else None,
                "" if net is not None else "הנטו לא חושב: " + MANUAL]
        for c, v in enumerate(vals, 1):
            x = ws.cell(r, c, v)
            x.font = bf
        if net is not None:
            ws.cell(r, 3).number_format = "#,##0.00"
            total += float(net)
        else:
            manual += 1
    n = len(stubs) + 2
    ws.cell(n, 1, "סה\"כ").font = Font(name="Arial", bold=True)
    ws.cell(n, 3, f"=SUM(C2:C{n - 1})").number_format = "#,##0.00"
    ws.cell(n + 1, 1, "זו רשימה בלבד, לא קובץ העברה לבנק. המערכת לא מבצעת תשלום.").font = bf
    summ = payments_summary.summarize(year, stubs)
    m = next((x for x in summ if x["month"] == month), None)
    w2 = wb.create_sheet("תשלומים לרשויות")
    w2.sheet_view.rightToLeft = True
    head(w2, ["פריט", "סכום", "מועד", "מקור המועד"], [34, 16, 16, 70])
    rows = []
    if m:
        rows = [("מס הכנסה שנוכה", m["income_tax"], MANUAL, ""),
                ("ביטוח לאומי עובד", m["ni_employee"], "", ""),
                ("ביטוח בריאות", m["health_employee"], "", ""),
                ("ביטוח לאומי מעסיק", m["ni_employer"], "", ""),
                ("סה\"כ לביטוח לאומי", m["btl_total"], m["btl_deadline"], m["btl_deadline_source"]),
                ("פנסיה מעסיק", m["pension_employer"], MANUAL, ""),
                ("פיצויים מעסיק", m["severance_employer"], MANUAL, ""),
                ("קרן השתלמות מעסיק", m["study_fund_employer"], MANUAL, "")]
        if m["ni_employer_missing"]:
            rows.append((f"ב\"ל מעסיק חסר ב-{m['ni_employer_missing']} תלושים: הסכום חלקי", None, "", ""))
    rows.append(("תשלום שכר לעובדים", None, wage_deadline(year, month), WAGE_LAW_SOURCE))
    for r, row in enumerate(rows, 2):
        for c, v in enumerate(row, 1):
            x = w2.cell(r, c, v)
            x.font = bf
        if isinstance(row[1], (int, float)):
            w2.cell(r, 2).number_format = "#,##0.00"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), {"employees": len(stubs), "net_total": round(total, 2), "net_missing": manual}


def build_readme(year, month, info, drafts, pension_note, skipped):
    L = [f"חבילה חודשית {month:02d}/{year}", "",
         "המערכת לא שלחה ולא שילמה דבר. חשבת השכר בודקת, מאשרת ומשדרת בעצמה.", "",
         f"תלושים בחבילה: {info['employees']}. סה\"כ נטו: {info['net_total']:.2f}."]
    if info["net_missing"]:
        L.append(f"שימו לב: ב-{info['net_missing']} תלושים הנטו לא חושב (נדרש טיפול ידני).")
    if drafts:
        L.append("תלושים שהופקו כטיוטה (חסר מידע או נדרש טיפול ידני): " + ", ".join(drafts))
    if skipped:
        L.append("עובדים שלא נכללו: " + "; ".join(skipped))
    L += ["", "קובץ פנסיה: " + pension_note, "",
          "מועדים: ביטוח לאומי עד ה-15 לחודש העוקב; שכר עד ה-9 לחודש העוקב. מס הכנסה, פנסיה והשתלמות: נדרש טיפול ידני (אין מקור ראשוני).",
          "קובץ העברה לבנק (מס\"ב) אינו כלול."]
    return "\n".join(L)
