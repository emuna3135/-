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
from engine import BY_LAW, MANUAL, item

OFFICIAL_BTL = "אתר ביטוח לאומי"
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
    "reserve_monthly_max": {
        2025: (D("50695"), OFFICIAL_BTL_2025, BY_LAW),
        2026: (D("51910"), OFFICIAL_BTL, BY_LAW),
    },
}


def param(name, year):
    """מחזיר item(value, status, note). ערך חסר לשנה -> MANUAL."""
    row = PARAMS.get(name, {}).get(year)
    if row is None:
        return item(None, MANUAL, f"פרמטר {name} לא מוגדר לשנת {year}")
    value, source, status = row
    return item(value, status, f"מקור: {source}")
