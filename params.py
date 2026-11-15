"""
טבלת פרמטרים לפי שנה לגמלאות ביטוח לאומי. שנה חדשה = שורה חדשה בטבלה, בלי לשנות קוד.
לכל ערך: מקור ורמת אימות. ערך חסר לשנה = MANUAL (המערכת לא מנחשת ולא מעתיקה משנה אחרת).

מקורות:
  OFFICIAL_BTL - אתר הביטוח הלאומי (btl.gov.il), נבדק באוקטובר 2026. מופיעים שם רק ערכי 2026.
  COURSE       - תרגילי הקורס. ערכי 2025 עקביים עם ערכי 2026 הרשמיים: שלושתם עלו ב-2.397%
                 (1,283.50 -> 1,314.25, 9,632 -> 9,863, 50,695 -> 51,910), אך לא נבדקו מול מקור ל-2025.
"""
from decimal import Decimal as D
from engine import BY_LAW, COURSE, MANUAL, item

OFFICIAL_BTL = "אתר ביטוח לאומי"
COURSE_SRC = "קורס, עקבי עם ערכי 2026 הרשמיים"

# שם פרמטר -> {שנה: (ערך, מקור, סטטוס)}
PARAMS = {
    # תקרת דמי פגיעה ליום
    "injury_daily_cap": {
        2025: (D("1283.50"), COURSE_SRC, COURSE),
        2026: (D("1314.25"), OFFICIAL_BTL, BY_LAW),
    },
    # תגמול מילואים חודשי: מינימום ומקסימום (מקסימום = פי 5 מסכום הבסיס; מינימום = 95% ממנו)
    "reserve_monthly_min": {
        2025: (D("9632"), COURSE_SRC, COURSE),
        2026: (D("9863"), OFFICIAL_BTL, BY_LAW),
    },
    "reserve_monthly_max": {
        2025: (D("50695"), COURSE_SRC, COURSE),
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
