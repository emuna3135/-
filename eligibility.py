"""התאמת ביטוח לאומי ובריאות לגיל ולסוג העובד. פונקציות טהורות (בלי FastAPI), נבדקות ב-test_eligibility.py.

המערכת מחשבת ביטוח לאומי ובריאות רק בשיעורי 'שכיר תושב ישראל בן 18 עד גיל פרישה' (btl.gov.il/Insurance/Rates).
לעובד מתחת ל-18, בגיל פרישה או מעליו, ולעובד זר, יש בביטוח הלאומי שיעורים או פטורים אחרים (אגרת למעסיק בל/654;
מסמך הלשכה המשפטית על עובדים זרים). עד שיתועדו אצלנו מכל הטבלאות, המערכת לא מנחשת: הסעיף מסומן 'נדרש טיפול ידני'.
גיל פרישה: גברים 67; נשים 62 עד 65 לפי תאריך לידה (ביטוח לאומי). כדי לא לפספס, מסמנים אישה מגיל 62."""
import datetime

RETIREMENT_AGE_MEN = 67
RETIREMENT_AGE_WOMEN_MIN = 62       # לנשים הגיל בפועל 62-65 לפי שנת לידה; סימון מגיל 62 הוא זהיר
FOREIGN_TYPES = ("foreign_legal", "foreign_nursing", "foreign_other")


def _last_day(year: int, month: int) -> datetime.date:
    nxt = datetime.date(year + (month == 12), month % 12 + 1, 1)
    return nxt - datetime.timedelta(days=1)


def age_at_end_of_month(birth_date, year: int, month: int):
    """גיל בסוף החודש (שלם). birth_date בפורמט YYYY-MM-DD או date. חסר/לא תקין -> None."""
    if not birth_date:
        return None
    try:
        b = birth_date if isinstance(birth_date, datetime.date) else datetime.date.fromisoformat(str(birth_date)[:10])
    except ValueError:
        return None
    end = _last_day(year, month)
    return end.year - b.year - ((end.month, end.day) < (b.month, b.day))


# טבלת גיל פרישה לנשים לפי שנת לידה (חודשים). מקור: ביטוח לאומי, חוברת "אזרח ותיק" (btl.gov.il/Publications/booklet/hebrew_booklet/Documents/EzrahVatik.pdf);
# עד דצמבר 1959: 62 (חוק גיל פרישה). 1970 ואילך: 65.
WOMEN_RETIREMENT_MONTHS = {1960: 62 * 12 + 4, 1961: 62 * 12 + 8, 1962: 63 * 12, 1963: 63 * 12 + 3, 1964: 63 * 12 + 6,
                           1965: 63 * 12 + 9, 1966: 64 * 12, 1967: 64 * 12 + 3, 1968: 64 * 12 + 6, 1969: 64 * 12 + 9}
MEN_RETIREMENT_AGE = 67
OLD_AGE_PENSION_ENTITLEMENT_AGE = 70    # "גיל הזכאות": מגיל 70 לכולם, ללא מבחן הכנסות (שורה בטבלת טופס 102: "70 ומעלה" 0.61%/2.12% מעסיק בלבד)

from decimal import Decimal as _D
# שיעורי 2026 (בתוקף מ-1.1.2025 / 1.2.2025 לפי btl.gov.il/Insurance/Maasik/MToshavYisrael/Pages/DBSchirim.aspx, טופס 102, נקרא 26.11.2026).
# שיעור עובד ב"ל = (סך עובד בטבלה) פחות בריאות (3.23% / 5.17%): הטבלה מפרטת סך עובד, והפיצול מחושב כהפרש. מעסיק: כמו בטבלה.
_CATEGORIES = {
    "exempt_employee": dict(label="בן/בת פחות מ-18, או מקבל קצבת זקנה, או בן 70 ומעלה: מעסיק בלבד",
                            ni=(_D("0"), _D("0")), health=(_D("0"), _D("0")), er=(_D("0.0061"), _D("0.0212"))),
    "age67_no_pension": dict(label="גיל 67 עד 70 שאינו מקבל קצבת זקנה (גברים ונשים)",
                             ni=(_D("0.0070"), _D("0.0486")), health=(_D("0.0323"), _D("0.0517")), er=(_D("0.0413"), _D("0.0696"))),
    "woman_between": dict(label="אישה בין גיל הפרישה שלה לגיל 67, שאינה מקבלת קצבת זקנה",
                          ni=(_D("0.0072"), _D("0.0507")), health=(_D("0.0323"), _D("0.0517")), er=(_D("0.0417"), _D("0.0712"))),
}


