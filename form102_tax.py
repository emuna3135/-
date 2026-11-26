"""
דיווח ניכויים 102 למס הכנסה (סוג ניכוי 00, ניכויים ממשכורת ושכ"ע): בניית נתוני הדיווח לפי המפרט הרשמי.
נוצר 26.11.2026, ענף dev-components. המערכת לא משדרת: היא מייצרת את הנתונים, והחשב בודק ומשדר בעצמו.

מקורות רשמיים (נקראו 26.11.2026):
1. רשות המסים, "דיווח ותשלום ניכויים באמצעות API", מהדורה 1.1
   https://www.gov.il/BlobFolder/generalpage/hor-software-other/he/IncomeTax_software-houses-150525-1.pdf
   שדות קלט: RepresentNumber 9(N), TaxpayerNumber 9(N), Period N(6) YYYYMM, ActionCode 2(N) (1 = דיווח ראשוני),
   RegisterNumber 2(N), DeductionTypeCount 1(N) 1-6, DeductionTypeList: DeductionType 2(A), NonEmployment 1(N),
   EmployeesNumber 5(N), Payments 10(N), Charges 10(N); PaymentAmount 13(N), PaymentDate 8(N) YYYYMMDD, PaymentMethod 1(N).
   כללי שגיאה: 118 חיוב גבוה מסך המשכורות; 119 סכום לתשלום שונה מסך החיובים; 111/112 כמות סוגי ניכוי; 121 סוג כפול;
   114/115 אי העסקה מול סכומים; 116/117 חסר מספר עובדים/משכורות; 203/204/211 אפסים; 228 סכום שלילי; 229 סכום זהה למספר התיק.
2. רשות המסים, הדרכה לדו"ח הניכויים (secapp.taxes.gov.il, NikPay): סוג ניכוי 00 "ניכויים ממשכורת ושכ"ע":
   "עליך לרשום את סה"כ המשכורות ושכר עבודה ששולמו, גם אם לא נוכה מהם מס במקור מסיבה כלשהי (כגון: פטור)";
   אם דווחו משכורות חובה למלא מספר עובדים וחיוב לתשלום.

מה שהמפרט לא קובע (ולכן מסומן, ואינו "עפ"י החוק"):
- כתובת שירות, הזדהות, מבנה JSON/XML מדויק ודוגמאות: אינם במסמך. הפלט כאן הוא מילון בשמות השדות הרשמיים, לא בקשת רשת.
- משמעות הקודים 06, 08, 10, 16, 17 לא מוגדרת במפרט עצמו; כאן מיוצר רק 00.
- כללי עיגול לשקל שלם: המפרט קובע N(10) (מספר שלם), ללא כלל עיגול. כאן עיגול חצי-למעלה של סכום חודשי כולל, ומסומן.
- איזה רכיבי שכר נכללים ב-Payments (כולל שווי הטבות ופטורים): מנוסחת ההדרכה "כל המשכורות", אך ההגדרה המלאה בתקנות המשכורת. נלקח "gross" מהתלוש.
- המפרט מתיר דיווח ראשוני בלבד, לחודש השוטף בלבד (שגיאות 209, 271).
"""
from decimal import Decimal as D, ROUND_HALF_UP

SOURCE = "רשות המסים - דיווח ותשלום ניכויים באמצעות API, מהדורה 1.1 (gov.il, נקרא 26.11.2026)"
GUIDE_SOURCE = "רשות המסים - הדרכה למילוי דו\"ח הניכויים, סוג ניכוי 00 (secapp.taxes.gov.il, נקרא 26.11.2026)"
NOTES = [
    "המפרט אינו כולל כתובת שירות, הזדהות או מבנה הודעה: נדרש אימות מול שע\"ם לפני שידור",
    "עיגול לשקל שלם אינו מוגדר במפרט: סכומים מעוגלים חצי-למעלה לשקל; נדרש אישור רואת חשבון",
    "הגדרת Payments (אילו רכיבים כלולים, כולל שווי הטבות ופטורים) לפי תקנות המשכורת: נדרש אישור רואת חשבון",
    "המפרט מאפשר רק דיווח ראשוני לחודש השוטף; דיווח מתקן או הפרשים לא נתמכים כאן",
]
PAYMENT_METHODS = {0: "דוח אפס", 1: "הרשאה לחיוב חשבון", 2: "אשראי (לבעלי כרטיס רשום)", 9: "לא נבחר אמצעי תשלום"}
CREDIT_LIMIT = 50000   # שגיאה 274: אשראי עד 50,000 ש"ח


def _whole(x):
    return int(D(str(x)).quantize(D("1"), rounding=ROUND_HALF_UP))


def _digits(v, width, name):
    s = str(v).strip()
    if not s.isdigit() or len(s) > width:
        raise ValueError(f"{name}: נדרשות עד {width} ספרות")
    return s.zfill(width)


def _nz(v):
    return D(str(v)) if v is not None else D(0)


