"""
גמלאות ביטוח לאומי שמעסיק מעורב בהן: דמי פגיעה (החזר מעסיק), גמלת שמירת היריון,
תגמול מילואים, ושכר חודשי רגיל לפי סעיף 335.

כללי החישוב נלמדו מתרגילי הקורס (עקביים בעשרות תרגילים) ולכן הסטטוס COURSE:
לא נבדקו מול החוק. הפרמטרים לפי שנה נמצאים ב-params.py, ומקור כל אחד שם.
כל מקרה שהקורס לא לימד -> MANUAL (המערכת לא מנחשת). אין עיגול בין שלבים: עיגול לאגורה רק בסוף.
"""
from datetime import date
from decimal import Decimal as D

from engine import COURSE, MANUAL, item, r2
from params import param


def _manual(note):
    return item(None, MANUAL, note)


def _d(x):
    return D(str(x))


# ---------------------------------------------------------------------------
# דמי פגיעה: החזר מעסיק למוסד
# ---------------------------------------------------------------------------
INJURY_RATE = D("0.75")
INJURY_EMPLOYER_DAYS = 12   # המעסיק מחזיר 12 ימים (מאמר ביזפורטל המצטט את הנחיית הביטוח הלאומי: 12 ימי ההיעדרות הראשונים על חשבון המעסיק)


def injury_employer_reimbursement(year, income_3m_total, absence_days):
    """
    יומי = min(הכנסה ב-3 החודשים המלאים שקדמו / 90 x 75%, תקרה יומית); החזר = יומי x 12.
    היעדרות מעל 12 ימים לא משנה את ההחזר (נבדק ב-10 תרגילים, כולל 13 ו-40 ימים).
    היעדרות קצרה מ-12 ימים: הקורס לא לימד -> MANUAL.
    חישוב חלופי של האתר (חודש הפגיעה עד יום הפגיעה + שני חודשים לפניו, הגבוה חל) לא ממומש:
    הקורס מלמד רק 3 חודשים מלאים, ולכן אם החלופה גבוהה יותר יש להזין ידנית.
    """
    cap = param("injury_daily_cap", year)
    if cap["value"] is None:
        return _manual(cap["note"])
    if int(absence_days) < INJURY_EMPLOYER_DAYS:
        return _manual("היעדרות קצרה מ-12 ימים: כלל ההחזר לא נלמד")
    raw = _d(income_3m_total) * INJURY_RATE / 90
    daily = min(raw, cap["value"])
    res = item(r2(daily * INJURY_EMPLOYER_DAYS), COURSE,
               ("תקרה יומית חלה. " if raw > cap["value"] else "") + cap["note"] +
               ". בסיס: 3 חודשים מלאים בלבד (החלופה של האתר לא ממומשת)")
    res["daily"] = r2(daily)
    return res


# ---------------------------------------------------------------------------
# גמלת שמירת היריון
# ---------------------------------------------------------------------------
PREGNANCY_HIGH_AVG_MONTHLY = D("20000")   # מעל זה התקרה לא נלמדה -> MANUAL


def pregnancy_rest_daily(monthly_incomes_last6):
    """
    גמלה יומית = max(הכנסה ב-3 החודשים האחרונים / 90, הכנסה ב-6 החודשים האחרונים / 180). ללא אחוז (100%).
    הקלט: 6 הכנסות חודשיות חייבות בדמי ביטוח, מהישנה לחדשה, מ-6 החודשים שקדמו ליום הקובע.
    תשלום נוסף (בונוס, ביגוד, פדיון חופשה) נכנס במלואו לחודש שבו שולם, בלי פריסה.
    מספר ימי השמירה לא משפיע על הסכום היומי. תקרה: לא נלמדה.
    """
    inc = [_d(x) for x in monthly_incomes_last6]
    if len(inc) != 6:
        return _manual("נדרשות בדיוק 6 הכנסות חודשיות")
    if sum(inc) / 6 > PREGNANCY_HIGH_AVG_MONTHLY:
        return _manual("הכנסה גבוהה: תקרת גמלת שמירת היריון לא נלמדה")
    three = sum(inc[3:]) / 90
    six = sum(inc) / 180
    res = item(r2(max(three, six)), COURSE,
               "הגבוה מבין 3 חודשים/90 ו-6 חודשים/180; תקרה לא נלמדה")
    res["basis"] = "3 חודשים" if three >= six else "6 חודשים"
    return res


# ---------------------------------------------------------------------------
# תגמול מילואים
# ---------------------------------------------------------------------------
RESERVE_DAYS_THRESHOLD = 75


