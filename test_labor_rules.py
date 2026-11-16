import unittest
from decimal import Decimal as D

import labor_rules as lr
from engine import COURSE, MANUAL


class Severance(unittest.TestCase):
    def test_included_and_excluded(self):
        # תרגיל עומר: יסוד 6,200 + עמלות ממוצע 2,083.33; רכב/טלפון/בונוס חד פעמי לא נכללים
        w = lr.severance_wage([("base", 6200), ("commissions_avg12", "2083.33"), ("car_maintenance", 900),
                               ("phone_upkeep", 150), ("one_time_bonus", 5000)])
        self.assertEqual(w["value"], D("8283.33"))
        self.assertEqual(w["status"], lr.BY_LAW)   # תקנות 1 ו-9 (btl.gov.il)

    def test_unknown_component_is_manual(self):
        w = lr.severance_wage([("base", 6000), ("mystery_allowance", 300)])
        self.assertIsNone(w["value"])
        self.assertEqual(w["status"], MANUAL)

    def test_pay_is_wage_times_months_over_12(self):
        self.assertEqual(lr.severance_pay(6550, 36)["value"], D(19650))   # תרגיל קרן
        self.assertIsNone(lr.severance_pay(6550, 36.5)["value"])           # חודש חלקי לא נלמד


class AdvanceNotice(unittest.TestCase):
    def test_daily_hourly_year_one(self):
        self.assertEqual(lr.advance_notice_days_resignation(5, "daily_hourly")["value"], 5)
        self.assertEqual(lr.advance_notice_days_resignation(12, "daily_hourly")["value"], 12)   # היום האחרון של שנה 1

    def test_daily_hourly_year_two_and_three(self):
        self.assertEqual(lr.advance_notice_days_resignation(13, "daily_hourly")["value"], 14)
        self.assertEqual(lr.advance_notice_days_resignation(16, "daily_hourly")["value"], 16)   # 14 + 2
        self.assertEqual(lr.advance_notice_days_resignation(26, "daily_hourly")["value"], 22)   # 21 + 1

    def test_daily_hourly_after_three_years(self):
        self.assertEqual(lr.advance_notice_days_resignation(37, "daily_hourly")["value"], 30)

    def test_monthly_follows_the_law_not_the_exercise_table(self):
        f = lambda m: lr.advance_notice_days_resignation(m, "monthly")["value"]
        self.assertEqual(f(4), 4)              # דוגמה מהמקור: 4 חודשים = 4 ימים
        self.assertEqual(f(6), 6)
        self.assertEqual(f(7), D("8.5"))       # 6 + 2.5
        self.assertEqual(f(11), D("18.5"))     # 6 + 2.5*5
        self.assertEqual(f(12), 30)

    def test_status_is_by_law_with_note_on_secondary_source(self):
        r = lr.advance_notice_days_resignation(4, "monthly")
        self.assertEqual(r["status"], lr.BY_LAW)
        self.assertIn("advance_notice", lr.SOURCES)

    def test_unknown_pay_type_is_manual(self):
        self.assertEqual(lr.advance_notice_days_resignation(4, "weekly")["status"], MANUAL)


class SickPay(unittest.TestCase):
    def test_schedule(self):
        self.assertEqual([lr.sick_pay_percent(d) for d in (1, 2, 3, 4, 10)],
                         [0, D("0.5"), D("0.5"), 1, 1])

    def test_total(self):
        self.assertEqual(lr.sick_pay(300, 1)["value"], 0)
        self.assertEqual(lr.sick_pay(300, 3)["value"], D(300))        # 0 + 150 + 150
        self.assertEqual(lr.sick_pay(300, 5)["value"], D(900))        # + 300 + 300

    def test_child_quota(self):
        self.assertEqual(lr.child_sick_days_remaining("single_parent", 5, 10)["value"], 11)
        self.assertEqual(lr.child_sick_days_remaining("other_parent", 8, 10)["value"], 0)
        self.assertEqual(lr.child_sick_days_remaining("other_parent", 20, 10)["value"], 0)
        self.assertEqual(lr.child_sick_days_remaining("single_parent", 0, 16)["value"], 0)
        self.assertIsNone(lr.child_sick_days_remaining("x", 0, 5)["value"])


