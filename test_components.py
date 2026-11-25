import unittest
from decimal import Decimal as D
import components as c


class Build(unittest.TestCase):
    FIXED = [{"code": "001", "amount": "7800"}, {"code": "004", "rate": "12.5"},
             {"code": "007", "rate": "75"}, {"code": "008", "rate": "90"}]

    def test_video_example(self):
        # דוגמת ההדרכה: משכורת 7,800, נסיעות 250, ש.נוס 125% 10x75, ש.נוס 150% 2x90 -> 9,480 - 500 (יום פיצול) = 8,980
        r = c.build_lines(self.FIXED, {"004": 20, "007": 10, "008": 2})
        self.assertEqual(r["gross"], D("8980.00"))
        self.assertEqual(r["pension_base"], D("7800.00"))     # שכר יסוד בלבד
        self.assertEqual(r["pension_base_status"], "שכר יסוד בלבד")

    def test_pension_base_by_accountant(self):
        r = c.build_lines(self.FIXED, {"004": 20, "007": 10, "008": 2}, pension_base_codes=("007",))
        self.assertEqual(r["pension_base"], D("8550.00"))
        self.assertEqual(r["pension_base_status"], 'עפ"י רואת חשבון')

    def test_travel_over_cap_flagged(self):
        r = c.build_lines([{"code": "001", "amount": "7000"}, {"code": "004", "rate": "30"}], {"004": 20})
        self.assertTrue(any("מעל התקרה" in o for o in r["open"]))
        self.assertTrue(any("הפטור" in o for o in r["open"]))

    def test_closed_list(self):
        with self.assertRaises(ValueError):
            c.build_lines([{"code": "999", "amount": "1"}], {})
        with self.assertRaises(ValueError):
            c.build_lines([{"code": "001", "amount": "1"}, {"code": "001", "amount": "2"}], {})
        with self.assertRaises(ValueError):
            c.build_lines([{"code": "001", "amount": "-1"}], {})

    def test_severance_unknown_is_manual(self):
        r = c.build_lines([{"code": "001", "amount": "7000"}, {"code": "011", "amount": "500"}], {})
        self.assertIsNone(r["severance_wage"]["value"])     # פרמיה קבועה: ידני לפי תקנה 1

    def test_severance_base(self):
        r = c.build_lines([{"code": "001", "amount": "7000"}, {"code": "012", "amount": "300"}, {"code": "010", "amount": "900"}], {})
        self.assertEqual(r["severance_wage"]["value"], D("7300.00"))


if __name__ == "__main__":
    unittest.main()


class Extras(unittest.TestCase):
    def test_none(self):
        self.assertEqual(c.extras_for_paystub([], {}), (D(0), D(0), [], []))

    def test_premium_not_in_pension_by_default(self):
        g, pen, lines, open_ = c.extras_for_paystub([{"code": "011", "amount": 500}], {})
        self.assertEqual((g, pen), (D("500.00"), D(0)))

    def test_premium_in_pension_when_chosen(self):
        g, pen, *_ = c.extras_for_paystub([{"code": "011", "amount": 500}], {}, ["011"])
        self.assertEqual((g, pen), (D("500.00"), D("500.00")))

    def test_duplicates_with_existing_fields_rejected(self):
        for code in ("001", "007", "008", "010"):
            with self.assertRaises(ValueError):
                c.extras_for_paystub([{"code": code, "amount": 1}], {})

    def test_travel_by_days_flags_open(self):
        g, pen, lines, open_ = c.extras_for_paystub([{"code": "004", "rate": 22.6}], {"004": 20})
        self.assertEqual(g, D("452.00"))
        self.assertTrue(any("פטור" in o for o in open_))
