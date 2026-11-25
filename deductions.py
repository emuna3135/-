"""
ניכויים קבועים והלוואות עם תאריך סיום. נוצר 25.11.2026, ענף dev-components.

עקרונות:
1. סכומים ב-Decimal, עיגול לאגורה. התשלום האחרון = מה שנשאר ביתרה (לא יותר מהיתרה).
2. תקופה: start/end בפורמט YYYY-MM (כולל). ללא end: עד סיום היתרה (אם יש total) אחרת ללא הגבלה.
3. יתרה: total (סכום ההלוואה) פחות paid_before (מה ששולם לפני חודש ההתחלה במערכת). אין total = ניכוי ללא יתרה.
4. הלוואה מהמעסיק: שווי הטבת ריבית (הכנסה חייבת לפי סעיף 3(ט) לפקודה) אינו מחושב כאן -> "נדרש טיפול ידני".
5. עיקול/מזונות: סכום נקבע ע"י הגוף המוסמך ולא נגזר כאן; נשמר כניכוי מוזן + הערה ידנית.
6. מגבלת חוק הגנת השכר §25: נבדקת ב-main_api על סך כל ניכויי הרשות (דגל בלבד).
"""
from decimal import Decimal as D, ROUND_HALF_UP

KINDS = {
    "loan": "הלוואה מהמעסיק",
    "advance": "מקדמה",
    "garnishment": "עיקול/הוצאה לפועל",
    "other": "ניכוי אחר",
}
Q = D("0.01")


def _d(x, name):
    try:
        v = D(str(x))
    except Exception:
        raise ValueError(f"{name}: ערך לא תקין")
    if v < 0:
        raise ValueError(f"{name}: ערך שלילי")
    return v


def _ym(s, name):
    try:
        y, m = str(s).split("-")
        y, m = int(y), int(m)
    except Exception:
        raise ValueError(f"{name}: פורמט YYYY-MM נדרש")
    if not (1 <= m <= 12 and 2000 <= y <= 2100):
        raise ValueError(f"{name}: חודש/שנה לא תקינים")
    return y * 12 + (m - 1)


def months_between(start_ym, year, month):
    """מספר החודשים מ-start (כולל) עד החודש הנוכחי (לא כולל). 0 = החודש הראשון."""
    return (year * 12 + month - 1) - _ym(start_ym, "start")


def _paid_before(item, k):
    """סכום ששולם בתשלומים הרגילים לפני החודש הנוכחי (k = מספר חודשים מההתחלה), בנוסף ל-paid_before."""
    monthly = _d(item["monthly"], "monthly")
    total = item.get("total")
    paid = _d(item.get("paid_before", 0), "paid_before")
    if total is None:
        return paid
    return min(paid + monthly * k, _d(total, "total"))


def month_deductions(items, year, month):
    """
    מחזיר dict: amount (סכום הניכוי החודש), lines, open (הערות ידניות), balances (יתרות אחרי החודש).
    items: [{code, kind, monthly, start, end?, total?, paid_before?}]
    """
    amount = D(0)
    lines, open_, balances = [], [], []
    seen = set()
    for it in items or []:
        code = str(it.get("code") or "").strip()
        if not code:
            raise ValueError("ניכוי קבוע חייב קוד")
        if code in seen:
            raise ValueError(f"קוד ניכוי כפול: {code}")
        seen.add(code)
        kind = it.get("kind")
        if kind not in KINDS:
            raise ValueError(f"סוג ניכוי לא מוכר: {kind}")
        monthly = _d(it.get("monthly", 0), "monthly")
        if monthly == 0:
            raise ValueError(f"{code}: סכום חודשי חייב להיות גדול מאפס")
        cur = year * 12 + month - 1
        start = _ym(it["start"], "start")
        end = _ym(it["end"], "end") if it.get("end") else None
        if end is not None and end < start:
            raise ValueError(f"{code}: תאריך סיום לפני ההתחלה")
        if cur < start or (end is not None and cur > end):
            continue
        k = cur - start
        total = _d(it["total"], "total") if it.get("total") is not None else None
        paid = _paid_before(it, k)
        due = monthly
        if total is not None:
            remaining = total - paid
            if remaining <= 0:
                continue
            due = min(monthly, remaining)
        due = due.quantize(Q, ROUND_HALF_UP)
        amount += due
        label = it.get("label") or KINDS[kind]
        lines.append({"code": code, "label": label, "kind": kind, "amount": due})
        if total is not None:
            balances.append({"code": code, "label": label,
                             "remaining_after": (total - paid - due).quantize(Q, ROUND_HALF_UP)})
        if kind == "loan":
            open_.append(f"{label}: שווי הטבת ריבית על הלוואה מהמעסיק (סעיף 3(ט) לפקודה) לא מחושב - נדרש טיפול ידני")
        if kind == "garnishment":
            open_.append(f"{label}: סכום העיקול נקבע ע\"י הגוף המוסמך - נדרש אימות ידני מול ההודעה")
    return {"amount": amount.quantize(Q, ROUND_HALF_UP), "lines": lines, "open": open_, "balances": balances}
