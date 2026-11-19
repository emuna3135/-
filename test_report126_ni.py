import unittest
import report126_data as r
import engine


class NiFields(unittest.TestCase):
    def test_split_below_and_above_cap(self):
        cap = float(engine.NI_MAX_INSURED[2026])
        self.assertEqual(r._ni_split(2026, 10000), (10000.0, 0.0))
        b, o = r._ni_split(2026, cap + 1000)
        self.assertEqual((b, o), (cap, 1000.0))

    def test_unknown_year_gives_none(self):
        self.assertEqual(r._ni_split(1999, 5000), (None, None))

    def test_employer_ni_manual_is_none(self):
        s = {"employer": {"national_insurance": {"value": 5, "status": engine.MANUAL}}}
        self.assertIsNone(r._employer_ni(s))
        s = {"employer": {"national_insurance": {"value": 225.5, "status": engine.BY_LAW}}}
        self.assertEqual(r._employer_ni(s), 225.5)
        self.assertIsNone(r._employer_ni({}))


if __name__ == "__main__":
    unittest.main()
