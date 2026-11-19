"""ייבוא עובדים וטופס 101 מאקסל. פונקציות טהורות (בלי FastAPI), נבדקות ב-test_employee_import.py.
כל ערך שלא מזוהה = שגיאת שורה; המערכת לא מנחשת ערך חסר. תעודת זהות נבדקת בנפרד (secure.valid_israeli_id) בשרת."""
import datetime
import io

SHEET_EMPLOYEES = "עובדים"
SHEET_FORM101 = "טופס 101"

_GENDER = {"f": "F", "m": "M", "נקבה": "F", "אישה": "F", "נ": "F", "זכר": "M", "גבר": "M", "ז": "M"}
_MARITAL = {"single": "single", "married": "married", "divorced": "divorced", "widowed": "widowed", "separated": "separated",
            "רווק": "single", "רווקה": "single", "רווק/ה": "single", "נשוי": "married", "נשואה": "married", "נשוי/אה": "married",
            "גרוש": "divorced", "גרושה": "divorced", "גרוש/ה": "divorced", "אלמן": "widowed", "אלמנה": "widowed",
            "אלמן/ה": "widowed", "פרוד": "separated", "פרודה": "separated", "פרוד/ה": "separated"}
_YES = ("כן", "yes", "true", "1", "y")
_NO = ("לא", "no", "false", "0", "n")

ALIASES = {
    "id_number": ("תעודת זהות", "ת.ז", "id_number"),
    "full_name": ("שם מלא", "שם עובד", "שם", "full_name"),
    "gender": ("מין", "gender"),
    "birth_date": ("תאריך לידה", "birth_date"),
    "start_date": ("תאריך תחילת עבודה", "תחילת עבודה", "start_date"),
    "is_resident": ("תושב", "is_resident"),
    "family_name": ("שם משפחה", "family_name"),
    "first_name": ("שם פרטי", "first_name"),
    "street": ("רחוב ומספר בית", "רחוב", "street"),
    "city": ("עיר", "ישוב", "city"),
    "zip": ("מיקוד", "zip"),
    "base_salary": ("שכר יסוד", "base_salary"),
    "pension_employee_rate": ("אחוז פנסיה עובד", "pension_employee_rate"),
    "employer_pension_rate": ("אחוז פנסיה מעסיק", "employer_pension_rate"),
    "employer_severance_rate": ("אחוז פיצויים מעסיק", "employer_severance_rate"),
    "position_scope_percent": ("היקף משרה %", "היקף משרה", "position_scope_percent"),
    "tax_year": ("שנת מס", "שנה", "tax_year"),
    "signed_on": ("תאריך חתימה", "signed_on"),
    "income_type": ("סוג הכנסה", "income_type"),
    "other_income": ("הכנסה אחרת", "other_income"),
    "other_income_credit": ("זיכוי כנגד הכנסה זו", "other_income_credit"),
    "marital": ("מצב משפחתי", "marital"),
    "custody": ("שנות לידה ילדים בחזקתו", "custody_birth_years"),
    "noncustody": ("שנות לידה ילדים שלא בחזקתו", "noncustody_birth_years"),
    "flags": ("מצבי חיים", "family_flags"),
}


class RowError(ValueError):
    pass


def _get(row, key):
    for a in ALIASES[key]:
        if a in row and row[a] not in (None, ""):
            return row[a]
    return None


def _need(row, key):
    v = _get(row, key)
    if v is None:
        raise RowError(f"חסר ערך בעמודה '{ALIASES[key][0]}'")
    return v


def _date(v, label):
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    try:
        return datetime.date.fromisoformat(str(v).strip()[:10]).isoformat()
    except ValueError:
        raise RowError(f"תאריך לא תקין בעמודה '{label}' (נדרש YYYY-MM-DD)")


def _num(v, label):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except ValueError:
        raise RowError(f"מספר לא תקין בעמודה '{label}'")


def _rate(v, label):
    """שיעור כשבר עשרוני (0.06). ערך מעל 1 נקרא כאחוזים (6 = 6%)."""
    x = _num(v, label)
    return x / 100 if x > 1 else x


def _yes_no(v, label):
    s = str(v).strip().lower()
    if s in _YES:
        return True
    if s in _NO:
        return False
    raise RowError(f"ערך לא מזוהה בעמודה '{label}' (כן/לא)")


