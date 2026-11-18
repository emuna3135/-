"""סיכום העברות לתשלום לפי חודש (פונקציות טהורות, נבדקות בלי FastAPI).

המערכת לא משלמת ולא מדווחת: היא מסכמת מהתלושים השמורים כמה יש להעביר, והחשב מעביר בעצמו.
מקור היחיד למועד: אתר ביטוח לאומי, עמוד "דיווח ותשלום עבור עובדים": הדיווח והתשלום חלים ב-15 בכל חודש בעבור החודש שקדם לו.
מועד תשלום מס הכנסה, פנסיה והשתלמות: לא נמצא מקור ראשוני, ולכן deadline=None ו-status="manual". לא מנחשים.
"""
from datetime import date

BTL_DEADLINE_SOURCE = "https://www.btl.gov.il/Insurance/Maasik/MToshavYisrael/DivuahVetashlum/Pages/Divuhach.aspx"


def _n(v):
    return float(v) if v is not None else 0.0


def _val(x):
    return x.get("value") if isinstance(x, dict) else x


def btl_deadline(year: int, month: int) -> str:
    """15 בחודש שלאחר חודש השכר. מה קורה כשהמועד חל ביום שאינו יום עסקים: אין מקור -> לא מחושב."""
    y, m = (year + 1, 1) if month == 12 else (year, month + 1)
    return date(y, m, 15).isoformat()


def summarize(year: int, stubs: list[dict]) -> list[dict]:
    """stubs: תלושים שמורים (בסדר יצירה; מאוחר באותו חודש/עובד דורס). מחזיר שורה לכל חודש."""
    latest: dict[tuple, dict] = {}
    for s in stubs:
        if s.get("year") != year or not s.get("month"):
            continue
        latest[(int(s["month"]), str(s.get("emp_id_number")))] = s
    months: dict[int, dict] = {}
    for (m, _), s in sorted(latest.items()):
        r = months.setdefault(m, {"month": m, "employees": 0, "income_tax": 0.0, "ni_employee": 0.0,
                                  "health_employee": 0.0, "ni_employer": 0.0, "ni_employer_missing": 0,
                                  "pension_employer": 0.0, "severance_employer": 0.0,
                                  "study_fund_employer": 0.0})
        emp = s.get("employer") or {}
        r["employees"] += 1
        r["income_tax"] += _n(s.get("income_tax"))
        r["ni_employee"] += _n(s.get("national_insurance"))
        r["health_employee"] += _n(s.get("health"))
        ne = _val(emp.get("national_insurance"))
        if ne is None:
            r["ni_employer_missing"] += 1
        else:
            r["ni_employer"] += _n(ne)
        for k in ("pension", "severance", "study_fund"):
            r[k + "_employer"] += _n(_val(emp.get(k)))
    out = []
    for m in sorted(months):
        r = months[m]
        r = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}
        r["btl_total"] = round(r["ni_employee"] + r["health_employee"] + r["ni_employer"], 2)
        r["btl_deadline"] = btl_deadline(year, m)
        r["btl_deadline_source"] = BTL_DEADLINE_SOURCE
        r["income_tax_deadline"] = None
        r["pension_deadline"] = None
        r["status"] = "manual" if r["ni_employer_missing"] else "partial"
        r["notes"] = ["מועד תשלום מס הכנסה: נדרש טיפול ידני (אין מקור במערכת)",
                      "מועד הפקדה לפנסיה/השתלמות: נדרש טיפול ידני (אין מקור במערכת)",
                      "מועד ב\"ל: אם ה-15 חל ביום שאינו יום עסקים – לבדוק ידנית (אין מקור במערכת)"]
        if r["ni_employer_missing"]:
            r["notes"].append(f"ב\"ל מעסיק חסר ב-{r['ni_employer_missing']} תלושים: הסכום חלקי")
        out.append(r)
    return out
