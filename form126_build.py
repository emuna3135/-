"""Builds a Form 126 file from payroll data.

Pure functions: no database, no network. The caller (the API layer) gathers
the plain dictionaries described below from the stored paystubs, employees and
Form 101 data.

The result is ``(lines, issues)``:
  * ``lines``  - the 964-column records, sorted as the specification requires;
  * ``issues`` - everything the system could not fill from a source, or that
                 failed a rule of the specification. Each issue has a
                 ``level``: ``"block"`` (the file must not be submitted) or
                 ``"warn"`` (a value was written as zero or defaulted and the
                 accountant must confirm it).

Nothing is guessed. A field with no source is left at zero/blank and listed.
With ``issues`` containing any ``block`` the file is a draft only.

``company``:  file_no (9 digits), agid (default 0), factory_no (optional),
              legal_status (1 company, 2 individual, 3 partnership,
              4 non-profit, 5 authority), tax_file_no, name, phone.
``employee``: id_number, family_name, first_name, gender "M"/"F", birth_date,
              start_date, marital (single/married/divorced/widowed/separated),
              income_type "main"/"additional", street, city, zip,
              form101 (1 electronic, 2 manual, 3 none, 4 exempt) or None,
              months {1..12: {gross, tax, ni, health,
                              ni_base (optional), ni_exempt_over (optional)}}.
``money``     whole shekels are written (``round`` to an int); the spec does not
              say plainly whether agorot are expected, and that is reported.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP

import form126 as f

_MARITAL = {"single": 10, "married": 20, "divorced": 30, "widowed": 40, "separated": 70}


def _issue(level, scope, field, text):
    return {"level": level, "scope": scope, "field": field, "text": text}


def _shekels(v) -> int:
    return int(Decimal(str(v or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _date(d) -> int:
    if d is None:
        return 0
    if isinstance(d, str):
        d = datetime.date.fromisoformat(d)
    return int(d.strftime("%Y%m%d"))


def _months_detail(months: list[int]) -> tuple[str, int]:
    months = sorted(set(months))
    if months == list(range(1, 13)):
        return "N", 12            # full year: "N" then blanks (spec, field 24)
    return "".join(f"{m:02d}" for m in months), len(months)


def build(company: dict, tax_year: int, employees: list[dict], *,
          hebrew_visual: bool | None, encoding: str | None = None):
    issues: list[dict] = []
    c = company
    file_no = str(c.get("file_no") or "")
    if not (len(file_no) == 9 and file_no.isdigit() and file_no[0] == "9"):
        issues.append(_issue("block", "חברה", "1", "מספר תיק ניכויים חייב להיות 9 ספרות שמתחילות ב-9"))
    agid = int(c.get("agid") or 0)
    common = {"1": int(file_no) if file_no.isdigit() else 0, "2": agid, "4": tax_year}
    factory = int(c["factory_no"]) if c.get("factory_no") else 0

    emps = sorted(employees, key=lambda e: str(e["id_number"]))
    seen = set()
    rec20: list[str] = []
    tot = dict(f26=0, f39=0, f116=0, f124=0, f125=0, f126=0, f127=0, n=0)
    monthly = {m: dict(n=0, gross=0, tax=0, ni=0) for m in range(1, 13)}

    for e in emps:
        who = f"ת\"ז {e['id_number']}"
        idn = str(e["id_number"])
        if idn in seen:
            issues.append(_issue("block", who, "5", "מספר זהות כפול בקובץ"))
        seen.add(idn)
        if not f.check_id_digit(idn.zfill(9)):
            issues.append(_issue("block", who, "5", "ספרת ביקורת של מספר הזהות לא תקינה"))
        for key, fld, label in (("family_name", "9", "שם משפחה"), ("first_name", "10", "שם פרטי"),
                                ("street", "11", "רחוב ומספר בית"), ("city", "12", "עיר"),
                                ("zip", "13", "מיקוד")):
            if not e.get(key):
                issues.append(_issue("block", who, fld, f"חסר {label}"))
        if e.get("marital") not in _MARITAL:
            issues.append(_issue("block", who, "15", "חסר מצב משפחתי"))
        elif e["marital"] == "separated":
            issues.append(_issue("block", who, "15", "פרוד מדווח רק עם אישור פקיד שומה – נדרש טיפול ידני"))
        if e.get("gender") not in ("M", "F"):
            issues.append(_issue("block", who, "14", "חסר מין"))
        if not e.get("birth_date"):
            issues.append(_issue("block", who, "18", "חסר תאריך לידה"))
        if not e.get("start_date"):
            issues.append(_issue("block", who, "23", "חסר תאריך תחילת עבודה"))
        if e.get("income_type") not in ("main", "additional"):
            issues.append(_issue("block", who, "22", "סוג משרה: נקבע רק משרה יחידה/נוספת מטופס 101; אחר – ידני"))
        if e.get("form101") not in (1, 2, 3, 4):
            issues.append(_issue("block", who, "122ה'", "חסרה ידיעה אם מולא טופס 101"))

        ms = {int(m): v for m, v in (e.get("months") or {}).items()
              if v and (v.get("gross") or v.get("tax") is not None)}
        if not ms:
            issues.append(_issue("block", who, "24", "אין תלושים בשנה זו"))
            continue
        detail, count = _months_detail(list(ms))
        gross = sum(_shekels(v.get("gross")) for v in ms.values())
        tax = sum(_shekels(v.get("tax")) for v in ms.values())
        ni = sum(_shekels(v.get("ni")) for v in ms.values())
        health = sum(_shekels(v.get("health")) for v in ms.values())
        if all(v.get("ni_base") is not None for v in ms.values()):
            f126 = sum(_shekels(v["ni_base"]) for v in ms.values())
            f127 = sum(_shekels(v.get("ni_exempt_over")) for v in ms.values())
        else:
            f126 = f127 = 0
            issues.append(_issue("block", who, "126/127",
                                 "חסר הבסיס לביטוח לאומי עד המקסימום ומעליו – נדרש טיפול ידני"))

        vals = {**common, "5": int(idn), "14": 1 if e.get("gender") == "M" else 2,
                "15": _MARITAL.get(e.get("marital"), 0), "18": _date(e.get("birth_date")),
                "22": 1 if e.get("income_type") == "main" else 2,
                "23": _date(e.get("start_date")), "24": detail, "25": count,
                "26": gross, "39": gross, "116": tax, "124": ni, "125": health,
                "126": f126, "127": f127, "122ה'": e.get("form101") or 0,
                "130": 1 if e.get("income_type") == "main" else 2, "143": factory,
                "9": e.get("family_name"), "10": e.get("first_name"),
                "11": e.get("street"), "12": e.get("city"),
                "13": int(e["zip"]) if str(e.get("zip") or "").isdigit() else 0}
        try:
            rec20.append(f.build_record("20", vals, hebrew_visual=hebrew_visual))
        except (ValueError, f.SpecError) as ex:
            issues.append(_issue("block", who, "-", str(ex)))
            continue
        tot["n"] += 1
        for k, v in (("f26", gross), ("f39", gross), ("f116", tax), ("f124", ni),
                     ("f125", health), ("f126", f126), ("f127", f127)):
            tot[k] += v
        for m, v in ms.items():
            monthly[m]["n"] += 1
            monthly[m]["gross"] += _shekels(v.get("gross"))
            monthly[m]["tax"] += _shekels(v.get("tax"))
            monthly[m]["ni"] += _shekels(v.get("ni")) + _shekels(v.get("health"))

    issues.append(_issue("warn", "כל העובדים", "27-38, 40-51, 84-99",
                         "שדות רכיבי שכר מיוחדים, ניכויים והפרשות נכתבו כ-0 – יש לוודא שאין רכיבים כאלה"))
    issues.append(_issue("warn", "קובץ", "-",
                         "סכומים נכתבו בשקלים שלמים; המפרט לא מבהיר לגבי אגורות – לאמת בבדיקת הרשות"))
    issues.append(_issue("block", "קובץ", "-",
                         "ביטוח לאומי של המעביד מחושב בתלוש, אך מיפוי שדותיו לרשומות 40 ו-50 טרם הוגדר במפרט – נדרש טיפול ידני"))

    if c.get("employer_tax") not in (1, 2):
        issues.append(_issue("block", "חברה", "10/13", "חסר: מעביד פטור (1) או חייב (2) במס מעסיקים"))
    rec10 = f.build_record("10", {**common, "6": 1, "7": tot["n"], "9": c.get("name"),
                                  "11": int(c["phone"]) if str(c.get("phone") or "").isdigit() else 0,
                                  "13": c.get("employer_tax") or 0, "25": factory}, hebrew_visual=hebrew_visual)
    rec50 = [f.build_record("50", {**common, "6": m, "7": monthly[m]["n"], "8": monthly[m]["gross"],
                                   "9": monthly[m]["tax"], "11": monthly[m]["tax"],
                                   "13": monthly[m]["tax"], "14": monthly[m]["ni"],
                                   "15": monthly[m]["gross"], "26": factory}, hebrew_visual=hebrew_visual)
             for m in range(1, 13) if monthly[m]["n"]]
    n_total_pre = 1 + len(rec20) + 1 + 1 + len(rec50)   # 10 + 20s + 30 + 40 + 50s
    rec30 = f.build_record("30", {**common, "7": tot["f26"], "12": tot["f39"], "13": tot["f116"],
                                  "14": tot["n"], "15": tot["f126"], "17": tot["f127"],
                                  "20": tot["f124"], "21": tot["f125"], "24א'": n_total_pre,
                                  "25": factory}, hebrew_visual=hebrew_visual)
    rec40 = f.build_record("40", {**common, "8": 2, "9": int(c["tax_file_no"]) if str(c.get("tax_file_no") or "").isdigit() else 0,
                                  "10": int(c.get("legal_status") or 0),
                                  "11": sum(m["gross"] for m in monthly.values()),
                                  "12": sum(m["ni"] for m in monthly.values()),
                                  "17": tot["f39"], "19": sum(m["gross"] for m in monthly.values()),
                                  "22": sum(m["tax"] for m in monthly.values()),
                                  "24": tot["f116"], "30": tot["n"], "31": factory},
                         hebrew_visual=hebrew_visual)

    # reconciliations the authority checks after submission (spec: 20 vs 40 vs 50)
    if tot["f116"] != sum(m["tax"] for m in monthly.values()):
        issues.append(_issue("block", "קובץ", "40/50", "סכום המס ברשומות 20 לא תואם את הרשומות החודשיות"))
    if tot["f39"] != sum(m["gross"] for m in monthly.values()):
        issues.append(_issue("block", "קובץ", "40/50", "סה\"כ שכר ברשומות 20 לא תואם את הרשומות החודשיות"))
    if not c.get("tax_file_no"):
        issues.append(_issue("block", "חברה", "40/9", "חסר מספר תיק עצמאי/חברה במס הכנסה"))
    if not c.get("legal_status"):
        issues.append(_issue("block", "חברה", "40/10", "חסר מעמד משפטי של המשלם"))

    lines = [rec10, *rec20, rec30, rec40, *rec50]
    if len(lines) != n_total_pre:
        issues.append(_issue("block", "קובץ", "24א'", "מספר הרשומות בקובץ לא תואם את הספירה ברשומה 30"))
    return lines, issues


def is_submittable(issues: list[dict]) -> bool:
    return not any(i["level"] == "block" for i in issues)
