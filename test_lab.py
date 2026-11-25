import sys, unittest
sys.path.insert(0, "lab")
import synthetic_lab as lab


class Lab(unittest.TestCase):
    def test_lab(self):
        out = lab.run()
        self.assertEqual(out["sim_bad"], 0)                 # כל 123 מקרי הסימולטור דרך שכבת 101
        self.assertEqual(out["inv"]["tax_mismatch"], 0)     # מס מצטבר מול חישוב בלתי תלוי
        self.assertEqual(out["inv"]["ni_mismatch"], 0)      # ב"ל ובריאות מול חישוב בלתי תלוי
        self.assertEqual(out["inv"]["manual"], 0)
        self.assertEqual(out["findings"], [])
