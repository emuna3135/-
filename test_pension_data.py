import io
import unittest
from datetime import date
import openpyxl
import employee_import as ei
import pension_data as pd
import upload_template

PROFILE = {"name": "חברת דמו", "file_no": "912345678", "phone": "035551234",
           "pension": {"employer_id": "515000000", "employer_id_type": 1, "operator_id": "1", "contact_first": "רות",
                       "contact_last": "כהן", "contact_email": "a@b.co", "contact_mobile": "0501111111"}}
EMP = {"id_number": "000000018", "first_name": "דנה", "family_name": "לוי", "street": "הנשיא", "city": "חיפה", "gender": "F",
       "birth_date": "1990-05-12", "start_date": "2020-03-01", "pension_employee_rate": 0.06, "employer_pension_rate": 0.065,
       "employer_severance_rate": 0.06, "position_scope_percent": 100}
STUB = {"emp_id_number": "000000018", "year": 2026, "month": 10, "pension_base": 10000.0, "pension_employee": 600.0,
        "employer": {"pension": 650.0, "severance": 600.0}}
G = "0A1B2C3D-0000-4000-8000-0123456789AB"
ROW = {"id_number": "000000018", "fund_code": "5" * 30, "fund_type": 2, "pension_kind": 1, "fund_name": "קרן", "fund_no": "1",
       "nimaan_kind": 1, "nimaan_id_type": 1, "nimaan_id": "510000000", "nimaan_at_producer": "1",
       "employer_at_producer": "123", "masav": "1", "pay_method": 1, "bank": 12, "branch": "600", "account": "0" * 20,
       "account_type": "001", "employer_acc_kind": 1, "collector_acc_kind": 1, "collector_bank": 10, "collector_branch": "100",
       "collector_account": "0" * 20, "prev_id": G, "mislaka": G, "mislaka_prev": G, "prev_record_id": G, "policy": "9",
       "emp_no": "1", "seif14": 1, "maamad": 1, "email": "d@e.co", "mobile": "0501234567", "house_no": "5", "apartment": 0,
       "mikud": 3300000, "po_box": 0, "work_days": 22}


def run(row=ROW, profile=PROFILE, stubs=(STUB,)):
    return pd.run(profile, 2026, 10, [EMP], [row] if row else [], list(stubs), env="test",
                  value_date=date(2026, 11, 15), asmachta="A1")


class Build(unittest.TestCase):
    def test_complete_is_valid_and_has_amounts(self):
        files, issues, ok = run()
        self.assertTrue(ok, issues)
        self.assertFalse(files[0]["draft"])
        self.assertIn("<SCHUM-HAFKADA-KOLEL>1850.00</SCHUM-HAFKADA-KOLEL>", files[0]["xml"])
        self.assertIn("<SHIUR-HAFRASHA>6.00</SHIUR-HAFRASHA>", files[0]["xml"])

    def test_missing_is_draft_with_hebrew_issue(self):
        row = {k: v for k, v in ROW.items() if k not in ("policy", "mislaka")}
        files, issues, ok = run(row)
        self.assertFalse(ok)
        self.assertTrue(files[0]["draft"])
        texts = " ".join(i["text"] for i in issues)
        self.assertIn("מספר פוליסה או חשבון", texts)
        self.assertIn("מזהה מסלקה", texts)
        self.assertNotIn("000000018", " ".join(i["scope"] for i in issues))

    def test_missing_employer_id_blocks(self):
        files, issues, ok = run(profile={**PROFILE, "pension": {}})
        self.assertFalse(ok)

    def test_no_rows_blocks(self):
        files, issues, ok = run(None)
        self.assertEqual(files, [])
        self.assertFalse(ok)

    def test_no_stub_for_month(self):
        files, issues, ok = run(stubs=[])
        self.assertEqual(files, [])
        self.assertFalse(ok)

    def test_two_recipients_two_files(self):
        r2 = {**ROW, "nimaan_id": "520000000", "fund_code": "6" * 30}
        files, _ = pd.build_files(PROFILE, 2026, 10, [EMP, {**EMP, "id_number": "000000026"}], [ROW, {**r2, "id_number": "000000026"}],
                                     [STUB, {**STUB, "emp_id_number": "000000026"}], env="test", value_date=date(2026, 11, 15), asmachta="A")
        self.assertEqual(len(files), 2)


class Template(unittest.TestCase):
    def test_template_has_pension_sheet_and_example_parses(self):
        wb = openpyxl.load_workbook(io.BytesIO(upload_template.build_template()))
        self.assertIn("פנסיה", wb.sheetnames)
        sheets = ei.read_sheets(upload_template.build_template())
        r = ei.parse_pension_row(sheets["פנסיה"][0])
        self.assertEqual(r["fund_type"], 2)
        self.assertEqual(len(r["fund_code"]), 30)
        self.assertEqual(ei.parse_employer_pension(sheets["מעביד"][0])["employer_id_type"], 1)

    def test_unknown_value_is_error(self):
        with self.assertRaises(ei.RowError):
            ei.parse_pension_row({"תעודת זהות": "1", "סוג קופה": "משהו"})


if __name__ == "__main__":
    unittest.main()
