"""
מנוע חישוב שכר אחיד לפי שנה. כל רכיב חוזר עם סטטוס אימות:

  VERIFIED  - שוחזר מול תלוש אמיתי באגורה (נבדק ב-test_payslips.py / test_engine.py)
  BY_LAW    - חושב לפי שיעורי החוק אך לא נבדק מול תלוש באגורה (יש סטייה ידועה/אפשרית)
  MANUAL    - לא מחושב. המשתמש חייב להזין ידנית. המערכת לא מנחשת.

שנים נתמכות: 2025 ו-2026 בלבד. כל שנה אחרת -> MANUAL.
"""
from decimal import Decimal, ROUND_HALF_UP

D = Decimal

VERIFIED = "מאומת"
BY_LAW = "לפי חוק - לא נבדק מול תלוש"
MANUAL = "נדרש טיפול ידני"
ACCOUNTANT = "לפי רואת חשבון (אין מקור ראשוני)"


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


# ---------------------------------------------------------------------------
# מס הכנסה
# ---------------------------------------------------------------------------
# מדרגות חודשיות. 2025: כל-זכות. 2026: לוח עזר של רשות המסים "לחישוב מס הכנסה ממשכורת לינואר 2026 ואילך"
# (מעודכן לאפריל 2026): שנתי 84,120 / 120,720 / 228,000 / 301,200 / 560,280, חלקי 12.
# ה-20% וה-31% הורחבו בחוק שפורסם ב-31.3.2026 (בתוקף מ-1.1.2026). מס יסף (50%) מעל 60,130 - הנחה שלא השתנה.
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
# תקנות מס הכנסה (ניכוי ממשכורת ומשכר עבודה), התשנ"ג-1993 (נוסח נבו/פרישה, נקרא 16.11.2026):
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


# תקנה 4(ב) (btl.gov.il/Laws1/02_0103_100076.pdf, נוסח ק"ת 5502, 18.2.1993, נקרא 16.11.2026): לעובד יומי - אותה שיטה, כפול 300
# במקום 12 (הפרש המס כשמוסיפים 1/300 מהתשלום). לא ממומש: ערך נקודת זיכוי יומית לפי תוספת ב' לא נקרא. בנוסח זה לתקנה 4 רק (א)-(ג);
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
        return item(month_tax, BY_LAW, f"ניכוי בשיעור קבוע {D(str(fixed_rate)) * 100:g}% לפי אישור תיאום מס שהוזן על ידי חשב השכר (האישור והיקף תוקפו לא נבדקו)"), new
    if mode == "no_coordination":
        month_tax = r0(tg * NO_COORDINATION_RATE)
        new["cum_tax"] = prev["cum_tax"] + month_tax
        return item(month_tax, VERIFIED, "47% בלי תיאום מס (נבדק במרץ 2025 ובמשרה נוספת 2024)"), new
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
# שווי הטבות (זקיפה): רכב צמוד ורט"ן. מקור: טבלאות מס הכנסה 2025 של לשכת רו"ח (למבחני חשב שכר בכיר)
# הטבה חייבת במס ובביטוח לאומי, אך לא משולמת במזומן: נזקפת לברוטו ומנוכה בחזרה מהנטו.
# ---------------------------------------------------------------------------
CAR_RATE = D("0.0248")          # המודל הליניארי: 2.48% ממחיר הרכב המתואם (רכב שנרשם מ-1.1.2010)
CAR_PRICE_CAP = D("583100")
CAR_MAX_WEIGHT_KG = D("3500")   # רכב כבד מזה אינו "רכב" לעניין שווי שימוש     # תקרת המחיר המתואם
CAR_REDUCTION = {"regular": D(0), "hybrid": D(560), "plugin": D(1130), "electric": D(1350)}
PHONE_DEFAULT_VALUE = D("115")  # תקרת שווי רט"ן חודשי לפי התקנות (טבלת לשכת רו"ח, ותרגיל)


def is_operational_car(business_use_only, leaves_workplace_after_hours, workplace_is_residence=False):
    """
    רכב תפעולי (תקנה 1 לתקנות ניכוי הוצאות רכב): תנאים מצטברים, לפי תרגילי לשכת רו"ח:
    משמש לצורכי העסק בלבד, מקום העיסוק אינו בית המגורים, ובתום שעות העבודה אינו יוצא ממקום העיסוק.
    כל תשובה חסרה (None) נחשבת כאי-עמידה בתנאי: ברירת המחדל היא לזקוף שווי.
    """
    return (business_use_only is True and leaves_workplace_after_hours is False
            and workplace_is_residence is False)


