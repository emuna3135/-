"""
מנוע חישוב שכר אחיד לפי שנה. כל רכיב חוזר עם סטטוס אימות:

  VERIFIED  - שוחזר מול תלוש אמיתי באגורה (נבדק ב-test_payslips.py / test_engine.py)
  BY_LAW    - חושב לפי שיעורי החוק אך לא נבדק מול תלוש באגורה (יש סטייה ידועה/אפשרית)
  MANUAL    - לא מחושב. המשתמש חייב להזין ידנית. המערכת לא מנחשת.

שנים נתמכות: 2025 ו-2026 בלבד. כל שנה אחרת -> MANUAL.
"""
import basis
from decimal import Decimal, ROUND_HALF_UP

D = Decimal

# שני קריטריונים בלבד למקור הכלל: "עפ"י החוק" או "עפ"י רואת חשבון". אימות מול תלוש אינו קריטריון נפרד (הוחלט 18.11.2026),
# לכן VERIFIED הוא כינוי ל-BY_LAW. MANUAL = אין מקור, המערכת לא מנחשת.
BY_LAW = "עפ\"י החוק"
VERIFIED = BY_LAW
MANUAL = "נדרש טיפול ידני"
ACCOUNTANT = "עפ\"י רואת חשבון"


def r0(x) -> int:
    return int(D(str(x)).quantize(D("1"), rounding=ROUND_HALF_UP))


def r2(x) -> Decimal:
    return D(str(x)).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def item(value, status, note=""):
    return {"value": value, "status": status, "note": note}


# ---------------------------------------------------------------------------
# ביטוח לאומי ובריאות (עובד) - נגזר מ-12 תלושי 2025-2026
# ---------------------------------------------------------------------------
# שנה: (סף מופחת חודשי, ב"ל מופחת, ב"ל מלא, בריאות מופחת, בריאות מלא)
NI_RATES = {
    2025: (D("7522"), D("0.0104"), D("0.07"), D("0.0323"), D("0.0517")),
    2026: (D("7703"), D("0.0104"), D("0.07"), D("0.0323"), D("0.0517")),
}
NI_VERIFIED_MAX = D("14647.00")   # השכר הגבוה ביותר שנבדק מול תלוש (עד 11,970.73 באגורה; מעל זה מול תלושים שמעגלים לשקל)
NI_BY_LAW_MAX = D("20000")        # מעל זה תלוי בתקרת ההכנסה המבוטחת (ראו NI_MAX_INSURED)
# תקרת הכנסה מבוטחת חודשית. 2025: 50,695 מתרגיל קורס. עקבית עם נתוני ביטוח לאומי הרשמיים ל-2026
# (תקרת תגמול מילואים 51,910 = פי 5 מסכום הבסיס; 50,695 = פי 5 מ-10,139 ב-2025), אך לא נבדקה מול תלוש.
# 2026: 51,910 - אומת מול אתר ביטוח לאומי (הכנסה חייבת בדמי ביטוח, "החל ב-01.01.2026") ומול חוזר הביטוח הלאומי מ-30.12.2025
# (סף מופחת 7,703). 2025: 50,695 מהקורס, לא אומת (ב-2026 התקרה היא פי 5 מסכום בסיס שונה, 10,382, מזה של גמלאות, 10,514; לכן אי אפשר להסיק ל-2025).
# שיעורי 2026: אומתו מול btl.gov.il/Insurance/Rates (לעובדים שכירים, נקרא 16.11.2026): עובד - לאומי 1.04% מופחת / 7% מלא, בריאות 3.23% / 5.17% (מ-1.2.2025; בינואר 2025 5.16%); סף מופחת 7,703 והכנסה מרבית 51,910 מ-1.1.2026.
NI_MAX_INSURED = {2025: D("50695"), 2026: D("51910")}
NI_CAP_OFFICIAL = {2025, 2026}   # 2025: חוזר ב"ל 1515 (1.1.2025): הכנסה מרבית 50,695, תקרה מופחת 7,522


# בריאות מלא בינואר 2025: 5.16% (ולא 5.17%). אומת: מחשבון ב"ל רשמי ינואר 2025, 11,416.33 -> 794.74
# (5.16% נותן 794.7399; 5.17% נותן 795.1294) + תלוש משרד החינוך ינואר 2025 (בריאות 443.91). ב301.
HEALTH_FULL_OVERRIDE = {(2025, 1): D("0.0516")}


def ni_health(year, gross, month=None):
    """מחזיר (שורת ב"ל, שורת בריאות). month אופציונלי; ללא חודש - שיעור השנה."""
    g = D(str(gross))
    if year not in NI_RATES:
        m = item(None, MANUAL, f"שנה {year} לא נתמכת")
        return m, dict(m)
    cap = NI_MAX_INSURED.get(year)
    if g > NI_BY_LAW_MAX and cap is None:
        m = item(None, MANUAL, "שכר גבוה: תקרת הכנסה מבוטחת לא ידועה לשנה זו")
        return m, dict(m)
    high_zone = g > NI_BY_LAW_MAX
    note = ""
    if cap is not None and g > cap:
        g = cap
        note = f"הכנסה מעל התקרה, חויב עד {cap}. "
    t, bl_lo, bl_hi, h_lo, h_hi = NI_RATES[year]
    h_hi = HEALTH_FULL_OVERRIDE.get((year, month), h_hi)
    lo, hi = min(g, t), max(g - t, D(0))
    if high_zone and year in NI_CAP_OFFICIAL:
        status = BY_LAW
        note += f"שכר מעל 20,000: תקרה {cap} לפי ביטוח לאומי; שיעורים לפי הטבלה, לא נבדק מול תלוש"
    elif high_zone:
        status = MANUAL
        note += "שכר מעל 20,000: אין תקרה רשמית לשנה זו"
    elif g <= NI_VERIFIED_MAX:
        status = VERIFIED
    else:
        status = BY_LAW
        note += "שכר מעל 14,647: שיעורי החוק, לא נבדק מול תלוש"
    # ללא עיגול (לפי רו"ח 11.11.2026): ערך מלא, תצוגה בלבד לאגורה. ב"ל ובריאות שורות נפרדות.
    note += " | ללא עיגול (ערך מלא; תצוגה בלבד לאגורה)"
    return (item(lo * bl_lo + hi * bl_hi, status, note),
            item(lo * h_lo + hi * h_hi, status, note))