class AnnualLeave(unittest.TestCase):
    def test_proportional_values_from_exercises(self):
        # בסיס 16 (לדוגמה) ימי עבודה -> ללא שברי יום; הערכים אומתו מול פתרונות התרגילים
        cases = [("15.84", 15), ("12.75", 12), ("17.91", 17), ("22.655", 22), ("10.89", 10),
                 ("10.56", 10), ("6.4", 6), ("14", 14)]
        for exact, expected in cases:
            with self.subTest(exact=exact):
                # בסיס 100 וימים = exact -> base*days/200 = exact/2 ... במקום זה בודקים ישירות את הרצפה
                self.assertEqual(lr._floor(D(exact)), expected)

    def test_formula(self):
        self.assertEqual(lr.annual_leave_proportional(16, 100)["value"], 8)
        self.assertEqual(lr.annual_leave_proportional(16, 199)["value"], 15)    # 15.92
        self.assertEqual(lr.annual_leave_proportional(16, 200)["value"], 16)
        self.assertEqual(lr.annual_leave_proportional(14, 300)["value"], 14)

    def test_threshold_240_when_not_continuous(self):
        self.assertEqual(lr.annual_leave_proportional(12, 180, continuous_year=False)["value"], 9)   # 12*180/240
        self.assertEqual(lr.annual_leave_proportional(12, 180)["value"], 10)    # 10.8 -> 10, דוגמת המקור

    def test_base_table_unresolved(self):
        self.assertEqual(lr.annual_leave_proportional(None, 100)["status"], MANUAL)


class AnnualLeaveStatute(unittest.TestCase):
    def test_table(self):
        got = [lr.annual_leave_statutory_days(y)["value"] for y in (1, 5, 6, 7, 8, 13, 14, 20)]
        self.assertEqual(got, [16, 16, 18, 21, 22, 27, 28, 28])

    def test_is_by_law_with_source(self):
        self.assertEqual(lr.annual_leave_statutory_days(1)["status"], lr.BY_LAW)
        self.assertIn("annual_leave", lr.SOURCES)

    def test_exercise_values_come_from_statutory_base(self):
        base = lr.annual_leave_statutory_days(1)["value"]            # 16, כמו בתרגילים
        self.assertEqual(lr.annual_leave_proportional(base, 198)["value"], 15)    # 15.84 -> 15


class Recreation(unittest.TestCase):
    def test_days_table(self):
        got = [lr.recreation_days(y) for y in (1, 2, 3, 4, 10, 11, 15, 16, 19, 20, 30)]
        self.assertEqual(got, [5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10])

    def test_pay_with_reductions(self):
        self.assertEqual(lr.recreation_pay_2025(1)["value"], D(5 * 418 - 418))
        self.assertEqual(lr.recreation_pay_2025(1, reduction="partial")["value"], D("5") * 418 - D(209))
        self.assertEqual(lr.recreation_pay_2025(4, fraction="0.5")["value"], (D(7 * 418) - 418) / 2)

    def test_fraction_scales_both(self):
        self.assertEqual(lr.recreation_pay_2025(2, fraction="0.25")["value"], (D(6 * 418) - 418) * D("0.25"))

    def test_exercise_rena(self):
        # תרגיל דמי הבראה, רנה: משרה מלאה, שנה ראשונה, בלי הפחתה חלקית -> 5*418 - 418
        self.assertEqual(lr.recreation_pay_2025(1)["value"], D(1672))

    def test_partial_reduction_threshold_scales_with_position(self):
        self.assertEqual(lr.recreation_reduction_type(6150), "partial")
        self.assertEqual(lr.recreation_reduction_type(6151), "full")
        self.assertEqual(lr.recreation_reduction_type(3075, "0.5"), "partial")
        self.assertEqual(lr.recreation_reduction_type(3076, "0.5"), "full")

    def test_status_by_law_after_days_table_verified(self):
        self.assertEqual(lr.recreation_pay_2025(1)["status"], lr.BY_LAW)
        self.assertIn("recreation", lr.SOURCES)

    def test_bad_reduction(self):
        self.assertIsNone(lr.recreation_pay_2025(1, reduction="odd")["value"])


