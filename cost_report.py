"""
דוח עלות מעביד לפי עובד וחודש, מהתלושים השמורים. פונקציות טהורות. נוצר 26.11.2026, ענף dev-components.

עלות מעביד = ברוטו (כולל שווי הטבות במס) + ב"ל מעסיק + פנסיה מעסיק + פיצויים מעסיק + השתלמות מעסיק.
- זה דוח ניהולי פנימי ולא דוח רשמי: אין מקור חיצוני לתבנית, והוא רק מסכם נתונים שחושבו בתלוש.
- רכיב מעסיק חסר (None) לא נספר כאפס: השורה מסומנת "partial" והרכיב החסר מפורט.
- שווי הטבות (רכב/טלפון) כלול בברוטו שבתלוש: זו עלות חשבונאית של ההטבה לעובד, לא בהכרח הוצאה במזומן של המעביד (נדרש עיון רו"ח).
- סכומים ב-Decimal ועיגול לאגורה.
"""
from decimal import Decimal as D, ROUND_HALF_UP

EMPLOYER_KEYS = ("national_insurance", "pension", "severance", "study_fund")
Q = D("0.01")


def _val(x):
    return x.get("value") if isinstance(x, dict) else x


def _d(x):
    return D(str(x)).quantize(Q, ROUND_HALF_UP)


def employer_cost(year, stubs):
    """מחזיר {rows: [...], by_employee: [...], total: {...}}. מאוחר באותו חודש/עובד דורס (כמו payments_summary)."""
    latest = {}
    for s in stubs:
        if s.get("year") != year or not s.get("month"):
            continue
        latest[(str(s.get("emp_id_number")), int(s["month"]))] = s
    rows = []
    for (idn, m), s in sorted(latest.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        emp = s.get("employer") or {}
        gross = _d(s.get("gross") or 0)
        parts, missing = {}, []
        for k in EMPLOYER_KEYS:
            v = _val(emp.get(k))
            if v is None:
                missing.append(k)
                parts[k] = D(0)
            else:
                parts[k] = _d(v)
        total = gross + sum(parts.values(), D(0))
        rows.append({"emp_id_number": idn, "emp_name": s.get("emp_name"), "month": m, "gross": gross, **parts,
                     "total": total, "status": "partial" if missing else "complete", "missing": missing})
    by_emp = {}
    for r in rows:
        e = by_emp.setdefault(r["emp_id_number"], {"emp_id_number": r["emp_id_number"], "emp_name": r["emp_name"],
                                                    "months": 0, "gross": D(0), "total": D(0), "partial_months": 0,
                                                    **{k: D(0) for k in EMPLOYER_KEYS}})
        e["months"] += 1
        e["gross"] += r["gross"]; e["total"] += r["total"]
        e["partial_months"] += 1 if r["status"] == "partial" else 0
        for k in EMPLOYER_KEYS:
            e[k] += r[k]
    tot = {"employees": len(by_emp), "gross": sum((e["gross"] for e in by_emp.values()), D(0)),
           "total": sum((e["total"] for e in by_emp.values()), D(0)),
           "partial_months": sum(e["partial_months"] for e in by_emp.values()),
           **{k: sum((e[k] for e in by_emp.values()), D(0)) for k in EMPLOYER_KEYS}}
    return {"rows": rows, "by_employee": sorted(by_emp.values(), key=lambda e: e["emp_id_number"]), "total": tot,
            "notes": ["דוח ניהולי פנימי, לא דוח רשמי",
                      "שווי הטבות כלול בברוטו (עלות חשבונאית, לא בהכרח הוצאה במזומן)",
                      "רכיב מעסיק חסר מסומן partial ולא נספר כאפס"]}