# ביטוח לאומי של המעסיק (שכיר תושב ישראל בגיל 18 עד גיל פרישה): שיעורים לפי btl.gov.il/Insurance/Rates (לעובדים שכירים), נקרא 18.11.2026:
# מעסיק 4.51% עד הסף המופחת ו-7.6% מעליו (עד ההכנסה המרבית); אין דמי ביטוח בריאות למעסיק. סף מופחת 7,703 והכנסה מרבית 51,910 מ-1.1.2026.
# אסמכתא נוספת: חוזר ביטוח לאומי 1522 (1.4.2026) "שינוי בתשלום דמי ביטוח לאומי ודמי ביטוח בריאות לשנת 2026".
# הערה: בחוזר מוגדר שכר ממוצע 13,769 ו-60% ממנו הם 8,261.40, ואילו הסף המופחת שפורסם הוא 7,703; המערכת משתמשת בסף שפורסם ולא בחישוב עצמי.
# 2025: אותם שיעורי מעסיק לפי טבלת האתר (4.51% "החל ב-01.01.2025"), עם הסף וההכנסה המרבית של 2025.
# הערה: הסעיף בחוק לא תועד; לוח השיעורים הוא הוראת שעה עד סוף 2026 לפי החוזר.
NI_EMPLOYER_RATES = {
    2025: (D("7522"), D("0.0451"), D("0.076")),
    2026: (D("7703"), D("0.0451"), D("0.076")),
}


def ni_employer(year, gross):
    """ביטוח לאומי של המעסיק לשכיר רגיל. מחזיר item. שנה לא נתמכת או שכר מעל סף בלי תקרה -> MANUAL."""
    g = D(str(gross))
    if year not in NI_EMPLOYER_RATES or year not in NI_MAX_INSURED:
        return item(None, MANUAL, f"שנה {year} לא נתמכת")
    cap = NI_MAX_INSURED[year]
    note = ""
    if g > cap:
        g = cap
        note = f"הכנסה מעל התקרה, חויב עד {cap}. "
    t, lo_r, hi_r = NI_EMPLOYER_RATES[year]
    lo, hi = min(g, t), max(g - t, D(0))
    note += "שכיר תושב ישראל בן 18 עד גיל פרישה; ללא עיגול (ערך מלא)"
    return item(lo * lo_r + hi * hi_r, BY_LAW, note)


# ---------------------------------------------------------------------------
# מס הכנסה
# ---------------------------------------------------------------------------
# מדרגות חודשיות. 2025: כל-זכות. 2026: לוח עזר של רשות המסים "לחישוב מס הכנסה ממשכורת לינואר 2026 ואילך"
# (מעודכן לאפריל 2026): שנתי 84,120 / 120,720 / 228,000 / 301,200 / 560,280, חלקי 12.
# ה-20% וה-31% הורחבו בחוק ההתייעלות הכלכלית (תיקוני חקיקה להשגת יעדי התקציב לשנת התקציב 2026), התשפ״ו-2026, ספר החוקים 3511 (31.3.2026) עמ' 414,
# פרק ג' (ריווח מדרגות), סעיף 5 (תיקון סעיף 121): 20% עד 228,000; 31% מ-228,001 עד 301,200; 35% מ-301,201 עד 560,280; תחילה 1.1.2026 (סעיף 6). נקרא מהקובץ הרשמי.
# מס יסף 121ב(א): 3% על הכנסה חייבת מעל 721,560 (= 60,130 לחודש) - ספר החוקים 3342 (26.12.2024, חוק ההתייעלות הכלכלית (הקפאת עדכוני מס ומס יסף) התשפ״ה-2024):
# הוסף 121ב(א1): 2% נוסף על הכנסה חייבת ממקורות הוניים מעל הסף (תחילה 1.1.2025) - לא רלוונטי למשכורת. ספר החוקים 3511 לא שינה את 121ב.
# מס נוסף 121ב: המדרגה העליונה 50% (47% + 3%) חלה רק מעל הסף השנתי (721,560 ₪ = 60,130 לחודש); לפי רואת חשבון (18.11.2026) מס נוסף רלוונטי רק בהכנסות גבוהות מאוד, ובניכוי בשיעור מרבי 47% (תקנה 5(א)) לא מוסיפים אותו מעבר לכך.
BRACKETS = {
    2025: [(D("7010"), D("0.10")), (D("10060"), D("0.14")), (D("16150"), D("0.20")),
           (D("22440"), D("0.31")), (D("46690"), D("0.35")), (D("60130"), D("0.47")), (None, D("0.50"))],
    2026: [(D("7010"), D("0.10")), (D("10060"), D("0.14")), (D("19000"), D("0.20")),
           (D("25100"), D("0.31")), (D("46690"), D("0.35")), (D("60130"), D("0.47")), (None, D("0.50"))],
}
CREDIT_POINT_2025 = D("242")     # נקודת זיכוי 242 לחודש: 2025 ו-2026 (לוח עזר רשות המסים)
PENSION_CREDIT_RATE = D("0.35")
# תקרת הפקדות מזכות (סעיף 45א): 8,148 ש"ח לשנה = 679 לחודש. זהו 7% x תקרת הכנסה 9,700 x 12
# (לוח עזר רשות המסים; כל-זכות). הוכח גם מול 5 תלושים.
PENSION_CREDIT_CAP_MONTHLY = D("679")
LIFE_CREDIT_RATE = D("0.25")
NO_COORDINATION_RATE = D("0.47")

# ---------------------------------------------------------------------------
# לוח ניכוי יומי לעובד יומי (הכנסה מיגיעה אישית), 2026. מקור ראשוני: לוח עזר רשות המסים 2026, פרק ב' עמ' 10
# (אומת מול תמונת העמוד 16.11.2026): 280.40 / 402.40 / 760.00 / 1,004.00 / 1,867.60 ליום; = המדרגה החודשית / 25.
# נדרש לפי טופס 101: שכר עבודה (פחות מ-18 יום בחודש, לפחות 8 שעות בשבוע) מנוכה לפי לוח יומי כשזו הכנסה יחידה.
# לא מחובר ל-card.tax_mode (הזיכוי בנקודות לעובד יומי והעיגול היומי לא נבדקו מול לוח).
DAILY_BRACKETS_2026 = [(D("280.40"), D("0.10")), (D("402.40"), D("0.14")), (D("760.00"), D("0.20")),
                       (D("1004.00"), D("0.31")), (D("1867.60"), D("0.35")), (None, D("0.47"))]


