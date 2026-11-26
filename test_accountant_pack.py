import unittest
from lab import accountant_pack as A


def luhn_ok(s):
    tot = 0
    for i, ch in enumerate(s):
        x = int(ch) * (1 if i % 2 == 0 else 2)
        tot += x - 9 if x > 9 else x
    return tot % 10 == 0


class AccountantPack(unittest.TestCase):
    def test_fifty_rows_no_gaps_vs_independent_calc(self):
        rows, issues = A.build(10, 50)
        self.assertEqual(len(rows), 50)
        self.assertEqual(issues, [])
        self.assertEqual(len(rows[0]), len(A.HEAD))

    def test_ids_are_synthetic_and_valid(self):
        rows, _ = A.build(10, 50)
        ids = [r[0] for r in rows]
        self.assertEqual(len(set(ids)), 50)
        for i in ids:
            self.assertTrue(luhn_ok(i), i)
            self.assertTrue(i.startswith("0010"), i)   # טווח המעבדה בלבד

    def test_each_month_runs(self):
        for m in (1, 6, 12):
            rows, issues = A.build(m, 12)
            self.assertEqual(issues, [], m)


if __name__ == "__main__":
    unittest.main()
