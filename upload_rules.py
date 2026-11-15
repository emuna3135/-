"""כללי העלאת Excel: עמודה חובה שחסרה = שגיאת שורה, בלי ערך ברירת מחדל מנוחש."""

COLUMN_ALIASES = {
    "credit_points": ["credit_points", "נקודות זיכוי"],
    "pension_employee_rate": ["pension_employee_rate", "אחוז פנסיה עובד"],
    "tax_mode": ["tax_mode", "שיטת מס"],
}
LABELS = {"credit_points": "נקודות זיכוי", "pension_employee_rate": "אחוז פנסיה עובד",
          "tax_mode": "שיטת מס"}


def require(row: dict, key: str):
    """מחזיר את הערך מהשורה. חסר או ריק -> ValueError (לא ברירת מחדל)."""
    for alias in COLUMN_ALIASES[key]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    raise ValueError(f"חסר ערך בעמודה '{LABELS[key]}'. אין ברירת מחדל, יש להזין")


def required_for_row(row: dict):
    """(tax_mode, credit_points, pension_rate). נקודות זיכוי נדרשות רק בשיטת מצטבר."""
    mode = str(require(row, "tax_mode"))
    pension = float(require(row, "pension_employee_rate"))
    points = float(require(row, "credit_points")) if mode == "cumulative" else 0.0
    return mode, points, pension