def aggregate(year, month, stubs):
    """מצרף תלושים שמורים של חודש אחד. תלוש מאוחר לאותו עובד דורס. מחזיר (עובדים, משכורות, מס שנוכה, חסרים)."""
    latest = {}
    for s in stubs:
        if s.get("year") == year and s.get("month") == month:
            latest[str(s.get("emp_id_number"))] = s
    employees = payments = charges = D(0)
    missing = []
    for k, s in sorted(latest.items()):
        if s.get("gross") is None:
            missing.append(f"{s.get('emp_name') or k}: אין ברוטו בתלוש")
            continue
        if s.get("income_tax") is None:
            missing.append(f"{s.get('emp_name') or k}: מס הכנסה בתלוש לא חושב (נדרש טיפול ידני)")
            continue
        if _nz(s["gross"]) < 0 or _nz(s["income_tax"]) < 0:
            missing.append(f"{s.get('emp_name') or k}: סכום שלילי בתלוש (המפרט אוסר סכום שלילי, שגיאה 228)")
            continue
        employees += 1
        payments += _nz(s["gross"])
        charges += _nz(s["income_tax"])
    return int(employees), payments, charges, missing


def build(year, month, stubs, represent_number, taxpayer_number, register_number,
          payment_method=9, payment_date=None, non_employment=False):
    """
    מחזיר {"input": {...בשמות השדות הרשמיים...}, "summary": {...}, "problems": [...], "status", "notes"}.
    non_employment=True: דיווח אי העסקה (עובדים, תשלומים וחיובים מאופסים).
    payment_date: "YYYYMMDD" או None (המערכת של שע"ם ממלאת כשהשדה ריק).
    """
    rep = _digits(represent_number, 9, "מספר מייצג (RepresentNumber)")
    tax = _digits(taxpayer_number, 9, "מספר תיק ניכויים (TaxpayerNumber)")
    reg = _digits(register_number, 2, "מספר פנקס (RegisterNumber)")
    if int(rep) == 0:
        raise ValueError("מספר מייצג מאופס (שגיאה 204)")
    if int(tax) == 0:
        raise ValueError("מספר תיק ניכויים מאופס (שגיאה 203)")
    if int(reg) == 0:
        raise ValueError("מספר פנקס מאופס (שגיאה 211)")
    if payment_method not in PAYMENT_METHODS:
        raise ValueError("קוד אמצעי תשלום שגוי (שגיאה 221)")
    if not 1 <= int(month) <= 12 or not 2000 <= int(year) <= 2100:
        raise ValueError("חודש הדיווח במבנה לא תקין (שגיאה 208)")
    if payment_date is not None:
        pd = str(payment_date)
        if not (pd.isdigit() and len(pd) == 8):
            raise ValueError("תאריך תשלום במבנה לא תקין, נדרש YYYYMMDD (שגיאה 218)")

    emp, pay, chg, missing = aggregate(year, month, stubs)
    if non_employment:
        emp, pay, chg = 0, D(0), D(0)
    elif not stubs:
        missing.append("אין תלושים שמורים לחודש. לדיווח אי העסקה יש לבקש במפורש non_employment")
    elif emp == 0 and not missing:
        missing.append("אין עובדים בתלושים של החודש")

    payments_i, charges_i = _whole(pay), _whole(chg)
    problems = list(missing)
    if emp > 99999:
        problems.append("מספר עובדים חורג מ-5 ספרות")
    if len(str(payments_i)) > 10 or len(str(charges_i)) > 10:
        problems.append("סכום חורג מ-10 ספרות")
    if charges_i > payments_i:
        problems.append("חיוב גבוה מסך המשכורות (שגיאה 118)")
    if str(payments_i) == str(int(tax)) or str(charges_i) == str(int(tax)):
        problems.append("אחד הסכומים זהה למספר התיק (שגיאה 229)")
    if payment_method == 2 and charges_i > CREDIT_LIMIT:
        problems.append("תשלום באשראי מוגבל ל-50,000 ש\"ח (שגיאה 274)")
    zero_report = (not non_employment) and payments_i == 0 and charges_i == 0 and emp == 0
    if payment_method == 0 and charges_i != 0:
        problems.append("אמצעי תשלום 0 (דוח אפס) אך יש חיוב לתשלום")
    if charges_i == 0 and payment_method not in (0, 9):
        problems.append("אין סכום לתשלום: אמצעי התשלום צריך להיות 0 (דוח אפס) או 9")

    line = {"DeductionType": "00", "NonEmployment": 1 if non_employment else 0}
    line.update({"EmployeesNumber": emp, "Payments": payments_i, "Charges": charges_i})
    inp = {
        "RepresentNumber": rep, "TaxpayerNumber": tax, "Period": f"{int(year):04d}{int(month):02d}",
        "ActionCode": 1, "RegisterNumber": reg, "DeductionTypeCount": 1,
        "DeductionTypeList": [line],
        "PaymentAmount": charges_i,
        "PaymentDate": payment_date,
        "PaymentMethod": payment_method,
    }
    exact = {"payments": str(pay), "charges": str(chg)}
    return {
        "input": inp,
        "summary": {"employees": emp, "payments": payments_i, "charges": charges_i,
                    "exact_before_rounding": exact, "zero_report": zero_report},
        "problems": problems,
        "status": "ready_for_review" if not problems else "blocked",
        "sources": [SOURCE, GUIDE_SOURCE],
        "notes": NOTES,
    }