def daily_tax_before_credits(daily_income, year=2026):
    if year != 2026:
        return item(None, MANUAL, "לוח יומי מאומת רק ל-2026")
    g = D(str(daily_income))
    if g < 0:
        return item(None, MANUAL, "הכנסה יומית שלילית")
    tax, prev = D(0), D(0)
    for upper, rate in DAILY_BRACKETS_2026:
        top = g if upper is None else min(g, upper)
        if top > prev:
            tax += (top - prev) * rate
        if upper is None or g <= upper:
            break
        prev = upper
    return item(r2(tax), BY_LAW, "לוח יומי 2026 (לוח עזר רשות המסים, עמ' 10); לפני נקודות זיכוי; עיגול היומי לא נבדק")


# ---------------------------------------------------------------------------
# תקנות מס הכנסה (ניכוי ממשכורת ומשכר עבודה), התשנ"ג-1993. מקור רשמי: btl.gov.il/Laws1/02_0103_100076.pdf (תקנות 1,3,4,5,6 ותוספות א/ב נקראו 16.11.2026, תואם למימוש; בעבר נוסח נבו/פרישה). אימות רשמי חלקי: טופס 101 באתר רשות המסים (gov.il/BlobFolder/service/itc101/...) מגדיר משכורת חודש (לפחות 18 יום בחודש), חלקית (עד 5 שעות ליום, או יותר מ-5 ופחות מ-8 שעות ליום/בשבוע) ושכר עבודה/עובד יומי; ממשכורת חלקית ינוכה מס בשיעור מרבי אלא אם היא הכנסה יחידה, ומשכר עבודה לפי לוח יומי:
# תוספת א': משכורת החודש x12; מס לפי סעיפים 121, 121ב; בניכוי נקודות זיכוי; חלקי 12; "כל שבר של שקל חדש מן המשכורת או
# מן המס העולה על 49 אגורות יראוהו כשקל חדש אחד" (עיגול half-up לשקל שלם).
# תקנה 4(א) משכורת בלתי קבועה (בונוס/מענק): מס מנוכה = "הפרש המס" x 12, כאשר הפרש המס = המס על משכורת החודש
# בתוספת 1/12 מהמשכורת הבלתי קבועה פחות המס על משכורת החודש לאותו חודש. (4)(ג): פקיד שומה רשאי לשנות את השיעור.
# עובד יומי (4)(ב): אותו עיקרון עם x300 והלוח היומי - לא מיושם כאן.
# הערה: תקנה 3 אינה מזכירה ניכוי מצטבר; חישוב המס החודשי לפי התקנות הוא x12 מהחודש עצמו.
def monthly_deduction_by_regulation(monthly_taxable, points, year=2026):
    """המס החודשי לפי תוספת א': מס על (חודשי x12), פחות נקודות x 242 x12, חלקי 12, מעוגל לשקל."""
    if year not in BRACKETS:
        return None
    gross_tax = tax_before_credits(D(str(monthly_taxable)), 1, year)
    credit = D(str(points)) * CREDIT_POINT_2025
    return r0(max(gross_tax - credit, D(0)))


def irregular_salary_tax(regular_monthly_taxable, irregular_amount, points, year=2026):
    """תקנה 4(א). מחזיר item עם המס לניכוי מהמשכורת הבלתי קבועה. עיגול כל רכיב חודשי לשקל לפי שלב 5 בתוספת א' (הנחה מפורשת)."""
    if year not in BRACKETS:
        return item(None, MANUAL, "מדרגות לשנה זו לא הוגדרו")
    b = D(str(irregular_amount))
    if b < 0:
        return item(None, MANUAL, "משכורת בלתי קבועה שלילית")
    m = D(str(regular_monthly_taxable))
    with_b = monthly_deduction_by_regulation(m + b / 12, points, year)
    base = monthly_deduction_by_regulation(m, points, year)
    return item(D((with_b - base) * 12), BY_LAW,
                "תקנה 4(א): הפרש המס x12 (המס על החודש + 1/12 מהבונוס פחות המס על החודש); עיגול כל מס חודשי לשקל; "
                "פקיד שומה רשאי לשנות (4(ג)); לא כולל מקרים מיוחדים (פושט רגל/פירוק - לפחות 25%)")


# תקנה 4(ב) + תוספת ב' (btl.gov.il/Laws1/02_0103_100076.pdf, ק"ת 5502, 18.2.1993, נקרא 16.11.2026; הנוסח סרוק עם שגיאות עימוד):
# שכר יומי x300 -> מס לפי סעיפים 121,121ב -> פחות נקודות זיכוי -> חלקי 300 -> מנוכה מהשכר היומי; "יותר מ-49 אגורות = שקל".
# סדר השלבים בנוסח (נקרא ב-nevo וב-wikisource, 19.11.2026): (4) המס אחרי נקודות הזיכוי מחולק ב-300 והמנה מנוכה; (5) "כל שבר של שקל חדש משכר עבודה או מן המס
# העולה על 49 אגורות יראוהו כשקל חדש אחד". שלב העיגול בא אחרי החלוקה, ולכן העיגול על הניכוי היומי הסופי. הסעיף זהה בלשונו לתוספת א', ובתוספת א' אומת מול סימולטור רשות המסים שרק המס מעוגל.
def daily_wage_deduction(daily_wage, points, year=2026):
    if year not in BRACKETS:
        return item(None, MANUAL, "מדרגות לשנה זו לא הוגדרו")
    w = D(str(daily_wage))
    if w < 0:
        return item(None, MANUAL, "שכר יומי שלילי")
    annual_tax = tax_before_credits(w * 300 / 12, 1, year) * 12
    credit = D(str(points)) * CREDIT_POINT_2025 * 12
    ded = r0(max(annual_tax - credit, D(0)) / 300)
    return item(ded, BY_LAW, "תוספת ב': שכר יומי x300, מס שנתי, פחות נקודות זיכוי (x12), חלקי 300, עיגול לשקל (שלב 5 בתוספת ב', אחרי החלוקה ב-300)")


