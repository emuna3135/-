"""
תלושים מיוחדים (הבראה ועוד). נוצר 11.11.2026.
עיקרון: תשלום חריג (לא משכורת חודש) לא מקבל סטטוס מאומת בשורות המס והביטוח הלאומי עד שיש לו מקור ראשוני וחישוב מלא.
מקורות ראשוניים כאן:
  - תקנות מס הכנסה (ניכוי ממשכורת ומשכר עבודה) 1993: תקנה 3 + תוספת א' (משכורת חודש), תקנה 4 (משכורת בלתי קבועה).
"""
from decimal import Decimal as D

from engine import (BRACKETS, BY_LAW, CREDIT_POINT_2025, MANUAL, item, r0, r2,
                    recuperation_days, recuperation_pay, tax_before_credits)


def monthly_withholding(year, monthly_wage, points):
    """
    תוספת א' לתקנות הניכוי: משכורת x12; מס לפי 121/121ב; פחות נקודות זיכוי; /12; עיגול:
    שבר שקל מעל 49 אגורות נחשב שקל שלם (תוספת א' (5)) - גם למשכורת וגם למס.
    בלי זיכוי פנסיה/ביטוח חיים (לא בתוספת א' עצמה). לא יורד מ-0.
    """
    if year not in BRACKETS:
        return item(None, MANUAL, "שנת מס לא נתמכת")
    wage = D(r0(monthly_wage))
    annual_tax = tax_before_credits(wage * 12, 12, year)
    credit = D(str(points)) * CREDIT_POINT_2025 * 12
    tax = max(annual_tax - credit, D(0)) / 12
    return item(D(r0(tax)), BY_LAW, "תוספת א' (משכורת חודש): x12, מס, פחות נקודות זיכוי, /12, עיגול 49 אגורות")


def irregular_tax_reg4(year, regular_monthly, irregular, points):
    """
    תקנה 4(א): מס = (מס על משכורת החודש + חלק 1/12 מהמשכורת הבלתי קבועה, פחות מס על משכורת החודש) x 12.
    כל אחד מהמסים לפי תוספת א'. סטטוס BY_LAW: ישור הקו מול מצטבר (תלוש חינוך/רו"ח) לא נבדק.
    """
    reg = monthly_withholding(year, regular_monthly, points)
    with_p = monthly_withholding(year, D(str(regular_monthly)) + D(str(irregular)) / 12, points)
    if reg["value"] is None or with_p["value"] is None:
        return item(None, MANUAL, "שנת מס לא נתמכת")
    return item((with_p["value"] - reg["value"]) * 12, BY_LAW,
                "תקנה 4(א) לתקנות הניכוי: הפרש המס x12 (חלק 1/12 מהתשלום). לא נבדק מול תלוש; לא הוכרע אם תלוש מצטבר משתמש בו")


def recuperation_month(year, month, base_salary, seniority_year, reduced_partial,
                       job_fraction="1", period_fraction="1", points="2.75"):
    """
    חודש עם תשלום הבראה (מגזר פרטי, 2025). מחזיר את מרכיבי התלוש עם סטטוס לכל שורה וגם רשימת "פתוח".
    לא מייצר נטו מחייב: ב"ל, מס ובסיס פנסיוני עדיין לא סגורים לתשלום חריג.
    """
    days = recuperation_days(seniority_year)
    pay = recuperation_pay(year, days["value"], job_fraction, period_fraction, reduced_partial)
    out = {"days": days, "recuperation_gross": pay, "open": []}
    if pay["value"] is None:
        out["open"].append("סכום ההבראה לא חושב: " + pay["note"])
        return out
    base = D(str(base_salary))
    out["tax_reg4_on_recuperation"] = irregular_tax_reg4(year, base, pay["value"], points)
    out["tax_regular_month"] = monthly_withholding(year, base, points)
    out["open"] += [
        "מס: תקנה 4 (שורה למעלה) מול החישוב המצטבר של רו\"ח – לא הוכרע איזה חל על תשלום חריג בתלוש",
        "ב\"ל ובריאות: פריסה לפי תקנה 5 לתקנות ב\"ל (רף 25% משכר מינימום; 11 חודשים קודמים) – לא ממומש בתלוש; נדרשות משכורות קודמות",
        "בסיס פנסיוני: האם ההבראה נכללת (Q11) – לא הוכרע",
    ]
    return out
