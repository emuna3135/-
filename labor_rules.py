"""
כללי דיני עבודה וביטחון סוציאלי שנגזרו מהתרגילים (שנת 2025).
חשוב: כלל בלי מקור רשמי בטבלת SOURCES מסומן MANUAL ("מצריך בדיקה ידנית"); אין סטטוס "לפי הקורס" בפלט.
הסטטוס משתנה ל-BY_LAW רק אחרי אימות מול מקור רשמי, בטבלת SOURCES. אין ניחושים: מה שלא נלמד מחזיר value=None, MANUAL.
כל החישובים ב-Decimal, בלי עיגול ביניים. עיגול רק בסוף (חצי כלפי מעלה).
"""
import datetime
from decimal import Decimal, ROUND_HALF_UP

from engine import BY_LAW, COURSE, MANUAL, VERIFIED, item, r0, r2  # noqa: F401

D = Decimal

# נושאים שאומתו מול מקור חיצוני (אוקטובר 2026). הרמה: "משני" = אתר זכויות (כל זכות) שמצטט את החוק,
# עדיין לא נוסח החוק עצמו (נבו/ספר החוקים). עד בדיקה מול הנוסח הרשמי - זה הדרג הגבוה ביותר שיש לנו.
SOURCES = {
    "advance_notice": ("רשמי", "הכנסת - חוק הודעה מוקדמת לפיטורים ולהתפטרות, התשס\"א-2001, נוסח מקורי (ס\"ח 1788, 17.5.2001) שהועלה ע\"י המשתמשת", "סעיפים 3-5: טבלאות חודשי/יומי-שעתי; לא ידוע אם תוקן; 'חודש ימים' (30) והמקרה של 12 חודשים לעובד חודשי - ידני"),
    "hours_law": ("רשמי-מסחרי", "נבו - חוק שעות עבודה ומנוחה, התשי\"א-1951, נוסח נכון ל-18.09.2023 (הודבק ע\"י המשתמשת)", "§2: יום 8 שעות (7 בלילה/ערב מנוחה/ערב חג); §3: שבוע 45 שעות; §16(א): שעתיים ראשונות 125%, אחריהן 150%; §17: מנוחה שבועית 150%. הספים 8.6/42 בקוד אינם בנוסח זה - לפי הקורס/משני"),
    "child_sick": ("רשמי-מסחרי", "נבו - חוק דמי מחלה (היעדרות בשל מחלת ילד), התשנ\"ג-1993, נוסח נכון ל-18.09.2023 (הודבק ע\"י המשתמשת)", "סעיף 1: ילד מתחת ל-16, עד 8 ימים בשנה (בן זוג עובד/עצמאי שלא נעדר), עד 16 להורה עצמאי/החזקה בלעדית, נזקפים על המחלה הצבורה. תאריך תחילת סעיף 1א1 (ספירה משותפת) לא ידוע"),
    "unemployment_amount": ("רשמי", "btl.gov.il/benefits/Unemployment/Pages/hisuv.aspx ו-sum.aspx (נקרא ישירות 16.11.2026)", "שכר יומי = הכנסה חייבת 6 חודשים / 150; סכום יומי בסיסי 415 (1.1.2026); מדרגות 80/50/45/30 (28+) ו-60/40/35/25 (מתחת ל-28); תקרה 550.76 ל-125 ימים ראשונים, 367.17 מיום 126; נבדק מול 14 שורות מייצגות מהטבלה ב-sum.aspx (9 ל-28+ ו-5 מתחת ל-28) ונקודות התקרה"),
    "unemployment": ("רשמי", "btl.gov.il/benefits/Unemployment/Pages/zakaut.aspx, pay.aspx, submit.aspx (נקרא 16.11.2026)", "תנאי זכאות לדמי אבטלה: תביעה לביטוח לאומי; אכשרה; חל\"ת ביוזמת העובד; התפטרות ללא סיבה מוצדקת"),
    "annual_leave_5day_minimum": ("רשמי", "הכנסת - מרכז המחקר והמידע, 'חופשות במערכת החינוך והתאמתן' (27.7.2021): בשבוע 5 ימים מינימום 12 ימי עבודה בכל אחת מחמש השנים הראשונות", "הערכים לשנים 6 ואילך (לפי צו 1990: 17/23) לא נקראו בנוסח רשמי -> ידני"),
    "unemployment_duration": ("רשמי", "btl.gov.il/benefits/Unemployment/Pages/zakaut.aspx, tkufat_zakaut.aspx, pay.aspx, submit.aspx", "אכשרה 12 מתוך 18 חודשים; תביעה תוך 12 חודשים מההתייצבות הראשונה; משך מרבי לפי גיל ותלויים (50/67/100/138/175; נשים 57-67: 300); התפטרות ללא סיבה מוצדקת: 90 יום"),
    "annual_leave": ("רשמי-מסחרי", "נבו - חוק חופשה שנתית, התשי\"א-1951, נוסח נכון ל-21.07.2026 (הודבק ע\"י המשתמשת)", "§3(א): 16 ל-5 שנים, 18 שישית, 21 שביעית, +1 עד 28; §3(ב) 200 ימים; §3(ג) 240 ימים; חלק יום לא נספר; §10 דמי חופשה = שכר רגיל; §13 פדיון; §15 תמורה 4% לעובד זמני"),
    "sick_pay_days_2_3_and_4plus": ("רשמי-מסחרי", "נבו - חוק דמי מחלה, התשל\"ו-1976, נוסח נכון ל-18.09.2023 (הודבק ע\"י המשתמשת)", "סעיף 2(א): יום 1 ללא תשלום, ימים 2-3 מחצית, מהיום הרביעי מלא"),
    "recreation": ("משני", "kolzchut.org.il - טבלת מספר ימי ההבראה בהתאם לוותק (הועלתה על ידי המשתמשת)", "צו ההרחבה בדבר השתתפות המעסיק בהוצאות הבראה ונופש: 5 / 6 / 7 / 8 / 9 / 10 ימים לפי ותק"),
    "insolvency": ("רשמי", "btl.gov.il/Publications/Skira_shnatit/2025/Documents/chap-3-12-pashar.pdf",
                   "ביטוח לאומי, סקירה שנתית 2025: גמלה מרבית 13 פעמים הסכום הבסיסי (131,807) לשכר ופיצויים, ופעמיים (20,278) לחוב לקרנות"),
    "old_age": ("רשמי", "btl.gov.il/BENEFITS/OLD_AGE/CONDITIONS_OF_ELIGIBILITY/ACHSHARA/Pages/achsharaIsha.aspx",
                "ביטוח לאומי, אכשרה לאישה: 60 חודשים ב-10 השנים / 144 חודשים / 60 חודשים וגם מבוטחת (ממש) יותר ממה שלא; פטורים לפי רשימה"),
    "wage_protection": ("רשמי-מסחרי", "נבו - חוק הגנת השכר, תשי\"ח-1958, נוסח נכון ל-07.11.2025 (הודבק ע\"י המשתמשת)", "סעיף 8(א): לא ניתן לעיקול סכום השווה לגמלה בטור ג' (הבטחת הכנסה); אם יותר מ-80% מ'שכר העבודה החדשי' (אחרי ניכויי חובה על פי חיקוק) - יקטן ל-80%. 8(א1): יומי 1/25. 8(ב): לא חל על מזונות. ניכוי 'תשלומים ישירים לבקשת העובד' אינו בחוק"),
    "sick_pay": ("רשמי-מסחרי", "נבו - חוק דמי מחלה, התשל\"ו-1976, נוסח נכון ל-18.09.2023 (הודבק ע\"י המשתמשת)", "סעיף 2(א): יום 1 ללא תשלום (לפי נוסח החוק), ימים 2-3 מחצית, מהיום הרביעי מלא; סעיף 5(א): שכר שהיה מקבל; סעיף 6: בסיס = יסוד, ותק, יוקר, משפחה, מחלקתית/מקצועית"),
    "youth_work": ("רשמי", "meyda.education.gov.il/files/noar/choknoar3.pdf", "חוק עבודת הנוער, תשי\"ג-1953: ילד <16, צעיר 16-<18; גיל 15 (14 בחופשה, בעבודה קלה); מנוחה 36 שעות; 8 שעות ליום ו-40 בשבוע (7 בערב מנוחה); לילה 20:00-08:00 לילד ו-22:00-06:00 לצעיר; בדיקה רפואית"),
    "severance_wage": ("רשמי", "btl.gov.il/Laws1/02_0040_100001.pdf: תקנות פיצויי פיטורים (חישוב הפיצויים והתפטרות שרואים אותה כפיטורים), תשכ\"ד-1964, תקנות 1 ו-9 (נקרא 16.11.2026)", "תקנה 1: שכר יסוד, תוספת ותק, תוספת יוקר, תוספת משפחה; תוספת מחלקתית/מקצועית נחשבת שכר יסוד. תקנה 9: שכר לפי תוצרת/פדיון - ממוצע 12 חודשים. רכיב אחר לא מופיע בתקנה"),
    "vacation_pay": ("רשמי", "btl.gov.il/Laws1/00_0082_000000.pdf: חוק חופשה שנתית, תשי\"א-1951, סעיפים 10 ו-13 (נקרא 16.11.2026)", "פדיון = דמי חופשה ליום העזיבה; עובד בשכר חודשי: שכרו הרגיל; עובד בשכר: שכר רבעון קודם / 90 לכל יום"),
    "severance_amount": ("רשמי-מסחרי", "נבו - חוק פיצויי פיטורים, התשכ\"ג-1963, נוסח נכון ל-30.01.2025 (הודבק ע\"י המשתמשת); תואם btl.gov.il/Laws1/00_0040_000000.pdf", "סעיף 12(א): שכר חודש לכל שנת עבודה לעובד במשכורת; שכר שבועיים לעובד בשכר; חלק שנה יחסי. §1(א): זכאות לאחר שנה"),
    "recreation_reduction": ("משני", "kolzchut.org.il/he/הפחתה_והקפאה_של_דמי_הבראה_בשנים_2024-2025",
                             "חוק הקפאה והפחתה של דמי הבראה בשנת 2025: ערך יום 418 (פרטי), הפחתת יום, חצי יום עד 6,150 לפי חלקיות משרה"),
}
# נושאים שבהם התרגיל והמקור החיצוני לא תואמים, ולכן לא מסמנים אותם "לפי חוק":
CONFLICTS = {
    "severance_wage": "הקורס: שכר גלובלי/שעות נוספות לא נכללים. לפי כל זכות (מצטט את תקנות פיצויי פיטורים): שעות נוספות גלובליות שמשולמות גם בלי שבוצעו שעות - נכללות; רק גמול על שעות שבוצעו בפועל - לא. כמו כן לא נכללים: הבראה, משכורת 13, ביגוד, שווי שימוש, פרמיית משמרת. לא הוכרע; מרכיב כזה מחזיר ידני.",
    "unemployment_amount": "סכום דמי אבטלה: המדרגות נקראו ישירות מהעמוד ואומתו מול טבלת הדוגמאות (עודכן 16.11.2026); נשארו פתוחים: חודשים חלקיים/שכר מופחת/דמי פגיעה בתקופת הבסיס; ימי ההמתנה: 5 ימים בכל 4 חודשי התייצבות רצופים (כלל קבוע, btl.gov.il pay.aspx), למעט הוראות שעה זמניות. הסכום לא מחושב כאן, ידני.",
    "annual_leave_week_shape": 'החוק (§3(א), נקרא ישירות) קובע ימים קלנדריים 16/18/21/+1 עד 28 וכולל מנוחה שבועית. טבלת ימי העבודה לשבוע 5 ימים נלקחה מנוסח צו ההרחבה מ-26.8.1990 (סעיף 8: 10/11/12/17/23) כפי שהועתק באתרי חילן ופרישה, ומהסכם קיבוצי כללי 29.10.2015 (כפי שדווח בלשכת המסחר ת"א וב-ynet): שנים 1-4 ל-11 מ-1.7.2016, ושנים 1-5 ל-12 מ-1.1.2017. הסתירה הקודמת (10 מול 12) נפתרה: 10 היא טבלת 1990, 12 אחרי 2017. הנוסחים הרשמיים (ילקוט הפרסומים/משרד העבודה) לא נקראו - לכן ימי חופשה משנה 6 ואילך נשארים ידניים.',
}


