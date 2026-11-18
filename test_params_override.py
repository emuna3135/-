import unittest
from decimal import Decimal as D
import params


class Override(unittest.TestCase):
    def test_default_is_law_value_with_as_of(self):
        r = params.param("reserve_monthly_max", 2026)
        self.assertEqual(r["value"], D("51910"))
        self.assertIn("מעודכן ל-2026", r["note"])

    def test_accountant_override_wins_and_is_marked(self):
        ov = {("reserve_monthly_max", 2026): {"value": "52000", "reason": "עדכון חוזר ב\"ל", "by": "חשבת", "at": "2026-11-18"}}
        with params.use_overrides(ov):
            r = params.param("reserve_monthly_max", 2026)
        self.assertEqual(r["value"], D("52000"))
        self.assertEqual(r["status"], params.ACCOUNTANT)
        self.assertIn("ערך החוק: 51910", r["note"])
        # מחוץ להקשר השינוי חוזר ערך החוק
        self.assertEqual(params.param("reserve_monthly_max", 2026)["value"], D("51910"))

    def test_override_fills_missing_year_but_marked(self):
        with params.use_overrides({("reserve_monthly_max", 2027): {"value": "53000", "reason": "שנה חדשה"}}):
            r = params.param("reserve_monthly_max", 2027)
        self.assertEqual(r["value"], D("53000"))
        self.assertEqual(r["status"], params.ACCOUNTANT)

    def test_bad_override_is_manual(self):
        with params.use_overrides({("reserve_monthly_max", 2026): {"value": "abc"}}):
            self.assertEqual(params.param("reserve_monthly_max", 2026)["status"], params.MANUAL)


if __name__ == "__main__":
    unittest.main()
