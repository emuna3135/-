"""תבנית אקסל ריקה להעלאה (שלב 1): שלושה גיליונות + הסבר. שורת דוגמה אחת בכל גיליון, בנתוני דמו בדויים.
הכותרות זהות לאלה שהמערכת קוראת (employee_import.ALIASES ו-COLUMN_MAP בשרת)."""
import io

MONTH_HEAD = ["תעודת זהות", "שם עובד", "שכר יסוד", "שעות 125", "שעות 150", "בונוס", "נקודות זיכוי", "שנה", "חודש",
              "פטור ממס", "אחוז פנסיה עובד", "אחוז קרן השתלמות עובד", "ביטוח חיים", "שיטת מס", "ימי עבודה בחודש",
              "חופשה (ניצול/יתרה)", "מחלה (ניצול/יתרה)", "אופן תשלום", "ערך שעת עבודה רגילה"]
MONTH_EXAMPLE = ["000000018", "דנה כהן (דוגמה)", 12000, 0, 0, 0, 2.75, 2026, 1, 0, 0.06, 0, 0, "cumulative",
                 "22 ימים", "0 / 10", "0 / 8", "העברה בנקאית", 65.93]
EMP_HEAD = ["תעודת זהות", "שם מלא", "מין", "תאריך לידה", "תאריך תחילת עבודה", "תושב", "שכר יסוד", "אחוז פנסיה עובד",
            "אחוז פנסיה מעסיק", "אחוז פיצויים מעסיק", "היקף משרה %", "שם משפחה", "שם פרטי", "רחוב ומספר בית", "עיר", "מיקוד"]
EMP_EXAMPLE = ["000000018", "דנה כהן (דוגמה)", "F", "1990-05-12", "2020-03-01", "כן", 12000, 0.06, 0.065, 0.06, 100,
               "כהן", "דנה", "הרצל 1", "חיפה", "33000"]
F101_HEAD = ["תעודת זהות", "שם עובד", "שנת מס", "תאריך חתימה", "סוג הכנסה", "הכנסה אחרת", "זיכוי כנגד הכנסה זו",
             "מצב משפחתי", "שנות לידה ילדים בחזקתו", "שנות לידה ילדים שלא בחזקתו", "מצבי חיים"]
F101_EXAMPLE = ["000000018", "דנה כהן (דוגמה)", 2026, "2026-01-05", "משרה עיקרית", "לא", "כאן", "רווק/ה", None, None, None]

NOTES = [
    "תבנית להעלאה: שלושה גיליונות. מלאו בנתוני ניסוי בלבד – נתונים בדויים, לא נתוני עובדים אמיתיים.",
    "שורת הדוגמה (דנה כהן) מופיעה בכל גיליון. אפשר להחליף אותה או למחוק אותה.",
    "תעודת זהות: 9 ספרות עם ספרת ביקורת תקינה (המערכת בודקת). עמודה זו צריכה להיות טקסט.",
    "גיליון 'תלושים לטעינה': נתוני החודש. גיליון 'עובדים': כרטיס העובד. גיליון 'טופס 101': מה שמולא בטופס 101.",
    "גיליון 'עובדים': שם משפחה, שם פרטי, רחוב, עיר ומיקוד הם אופציונליים וישמשו בדוח השנתי לרשות המסים (126). שם מלא לא מפוצל אוטומטית.",
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
    h = wb.create_sheet("הסבר")
    h.sheet_view.rightToLeft = True
    h.column_dimensions["A"].width = 110
    for i, t in enumerate(NOTES, 1):
        h.cell(i, 1, t).font = body_font
        h.cell(i, 1).alignment = Alignment(wrap_text=True, vertical="top")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
