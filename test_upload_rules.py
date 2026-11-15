import unittest
import upload_rules as u


class UploadRules(unittest.TestCase):
    def test_missing_points_is_error_not_default(self):
        with self.assertRaises(ValueError):
            u.required_for_row({"tax_mode": "cumulative", "pension_employee_rate": 0.06})

    def test_missing_pension_is_error(self):
        with self.assertRaises(ValueError):
            u.required_for_row({"tax_mode": "cumulative", "credit_points": 2.75})

    def test_missing_mode_is_error(self):
        with self.assertRaises(ValueError):
            u.required_for_row({"credit_points": 2.75, "pension_employee_rate": 0.06})

    def test_hebrew_headers(self):
        self.assertEqual(u.required_for_row({"שיטת מס": "cumulative", "נקודות זיכוי": 2.75,
                                             "אחוז פנסיה עובד": 0.06}), ("cumulative", 2.75, 0.06))

    def test_points_not_needed_outside_cumulative(self):
        self.assertEqual(u.required_for_row({"tax_mode": "no_coordination",
                                             "pension_employee_rate": 0.06}),
                         ("no_coordination", 0.0, 0.06))

    def test_empty_string_is_missing(self):
        with self.assertRaises(ValueError):
            u.required_for_row({"tax_mode": "cumulative", "credit_points": "",
                                "pension_employee_rate": 0.06})


if __name__ == "__main__":
    unittest.main()