def irregular_daily_tax(daily_wage, irregular_amount, points, year=2026):
    """תקנה 4(ב): הפרש המס (מס על יום+1/300 מהתשלום פחות מס על היום, לפי תוספת ב') x300."""
    if year not in BRACKETS:
        return item(None, MANUAL, "מדרגות לשנה זו לא הוגדרו")
    b = D(str(irregular_amount))
    if b < 0:
        return item(None, MANUAL, "משכורת בלתי קבועה שלילית")
    w = D(str(daily_wage))
    diff = daily_wage_deduction(w + b / 300, points, year)["value"] - daily_wage_deduction(w, points, year)["value"]
    return item(D(diff * 300), BY_LAW, "תקנה 4(ב): הפרש המס x300 לעובד יומי; פקיד שומה רשאי לשנות (4(ג))")


# תקנה 6 (אותו מקור): שיעורי ניכוי מיוחדים. הערה: (א) נפטר: הנמוך מבין 40% והשיעור שהיה חל; (ב) תשלום ללא משכורת חודשית: השיעור המרבי;
# (ד) קופת גמל המשלמת חופשה/מחלה/חגים: 25%; (ז) שבתון: 35%; (ח) מלווה נכה: עד 25%; (ט) שכר יומי חד-פעמי לקבוצה: 35%; (י) היוון קצבה: 15% מהרכיב הרווחי.
REG6_SPECIAL_RATES = {"gemel_leave_sick_holiday": D("0.25"), "shabbaton": D("0.35"), "disabled_companion_max": D("0.25"),
                      "lump_daily_group": D("0.35"), "annuity_capitalization": D("0.15"), "deceased_heirs_max": D("0.40")}


# תקנה 4(ב) (btl.gov.il/Laws1/02_0103_100076.pdf, נוסח ק"ת 5502, 18.2.1993, נקרא 16.11.2026): לעובד יומי - אותה שיטה, כפול 300
# (ממומש כעת בפונקציות למעלה) בנוסח זה לתקנה 4 רק (א)-(ג);
# 4(ג) פקיד שומה רשאי לקבוע שיעור אחר. ייתכנו תיקונים מאוחרים לנוסח שאינם בו.
# תקרות לפי לוח עזר 2026 פרק ג' (עמ' 12, אומת מול תמונת העמוד): 3(ה3) תקרת הפרשות המעביד לקופת גמל לקצבה 34,423 לחודש;
# תקרת סכום הפיצויים להפקדה 3(ה3): 45,600 לשנה; תקרת ניכוי הוצאות על מתנות 240 לאדם לשנה (עמ' 13-14).
EMPLOYER_PENSION_CEILING_3E3_MONTHLY_2026 = D("34423")
SEVERANCE_DEPOSIT_CEILING_3E3_ANNUAL_2026 = D("45600")
GIFT_EXPENSE_CEILING_ANNUAL_2026 = D("240")


def tax_before_credits(cum_taxable, months, year=2025):
    g, tax, prev = D(str(cum_taxable)), D(0), D(0)
    for upper, rate in BRACKETS[year]:
        top = g if upper is None else min(g, upper * months)
        if top > prev:
            tax += (top - prev) * rate
        if upper is None or g <= upper * months:
            break
        prev = upper * months
    return tax


def income_tax(year, month, mode, taxable_gross, points, prev, deposits, life, weight=1, locality=None,
               fixed_rate=None):
    """
    mode: 'cumulative' (משרה עיקרית עם 101) או 'no_coordination' (47% מהברוטו).
    prev: dict עם cum_taxable, cum_tax, cum_deposits, cum_life (ואופציונלי cum_weight).
    deposits: הפקדות עובד לפנסיה החודש (זיכוי 35% עד התקרה); life: ביטוח חיים (זיכוי 25%).
    weight: משקל החודש (1 = חודש מלא; 17/25 = חודש עבודה חלקי). משפיע על המדרגות ועל נקודות הזיכוי
            (נצפה בתלוש אחד: נובמבר 2025, עובד שהתחיל ב-12.1). לא משפיע על תקרת ההפקדות.
    מחזיר (שורת מס, מצטבר חדש).
    """
    tg = D(str(taxable_gross))
    cum_weight = prev.get("cum_weight", D(month - 1)) + D(str(weight))
    new = {
        "cum_taxable": prev["cum_taxable"] + tg,
        "cum_deposits": prev["cum_deposits"] + D(str(deposits)),
        "cum_life": prev["cum_life"] + D(str(life)),
        "cum_weight": cum_weight,
    }
    if mode == "fixed_rate":
        # אישור תיאום מס עם שיעור ניכוי קבוע: חשב השכר מזין את השיעור מהאישור; האישור עצמו לא נבדק במערכת
        if fixed_rate is None or not (D(0) <= D(str(fixed_rate)) <= D("0.5")):
            new["cum_tax"] = prev["cum_tax"]
            return item(None, MANUAL, "אישור תיאום מס: שיעור הניכוי חסר או לא תקין"), new
        month_tax = r0(tg * D(str(fixed_rate)))
        new["cum_tax"] = prev["cum_tax"] + month_tax
        return item(month_tax, ACCOUNTANT, f"ניכוי בשיעור קבוע {D(str(fixed_rate)) * 100:g}% לפי אישור תיאום מס שהוזן על ידי חשב השכר (האישור והיקף תוקפו לא נבדקו); העיגול לשקל שלם של התוצאה אינו כתוב בתקנות לניכוי בשיעור קבוע"), new
    if mode == "two_rates":
        # אישור תיאום מס למשרה משנית: שיעור נמוך עד תקרה שנתית מצטברת ושיעור גבוה מעליה. fixed_rate = (שיעור_נמוך, תקרה_שנתית, שיעור_גבוה).
        # האישור שנתי (ינואר-דצמבר) גם אם הוצא באמצע השנה: המס המצטבר מחושב מתחילת השנה והחודש מנכה את ההפרש.
        # מקור: אישור רואת חשבון (18.11.2026). נוסח אחיד של הוראה רשמית למעסיק לא נמצא -> ACCOUNTANT.
        try:
            low, ceil_, high = (D(str(x)) for x in fixed_rate)
        except Exception:
            low = None
        if low is None or not (D(0) <= low <= high <= D("0.5")) or ceil_ < 0:
            new["cum_tax"] = prev["cum_tax"]
            return item(None, MANUAL, "אישור תיאום מס בשני שיעורים: נתוני האישור חסרים או לא תקינים"), new
        cum_total = low * min(new["cum_taxable"], ceil_) + high * max(new["cum_taxable"] - ceil_, D(0))
        month_tax = max(r0(cum_total) - prev["cum_tax"], D(0))
        new["cum_tax"] = prev["cum_tax"] + month_tax
        return item(month_tax, ACCOUNTANT, f"אישור תיאום מס בשני שיעורים: {low * 100:g}% עד תקרה מצטברת {ceil_:,.0f} ₪ ו-{high * 100:g}% מעליה; החישוב מצטבר מינואר (האישור שנתי); המעסיק עשוי להידרש לכלול גם הפרשות מעסיק לפנסיה/פיצויים/השתלמות בהכנסה החייבת לפי האישור (לא ממומש)"), new
    if mode == "no_coordination":
        month_tax = r0(tg * NO_COORDINATION_RATE)
        new["cum_tax"] = prev["cum_tax"] + month_tax
        return item(month_tax, VERIFIED, "47% בלי תיאום מס (נבדק במרץ 2025 ובמשרה נוספת 2024); בסיס בנוסח: תקנה 5(א) לתקנות ניכוי ממשכורת - שיעור מרבי (ללא טופס 101 / משכורת חלקית / משרה נוספת), btl.gov.il/Laws1/02_0103_100076.pdf"), new
    if year not in (2025, 2026):
        new["cum_tax"] = prev["cum_tax"]
        return item(None, MANUAL, "שנת המס לא נתמכת; הזינו את המס ידנית"), new
    before = tax_before_credits(new["cum_taxable"], cum_weight, year)
    eligible = min(new["cum_deposits"], PENSION_CREDIT_CAP_MONTHLY * month)
    loc_credit = D(0)
    if locality is not None:    # (שיעור, תקרה שנתית): הנחה על הכנסה מיגיעה אישית עד התקרה (מצטבר: תקרה x חודשים/12)
        l_rate, l_cap = locality
        loc_credit = l_rate * min(new["cum_taxable"], l_cap * cum_weight / 12)
    credits = min(before, D(str(points)) * CREDIT_POINT_2025 * cum_weight
                  + PENSION_CREDIT_RATE * eligible
                  + LIFE_CREDIT_RATE * new["cum_life"] + loc_credit)
    cum_tax = r0(before - credits)
    month_tax = cum_tax - prev["cum_tax"]
    new["cum_tax"] = cum_tax
    note = "מצטבר, ערך נקודה 242, תקרת הפקדות 679 לחודש"
    if year == 2026:
        note += " | מדרגות 2026 לפי לוח עזר רשות המסים; נבדק מול תלושים רק עד 14,647"
    if cum_weight != month:
        note += " | חודש עבודה חלקי: לא מאומת מעבר לתלוש אחד"
    if new["cum_deposits"] > PENSION_CREDIT_CAP_MONTHLY * month:
        note += " | הפקדות מעל התקרה: הזיכוי הוגבל"
    if month_tax < 0:
        note += " | חודש עם החזר מס"
    status = ACCOUNTANT
    if locality is not None:
        status = BY_LAW
        note += " | הנחת יישוב מוטב §11 לפי לוח עזר 2026 (פרק ח'); יישום מצטבר חודשי לא אומת מול תלוש"
    return item(month_tax, status, note + " | מקור לעקרון: דוח מבקר המדינה 72א (2021) עמ' 1251 - \"חישוב המס הוא שנתי ולא חודשי\", המעסיק מנכה לפי המשכורת הממוצעת בחודשים שבהם עבד כאילו יעבוד שנת מס מלאה (הערה 28: תקנה 3 לתקנות הניכוי); נוסח הוראה מפורש של רשות המסים לא נמצא"), new



