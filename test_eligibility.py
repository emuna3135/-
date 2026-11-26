import datetime
import unittest

import employee_import as ei
import engine as pe
import eligibility as el


class TestAge(unittest.TestCase):
    def test_age_end_of_month(self):
        self.assertEqual(el.age_at_end_of_month("2008-03-31", 2026, 3), 18)
        self.assertEqual(el.age_at_end_of_month("2008-04-01", 2026, 3), 17)
        self.assertIsNone(el.age_at_end_of_month(None, 2026, 3))
        self.assertIsNone(el.age_at_end_of_month("לא תאריך", 2026, 3))

    def test_adult_resident_has_no_issue(self):
        r = el.ni_health_issue("1985-05-05", "M", "resident", 2026, 6)
        self.assertEqual((r["ni"], r["health"], r["missing_birth"]), (None, None, False))

    def cat(self, birth, g, pension, y=2026, m=1):
        return el.ni_category(birth, g, pension, y, m)

    def test_minor_exempt_employee(self):
        self.assertEqual(self.cat("2009-03-03", "M", None), ("exempt_employee", None))

    def test_regular_adult_none(self):
        self.assertEqual(self.cat("1985-05-05", "M", None), (None, None))
        self.assertEqual(self.cat("1959-12-31", "M", None), (None, None))      # גבר בן 66

    def test_man_67_needs_pension_answer(self):
        c, why = self.cat("1958-02-02", "M", None)
        self.assertIsNone(c); self.assertTrue(why)
        self.assertEqual(self.cat("1958-02-02", "M", False), ("age67_no_pension", None))
        self.assertEqual(self.cat("1958-02-02", "M", True), ("exempt_employee", None))

    def test_age_70_exempt_without_flag(self):
        self.assertEqual(self.cat("1955-01-01", "M", None), ("exempt_employee", None))

    def test_woman_uses_birth_year_table(self):
        self.assertEqual(self.cat("1964-02-02", "F", None), (None, None))           # בת 61: לפני גיל פרישה
        self.assertEqual(self.cat("1964-01-31", "F", None), (None, None))           # בת 62, פרישה ב-63 ו-6 חודשים
        c, why = self.cat("1963-06-15", "F", None)                                  # בת 62.5, פרישה 63.3: עדיין לא
        self.assertEqual((c, why), (None, None))
        c, why = self.cat("1962-12-01", "F", None)                                  # בת 63 ו-1 חודש, פרישה 63: כן
        self.assertTrue(why)
        self.assertEqual(self.cat("1962-12-01", "F", False), ("woman_between", None))
        self.assertEqual(self.cat("1958-02-02", "F", False), ("age67_no_pension", None))   # בת 67

    def test_missing_birth(self):
        self.assertEqual(self.cat(None, "M", None), (None, None))

    def test_foreign_categories(self):
        fc = el.foreign_category
        self.assertEqual(fc("resident", None), (None, None))
        self.assertEqual(fc("foreign_nursing", None), ("nursing_foreign", None))
        self.assertEqual(fc("foreign_legal", "הודו"), ("nonresident", None))
        self.assertEqual(fc("foreign_legal", "גרמניה"), ("treaty_no_health", None))
        self.assertEqual(fc("foreign_other", "קנדה"), ("nonresident", None))        # קנדה כמו עובד זר שאינו ממדינת אמנה
        self.assertEqual(fc("foreign_legal", "רוסיה"), ("treaty_no_health", None))
        c, why = fc("foreign_legal", "פולין"); self.assertIsNone(c); self.assertTrue(why)
        c, why = fc("foreign_legal", None); self.assertIsNone(c); self.assertTrue(why)

    def test_area_resident_manual(self):
        self.assertTrue(el.area_resident_issue("area_resident"))
        self.assertIsNone(el.area_resident_issue("resident"))


    def test_missing_birth_flagged_not_blocked(self):
        r = el.ni_health_issue(None, "M", None, 2026, 1)
        self.assertTrue(r["missing_birth"])
        self.assertEqual((r["ni"], r["health"]), (None, None))

    def test_start_month(self):
        self.assertTrue(el.is_start_month("2026-03-16", 2026, 3))
        self.assertFalse(el.is_start_month("2026-03-16", 2026, 4))
        self.assertFalse(el.is_start_month("2025-03-16", 2026, 3))
        self.assertFalse(el.is_start_month(None, 2026, 3))


class TestEngineOverride(unittest.TestCase):
    def test_manual_reason_leaves_net_unresolved(self):
        r = pe.compute_month(year=2026, month=1, gross=12000, ni_manual_reason="סיבה", health_manual_reason="סיבה")
        self.assertIsNone(r["items"]["national_insurance"]["value"])
        self.assertIsNone(r["net"])
        self.assertEqual(r["overall_status"], pe.MANUAL)

    def test_health_only_reason(self):
        r = pe.compute_month(year=2026, month=1, gross=12000, health_manual_reason="זר")
        self.assertIsNotNone(r["items"]["national_insurance"]["value"])
        self.assertIsNone(r["items"]["health"]["value"])

    def test_default_unchanged(self):
        r = pe.compute_month(year=2026, month=1, gross=12000)
        self.assertIsNotNone(r["net"])


