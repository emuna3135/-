"""תבנית אקסל ריקה להעלאה (שלב 1): שלושה גיליונות + הסבר. שורת דוגמה אחת בכל גיליון, בנתוני דמו בדויים.
הכותרות זהות לאלה שהמערכת קוראת (employee_import.ALIASES ו-COLUMN_MAP בשרת)."""
import io

MONTH_HEAD = ["תעודת זהות", "שם עובד", "שכר יסוד", "שעות 125", "שעות 150", "בונוס", "נקודות זיכוי", "שנה", "חודש",
              "פטור ממס", "אחוז פנסיה עובד", "אחוז קרן השתלמות עובד", "ביטוח חיים", "שיטת מס", "ימי עבודה בחודש",
              "חופשה (ניצול/יתרה)", "מחלה (ניצול/יתרה)", "אופן תשלום", "ערך שעת עבודה רגילה",
              "מצטבר קודם: הכנסה חייבת", "מצטבר קודם: מס", "מצטבר קודם: הפקדות", "מצטבר קודם: ביטוח חיים",
              "מצטבר קודם: שכר לביטוח לאומי"]
MONTH_EXAMPLE = ["000000018", "דנה כהן (דוגמה)", 12000, 0, 0, 0, 2.75, 2026, 1, 0, 0.06, 0, 0, "cumulative",
                 "22 ימים", "0 / 10", "0 / 8", "העברה בנקאית", 65.93, None, None, None, None, None]
EMP_HEAD = ["תעודת זהות", "שם מלא", "מין", "תאריך לידה", "תאריך תחילת עבודה", "תושב", "שכר יסוד", "אחוז פנסיה עובד",
            "אחוז פנסיה מעסיק", "אחוז פיצויים מעסיק", "היקף משרה %", "שם משפחה", "שם פרטי", "רחוב ומספר בית", "עיר", "מיקוד", "מקבל קצבת זקנה"]
EMP_EXAMPLE = ["000000018", "דנה כהן (דוגמה)", "F", "1990-05-12", "2020-03-01", "כן", 12000, 0.06, 0.065, 0.06, 100,
               "כהן", "דנה", "הרצל 1", "חיפה", "33000", "לא"]
F101_HEAD = ["תעודת זהות", "שם עובד", "שנת מס", "תאריך חתימה", "סוג הכנסה", "הכנסה אחרת", "זיכוי כנגד הכנסה זו",
             "מצב משפחתי", "שנות לידה ילדים בחזקתו", "שנות לידה ילדים שלא בחזקתו", "מצבי חיים"]
F101_EXAMPLE = ["000000018", "דנה כהן (דוגמה)", 2026, "2026-01-05", "משרה עיקרית", "לא", "כאן", "רווק/ה", None, None, None]

EMPLOYER_HEAD = ["שם המעביד", "תיק ניכויים", "מספר תיק במס הכנסה", "טלפון", "מעמד משפטי", "מס מעסיקים", "מספר אגיד", "מספר מפעל",
                 "מספר זיהוי מעביד (ח.פ/ת.ז)", "סוג מזהה מעביד", "מזהה מתפעל", "איש קשר: שם פרטי", "איש קשר: שם משפחה",
                 "איש קשר: אימייל", "איש קשר: נייד"]
EMPLOYER_EXAMPLE = ["חברת דמו בע\"מ", "912345678", "515000000", "035551234", "חברה", "חייב", 0, None,
                    "515000000", "ח.פ", "000000000", "רות", "כהן", "demo@example.com", "0501111111"]

import employee_import as _ei
PENSION_HEAD = [v[0] for v in _ei.PENSION_FIELDS.values()]
_PEN_EX = {"id_number": "000000018", "fund_code": "0" * 30, "fund_type": "קרן פנסיה", "pension_kind": "מקיפה",
           "fund_name": "קרן פנסיה לדוגמה", "fund_no": "1", "nimaan_kind": "יצרן", "nimaan_id_type": "ח.פ",
           "nimaan_id": "510000000", "nimaan_at_producer": "1", "employer_at_producer": "123456", "masav": "12345678",
           "pay_method": "העברה בנקאית", "bank": 12, "branch": "600", "account": "0" * 18 + "12", "account_type": "001",
           "employer_acc_kind": "ישראלי", "collector_acc_kind": "ישראלי", "collector_bank": 10, "collector_branch": "100",
           "collector_account": "0" * 18 + "99", "policy": "12345", "emp_no": "1", "seif14": "כן, מתחילת העסקה", "maamad": "שכיר",
           "email": "dana@example.com", "mobile": "0501234567", "house_no": "1", "apartment": 0, "mikud": 3300000,
           "po_box": 0, "work_days": 22}