# תקרת מחיר מתואם והפחתות לפי שנה. 2026: לוח עזר 2026 של רשות המסים, פרק ד (תקרה 596,860; הפחתות 580/1,150/1,380, הוראת שעה עד 31.12.2028).
# 2025: תקרה 583,100 והפחתה לחשמלי 1,350 לפי מסמך מרכז המחקר והמידע של הכנסת המצטט את רשות המסים; הפחתות היברידי (560) ופלאג-אין (1,130)
# נגזרו מטבלת הלשכה ולא אומתו מול מקור ראשוני.
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
    if gross_weight_kg is not None and D(str(gross_weight_kg)) > CAR_MAX_WEIGHT_KG:
        return item(D(0), BY_LAW, "משקל כולל מותר מעל 3,500 ק\"ג: אינו 'רכב' לעניין התקנות, אין שווי (תרגיל לשכת רו\"ח)")
    if operational:
        return item(D(0), BY_LAW, "רכב תפעולי: אין שווי שימוש (תקנות מס הכנסה, ניכוי הוצאות רכב)")
    raw = min(D(str(price)), cap) * CAR_RATE
    value = (raw / 10).quantize(D("1"), rounding=ROUND_HALF_UP) * 10 - reductions[kind]
    src = "לוח עזר 2026 של רשות המסים" if year is not None and int(year) == 2026 else "טבלת 2025"
    return item(max(value, D(0)), BY_LAW,
                f"מודל ליניארי 2.48%, {src}, תקרת מחיר {cap}; רכב שנרשם לפני 2010 וניכוי השתתפות עובד לא נתמכים")


def works_committee_benefit(employer_amount_per_employee, specific_per_employee):
    """
    השתתפות המעסיק בפעילות ועד עובדים (יום כיף, טיול, מסיבה). כשהיא נקבעה בגין כל עובד ספציפית
    (למשל 340 לכל משתתף בפועל) היא הכנסת עבודה חייבת בסכום השתתפות המעסיק, גם אם שולמה לוועד
    (תרגיל לשכת רו"ח; חוזר מס הכנסה 34/93). מה שעובד שילם בעצמו אינו חלק מהזקיפה.
    כשההשתתפות כללית (לא לפי עובד) הכלל לא נבדק ולכן לא מחושב.
    """
    amount = D(str(employer_amount_per_employee))
    if specific_per_employee is True:
        return item(r2(amount), BY_LAW, "השתתפות מעסיק לפי עובד: הכנסת עבודה חייבת")
    if specific_per_employee is False:
        return item(D(0), BY_LAW, "השתתפות כוללת באירוע, לא ניתנת לייחוס לעובד: אין זקיפה (תרגילי לשכת רו\"ח)")
    return item(None, MANUAL, "לא ידוע אם ההשתתפות נקבעה לפי עובד: יש להכריע ידנית")


def team_building_benefit(employer_initiated, workday, full_pay, spouses_allowed, in_israel,
                          schedule_by_employer, professional_purpose, per_employee_amount=False):
    """
    פעילות גיבוש: אין זקיפה כשכל התנאים מתקיימים (יוזמת מעסיק, יום עבודה, שכר מלא, בלי בני זוג,
    בישראל, לו"ז של המעסיק, תוכן מקצועי, ובלי סכום נפרד לעובד). נגזר מתרגיל לשכת רו"ח, לא נבדק מול הנחיית רשות המסים.
    אם תנאי חסר או לא ידוע: לא מחשבים, הכרעה ידנית.
    """
    conds = [employer_initiated, workday, full_pay, not spouses_allowed if spouses_allowed is not None else None,
             in_israel, schedule_by_employer, professional_purpose,
             not per_employee_amount if per_employee_amount is not None else None]
    if all(c is True for c in conds):
        return item(D(0), BY_LAW, "כל תנאי הגיבוש מתקיימים: טובת המעסיק גוברת, אין זקיפה")
    return item(None, MANUAL, "תנאי גיבוש חסר או לא ידוע: יש להכריע ידנית")


def phone_benefit(monthly_expense, employee_share_rate="0", employee_share_amount="0"):
    """
    שווי רט"ן = הנמוך מבין חצי ההוצאה החודשית ל-115 ש"ח, פחות מה שהעובד משלם
    (באחוז מההוצאה המלאה ו/או בסכום קבוע). נבדק מול 3 תרגילי לשכת רו"ח (23,788 / 22,567 / 26,365).
    """
    exp = D(str(monthly_expense))
    base = min(exp / 2, PHONE_DEFAULT_VALUE)
    paid = exp * D(str(employee_share_rate)) + D(str(employee_share_amount))
    return item(max(r2(base - paid), D(0)), BY_LAW, "הנמוך מ-50% מההוצאה ו-115, פחות השתתפות העובד")


# ---------------------------------------------------------------------------
# דמי הבראה 2025 (תרגיל לשכת רו"ח: 418 ₪ ליום, הפחתה של יום אחד, מחצית ליום לשכר נמוך)
# ---------------------------------------------------------------------------
RECUPERATION_DAY_2025 = D("418")
RECUPERATION_LOW_SALARY_2025 = D("6150")


