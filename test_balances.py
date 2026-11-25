import unittest
from decimal import Decimal as D
import balances as B
import labor_rules as L


class Sick(unittest.TestCase):
    def test_accrual(self):
        r = B.sick_balance(0, [1] * 4, 2)
        self.assertEqual(r["remaining"], D("4.0")); self.assertEqual(r["status"], L.BY_LAW)

    def test_cap_90(self):
        r = B.sick_balance(89, [1, 1], 0)
        self.assertEqual(r["remaining"], D(90)); self.assertEqual(r["accrued"], D(1))

    def test_partial_month(self):
        self.assertEqual(B.sick_balance(0, ["0.5"])["remaining"], D("0.75"))

    def test_negative_flagged(self):
        r = B.sick_balance(0, [1], 5)
        self.assertEqual(r["remaining"], D("-3.5")); self.assertTrue(any("ידני" in n for n in r["notes"]))

    def test_errors(self):
        for f in (lambda: B.sick_balance(91), lambda: B.sick_balance(0, [2]), lambda: B.sick_balance(0, [1], -1)):
            with self.assertRaises(ValueError): f()


class Vacation(unittest.TestCase):
    def test_six_day_years(self):
        self.assertEqual(B.vacation_balance(1)["entitlement"], D(16))
        self.assertEqual(B.vacation_balance(6)["entitlement"], D(18))
        self.assertEqual(B.vacation_balance(20)["entitlement"], D(28))

    def test_balance(self):
        r = B.vacation_balance(1, opening=3, used=10)
        self.assertEqual(r["remaining"], D(9))

    def test_proportional_floor(self):
        r = B.vacation_balance(1, days_worked=100)
        self.assertEqual(r["entitlement"], D(8))

    def test_five_day_manual_before_2017(self):
        r = B.vacation_balance(1, five_day_week=True, as_of_year=2016)
        self.assertEqual(r["status"], L.MANUAL); self.assertIsNone(r["remaining"])

    def test_five_day_2026(self):
        self.assertEqual(B.vacation_balance(1, five_day_week=True)["entitlement"], D(12))


class Recreation(unittest.TestCase):
    def test_days(self):
        self.assertEqual(B.recreation_balance(1, 2)["remaining"], D(3))
        self.assertEqual(B.recreation_balance(25)["entitled"], D(10))

    def test_bad_year(self):
        self.assertEqual(B.recreation_balance(0)["status"], L.MANUAL)


if __name__ == "__main__":
    unittest.main()