class HourlyPay(unittest.TestCase):
    def test_no_overtime(self):
        r = lr.hourly_pay(40, [("08:00", "16:00")] * 5, "0.75")        # 7.25 נטו ליום, 36.25 שעות
        self.assertEqual(r["net_hours"], D("36.25"))
        self.assertEqual(r["pay"], D("1450"))

    def test_daily_overtime_two_tiers(self):
        # 08:00-20:00 = 12 - 0.75 = 11.25 נטו; מעל 8.6: 2.65 -> 2 ב-125% ו-0.65 ב-150%
        r = lr.hourly_pay(100, [("08:00", "20:00")], "0.75")
        self.assertEqual(r["hours_125"], D(2))
        self.assertEqual(r["hours_150"], D("0.65"))
        self.assertEqual(r["pay"], D("11.25") * 100 + D("0.25") * 2 * 100 + D("0.5") * D("0.65") * 100)

    def test_weekly_overtime_first_two_hours(self):
        r = lr.hourly_pay(100, [("08:00", "17:00")] * 5 + [("08:00", "10:00")], "0.75")
        # 5 * 8.25 + 1.25 = 42.5 -> 0.5 מעל 42 ב-125%
        self.assertEqual(r["weekly_ot_hours"], D("0.5"))
        self.assertEqual(r["hours_125"], D("0.5"))

    def test_weekly_overtime_beyond_two_hours_is_manual(self):
        r = lr.hourly_pay(100, [("08:00", "17:00")] * 6, "0.75")        # 49.5 נטו
        self.assertIsNone(r["pay"])
        self.assertEqual(r["status"], MANUAL)

    def test_round_half_up_only_at_end(self):
        self.assertEqual(lr.r0(D("4009.50")), 4010)


class WageProtection(unittest.TestCase):
    def test_protected_is_min_of_benefit_and_80_percent(self):
        r = lr.wage_attachment(wage=10000, benefit=4049, attachment_amount=9000)
        self.assertEqual(r["protected"], D(4049))
        self.assertEqual(r["max_attachable"], D(5951))
        self.assertEqual(r["actual_attachment"], D(5951))

    def test_low_wage_protects_80_percent(self):
        r = lr.wage_attachment(wage=3000, benefit=4049, attachment_amount=5000)
        self.assertEqual(r["protected"], D(2400))
        self.assertEqual(r["actual_attachment"], D(600))

    def test_small_attachment_not_exceeded(self):
        self.assertEqual(lr.wage_attachment(10000, 2076, 500)["actual_attachment"], D(500))

    def test_direct_payments_first(self):
        r = lr.wage_attachment(wage=10000, benefit=2000, attachment_amount=9999, direct_payments=3000)
        self.assertEqual(r["remaining_wage"], D(7000))
        self.assertEqual(r["actual_attachment"], D(5000))


class Insolvency(unittest.TestCase):
    def test_caps_2025(self):
        self.assertEqual(lr.insolvency_benefit_2025(200000, 50000)["value"], D(131807 + 20278))
        self.assertEqual(lr.insolvency_benefit_2025(50000, 5000)["value"], D(55000))
        self.assertEqual(lr.insolvency_benefit_2025(0, 30000)["value"], D(20278))


class VerifiedStatuses(unittest.TestCase):
    def test_insolvency_caps_are_13_and_2_times_basic_amount(self):
        basic = D(131807) / 13
        self.assertEqual(basic, D(10139))
        self.assertEqual(D(20278), basic * 2)
        self.assertEqual(lr.insolvency_benefit_2025(1, 1)["status"], lr.BY_LAW)

    def test_old_age_by_law_and_exemption_groups_from_btl(self):
        self.assertEqual(lr.old_age_qualifying(60, 0)["status"], lr.BY_LAW)
        for g in ("divorced", "agunah"):
            self.assertIn(g, lr.OLD_AGE_EXEMPTION_GROUPS)

    def test_wage_protection_matches_statute_section_8(self):
        r = lr.wage_attachment(3000, 4049, 5000)         # קצבה > 80% מהשכר -> מוגן 80%
        self.assertEqual(r["protected"], D(2400))
        self.assertEqual(r["status"], lr.BY_LAW)

    def test_sick_pay_and_severance_amount_by_law(self):
        self.assertEqual(lr.sick_pay(300, 3)["status"], lr.BY_LAW)
        self.assertEqual(lr.severance_pay(6000, 12)["status"], lr.BY_LAW)

    def test_severance_wage_by_regulation(self):
        self.assertEqual(lr.severance_wage([("base", 6000)])["status"], lr.BY_LAW)
        self.assertEqual(lr.severance_wage([("base", 6000), ("fixed_premium", 500)])["status"], MANUAL)
        self.assertIn("severance_wage", lr.SOURCES)

    def test_global_overtime_is_manual_not_guessed(self):
        r = lr.severance_wage([("base", 6000), ("global_overtime", 1000)])
        self.assertEqual(r["status"], MANUAL)

    def test_unemployment_eligibility_by_law(self):
        self.assertEqual(lr.unemployment_eligibility(True)["status"], lr.BY_LAW)


