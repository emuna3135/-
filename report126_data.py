"""איסוף נתוני דוח 126 מנתוני המערכת (פונקציות טהורות, נבדקות בלי FastAPI).

הקלט הוא מילונים רגילים (אחרי פענוח): עובדים, טפסי 101 לשנה, ותלושים שמורים.
הפלט מתאים ל-form126_build.build. שדה בלי מקור נשאר חסר (None) ולכן הבנייה מסמנת אותו כחוסם; לא ממציאים ערך.
"""
import form126
import form126_build


def _num(v):
    return float(v) if v is not None else 0.0


def collect_employees(year: int, employees: list[dict], form101_by_id: dict, stubs: list[dict]) -> list[dict]:
    """employees: מטענים של Employee; form101_by_id: {id_number: מטען 101 לשנה}; stubs: תלושים שמורים (בסדר יצירה)."""
    months: dict[str, dict[int, dict]] = {}
    for s in stubs:                                  # תלוש מאוחר באותו חודש דורס קודם (חישוב חוזר)
        if s.get("year") != year or not s.get("month"):
            continue
        months.setdefault(str(s["emp_id_number"]), {})[int(s["month"])] = {
            "gross": _num(s.get("gross")), "tax": _num(s.get("income_tax")),
            "ni": _num(s.get("national_insurance")), "health": _num(s.get("health"))}
    out = []
    for e in employees:
        idn = str(e["id_number"])
        f = form101_by_id.get(idn) or {}
        out.append({
            "id_number": idn.zfill(9),
            "family_name": e.get("family_name"), "first_name": e.get("first_name"),
            "street": e.get("street"), "city": e.get("city"), "zip": e.get("zip"),
            "gender": e.get("gender"), "birth_date": e.get("birth_date"), "start_date": e.get("start_date"),
            "marital": f.get("marital"),
            "income_type": f.get("income_type") if f else None,
            "form101": 1 if (f and f.get("signed_on")) else 3,
            "months": months.get(idn, {}),
        })
    return out


def company_dict(profile: dict) -> dict:
    return {k: profile.get(k) for k in ("file_no", "agid", "factory_no", "legal_status",
                                        "tax_file_no", "name", "phone", "employer_tax")}


def mask_id(text: str) -> str:
    """בתשובות בדיקה מציגים רק 4 ספרות אחרונות של ת"ז."""
    import re
    return re.sub(r"ת\"ז (\d{5})(\d{4})", r'ת"ז *****\2', text)


def run(profile: dict, year: int, employees: list[dict], form101_by_id: dict, stubs: list[dict], *,
        hebrew_visual: bool, encoding: str):
    """מחזיר (קובץ בייטים, issues בלי ת"ז מלאה, מספר רשומות, submittable)."""
    emps = collect_employees(year, employees, form101_by_id, stubs)
    lines, issues = form126_build.build(company_dict(profile), year, emps, hebrew_visual=hebrew_visual)
    data = form126.encode_file(lines, encoding)
    safe = [{**i, "scope": mask_id(i["scope"])} for i in issues]
    return data, safe, len(lines), form126_build.is_submittable(issues)