def count_days_for_75(worked=0, shabbat_holidays=0, vacation_paid=0, vacation_unpaid=0,
                      sick_or_accident=0, mourning=0):
    """ימים שנספרים לסף 75 הימים (עובד שעתי/יומי): כל הסוגים הללו, לא רק ימי עבודה בפועל."""
    return int(worked) + int(shabbat_holidays) + int(vacation_paid) + int(vacation_unpaid) \
        + int(sick_or_accident) + int(mourning)


def reserve_via_employer(worker_type, counted_days=None):
    """
    האם התגמול משולם דרך המעסיק. עובד חודשי: תמיד (גם אם התחיל יום לפני השירות).
    עובד שעתי/יומי: רק אם נספרו לפחות 75 ימים ב-3 החודשים שקדמו לשירות; אחרת ישירות מהמוסד.
    """
    if worker_type == "monthly":
        return item(True, COURSE, "עובד חודשי: דרך המעסיק, ללא סף ימים")
    if worker_type in ("hourly", "daily"):
        if counted_days is None:
            return _manual("חסר מספר ימים לסף 75")
        ok = int(counted_days) >= RESERVE_DAYS_THRESHOLD
        return item(ok, COURSE, f"{counted_days} ימים נספרו; סף {RESERVE_DAYS_THRESHOLD}" +
                    ("" if ok else ". התגמול משולם ישירות מהמוסד"))
    return _manual(f"סוג עובד לא מוכר: {worker_type}")


def _reserve_daily_raw(year, income_3m_total):
    mn, mx = param("reserve_monthly_min", year), param("reserve_monthly_max", year)
    if mn["value"] is None or mx["value"] is None:
        return None, _manual(mn["note"] if mn["value"] is None else mx["note"])
    raw = _d(income_3m_total) / 90
    return max(min(raw, mx["value"] / 30), mn["value"] / 30), None


def reserve_daily(year, income_3m_total):
    """תגמול יומי = הכנסה ב-3 החודשים שקדמו / 90, בין מינימום חודשי/30 למקסימום חודשי/30."""
    daily, err = _reserve_daily_raw(year, income_3m_total)
    if err:
        return err
    return item(r2(daily), COURSE, "הכנסה/90, מוגבל למינימום ולמקסימום היומיים (חודשי/30)")


def reserve_pay_period(year, income_3m_total, service_days):
    """תגמול לתקופה = תגמול יומי (ללא עיגול) x ימי שירות; עיגול לאגורה רק בסוף."""
    daily, err = _reserve_daily_raw(year, income_3m_total)
    if err:
        return err
    return item(r2(daily * int(service_days)), COURSE,
                "הכנסה/90 x ימי שירות; רצפה ותקרה יומיות = חודשי/30 (לתקופה חלקית זו הנחה: נבדק רק בחודש מלא ובתרגיל בלי חריגה)")


def reserve_full_month(year, monthly_calc_amount):
    """חודש שירות מלא: הסכום המחושב מוגבל בין מינימום חודשי למקסימום חודשי."""
    mn, mx = param("reserve_monthly_min", year), param("reserve_monthly_max", year)
    if mn["value"] is None or mx["value"] is None:
        return _manual(mn["note"] if mn["value"] is None else mx["note"])
    v = max(min(_d(monthly_calc_amount), mx["value"]), mn["value"])
    return item(r2(v), COURSE, "הגבלה לטווח [מינימום, מקסימום] חודשי")


# ---------------------------------------------------------------------------
# סעיף 335: שכר חודשי רגיל
# ---------------------------------------------------------------------------
# הרף שמעליו תשלום נוסף נפרס לא ידוע (הפתרונות אומרים "הרף שנקבע" ולא נוקבים בו).
# מהתרגילים: לא נפרסו 1,400 (שכר 21,900) ו-1,560 (שכר 17,500). נפרסו 1,800 (שכר 18,600) ומעלה.
# שתי השערות מתאימות: סכום קבוע בין 1,560 ל-1,800, או אחוז מהשכר בין 8.9% ל-9.7%.
# לכן מכריעים רק כשההכרעה זהה בשתי ההשערות. אחרת MANUAL. אפשר להעביר threshold קבוע לעקיפה.
NOT_SPREAD_MAX_TOTAL = D("1560")
NOT_SPREAD_PCT = (D("1560"), D("17500"))   # סכום/שכר <= 1560/17500
SPREAD_MIN_TOTAL = D("1800")
SPREAD_PCT = (D("1800"), D("18600"))       # סכום/שכר >= 1800/18600


def months_from_start(start, pay_year, pay_month):
    """חודשים מתחילת העבודה עד חודש התלוש כולל (חודשי היעדרות נספרים)."""
    return (pay_year - start.year) * 12 + (pay_month - start.month) + 1