class OldAge(unittest.TestCase):
    def test_alternative_a_and_b(self):
        self.assertTrue(lr.old_age_qualifying(60, 70)["qualifies"])
        self.assertTrue(lr.old_age_qualifying(30, 144)["qualifies"])
        self.assertFalse(lr.old_age_qualifying(59, 143)["qualifies"])

    def test_alternative_c_is_strict(self):
        self.assertTrue(lr.old_age_qualifying(0, 100, 100, 99, is_woman=True)["qualifies"])
        self.assertFalse(lr.old_age_qualifying(0, 100, 100, 100, is_woman=True)["qualifies"])
        self.assertFalse(lr.old_age_qualifying(0, 50, 50, 10, is_woman=True)["qualifies"])   # פחות מ-60
        self.assertFalse(lr.old_age_qualifying(0, 100, 100, 99, is_woman=False)["qualifies"])

    def test_possible_exemption_is_manual_not_guessed(self):
        r = lr.old_age_qualifying(10, 20, exemption_flags=("single_woman_at_retirement",))
        self.assertIsNone(r["qualifies"])
        self.assertEqual(r["status"], MANUAL)


class Unemployment(unittest.TestCase):
    def test_claim_required(self):
        self.assertFalse(lr.unemployment_eligibility(False)["eligible"])

    def test_employee_initiated_unpaid_leave(self):
        self.assertFalse(lr.unemployment_eligibility(True, employee_initiated_unpaid_leave=True)["eligible"])

    def test_employer_failure_needs_proof(self):
        self.assertIsNone(lr.unemployment_eligibility(True, employer_did_not_pay_ni=True)["eligible"])
        self.assertTrue(lr.unemployment_eligibility(True, employer_did_not_pay_ni=True, work_proven=True)["eligible"])

    def test_abroad_noted(self):
        self.assertIn("חו\"ל", lr.unemployment_eligibility(True, abroad_days=5)["note"])


class Youth(unittest.TestCase):
    def test_adult_no_checks(self):
        self.assertEqual(lr.youth_work_check(18), ([], []))

    def test_violations(self):
        v, _ = lr.youth_work_check(17, weekly_rest_hours=30, overtime=True, works_on_weekly_rest_day=True)
        self.assertEqual(len(v), 4)         # כולל חוסר אישור רפואי

    def test_clean_case(self):
        v, m = lr.youth_work_check(17, weekly_rest_hours=36, medical_approval=True)
        self.assertEqual((v, m), ([], []))

    def test_night_work_is_manual(self):
        _, m = lr.youth_work_check(17, medical_approval=True, night_work=True)
        self.assertEqual(len(m), 1)

    def test_age_14_rules_from_statute(self):
        v, m = lr.youth_work_check(14, in_school_vacation=True, medical_approval=True)
        self.assertEqual((v, len(m)), ([], 1))                 # בחופשה: עבודה קלה בלבד -> בדיקה ידנית
        v, _ = lr.youth_work_check(14, in_school_vacation=False, medical_approval=True)
        self.assertEqual(len(v), 1)                            # מחוץ לחופשה: אסור

    def test_age_15_needs_manual_check(self):
        v, m = lr.youth_work_check(15, medical_approval=True)
        self.assertEqual((v, len(m)), ([], 1))

    def test_hours_limits(self):
        v, _ = lr.youth_work_check(17, medical_approval=True, daily_hours=8.5)
        self.assertEqual(len(v), 1)
        v, _ = lr.youth_work_check(17, medical_approval=True, weekly_hours=41)
        self.assertEqual(len(v), 1)
        self.assertEqual(lr.youth_work_check(17, medical_approval=True, daily_hours=8, weekly_hours=40), ([], []))

    def test_under_14_in_vacation_forbidden(self):
        v, _ = lr.youth_work_check(13, in_school_vacation=True, medical_approval=True)
        self.assertEqual(len(v), 1)


