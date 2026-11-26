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

    def test_minor_is_manual(self):
        r = el.ni_health_issue("2009-03-03", "M", None, 2026, 1)
        self.assertTrue(r["ni"] and r["health"])

    def test_man_67_and_over_manual_but_66_not(self):
        self.assertIsNone(el.ni_health_issue("1959-12-31", "M", None, 2026, 1)["ni"])   # בן 66
        self.assertTrue(el.ni_health_issue("1958-02-02", "M", None, 2026, 1)["ni"])     # בן 67 ומעלה

    def test_woman_flagged_from_62(self):
        self.assertIsNone(el.ni_health_issue("1965-06-01", "F", None, 2026, 1)["ni"])   # בת 60
        self.assertIsNone(el.ni_health_issue("1964-02-02", "F", None, 2026, 1)["ni"])   # בת 61 בסוף ינואר
        self.assertTrue(el.ni_health_issue("1964-01-31", "F", None, 2026, 1)["ni"])     # בת 62 בסוף ינואר
        self.assertTrue(el.ni_health_issue("1963-02-02", "F", None, 2026, 1)["ni"])

    def test_foreign_worker_health_only(self):
        r = el.ni_health_issue("1990-12-12", "M", "foreign_legal", 2026, 1)
        self.assertIsNone(r["ni"])
        self.assertTrue(r["health"])

    def test_area_resident_not_blocked(self):
        r = el.ni_health_issue("1987-03-13", "M", "area_resident", 2026, 1)
        self.assertEqual((r["ni"], r["health"]), (None, None))

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
