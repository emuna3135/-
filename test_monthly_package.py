import io, unittest
from openpyxl import load_workbook
import monthly_package as mp

STUBS = [
    {"year": 2026, "month": 11, "emp_name": "דנה כהן", "emp_id_number": "000000018", "net": 8000.5, "income_tax": 500, "national_insurance": 200,
     "health": 100, "employer": {"national_insurance": 300, "pension": 600, "severance": 0, "study_fund": 0}},
    {"year": 2026, "month": 11, "emp_name": "אבי לוי", "emp_id_number": "123456782", "net": None, "income_tax": 0, "national_insurance": 0,
     "health": 0, "employer": {"national_insurance": None}},
]


class Pkg(unittest.TestCase):
    def test_deadlines(self):
        self.assertEqual(mp.wage_deadline(2026, 11), "2026-12-09")
        self.assertEqual(mp.wage_deadline(2026, 12), "2027-01-09")

    def test_workbook(self):
        data, info = mp.build_workbook(2026, 11, STUBS)
        self.assertEqual(info, {"employees": 2, "net_total": 8000.5, "net_missing": 1})
        wb = load_workbook(io.BytesIO(data))
        ws = wb["העברות לעובדים"]
        self.assertEqual(ws["C2"].value, None)             # אבי: בלי נטו -> ריק, לא 0
        self.assertIn("נדרש טיפול ידני", ws["D2"].value)
        auth = {r[0].value: r for r in wb["תשלומים לרשויות"].iter_rows(min_row=2)}
        self.assertEqual(auth["מס הכנסה שנוכה"][2].value, mp.MANUAL)   # אין מקור -> לא מנחשים מועד
        self.assertEqual(auth["סה\"כ לביטוח לאומי"][2].value, "2026-12-15")
        self.assertEqual(auth["תשלום שכר לעובדים"][2].value, "2026-12-09")

    def test_readme_mentions_limits(self):
        t = mp.build_readme(2026, 11, {"employees": 2, "net_total": 1.0, "net_missing": 1}, ["אבי"], "לא הופק", [])
        self.assertIn("לא שלחה ולא שילמה", t)
        self.assertIn("אינו כלול", t)


if __name__ == "__main__":
    unittest.main()
