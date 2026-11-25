import unittest
import card
import engine as e


class Credit(unittest.TestCase):
    def test_resident_woman(self):
        self.assertEqual(card.credit_points(True, "F", False, None)[:2], (2.75, e.VERIFIED))

    def test_resident_man(self):
        self.assertEqual(card.credit_points(True, "M", False, None)[:2], (2.25, e.VERIFIED))

    def test_other_credits_need_manual(self):
        p, s, n = card.credit_points(True, "F", True, None)
        self.assertIsNone(p); self.assertEqual(s, e.MANUAL); self.assertIn("ידנית", n)

    def test_manual_points_used(self):
        self.assertEqual(card.credit_points(True, "F", True, 4.25)[:2], (4.25, e.MANUAL))

    def test_non_resident_unknown(self):
        self.assertIsNone(card.credit_points(False, "F", False, None)[0])

    def test_unknown_gender(self):
        self.assertIsNone(card.credit_points(True, "X", False, None)[0])


class Mode(unittest.TestCase):
    def test_main_with_101(self):
        self.assertEqual(card.tax_mode(True, "main", False)[0], "cumulative")

    def test_no_101(self):
        self.assertEqual(card.tax_mode(False, "main", False)[0], "no_coordination")

    def test_additional(self):
        self.assertEqual(card.tax_mode(True, "additional", False)[0], "no_coordination")

    def test_other_income(self):
        self.assertEqual(card.tax_mode(True, "main", True)[0], "no_coordination")
        self.assertEqual(card.tax_mode(True, "main", True, "elsewhere")[0], "no_coordination")
        self.assertEqual(card.tax_mode(True, "main", True, "here")[0], "cumulative")
        # משכורת חלקית / יומי: טופס 101, דברי הסבר 4-5 (כללים והוראות 2026)
        self.assertEqual(card.tax_mode(True, "main", False, None, "partial")[0], "cumulative")
        self.assertEqual(card.tax_mode(True, "main", True, "here", "partial")[0], "no_coordination")
        self.assertEqual(card.tax_mode(True, "main", False, None, "daily")[0], "manual")
        self.assertEqual(card.tax_mode(False, "main", False, None, "daily")[0], "no_coordination")   # בלי 101: מרבי


if __name__ == "__main__":
    unittest.main()


class ChildPoints(unittest.TestCase):
    def setUp(self):
        import card
        self.c = card

    def test_mother_ages_2026(self):
        f = self.c.child_points_for_year
        got = [str(f(2026, 2026 - a, "mother")) for a in range(0, 20)]
        self.assertEqual(got, ["2.5", "4.5", "4.5", "3.5", "2.5", "2.5"] + ["2"] * 12 + ["0.5", "0"])

    def test_father_ages(self):
        f = self.c.child_points_for_year
        self.assertEqual([str(f(2026, 2026 - a, "father")) for a in (0, 1, 3, 5, 6, 17, 18)],
                         ["2.5", "4.5", "3.5", "2.5", "1", "1", "0"])

    def test_single_parent_equals_mother_table(self):
        for a in range(0, 20):
            self.assertEqual(self.c.child_points_for_year(2025, 2025 - a, "single_parent"),
                             self.c.child_points_for_year(2025, 2025 - a, "mother"))

    def test_future_birth_is_zero(self):
        self.assertEqual(self.c.child_points_for_year(2026, 2027, "mother"), 0)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            self.c.child_points_for_year(2026, 2024, "uncle")

    def test_total_two_children_is_exact(self):
        pts, status, note = self.c.child_credit_points(2026, [2024, 2018], "mother")
        self.assertEqual(str(pts), "6.5")                       # 4.5 + 2
        self.assertEqual(status, self.c.VERIFIED)           # שני צירופי תפקיד/גיל נבדקו בסימולטור

    def test_credit_points_woman_with_children(self):
        pts, st, note = self.c.credit_points(True, "F", tax_year=2026, child_birth_years=[2024], parent_role="mother")
        self.assertEqual(pts, 7.25)                             # סימולטור 12.11.2026: 7.25
        self.assertEqual(st, self.c.VERIFIED)

    def test_children_with_other_credits_is_manual(self):
        pts, st, _ = self.c.credit_points(True, "F", other_credits_claimed=True, tax_year=2026,
                                          child_birth_years=[2024], parent_role="mother")
        self.assertIsNone(pts); self.assertEqual(st, self.c.MANUAL)

    def test_children_missing_role_is_manual(self):
        pts, st, _ = self.c.credit_points(True, "F", tax_year=2026, child_birth_years=[2024])
        self.assertIsNone(pts); self.assertEqual(st, self.c.MANUAL)

    def test_no_children_behaviour_unchanged(self):
        self.assertEqual(self.c.credit_points(True, "F")[0], 2.75)
        self.assertEqual(self.c.credit_points(True, "M")[0], 2.25)


class SimulatorProfiles(unittest.TestCase):
    """ארבעת הפרופילים שנבדקו מול סימולטור רשות המסים ב-12.11.2026 (שנת מס 2026)."""
    def test_profile_a_woman_child_10(self):
        self.assertEqual(card.credit_points(True, "F", tax_year=2026, child_birth_years=[2016], parent_role="mother")[0], 4.75)

    def test_profile_b_woman_child_2(self):
        self.assertEqual(card.credit_points(True, "F", tax_year=2026, child_birth_years=[2024], parent_role="mother")[0], 7.25)

    def test_profile_c_man_child_2(self):
        self.assertEqual(card.credit_points(True, "M", tax_year=2026, child_birth_years=[2024], parent_role="father")[0], 6.75)

    def test_profile_d_man_no_children(self):
        self.assertEqual(card.credit_points(True, "M")[0], 2.25)

    def test_unverified_combinations_stay_by_law(self):
        # צירופים שטרם נבדקו בסימולטור (לעדכן כשנוספים ל-SIMULATOR_VERIFIED)
        for role, g, birth in (("father", "M", 2016), ("mother", "F", 2008), ("father", "M", 2023)):
            self.assertNotIn((role, card._age_bucket(2026, birth)), card.SIMULATOR_VERIFIED)
            st = card.credit_points(True, g, tax_year=2026, child_birth_years=[birth], parent_role=role)[1]
            self.assertEqual(st, card.BY_LAW)

    def test_mixed_verified_and_unverified_is_by_law(self):
        st = card.credit_points(True, "F", tax_year=2026, child_birth_years=[2024, 2008], parent_role="mother")[1]
        self.assertEqual(st, card.BY_LAW)


class SimulatorExtra(unittest.TestCase):
    def test_p1_woman_birth_year(self):
        r = card.credit_points(True, "F", tax_year=2026, child_birth_years=[2026], parent_role="mother")
        self.assertEqual(r[0], 5.25)
        self.assertEqual(r[1], card.VERIFIED)


class SimulatorYear(unittest.TestCase):
    def test_other_year_not_marked_verified(self):
        # אותו צירוף (אישה, ילד בן 2) בשנת 2025 לא נבדק בסימולטור
        r = card.credit_points(True, "F", tax_year=2025, child_birth_years=[2023], parent_role="mother")
        self.assertEqual(r[1], card.BY_LAW)
        self.assertEqual(r[0], 7.25)
