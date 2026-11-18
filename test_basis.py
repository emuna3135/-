import unittest

import basis
import engine as e


class BasisPerLine(unittest.TestCase):
    def test_every_main_line_has_basis(self):
        r = e.compute_month(year=2026, month=1, gross="12000", prev=e.ZERO_PREV)
        for key in ("income_tax", "national_insurance", "health", "pension_employee", "study_fund_employee"):
            self.assertTrue(r["items"][key]["basis"], key)

    def test_income_tax_names_regulations_and_rounding_rule(self):
        b = basis.for_item("income_tax")
        self.assertIn("ניכוי ממשכורת", b[0]["law"]); self.assertIn("49 אגורות", b[0]["section"])

    def test_cumulative_is_not_presented_as_law(self):
        kinds = [b["kind"] for b in basis.for_item("income_tax")]
        self.assertIn("accountant", kinds)

    def test_unknown_section_is_none_not_invented(self):
        self.assertIsNone(basis.for_item("national_insurance")[0]["section"])

    def test_unknown_line_returns_empty(self):
        self.assertEqual(basis.for_item("no_such_line"), [])


if __name__ == "__main__":
    unittest.main()