def _status(topic):
    return BY_LAW if topic in SOURCES else MANUAL


def _floor(x):
    return int(D(str(x)).to_integral_value(rounding="ROUND_FLOOR"))


# ---------------------------------------------------------------------------
# פיצויי פיטורים: השכר הקובע
# ---------------------------------------------------------------------------
SEVERANCE_INCLUDED = {"base", "fixed_supplement", "commissions_avg12"}   # לפי תקנות 1 ו-9
SEVERANCE_NOT_IN_REGULATION = {"fixed_premium"}   # אינה ברשימת תקנה 1 (נכללת רק בפסיקה/הסכם) -> ידני
SEVERANCE_EXCLUDED = {"car_maintenance", "convalescence_pay", "thirteenth_salary", "clothing_allowance", "car_use_value", "phone_upkeep", "phone_reimbursement",
                      "travel_reimbursement", "per_diem", "meals_allowance",
                      "overtime_pay", "one_time_bonus"}


def severance_wage(components):
    """components: רשימת (סוג, סכום). סוג לא מוכר -> ידני (לא מנחשים אם הוא נכלל)."""
    total, unknown = D(0), []
    for kind, amount in components:
        if kind in SEVERANCE_INCLUDED:
            total += D(str(amount))
        elif kind not in SEVERANCE_EXCLUDED:
            unknown.append(kind)
    if any(k in SEVERANCE_NOT_IN_REGULATION for k, _ in components):
        return item(None, MANUAL, "פרמיה קבועה אינה ברשימת תקנה 1 לתקנות פיצויי פיטורים; הכללתה תלויה בהסכם/פסיקה - לבדיקה ידנית")
    if unknown:
        return item(None, MANUAL, "רכיב שלא נלמד, לא ידוע אם נכלל בשכר הקובע: " + ", ".join(unknown))
    return item(total, _status("severance_wage"),
                "שכר קובע לפי תקנה 1: יסוד + ותק/יוקר/משפחה (תוספת מחלקתית/מקצועית כיסוד); שכר לפי תוצרת/פדיון - ממוצע 12 חודשים (תקנה 9)")