# ימי הבראה לפי שנת ותק (מגזר פרטי). שנים 1-4, 11, 16 ו-21 נבדקו מול תרגילים (5, 6, 6, 7, 8, 9, 10); השאר מהצו, לא נבדקו מול תרגיל.
def recuperation_days(seniority_year):
    y = int(seniority_year)
    if y < 1:
        return item(None, MANUAL, "שנת ותק לא תקינה")
    if y == 1:
        return item(D(5), BY_LAW, "שנה 1: 5 ימים (תרגיל)")
    if y in (2, 3):
        return item(D(6), BY_LAW, f"שנה {y}: 6 ימים (תרגיל)")
    if 4 <= y <= 10:
        return item(D(7), BY_LAW, "שנים 4-10: 7 ימים (תרגיל: נבדקה שנה 4, הטווח מהסבר הפתרון)")
    if 11 <= y <= 15:
        return item(D(8), BY_LAW, "שנים 11-15: 8 ימים (תרגיל: נבדקה שנה 11, הטווח מהסבר הפתרון)")
    if 16 <= y <= 19:
        return item(D(9), BY_LAW, "שנים 16-19: 9 ימים (תרגיל: נבדקה שנה 16, הטווח מהסבר הפתרון)")
    return item(D(10), BY_LAW, "משנה 20 ואילך: 10 ימים (תרגיל: נבדקה שנה 21, הטווח מהסבר הפתרון)")


def recuperation_pay(year, entitled_days, job_fraction="1", period_fraction="1", reduced_partial=None):
    """
    דמי הבראה לתשלום = ימים x 418 x חלקיות משרה x חלקיות תקופה, פחות הפחתה:
    יום הבראה אחד (או חצי יום לעובד בהפחתה חלקית: שכר חודשי ממוצע עד 6,150), באותן חלקיות.
    reduced_partial חייב להיקבע במפורש (True/False); None = הכרעה ידנית, כי ההתאמה
    של סף השכר למשרה חלקית לא אומתה. נבדק מול תרגיל אחד (רנה, 5 ימים, משרה מלאה = 1,672).
    רק 2025: שנים אחרות לא מחושבות. החישוב כאן ברוטו; הטיפול במס/ב"ל לא נבדק.
    """
    if year != 2025:
        return item(None, MANUAL, "תעריף וכללי הפחתה מוגדרים רק ל-2025")
    if reduced_partial is None:
        return item(None, MANUAL, "יש להכריע אם העובד בהפחתה חלקית (שכר חודשי ממוצע עד 6,150, בהתאמה למשרה)")
    frac = D(str(job_fraction)) * D(str(period_fraction))
    gross = D(str(entitled_days)) * RECUPERATION_DAY_2025 * frac
    cut = RECUPERATION_DAY_2025 * (D("0.5") if reduced_partial else D(1)) * frac
    return item(r2(max(gross - cut, D(0))), MANUAL, "מקור משני בלבד (כל זכות); ימים x 418 x חלקיות, פחות הפחתת 2025")


# ---------------------------------------------------------------------------
# רצפות הפקדה לפנסיית חובה (צו ההרחבה לפנסיית חובה, נחתם 26.5.2016; מינימום מ-1.1.2017): עובד 6%, מעסיק 6.5%, פיצויים 6%.
# מקור: רשות שוק ההון (gov.il, דוח 2016) ומרכז המחקר של הכנסת המתארים את הצו (י"פ 7287, 23.5.2016): מעסיק 6.5% תגמולים + 6% פיצויים מ-1.1.2017, עובד 6%; נוסח הצו עצמו טרם נקרא. הבסיס ("השכר הקובע") לא הוגדר כאן -> ידני.
PENSION_FLOOR = {"employee": D("0.06"), "employer": D("0.065"), "severance": D("0.06")}


def pension_floor_check(employee_rate, employer_rate, severance_rate):
    """בודק שהשיעורים שהוגדרו לא נמוכים מרצפת הצו. מחזיר רשימת הפרות (ריקה = תקין). לא משנה חישוב."""
    got = {"employee": D(str(employee_rate)), "employer": D(str(employer_rate)), "severance": D(str(severance_rate))}
    return [k for k, floor in PENSION_FLOOR.items() if got[k] < floor]


# פנסיה וקרן השתלמות: כפל שיעור שהוגדר בבסיס (נבדק מול מירב 2019 וסיינל 2023)
# ---------------------------------------------------------------------------
def deposit(base, rate):
    return item(r2(D(str(base)) * D(str(rate))), VERIFIED, "בסיס x שיעור שהוגדר")


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
    return {"year": year, "month": month, "gross": r2(gross), "items": items,
            "employer": employer, "pension_base": r2(base),
            "net": net, "overall_status": overall, "unresolved": unresolved,
            "cumulative": cum}
