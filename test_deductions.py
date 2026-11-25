import unittest
from decimal import Decimal as D
import deductions as X


def loan(**kw):
    d = dict(code="L1", kind="loan", monthly="1000", start="2026-01", total="2500")
    d.update(kw)
    return d


class Deductions(unittest.TestCase):
    def test_empty(self):
        r = X.month_deductions([], 2026, 5)
        self.assertEqual(r["amount"], D(0)); self.assertEqual(r["lines"], [])

    def test_before_start_and_after_end(self):
        self.assertEqual(X.month_deductions([loan()], 2025, 12)["amount"], D(0))
        self.assertEqual(X.month_deductions([loan(end="2026-02")], 2026, 3)["amount"], D(0))

    def test_full_then_last_partial_then_stop(self):
        a = [X.month_deductions([loan()], 2026, m)["amount"] for m in (1, 2, 3, 4)]
        self.assertEqual(a, [D("1000.00"), D("1000.00"), D("500.00"), D(0)])

    def test_balance_after(self):
        r = X.month_deductions([loan()], 2026, 3)
        self.assertEqual(r["balances"][0]["remaining_after"], D("0.00"))
        r = X.month_deductions([loan()], 2026, 1)
        self.assertEqual(r["balances"][0]["remaining_after"], D("1500.00"))

    def test_paid_before(self):
        r = X.month_deductions([loan(paid_before="2000")], 2026, 1)
        self.assertEqual(r["amount"], D("500.00"))

    def test_no_total_runs_until_end(self):
        it = dict(code="A", kind="advance", monthly="300.555", start="2026-01", end="2026-03")
        self.assertEqual(X.month_deductions([it], 2026, 2)["amount"], D("300.56"))
        self.assertEqual(X.month_deductions([it], 2026, 4)["amount"], D(0))

    def test_manual_flags(self):
        r = X.month_deductions([loan(), dict(code="G", kind="garnishment", monthly="200", start="2026-01")], 2026, 1)
        self.assertEqual(len(r["open"]), 2)
        self.assertEqual(r["amount"], D("1200.00"))

    def test_errors(self):
        for bad in (dict(code="", kind="loan", monthly="1", start="2026-01"),
                    dict(code="X", kind="zzz", monthly="1", start="2026-01"),
                    dict(code="X", kind="loan", monthly="0", start="2026-01"),
                    dict(code="X", kind="loan", monthly="-5", start="2026-01"),
                    dict(code="X", kind="loan", monthly="1", start="2026/01"),
                    dict(code="X", kind="loan", monthly="1", start="2026-05", end="2026-01")):
            with self.assertRaises(ValueError):
                X.month_deductions([bad], 2026, 1)
        with self.assertRaises(ValueError):
            X.month_deductions([loan(), loan()], 2026, 1)


if __name__ == "__main__":
    unittest.main()
