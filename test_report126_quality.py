"""בדיקות איכות לקובץ 126: 100 עובדים, מקרי קצה, ושלמות מבנה הקובץ (אורך שורה, מיון, ללא NULL, מיסוך ת"ז)."""
import report126_data as rd

PROFILE = {"file_no": "912345678", "agid": 0, "legal_status": 1, "tax_file_no": 515000000,
           "name": "DEMO LTD", "phone": "035551234", "employer_tax": 1}


def _with_check_digit(base8: int) -> str:
    s = f"{base8:08d}"
    tot = 0
    for i, ch in enumerate(s):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        tot += d - 9 if d > 9 else d
    return s + str((10 - tot % 10) % 10)


def _emp(i, **kw):
    return {"id_number": _with_check_digit(1000 + i * 7), "family_name": "LEVI", "first_name": f"N{i}",
            "street": "HERZL 1", "city": "HAIFA", "zip": "33000", "gender": "F" if i % 2 else "M",
            "birth_date": "1985-03-14", "start_date": "2020-01-01", **kw}


def _stubs(emp, year=2025, months=range(1, 13)):
    return [{"emp_id_number": emp["id_number"], "year": year, "month": m, "gross": 9000 + m,
             "income_tax": 400, "national_insurance": 250, "health": 180} for m in months]


def test_100_employees_file_structure():
    emps = [_emp(i) for i in range(100)]
    f101 = {e["id_number"]: {"marital": "married", "income_type": "main", "signed_on": "2025-01-05"} for e in emps}
    stubs = [s for e in emps for s in _stubs(e)]
    data, issues, n, ok = rd.run(PROFILE, 2025, emps, f101, stubs, hebrew_visual=False, encoding="cp1255")
    lines = data.split(b"\r\n")
    assert lines[-1] == b"" and len(lines) - 1 == n
    assert n >= 100 and len(data) == n * 966           # כל הרשומות באורך קבוע
    assert b"\x00" not in data
    assert ok is False                                  # חוסמים ידניים עדיין קיימים (תוספת ב"ל מעביד וכו')
    for i in issues:                                    # ת"ז מלאה לא מופיעה בהודעות
        assert not any(e["id_number"] in i["scope"] for e in emps)


def test_edge_partial_year_and_no_payslips_do_not_crash():
    a, b, c = _emp(1), _emp(2), _emp(3)
    stubs = _stubs(a, months=[11, 12]) + _stubs(b, months=[1])
    data, issues, n, _ = rd.run(PROFILE, 2025, [a, b, c], {}, stubs, hebrew_visual=True, encoding="cp862")
    assert len(data) == n * 966 and n >= 3


def test_other_year_stubs_ignored():
    a = _emp(1)
    e = rd.collect_employees(2025, [a], {}, _stubs(a, year=2024))
    assert e[0]["months"] == {}


def test_same_input_same_output():
    emps = [_emp(i) for i in range(10)]
    stubs = [s for e in emps for s in _stubs(e)]
    r1 = rd.run(PROFILE, 2025, emps, {}, stubs, hebrew_visual=False, encoding="cp1255")
    r2 = rd.run(PROFILE, 2025, list(reversed(emps)), {}, stubs, hebrew_visual=False, encoding="cp1255")
    assert r1[0] == r2[0]                               # סדר הקלט לא משפיע (מיון לפי ת"ז)
