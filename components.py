"""
רכיבי שכר קבועים לעובד (רשימה סגורה). נוצר 25.11.2026, ענף dev-components.

עקרונות:
1. הרשימה סגורה: קוד מחוץ לרשימה נדחה (ValueError). לא ממציאים רכיב.
2. סיווג לפיצויים: לפי labor_rules.SEVERANCE_* (תקנה 1 לתקנות פיצויי פיטורים). רכיב שלא נלמד -> ידני.
3. בסיס פנסיה: צו הרחבה לפנסיית חובה (2011) לא נקרא במלואו (הגדרת "שכר", סעיף 2). לכן הכללת רכיב בבסיס הפנסיה היא בחירה של רואת החשבון
   לעובד (pension_base_codes), בסטטוס "עפ"י רואת חשבון". שכר יסוד נכלל תמיד. רכיב שלא נבחר: לא נכלל.
4. חיוב במס: כל רכיב כסף הוא הכנסת עבודה (הכלל), חוץ מנסיעות: החלק הפטור (עד התקרה) תלוי בכללי רשות המסים שלא נקראו - ידני.
5. נסיעות: תקרה 22.60 ליום עבודה (labor_rules.travel_reimbursement_cap, י"פ 7319). הסכום מעל התקרה מסומן.
"""
from decimal import Decimal as D

import labor_rules as L

# קוד -> (שם בתלוש, סוג לפיצויים, האם כמות x מחיר)
CATALOG = {
    "001": ("משכורת", "base", False),
    "004": ("נסיעות", "travel_reimbursement", True),
    "007": ("שעות נוספות 125%", "overtime_pay", True),
    "008": ("שעות נוספות 150%", "overtime_pay", True),
    "010": ("בונוס", "one_time_bonus", False),
    "011": ("פרמיה קבועה", "fixed_premium", False),
    "012": ("תוספת ותק/יוקר/משפחה", "fixed_supplement", False),
    "020": ("החזר טלפון", "phone_reimbursement", False),
}
BASE_CODE = "001"
# קודים שמחושבים בשדות הקיימים (משכורת, שעות נוספות, בונוס) ולא מוזנים כרכיב נוסף, כדי למנוע ספירה כפולה
HANDLED_ELSEWHERE = ("001", "007", "008", "010")


def _q(x, name):
    try:
        v = D(str(x))
    except Exception:
        raise ValueError(f"{name}: ערך לא תקין")
    if v < 0:
        raise ValueError(f"{name}: ערך שלילי")
    return v


def build_lines(fixed, month, pension_base_codes=()):
    """
    fixed: רשימת {"code", "amount" או "rate"} (הגדרה קבועה לעובד). month: {"code": כמות} לחריגי החודש (ימים/שעות/סכום).
    מחזיר {"lines", "gross", "pension_base", "severance_components", "open"}. open = רשימת הערות שדורשות טיפול ידני.
    """
    lines, open_, sev, pension = [], [], [], D(0)
    seen = set()
    for f in fixed:
        code = str(f["code"])
        if code not in CATALOG:
            raise ValueError(f"קוד רכיב לא ברשימה: {code}")
        if code in seen:
            raise ValueError(f"קוד רכיב כפול: {code}")
        seen.add(code)
        name, sev_kind, by_qty = CATALOG[code]
        if by_qty:
            qty = _q(month.get(code, f.get("qty", 0)), name)
            rate = _q(f.get("rate", 0), name)
            amount = (qty * rate).quantize(D("0.01"))
        else:
            qty, rate = D(1), None
            amount = _q(month.get(code, f.get("amount", 0)), name).quantize(D("0.01"))
        note = None
        if code == "004":
            cap = L.travel_reimbursement_cap(int(qty))
            if cap["value"] is not None and amount > cap["value"]:
                note = f"סכום נסיעות {amount} מעל התקרה {cap['value']} ({qty} ימים x 22.60)"
                open_.append(note)
            open_.append("נסיעות: החלק הפטור ממס לא נקבע במערכת (כללי רשות המסים לא נקראו) - ידני")
        lines.append({"code": code, "name": name, "qty": qty, "rate": rate, "amount": amount, "note": note})
        sev.append((sev_kind, amount))
        if code == BASE_CODE or code in pension_base_codes:
            pension += amount
    gross = sum((l["amount"] for l in lines), D(0))
    for c in pension_base_codes:
        if c not in CATALOG:
            raise ValueError(f"קוד רכיב לא ברשימה: {c}")
    sev_wage = L.severance_wage(sev)
    return {"lines": lines, "gross": gross, "pension_base": pension,
            "pension_base_status": 'עפ"י רואת חשבון' if pension_base_codes else "שכר יסוד בלבד",
            "severance_wage": sev_wage, "open": open_}


def extras_for_paystub(extra, month, pension_base_codes=()):
    """
    רכיבים נוספים לתלוש (מעבר למשכורת, שעות נוספות ובונוס שמחושבים בשדות הקיימים).
    מחזיר (סכום ברוטו נוסף, החלק לבסיס פנסיה, שורות, הערות פתוחות). בלי רכיבים: (0, 0, [], []).
    """
    if not extra:
        return D(0), D(0), [], []
    bad = [str(c.get("code")) for c in extra if str(c.get("code")) in HANDLED_ELSEWHERE]
    if bad:
        raise ValueError("רכיב " + ", ".join(bad) + " מחושב משדות המשכורת, השעות הנוספות והבונוס ולא כרכיב נוסף")
    r = build_lines(extra, month, pension_base_codes)
    return r["gross"], r["pension_base"], r["lines"], r["open"]