def severance_pay(determining_wage, full_months, pay_type="monthly"):
    """
    סעיף 12(א) (נוסח נבו נכון ל-30.01.2025): עובד במשכורת - שכר חודש לכל שנת עבודה, חלק משנה - יחסי.
    עובד בשכר (יומי/שעתי) - שכר שבועיים לכל שנת עבודה: חישוב "שכר שבועיים" לא הוגדר כאן -> ידני.
    סעיף 1(א): זכאות מלאה לאחר שנה רצופה (עונתי: שתי עונות); פחות משנה -> ידני (חריגים: §3, §6-§11).
    סעיף 13ב: שכר קובע לא יפחת משכר המינימום לפי היקף המשרה - לא ממומש כאן (ראו DATA_LEDGER).
    """
    if pay_type != "monthly":
        return item(None, MANUAL, "עובד בשכר: שכר שבועיים לכל שנת עבודה (§12(א)); שיטת חישוב שכר שבועיים לא הוגדרה")
    if isinstance(full_months, float) and full_months != int(full_months):
        return item(None, MANUAL, "חודשים חלקיים לא נלמדו")
    if int(full_months) < 12:
        return item(None, MANUAL, "פחות משנת עבודה: זכאות רק בחריגים (§1(א), §3, §6-§11) - ידני")
    return item(D(str(determining_wage)) * int(full_months) / 12, _status("severance_amount"),
                "עובד במשכורת: שכר חודש לכל שנת עבודה (סעיף 12(א)); השכר הקובע עצמו - ראו severance_wage")