def _years(v):
    if v is None:
        return []
    if isinstance(v, (int, float)):
        return [int(v)]
    out = []
    for part in str(v).replace(";", ",").split(","):
        part = part.strip()
        if part:
            if not part.isdigit() or not (1950 <= int(part) <= 2100):
                raise RowError("שנות לידה של ילדים: מספרים מופרדים בפסיק")
            out.append(int(part))
    return out


def parse_employee(row):
    """שורת עובד -> dict בפורמט EmployeeIn. חסר ערך חובה = RowError."""
    idn = str(_need(row, "id_number")).strip()
    g = str(_need(row, "gender")).strip().lower()
    if g not in _GENDER:
        raise RowError("מין לא מזוהה (F/M או נקבה/זכר)")
    res = _get(row, "is_resident")
    out = {
        "id_number": idn,
        "full_name": str(_need(row, "full_name")).strip(),
        "gender": _GENDER[g],
        "birth_date": _date(_get(row, "birth_date"), "תאריך לידה"),
        "start_date": _date(_get(row, "start_date"), "תאריך תחילת עבודה"),
        "is_resident": True if res is None else _yes_no(res, "תושב"),
        "base_salary": _num(_need(row, "base_salary"), "שכר יסוד"),
        "pension_employee_rate": _rate(_need(row, "pension_employee_rate"), "אחוז פנסיה עובד"),
    }
    for key, label in (("employer_pension_rate", "אחוז פנסיה מעסיק"), ("employer_severance_rate", "אחוז פיצויים מעסיק")):
        v = _get(row, key)
        if v is not None:
            out[key] = _rate(v, label)
    # פרטי דיווח לרשויות (טופס 126): אופציונליים. ערך מוזן מועתק כמו שהוא, לא מפוצל ולא מנוחש
    for key in ("family_name", "first_name", "street", "city"):
        v = _get(row, key)
        if v is not None:
            out[key] = str(v).strip()
    z = _get(row, "zip")
    if z is not None:
        z = str(z).strip()
        if z.endswith(".0"):
            z = z[:-2]
        if not z.isdigit() or len(z) > 5:
            raise RowError("מיקוד: עד 5 ספרות")
        out["zip"] = z.zfill(5)
    scope = _get(row, "position_scope_percent")
    if scope is not None:
        out["position_scope_percent"] = _num(scope, "היקף משרה %")
    if out["base_salary"] <= 0:
        raise RowError("שכר יסוד חייב להיות חיובי")
    return out


_FLAGS = {"נער/ה 16-18": "teen", "נער 16-18": "teen", "teen": "teen",
          "יחיד מוטב": "benef", "benef": "benef", "נשואה לאלמן": "widower", "widower": "widower",
          "חי בנפרד ללא משק בית משותף": "nomesh", "nomesh": "nomesh",
          "חי בנפרד עם משק בית משותף": "yesmesh", "yesmesh": "yesmesh",
          "הורה יחיד": "niptar", "niptar": "niptar", "משלם מזונות": "mezonut", "mezonut": "mezonut"}


def _flags(v):
    """תא 'מצבי חיים': ערכים מופרדים בפסיק או נקודה-פסיק. ערך לא מזוהה = שגיאה (לא מנחשים)."""
    if v is None:
        return []
    out = []
    for part in str(v).replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        f = _FLAGS.get(part.lower() if part.isascii() else part)
        if f is None:
            raise RowError("מצב חיים לא מזוהה: " + part)
        if f not in out:
            out.append(f)
    return out