# ---------------------------------------------------------------------------
# רף הפריסה לפי החוק (תקנה 5 לתקנות ביטוח לאומי (תשלום ופטור), תיקון 1.6.2014; חוזר 1455):
# תשלום נוסף שאינו נמוך מ-25% משכר המינימום החודשי שבתוקף בחודש התשלום נפרס.
# שכר המינימום החודשי: 5,880.02 עד 31.3.2025; 6,247.67 מ-1.4.2025 (מלם + תלושי חינוך, מקור משני);
# 6,443.85 מ-1.4.2026 (דוגמת חוזר ב"ל; מקור ראשוני טרם נקרא). לא ידוע: איזה חודש קובע (Q25) -> כאן חודש התשלום.
# ---------------------------------------------------------------------------
MIN_WAGE_MONTHLY = [  # (מתאריך כולל כ-(שנה, חודש), סכום)
    ((2025, 1), D("5880.02")),
    ((2025, 4), D("6247.67")),
    ((2026, 4), D("6443.85")),
]
SPREAD_MIN_WAGE_PCT = D("0.25")


def min_wage_monthly(year, month):
    cur = None
    for (y, m), v in MIN_WAGE_MONTHLY:
        if (year, month) >= (y, m):
            cur = v
    return cur


def spread_threshold(year, month):
    """25% משכר המינימום החודשי בחודש התשלום. לפני 1.1.2025 -> MANUAL (לא נבדק)."""
    mw = min_wage_monthly(year, month)
    if mw is None:
        return _manual("שכר מינימום לחודש הזה לא הוזן: הרף לא ידוע")
    return item(r2(mw * SPREAD_MIN_WAGE_PCT), "לפי חוק - לא נבדק מול תלוש",
                f"25% x שכר מינימום {mw}; חודש התשלום קובע (Q25 פתוחה); שכר המינימום מקור משני")


BELOW_THRESHOLD_RULES = ("add_in_full", "ignore")


def regular_monthly_wage_335(regular_wage, extra_payments, start_date, pay_year, pay_month,
                             threshold=None, below_threshold_rule="add_in_full"):
    """
    שכר חודשי רגיל = שכר רגיל + תשלומים נוספים / מחלק, כשסכום התשלומים הנוספים עולה על הרף.
    מחלק = min(12, חודשים מתחילת העבודה עד חודש התלוש כולל). תשלום שלא עולה על הרף לא נפרס.
    start_date חייב להיות 1 לחודש (התחלה באמצע חודש לא נלמדה -> MANUAL).
    """
    if below_threshold_rule not in BELOW_THRESHOLD_RULES:
        return _manual(f"below_threshold_rule לא מוכר: {below_threshold_rule}")
    wage = _d(regular_wage)
    total = sum((_d(x) for x in extra_payments), D(0))
    if not isinstance(start_date, date):
        return _manual("start_date חייב להיות date")
    if start_date.day != 1:
        return _manual("התחלת עבודה באמצע חודש: ספירת חודשים לא נלמדה")
    months = months_from_start(start_date, pay_year, pay_month)
    if months < 1:
        return _manual("חודש התלוש לפני תחילת העבודה")
    divisor = min(12, months)

    if total == 0:
        spread = False
    elif threshold is not None:
        spread = total > _d(threshold)
    elif total <= NOT_SPREAD_MAX_TOTAL and total * NOT_SPREAD_PCT[1] <= NOT_SPREAD_PCT[0] * wage:
        spread = False
    elif total >= SPREAD_MIN_TOTAL and total * SPREAD_PCT[1] >= SPREAD_PCT[0] * wage:
        spread = True
    else:
        return _manual("הרף לפריסה לא ידוע, והמקרה הזה בין הערכים שנבדקו. יש להכריע ידנית או להעביר threshold")

    if spread:
        value = wage + total / divisor
    elif below_threshold_rule == "add_in_full":
        value = wage + total     # תשלום שלא עולה על הרף: לא נפרס, מתווסף במלואו
    else:
        value = wage             # הכלל הישן: התעלמות מהתשלום שמתחת לרף
    res = item(r2(value), COURSE,
               (f"נפרס על {divisor} חודשים" if spread else
                ("לא נפרס (לא עולה על הרף), נוסף במלואו" if below_threshold_rule == "add_in_full"
                 else "לא נפרס (לא עולה על הרף), לא נוסף (כלל ישן)")) +
               "; הרף עצמו לא ידוע, הוכרע לפי תרגילי הקורס בלבד")
    res["divisor"] = divisor if spread else None
    return res
