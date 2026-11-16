"""
חישוב זכויות סיום העסקה (שכיר במשכורת). ספרייה טהורה: אין גישה למסד נתונים.
עיקרון: כל רכיב נשען על פונקציה קיימת ב-labor_rules (ומקורה הרשום שם) או מוזן ידנית על ידי חשב השכר.
מה שלא ידוע מחזיר MANUAL ולא מנחש. המס על רכיבי הסיום (פטור/פריסה, טופס 161) אינו מחושב כאן.
"""
import datetime
from decimal import Decimal

import labor_rules as lr
from engine import BY_LAW, MANUAL, item, r2

D = Decimal


def full_months_of_service(start, end):
    """חודשים מלאים בין תחילת העבודה לסיומה (כולל יום הסיום). end לפני start -> ValueError."""
    if end < start:
        raise ValueError("תאריך סיום לפני תאריך תחילה")
    last = end + datetime.timedelta(days=1)
    months = (last.year - start.year) * 12 + (last.month - start.month)
    if last.day < start.day:
        months -= 1
    return months


def settlement(*, start_date, end_date, ended_by, severance_components, section14=False,
               unused_vacation_days=None, vacation_day_value=None,
               notice_days_unworked=None, notice_day_value=None, pay_type="monthly",
               min_wage_monthly=None, job_scope=None, quarter_wage=None):
    """
    ended_by: "dismissed" | "resigned".
    section14: האם יש הסדר סעיף 14 (תשלומי המעסיק לקרן במקום פיצויים). אם כן הפיצויים משולמים מהקרן, והמעסיק חב רק
      בהשלמה אם ההפרשות נמוכות מהשכר הקובע; חישוב ההשלמה אינו ממומש -> ידני.
    unused_vacation_days / vacation_day_value: חשב השכר מזין (שווי יום חופשה לא הוכרע במערכת).
    notice_days_unworked / notice_day_value: ימי הודעה מוקדמת שלא ניתנו בפועל והשווי היומי (מוזנים).
    quarter_wage: לעובד בשכר - שכר רבע השנה לפני סיום (או רבע העבודה המלאה ביותר ב-12 חודשים לפי בחירת העובד) לחישוב שווי יום חופשה.
    min_wage_monthly / job_scope: רצפת שכר מינימום לפי היקף משרה (§13ב לחוק פיצויי פיטורים); חסרים -> הפיצויים ידניים.
    מחזיר {"months": int, "items": {...}, "overall": סטטוס, "notes": [...]}
    """
    if ended_by not in ("dismissed", "resigned"):
        raise ValueError("ended_by חייב להיות dismissed או resigned")
    months = full_months_of_service(start_date, end_date)
    items, notes = {}, []

    wage = lr.severance_wage(severance_components)
    items["severance_wage"] = wage
    if ended_by == "resigned":
        items["severance"] = item(None, MANUAL, "התפטרות: זכאות לפיצויים רק בחריגים (§6-§11); לא מחושב אוטומטית")
    elif section14:
        items["severance"] = item(None, MANUAL, "הסדר סעיף 14: הפיצויים משולמים מהקרן; השלמת מעסיק לא ממומשת")
    elif wage["value"] is None:
        items["severance"] = item(None, MANUAL, "השכר הקובע לא הוכרע: " + wage["note"])
    else:
        items["severance"] = lr.severance_pay(wage["value"], months, pay_type, min_wage_monthly, job_scope)

    if vacation_day_value is None and quarter_wage is not None and pay_type != "monthly":
        dv = lr.vacation_day_value_wage_worker(quarter_wage)   # §10(ב)(2): שכר רבעון / 90
        vacation_day_value = dv["value"]
        notes.append("שווי יום חופשה נגזר משכר רבע השנה (§10(ב)(2) לחוק חופשה שנתית)")
        if unused_vacation_days is not None:
            items["vacation_redemption"] = item(r2(D(str(unused_vacation_days)) * D(str(vacation_day_value))), dv["status"],
                                                "פדיון = ימים x (שכר רבע שנה / 90), §10(ב)(2), §13")
    if "vacation_redemption" in items:
        pass
    elif unused_vacation_days is None or vacation_day_value is None:
        items["vacation_redemption"] = item(None, MANUAL, "יש להזין ימי חופשה שלא נוצלו ושווי יום (§13 לחוק חופשה שנתית)")
    else:
        items["vacation_redemption"] = item(r2(D(str(unused_vacation_days)) * D(str(vacation_day_value))),
                                            MANUAL, "ימים x שווי יום שהוזן; שווי היום לא נבדק מול הנוסח")

    if notice_days_unworked is None or notice_day_value is None:
        items["notice_pay"] = item(None, MANUAL, "יש להזין ימי הודעה מוקדמת שלא ניתנו והשווי היומי")
    else:
        due = lr.advance_notice_days_resignation(months, pay_type)
        note = "ימים x שווי יום שהוזן"
        if due["value"] is not None and D(str(notice_days_unworked)) > due["value"]:
            items["notice_pay"] = item(None, MANUAL,
                                       f"ימי ההודעה שהוזנו ({notice_days_unworked}) מעל הטבלה ({due['value']}); לבדוק")
        else:
            items["notice_pay"] = item(r2(D(str(notice_days_unworked)) * D(str(notice_day_value))), MANUAL,
                                       note + f"; לפי הטבלה בחוק עד {due['value']} ימים (טבלת התפטרות)")
        if ended_by == "dismissed":
            notes.append("טבלת ההודעה המוקדמת אומתה לנוסח ההתפטרות; זהותה לפיטורים לא נבדקה")

    notes.append("מס הכנסה, ביטוח לאומי ופטור/פריסה על רכיבי הסיום (טופס 161) לא מחושבים כאן")
    statuses = {v["status"] for v in items.values()}
    overall = MANUAL if MANUAL in statuses else BY_LAW
    return {"months": months, "items": items, "overall": overall, "notes": notes}