# ---------------------------------------------------------------------------
# שווי הטבות (זקיפה): רכב צמוד ורט"ן. מקורות ראשוניים: תקנות מס הכנסה (שווי השימוש ברכב), התשמ"ז-1987; לוח עזר לחישוב מס הכנסה ממשכורת 2025 ו-2026 (gov.il);
# תקנות מס הכנסה (שווי השימוש ברדיו טלפון נייד), התשס"ב-2002 (תקנה 2: מחצית ההוצאה או הסכום הנקוב, לפי הנמוך; הסכום המתואם 115 ₪ בלוחות העזר 2025 ו-2026).
# הטבה חייבת במס ובביטוח לאומי, אך לא משולמת במזומן: נזקפת לברוטו ומנוכה בחזרה מהנטו.
# ---------------------------------------------------------------------------
CAR_RATE = D("0.0248")          # המודל הליניארי: 2.48% ממחיר הרכב המתואם (רכב שנרשם מ-1.1.2010)
CAR_PRICE_CAP = D("583100")
CAR_MAX_WEIGHT_KG = D("3500")   # "רכב" = משקל כולל מותר פחות מ-3,500 ק"ג (תקנות ניכוי הוצאות רכב 1995, הגדרת "רכב"; תקנות שווי השימוש מפנות אליה)     # תקרת המחיר המתואם
CAR_REDUCTION = {"regular": D(0), "hybrid": D(560), "plugin": D(1130), "electric": D(1350)}
PHONE_DEFAULT_VALUE = D("115")  # הסכום הנקוב בתקנות רט"ן בעדכון שנתי: 115 ₪ לחודש (לוח עזר 2025 ו-2026, gov.il)


def is_operational_car(business_use_only, leaves_workplace_after_hours, workplace_is_residence=False):
    """
    רכב תפעולי (תקנה 1 לתקנות מס הכנסה (ניכוי הוצאות רכב), התשנ"ה-1995, פסקה (2), btl.gov.il/Laws1/02_0103_100052.pdf):
    תנאים מצטברים: לא הועמד לרשות עובד, משמש לצורכי העסק בלבד, נמצא במקום העיסוק ולא בבית המגורים,
    ובתום שעות העבודה אינו יוצא ממקום העיסוק. (פסקה (1) - רכב ביטחון - לא נתמכת.) התקנה מותנית בהנחת דעתו של פקיד השומה.
    כל תשובה חסרה (None) נחשבת כאי-עמידה בתנאי: ברירת המחדל היא לזקוף שווי.
    """
    return (business_use_only is True and leaves_workplace_after_hours is False
            and workplace_is_residence is False)


