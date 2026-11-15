import unittest
from decimal import Decimal as D
import engine as e


class CumNiBase(unittest.TestCase):
    def test_first_month_known(self):
        r = e.compute_month(year=2026, month=1, gross=D("8000"), points="2.25")
        self.assertEqual(r["cumulative"]["cum_ni_base"], D("8000"))

    def test_chain_and_unknown_prev(self):
        prev = dict(e.ZERO_PREV, cum_ni_base=D("8000"))
        r = e.compute_month(year=2026, month=2, gross=D("9000"), points="2.25", prev=prev)
        self.assertEqual(r["cumulative"]["cum_ni_base"], D("17000"))
        old = dict(e.ZERO_PREV, cum_taxable=D("8000"), cum_tax=0)
        r2 = e.compute_month(year=2026, month=2, gross=D("9000"), points="2.25", prev=old)
        self.assertNotIn("cum_ni_base", r2["cumulative"])      # לא ידוע -> לא ממציאים


class FixedRate(unittest.TestCase):
    def test_rate_applied_and_flagged(self):
        r = e.compute_month(year=2026, month=3, gross=D("10000"), points="0", mode="fixed_rate", fixed_rate=0.15,
                            prev=dict(e.ZERO_PREV, cum_taxable=D("20000"), cum_tax=0))
        t = r["items"]["income_tax"]
        self.assertEqual(t["value"], 1500)
        self.assertEqual(t["status"], e.BY_LAW)
        self.assertIn("אישור תיאום מס", t["note"])
        self.assertEqual(r["cumulative"]["cum_tax"], 1500)

    def test_missing_or_bad_rate_is_manual(self):
        for rate in (None, -0.1, 0.9):
            r = e.compute_month(year=2026, month=3, gross=D("10000"), points="0", mode="fixed_rate", fixed_rate=rate)
            self.assertIsNone(r["items"]["income_tax"]["value"])
            self.assertEqual(r["overall_status"], e.MANUAL)

    def test_ni_still_on_gross_with_exempt_taxable(self):
        # פטור ממס (למשל נכה 100%) דרך taxable_gross נמוך: ב"ל ובריאות עדיין על הברוטו
        a = e.compute_month(year=2026, month=1, gross=D("10000"), taxable_gross=D("0"), points="2.25")
        b = e.compute_month(year=2026, month=1, gross=D("10000"), points="2.25")
        self.assertEqual(a["items"]["income_tax"]["value"], 0)
        self.assertEqual(a["items"]["national_insurance"]["value"], b["items"]["national_insurance"]["value"])


if __name__ == "__main__":
    unittest.main()