if __name__ == "__main__":
    unittest.main()


class UnemploymentDuration(unittest.TestCase):
    """משך דמי אבטלה לפי btl.gov.il tkufat_zakaut.aspx (נקרא 16.11.2026)."""
    def test_table(self):
        import labor_rules as lr
        cases = [(24, 0, 50), (24, 3, 138), (26, 2, 67), (30, 1, 100), (34, 3, 138), (35, 2, 138), (35, 3, 175), (44, 0, 138), (45, 0, 175), (60, 5, 175)]
        for age, dep, days in cases:
            r = lr.unemployment_max_days(age, dep)
            self.assertEqual(r["value"], days, (age, dep))
            self.assertEqual(r["status"], lr.BY_LAW)

    def test_women_57_67(self):
        import labor_rules as lr
        self.assertEqual(lr.unemployment_max_days(60, 0, True)["value"], 300)
        self.assertEqual(lr.unemployment_max_days(67, 0, True)["value"], 175)

    def test_bad_input_manual(self):
        import labor_rules as lr
        self.assertEqual(lr.unemployment_max_days(None, 0)["status"], lr.MANUAL)


class UnemploymentAmount(unittest.TestCase):
    """שורות הטבלה ב-btl.gov.il sum.aspx (נקרא 16.11.2026); שכר חודשי -> 6 חודשים = x6, /150."""
    def test_28_plus(self):
        import labor_rules as lr
        rows = {3000: "96.00", 4000: "128.00", 5000: "160.00", 6000: "182.25", 8000: "221.81", 10000: "257.81",
                12000: "284.06", 20000: "380.06", 33000: "536.06"}
        for m, v in rows.items():
            r = lr.unemployment_daily_benefit(m * 6, 30)
            self.assertEqual(str(r["value"]), v, m)
            self.assertEqual(r["status"], lr.BY_LAW)

    def test_under_28(self):
        import labor_rules as lr
        rows = {3000: "72.00", 6000: "137.50", 8000: "169.06", 10000: "197.06", 28000: "378.56"}
        for m, v in rows.items():
            self.assertEqual(str(lr.unemployment_daily_benefit(m * 6, 25)["value"]), v, m)

    def test_caps(self):
        import labor_rules as lr
        self.assertEqual(str(lr.unemployment_daily_benefit(40000 * 6, 40)["value"]), "550.76")
        self.assertEqual(str(lr.unemployment_daily_benefit(40000 * 6, 40, 126)["value"]), "367.17")

    def test_bad_input(self):
        import labor_rules as lr
        self.assertIsNone(lr.unemployment_daily_benefit(-1, 30)["value"])


class AnnualLeaveFiveDay(unittest.TestCase):
    def test_table(self):
        import labor_rules as lr
        for y in (1, 2, 4, 5):
            r = lr.annual_leave_net_days_five_day_week(y)
            self.assertEqual((r["value"], r["status"]), (12, lr.BY_LAW), y)
        for y, yr in ((6, 2026), (8, 2026), (1, 2015)):
            r = lr.annual_leave_net_days_five_day_week(y, yr)
            self.assertIsNone(r["value"])
            self.assertEqual(r["status"], MANUAL)

    def test_year9_is_23(self):
        import labor_rules as lr
        r = lr.annual_leave_net_days_five_day_week(9)
        self.assertEqual((r["value"], r["status"]), (23, lr.BY_LAW))

    def test_hourly_defaults_are_manual(self):
        import labor_rules as lr
        r = lr.hourly_pay(50, [("08:00", "17:00")], 1)
        self.assertEqual(r["status"], MANUAL)
        r = lr.hourly_pay(50, [("08:00", "17:00")], 1, daily_threshold=lr.D(8), weekly_threshold=lr.D(42))
        self.assertEqual(r["status"], lr.BY_LAW)
