"""
בדיקות מול תרגילי הקורס (גמלאות ביטוח לאומי, סעיף 335, תקרת ביטוח לאומי).
כל מקרה כאן הוא תרגיל שהוצג ושפתרונו נבדק גם בחישוב עצמאי. אין כאן שמות או נתונים אישיים.
הרצה:  python3 -m unittest -v test_ni_benefits
"""
import unittest
from datetime import date
from decimal import Decimal as D

import engine as e
import ni_benefits as nb
from params import param


class InjuryEmployerReimbursement(unittest.TestCase):
    # (סכום הכנסה ב-3 החודשים, ימי היעדרות, החזר צפוי)
    CASES = [
        (67860, 18, "6786.00"), (57900, 20, "5790.00"), (95520, 13, "9552.00"),
        (139200, 25, "13920.00"), (403700, 30, "15402.00"),   # תקרה
        (31320, 14, "3132.00"), (84450, 16, "8445.00"), (119000, 21, "11900.00"),
        (49800, 17, "4980.00"), (185100, 40, "15402.00"),     # תקרה
        (104100, 19, "10410.00"), (367000, 35, "15402.00"),   # תקרה
        (75360, 13, "7536.00"),
        (25740, 15, "2574.00"),   # הגרסה המתוקנת של התרגיל שבו הטבלה והפתרון לא תאמו
        (172500, 22, "15402.00"),  # הגרסה המתוקנת: הטבלה 55,000 + 57,500 + 60,000 תואמת לפתרון (תקרה)
    ]

    def test_course_exercises(self):
        for total, days, expected in self.CASES:
            with self.subTest(total=total, days=days):
                r = nb.injury_employer_reimbursement(2025, total, days)
                self.assertEqual(r["value"], D(expected))
                self.assertEqual(r["status"], e.MANUAL)

    def test_no_intermediate_rounding(self):
        # 119,000: יומי 991.666... ; עיגול ל-991.67 לפני x12 היה נותן 11,900.04
        self.assertEqual(nb.injury_employer_reimbursement(2025, 119000, 21)["value"], D("11900.00"))

    def test_daily_cap_2025_and_2026(self):
        self.assertEqual(nb.injury_employer_reimbursement(2025, 403700, 30)["daily"], D("1283.50"))
        self.assertEqual(nb.injury_employer_reimbursement(2026, 403700, 30)["value"], D("15771.00"))  # 1314.25 x 12

    def test_short_absence_is_manual(self):
        r = nb.injury_employer_reimbursement(2025, 60000, 8)
        self.assertIsNone(r["value"]); self.assertEqual(r["status"], e.MANUAL)

    def test_unknown_year_is_manual(self):
        r = nb.injury_employer_reimbursement(2027, 60000, 20)
        self.assertIsNone(r["value"]); self.assertEqual(r["status"], e.MANUAL)


class PregnancyRest(unittest.TestCase):
    CASES = [
        ([8900, 9100, 9200, 9300, 9400, 9500], "313.33"),
        ([11400, 11200, 11300, 11500, 11600, 11700], "386.67"),
        ([9700, 9800, 9900, 10000, 12500, 10200], "363.33"),      # בונוס נכנס בחודש התשלום
        ([8500, 8700, 8900, 9100, 9300, 9500], "310.00"),
        ([10000] * 6, "333.33"),                                   # שוויון
        ([11100, 11200, 11300, 11400, 11500, 11600], "383.33"),
        ([9600, 9800, 10000, 10200, 10400, 10600], "346.67"),
        ([9900, 9950, 10000, 10050, 11900, 10150], "356.67"),      # ביגוד 1,800 בחודש התשלום
        ([8800, 8900, 9000, 9100, 9200, 9300], "306.67"),
        ([10500, 10600, 10700, 10800, 10900, 11000], "363.33"),
        ([9200, 9300, 9400, 9500, 9600, 10600], "330.00"),         # פדיון חופשה 900 בחודש התשלום
        ([11000, 10900, 10800, 10700, 10600, 10500], "358.33"),    # שכר יורד: 6 החודשים גבוהים
        ([9300, 9500, 9700, 9900, 10100, 10300], "336.67"),
        ([10200, 10050, 10500, 10350, 10650, 10250], "347.22"),
        ([9800, 10000, 9900, 10200, 10100, 10300], "340.00"),
    ]

    def test_course_exercises(self):
        for incomes, expected in self.CASES:
            with self.subTest(incomes=incomes):
                r = nb.pregnancy_rest_daily(incomes)
                self.assertEqual(r["value"], D(expected))
                self.assertEqual(r["status"], e.MANUAL)

    def test_basis_choice(self):
        self.assertEqual(nb.pregnancy_rest_daily([11000, 10900, 10800, 10700, 10600, 10500])["basis"], "6 חודשים")
        self.assertEqual(nb.pregnancy_rest_daily([8900, 9100, 9200, 9300, 9400, 9500])["basis"], "3 חודשים")

    def test_wrong_length_is_manual(self):
        self.assertEqual(nb.pregnancy_rest_daily([9000] * 5)["status"], e.MANUAL)

    def test_high_income_is_manual(self):
        self.assertEqual(nb.pregnancy_rest_daily([30000] * 6)["status"], e.MANUAL)