PENSION_EXAMPLE = [_PEN_EX.get(k) for k in _ei.PENSION_FIELDS]
PENSION_TEXT_COLS = ("תעודת זהות", "קוד מזהה קופה (30 ספרות)", "חשבון המעסיק (20 ספרות)", "חשבון הקולט (20 ספרות)",
                     "סניף המעסיק", "סניף הקולט", "סוג חשבון (3 ספרות)", "קוד מס\"ב", "מזהה הנמען אצל היצרן",
                     "מזהה המעסיק אצל הגוף המוסדי", "מזהה הגוף הנמען", "מספר קופה אצל המעסיק", "מספר עובד אצל המעסיק",
                     "מספר פוליסה או חשבון", "מספר בית")

NOTES = [
    "תבנית להעלאה: חמישה גיליונות. מלאו בנתוני ניסוי בלבד – נתונים בדויים, לא נתוני עובדים אמיתיים.",
    "שורת הדוגמה (דנה כהן) מופיעה בכל גיליון. אפשר להחליף אותה או למחוק אותה.",
    "תעודת זהות: 9 ספרות עם ספרת ביקורת תקינה (המערכת בודקת). עמודה זו צריכה להיות טקסט.",
    "גיליון 'תלושים לטעינה': נתוני החודש. גיליון 'עובדים': כרטיס העובד. גיליון 'טופס 101': מה שמולא בטופס 101.",
    "גיליון 'עובדים': שם משפחה, שם פרטי, רחוב, עיר ומיקוד הם אופציונליים וישמשו בדוח השנתי לרשות המסים (126). שם מלא לא מפוצל אוטומטית.",
    "גיליון 'מעביד': שורה אחת, ממלאים פעם אחת. פרטי המעביד לדוח השנתי (126): שם, תיק ניכויים (9 ספרות, מתחיל ב-9), תיק במס הכנסה, טלפון, מעמד משפטי (חברה/יחיד/שותפות/עמותה/רשות), מס מעסיקים (פטור/חייב). נשמר אוטומטית בהעלאה ולא צריך למלא שוב בשלב 4.",
    "גיליון 'פנסיה' (לקובץ הפנסיה, שלב 4): שורה לכל עובד בכל קופה. קוד הקופה, מזהי הגוף המוסדי, פרטי הבנק ומספר הפוליסה מגיעים מהגוף המוסדי; כל מה שחסר יסומן 'נדרש טיפול ידני' ולא ינוחש. סכומי ההפרשה, השכר והשיעורים נלקחים מהתלושים. קרן השתלמות עדיין לא נתמכת. בגיליון 'מעביד' יש עמודות נוספות לפנסיה (מזהה מעביד, איש קשר).",
    "מס מצטבר: המס מחושב לפי הכנסה מצטברת מתחילת השנה, ולכן כל חודש (מפברואר) דורש שהחודש הקודם כבר חושב במערכת; הקובץ ממוין אוטומטית לפי שנה וחודש. אם עוברים ממערכת אחרת באמצע השנה, ממלאים בשורת החודש הראשון את העמודות 'מצטבר קודם' (הכנסה חייבת, מס, הפקדות, ביטוח חיים, שכר לביטוח לאומי) מהתלוש האחרון של המערכת הקודמת; בחודשים הבאים משאירים אותן ריקות.",
    "מצב משפחתי: רווק/ה, נשוי/אה, גרוש/ה, אלמן/ה, פרוד/ה. 'מצבי חיים' לפי הצורך (למשל הורה יחיד, משלם מזונות).",
    "ערך שהמערכת לא מזהה יסומן בשגיאת שורה. היא לא מנחשת ערכים חסרים.",
]


