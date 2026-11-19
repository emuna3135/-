import unittest
import form106 as f
import report126_data as r126

PROFILE = {"name": "חברה", "file_no": "912345678"}
EMP = {"id_number": "123456782", "first_name": "דנה", "family_name": "לוי", "street": "הרצל 1", "city": "חיפה"}


def stub(m, **kw):
    d = {"emp_id_number": "123456782", "year": 2026, "month": m, "gross": 10000.0, "taxable": 10000.0,
         "income_tax": 500.0, "national_insurance": 300.0, "health": 200.0, "pension_employee": 600.0,
         "points": 2.25, "benefits": {}, "employer": {"pension": 650.0, "severance": 833.0, "study_fund": 0.0,
                                                        "national_insurance": 400.0}}
    d.update(kw)
    return d


class Collect(unittest.TestCase):
    def test_annual_sums(self):
        recs, issues = f.collect(2026, PROFILE, [EMP], [stub(m) for m in range(1, 13)])
        r = recs[0]
        self.assertEqual(r["months"], 12)
        self.assertEqual(r["salary"], 120000.0)
        self.assertEqual(r["tax"], 6000.0)
        self.assertEqual(r["ni"], 3600.0)
        self.assertEqual(r["pension_employer"], 7800.0)
        self.assertEqual(r["points"], 2.25)
        self.assertTrue(f.submittable(issues))

    def test_recalc_overrides_same_month(self):
        recs, _ = f.collect(2026, PROFILE, [EMP], [stub(1, income_tax=100.0), stub(1, income_tax=200.0)])
        self.assertEqual(recs[0]["tax"], 200.0)
        self.assertEqual(recs[0]["months"], 1)

    def test_manual_month_blocks_not_guesses(self):
        recs, issues = f.collect(2026, PROFILE, [EMP], [stub(1), stub(2, income_tax=None)])
        self.assertIsNone(recs[0]["tax"])
        self.assertFalse(f.submittable(issues))

    def test_missing_profile_blocks(self):
        _, issues = f.collect(2026, {}, [EMP], [stub(1)])
        self.assertFalse(f.submittable(issues))

    def test_no_stubs_blocks(self):
        recs, issues = f.collect(2026, PROFILE, [EMP], [stub(1, year=2025)])
        self.assertEqual(recs, [])
        self.assertFalse(f.submittable(issues))

    def test_exempt_amount_flagged_manual(self):
        _, issues = f.collect(2026, PROFILE, [EMP], [stub(1, taxable=9000.0)])
        self.assertTrue(any("פטור" in i["text"] for i in issues))

    def test_points_change_warns(self):
        _, issues = f.collect(2026, PROFILE, [EMP], [stub(1), stub(2, points=3.0)])
        self.assertTrue(any("השתנה" in i["text"] for i in issues))


class Pdf(unittest.TestCase):
    def test_pdf_created_and_masks_id(self):
        data, issues, n, ok = f.run(PROFILE, 2026, [EMP], [stub(m) for m in range(1, 4)])
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertEqual(n, 1)
        self.assertTrue(ok)

    def test_employer_ni_stored_as_number(self):
        self.assertEqual(r126._employer_ni({"employer": {"national_insurance": 225.5}}), 225.5)
        self.assertIsNone(r126._employer_ni({"employer": {"national_insurance": None}}))


if __name__ == "__main__":
    unittest.main()
