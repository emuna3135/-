"""
טבלת פרמטרים לפי שנה לגמלאות ביטוח לאומי. שנה חדשה = שורה חדשה בטבלה, בלי לשנות קוד.
לכל ערך: מקור ורמת אימות. ערך חסר לשנה = MANUAL (המערכת לא מנחשת ולא מעתיקה משנה אחרת).

מקורות:
  OFFICIAL_BTL - אתר הביטוח הלאומי (btl.gov.il), נבדק באוקטובר 2026. מופיעים שם רק ערכי 2026.
  OFFICIAL_BTL_2025 - ביטוח לאומי, דוח שנתי 2025 (פרק עבודה: דמי פגיעה "בינואר 2025 - 1,283.50 ש"ח ליום"; פרק מילואים:
                 "התגמול המינימלי ב-2025 היה 321.07 ש"ח ליום", x30 = 9,632) ואגרת למעסיק ינואר 2025 (הכנסה מרבית 50,695 = פי 5 מהסכום
                 הבסיסי 10,139 לפי תקציב ב"ל 2025). נקראו 16.11.2026.
"""
from decimal import Decimal as D
from engine import ACCOUNTANT, BY_LAW, MANUAL, item

OFFICIAL_BTL = "אתר ביטוח לאומי"
OFFICIAL_YALKUT_14863 = "ילקוט הפרסומים 14863, 18.8.2026: צו הרחבה בדבר השתתפות המעסיק בהוצאות הבראה ונופש (הסכם 7011/2026), סעיף 3, נחתם ע''י שר העבודה 16.8.2026"
OFFICIAL_BTL_2025 = "ביטוח לאומי: דוח שנתי 2025 ואגרת למעסיק 01.2025"

# שם פרמטר -> {שנה: (ערך, מקור, סטטוס)}
PARAMS = {
    # תקרת דמי פגיעה ליום
    "injury_daily_cap": {
        2025: (D("1283.50"), OFFICIAL_BTL_2025, BY_LAW),
        2026: (D("1314.25"), OFFICIAL_BTL, BY_LAW),
    },
    # תגמול מילואים חודשי: מינימום ומקסימום (מקסימום = פי 5 מסכום הבסיס; מינימום = 95% ממנו)
    "reserve_monthly_min": {
        2025: (D("9632"), OFFICIAL_BTL_2025, BY_LAW),
        2026: (D("9863"), OFFICIAL_BTL, BY_LAW),
    },
    # קצבת שמירת היריון: מקסימום ליום (btl.gov.il Risk_Pregnancy, "החל ב-01.01.2026"); לשנים אחרות לא נמצא ערך רשמי -> MANUAL
    "pregnancy_daily_cap": {
        2026: (D("350.47"), OFFICIAL_BTL, BY_LAW),
    },
    # מחיר יום הבראה, מגזר פרטי. לשנת ההבראה 2026 (בלבד): 451.50 לפי הצו ברשומות. ימי הזכאות לפי ותק והפחתות 2025 אינם בצו זה (סעיפים 1,2,5,6 "לא הורחב") -> לא נקראו ממקור רשמי.
    "recreation_day_value": {
        2026: (D("451.50"), OFFICIAL_YALKUT_14863, BY_LAW),
    },
    "reserve_monthly_max": {
        2025: (D("50695"), OFFICIAL_BTL_2025, BY_LAW),
        2026: (D("51910"), OFFICIAL_BTL, BY_LAW),
    },
}


# שכבת שינוי של חשב השכר (הכפתור "שנה"): הערך שהוא מזין מחליף את ערך החוק בחישוב, מסומן "עפ"י רואת חשבון" ונשמר יחד עם הסיבה.
# נטען לפי בקשה (משרד אחד): with use_overrides({(name, year): {"value": ..., "reason": ..., "by": ..., "at": ...}}):
import contextlib
import contextvars
from decimal import InvalidOperation

_OVERRIDES = contextvars.ContextVar("param_overrides", default={})


@contextlib.contextmanager
def use_overrides(overrides):
    token = _OVERRIDES.set(dict(overrides or {}))
    try:
        yield
    finally:
        _OVERRIDES.reset(token)


def param(name, year):
    """מחזיר item(value, status, note). ערך חסר לשנה -> MANUAL. אם החשב שינה את הערך: הערך שלו, סטטוס עפ"י רואת חשבון, וערך החוק נשמר בהערה."""
    row = PARAMS.get(name, {}).get(year)
    ov = _OVERRIDES.get().get((name, year))
    if ov is not None:
        try:
            ov_value = D(str(ov["value"]))
        except (InvalidOperation, KeyError, TypeError):
            return item(None, MANUAL, f"שינוי ידני לפרמטר {name} לא תקין")
        law = f"ערך החוק: {row[0]} ({row[1]})" if row else "אין ערך חוק לשנה זו"
        return item(ov_value, ACCOUNTANT,
                    f"שונה ע\"י חשב השכר ({ov.get('by', '?')}, {ov.get('at', '?')}): {ov.get('reason', 'ללא סיבה')}. {law}")
    if row is None:
        return item(None, MANUAL, f"פרמטר {name} לא מוגדר לשנת {year}")
    value, source, status = row
    return item(value, status, f"{source} | מעודכן ל-{year}")


SYSTEM_YEAR = 2026   # שנת המערכת: ערכים משתנים חייבים להיות מעודכנים לשנה זו


def params_status(system_year=SYSTEM_YEAR):
    """
    חלק משתנה (ערכים שמתעדכנים כל שנה): מדווח לכל פרמטר אם יש ערך רשמי לשנת המערכת.
    חסר ערך לשנה -> דרושה התערבות ידנית (המערכת לא מעתיקה משנה קודמת). אין עדכון אוטומטי שמחליף ערכים בלי אישור אנושי.
    """
    rows, missing = [], []
    for name, years in PARAMS.items():
        row = years.get(system_year)
        if row is None:
            missing.append(name)
            rows.append({"name": name, "year": system_year, "value": None, "source": None, "status": MANUAL,
                         "note": "אין ערך לשנה זו: נדרשת התערבות ידנית"})
        else:
            value, source, status = row
            rows.append({"name": name, "year": system_year, "value": str(value), "source": source, "status": status,
                         "note": ""})
    return {"system_year": system_year,
            "up_to_date": not missing,
            "label": (f"מעודכן ל-{system_year}" if not missing else f"לא מעודכן ל-{system_year}: נדרשת התערבות ידנית ({len(missing)} פרמטרים)"),
            "missing": missing, "params": rows}
