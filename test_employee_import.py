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


class FamilyFlags(unittest.TestCase):
    def test_flags_parsed(self):
        _id, _y, f = ei.parse_form101({"תעודת זהות": "1", "שנת מס": 2026, "מצבי חיים": "הורה יחיד; נער/ה 16-18"})
        self.assertEqual(f["family_flags"], ["niptar", "teen"])

    def test_no_flags_cell_is_empty(self):
        _id, _y, f = ei.parse_form101({"תעודת זהות": "1", "שנת מס": 2026})
        self.assertEqual(f["family_flags"], [])

    def test_unknown_flag_is_error_not_guess(self):
        with self.assertRaises(ei.RowError):
            ei.parse_form101({"תעודת זהות": "1", "שנת מס": 2026, "מצבי חיים": "משהו"})


class ReportingDetails(unittest.TestCase):
    BASE = {"תעודת זהות": "000000018", "שם מלא": "דן לוי", "מין": "זכר", "שכר יסוד": 10000,
            "אחוז פנסיה עובד": 0.06}

    def test_optional_details_are_copied_as_given(self):
        r = ei.parse_employee({**self.BASE, "שם משפחה": "לוי", "שם פרטי": "דן", "רחוב ומספר בית": "הרצל 1",
                               "עיר": "חיפה", "מיקוד": 33000})
        self.assertEqual((r["family_name"], r["first_name"], r["street"], r["city"], r["zip"]),
                         ("לוי", "דן", "הרצל 1", "חיפה", "33000"))

    def test_missing_details_are_not_invented(self):
        r = ei.parse_employee(self.BASE)
        for k in ("family_name", "first_name", "street", "city", "zip"):
            self.assertNotIn(k, r)

    def test_zip_is_padded_and_validated(self):
        self.assertEqual(ei.parse_employee({**self.BASE, "מיקוד": "1234.0"})["zip"], "01234")
        with self.assertRaises(ei.RowError):
            ei.parse_employee({**self.BASE, "מיקוד": "12AB5"})
        with self.assertRaises(ei.RowError):
            ei.parse_employee({**self.BASE, "מיקוד": "123456"})

    def test_full_name_is_never_split(self):
        r = ei.parse_employee(self.BASE)
        self.assertNotIn("family_name", r)
