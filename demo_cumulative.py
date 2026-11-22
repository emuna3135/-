"""חוברת דמו למס מצטבר: שלושה עובדים בדויים, חודשים 1-10 של 2026, עם בונוס ושעות נוספות באמצע השנה,
כדי לראות איך המס המצטבר מתאזן מחודש לחודש. נתונים בדויים בלבד. הרצה: python3 demo_cumulative.py out.xlsx"""
import sys
import upload_template as ut

YEAR = 2026
EMPLOYEES = [  # ת"ז, שם, מין, לידה, תחילה, שכר, מצב משפחתי
    ("000000018", "דנה כהן (דמו)", "F", "1990-05-12", "2020-03-01", 12000, "רווק/ה"),
    ("000000026", "יוסי לוי (דמו)", "M", "1985-09-03", "2019-01-01", 9500, "רווק/ה"),
    ("000000034", "נועה אברהם (דמו)", "F", "1992-02-20", "2022-06-01", 15000, "נשוי/אה"),
]


def build() -> bytes:
    import io
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(ut.build_template()))
    for name in ("תלושים לטעינה", "עובדים", "טופס 101"):
        ws = wb[name]
        ws.delete_rows(2, ws.max_row)
    ws = wb["תלושים לטעינה"]
    head = [c.value for c in ws[1]]
    for idn, name, g, bd, sd, sal, mar in EMPLOYEES:
        for m in range(1, 11):
            row = {"תעודת זהות": idn, "שם עובד": name, "שכר יסוד": sal, "שעות 125": 0, "שעות 150": 0, "בונוס": 0,
                   "שנה": YEAR, "חודש": m, "פטור ממס": 0}
            if idn == "000000018" and m == 6:
                row["בונוס"] = 15000                      # בונוס באמצע השנה: המצטבר מתאזן בחודש הבא
            if idn == "000000026" and m in (3, 4):
                row["שעות 125"], row["שעות 150"] = 10, 5
            if idn == "000000034" and m == 8:
                row["שכר יסוד"] = 17000                   # העלאת שכר מאוגוסט
            if idn == "000000034" and m > 8:
                row["שכר יסוד"] = 17000
            ws.append([row.get(h) for h in head])
    ws = wb["עובדים"]
    head = [c.value for c in ws[1]]
    for idn, name, g, bd, sd, sal, mar in EMPLOYEES:
        r = {"תעודת זהות": idn, "שם מלא": name, "מין": g, "תאריך לידה": bd, "תאריך תחילת עבודה": sd, "תושב": "כן",
             "שכר יסוד": sal, "אחוז פנסיה עובד": 0.06, "אחוז פנסיה מעסיק": 0.065, "אחוז פיצויים מעסיק": 0.06,
             "היקף משרה %": 100, "שם משפחה": name.split()[1], "שם פרטי": name.split()[0], "רחוב ומספר בית": "הרצל 1",
             "עיר": "חיפה", "מיקוד": "33000"}
        ws.append([r.get(h) for h in head])
    ws = wb["טופס 101"]
    head = [c.value for c in ws[1]]
    for idn, name, g, bd, sd, sal, mar in EMPLOYEES:
        r = {"תעודת זהות": idn, "שם עובד": name, "שנת מס": YEAR, "תאריך חתימה": "2026-01-05", "סוג הכנסה": "משרה עיקרית",
             "הכנסה אחרת": "לא", "מצב משפחתי": mar}
        ws.append([r.get(h) for h in head])
    wb["הסבר"].cell(wb["הסבר"].max_row + 1, 1,
                    "חוברת דמו למס מצטבר: 3 עובדים בדויים, חודשים 1-10 של 2026. בונוס אצל דנה ביוני, שעות נוספות אצל יוסי במרץ-אפריל, העלאת שכר אצל נועה באוגוסט.")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    open(sys.argv[1] if len(sys.argv) > 1 else "payroll-demo-cumulative.xlsx", "wb").write(build())
