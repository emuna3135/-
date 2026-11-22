import unittest
import card, proposals


class PointsYear(unittest.TestCase):
    def test_2026_verified_note(self):
        p, st, n = card.points_from_form101(2026, True, "F", {})
        self.assertEqual(p, 2.75)
        self.assertIn("סימולטור", n)
        self.assertNotIn("לא נבדק", n)

    def test_other_year_not_claimed_verified(self):
        p, st, n = card.points_from_form101(2020, True, "F", {})
        self.assertEqual(p, 2.75)
        self.assertIn("לפי החוק בלבד", n)
        self.assertNotIn("מאומת", n)

    def test_man_other_year(self):
        _p, _s, n = card.points_from_form101(2020, True, "M", {})
        self.assertNotIn("מאומת", n)


class ManualFill(unittest.TestCase):
    ctx = {"id_number": "000000018", "is_resident": True, "gender": "F"}

    def test_unmarked_boxes_block_then_fill_recalculates(self):
        raw = {"id_number": "000000018", "tax_year": 2020, "signed_on": "2020-01-01"}
        prop, val = proposals.build_proposal(proposals.KIND_FORM101, raw, "t", [], ctx=self.ctx)
        for k in ("income_type", "other_income", "other_credits_claimed"):
            self.assertIn(k, val.errors)
        raw.update(income_type="main", other_income=False, other_credits_claimed=False)
        prop, val = proposals.build_proposal(proposals.KIND_FORM101, raw, "t", [], ctx=self.ctx)
        self.assertEqual(val.errors, {})
        self.assertEqual(val.checks["credit_points"]["points"], 2.75)
        raw.update(other_credits_claimed=True)   # סימון ידני של "זיכויים נוספים" משנה את החישוב
        prop, val = proposals.build_proposal(proposals.KIND_FORM101, raw, "t", [], ctx=self.ctx)
        self.assertIsNone(val.checks["credit_points"]["points"])


if __name__ == "__main__":
    unittest.main()
