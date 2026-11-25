import unittest
from decimal import Decimal as D
import engine as e
import special_payslips as sp


class Schedule(unittest.TestCase):
    def test_matches_cumulative_month1_and_official_simulator_points(self):
        # נקודות שאומתו מול סימולטור רשות המסים (2.75 נקודות, חודשי): 10,000 -> 454
        self.assertEqual(sp.monthly_withholding(2025, "10000", "2.75")["value"], D(454))
        for g in ("10000", "15000", "30000"):
            r = e.compute_month(year=2025, month=1, gross=g, pension_employee_rate="0")
            self.assertEqual(sp.monthly_withholding(2025, g, "2.75")["value"], r["items"]["income_tax"]["value"])

    def test_zero_when_below_credits(self):
        self.assertEqual(sp.monthly_withholding(2025, "5000", "2.75")["value"], D(0))

    def test_unsupported_year_manual(self):
        self.assertEqual(sp.monthly_withholding(2023, "10000", "2.75")["status"], e.MANUAL)


class Reg4(unittest.TestCase):
    def test_identity(self):
        a = sp.monthly_withholding(2025, "15000", "2.75")["value"]
        b = sp.monthly_withholding(2025, "10000", "2.75")["value"]
        self.assertEqual(sp.irregular_tax_reg4(2025, "10000", "60000", "2.75")["value"], (a - b) * 12)

    def test_status_not_verified(self):
        self.assertEqual(sp.irregular_tax_reg4(2025, "10000", "2000", "2.75")["status"], e.BY_LAW)


class Recuperation(unittest.TestCase):
    def test_open_items_always_listed(self):
        r = sp.recuperation_month(2025, 7, "10000", 3, False)
        self.assertEqual(r["recuperation_gross"]["value"], D("2090.00"))
        self.assertEqual(len(r["open"]), 3)

    def test_manual_when_reduction_undecided(self):
        r = sp.recuperation_month(2025, 7, "10000", 3, None)
        self.assertIsNone(r["recuperation_gross"]["value"])
        self.assertTrue(r["open"])

    def test_2026_computed(self):
        r = sp.recuperation_month(2026, 7, "10000", 3, False)
        self.assertEqual(r["recuperation_gross"]["value"], D("2709.00"))   # 6 ימים x 451.50
        self.assertEqual(r["recuperation_gross"]["status"], "עפ\"י החוק")


if __name__ == "__main__":
    unittest.main()
