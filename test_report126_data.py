import report126_data as rd

PROFILE = {"file_no": "912345678", "agid": 0, "legal_status": 1, "tax_file_no": 515000000,
           "name": "DEMO LTD", "phone": "035551234", "employer_tax": 1}
EMP = {"id_number": "000000018", "family_name": "LEVI", "first_name": "DAN", "street": "HERZL 1",
       "city": "HAIFA", "zip": "33000", "gender": "M", "birth_date": "1985-03-14", "start_date": "2020-01-01"}
F101 = {"000000018": {"marital": "single", "income_type": "main", "signed_on": "2025-01-05"}}


def stubs(year=2025, months=range(1, 13), emp="000000018"):
    return [{"emp_id_number": emp, "year": year, "month": m, "gross": 10000, "income_tax": 500,
             "national_insurance": 300, "health": 200} for m in months]


def test_collects_year_months_and_form101():
    e = rd.collect_employees(2025, [EMP], F101, stubs() + stubs(year=2024))
    assert len(e) == 1 and sorted(e[0]["months"]) == list(range(1, 13))
    assert e[0]["marital"] == "single" and e[0]["form101"] == 1 and e[0]["income_type"] == "main"


def test_later_stub_for_same_month_wins():
    s = stubs(months=[1]) + [{**stubs(months=[1])[0], "gross": 12000}]
    e = rd.collect_employees(2025, [EMP], F101, s)
    assert e[0]["months"][1]["gross"] == 12000


def test_missing_form101_leaves_fields_missing_not_invented():
    e = rd.collect_employees(2025, [EMP], {}, stubs())[0]
    assert e["marital"] is None and e["income_type"] is None and e["form101"] == 3


def test_run_returns_file_issues_and_is_never_submittable_yet():
    data, issues, n, ok = rd.run(PROFILE, 2025, [EMP], F101, stubs(), hebrew_visual=False, encoding="cp1255")
    assert n >= 15 and data.endswith(b"\r\n") and len(data) == n * 966
    assert ok is False                                  # ביטוח לאומי של המעביד + בסיס 126/127 עדיין חסרים
    assert any("ביטוח לאומי של המעביד" in i["text"] for i in issues)


def test_ids_are_masked_in_issues():
    emp = {**EMP, "family_name": ""}
    _, issues, _, _ = rd.run(PROFILE, 2025, [emp], F101, stubs(), hebrew_visual=False, encoding="cp1255")
    scopes = [i["scope"] for i in issues if "שם משפחה" in i["text"]]
    assert scopes and all("000000018" not in s and "*****0018" in s for s in scopes)
