import datetime
import unittest
from decimal import Decimal as D

import termination as t
from engine import BY_LAW, MANUAL

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

    def test_severance_floor_min_wage_13b(self):
        b = dict(start_date=d(2024, 1, 1), end_date=d(2026, 12, 31), severance_components=[("base", 5000)])
        r = t.settlement(ended_by="dismissed", min_wage_monthly="6443.85", job_scope=1, **b)
        self.assertEqual(r["items"]["severance"]["value"], D("6443.85") * 3)   # רצפה 13ב
        self.assertEqual(r["items"]["severance"]["status"], BY_LAW)
        r2_ = t.settlement(ended_by="dismissed", **b)   # בלי שכר מינימום -> ידני
        self.assertEqual(r2_["items"]["severance"]["status"], MANUAL)

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


class VacationWageWorker(unittest.TestCase):
    def test_day_value_quarter_over_90(self):
        import labor_rules as lr
        r = lr.vacation_day_value_wage_worker(9000)
        self.assertEqual(r["value"], D(100))
        self.assertEqual(r["status"], BY_LAW)

    def test_termination_wage_worker_redemption(self):
        b = dict(start_date=d(2024, 1, 1), end_date=d(2026, 6, 30), severance_components=[("base", 6000)])
        r = t.settlement(ended_by="resigned", pay_type="daily_hourly", unused_vacation_days=3, quarter_wage=9000, **b)
        self.assertEqual(r["items"]["vacation_redemption"]["value"], D(300))
        self.assertEqual(r["items"]["vacation_redemption"]["status"], BY_LAW)
        r = t.settlement(ended_by="resigned", unused_vacation_days=3, quarter_wage=9000, **b)   # חודשי: לא נגזר
        self.assertEqual(r["items"]["vacation_redemption"]["status"], MANUAL)


class Section14Approval(unittest.TestCase):
    base = dict(start_date=d(2020, 1, 1), end_date=d(2024, 12, 31), severance_components=[("base", 10000)])

    def _s(self, **terms):
        t_ = dict(route="pension", deposit_rate=14.33, completion_rate=0, disability_insurance=False, agreement_ok=True)
        t_.update(terms)
        return t.settlement(ended_by="dismissed", section14=True, section14_terms=t_, min_wage_monthly=6000, job_scope=1, **self.base)

    def test_full_replacement_no_topup(self):
        r = self._s()
        self.assertEqual(r["items"]["severance"]["value"], D("0.00"))

    def test_12_percent_only_replaces_72(self):
        r = self._s(deposit_rate=12)        # 5 שנים x 10000 = 50000; נשאר 28%
        self.assertEqual(r["items"]["severance"]["value"], D("14000.00"))

    def test_12_plus_233_full(self):
        self.assertEqual(self._s(deposit_rate=12, completion_rate=2.33)["items"]["severance"]["value"], D("0.00"))

    def test_insurance_11_with_disability(self):
        r = self._s(route="insurance", deposit_rate=11, disability_insurance=True)
        self.assertEqual(r["items"]["severance"]["value"], D("14000.00"))

    def test_no_written_agreement_manual(self):
        self.assertEqual(self._s(agreement_ok=False)["items"]["severance"]["status"], MANUAL)

    def test_below_thresholds_full_severance_owed(self):
        self.assertEqual(self._s(deposit_rate=10)["items"]["severance"]["value"], D("50000.00"))