# תקרת מחיר מתואם והפחתות לפי שנה. 2026: לוח עזר 2026 של רשות המסים, פרק ד (תקרה 596,860; הפחתות 580/1,150/1,380, הוראת שעה עד 31.12.2028).
# 2025: תקרה 583,100 והפחתות 560 / 1,130 / 1,350 לפי לוח עזר 2025 של רשות המסים (gov.il, פרק ד); תואם גם לטיוטת תקנות מס הכנסה (שווי השימוש ברכב) (הוראת שעה) (תיקון) התשפ"ו-2025,
# אתר החקיקה הממשלתי (tazkirim.gov.il): "בשנת 2025 סכומם עומד על 560 ש"ח עבור רכב היברידי, 1,130 עבור פלאג-אין ו-1,350 עבור רכב חשמלי".
CAR_PARAMS = {
    2025: (D("583100"), {"regular": D(0), "hybrid": D(560), "plugin": D(1130), "electric": D(1350)}),
    2026: (D("596860"), {"regular": D(0), "hybrid": D(580), "plugin": D(1150), "electric": D(1380)}),
}


def car_benefit(price, kind="regular", operational=False, gross_weight_kg=None, year=None):
    """שווי שימוש חודשי ברכב צמוד (נרשם מ-2010). מעוגל ל-10 ש"ח (תקנות שווי השימוש ברכב).
    year: שנת המס; ללא שנה = ערכי 2025 (תאימות). שנה שאינה 2025/2026 -> ידני."""
    cap, reductions = CAR_PARAMS.get(2025 if year is None else int(year), (None, None))
    if cap is None:
        return item(None, MANUAL, f"שנה {year}: תקרת מחיר והפחתות לא הוגדרו, נדרשת הזנה ידנית")
    if kind not in reductions:
        return item(None, MANUAL, "סוג רכב לא מוכר")
    if gross_weight_kg is not None and D(str(gross_weight_kg)) >= CAR_MAX_WEIGHT_KG:
        return item(D(0), BY_LAW, "משקל כולל מותר 3,500 ק\"ג ומעלה: אינו 'רכב' לעניין שווי השימוש, אין שווי (הגדרת 'רכב' בתקנות מס הכנסה (ניכוי הוצאות רכב), התשנ\"ה-1995, שאליה מפנה תקנה 1 לתקנות שווי השימוש: משקל פחות מ-3,500 ק\"ג)")
    if operational:
        return item(D(0), BY_LAW, "רכב תפעולי: אין שווי שימוש (תקנות מס הכנסה, ניכוי הוצאות רכב)")
    raw = min(D(str(price)), cap) * CAR_RATE
    value = (raw / 10).quantize(D("1"), rounding=ROUND_HALF_UP) * 10 - reductions[kind]
    src = "לוח עזר 2026 של רשות המסים" if year is not None and int(year) == 2026 else "טבלת 2025"
    return item(max(value, D(0)), BY_LAW,
                f"מודל ליניארי 2.48%, {src}, תקרת מחיר {cap}; רכב שנרשם לפני 2010 וניכוי השתתפות עובד לא נתמכים")


def works_committee_benefit(employer_amount_per_employee, specific_per_employee):
    """
    השתתפות המעסיק בפעילות ועד עובדים (יום כיף, טיול, מסיבה).
    מקור: פקודת מס הכנסה. סעיף 2(2)(א): כל טובת הנאה שניתנה לעובד ממעבידו היא הכנסת עבודה.
    סעיף 32(11): הוצאה למתן טובת הנאה שלא ניתן לייחסה לעובד פלוני אינה מותרת בניכוי למעביד,
    ו"הוצאות שאינן ניתנות לניכוי כאמור לא ייראו כהכנסת עבודה בידי העובדים".
    לכן: השתתפות שנקבעה לפי עובד (ניתן לייחס) = הכנסת עבודה בסכום ההשתתפות של המעסיק לעובד;
    השתתפות כוללת שלא ניתן לייחס = אין זקיפה (הוצאה עודפת אצל המעסיק). הסיווג נקבע על ידי המשתמש.
    הערכת השווי לפי עלות המעסיק לעובד אינה מפורשת בנוסח החוק ושווה לשיטת הזקיפה המקובלת.
    """
    ref = "פקודת מס הכנסה, סעיפים 2(2)(א) ו-32(11)"
    amount = D(str(employer_amount_per_employee))
    if specific_per_employee is True:
        return item(r2(amount), BY_LAW, "השתתפות מעסיק שניתן לייחס לעובד: הכנסת עבודה בסכום ההשתתפות (" + ref + ")")
    if specific_per_employee is False:
        return item(D(0), BY_LAW, "השתתפות כוללת שלא ניתן לייחס לעובד: לא נחשבת הכנסת עבודה (" + ref + ")")
    return item(None, MANUAL, "נדרש טיפול ידני: לא ידוע אם ניתן לייחס את ההשתתפות לעובד מסוים")

TEAM_BUILDING_COST_CAP = D("400")          # ליום ללא לינה, לפי ההנחיה (נכון ל-2018)
TEAM_BUILDING_COST_CAP_OVERNIGHT = D("700")  # ליום עם לינה


def team_building_benefit(employer_initiated, workday, full_pay, spouses_allowed, in_israel,
                          schedule_by_employer, professional_purpose, per_employee_amount=False,
                          weekdays_only=None, cost_per_day=None, overnight=False, documents_kept=None):
    """
    פעילות גיבוש: אין זקיפה כשכל התנאים המצטברים בהנחיית רשות המסים מתקיימים
    (סימוכין MA50D1-6-62-18, 9.4.2018): יוזמת מעסיק, יום עבודה בשכר מלא, בלי בני זוג/קרובים, בישראל,
    לו"ז של המעסיק, תוכן מקצועי/העשרה, פעילות רק בשבוע העבודה, עלות סבירה (עד 400 ₪ ליום, 700 ₪ ליום עם לינה, נכון למועד ההנחיה),
    ושמירת מסמכים. אם תנאי חסר, לא ידוע או לא מתקיים: אין חישוב והכרעה ידנית (אין "זקיפה אוטומטית" כי ההנחיה אינה קובעת שווי).
    """
    cap = TEAM_BUILDING_COST_CAP_OVERNIGHT if overnight else TEAM_BUILDING_COST_CAP
    cost_ok = None if cost_per_day is None else D(str(cost_per_day)) <= cap
    conds = [employer_initiated, workday, full_pay, not spouses_allowed if spouses_allowed is not None else None,
             in_israel, schedule_by_employer, professional_purpose,
             not per_employee_amount if per_employee_amount is not None else None,
             weekdays_only, cost_ok, documents_kept]
    if all(c is True for c in conds):
        return item(D(0), BY_LAW, "כל תנאי ההנחיה מתקיימים (רשות המסים 9.4.2018, כולל עלות סבירה ושמירת מסמכים): אין זקיפה")
    return item(None, MANUAL, "תנאי גיבוש חסר, לא ידוע או לא מתקיים (כולל עלות עד 400/700 ₪ ליום, שמירת מסמכים, פעילות בימות השבוע): יש להכריע ידנית")

