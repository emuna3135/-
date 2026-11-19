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