_CATEGORIES.update({
    # תושב חוץ (דף "שיעורי דמי הביטוח לתושב חוץ", btl.gov.il, מ-1.1.2026): ביטוח לאומי בלבד, בלי בריאות
    "nonresident": dict(src="btl.gov.il, שיעורי תושב חוץ מ-1.1.2026", src_er="btl.gov.il, שיעורי תושב חוץ מ-1.1.2026", label="עובד זר (תושב חוץ): ביטוח לאומי בלבד", ni=(_D("0.001"), _D("0.0087")), health=(_D("0"), _D("0")),
                        er=(_D("0.0075"), _D("0.0265"))),
    # עובד ממדינת אמנה: "לפי האחוזים המלאים, פחות אחוזי דמי ביטוח בריאות" (חוזר ב"ל, עדכון 2015; חוזר 1680/2026 סעיפים 3.2, 4.2)
    "treaty_no_health": dict(src="btl.gov.il, חוזר עובדים זרים ממדינות אמנה וחוזר 1680/2026", src_er="btl.gov.il, חוזר עובדים זרים ממדינות אמנה וחוזר 1680/2026", label="עובד זר ממדינת אמנה: כמו תושב ישראל בלי בריאות", ni=(_D("0.0104"), _D("0.07")),
                             health=(_D("0"), _D("0")), er=(_D("0.0451"), _D("0.076"))),
    # עובד זר בסיעוד/משק בית: 3.6% מהשכר, המעסיק בלבד (btl.gov.il/Insurance/Rates "עובד משק בית"; MasikOvedSARAM: 3.6% מינואר 2025)
    "nursing_foreign": dict(src="btl.gov.il, עובד זר לצורך טיפול סיעודי, 3.6% מ-2025", src_er="btl.gov.il, עובד זר לצורך טיפול סיעודי, 3.6% מ-2025", label="עובד זר בסיעוד: 3.6% מהשכר, מעסיק בלבד", ni=(_D("0"), _D("0")), health=(_D("0"), _D("0")),
                            er=(_D("0.036"), _D("0.036"))),
})

# מדינות האמנה לפי btl.gov.il/benefits/International_Conventions (נקרא 26.11.2026), מפתח: שם בעברית
TREATY_COUNTRIES = {"אוסטריה", "אורוגוואי", "איטליה", "ארגנטינה", "בולגריה", "בלגיה", "בריטניה", "גרמניה", "דנמרק", "הולנד", "נורווגיה",
                    "סלובקיה", "פולין", "פינלנד", "צ'כיה", "צרפת", "רומניה", "רוסיה", "שוודיה", "שווייץ"}
# ארבע מדינות שבהן העובד מבוטח בשלושה ענפים בלבד (חוזר 1680/2026): השיעורים לא מפורטים
THREE_BRANCH_COUNTRIES = {"ארגנטינה", "בולגריה", "פולין", "רומניה"}
_COUNTRY_ALIASES = {"שוויץ": "שווייץ", "שוויץ ": "שווייץ", "הולנד": "הולנד", "ארה\"ב": "ארצות הברית", "בריטניה": "בריטניה",
                    "אנגליה": "בריטניה", "צ׳כיה": "צ'כיה", "צכיה": "צ'כיה", "צ'כיה": "צ'כיה", "רוסיה": "רוסיה"}


