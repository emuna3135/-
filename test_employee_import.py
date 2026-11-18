import datetime
import unittest

import employee_import as ei


class ParseEmployee(unittest.TestCase):
    def row(self, **kw):
        r = {"תעודת זהות": "123456782", "שם מלא": "דנה", "מין": "F", "תאריך לידה": "1985-03-04",
             "תאריך תחילת עבודה": datetime.datetime(2020, 5, 1), "תושב": "כן", "שכר יסוד": 9800,
             "אחוז פנסיה עובד": 0.06, "אחוז פנסיה מעסיק": 0.065, "אחוז פיצויים מעסיק": 0.06, "היקף משרה %": 100}
        r.update(kw)
        return r

    def test_full_row(self):
        e = ei.parse_employee(self.row())
        self.assertEqual(e["gender"], "F"); self.assertEqual(e["start_date"], "2020-05-01")
        self.assertEqual(e["pension_employee_rate"], 0.06); self.assertTrue(e["is_resident"])

    def test_percent_style_rate_is_read_as_percent(self):
        self.assertAlmostEqual(ei.parse_employee(self.row(**{"אחוז פנסיה עובד": 6}))["pension_employee_rate"], 0.06)

    def test_missing_required_is_error_not_default(self):
        r = self.row(); del r["אחוז פנסיה עובד"]
        with self.assertRaises(ei.RowError): ei.parse_employee(r)
        r = self.row(); del r["שכר יסוד"]
        with self.assertRaises(ei.RowError): ei.parse_employee(r)

    def test_bad_gender_and_date(self):
        with self.assertRaises(ei.RowError): ei.parse_employee(self.row(מין="?"))
        with self.assertRaises(ei.RowError): ei.parse_employee(self.row(**{"תאריך לידה": "04/03/1985"}))

    def test_hebrew_gender(self):
        self.assertEqual(ei.parse_employee(self.row(מין="זכר"))["gender"], "M")


class ParseForm101(unittest.TestCase):
    def test_hebrew_values(self):
        idn, y, f = ei.parse_form101({"תעודת זהות": "1", "שנת מס": 2026, "תאריך חתימה": "2026-01-05",
                                      "סוג הכנסה": "משרה נוספת", "הכנסה אחרת": "כן", "זיכוי כנגד הכנסה זו": "אצל מעסיק אחר",
                                      "מצב משפחתי": "נשוי/אה", "שנות לידה ילדים בחזקתו": "2010, 2015"})
        self.assertEqual((idn, y), ("1", 2026))
        self.assertEqual(f["income_type"], "additional"); self.assertTrue(f["other_income"])
        self.assertEqual(f["other_income_credit"], "elsewhere"); self.assertEqual(f["marital"], "married")
        self.assertEqual(f["custody_birth_years"], [2010, 2015])

    def test_unknown_marital_is_error(self):
        with self.assertRaises(ei.RowError):
            ei.parse_form101({"תעודת זהות": "1", "שנת מס": 2026, "מצב משפחתי": "מסובך"})

    def test_missing_tax_year_is_error(self):
        with self.assertRaises(ei.RowError): ei.parse_form101({"תעודת זהות": "1"})


if __name__ == "__main__":
    unittest.main()
