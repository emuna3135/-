"""בדיקה מקדימה של קובץ הקמת עובדים (מסך 'מה קראתי'): מה המערכת הבינה מכל שורה, בלי לשמור דבר.
פונקציה טהורה, נבדקת ב-test_import_preview.py. אין ניחוש: כל ערך שלא זוהה מוצג כשגיאה, וערך חסר שיש לו השפעה על החישוב מוצג כאזהרה.
כל שדה שנקרא מתא מפורש בקובץ מסומן 'נקרא מהקובץ'; בדיקות על הערכים (תעודת זהות, תאריכים, גיל) מסומנות בנפרד."""
import datetime

import eligibility
import employee_import as ei
import secure

WORKER_LABEL = {"resident": "תושב ישראל", "foreign_nursing": "עובד זר בסיעוד", "foreign_legal": "עובד זר חוקי",
                "area_resident": "תושב האזור", "foreign_other": "עובד זר אחר"}


def _mask(idn):
    s = str(idn or "")
    return "*****" + s[-4:] if len(s) >= 4 else "****"


def build(sheets, existing_ids=(), today=None):
    """sheets: פלט employee_import.read_sheets. existing_ids: ת"ז שכבר קיימות בחברה. מחזיר dict לתצוגה."""
    today = today or datetime.date.today()
    existing_ids = set(existing_ids)
    emp_rows = sheets.get(ei.SHEET_EMPLOYEES)
    if emp_rows is None:
        return {"error": "חסר גיליון בשם 'עובדים'", "employees": [], "counts": {}}
    f101 = {}
    f101_errors = []
    for i, row in enumerate(sheets.get(ei.SHEET_FORM101, []), start=2):
        try:
            idn, year, f = ei.parse_form101(row)
            f101.setdefault(idn, []).append((year, f))
        except ValueError as e:
            f101_errors.append({"level": "block", "text": f"גיליון 'טופס 101' שורה {i}: {e}"})
    out = []
    for i, row in enumerate(emp_rows, start=2):
        issues, fields = [], []
        try:
            e = ei.parse_employee(row)
        except ValueError as ex:
            out.append({"row": i, "id": _mask(row.get("תעודת זהות")), "name": str(row.get("שם מלא") or ""), "status": "error",
                        "fields": [], "issues": [{"level": "block", "text": str(ex)}]})
            continue
        idn = e["id_number"]
        if not secure.valid_israeli_id(idn):
            issues.append({"level": "block", "text": "מספר תעודת זהות לא תקין (ספרת ביקורת)"})
        known = idn in existing_ids
        issues.append({"level": "info", "text": "עובד קיים: פרטיו לא יידרסו, יושלמו רק פרטי דיווח חסרים" if known else "עובד חדש"})
        fields += [("תעודת זהות", _mask(idn), "נקרא מהקובץ"), ("שם", e["full_name"], "נקרא מהקובץ"),
                   ("מין", "נקבה" if e["gender"] == "F" else "זכר", "נקרא מהקובץ"),
                   ("שכר יסוד", f'{e["base_salary"]:,.2f}', "נקרא מהקובץ"),
                   ("פנסיה עובד", f'{e["pension_employee_rate"] * 100:g}%', "נקרא מהקובץ")]
        if e.get("birth_date"):
            fields.append(("תאריך לידה", e["birth_date"], "נקרא מהקובץ"))
        else:
            issues.append({"level": "warn", "text": "חסר תאריך לידה: לא ייבדק גיל לביטוח לאומי (מתחת ל-18 או בגיל פרישה יש שיעורים אחרים)"})
        if e.get("start_date"):
            fields.append(("תחילת עבודה", e["start_date"], "נקרא מהקובץ"))
        else:
            issues.append({"level": "warn", "text": "חסר תאריך תחילת עבודה: חודש תחילת העבודה לא יזוהה (מצטבר קודם לא יאופס אוטומטית)"})
        forms = f101.get(idn, [])
        wt = next((f.get("worker_type") for _, f in forms if f.get("worker_type")), None)
        country = next((f.get("origin_country") for _, f in forms if f.get("origin_country")), None)
        if not forms:
            issues.append({"level": "warn", "text": "אין טופס 101 לעובד בקובץ: נקודות זיכוי ותיאום מס יחסרו עד שיוזן טופס"})
        else:
            fields.append(("טופס 101", ", ".join(str(y) for y, _ in forms), "נקרא מהקובץ"))
        if wt:
            fields.append(("סוג עובד", WORKER_LABEL.get(wt, wt), "נקרא מהקובץ"))
        if wt in eligibility.FOREIGN_TYPES and wt != "foreign_nursing":
            cat, why = eligibility.foreign_category(wt, country)
            if why:
                issues.append({"level": "warn", "text": why})
            else:
                fields.append(("מדינת מוצא", country or "", "נקרא מהקובץ"))
        if wt == "area_resident":
            issues.append({"level": "warn", "text": eligibility.area_resident_issue(wt)})
        if wt not in eligibility.FOREIGN_TYPES and wt != "area_resident":
            cat, why = eligibility.ni_category(e.get("birth_date"), e.get("gender"), e.get("old_age_pension"), today.year, today.month)
            if why:
                issues.append({"level": "warn", "text": why})
            elif cat:
                issues.append({"level": "info", "text": "ביטוח לאומי יחושב בקטגוריה: " + eligibility._CATEGORIES[cat]["label"]})
        status = "error" if any(x["level"] == "block" for x in issues) else ("warn" if any(x["level"] == "warn" for x in issues) else "ok")
        out.append({"row": i, "id": _mask(idn), "name": e["full_name"], "status": status,
                    "fields": [{"label": a, "value": b, "source": c} for a, b, c in fields], "issues": issues})
    counts = {s: sum(1 for x in out if x["status"] == s) for s in ("ok", "warn", "error")}
    counts["total"] = len(out)
    return {"employees": out, "counts": counts, "sheet_issues": f101_errors,
            "sheets": [k for k in sheets.keys()], "ready": counts["error"] == 0 and not f101_errors and counts["total"] > 0}