def foreign_category(worker_type, origin_country):
    """עובד זר: (קטגוריה|None, סיבה לטיפול ידני|None). None,None = לא עובד זר."""
    if worker_type not in FOREIGN_TYPES:
        return None, None
    if worker_type == "foreign_nursing":
        return "nursing_foreign", None
    c = str(origin_country or "").strip()
    c = _COUNTRY_ALIASES.get(c, c)
    if not c:
        return None, ("עובד זר: חסרה מדינת מוצא. עובד ממדינת אמנה משלם כמו תושב ישראל בלי בריאות, וכל השאר לפי שיעורי תושב חוץ. "
                      "יש למלא 'מדינת מוצא' בטופס 101. נדרש טיפול ידני עד אז")
    if c in THREE_BRANCH_COUNTRIES:
        return None, (f"עובד ממדינת אמנה ({c}) מבוטח בשלושה ענפים בלבד (חוזר ביטוח לאומי 1680/2026) והשיעורים לא מפורטים בחוזר. נדרש טיפול ידני")
    if c in TREATY_COUNTRIES:
        return "treaty_no_health", None
    return "nonresident", None


def women_retirement_months(birth_year: int):
    if birth_year < 1960:
        return 62 * 12
    return WOMEN_RETIREMENT_MONTHS.get(birth_year, 65 * 12)


def _age_months(birth, year, month):
    end = _last_day(year, month)
    m = (end.year - birth.year) * 12 + end.month - birth.month
    return m - (1 if end.day < birth.day else 0)


def ni_category(birth_date, gender, old_age_pension, year: int, month: int):
    """קטגוריית ביטוח לאומי של שכיר תושב. מחזיר (קטגוריה|None, סיבה לטיפול ידני|None).
    None,None = שכיר רגיל 18 עד גיל פרישה (השיעורים הרגילים של המערכת)."""
    if not birth_date:
        return None, None
    try:
        b = birth_date if isinstance(birth_date, datetime.date) else datetime.date.fromisoformat(str(birth_date)[:10])
    except ValueError:
        return None, None
    am = _age_months(b, year, month)
    if am < 18 * 12:
        return "exempt_employee", None
    g = str(gender or "").upper()
    retire = MEN_RETIREMENT_AGE * 12 if g == "M" else women_retirement_months(b.year)
    if am < retire:
        return None, None
    if am >= OLD_AGE_PENSION_ENTITLEMENT_AGE * 12:
        return "exempt_employee", None
    if old_age_pension is True:
        return "exempt_employee", None
    if old_age_pension is None:
        return None, ("העובד/ת בגיל פרישה (לפני גיל 70): השיעורים תלויים בשאלה אם מקבל/ת קצבת זקנה. "
                      "יש למלא 'מקבל קצבת זקנה' (כן/לא) בגיליון העובדים. נדרש טיפול ידני עד אז")
    if am >= 67 * 12:
        return "age67_no_pension", None
    return ("woman_between", None) if g == "F" else (None, None)


def ni_health_issue(birth_date, gender, worker_type, year: int, month: int):
    """מחזיר {'ni','health': סיבה ידנית|None, 'missing_birth': bool}. עובד זר מטופל ב-foreign_category."""
    return {"ni": None, "health": None, "missing_birth": not birth_date}


def area_resident_issue(worker_type):
    if worker_type == "area_resident":
        return ("תושב האזור: לפי ביטוח לאומי, מעסיק של תושב הרשות הפלסטינית/יהודה ושומרון בתוך ישראל מדווח ומשלם דרך רשות האוכלוסין, "
                "וביישובים ואתרים צבאיים באזור חלים שיעורים נפרדים (0.71%/2.49% מעסיק, 0.07%/0.61% עובד). מקום העבודה לא ידוע במערכת; נדרש טיפול ידני")
    return None


def is_start_month(start_date, year: int, month: int) -> bool:
    """האם חודש החישוב הוא חודש תחילת העבודה (אז אין חודשים קודמים אצל המעסיק)."""
    if not start_date:
        return False
    try:
        st = start_date if isinstance(start_date, datetime.date) else datetime.date.fromisoformat(str(start_date)[:10])
    except ValueError:
        return False
    return (st.year, st.month) == (year, month)
