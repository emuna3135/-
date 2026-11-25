"""
יתרות חופשה, מחלה והבראה לעובד. נוצר 25.11.2026, ענף dev-components.

עקרונות:
1. יתרה = פתיחה (מוזנת ע"י רואת החשבון) + צבירה/זכאות - ניצול. אין ניחוש של מה שלא נקבע במקור רשמי.
2. מחלה: צבירה יום וחצי לחודש עבודה מלא, תקרה 90 מצטבר (חוק דמי מחלה §4(א)). חודש חלקי: חלקיות מוזנת (§4(ב)).
3. חופשה: זכאות שנתית לפי labor_rules (קלנדרי בשבוע 6 ימים; ימי עבודה בשבוע 5 ימים רק בכפוף לכללים שם). העברת יתרה לשנה
   הבאה אינה מוגדרת כאן: היתרה הפותחת מוזנת ידנית ("עפ"י רואת חשבון").
4. הבראה: ימים לפי ותק (engine.recuperation_days); מימוש הכסף נעשה ב-engine.recuperation_pay.
5. יתרה שלילית (ניצול מעבר לזכאות) לא נחסמת; היא מסומנת לטיפול ידני.
"""
from decimal import Decimal as D

import engine as E
import labor_rules as L

SICK_PER_MONTH = D("1.5")
SICK_CAP = D(90)


def _d(x, name):
    try:
        v = D(str(x))
    except Exception:
        raise ValueError(f"{name}: ערך לא תקין")
    if v < 0:
        raise ValueError(f"{name}: ערך שלילי")
    return v


def sick_balance(opening=0, month_fractions=(), used=0):
    """month_fractions: חלקיות כל חודש עבודה בתקופה (1 = חודש מלא). הצבירה נעצרת בתקרה 90 (מצטבר)."""
    bal = _d(opening, "opening")
    if bal > SICK_CAP:
        raise ValueError("יתרת פתיחה מעל תקרת 90 ימים")
    accrued = D(0)
    for i, f in enumerate(month_fractions):
        f = _d(f, f"month_fractions[{i}]")
        if f > 1:
            raise ValueError("חלקיות חודש מעל 1")
        add = min(SICK_PER_MONTH * f, SICK_CAP - bal)
        bal += add
        accrued += add
    used = _d(used, "used")
    remaining = bal - used
    notes = ["יום וחצי לחודש עבודה מלא, עד 90 יום מצטבר (חוק דמי מחלה §4(א))"]
    if remaining < 0:
        notes.append("ניצול מעבר לצבירה: נדרש טיפול ידני")
    return {"status": L._status("sick_accrual"), "opening": D(str(opening)), "accrued": accrued,
            "used": used, "remaining": remaining, "notes": notes}


def vacation_balance(year_of_service, five_day_week=False, days_worked=None, continuous_year=True,
                     opening=0, used=0, as_of_year=2026):
    """זכאות שנתית + יתרה. days_worked: ימי עבודה בשנה (לחלקיות לפי §3(ב)/(ג)); None = שנה מלאה."""
    base = (L.annual_leave_net_days_five_day_week(year_of_service, as_of_year) if five_day_week
            else L.annual_leave_statutory_days(year_of_service))
    ent = base["value"]
    status = base["status"]
    notes = [base["note"]]
    if ent is not None and days_worked is not None:
        p = L.annual_leave_proportional(ent, _d(days_worked, "days_worked"), continuous_year)
        ent, status = p["value"], p["status"]
        notes.append(p["note"])
    if ent is None:
        return {"status": L.MANUAL, "entitlement": None, "opening": D(str(opening)), "used": D(str(used)),
                "remaining": None, "notes": notes + ["זכאות לא נקבעה ממקור רשמי: להזין ידנית"]}
    ent = D(str(ent))
    opening, used = _d(opening, "opening"), _d(used, "used")
    remaining = opening + ent - used
    notes.append("יתרה פותחת מוזנת ידנית (העברה בין שנים: עפ\"י רואת חשבון)")
    if remaining < 0:
        notes.append("ניצול מעבר לזכאות: נדרש טיפול ידני")
    return {"status": status, "entitlement": ent, "opening": opening, "used": used,
            "remaining": remaining, "notes": notes}


def recreation_balance(seniority_year, paid_days=0, job_fraction="1"):
    """ימי הבראה לפי ותק, פחות מה ששולם בשנת ההבראה. חלקיות משרה משפיעה על הסכום בכסף (recuperation_pay), לא על הימים."""
    r = E.recuperation_days(seniority_year)
    if r["value"] is None:
        return {"status": L.MANUAL, "entitled": None, "paid": D(str(paid_days)), "remaining": None, "notes": [r["note"]]}
    paid = _d(paid_days, "paid_days")
    rem = D(str(r["value"])) - paid
    notes = [r["note"]]
    if rem < 0:
        notes.append("שולם מעבר לזכאות: נדרש טיפול ידני")
    return {"status": r["status"], "entitled": D(str(r["value"])), "paid": paid, "remaining": rem, "notes": notes}