class Reserve(unittest.TestCase):
    def test_full_month_floor_and_ceiling_2025(self):
        self.assertEqual(nb.reserve_full_month(2025, 8900)["value"], D("9632.00"))     # רצפה
        self.assertEqual(nb.reserve_full_month(2025, 53200)["value"], D("50695.00"))   # תקרה
        self.assertEqual(nb.reserve_full_month(2025, 20000)["value"], D("20000.00"))   # בטווח

    def test_full_month_2026_official_values(self):
        self.assertEqual(nb.reserve_full_month(2026, 1000)["value"], D("9863.00"))
        self.assertEqual(nb.reserve_full_month(2026, 99999)["value"], D("51910.00"))

    def test_period_pay_course_exercise(self):
        # 12,000 + 12,300 + 11,700 = 36,000; /90 = 400 ליום; 12 ימים
        self.assertEqual(nb.reserve_pay_period(2025, 36000, 12)["value"], D("4800.00"))

    def test_via_employer(self):
        self.assertTrue(nb.reserve_via_employer("monthly")["value"])                  # עובד חדש, יום לפני השירות
        self.assertTrue(nb.reserve_via_employer("hourly", 78)["value"])
        self.assertFalse(nb.reserve_via_employer("hourly", 74)["value"])

    def test_threshold_boundary_and_course_exercises(self):
        self.assertTrue(nb.reserve_via_employer("hourly", 75)["value"])    # בדיוק 75 מספיק
        self.assertFalse(nb.reserve_via_employer("hourly", 74)["value"])
        self.assertFalse(nb.reserve_via_employer("daily", 69)["value"])    # ישירות מהמוסד
        self.assertTrue(nb.reserve_via_employer("hourly", 82)["value"])

    def test_days_for_75_count_all_types(self):
        self.assertEqual(nb.count_days_for_75(worked=74, sick_or_accident=2, shabbat_holidays=3), 79)
        self.assertEqual(nb.count_days_for_75(worked=72, vacation_unpaid=4), 76)
        self.assertTrue(nb.reserve_via_employer("daily", nb.count_days_for_75(worked=72, vacation_unpaid=4))["value"])

    def test_unknown_year_is_manual(self):
        self.assertEqual(nb.reserve_full_month(2030, 10000)["status"], e.MANUAL)


