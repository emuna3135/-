import unittest
from decimal import Decimal as D
import localities as L
import engine as pe

PREV0 = dict(pe.ZERO_PREV)


class Data(unittest.TestCase):
    def test_count_and_combos(self):
        self.assertEqual(len(L.names()), 492)          # 491 מפרק ח' + אילת (פרק ה')
        ok = {(7, 146640), (10, 180000), (12, 186000), (12, 186600), (12, 213240), (12, 226560), (14, 180000),
              (14, 213240), (14, 219960), (14, 259920), (16, 226560), (18, 245400), (18, 259920), (20, 259920), (20, 267840)}
        for n in [x for x in L.names() if x != L.EILAT]:
            r, c = L.lookup(n, 2026)
            self.assertIn((int(r * 100), int(c)), ok, n)

    def test_known_entries_from_booklet(self):
        self.assertEqual(L.lookup("קריית שמונה", 2026), (D("0.20"), D("259920")))
        self.assertEqual(L.lookup("אשקלון", 2026), (D("0.07"), D("146640")))
        self.assertEqual(L.lookup("נוף הגליל", 2026), (D("0.12"), D("226560")))
        self.assertEqual(L.lookup("קדם ערבה", 2026), (D("0.10"), D("180000")))

    def test_eilat_from_chapter_5(self):
        self.assertEqual(L.lookup(L.EILAT, 2026), (D("0.10"), D("268560")))

    def test_other_year_or_unknown(self):
        self.assertIsNone(L.lookup("שדרות", 2025))
        self.assertIsNone(L.lookup("אין כזה יישוב", 2026))
        self.assertIsNone(L.lookup(None, 2026))


class InTax(unittest.TestCase):
    def _tax(self, loc, gross="15000"):
        r = pe.compute_month(year=2026, month=1, gross=D(gross), points="2.25", mode="cumulative", prev=None,
                             locality=loc)
        return r["items"]["income_tax"]

    def test_locality_reduces_tax_and_downgrades_status(self):
        base = self._tax(None)
        with_loc = self._tax(L.lookup("שדרות", 2026))
        self.assertLess(with_loc["value"], base["value"])
        self.assertIn("יישוב מוטב", with_loc["note"])
        self.assertEqual(with_loc["status"], pe.BY_LAW)
        self.assertEqual(base["status"], pe.ACCOUNTANT)

    def test_credit_is_rate_times_income_up_to_cap(self):
        rate, cap = L.lookup("אשקלון", 2026)
        base, loc = self._tax(None, "9000"), self._tax((rate, cap), "9000")
        self.assertLessEqual(base["value"] - loc["value"], 9000 * 0.07 + 1)
        self.assertGreaterEqual(base["value"] - loc["value"], 0)

    def test_cap_applies_monthly(self):
        # תקרה 146,640 לשנה = 12,220 לחודש: הכנסה גבוהה לא מגדילה את ההנחה מעבר ל-rate x 12,220
        rate, cap = L.lookup("אשקלון", 2026)
        a = self._tax(None, "30000")["value"] - self._tax((rate, cap), "30000")["value"]
        self.assertLessEqual(a, float(rate * D(12220)) + 1)
        self.assertGreaterEqual(a, float(rate * D(12220)) - 1)


if __name__ == "__main__":
    unittest.main()