def build_template() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    head_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Arial", size=11)
    fill = PatternFill("solid", fgColor="1F4E79")

    def sheet(ws, heads, example, text_cols=()):
        ws.sheet_view.rightToLeft = True
        for c, h in enumerate(heads, 1):
            x = ws.cell(1, c, h)
            x.font, x.fill = head_font, fill
            x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.column_dimensions[get_column_letter(c)].width = max(12, len(h) + 4)
        for c, v in enumerate(example, 1):
            x = ws.cell(2, c, v)
            x.font = body_font
            x.alignment = Alignment(horizontal="center")
            if heads[c - 1] in text_cols:
                x.number_format = "@"
        for r in range(3, 203):                       # עמודות טקסט נשארות טקסט גם בשורות חדשות
            for c, h in enumerate(heads, 1):
                if h in text_cols:
                    ws.cell(r, c).number_format = "@"
        ws.row_dimensions[1].height = 32
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "תלושים לטעינה"
    sheet(ws, MONTH_HEAD, MONTH_EXAMPLE, ("תעודת זהות",))
    sheet(wb.create_sheet("עובדים"), EMP_HEAD, EMP_EXAMPLE, ("תעודת זהות", "מיקוד"))
    sheet(wb.create_sheet("טופס 101"), F101_HEAD, F101_EXAMPLE, ("תעודת זהות",))
    sheet(wb.create_sheet("מעביד"), EMPLOYER_HEAD, EMPLOYER_EXAMPLE, ("תיק ניכויים", "מספר תיק במס הכנסה", "טלפון", "מספר מפעל", "מספר זיהוי מעביד (ח.פ/ת.ז)", "מזהה מתפעל", "איש קשר: נייד"))
    sheet(wb.create_sheet("פנסיה"), PENSION_HEAD, PENSION_EXAMPLE, PENSION_TEXT_COLS)
    h = wb.create_sheet("הסבר")
    h.sheet_view.rightToLeft = True
    h.column_dimensions["A"].width = 110
    for i, t in enumerate(NOTES, 1):
        h.cell(i, 1, t).font = body_font
        h.cell(i, 1).alignment = Alignment(wrap_text=True, vertical="top")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


MONTH_SHEET_HEAD = ["תעודת זהות", "שם עובד", "שנה", "חודש", "שעות 125", "שעות 150", "בונוס", "פטור ממס", "ניכויים אחרים", "שכר יסוד"]
MONTH_SHEET_NOTE = ("חודש חדש מוכן: כל העובדים הרשומים כבר כאן. השכר, הפנסיה, נקודות הזיכוי ושיטת המס נלקחים מכרטיס העובד ומטופס 101, ולכן לא צריך להקליד אותם. "
                    "ממלאים רק מה שחריג החודש: שעות נוספות, בונוס, פטור ממס, ניכויים אחרים. עמודת 'שכר יסוד' ריקה = השכר שבכרטיס; ממלאים אותה רק אם השכר החודש שונה. "
                    "שורה של עובד שלא עובד החודש: למחוק. עובד חדש: להוסיף קודם במסך העובדים.")


def build_month_sheet(employees, year, month) -> bytes:
    """employees: [(תעודת זהות, שם)]. קובץ אקסל עם שורה לכל עובד ועמודות משתנות ב-0. עמודת ת.ז כטקסט (לא מאבדת אפסים מובילים)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = "נתוני החודש"
    ws.sheet_view.rightToLeft = True
    head_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Arial", size=11)
    fill = PatternFill("solid", fgColor="1F4E79")
    for c, h in enumerate(MONTH_SHEET_HEAD, 1):
        x = ws.cell(1, c, h)
        x.font, x.fill = head_font, fill
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = max(12, len(h) + 4)
    ws.column_dimensions["B"].width = 24
    for r, (idn, name) in enumerate(employees, 2):
        vals = [str(idn), name, int(year), int(month), 0, 0, 0, 0, 0, None]
        for c, v in enumerate(vals, 1):
            x = ws.cell(r, c, v)
            x.font = body_font
            x.alignment = Alignment(horizontal="center")
            if c == 1:
                x.number_format = "@"
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"
    h = wb.create_sheet("הסבר")
    h.sheet_view.rightToLeft = True
    h.column_dimensions["A"].width = 110
    h.cell(1, 1, MONTH_SHEET_NOTE).font = body_font
    h.cell(1, 1).alignment = Alignment(wrap_text=True, vertical="top")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
