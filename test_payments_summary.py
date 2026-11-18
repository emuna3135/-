import payments_summary as ps


def stub(m, emp="1", tax=500, ni=300, health=200, ne=450, **kw):
    return {"emp_id_number": emp, "year": 2026, "month": m, "income_tax": tax, "national_insurance": ni,
            "health": health, "employer": {"national_insurance": {"value": ne}, "pension": {"value": 600}, **kw}}


def test_deadline_is_15th_of_next_month():
    assert ps.btl_deadline(2026, 3) == "2026-04-15"
    assert ps.btl_deadline(2026, 12) == "2027-01-15"


def test_sums_per_month_and_btl_total():
    r = ps.summarize(2026, [stub(1), stub(1, emp="2"), stub(2)])
    assert [x["month"] for x in r] == [1, 2]
    assert r[0]["employees"] == 2 and r[0]["income_tax"] == 1000 and r[0]["btl_total"] == 2 * (300 + 200 + 450)
    assert r[0]["pension_employer"] == 1200


def test_other_year_ignored_and_later_stub_wins():
    r = ps.summarize(2026, [stub(1, tax=100), stub(1, tax=700), {**stub(1), "year": 2025}])
    assert len(r) == 1 and r[0]["employees"] == 1 and r[0]["income_tax"] == 700


def test_missing_employer_ni_marks_manual_not_zero_silently():
    s = stub(1); s["employer"]["national_insurance"] = {"value": None}
    r = ps.summarize(2026, [s])[0]
    assert r["status"] == "manual" and r["ni_employer_missing"] == 1
    assert any("חסר" in n for n in r["notes"])


def test_unsourced_deadlines_stay_none():
    r = ps.summarize(2026, [stub(1)])[0]
    assert r["income_tax_deadline"] is None and r["pension_deadline"] is None
