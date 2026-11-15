import unittest
import card
import proposals as p


class PointsFromForm101(unittest.TestCase):
    def test_no_family_data_is_base(self):
        self.assertEqual(card.points_from_form101(2026, True, "F", {})[0], 2.75)
        self.assertEqual(card.points_from_form101(2026, True, "M", {})[0], 2.25)

    def test_manual_and_other_credits_and_nonresident(self):
        self.assertEqual(card.points_from_form101(2026, True, "F", {"manual_points": 5})[1], card.MANUAL)
        self.assertEqual(card.points_from_form101(2026, True, "F", {"other_credits_claimed": True})[1], card.MANUAL)
        self.assertEqual(card.points_from_form101(2026, False, "F", {})[1], card.MANUAL)

    def test_children_without_marital_is_manual(self):
        r = card.points_from_form101(2026, True, "F", {"custody_birth_years": [2016]})
        self.assertIsNone(r[0]); self.assertEqual(r[1], card.MANUAL)

    def test_married_mother_child_age_10_matches_simulator(self):
        # simulator 2026: woman, married, one child aged 10 = 4.75
        r = card.points_from_form101(2026, True, "F", {"marital": "married", "custody_birth_years": [2016]})
        self.assertEqual((r[0], r[1]), (4.75, card.VERIFIED))

    def test_other_year_is_by_law(self):
        r = card.points_from_form101(2027, True, "F", {"marital": "married", "custody_birth_years": [2017]})
        self.assertEqual(r[1], card.BY_LAW)


class SchemaCleaning(unittest.TestCase):
    def test_lists(self):
        self.assertEqual(p._clean_year_list([2016, "2018"]), [2016, 2018])
        for bad in ("x", [1800], list(range(2000, 2030))):
            with self.assertRaises(ValueError):
                p._clean_year_list(bad)

    def test_flags_whitelist(self):
        self.assertEqual(p._clean_flags(["niptar", "niptar"]), ["niptar"])
        with self.assertRaises(ValueError):
            p._clean_flags(["hacker"])


class MonthlyCredits(unittest.TestCase):
    import datetime as _dt

    def test_olim_schedule_boundaries(self):
        d = self._dt.date(2026, 3, 10)
        got = {(2026, 2): 0.0, (2026, 3): 1.0, (2027, 2): 1.0, (2027, 3): 3.0,
               (2028, 8): 3.0, (2028, 9): 2.0, (2029, 8): 2.0, (2029, 9): 1.0,
               (2030, 8): 1.0, (2030, 9): 0.0}
        for (y, m), want in got.items():
            self.assertEqual(card.olim_points(d, y, m)[0], want, (y, m))
        self.assertEqual(card.olim_points(d, 2026, 3)[1], card.BY_LAW)

    def test_soldier_window(self):
        d = self._dt.date(2026, 1, 20)
        self.assertEqual(card.discharged_soldier_points(d, True, 2026, 1)[0], 0.0)
        self.assertEqual(card.discharged_soldier_points(d, True, 2026, 2)[0], 2.0)
        self.assertEqual(card.discharged_soldier_points(d, False, 2029, 1)[0], 1.0)
        self.assertEqual(card.discharged_soldier_points(d, False, 2029, 2)[0], 0.0)
        self.assertEqual(card.discharged_soldier_points(d, None, 2026, 5)[1], card.MANUAL)

    def test_wrapper_adds_to_base_and_downgrades_status(self):
        y = {"aliyah_date": "2026-03-10"}
        r = card.points_from_form101(2026, True, "F", y, 4)
        self.assertEqual(r[0], 3.75)
        self.assertEqual(r[1], card.BY_LAW)
        both = dict(y, discharge_date="2026-01-31", soldier_full_service=True)
        self.assertEqual(card.points_from_form101(2026, True, "M", both, 4)[0], 5.25)

    def test_without_month_shows_base_only_with_note(self):
        r = card.points_from_form101(2026, True, "F", {"aliyah_date": "2026-03-10"})
        self.assertEqual(r[0], 2.75)
        self.assertIn("לא נכללות", r[2])

    def test_bad_date_is_manual(self):
        r = card.points_from_form101(2026, True, "F", {"aliyah_date": "garbage"}, 4)
        self.assertEqual(r[1], card.MANUAL)


