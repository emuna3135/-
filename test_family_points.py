import unittest
import card
import simulator_results_2026 as sim

FLAG = {None: (), "teen": ("teen",), "benef": ("benef",), "widower": ("widower",), "nomesh": ("nomesh",),
        "yesmesh": ("yesmesh",), "niptar": ("niptar",), "mezonut": ("mezonut",)}


def birth(age):          # age 6 מייצג את הטווח 6-17 בסימולטור; שנת מס 2026
    return 2026 - age


class FamilyPoints(unittest.TestCase):
    def test_every_simulator_result_is_reproduced(self):
        bad = []
        for g, m, flag, cust, nonc, total in sim.R:
            pts, st, _ = card.family_credit_points(2026, g, m, [birth(a) for a in cust], [birth(a) for a in nonc], (flag if isinstance(flag, tuple) else FLAG[flag]))
            if pts != total or st != card.VERIFIED:
                bad.append((g, m, flag, cust, nonc, total, pts, st))
        self.assertEqual(bad, [], f"{len(bad)} mismatches")

    def test_number_of_simulator_cases(self):
        self.assertGreaterEqual(len(sim.R), 80)

    def test_other_year_is_by_law_not_verified(self):
        pts, st, _ = card.family_credit_points(2025, "F", True, [2023])
        self.assertEqual((pts, st), (7.25, card.BY_LAW))

    def test_unexplained_cases_are_manual(self):
        for flags in (("esha",), ("niyud",), ("nidcha",)):
            self.assertEqual(card.family_credit_points(2026, "F", True, [], [], flags)[1], card.MANUAL)
        pts, st, note = card.family_credit_points(2026, "F", False, [2024], [], ())
        self.assertEqual(pts, 2.75)          # כמו הסימולטור: הילד לא נספר בלי סימון בטופס 101
        self.assertIn("לא סומן", note)

    def test_unverified_combinations_are_manual(self):
        self.assertEqual(card.family_credit_points(2026, "F", False, [], [], ("nomesh", "yesmesh"))[1], card.MANUAL)
        self.assertEqual(card.family_credit_points(2026, "F", True, [], [2024], ("mezonut",))[1], card.MANUAL)
        self.assertEqual(card.family_credit_points(2026, "F", True, [], [], ("niptar",))[1], card.MANUAL)
        self.assertEqual(card.family_credit_points(2026, "F", False, [], [], ("benef",))[1], card.MANUAL)
        self.assertEqual(card.family_credit_points(2026, "M", True, [], [], ("widower",))[1], card.MANUAL)
        self.assertEqual(card.family_credit_points(2026, "F", False, [], [2024], ())[1], card.MANUAL)

    def test_bad_gender_is_manual(self):
        self.assertEqual(card.family_credit_points(2026, None, True)[1], card.MANUAL)


if __name__ == "__main__":
    unittest.main()


class MissingInputs(unittest.TestCase):
    def test_reports_what_is_missing(self):
        self.assertEqual(card.missing_inputs("F", True, {"custody_birth_years": [2015]}), [("marital", "מצב משפחתי")])
        self.assertEqual([k for k, _ in card.missing_inputs(None, False, {})], ["gender", "worker_type"])
        self.assertEqual(card.missing_inputs("M", True, {"marital": "married", "custody_birth_years": [2015]}), [])


class ForeignWorkers(unittest.TestCase):
    """תקנות מס הכנסה (זיכויים לעובד זר), תשע"ה-2014, תקנה 3 (נבו, נוסח 2.7.2025); צו תושבי האזור תשנ"ה-1995."""
    def fp(self, *a):
        return card.foreign_points(*a)

    def test_nursing(self):
        self.assertEqual(self.fp("foreign_nursing", "M", 12, 2026)[0], 2.25)
        self.assertEqual(self.fp("foreign_nursing", "F", 12, 2026)[0], 2.75)
        self.assertAlmostEqual(self.fp("foreign_nursing", "M", 8, 2026)[0], 1.5)    # 2.25 x 8/12

    def test_legal_not_nursing(self):
        self.assertEqual(self.fp("foreign_legal", "M", 12, 2026)[0], 1.0)           # תקנה 3(א1)
        self.assertEqual(self.fp("foreign_legal", "F", 12, 2026)[0], 1.5)           # + חצי נקודה, תקנה 3(ב)

    def test_area_resident(self):
        self.assertEqual(self.fp("area_resident", "M", None, 2026)[0], 2.25)
        self.assertEqual(self.fp("area_resident", "F", None, 2026)[1], card.MANUAL)

    def test_everything_else_is_manual(self):
        self.assertEqual(self.fp("foreign_other", "M", 12, 2026)[1], card.MANUAL)
        self.assertEqual(self.fp("foreign_nursing", "M", None, 2026)[1], card.MANUAL)   # חסרים חודשי שהייה
        self.assertEqual(self.fp("foreign_nursing", "M", 12, 2018)[1], card.MANUAL)

    def test_flows_through_form101(self):
        pts, st, _ = card.points_from_form101(2026, False, "M", {"worker_type": "foreign_legal", "months_in_israel": 12})
        self.assertEqual((pts, st), (1.0, card.BY_LAW))