def parse_form101(row):
    """שורת טופס 101 -> (id_number, שנת מס, dict בפורמט Form101In)."""
    idn = str(_need(row, "id_number")).strip()
    year = int(_num(_get(row, "tax_year") if _get(row, "tax_year") is not None else _need(row, "tax_year"), "שנת מס"))
    income = str(_get(row, "income_type") or "main").strip().lower()
    income = {"משרה עיקרית": "main", "main": "main", "משרה נוספת": "additional", "additional": "additional"}.get(income)
    if income is None:
        raise RowError("סוג הכנסה לא מזוהה (משרה עיקרית / משרה נוספת)")
    other = _get(row, "other_income")
    credit = _get(row, "other_income_credit")
    credit_val = None
    if credit is not None:
        c = str(credit).strip().lower()
        credit_val = {"כאן": "here", "here": "here", "אצל מעסיק אחר": "elsewhere", "elsewhere": "elsewhere"}.get(c)
        if credit_val is None:
            raise RowError("זיכוי כנגד הכנסה זו: 'כאן' או 'אצל מעסיק אחר'")
    marital = _get(row, "marital")
    m = None
    if marital is not None:
        m = _MARITAL.get(str(marital).strip().lower())
        if m is None:
            raise RowError("מצב משפחתי לא מזוהה")
    return idn, year, {
        "signed_on": _date(_get(row, "signed_on"), "תאריך חתימה"),
        "income_type": income,
        "other_income": False if other is None else _yes_no(other, "הכנסה אחרת"),
        "other_income_credit": credit_val,
        "other_credits_claimed": False,
        "marital": m,
        "custody_birth_years": _years(_get(row, "custody")),
        "noncustody_birth_years": _years(_get(row, "noncustody")),
        "family_flags": _flags(_get(row, "flags")),
    }


def read_sheets(content: bytes):
    """כל הגיליונות של קובץ xlsx -> {שם גיליון: [dict לשורה לפי הכותרות]}."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            out[ws.title] = []
            continue
        head = [str(h).strip() if h is not None else "" for h in rows[0]]
        out[ws.title] = [dict(zip(head, r)) for r in rows[1:] if any(c not in (None, "") for c in r)]
    return out


# --- פרטי מעביד (גיליון 'מעביד'): שורה אחת. משמש לדוח השנתי (126). ללא ניחוש: ערך חסר/לא מזוהה = שגיאה. ---
SHEET_EMPLOYER = "מעביד"
_LEGAL = {"חברה": 1, "יחיד": 2, "עוסק": 2, "שותפות": 3, "עמותה": 4, "רשות": 5}
_EMP_TAX = {"פטור": 1, "חייב": 2}
EMPLOYER_ALIASES = {
    "name": ("שם המעביד", "שם מעביד", "name"),
    "file_no": ("תיק ניכויים", "מספר תיק ניכויים", "file_no"),
    "tax_file_no": ("מספר תיק במס הכנסה", "תיק במס הכנסה", "tax_file_no"),
    "phone": ("טלפון", "phone"),
    "legal_status": ("מעמד משפטי", "legal_status"),
    "employer_tax": ("מס מעסיקים", "employer_tax"),
    "agid": ("מספר אגיד", "אגיד", "agid"),
    "factory_no": ("מספר מפעל", "factory_no"),
}


def _eget(row, key):
    for a in EMPLOYER_ALIASES[key]:
        if a in row and row[a] not in (None, ""):
            return row[a]
    return None


def _digits(v):
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def parse_employer(row):
    """שורת 'מעביד' -> dict תואם ProfileIn. חובה: שם, תיק ניכויים, תיק במס הכנסה, טלפון, מעמד משפטי, מס מעסיקים."""
    out = {}
    for key, label in (("name", "שם המעביד"), ("file_no", "תיק ניכויים"), ("tax_file_no", "מספר תיק במס הכנסה"), ("phone", "טלפון")):
        v = _eget(row, key)
        if v is None:
            raise RowError(f"חסר ערך בעמודה '{label}'")
        out[key] = str(v).strip() if key == "name" else _digits(v).replace("-", "")
    for key, label, table in (("legal_status", "מעמד משפטי", _LEGAL), ("employer_tax", "מס מעסיקים", _EMP_TAX)):
        v = _eget(row, key)
        if v is None:
            raise RowError(f"חסר ערך בעמודה '{label}'")
        s = str(v).strip()
        code = table.get(s) or (int(s) if s.isdigit() and int(s) in table.values() else None)
        if code is None:
            raise RowError(f"ערך לא מוכר בעמודה '{label}': {s}. ערכים אפשריים: {', '.join(table)}")
        out[key] = code
    a = _eget(row, "agid")
    out["agid"] = int(_digits(a)) if a is not None and _digits(a).isdigit() else 0
    fa = _eget(row, "factory_no")
    out["factory_no"] = _digits(fa) if fa is not None else None
    return out
