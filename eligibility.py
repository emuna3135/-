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


def ni_health_issue(birth_date, gender, worker_type, year: int, month: int):
    """מחזיר {'ni': סיבה|None, 'health': סיבה|None, 'missing_birth': bool}. סיבה = יש לטפל ידנית."""
    out = {"ni": None, "health": None, "missing_birth": False}
    age = age_at_end_of_month(birth_date, year, month)
    if age is None:
        out["missing_birth"] = True
    elif age < 18:
        out["ni"] = out["health"] = (f"העובד מתחת לגיל 18 (גיל {age}): לביטוח לאומי שיעורים נפרדים לשכיר שטרם מלאו לו 18 "
                                      "(אגרת למעסיק בל/654). לא ממומש; נדרש טיפול ידני")
    else:
        g = str(gender or "").upper()
        limit = RETIREMENT_AGE_MEN if g == "M" else RETIREMENT_AGE_WOMEN_MIN
        if age >= limit:
            out["ni"] = out["health"] = (f"העובד בגיל פרישה או קרוב אליו (גיל {age}): לשכיר בגיל פרישה שיעורים או פטור אחרים "
                                          "(למשל מקבל קצבת זקנה פטור; לנשים גיל הפרישה 62-65 לפי תאריך לידה). "
                                          "לא ממומש; נדרש טיפול ידני")
    if worker_type in FOREIGN_TYPES:
        out["health"] = ("עובד זר אינו מבוטח לפי חוק ביטוח בריאות ממלכתי (מסמך הלשכה המשפטית, ביטוח לאומי; מ-2002-2005): "
                         "לא מנכים ביטוח בריאות בשיעור רגיל. נדרש אימות מול רואת חשבון וטיפול ידני")
    return out


def is_start_month(start_date, year: int, month: int) -> bool:
    """האם חודש החישוב הוא חודש תחילת העבודה (אז אין חודשים קודמים אצל המעסיק)."""
    if not start_date:
        return False
    try:
        s = start_date if isinstance(start_date, datetime.date) else datetime.date.fromisoformat(str(start_date)[:10])
    except ValueError:
        return False
    return (s.year, s.month) == (year, month)
