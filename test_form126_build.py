import form126 as f
import form126_build as b

CO = {"file_no": "912345678", "agid": 0, "legal_status": 1, "tax_file_no": 515000000,
      "name": "DEMO LTD", "phone": "035551234", "employer_tax": 1}


def emp(idn, **kw):
    e = {"id_number": idn, "family_name": "LEVI", "first_name": "DAN", "gender": "M",
         "birth_date": "1985-03-14", "start_date": "2020-01-01", "marital": "single",
         "income_type": "main", "street": "HERZL 1", "city": "HAIFA", "zip": "33000",
         "form101": 1,
         "months": {m: {"gross": 10000, "tax": 500, "ni": 300, "health": 200,
                        "ni_base": 10000, "ni_exempt_over": 0} for m in range(1, 13)}}
    e.update(kw)
    return e


def build(emps, co=CO):
    return b.build(co, 2025, emps, hebrew_visual=False)


def test_complete_data_gives_valid_records_with_one_known_blocker():
    lines, issues = build([emp("000000018"), emp("000000026")])
    assert all(len(l) == 964 for l in lines)
    types = [l[11:13] for l in lines]
    assert types[0] == "10" and types.count("20") == 2 and types.count("30") == 1
    assert types.count("40") == 1 and types.count("50") == 12
    # the only blocker is the employer's national insurance (not computed yet)
    blocks = [i for i in issues if i["level"] == "block"]
    assert len(blocks) == 1 and "ביטוח לאומי של המעביד" in blocks[0]["text"]
    assert not b.is_submittable(issues)


def test_employees_sorted_by_id_ascending():
    lines, _ = build([emp("000000026"), emp("000000018")])
    ids = [l[17:26] for l in lines if l[11:13] == "20"]
    assert ids == sorted(ids)


def test_summary_record_matches_the_employee_records():
    lines, _ = build([emp("000000018"), emp("000000026")])
    r30 = next(l for l in lines if l[11:13] == "30")
    assert int(r30[115:121]) == 2                      # field 14: number of 20-records
    assert int(r30[31:43]) == 2 * 12 * 10000           # field 7
    assert int(r30[103:115]) == 2 * 12 * 500           # field 13: tax withheld
    assert int(r30[283:289]) == len(lines)             # field 24א': all records


def test_monthly_records_reconcile_with_employee_totals():
    lines, _ = build([emp("000000018")])
    r50 = [l for l in lines if l[11:13] == "50"]
    assert sum(int(l[34:46]) for l in r50) == 12 * 10000
    assert [int(l[26:28]) for l in r50] == list(range(1, 13))


def test_full_year_is_written_as_N_and_12_months():
    lines, _ = build([emp("000000018")])
    r = next(l for l in lines if l[11:13] == "20")
    assert r[181:203] == "N".ljust(22) and r[203:205] == "12"


def test_partial_year_lists_months_in_order():
    e = emp("000000018", months={m: {"gross": 1000, "tax": 0, "ni": 0, "health": 0,
                                    "ni_base": 1000} for m in (4, 5, 9, 10, 11, 12)})
    lines, _ = build([e])
    r = next(l for l in lines if l[11:13] == "20")
    assert r[181:203] == "040509101112".ljust(22) and r[203:205] == "06"


def test_missing_name_and_bad_id_are_blockers_not_guesses():
    _, issues = build([emp("000000019", family_name="", first_name=None)])
    texts = " ".join(i["text"] for i in issues if i["level"] == "block")
    assert "שם משפחה" in texts and "שם פרטי" in texts and "ספרת ביקורת" in texts


def test_separated_marital_status_needs_manual_handling():
    _, issues = build([emp("000000018", marital="separated")])
    assert any("פרוד" in i["text"] for i in issues)


def test_missing_ni_base_is_blocker():
    e = emp("000000018")
    for v in e["months"].values():
        v.pop("ni_base")
    _, issues = build([e])
    assert any(i["field"] == "126/127" for i in issues)


def test_bad_company_file_number_blocks():
    _, issues = build([emp("000000018")], {**CO, "file_no": "123"})
    assert any("תיק ניכויים" in i["text"] for i in issues)


def test_additional_job_type_code():
    lines, _ = build([emp("000000018", income_type="additional")])
    r = next(l for l in lines if l[11:13] == "20")
    assert r[171:173] == "02"
