import unittest
import places


class Places(unittest.TestCase):
    def test_list_size(self):
        self.assertGreater(len(places.names()), 1200)

    def test_exact(self):
        for n in ("באר יעקב", "ירושלים", "בני ברק", "תל־אביב–יפו", "אבו ג'וויעד", "קריית שמונה"):
            self.assertEqual(places.check(n)["status"], "exact", n)

    def test_spaces_and_hyphens_ignored(self):
        self.assertEqual(places.check("באר  יעקב")["status"], "exact")
        self.assertEqual(places.check("תל אביב יפו")["status"], "exact")

    def test_handwriting_error_suggests(self):
        r = places.check("מאר יעקב")                       # שגיאת קריאה מהטופס בכתב יד
        self.assertEqual(r["status"], "suggest")
        self.assertIn("באר יעקב", r["suggestions"])
        self.assertIsNone(r["canonical"])                   # לא מתקנים אוטומטית

    def test_spelling_variant(self):
        r = places.check("הרצליה")                          # הרשמי: הרצלייה
        self.assertEqual((r["status"], r["canonical"]), ("variant", "הרצלייה"))

    def test_part_of_double_name(self):
        r = places.check("תל אביב")
        self.assertEqual((r["status"], r["canonical"]), ("variant", "תל־אביב–יפו"))

    def test_unknown_and_empty(self):
        self.assertEqual(places.check("אאאאאאא")["status"], "unknown")
        self.assertEqual(places.check("")["status"], "empty")

    def test_warning(self):
        self.assertIsNone(places.warning_for("באר יעקב"))
        self.assertIn("באר יעקב", places.warning_for("מאר יעקב"))
        self.assertIn("לא נמצא", places.warning_for("אאאאאאא"))


class InProposal(unittest.TestCase):
    def test_city_warning_not_blocking(self):
        import proposals
        prop, val = proposals.build_proposal(
            proposals.KIND_FORM101,
            {"id_number": "123456782", "tax_year": 2026, "income_type": "main", "other_income": False,
             "other_credits_claimed": False, "city": "מאר יעקב"}, "test", [])
        self.assertTrue(any("באר יעקב" in w for w in val.warnings))
        self.assertNotIn("city", val.errors)
        self.assertEqual(prop["fields"]["city"], "מאר יעקב")        # לא מתוקן אוטומטית


if __name__ == "__main__":
    unittest.main()
