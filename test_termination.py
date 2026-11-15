import datetime
import unittest
from decimal import Decimal as D

import termination as t
from engine import MANUAL

d = datetime.date


class Months(unittest.TestCase):
    def test_full_years(self):
        self.assertEqual(t.full_months_of_service(d(2020, 1, 1), d(2022, 12, 31)), 36)

    def test_partial_month_not_counted(self):
        self.assertEqual(t.full_months_of_service(d(2025, 1, 15), d(2025, 3, 14)), 2)
        self.assertEqual(t.full_months_of_service(d(2025, 1, 15), d(2025, 3, 13)), 1)

    def test_end_before_start(self):
        with self.assertRaises(ValueError):
            t.full_months_of_service(d(2025, 2, 1), d(2025, 1, 1))


class Settlement(unittest.TestCase):
    base = dict(start_date=d(2020, 1, 1), end_date=d(2022, 12, 31), severance_components=[("base", 6550)])

    def test_dismissed_three_years_matches_course_exercise(self):
        r = t.settlement(ended_by="dismissed", **self.base)
        self.assertEqual(r["months"], 36)
        self.assertEqual(r["items"]["severance"]["value"], D(19650))

    def test_resigned_severance_manual(self):
        r = t.settlement(ended_by="resigned", **self.base)
        self.assertEqual(r["items"]["severance"]["status"], MANUAL)

    def test_section14_manual(self):
        r = t.settlement(ended_by="dismissed", section14=True, **self.base)
        self.assertEqual(r["items"]["severance"]["status"], MANUAL)

    def test_unknown_component_manual(self):
        r = t.settlement(ended_by="dismissed", start_date=d(2020, 1, 1), end_date=d(2022, 12, 31),
                         severance_components=[("base", 6000), ("mystery", 100)])
        self.assertIsNone(r["items"]["severance"]["value"])

    def test_less_than_year_manual(self):
        r = t.settlement(ended_by="dismissed", start_date=d(2025, 1, 1), end_date=d(2025, 6, 30),
                         severance_components=[("base", 6000)])
        self.assertEqual(r["items"]["severance"]["status"], MANUAL)

    def test_vacation_and_notice_need_input(self):
        r = t.settlement(ended_by="dismissed", **self.base)
        self.assertEqual(r["items"]["vacation_redemption"]["status"], MANUAL)
        self.assertEqual(r["items"]["notice_pay"]["status"], MANUAL)
        self.assertEqual(r["overall"], MANUAL)

    def test_vacation_computed_from_inputs(self):
        r = t.settlement(ended_by="dismissed", unused_vacation_days=5, vacation_day_value="300.50", **self.base)
        self.assertEqual(r["items"]["vacation_redemption"]["value"], D("1502.50"))

    def test_notice_above_table_is_flagged(self):
        r = t.settlement(ended_by="dismissed", notice_days_unworked=40, notice_day_value=300, **self.base)
        self.assertIsNone(r["items"]["notice_pay"]["value"])

    def test_notice_within_table(self):
        r = t.settlement(ended_by="dismissed", notice_days_unworked=30, notice_day_value=300, **self.base)
        self.assertEqual(r["items"]["notice_pay"]["value"], D(9000))

    def test_bad_ended_by(self):
        with self.assertRaises(ValueError):
            t.settlement(ended_by="x", **self.base)


if __name__ == "__main__":
    unittest.main()
