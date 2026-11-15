import unittest
import overrides as o


def base():
    return {"net": 8777.24, "overall_status": "מאומת", "income_tax": 0.0, "national_insurance": 251.69,
            "health": 371.07, "flags": [],
            "items": {"income_tax": {"value": 0.0, "status": "x", "note": ""},
                      "national_insurance": {"value": 251.69, "status": "x", "note": ""},
                      "health": {"value": 371.07, "status": "x", "note": ""},
                      "pension_employee": {"value": 600.0, "status": "x", "note": ""},
                      "study_fund_employee": {"value": 0.0, "status": "x", "note": ""}}}


class Overrides(unittest.TestCase):
    def test_net_recomputed_and_logged(self):
        r = o.apply_override(base(), "national_insurance", "260.00", "שינוי בחוק", "acct@x")
        self.assertEqual(r["items"]["national_insurance"]["value"], 260.0)
        self.assertEqual(r["national_insurance"], 260.0)
        self.assertEqual(r["net"], 8768.93)           # 8777.24 + 251.69 - 260.00
        self.assertEqual(r["items"]["national_insurance"]["status"], o.OVERRIDDEN)
        self.assertEqual(r["overall_status"], o.OVERRIDDEN)
        self.assertEqual(len(r["overrides"]), 1)
        self.assertEqual(r["overrides"][0]["old"], 251.69)
        self.assertEqual(r["overrides"][0]["by"], "acct@x")

    def test_original_untouched(self):
        b = base(); o.apply_override(b, "health", 400, "סיבה", "u")
        self.assertEqual(b["items"]["health"]["value"], 371.07)
        self.assertNotIn("overrides", b)

    def test_reason_required(self):
        for bad in ("", "   ", None):
            with self.assertRaises(o.OverrideError):
                o.apply_override(base(), "health", 400, bad, "u")

    def test_user_required(self):
        with self.assertRaises(o.OverrideError):
            o.apply_override(base(), "health", 400, "סיבה", "")

    def test_field_whitelist(self):
        for f in ("gross", "net", "points", "weird"):
            with self.assertRaises(o.OverrideError):
                o.apply_override(base(), f, 1, "סיבה", "u")

    def test_bad_values(self):
        for v in (-1, "abc", float("nan"), float("inf"), None):
            with self.assertRaises(o.OverrideError):
                o.apply_override(base(), "health", v, "סיבה", "u")

    def test_net_rounded_when_old_value_unrounded(self):
        b = base(); b["items"]["national_insurance"]["value"] = 251.6888
        r = o.apply_override(b, "national_insurance", 260, "סיבה", "u")
        self.assertEqual(r["net"], 8768.93)

    def test_rounds_to_agora(self):
        r = o.apply_override(base(), "health", "371.075", "סיבה", "u")
        self.assertEqual(r["items"]["health"]["value"], 371.08)

    def test_multiple_overrides_kept_in_order(self):
        r = o.apply_override(base(), "health", 400, "א", "u")
        r = o.apply_override(r, "health", 410, "ב", "u")
        self.assertEqual([x["old"] for x in r["overrides"]], [371.07, 400.0])
        self.assertEqual(r["net"], round(8777.24 + 371.07 - 410, 2))

    def test_income_tax_flags_cumulative(self):
        r = o.apply_override(base(), "income_tax", 100, "סיבה", "u")
        self.assertTrue(any("מצטבר" in f for f in r["flags"]))

    def test_incomplete_slip_refused(self):
        b = base(); b["net"] = None
        with self.assertRaises(o.OverrideError):
            o.apply_override(b, "health", 400, "סיבה", "u")


if __name__ == "__main__":
    unittest.main()