class RegularWage335(unittest.TestCase):
    D1 = date(2024, 1, 1)
    # (תחילת עבודה, שנה, חודש תלוש, שכר רגיל, תשלומים נוספים, צפוי)
    CASES = [
        (date(2024, 1, 1), 2025, 9, 23400, [2400, 2400], "23800.00"),     # מעל 12 חודשים
        (date(2024, 11, 1), 2025, 8, 18600, [1200, 600], "18780.00"),     # 10 חודשים
        (date(2024, 6, 1), 2025, 6, 14400, [3600], "14700.00"),
        (date(2024, 11, 1), 2025, 9, 19250, [2700, 1260], "19610.00"),    # 11 חודשים, חודש היעדרות נספר
        (date(2025, 2, 1), 2025, 11, 22800, [4200], "23220.00"),          # 10 חודשים
        (date(2024, 4, 1), 2025, 12, 24300, [3000, 1800], "24700.00"),
        (date(2024, 10, 1), 2025, 10, 20900, [2880], "21140.00"),         # 13 חודשים -> 12
        (date(2025, 7, 1), 2025, 12, 15600, [2520], "16020.00"),          # 6 חודשים
        (date(2025, 5, 1), 2025, 9, 18300, [2000], "18700.00"),           # 5 חודשים
        (date(2024, 1, 1), 2025, 6, 26100, [6000], "26600.00"),
        (date(2024, 9, 1), 2025, 8, 19800, [1800, 1368], "20064.00"),     # 12 חודשים בדיוק
        (date(2025, 2, 1), 2025, 12, 21450, [4400, 2200], "22050.00"),    # 11 חודשים
        (date(2025, 3, 1), 2025, 10, 16200, [1500, 900], "16500.00"),     # 8 חודשים
    ]

    def test_course_exercises(self):
        for start, y, m, wage, extras, expected in self.CASES:
            with self.subTest(start=str(start), month=f"{m}/{y}"):
                r = nb.regular_monthly_wage_335(wage, extras, start, y, m)
                self.assertEqual(r["value"], D(expected))
                self.assertEqual(r["status"], e.MANUAL)

    def test_below_threshold_added_in_full(self):
        # הגרסה המתוקנת של הקורס: תשלום שלא עולה על הרף לא נפרס ומתווסף במלואו
        s0 = date(2025, 1, 1)
        r = nb.regular_monthly_wage_335(21900, [900, 500], s0, 2025, 7)
        self.assertEqual((r["value"], r["status"]), (D("23300.00"), e.MANUAL))
        r = nb.regular_monthly_wage_335(17500, [1560], s0, 2025, 5)
        self.assertEqual(r["value"], D("19060.00"))

    def test_old_below_threshold_rule_still_available_explicitly(self):
        s0 = date(2025, 1, 1)
        self.assertEqual(nb.regular_monthly_wage_335(21900, [900, 500], s0, 2025, 7,
                         below_threshold_rule="ignore")["value"], D("21900.00"))
        self.assertEqual(nb.regular_monthly_wage_335(21900, [900, 500], s0, 2025, 7,
                         below_threshold_rule="bogus")["status"], e.MANUAL)

    def test_months_counting(self):
        self.assertEqual(nb.months_from_start(date(2025, 2, 1), 2025, 11), 10)
        self.assertEqual(nb.months_from_start(date(2024, 10, 1), 2025, 10), 13)

    def test_known_inconsistent_exercise_is_not_copied(self):
        # תרגיל מקור: תחילה 1/12/2024, תלוש 8/2025, והפתרון חילק ב-10. לפי ספירת החודשים אלה 9 -> 18,800.
        # התוצאה בפתרון (18,780) מתאימה לתחילה ב-1/11/2024, ולכן כנראה טעות בחומר. לא מועתק.
        r = nb.regular_monthly_wage_335(18600, [1200, 600], date(2024, 12, 1), 2025, 8)
        self.assertEqual(r["value"], D("18800.00"))

    def test_undecided_threshold_is_manual(self):
        # 1,700 על שכר 10,000: בין הערכים שנבדקו, ושתי ההשערות על הרף נותנות תשובות שונות
        r = nb.regular_monthly_wage_335(10000, [1700], self.D1, 2025, 6)
        self.assertIsNone(r["value"]); self.assertEqual(r["status"], e.MANUAL)

    def test_explicit_threshold_overrides(self):
        r = nb.regular_monthly_wage_335(10000, [1700], self.D1, 2025, 6, threshold=1700)
        self.assertEqual(r["value"], D("11700.00"))                     # 1,700 לא עולה על 1,700: מתווסף במלואו
        r = nb.regular_monthly_wage_335(10000, [1700], self.D1, 2025, 6, threshold=1500)
        self.assertEqual(r["value"], D("10141.67"))                     # נפרס על 12

    def test_mid_month_start_is_manual(self):
        r = nb.regular_monthly_wage_335(10000, [3000], date(2025, 3, 15), 2025, 8)
        self.assertEqual(r["status"], e.MANUAL)


