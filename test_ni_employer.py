"""ביטוח לאומי של המעסיק: שיעורים 4.51% / 7.6% לפי btl.gov.il (חישוב עצמאי במבחנים)."""
import unittest
from decimal import Decimal as D

import engine as e


class NiEmployer(unittest.TestCase):
    def test_below_threshold(self):
        self.assertEqual(e.ni_employer(2026, 5000)["value"], D("5000") * D("0.0451"))

    def test_above_threshold(self):
        v = e.ni_employer(2026, 10000)["value"]
        self.assertEqual(v, D("7703") * D("0.0451") + D("2297") * D("0.076"))
        self.assertAlmostEqual(float(v), 347.4053 + 174.572, places=3)

    def test_cap(self):
        a = e.ni_employer(2026, 51910)["value"]
        b = e.ni_employer(2026, 90000)
        self.assertEqual(a, b["value"])
        self.assertIn("תקרה", b["note"])

    def test_unsupported_year(self):
        r = e.ni_employer(2030, 8000)
        self.assertIsNone(r["value"]); self.assertEqual(r["status"], e.MANUAL)

    def test_in_month(self):
        r = e.compute_month(year=2026, month=3, gross=10000)
        ne = r["employer"]["national_insurance"]
        self.assertEqual(ne["status"], e.BY_LAW)
        self.assertTrue(ne["basis"])
        self.assertEqual(ne["value"], e.ni_employer(2026, 10000)["value"])

    def test_not_deducted_from_net(self):
        base = e.compute_month(year=2026, month=3, gross=10000)["net"]
        self.assertEqual(base, e.compute_month(year=2026, month=3, gross=10000)["net"])
        r = e.compute_month(year=2026, month=3, gross=10000)
        self.assertNotIn("national_insurance_employer", r["items"])


if __name__ == "__main__":
    unittest.main()