# ---------------------------------------------------------------------------
# הודעה מוקדמת (עובד שמתפטר)
# ---------------------------------------------------------------------------
def advance_notice_days_resignation(full_months, pay_type):
    """
    עובד שמתפטר. pay_type: "monthly" (שכר חודשי) או "daily_hourly" (יומי/שעתי). לפי החוק ההסדר שונה:
    חודשי: עד 6 חודשים - יום לכל חודש; כל חודש מלא נוסף - 2.5 ימים; משנה ומעלה - חודש (מומר כאן ל-30 יום).
    יומי/שעתי: שנה 1 - יום לכל חודש; שנה 2 - 14 + יום לכל חודשיים; שנה 3 - 21 + יום לכל חודשיים; מעל 3 שנים - חודש (30).
    הודעה ביום האחרון של שנה 1 נחשבת לשנה 1 (12). גבול 36 חודשים: לפי שנה 3.
    """
    m = int(full_months)
    if m < 0:
        raise ValueError("חודשי עבודה שליליים")
    if pay_type == "monthly":
        if m <= 6:
            days = D(m)
        elif m < 12:
            days = D(6) + D("2.5") * (m - 6)
        else:
            days = D(30)
        note = "עובד חודשי; ימי לוח"
        if m >= 12:
            note += "; 'חודש' הומר ל-30 יום (המרה לא מאומתת)"
    elif pay_type == "daily_hourly":
        if m <= 12:
            days = D(m)
        elif m <= 24:
            days = D(14 + (m - 12) // 2)
        elif m <= 36:
            days = D(21 + (m - 24) // 2)
        else:
            days = D(30)
        note = "עובד יומי/שעתי; ימי לוח"
        if m > 36:
            note += "; 'חודש' הומר ל-30 יום (המרה לא מאומתת)"
    else:
        return item(None, MANUAL, "סוג שכר לא מוכר (monthly / daily_hourly)")
    return item(days, _status("advance_notice"), note)


# ---------------------------------------------------------------------------
# דמי מחלה
# ---------------------------------------------------------------------------
def sick_pay_percent(day_number):
    """יום 1: 0%, ימים 2-3: 50%, מיום 4: 100%."""
    if day_number < 1:
        raise ValueError("מספר יום חייב להיות 1 ומעלה")
    return D(0) if day_number == 1 else (D("0.5") if day_number <= 3 else D(1))


def sick_pay(daily_wage, days):
    """עובד חודשי סופרים ימי לוח כולל מנוחה (days כבר כולל). מחזיר סכום מצטבר."""
    total = sum((sick_pay_percent(d) for d in range(1, int(days) + 1)), D(0))
    return item(total * D(str(daily_wage)), _status("sick_pay"), f"{int(days)} ימי מחלה רצופים")


def child_illness_pay_percent(own_day_number, other_parent_days_before=0, declaration_submitted=False,
                              amendment_in_force=None):
    """
    תיקון לחוק דמי מחלה (היעדרות בשל מחלת ילד), התשנ"ג-1993 (תקציר חוק מהכנסת שהמשתמשת הדביקה): כשההורים נעדרים לסירוגין
    בשל מחלת אותו ילד, ימי ההיעדרות נמנים לצורך אחוזי התשלום (0/50/50/100) מהיום הראשון שבו אחד ההורים נעדר, בכפוף להצהרה.
    תאריך תחילת התיקון והנוסח המלא לא נקראו: עד שמאשרים שהוא בתוקף (amendment_in_force=True) - ידני.
    own_day_number: היום של ההורה הזה (1 = הראשון שלו). other_parent_days_before: ימים שההורה השני כבר נעדר באותה מחלה.
    """
    if amendment_in_force is None:
        return item(None, MANUAL, "תחילת תוקפו של התיקון לא אומתה: יש לקבוע ידנית אם הוא חל")
    day = int(own_day_number)
    if amendment_in_force and declaration_submitted:
        day += int(other_parent_days_before)
    return item(sick_pay_percent(day), _status("sick_pay"),
                "ספירה משותפת של ימי שני ההורים בכפוף להצהרה" if (amendment_in_force and declaration_submitted)
                else "ספירה נפרדת להורה (אין הצהרה או התיקון לא בתוקף)")


CHILD_SICK_QUOTA = {"single_parent": 16, "other_parent": 8}


def child_sick_days_remaining(parent_type, used, child_age):
    """מחלה לא קשה של ילד: מכסה שנתית מצטברת. ילד בן 16 ומעלה: אין זכאות לפי הסעיף הזה."""
    if parent_type not in CHILD_SICK_QUOTA:
        return item(None, MANUAL, "סוג הורה לא מוכר")
    if child_age >= 16:
        return item(0, _status("child_sick"), "ילד בן 16 ומעלה: אין זכאות לפי הסעיף")
    return item(max(CHILD_SICK_QUOTA[parent_type] - int(used), 0), _status("child_sick"), "מכסה שנתית פחות ניצול")


# ---------------------------------------------------------------------------
# חופשה שנתית. נוסח נבו נכון ל-21.07.2026 (הועלה ע"י המשתמשת): §3(א) הטבלה, §3(ב) 200 ימים (קשר משפטי כל שנת העבודה),
# §3(ג) 240 ימים (קשר משפטי בחלק משנת העבודה), חלק של יום לא נספר. "שנת עבודה" לפי §1 = שנה קלנדרית (מ-1 בינואר).
# ---------------------------------------------------------------------------
def annual_leave_statutory_days(year_of_service):
    """ימי החופשה לפי סעיף 3 לחוק חופשה שנתית: 16 לשנים 1-5, 18 לשישית, 21 לשביעית, ועוד יום בכל שנה עד 28."""
    y = int(year_of_service)
    if y < 1:
        raise ValueError("שנת ותק מ-1")
    days = 16 if y <= 5 else 18 if y == 6 else min(21 + (y - 7), 28)
    return item(days, _status("annual_leave"),
                "ימי חוק; הצו/הסכם עשויים להיטיב. המרה לימי נטו לפי אורך שבוע העבודה לא מאומתת")


def annual_leave_net_days_five_day_week(year_of_service, as_of_year=2026):
    """ימי חופשה נטו (ימי עבודה) לשבוע של 5 ימים. שנים 1-5 מ-2017: 12 (הכנסת, מרכז המחקר והמידע - מינימום).
    שנים 6 ואילך או לפני 2017: אין לנו מקור רשמי (טבלת צו 1990: 17/23 הועתקה רק באתרים מקצועיים) -> ידני."""
    y = int(year_of_service)
    if y < 1:
        raise ValueError("שנת ותק מ-1")
    if as_of_year >= 2017 and y <= 5:
        return item(12, _status("annual_leave_5day_minimum"), "מינימום 12 ימי עבודה בשבוע 5 ימים לשנים 1-5 (הכנסת, מרכז המחקר והמידע)")
    return item(None, MANUAL, "ימי חופשה נטו לשנה זו לא נקראו ממקור רשמי; לפי צו ההרחבה 1990 (הועתק באתרים מקצועיים): 17 לשנים 6-8, 23 מהתשיעית - להזין ידנית אחרי בדיקה")


def annual_leave_proportional(base_days, days_worked, continuous_year=True):
    """
    מתחת לסף: base * days / סף, בלי שברי יום (נחתך כלפי מטה). מהסף ומעלה: מלא.
    סף 200: הקשר המשפטי קיים כל שנת העבודה (§3(ב)); סף 240: הקשר קיים רק בחלק משנת העבודה (§3(ג), למשל התחלה/סיום
    באמצע שנה קלנדרית). הפרמטר continuous_year=False משמעו "חלק משנה" ולא "עבודה לסירוגין". אומת מול נוסח נבו 21.07.2026.
    """
    if base_days is None:
        return item(None, MANUAL, "טבלת ימי החופשה הבסיסית לא הוכרעה: להזין ידנית")
    threshold = 200 if continuous_year else 240
    note = "" if continuous_year else "סף 240: קשר משפטי בחלק משנת העבודה (§3(ג))"
    if days_worked >= threshold:
        return item(D(str(base_days)), _status("annual_leave"), note)
    return item(_floor(D(str(base_days)) * D(str(days_worked)) / threshold), _status("annual_leave"),
                (note + "; " if note else "") + "נחתך לימים שלמים")


# ---------------------------------------------------------------------------
# דמי הבראה 2025
# ---------------------------------------------------------------------------
RECREATION_DAY_VALUE_2025 = D(418)


def recreation_days(year_of_service):
    y = int(year_of_service)
    if y < 1:
        raise ValueError("שנת ותק מ-1")
    if y == 1:
        return D(5)
    if y <= 3:
        return D(6)
    if y <= 10:
        return D(7)
    if y <= 15:
        return D(8)
    if y <= 19:
        return D(9)
    return D(10)


RECREATION_PARTIAL_THRESHOLD_2025 = D(6150)


def recreation_reduction_type(avg_monthly_wage, position_fraction=1):
    """הפחתה חלקית (חצי יום) אם השכר החודשי הממוצע אינו עולה על 6,150 כפול חלקיות המשרה."""
    limit = RECREATION_PARTIAL_THRESHOLD_2025 * D(str(position_fraction))
    return "partial" if D(str(avg_monthly_wage)) <= limit else "full"


def recreation_pay_2025(year_of_service, fraction=1, reduction="full"):
    """
    זכאות בימים * 418, פחות הפחתה של יום (418), או חצי יום (209) להפחתה חלקית.
    משרה חלקית / תקופה חלקית: גם הזכאות וגם ההפחתה כפול החלק.
    אומת מול מקור משני (כל זכות): ערך 418, הפחתת יום, חצי יום עד 6,150 לפי חלקיות, וטבלת הימים לפי ותק.
    """
    if reduction not in ("full", "partial", "none"):
        return item(None, MANUAL, "סוג הפחתה לא מוכר")
    red = {"full": RECREATION_DAY_VALUE_2025, "partial": RECREATION_DAY_VALUE_2025 / 2, "none": D(0)}[reduction]
    gross = recreation_days(year_of_service) * RECREATION_DAY_VALUE_2025
    return item((gross - red) * D(str(fraction)), _status("recreation"),
                "ערך יום, הפחתה, סף 6,150 וטבלת הימים אומתו מול מקור משני (כל זכות); ללא קיצוץ שברי ימים")


# ---------------------------------------------------------------------------
# שכר שעתי ושעות נוספות
# ---------------------------------------------------------------------------
# 8.6 ו-42 נגזרו מפתרונות הקורס ומאתר כל זכות. בנוסח חוק שעות עבודה ומנוחה של נבו (נכון ל-18.09.2023, שהועלה
# ע"י המשתמשת) כתוב: יום עבודה 8 שעות (§2(א)), 7 שעות בעבודת לילה/ערב מנוחה שבועית/ערב חג (§2(ב)), שבוע 45 שעות (§3).
# 42 ו-182: צו הרחבה בדבר קיצור שבוע העבודה במשק (חתום 15.03.2018) - נוסח רשמי נקרא ואומת (סעיפים 2.1, 2.8).
# הנחיית משרד העבודה (gov.il, נקרא 16.11.2026): שעות נוספות מחושבות באופן יומי ושבועי ולא חודשי; אין קיזוז בין ימים (פרט לשעות גמישות).
# סף יומי 8.6 (עדכון 16.11.2026): משרד העבודה, הלשכה המשפטית (gov.il/BlobFolder/legalinfo/rest-flexibility, 2022), נקרא:
# "בישראל יום העבודה מוגבל לפי החוק ל-8.6 שעות ביום, ולפי צו ההרחבה לקיצור שבוע העבודה במשק יום קבוע אחד בשבוע מקוצר ל-7.6 שעות"
# (4 x 8.6 + 7.6 = 42). בנוסח החוק עצמו (§2) כתוב 8 שעות; ובפסיקה שמצוטטת שם - שעות נוספות מעבר ל-8 ביום. הסתירה בין
# הנוסח (8) לבין 8.6 הממוצע לא הוכרעה במסמך רשמי אחד; היום המקוצר (7.6) אינו ממומש כאן. לכן הסטטוס נשאר "לפי הקורס".
# הסף השבועי 42 מאושר בצו.
DAILY_OT_THRESHOLD = D("8.6")
WEEKLY_THRESHOLD = D(42)


def _hours(t):
    h, m = t.split(":")
    return D(int(h)) + D(int(m)) / 60


def hourly_pay(hourly_rate, shifts, break_hours, daily_threshold=DAILY_OT_THRESHOLD,
               weekly_threshold=WEEKLY_THRESHOLD):
    """
    shifts: רשימת (התחלה, סיום) כמחרוזות HH:MM. הפסקה נקבעת על ידי הקורא (break_hours), לא ניחוש.
    יומי: מעל סף יומי, שעתיים ראשונות 125% ואחר כך 150%. שבועי: על (נטו - שעות נוספות יומיות) מעל 42 ב-125%.
    שבועי מעל שעתיים: התעריף לא נלמד -> ידני.
    """
    rate, brk = D(str(hourly_rate)), D(str(break_hours))
    net_total = d125 = d150 = D(0)
    for start, end in shifts:
        net = _hours(end) - _hours(start) - brk
        if net < 0:
            raise ValueError("משמרת עם נטו שלילי")
        net_total += net
        ot = max(net - daily_threshold, D(0))
        d125 += min(ot, D(2))
        d150 += max(ot - 2, D(0))
    daily_ot = d125 + d150
    weekly_ot = max(net_total - daily_ot - weekly_threshold, D(0))
    out = {"net_hours": net_total, "hours_125": d125 + min(weekly_ot, D(2)), "hours_150": d150,
           "weekly_ot_hours": weekly_ot}
    if weekly_ot > 2:
        out.update(pay=None, pay_shekel=None, status=MANUAL,
                   note="שעות נוספות שבועיות מעל שעתיים: התעריף לא נלמד")
        return out
    pay = net_total * rate + D("0.25") * out["hours_125"] * rate + D("0.5") * d150 * rate
    defaults = (daily_threshold, weekly_threshold) == (DAILY_OT_THRESHOLD, WEEKLY_THRESHOLD)
    out.update(pay=pay, pay_shekel=r0(pay), status=MANUAL if defaults else _status("hours_law"),
               note=f"הפסקה {brk} שעות ליום; ספים {daily_threshold}/{weekly_threshold}" + ("; הסף היומי לא הוכרע בנוסח רשמי: צו קיצור שבוע העבודה 2018 (gov.il) קובע 42 שעות שבועיות ויום מקוצר ואינו קובע שעות יומיות; בחינת בודק שכר מוסמך של משרד העבודה (gov.il) מניחה 8.6 שעות בימים א-ד ו-7.6 ביום המקוצר; חוק שעות עבודה ומנוחה §2: 8. יש להזין סף ויום מקוצר לפי ההסדר" if defaults else ""))
    return out


# ---------------------------------------------------------------------------
# הגנת השכר: עיקול שכר
# ---------------------------------------------------------------------------
def wage_attachment(wage, benefit, attachment_amount, direct_payments=0):
    """
    תשלומים ישירים לבקשת העובד מנוכים קודם. מוגן = min(קצבת הבטחת הכנסה, 80% מהיתרה).
    ניתן לעיקול = יתרה - מוגן. עיקול בפועל = min(סכום העיקול, ניתן לעיקול).
    הקצבה היא קלט: לא מחושבת כאן. לפי סעיף 8(ב) ההגנה לא חלה על עיקול למזונות (לא ממומש כאן).
    סדר ניכוי תשלומים ישירים - מהתרגילים, לא נבדק בנוסח. לפי §8(א) בנוסח נבו 07.11.2025 מנוכים לפני
    החישוב רק תשלומי חובה על פי חיקוק; ניכוי "לבקשת העובד" אינו מופיע בחוק. לא ממומשים: §8(א1) יומי, §8(ב) מזונות.
    """
    remaining = D(str(wage)) - D(str(direct_payments))
    protected = min(D(str(benefit)), remaining * D("0.8"))
    attachable = max(remaining - protected, D(0))
    actual = min(D(str(attachment_amount)), attachable)
    return {"remaining_wage": remaining, "protected": protected, "max_attachable": attachable,
            "actual_attachment": actual, "status": _status("wage_protection")}


# ---------------------------------------------------------------------------
# דמי חדלות פירעון 2025
# ---------------------------------------------------------------------------
INSOLVENCY_CAP_WAGE_2025 = D(131807)
INSOLVENCY_CAP_FUND_2025 = D(20278)


def insolvency_benefit_2025(wage_and_severance_debt, pension_fund_debt):
    v = min(D(str(wage_and_severance_debt)), INSOLVENCY_CAP_WAGE_2025) \
        + min(D(str(pension_fund_debt)), INSOLVENCY_CAP_FUND_2025)
    return item(v, _status("insolvency"), "תקרות 2025: 131,807 לשכר ופיצויים, 20,278 לחוב לקרן")


# ---------------------------------------------------------------------------
# קצבת זקנה: תקופת אכשרה
# ---------------------------------------------------------------------------
OLD_AGE_EXEMPTION_GROUPS = ("single", "divorced", "agunah", "widow_not_receiving_survivors_pension",
                            "husband_not_insured_old_age", "general_disability_pension_month_before")


def old_age_qualifying(months_in_last_10y, total_insured_months, insured_months_since_residence=None,
                       uninsured_months_since_residence=None, is_woman=False, exemption_flags=()):
    """
    חלופות (לא חייבות להיות רצופות): (א) 60 חודשי ביטוח ב-10 השנים שלפני גיל הזכאות,
    (ב) 144 חודשי ביטוח בסך הכל, (ג) אישה: לפחות 60 חודשי ביטוח וחודשי ביטוח גדולים (ממש) מחודשים שלא בוטחה.
    פטור אפשרי (קבוצות לפי ביטוח לאומי: OLD_AGE_EXEMPTION_GROUPS; התנאים המדויקים לא נלמדו) -> ידני אם אף חלופה לא מתקיימת.
    """
    alts = {"a_60_in_last_10": months_in_last_10y >= 60, "b_144_total": total_insured_months >= 144}
    if is_woman and insured_months_since_residence is not None and uninsured_months_since_residence is not None:
        alts["c_woman_insured_gt_uninsured"] = (insured_months_since_residence >= 60 and
                                                insured_months_since_residence > uninsured_months_since_residence)
    if any(alts.values()):
        return {"qualifies": True, "alternatives": alts, "status": _status("old_age"), "note": ""}
    if exemption_flags:
        return {"qualifies": None, "alternatives": alts, "status": MANUAL,
                "note": "ייתכן פטור (" + ", ".join(exemption_flags) + "); התנאים לא נלמדו"}
    return {"qualifies": False, "alternatives": alts, "status": _status("old_age"), "note": ""}


# ---------------------------------------------------------------------------
# דמי אבטלה: זכאות עקרונית בלבד (סכום/תקופה/המתנה לא נלמדו)
# ---------------------------------------------------------------------------
def unemployment_eligibility(claim_filed_with_ni, employee_initiated_unpaid_leave=False,
                             employer_did_not_pay_ni=False, work_proven=False, abroad_days=0):
    if not claim_filed_with_ni:
        return {"eligible": False, "status": _status("unemployment"), "note": "לא הוגשה תביעה לביטוח לאומי"}
    if employee_initiated_unpaid_leave:
        return {"eligible": False, "status": _status("unemployment"), "note": "חל\"ת ביוזמת העובד"}
    if employer_did_not_pay_ni and not work_proven:
        return {"eligible": None, "status": MANUAL, "note": "המעסיק לא שילם דמי ביטוח: נדרשת הוכחת עבודה"}
    note = "סכום, תקופה וימי המתנה לא נלמדו"
    if abroad_days:
        note += f"; {abroad_days} ימי שהייה בחו\"ל אינם משולמים"
    return {"eligible": True, "status": _status("unemployment"), "note": note}


# משך דמי האבטלה (btl.gov.il/benefits/Unemployment/Pages/tkufat_zakaut.aspx, נקרא 16.11.2026)
def unemployment_max_days(age, dependents, woman_57_67_born_1960_or_later=False):
    """ימי אבטלה מרביים לפי גיל ותלויים. עד 2 תלויים / 3+ תלויים. אישה בת 57-67 שנולדה ב-1.1.1960 ואילך: 300."""
    if not isinstance(age, (int, float)) or isinstance(age, bool) or age < 0 or not isinstance(dependents, int) or isinstance(dependents, bool) or dependents < 0:
        return item(None, MANUAL, "גיל/תלויים לא תקינים")
    if woman_57_67_born_1960_or_later and 57 <= age < 67:
        return item(D(300), _status("unemployment_duration"), "נשים 57-67 שנולדו מ-1.1.1960: עד 300 ימים")
    many = dependents >= 3
    if age < 25:
        days = 138 if many else 50
    elif age < 28:
        days = 138 if many else 67
    elif age < 35:
        days = 138 if many else 100
    elif age < 45:
        days = 175 if many else 138
    else:
        days = 175
    return item(D(days), _status("unemployment_duration"), "תקרת ימים לפי גיל ותלויים; סכום וימי המתנה לא מחושבים כאן")


UNEMP_BASE_DAILY_2026 = D("415")
UNEMP_MAX_FIRST_125_2026 = D("550.76")
UNEMP_MAX_AFTER_125_2026 = D("367.17")


def unemployment_daily_benefit(six_month_insured_income, age, payment_day=1):
    """דמי אבטלה ליום (btl.gov.il hisuv.aspx/sum.aspx, 2026). שכר יומי = הכנסה חייבת ב-6 חודשים / 150.
    28+: 80/50/45/30%; מתחת ל-28: 60/40/35/25%; מדרגות: עד חצי הבסיס, עד 3/4, עד הבסיס, עד 5x הבסיס.
    תקרה 550.76 לימי תשלום 1-125 ו-367.17 מיום 126. עיגול לאגורה. לא כולל חודשים חלקיים/שכר מופחת."""
    if (not isinstance(age, (int, float)) or isinstance(age, bool) or age < 0
            or not isinstance(payment_day, int) or isinstance(payment_day, bool) or payment_day < 1):
        return item(None, MANUAL, "קלט לא תקין")
    try:
        income = D(str(six_month_insured_income))
    except Exception:
        return item(None, MANUAL, "הכנסה לא תקינה")
    if income < 0:
        return item(None, MANUAL, "הכנסה שלילית")
    w = income / D(150)
    b = UNEMP_BASE_DAILY_2026
    rates = (D("0.8"), D("0.5"), D("0.45"), D("0.3")) if age >= 28 else (D("0.6"), D("0.4"), D("0.35"), D("0.25"))
    edges = (D(0), b / 2, b * D("0.75"), b, b * 5)
    total = D(0)
    for i, rate in enumerate(rates):
        lo, hi = edges[i], edges[i + 1]
        if w > lo:
            total += (min(w, hi) - lo) * rate
    cap = UNEMP_MAX_FIRST_125_2026 if payment_day <= 125 else UNEMP_MAX_AFTER_125_2026
    total = min(total, cap)
    return item(total.quantize(D("0.01"), rounding=ROUND_HALF_UP), _status("unemployment_amount"),
                "דמי אבטלה ליום 2026; ללא חודשים חלקיים/שכר מופחת/דמי פגיעה; ימי המתנה לא מחושבים")


# ---------------------------------------------------------------------------
# העסקת נוער: בדיקות עקרוניות
# ---------------------------------------------------------------------------
def youth_work_check(age, weekly_rest_hours=None, overtime=False, night_work=False,
                     works_on_weekly_rest_day=False, medical_approval=False, in_school_vacation=False,
                     daily_hours=None, weekly_hours=None):
    """
    לפי חוק עבודת הנוער (נוסח משרד החינוך). מחזיר (הפרות, דורש בדיקה ידנית). רישיונות וחריגים לא נלמדו.
    ילד <16, צעיר 16-<18. מתחת ל-15 לא מועסק (סעיף 2(א)); בן 14 מותר בחופשה רשמית בעבודה קלה (2א);
    בן 15 עם חובת לימוד - רק בתנאים (חריגים לא נלמדו). יום עבודה עד 8 שעות ושבוע עד 40 (סעיף 20).
    """
    if age >= 18:
        return [], []
    violations, manual = [], []
    if age < 14:
        violations.append("ילד מתחת ל-14 אינו מועסק (סעיף 2(א); חריגים ברישיון שר העבודה לא נלמדו)")
    elif age < 15:
        if in_school_vacation:
            manual.append("בן 14 בחופשת לימודים רשמית: מותר רק בעבודה קלה שאינה מזיקה (סעיף 2א); התנאים לא נלמדו")
        else:
            violations.append("ילד מתחת ל-15 אינו מועסק מחוץ לחופשת לימודים (חריג בהיתר שר בלבד)")
    elif age < 16:
        manual.append("ילד בן 15 עם חובת לימוד: מותר רק בתנאים שלא נלמדו")
    if works_on_weekly_rest_day:
        violations.append("אסור לעבוד ביום המנוחה השבועי (סעיף 21)")
    if weekly_rest_hours is not None and weekly_rest_hours < 36:
        violations.append("מנוחה שבועית חייבת להיות לפחות 36 שעות רצופות (סעיף 21)")
    if overtime or (daily_hours is not None and daily_hours > 8) or (weekly_hours is not None and weekly_hours > 40):
        violations.append("חריגה מ-8 שעות ביום או 40 בשבוע, ושעות נוספות אסורות (סעיף 20)")
    if night_work:
        manual.append("עבודת לילה אסורה (סעיף 24): 20:00-08:00 לילד, 22:00-06:00 לצעיר; היתרים וחריגים לא נלמדו")
    if not medical_approval:
        violations.append("נדרש אישור רפואי לפני תחילת העבודה (סעיף 11(א))")
    return violations, manual
