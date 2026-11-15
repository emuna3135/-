"""
תיקון ידני של חשב השכר (אושר ע"י המשתמשת ב-12.11.2026).

כללים:
  - רק רכיבי ניכוי ברשימה לבנה. הברוטו, הנקודות והפרמטרים לא משתנים כאן.
  - חובה סיבה (טקסט לא ריק), שם המתקן וזמן. ערך חדש: מספר סופי, לא שלילי, עד אגורה.
  - כל תיקון נרשם ביומן res["overrides"]: ערך קודם, ערך חדש, סיבה, מי, מתי. אין מחיקה של תיקון קיים.
  - סטטוס הרכיב הופך ל"תוקן ידנית"; היומן פנימי בלבד; התלוש עצמו נקי מהערות.
  - נטו מחושב מחדש בקוד (נטו קודם + ערך קודם - ערך חדש), לא בראש.
  - לא נוגע ב-_cumulative; מס הכנסה מצטבר אחרי תיקון מס חייב טיפול ידני בחודש הבא (מסומן בהערה).
"""
import datetime
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

OVERRIDDEN = "תוקן ידנית על ידי חשב השכר"
ALLOWED = {"income_tax": "מס הכנסה", "national_insurance": "ביטוח לאומי", "health": "ביטוח בריאות",
           "pension_employee": "פנסיה - עובד", "study_fund_employee": "קרן השתלמות - עובד"}


class OverrideError(ValueError):
    pass


def _dec2(v):
    try:
        if isinstance(v, float) and not math.isfinite(v):
            raise OverrideError("ערך לא סופי")
        d = Decimal(str(v))
    except InvalidOperation:
        raise OverrideError("ערך לא מספרי")
    if not d.is_finite():
        raise OverrideError("ערך לא סופי")
    if d < 0:
        raise OverrideError("ערך שלילי לא מותר")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_override(res: dict, field: str, new_value, reason: str, user: str, when=None) -> dict:
    """מחזיר עותק של res עם התיקון. res לא משתנה. לא מתקן תלוש שאין לו נטו (רכיב חסר)."""
    if field not in ALLOWED:
        raise OverrideError(f"אפשר לתקן רק: {', '.join(ALLOWED.values())}")
    if not isinstance(reason, str) or not reason.strip():
        raise OverrideError("חובה לציין סיבה לתיקון")
    if not user:
        raise OverrideError("חסר שם המתקן")
    if res.get("net") is None:
        raise OverrideError("אי אפשר לתקן תלוש שאינו מחושב במלואו (יש רכיב חסר)")
    new = _dec2(new_value)
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in res.items()}
    out["items"] = {k: dict(v) for k, v in res["items"].items()}
    old_raw = out["items"][field]["value"]
    old = Decimal(str(old_raw)) if old_raw is not None else Decimal(0)
    when = when or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    it = out["items"][field]
    it["value"] = float(new)
    it["status"] = OVERRIDDEN
    it["note"] = (it.get("note", "") + f" | תוקן ידנית: {old} -> {new}").strip(" |")
    if field in out:                      # השדות העליונים שהתלוש קורא
        out[field] = float(new)
    out["net"] = float((Decimal(str(res["net"])) + old - new).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    out["overall_status"] = OVERRIDDEN
    flags = list(out.get("flags", []))
    if field == "income_tax":
        flags.append("מס הכנסה תוקן ידנית: המצטבר לחודש הבא לא עודכן, יש לבדוק אותו ידנית")
    out["flags"] = flags
    out["overrides"] = list(res.get("overrides", [])) + [
        {"field": field, "label": ALLOWED[field], "old": float(old), "new": float(new),
         "reason": reason.strip(), "by": user, "at": when}]
    return out