def phone_benefit(monthly_expense, employee_share_rate="0", employee_share_amount="0"):
    """
    שווי רט"ן = הנמוך מבין חצי ההוצאה החודשית ל-115 ש"ח, פחות מה שהעובד משלם
    (באחוז מההוצאה המלאה ו/או בסכום קבוע). תקנה 2 לתקנות מס הכנסה (שווי השימוש ברדיו טלפון נייד), התשס"ב-2002;
    הסכום 115 ₪ לפי לוח העזר של רשות המסים 2025 ו-2026 (gov.il).
    """
    exp = D(str(monthly_expense))
    base = min(exp / 2, PHONE_DEFAULT_VALUE)
    paid = exp * D(str(employee_share_rate)) + D(str(employee_share_amount))
    return item(max(r2(base - paid), D(0)), BY_LAW, "תקנה 2 לתקנות שווי השימוש ברט\"ן: הנמוך מ-50% מההוצאה ו-115 ₪ (לוח עזר 2025/2026), פחות השתתפות העובד")


# ---------------------------------------------------------------------------
# דמי הבראה 2025: 418 ₪ ליום, הפחתה של יום הבראה אחד, מחצית יום לשכר נמוך (עד 6,150 ₪). מקור: חוק הקפאה והפחתה של דמי הבראה, ספר החוקים 27.3.2025 (ראו sources_catalog).
# מ-2026: 451.50 ₪ ליום (צו הרחבה, י"פ 14863, 18.8.2026) - לא מחושב כאן עדיין (שנה שאינה 2025 = ידני).
# ---------------------------------------------------------------------------
RECUPERATION_DAY_2025 = D("418")
RECUPERATION_LOW_SALARY_2025 = D("6150")


# ימי הבראה לפי שנת ותק (מגזר פרטי): נקרא מהמקור הרשמי - י"פ 4689 (20.10.1998) עמ' 189, סעיף 5(א) (אומת מול לוח 1 של מרכז המחקר והמידע של הכנסת) (20.1.2025, מצטט את משרד העבודה): 1->5, 2-3->6, 4-10->7, 11-15->8, 16-19->9, 20+->10.
def recuperation_days(seniority_year):
    y = int(seniority_year)
    if y < 1:
        return item(None, MANUAL, "שנת ותק לא תקינה")
    if y == 1:
        return item(D(5), BY_LAW, "שנה 1: 5 ימים (י״פ 4689 20.10.1998 עמ' 189, צו הרחבה סעיף 5(א)) | מעודכן ל-2026, ניתן לעדכן אם השתנה החוק")
    if y in (2, 3):
        return item(D(6), BY_LAW, f"שנה {y}: 6 ימים (י״פ 4689 20.10.1998 עמ' 189, צו הרחבה סעיף 5(א)) | מעודכן ל-2026, ניתן לעדכן אם השתנה החוק")
    if 4 <= y <= 10:
        return item(D(7), BY_LAW, "שנים 4-10: 7 ימים (י״פ 4689 20.10.1998 עמ' 189, צו הרחבה סעיף 5(א)) | מעודכן ל-2026, ניתן לעדכן אם השתנה החוק")
    if 11 <= y <= 15:
        return item(D(8), BY_LAW, "שנים 11-15: 8 ימים (י״פ 4689 20.10.1998 עמ' 189, צו הרחבה סעיף 5(א)) | מעודכן ל-2026, ניתן לעדכן אם השתנה החוק")
    if 16 <= y <= 19:
        return item(D(9), BY_LAW, "שנים 16-19: 9 ימים (י״פ 4689 20.10.1998 עמ' 189, צו הרחבה סעיף 5(א)) | מעודכן ל-2026, ניתן לעדכן אם השתנה החוק")
    return item(D(10), BY_LAW, "משנה 20 ואילך: 10 ימים (י״פ 4689 20.10.1998 עמ' 189, צו הרחבה סעיף 5(א)) | מעודכן ל-2026, ניתן לעדכן אם השתנה החוק")


RECUPERATION_DAY_2025_MAX = D("471.4")


def recuperation_partial_reduction(entitled_days, avg_monthly_salary_oct_dec_2024, job_fraction="1"):
    """
    "עובד בהפחתה חלקית" לפי חוק הקפאה והפחתה של דמי הבראה בשנת 2025: זכאי ללא החוק ל*פחות משישה* ימי הבראה,
    ומשכורתו החודשית הממוצעת באוקטובר-דצמבר 2024 אינה עולה על 6,150 ₪ (כפול חלקיות המשרה).
    """
    days = D(str(entitled_days)); sal = D(str(avg_monthly_salary_oct_dec_2024))
    limit = RECUPERATION_LOW_SALARY_2025 * D(str(job_fraction))
    return days < 6 and sal <= limit


def recuperation_pay(year, entitled_days, job_fraction="1", period_fraction="1", reduced_partial=None, day_price=None):
    """
    דמי הבראה 2025 לתשלום = ימים x מחיר יום x חלקיות, פחות הפחתה של מחיר יום הבראה אחד
    (או מחציתו לעובד בהפחתה חלקית), באותן חלקיות. מחיר היום: לא פחות מ-418 ולא יותר מ-471.4 (ברירת מחדל 418).
    מקור: חוק הקפאה והפחתה של דמי הבראה בשנת 2025, התשפ"ה-2025 (ספר החוקים 27.3.2025), הגדרות וסעיף 3.
    reduced_partial חייב להיקבע במפורש (ראו recuperation_partial_reduction); None = הכרעה ידנית.
    רק 2025: שנים אחרות לא מחושבות. החישוב ברוטו.
    """
    if year != 2025:
        return item(None, MANUAL, "תעריף וכללי הפחתה מוגדרים רק ל-2025")
    if reduced_partial is None:
        return item(None, MANUAL, "יש להכריע אם העובד בהפחתה חלקית (פחות משישה ימי הבראה ושכר ממוצע 10-12/2024 עד 6,150, כפול חלקיות המשרה)")
    price = RECUPERATION_DAY_2025 if day_price is None else min(max(D(str(day_price)), RECUPERATION_DAY_2025), RECUPERATION_DAY_2025_MAX)
    frac = D(str(job_fraction)) * D(str(period_fraction))
    gross = D(str(entitled_days)) * price * frac
    cut = price * (D("0.5") if reduced_partial else D(1)) * frac
    return item(r2(max(gross - cut, D(0))), BY_LAW, "ימים x מחיר יום (418-471.4) x חלקיות, פחות הפחתה (יום אחד, או חצי יום בהפחתה חלקית); חוק הקפאה והפחתה של דמי הבראה בשנת 2025, הגדרות וסעיף 3")