class AnnualCredits(unittest.TestCase):
    def test_degree_schedule(self):
        d = [{"kind": "first", "study_years": 4, "completion_year": 2024}]
        self.assertEqual(card.degree_points(d, 2024)[0], 0.0)
        self.assertEqual(card.degree_points(d, 2025)[0], 1.0)
        self.assertEqual(card.degree_points(d, 2027)[0], 1.0)      # תקרה 3 שנים
        self.assertEqual(card.degree_points(d, 2028)[0], 0.0)
        s = [{"kind": "second", "study_years": 2, "completion_year": 2025}]
        self.assertEqual(card.degree_points(s, 2026)[0], 0.5)
        self.assertEqual(card.degree_points(s, 2028)[0], 0.0)
        short = [{"kind": "first", "study_years": 2, "completion_year": 2024}]
        self.assertEqual(card.degree_points(short, 2027)[0], 0.0)

    def test_degree_manual_cases(self):
        self.assertEqual(card.degree_points([{"kind": "third", "study_years": 4, "completion_year": 2020}], 2026)[1], card.MANUAL)
        both = [{"kind": "first", "study_years": 3, "completion_year": 2024},
                {"kind": "profession", "study_years": 2, "completion_year": 2024}]
        self.assertEqual(card.degree_points(both, 2026)[1], card.MANUAL)
        self.assertEqual(card.degree_points([{"kind": "first", "study_years": None, "completion_year": 2024}], 2026)[1], card.MANUAL)

    def test_reserve_schedule(self):
        for days, want in [(29, 0.0), (30, 0.5), (39, 0.5), (40, 0.75), (49, 0.75), (50, 1.0),
                           (54, 1.0), (55, 1.25), (60, 1.5), (500, 4.0)]:
            self.assertEqual(card.reserve_points(days)[0], want, days)
        self.assertEqual(card.reserve_points(-1)[1], card.MANUAL)

    def test_wrapper_combines_annual_and_monthly(self):
        y = {"degrees": [{"kind": "first", "study_years": 3, "completion_year": 2025}],
             "reserve_days_prev_year": 50, "aliyah_date": "2026-03-10"}
        r = card.points_from_form101(2026, True, "F", y, 4)
        self.assertEqual(r[0], 5.75)       # 2.75 + 1 (תואר) + 1 (מילואים) + 1 (עולה)
        self.assertEqual(r[1], card.BY_LAW)
        r2 = card.points_from_form101(2026, True, "F", y)
        self.assertEqual(r2[0], 4.75)      # בלי חודש: ללא תוספת עולה
        self.assertIn("לא נכללות", r2[2])

    def test_manual_inner_result_propagates(self):
        r = card.points_from_form101(2026, True, "F", {"degrees": [{"kind": "x", "study_years": 1, "completion_year": 2020}]}, 4)
        self.assertIsNone(r[0]); self.assertEqual(r[1], card.MANUAL)


class DegreeSchema(unittest.TestCase):
    def test_cleaner(self):
        ok = p._clean_degrees([{"kind": "first", "study_years": 3, "completion_year": 2024}])
        self.assertEqual(ok[0]["kind"], "first")
        for bad in ("x", [{"kind": "phd", "study_years": 3, "completion_year": 2024}],
                    [{"kind": "first", "study_years": 0, "completion_year": 2024}], [1]):
            with self.assertRaises(ValueError):
                p._clean_degrees(bad)


class DisabledChildren(unittest.TestCase):
    def test_points(self):
        self.assertEqual(card.disabled_children_points(0)[0], 0.0)
        self.assertEqual(card.disabled_children_points(2)[0], 4.0)
        self.assertEqual(card.disabled_children_points(-1)[1], card.MANUAL)
        self.assertEqual(card.disabled_children_points(True)[1], card.MANUAL)

    def test_wrapper(self):
        r = card.points_from_form101(2026, True, "F", {"disabled_children": 1}, 4)
        self.assertEqual((r[0], r[1]), (4.75, card.BY_LAW))


class AlimonyAndFlags(unittest.TestCase):
    def test_alimony_adds_one_point(self):
        r = card.points_from_form101(2026, True, "M", {"alimony_ex_spouse": True}, 4)
        self.assertEqual((r[0], r[1]), (3.25, card.BY_LAW))

    def test_benef_married_no_children_matches_simulator_rule(self):
        r = card.points_from_form101(2026, True, "M", {"marital": "married", "family_flags": ["benef"]}, 4)
        self.assertEqual((r[0], r[1]), (3.25, card.VERIFIED))


if __name__ == "__main__":
    unittest.main()
