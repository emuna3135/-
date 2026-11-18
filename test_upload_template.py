import employee_import as ei
import upload_template as ut


def test_template_has_expected_sheets_and_one_example_each():
    sheets = ei.read_sheets(ut.build_template())
    assert set(sheets) >= {"עובדים", "טופס 101"}
    assert len(sheets["עובדים"]) == 1 and len(sheets["טופס 101"]) == 1


def test_example_rows_are_accepted_by_the_importer():
    sheets = ei.read_sheets(ut.build_template())
    emp = ei.parse_employee(sheets["עובדים"][0])
    assert emp["family_name"] == "כהן" and emp["zip"] == "33000"
    idn, year, f = ei.parse_form101(sheets["טופס 101"][0])
    assert idn == "000000018" and year == 2026 and f["marital"] == "single"


def test_id_in_example_passes_check_digit():
    import form126
    assert form126.check_id_digit("000000018")


def test_month_headers_match_server_column_map():
    import re
    src = open("main_api.py", encoding="utf8").read()
    for head in ut.MONTH_HEAD:
        assert '"' + head + '"' in src, head