# ---------------------------------------------------------------------------
# רצפות הפקדה לפנסיית חובה (צו ההרחבה לפנסיית חובה, נחתם 26.5.2016; מינימום מ-1.1.2017): עובד 6%, מעסיק 6.5%, פיצויים 6%.
# מקור: נוסח הצו עצמו נקרא מילה במילה (16.11.2026): צו הגדלת ההפרשות 2016 (נחתם 23.5.2016) סעיף 3 + צו הפנסיה המשולב י"פ 6302 (27.9.2011). ראו labor_rules.SOURCES["pension_floor"]. הבסיס ("השכר הקובע": שכר ורכיבים לפי חוק/תקנות פיצויים, עד השכר הממוצע) לא ממומש כאן -> ידני.
PENSION_FLOOR = {"employee": D("0.06"), "employer": D("0.065"), "severance": D("0.06")}


def pension_floor_check(employee_rate, employer_rate, severance_rate):
    """בודק שהשיעורים שהוגדרו לא נמוכים מרצפת הצו. מחזיר רשימת הפרות (ריקה = תקין). לא משנה חישוב."""
    got = {"employee": D(str(employee_rate)), "employer": D(str(employer_rate)), "severance": D(str(severance_rate))}
    return [k for k, floor in PENSION_FLOOR.items() if got[k] < floor]


# פנסיה וקרן השתלמות: כפל שיעור שהוגדר בבסיס (נבדק מול מירב 2019 וסיינל 2023)
# ---------------------------------------------------------------------------
def deposit(base, rate):
    return item(r2(D(str(base)) * D(str(rate))), ACCOUNTANT, "בסיס x שיעור שהוזן (לפי הסכם/תקנון הקופה של העובד); השיעור עצמו אינו כלל חוק")


ZERO_PREV = {"cum_taxable": D(0), "cum_tax": 0, "cum_deposits": D(0), "cum_life": D(0)}


def compute_month(*, year, month, gross, taxable_gross=None, points="2.75",
                  mode="cumulative", prev=None,
                  pension_base=None, pension_employee_rate="0.06",
                  study_fund_employee_rate="0",
                  life_insurance=0, manual_income_tax=None, other_deductions=0,
                  employer_pension_rate="0", employer_severance_rate="0",
                  employer_study_fund_rate="0", weight=1, noncash_benefits=0,
                  irregular_payment=0, locality=None, fixed_rate=None):
    gross = D(str(gross))
    taxable_gross = gross if taxable_gross is None else D(str(taxable_gross))
    base = gross if pension_base is None else D(str(pension_base))
    prev = prev or dict(ZERO_PREV)

    ni, health = ni_health(year, gross, month)
    pension = deposit(base, pension_employee_rate)
    study = deposit(base, study_fund_employee_rate)
    tax, cum = income_tax(year, month, mode, taxable_gross, points, prev,
                          pension["value"], life_insurance, weight, locality, fixed_rate)
    if manual_income_tax is not None:   # חשב השכר רשאי תמיד לעקוף את החישוב; מסומן כידני
        tax = item(r0(manual_income_tax), MANUAL, "הוזן ידנית על ידי המשתמש")
        cum["cum_tax"] = prev["cum_tax"] + tax["value"]

    items = {"income_tax": tax, "national_insurance": ni, "health": health,
             "pension_employee": pension, "study_fund_employee": study}
    if D(str(irregular_payment)) > 0:
        # תשלום חריג (הבראה, בונוס...) בתוך הברוטו: מס ב"ל ובריאות מחושבים כאן כאילו שכר חודשי רגיל,
        # וזה לא הכלל (תקנה 4 למס; פריסה לפי תקנה 5 לתקנות ב"ל). לכן מסומנים ידניים ולא מאומתים.
        for k in ("income_tax", "national_insurance", "health"):
            if items[k]["value"] is not None:
                items[k] = dict(items[k], status=MANUAL,
                                note=items[k]["note"] + " | תשלום חריג בחודש: ערך תחשיבי כשכר רגיל, לא מאומת (ראו special_payslips)")
    pn = prev.get("cum_ni_base")
    if pn is None and month == 1:
        pn = D(0)
    if pn is not None:            # מצטבר שכר חייב בביטוח לאומי (לתלוש לפי סעיף 24); לא ידוע -> לא נשמר
        cum["cum_ni_base"] = D(str(pn)) + gross
    unresolved = [k for k, v in items.items() if v["value"] is None]
    net = None
    if not unresolved:
        deductions = sum((D(str(v["value"])) for v in items.values()), D(0))
        deductions += D(str(life_insurance)) + D(str(other_deductions)) + D(str(noncash_benefits))
        net = r2(gross - deductions)
    items = {k: dict(v, basis=basis.for_item(k)) for k, v in items.items()}
    statuses = {v["status"] for v in items.values()}
    if unresolved or MANUAL in statuses:
        overall = MANUAL
    elif BY_LAW in statuses:
        overall = BY_LAW
    elif ACCOUNTANT in statuses:
        overall = ACCOUNTANT
    else:
        overall = VERIFIED
    employer = {
        "pension": deposit(base, employer_pension_rate),
        "severance": deposit(base, employer_severance_rate),
        "study_fund": deposit(base, employer_study_fund_rate),
    }
    ni_emp = ni_employer(year, gross)
    if irregular_payment and D(str(irregular_payment)) > 0 and ni_emp["value"] is not None:
        ni_emp = dict(ni_emp, status=MANUAL, note=ni_emp["note"] + " | תשלום חריג בחודש: לא מאומת")
    employer["national_insurance"] = dict(ni_emp, basis=basis.for_item("national_insurance_employer"))
    return {"year": year, "month": month, "gross": r2(gross), "items": items,
            "employer": employer, "pension_base": r2(base),
            "net": net, "overall_status": overall, "unresolved": unresolved,
            "cumulative": cum}