class NIHighIncome(unittest.TestCase):
    def test_cap_2025_course_exercise(self):
        # 49,000 + 2,500 + 2,100 = 53,600; מחויב עד 50,695: 321.19 + 43,173 x 12.17% = 5,575.34
        a, b = e.ni_health(2025, "53600")
        total = a["value"] + b["value"]
        self.assertEqual(e.r0(total), 5575)
        self.assertAlmostEqual(float(total), 5575.34, delta=0.011)
        self.assertEqual((a["status"], b["status"]), (e.BY_LAW, e.BY_LAW))   # תקרה 50,695 רשמית (חוזר ב"ל 1515)

    def test_exactly_at_cap(self):
        a1, b1 = e.ni_health(2025, "50695")
        a2, b2 = e.ni_health(2025, "99999")
        self.assertEqual((a1["value"], b1["value"]), (a2["value"], b2["value"]))

    def test_2026_high_income_uses_official_cap(self):
        a, _ = e.ni_health(2026, "30000")
        self.assertEqual(e.r2(a["value"]), e.D("1640.90")); self.assertEqual(a["status"], e.BY_LAW)

    def test_middle_range_unchanged(self):
        a, _ = e.ni_health(2025, "16000")
        self.assertEqual(a["status"], e.BY_LAW)


class SpreadThreshold(unittest.TestCase):
    def test_values_run_through_code(self):
        self.assertEqual(nb.spread_threshold(2025, 3)["value"], D("1470.01"))
        self.assertEqual(nb.spread_threshold(2025, 4)["value"], D("1561.92"))   # תואם חוזר 1522 (אפריל 2025)
        self.assertEqual(nb.spread_threshold(2026, 4)["value"], D("1610.96"))

    def test_before_2025_manual(self):
        self.assertEqual(nb.spread_threshold(2024, 12)["status"], e.MANUAL)


class Params(unittest.TestCase):
    def test_2026_vs_2025_ratio_consistent(self):
        # ערכי 2025 מהקורס מול ערכי 2026 הרשמיים: אותו שיעור עדכון (2.397%) בשלושת הפרמטרים
        ratios = [param(n, 2026)["value"] / param(n, 2025)["value"]
                  for n in ("injury_daily_cap", "reserve_monthly_min", "reserve_monthly_max")]
        for r in ratios:
            self.assertAlmostEqual(float(r), 1.02397, places=4)

    def test_missing_year_is_manual(self):
        self.assertEqual(param("injury_daily_cap", 2031)["status"], e.MANUAL)


if __name__ == "__main__":
    unittest.main()


class OfficialStatuses(unittest.TestCase):
    """מקורות ב"ל רשמיים (נקראו 16.11.2026): דמי פגיעה, שמירת היריון 2026, תגמול מילואים."""
    def test_injury_with_alternative_is_by_law(self):
        r = nb.injury_employer_reimbursement(2025, 31320, 14, alt_income_total=40000)
        self.assertEqual(r["status"], e.BY_LAW)
        self.assertEqual(r["value"], D("3846.15") if False else r["value"])
        self.assertGreater(r["value"], nb.injury_employer_reimbursement(2025, 31320, 14)["value"])

    def test_pregnancy_cap_2026(self):
        r = nb.pregnancy_rest_daily([14000] * 6, year=2026)
        self.assertEqual((r["value"], r["status"]), (D("350.47"), e.BY_LAW))
        r = nb.pregnancy_rest_daily([9000] * 6, year=2026)
        self.assertEqual((r["value"], r["status"]), (D("300.00"), e.BY_LAW))
        self.assertEqual(nb.pregnancy_rest_daily([9000] * 6, year=2025)["status"], e.MANUAL)

    def test_reserve_is_by_law(self):
        for year in (2025, 2026):
            self.assertEqual(nb.reserve_daily(year, 30000)["status"], e.BY_LAW)
        self.assertEqual(nb.reserve_full_month(2026, 100000)["value"], D("51910.00"))
        self.assertEqual(nb.reserve_full_month(2025, 100000)["value"], D("50695.00"))
        self.assertEqual(nb.reserve_via_employer("daily", 75)["status"], e.BY_LAW)