class TestImportDates(unittest.TestCase):
    ROW = {"תעודת זהות": "900000019", "שם מלא": "בדוי", "מין": "M", "תאריך לידה": "1990-01-01",
           "תאריך תחילת עבודה": "2020-01-01", "שכר יסוד": 9000, "אחוז פנסיה עובד": 0.06}

    def test_ok(self):
        self.assertEqual(ei.parse_employee(self.ROW)["start_date"], "2020-01-01")

    def test_start_before_birth(self):
        with self.assertRaises(ei.RowError):
            ei.parse_employee({**self.ROW, "תאריך לידה": "2000-01-01", "תאריך תחילת עבודה": "1990-01-01"})

    def test_start_far_future(self):
        far = (datetime.date.today() + datetime.timedelta(days=800)).isoformat()
        with self.assertRaises(ei.RowError):
            ei.parse_employee({**self.ROW, "תאריך תחילת עבודה": far})


if __name__ == "__main__":
    unittest.main()


class TestStartMonthTax(unittest.TestCase):
    """עובד שמתחיל במרץ: המס לא יכול להיות נמוך משמעותית ממס עובד שמתחיל בינואר באותו שכר."""
    def test_march_starter_not_averaged_with_empty_months(self):
        import decimal
        D = decimal.Decimal
        jan = pe.compute_month(year=2026, month=1, gross=12000, points="2.25")
        prev = dict(pe.ZERO_PREV)
        prev["cum_weight"] = D(0)
        prev["cum_ni_base"] = D(0)
        prev["cum_months"] = D(0)
        mar = pe.compute_month(year=2026, month=3, gross=12000, points="2.25", prev=prev)
        self.assertEqual(mar["items"]["income_tax"]["value"], jan["items"]["income_tax"]["value"])


class TestCategoryAmounts(unittest.TestCase):
    """סכומים מחושבים ביד מטבלת טופס 102 (btl.gov.il), שכר 12,000, סף מופחת 7,703."""
    def run_cat(self, name, gross=12000):
        r = pe.compute_month(year=2026, month=1, gross=gross, ni_category=el._CATEGORIES[name])
        return r["items"]["national_insurance"]["value"], r["items"]["health"]["value"], r["employer"]["national_insurance"]["value"]

    def test_exempt(self):
        ni, h, er = self.run_cat("exempt_employee")
        self.assertEqual((float(ni), float(h)), (0.0, 0.0))
        self.assertAlmostEqual(float(er), 7703 * 0.0061 + 4297 * 0.0212, places=6)

    def test_age67(self):
        ni, h, er = self.run_cat("age67_no_pension")
        self.assertAlmostEqual(float(ni), 7703 * 0.0070 + 4297 * 0.0486, places=6)
        self.assertAlmostEqual(float(h), 470.9618, places=4)
        self.assertAlmostEqual(float(er), 7703 * 0.0413 + 4297 * 0.0696, places=6)

    def test_woman_between(self):
        ni, h, er = self.run_cat("woman_between")
        self.assertAlmostEqual(float(ni), 7703 * 0.0072 + 4297 * 0.0507, places=6)
        self.assertAlmostEqual(float(er), 7703 * 0.0417 + 4297 * 0.0712, places=6)

    def test_total_employee_matches_table(self):
        """סך עובד (לאומי+בריאות) חייב להתאים לטבלה: 3.93% / 10.03% ו-3.95% / 10.24%."""
        for name, lo, hi in (("age67_no_pension", 0.0393, 0.1003), ("woman_between", 0.0395, 0.1024)):
            c = el._CATEGORIES[name]
            self.assertAlmostEqual(float(c["ni"][0] + c["health"][0]), lo, places=6)
            self.assertAlmostEqual(float(c["ni"][1] + c["health"][1]), hi, places=6)

    def test_default_unchanged(self):
        ni, h, er = self.run_cat(None) if False else (None, None, None)
        r = pe.compute_month(year=2026, month=1, gross=12000)
        self.assertAlmostEqual(float(r["items"]["national_insurance"]["value"]), 380.9012, places=4)


class TestForeignAmounts(unittest.TestCase):
    def run_cat(self, name, gross=12000):
        r = pe.compute_month(year=2026, month=1, gross=gross, ni_category=el._CATEGORIES[name])
        return (float(r["items"]["national_insurance"]["value"]), float(r["items"]["health"]["value"]),
                float(r["employer"]["national_insurance"]["value"]))

    def test_nonresident(self):
        ni, h, er = self.run_cat("nonresident")
        self.assertAlmostEqual(ni, 7703 * 0.001 + 4297 * 0.0087, places=6)
        self.assertEqual(h, 0.0)
        self.assertAlmostEqual(er, 7703 * 0.0075 + 4297 * 0.0265, places=6)

    def test_treaty_no_health(self):
        ni, h, er = self.run_cat("treaty_no_health")
        self.assertAlmostEqual(ni, 7703 * 0.0104 + 4297 * 0.07, places=6)
        self.assertEqual(h, 0.0)
        self.assertAlmostEqual(er, 7703 * 0.0451 + 4297 * 0.076, places=6)

    def test_nursing_employer_only(self):
        ni, h, er = self.run_cat("nursing_foreign", 5000)
        self.assertEqual((ni, h), (0.0, 0.0))
        self.assertAlmostEqual(er, 180.0, places=6)
