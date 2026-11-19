import io
import unittest
import employee_import as ei
import upload_template


class EmployerSheet(unittest.TestCase):
    ROW = {"שם המעביד": "חברת דמו", "תיק ניכויים": 912345678, "מספר תיק במס הכנסה": "515000000",
           "טלפון": "035551234", "מעמד משפטי": "חברה", "מס מעסיקים": "חייב", "מספר אגיד": 0, "מספר מפעל": None}

    def test_parse_ok(self):
        r = ei.parse_employer(self.ROW)
        self.assertEqual((r["legal_status"], r["employer_tax"], r["file_no"], r["agid"]), (1, 2, "912345678", 0))
        self.assertIsNone(r["factory_no"])

    def test_missing_required(self):
        for k in ("שם המעביד", "תיק ניכויים", "מס מעסיקים"):
            row = {a: b for a, b in self.ROW.items() if a != k}
            with self.assertRaises(ei.RowError):
                ei.parse_employer(row)

    def test_unknown_value_not_guessed(self):
        with self.assertRaises(ei.RowError):
            ei.parse_employer({**self.ROW, "מעמד משפטי": "משהו"})

    def test_numeric_cells_from_excel(self):
        r = ei.parse_employer({**self.ROW, "תיק ניכויים": 912345678.0, "מספר אגיד": 3.0})
        self.assertEqual((r["file_no"], r["agid"]), ("912345678", 3))

    def test_template_has_employer_sheet_and_roundtrips(self):
        sheets = ei.read_sheets(upload_template.build_template())
        self.assertIn(ei.SHEET_EMPLOYER, sheets)
        r = ei.parse_employer(sheets[ei.SHEET_EMPLOYER][0])
        self.assertEqual(r["legal_status"], 1)
        self.assertRegex(r["file_no"], r"^9\d{8}$")


if __name__ == "__main__":
    unittest.main()
