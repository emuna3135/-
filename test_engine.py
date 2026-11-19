import unittest
from decimal import Decimal as D
import engine as e
from test_payslips import NI_2025_CASES, KNOWN_UNEXPLAINED


class CarYear2026Tests(unittest.TestCase):
    def test_2026_cap_and_reductions(self):
        e_ = e
        self.assertEqual(e_.car_benefit(900000, 'regular', year=2026)['value'], e_.car_benefit(596860, 'regular', year=2026)['value'])
        self.assertEqual(e_.car_benefit(596860, 'regular', year=2026)['value'] - e_.car_benefit(596860, 'electric', year=2026)['value'], 1380)
        self.assertEqual(e_.car_benefit(596860, 'regular', year=2026)['value'] - e_.car_benefit(596860, 'plugin', year=2026)['value'], 1150)
        self.assertEqual(e_.car_benefit(596860, 'regular', year=2026)['value'] - e_.car_benefit(596860, 'hybrid', year=2026)['value'], 580)

    def test_other_years_manual(self):
        self.assertIsNone(e.car_benefit(300000, 'regular', year=2024)['value'])


class NI(unittest.TestCase):
    def test_verified_against_slips(self):
        for name, y, m, g, bl, h in NI_2025_CASES:
            with self.subTest(name):
                a, b = e.ni_health(y, g, m)
                self.assertEqual((e.r2(a["value"]), e.r2(b["value"])), (D(bl), D(h)))
                self.assertEqual(a["status"], e.VERIFIED)

    def test_known_unexplained_slips_stay_flagged(self):
        # תלושים שהמנוע שונה מהם: לא נסתרים. אם ייסגרו, יש להעביר ל-NI_2025_CASES
        for name, y, m, g, bl, h in KNOWN_UNEXPLAINED:
            with self.subTest(name):
                a, b = e.ni_health(y, g, m)
                self.assertNotEqual((e.r2(a["value"]), e.r2(b["value"])), (D(bl), D(h)))

    def test_private_employer_slips_shekel_rounding(self):
        # מעסיק פרטי: המערכת שמדפיסה מעגלת לשקל. המנוע (אגורות) מעוגל לשקל חייב להתאים
        for name, y, g, bl, h in [("מאי 2026", 2026, "13000.10", 451, 523), ("יולי 2026", 2026, "14500.00", 556, 600),
                                  ("אוגוסט 2026", 2026, "14500.00", 556, 600), ("נובמבר 2025", 2025, "14647.00", 577, 611)]:
            with self.subTest(name):
                a, b = e.ni_health(y, g)
                self.assertEqual((e.r0(a["value"]), e.r0(b["value"])), (bl, h))
                self.assertEqual(a["status"], e.VERIFIED)

    def test_above_verified_is_by_law(self):
        a, _ = e.ni_health(2025, "16000")
        self.assertEqual(a["status"], e.BY_LAW)

    def test_high_salary_2025_uses_course_cap(self):
        # עד עכשיו MANUAL. מעל 20,000 ב-2025 מחושב עד תקרת 50,695 מהקורס, בסטטוס COURSE
        a, _ = e.ni_health(2025, "30000")
        self.assertIsNotNone(a["value"]); self.assertEqual(a["status"], e.BY_LAW)   # תקרה 50,695 רשמית (חוזר ב"ל 1515)

    def test_high_salary_2026_uses_official_cap(self):
        # תקרה 51,910 ב-2026 (ביטוח לאומי). 30,000: 7,703*1.04% + 22,297*7% ; בריאות 7,703*3.23% + 22,297*5.17%
        a, h = e.ni_health(2026, "30000")
        self.assertEqual((e.r2(a["value"]), e.r2(h["value"])), (e.D("1640.90"), e.D("1401.56")))   # ללא עיגול באחסון
        self.assertEqual(a["status"], e.BY_LAW)

    def test_income_above_2026_cap_is_capped(self):
        a, _ = e.ni_health(2026, "60000")
        self.assertEqual(e.r2(a["value"]), e.D("3174.60"))

    def test_unsupported_year_manual(self):
        a, _ = e.ni_health(2023, "9000")
        self.assertEqual(a["status"], e.MANUAL)


class PensionFloor(unittest.TestCase):
    def test_at_floor_ok(self):
        self.assertEqual(e.pension_floor_check("0.06", "0.065", "0.06"), [])

    def test_below_floor_flagged(self):
        self.assertEqual(e.pension_floor_check("0.05", "0.065", "0.0833"), ["employee"])
        self.assertEqual(e.pension_floor_check("0.06", "0.06", "0.05"), ["employer", "severance"])


class Tax(unittest.TestCase):
    def test_no_coordination_verified(self):
        t, _ = e.income_tax(2025, 3, "no_coordination", "11207.72", 2.75, e.ZERO_PREV, 0, 0)
        self.assertEqual((t["value"], t["status"]), (5268, e.VERIFIED))

    def test_unsupported_year_not_guessed(self):
        t, _ = e.income_tax(2027, 4, "cumulative", "10800", 2.75, e.ZERO_PREV, 0, 0)
        self.assertIsNone(t["value"]); self.assertEqual(t["status"], e.MANUAL)

    def test_private_employer_slips_2025_2026(self):
        # חמישה תלושים של עובד אצל מעסיק פרטי (שכר 14,000+נסיעות): מס מצטבר מודפס מול המנוע, סטייה עד 2 ש"ח
        cases = [("מאי 2026", 2026, 5, 71069, 4110, 5278, 5),
                 ("יוני 2026", 2026, 6, 92303, 5354, 7737, 6),
                 ("יולי 2026", 2026, 7, 106803, 6194, 8849, 7),
                 ("אוגוסט 2026", 2026, 8, 121303, 7034, 9962, 8),
                 ("נובמבר 2025 (חודש ראשון חלקי 17/25)", 2025, 11, 154870, 8942, 11810, "10.68")]
        for name, y, m, g, dep, tax, w in cases:
            with self.subTest(name):
                prev = {"cum_taxable": D(0), "cum_tax": 0, "cum_deposits": D(0), "cum_life": D(0),
                        "cum_weight": D(0)}
                _, c = e.income_tax(y, m, "cumulative", g, 2.75, prev, dep, 0, weight=D(str(w)))
                self.assertLessEqual(abs(c["cum_tax"] - tax), 2)

    def test_2025_matches_official_course_table(self):
        # בדיקת חישוב עצמאית של המס המצטבר ממדרגות הפקודה (לוח עזר 2025 של רשות המסים): המס המצטבר בסוף כל מדרגה (חודש אחד)
        for income, expected in [("7010", "701.00"), ("10060", "1128.00"), ("16150", "2346.00"),
                                 ("22440", "4295.90"), ("46690", "12783.40")]:
            with self.subTest(income):
                self.assertEqual(e.tax_before_credits(income, 1, 2025), D(expected))

    def test_pension_cap_matches_official_ceiling(self):
        # תקרת הכנסה מזכה 116,400 לשנה x 7% = 8,148 לשנה = 679 לחודש
        self.assertEqual(D("116400") * D("0.07") / 12, e.PENSION_CREDIT_CAP_MONTHLY)

    def test_2026_brackets_extended_20_percent(self):
        # רשות המסים: ב-2026 מדרגת ה-20% מתרחבת עד 19,000 לחודש (ב-2025: 16,150)
        b25 = e.tax_before_credits("20000", 1, 2025)
        b26 = e.tax_before_credits("20000", 1, 2026)
        self.assertEqual(b26, D("701") + D("427") + D("8940") * D("0.20") + D("1000") * D("0.31"))
        self.assertLess(b26, b25)
        # עד 16,150 אין שינוי
        self.assertEqual(e.tax_before_credits("14500", 1, 2025), e.tax_before_credits("14500", 1, 2026))

    def test_pension_credit_cap(self):
        # הפקדות מעל 679 לחודש לא מזכות: הפקדה 1,000 נותנת אותו זיכוי כמו 679
        a, _ = e.income_tax(2025, 1, "cumulative", "14500", 2.75, e.ZERO_PREV, 1000, 0)
        b, _ = e.income_tax(2025, 1, "cumulative", "14500", 2.75, e.ZERO_PREV, 679, 0)
        self.assertEqual(a["value"], b["value"])

    def test_annual_2025_matches_form_106(self):
        # טופס 106 לשנת 2025: מס 9,482; קיצבה 35% = 2,701; ביטוח חיים 186; 2.75 נקודות
        taxable = D("145714") - D("31.89") * 12   # בניכוי החזר טלפון פטור
        t, cum = e.income_tax(2025, 12, "cumulative", taxable, 2.75, e.ZERO_PREV, 2701, 186)
        self.assertLessEqual(abs(t["value"] - 9482), 2)
        self.assertEqual(t["status"], e.ACCOUNTANT)

    def test_credit_never_exceeds_tax(self):
        t, _ = e.income_tax(2025, 1, "cumulative", "3000", 2.75, e.ZERO_PREV, 180, 0)
        self.assertEqual(t["value"], 0)

    def test_refund_month_flagged(self):
        prev = {"cum_taxable": D("30000"), "cum_tax": 6000, "cum_deposits": D(0), "cum_life": D(0)}
        t, _ = e.income_tax(2025, 3, "cumulative", "3000", 2.75, prev, 0, 0)
        self.assertLess(t["value"], 0); self.assertIn("החזר", t["note"])


class Benefits(unittest.TestCase):
    def test_phone_course_exercise(self):
        # (נגזר מתרגיל; הכלל נתמך עתה בתקנההוצאה 79.20, השתתפות 15% -> שווי 27.72, ברוטו למס 23,787.72
        v = e.phone_benefit("79.20", "0.15")["value"]
        self.assertEqual(v, D("27.72")); self.assertEqual(D("23760") + v, D("23787.72"))

    def test_phone_course_exercise_2_no_participation(self):
        # (נגזר מתרגיל; הכלל נתמך עתה בתקנההוצאה 54.00, בלי השתתפות, רכב תפעולי -> ברוטו למס 22,567
        v = e.phone_benefit("54.00", "0")["value"]
        car = e.car_benefit(0, "regular", operational=True)["value"]
        self.assertEqual(D("22540") + v + car, D("22567"))

    def test_phone_course_exercise_3_cap_and_fixed_participation(self):
        # הוצאה 240: חצי = 120, תקרה 115, השתתפות 50 -> 65; ברוטו למס 26,365
        v = e.phone_benefit("240", "0", "50")["value"]
        self.assertEqual(v, D("65")); self.assertEqual(D("26300") + v, D("26365"))

    def test_phone_course_exercise_4_and_heavy_van(self):
        # הוצאה 70, השתתפות 50% -> 0; טנדר 4,200 ק"ג אינו רכב -> 0; ברוטו למס 21,900
        ph = e.phone_benefit("70", "0.5")["value"]
        van = e.car_benefit(250000, "regular", gross_weight_kg=4200)["value"]
        self.assertEqual((ph, van), (0, 0))
        self.assertGreater(e.car_benefit(250000, "regular", gross_weight_kg=3500)["value"], 0)  # בדיוק 3,500 עדיין רכב

    def test_operational_car_conditions(self):
        # תקנה 1 לתקנות ניכוי הוצאות רכב: כל התנאים מצטברים
        self.assertTrue(e.is_operational_car(True, False))        # רן, ליאת, מור: נשאר במקום העבודה
        self.assertFalse(e.is_operational_car(True, True))        # ענת: נלקח הביתה בסוף היום
        self.assertFalse(e.is_operational_car(False, False))      # שימוש פרטי
        self.assertFalse(e.is_operational_car(True, False, workplace_is_residence=True))
        self.assertFalse(e.is_operational_car(True, None))        # מידע חסר: לא מניחים

    def test_works_committee_is_manual_without_primary_source(self):
        # נוסח חוזר 34/93 לא נמצא: אין חישוב ואין ניחוש
        for spec in (True, False, None):
            r = e.works_committee_benefit("340", spec)
            self.assertIsNone(r["value"]); self.assertEqual(r["status"], e.MANUAL)

    def test_recuperation_2025(self):
        self.assertEqual(e.recuperation_pay(2025, 5, reduced_partial=False)["value"], D("1672"))  # רנה
        self.assertEqual(e.recuperation_pay(2025, 5, reduced_partial=True)["value"], D("1881"))  # ליבי (תרגיל)
        self.assertIsNone(e.recuperation_pay(2025, 5)["value"])
        self.assertIsNone(e.recuperation_pay(2026, 5, reduced_partial=False)["value"])

    def test_recuperation_second_year(self):
        d = e.recuperation_days(2)["value"]                      # דנה: 6 ימים
        self.assertEqual(e.recuperation_pay(2025, d, reduced_partial=False)["value"], D("2090"))
        self.assertEqual(e.recuperation_days(1)["value"], D(5))
        self.assertEqual(e.recuperation_days(4)["value"], D(7))
        self.assertEqual(e.recuperation_pay(2025, D(7), reduced_partial=False)["value"], D("2508"))  # יעל
        self.assertEqual(e.recuperation_days(11)["value"], D(8))
        self.assertEqual(e.recuperation_pay(2025, D(8), reduced_partial=False)["value"], D("2926"))  # מיכל
        self.assertEqual(e.recuperation_days(16)["value"], D(9))
        self.assertEqual(e.recuperation_pay(2025, D(9), reduced_partial=False)["value"], D("3344"))  # אורית
        self.assertEqual(e.recuperation_days(21)["value"], D(10))
        self.assertEqual(e.recuperation_pay(2025, D(10), reduced_partial=False)["value"], D("3762"))  # שרה
        self.assertIsNone(e.recuperation_days(0)["value"])
        # שנה 1, חצי משרה, בהפחתה חלקית: 1,045 פחות 104.50 = 940.50
        self.assertEqual(e.recuperation_pay(2025, D(5), job_fraction="0.5", reduced_partial=True)["value"], D("940.50"))
        # שנה 1, חצי משרה, בלי הפחתה חלקית: 1,045 פחות 209 = 836
        self.assertEqual(e.recuperation_pay(2025, D(5), job_fraction="0.5", reduced_partial=False)["value"], D("836"))
        # שנה 6, 80% משרה: 7x418x0.8 פחות 334.40 = 2,006.40
        d6 = e.recuperation_days(6)["value"]
        self.assertEqual(e.recuperation_pay(2025, d6, job_fraction="0.8", reduced_partial=False)["value"], D("2006.40"))
        # שנה 20, חצי משרה: 10x418x0.5 פחות 209 = 1,881
        d20 = e.recuperation_days(20)["value"]
        self.assertEqual(e.recuperation_pay(2025, d20, job_fraction="0.5", reduced_partial=False)["value"], D("1881"))
        # שנה 12, 9 חודשים: 6 ימים = 2,508 פחות 313.50 = 2,194.50
        d12 = e.recuperation_days(12)["value"]
        self.assertEqual(e.recuperation_pay(2025, d12, period_fraction="0.75", reduced_partial=False)["value"], D("2194.50"))
        # שנה 5, 9 חודשים: 5.25 ימים = 2,194.50 פחות 313.50 = 1,881
        d5 = e.recuperation_days(5)["value"]
        self.assertEqual(e.recuperation_pay(2025, d5, period_fraction="0.75", reduced_partial=False)["value"], D("1881"))
        # 6 חודשים מתוך שנה, משרה מלאה, שנה 2: 3 ימים = 1,254 פחות 209 = 1,045
        self.assertEqual(e.recuperation_pay(2025, D(6), period_fraction="0.5", reduced_partial=False)["value"], D("1045"))
        # רונית: שנה 3, חצי משרה: 6x418x0.5 פחות 209 = 1,045
        d3 = e.recuperation_days(3)["value"]
        self.assertEqual(e.recuperation_pay(2025, d3, job_fraction="0.5", reduced_partial=False)["value"], D("1045"))

    def test_team_building(self):
        ok = e.team_building_benefit(True, True, True, False, True, True, True, False)
        self.assertEqual(ok["value"], D(0))
        bad = e.team_building_benefit(True, True, True, True, True, True, True, False)  # בני זוג
        self.assertIsNone(bad["value"])
        # יום שישי בלי שכר + בני זוג: התנאים לא מתקיימים, לא פטור
        fri = e.team_building_benefit(True, False, False, True, True, True, True, False)
        self.assertIsNone(fri["value"])
        self.assertEqual(fri["status"], e.MANUAL)

    def test_operational_car_no_value(self):
        self.assertEqual(e.car_benefit(300000, "regular", operational=True)["value"], 0)

    def test_car_values_match_official_table(self):
        # טבלת שווי שימוש ברכב צמוד (ליניארי), שיעור 2.48% ותקרה 583,100 לפי לוח עזר 2025: מחיר, סוג, שווי חודשי
        for price, kind, expected in [(180983, "hybrid", 3930), (190155, "hybrid", 4160), (95140, "regular", 2360),
                                      (158230, "hybrid", 3360), (207781, "regular", 5150), (202690, "regular", 5030),
                                      (144145, "electric", 2220), (139990, "electric", 2120), (435627, "regular", 10800),
                                      (424800, "regular", 10540), (295000, "electric", 5970), (342906, "electric", 7150)]:
            with self.subTest(price):
                self.assertEqual(e.car_benefit(price, kind)["value"], expected)

    def test_price_cap(self):
        self.assertEqual(e.car_benefit(900000)["value"], e.car_benefit(583100)["value"])

    def test_noncash_benefits_not_paid_in_net(self):
        base = e.compute_month(year=2025, month=1, gross="10000", points="2.75")
        withb = e.compute_month(year=2025, month=1, gross="10500", points="2.75",
                                pension_base="10000", noncash_benefits="500")
        # ברוטו גבוה ב-500 (למס ול"ב), אך הנטו נמוך רק בשל המס/ב"ל על ההטבה, לא ב-500 מלאים
        self.assertGreater(base["net"], withb["net"])
        self.assertLess(base["net"] - withb["net"], 250)


class Month(unittest.TestCase):
    def test_manual_tax_gives_net_but_stays_manual(self):
        r = e.compute_month(year=2026, month=4, gross="10834.24", manual_income_tax=525)
        self.assertEqual(r["overall_status"], e.MANUAL)
        self.assertIsNotNone(r["net"])

    def test_no_tax_no_net(self):
        r = e.compute_month(year=2027, month=4, gross="10834.24")
        self.assertIsNone(r["net"]); self.assertIn("income_tax", r["unresolved"])

    def test_pension_arithmetic(self):
        self.assertEqual(e.deposit("10468.53", "0.07")["value"], D("732.80"))

    def test_cumulative_state_carried(self):
        r1 = e.compute_month(year=2025, month=1, gross="9000")
        r2 = e.compute_month(year=2025, month=2, gross="9000", prev=r1["cumulative"])
        self.assertEqual(r2["cumulative"]["cum_tax"],
                         r1["items"]["income_tax"]["value"] + r2["items"]["income_tax"]["value"])


if __name__ == "__main__":
    unittest.main()


class IrregularPaymentSafety(unittest.TestCase):
    def test_irregular_payment_marks_tax_and_ni_manual(self):
        r = e.compute_month(year=2025, month=7, gross="12090", pension_base="10000", irregular_payment="2090")
        for k in ("income_tax", "national_insurance", "health"):
            self.assertEqual(r["items"][k]["status"], e.MANUAL)
        self.assertEqual(r["overall_status"], e.MANUAL)

    def test_regular_month_unchanged(self):
        r = e.compute_month(year=2025, month=7, gross="10000")
        self.assertNotEqual(r["overall_status"], e.MANUAL)


class DailyTax2026(unittest.TestCase):
    """לוח יומי 2026 מאומת מול לוח עזר רשות המסים (עמ' 10); מדרגה יומית = חודשית / 25."""
    def test_thresholds_equal_monthly_div_25(self):
        import engine as e
        for (m, _), (d, _) in zip(e.BRACKETS[2026][:5], e.DAILY_BRACKETS_2026[:5]):
            self.assertEqual(m / 25, d)

    def test_values(self):
        import engine as e
        from decimal import Decimal as D
        self.assertEqual(e.daily_tax_before_credits(280.40)["value"], D("28.04"))
        self.assertEqual(e.daily_tax_before_credits(402.40)["value"], D("28.04") + D("17.08"))
        self.assertEqual(e.daily_tax_before_credits(0)["value"], D("0.00"))

    def test_other_year_manual(self):
        import engine as e
        self.assertEqual(e.daily_tax_before_credits(300, 2025)["status"], e.MANUAL)

    def test_ceilings(self):
        import engine as e
        self.assertEqual(e.EMPLOYER_PENSION_CEILING_3E3_MONTHLY_2026, 34423)
        self.assertEqual(e.SEVERANCE_DEPOSIT_CEILING_3E3_ANNUAL_2026, 45600)


class IrregularSalaryReg4(unittest.TestCase):
    """תקנה 4(א) לתקנות הניכוי: (מס על חודש + 1/12 בונוס - מס על חודש) x12. חישוב ידני ללוח 2026:
    חודש 10,000: 701 + 0.14*2,990 = 1,119.6; פחות 2.25*242=544.5 -> 575.1 -> 575.
    חודש 11,000 (10,000+12,000/12): 701+427+0.20*940 = 1,316; פחות 544.5 = 771.5 -> 772. הפרש 197 x12 = 2,364."""
    def test_manual_example(self):
        import engine as e
        self.assertEqual(e.monthly_deduction_by_regulation(10000, 2.25), 575)
        self.assertEqual(e.monthly_deduction_by_regulation(11000, 2.25), 772)
        r = e.irregular_salary_tax(10000, 12000, 2.25)
        self.assertEqual(r["value"], 2364)
        self.assertEqual(r["status"], e.BY_LAW)

    def test_zero_bonus_zero_tax(self):
        import engine as e
        self.assertEqual(e.irregular_salary_tax(10000, 0, 2.25)["value"], 0)

    def test_negative_manual(self):
        import engine as e
        self.assertEqual(e.irregular_salary_tax(10000, -1, 2.25)["status"], e.MANUAL)


class DailyWageRegulation(unittest.TestCase):
    """תוספת ב' ותקנה 4(ב) לתקנות ניכוי ממשכורת (btl.gov.il/Laws1/02_0103_100076.pdf)."""

    def test_daily_equals_monthly_over_25(self):
        # יומי x300 = חודשי x12 -> הניכוי היומי = חודשי / 25 (כאן ללא שבר)
        self.assertEqual(e.daily_wage_deduction(300, 2.25)["value"], 9)
        self.assertEqual(e.monthly_deduction_by_regulation(D("7500"), 2.25), 225)

    def test_no_negative(self):
        self.assertEqual(e.daily_wage_deduction(50, 2.25)["value"], 0)

    def test_irregular_daily_is_difference_times_300(self):
        r = e.irregular_daily_tax(300, 3000, 2.25)
        self.assertEqual(r["value"], 300)
        self.assertEqual(r["status"], e.BY_LAW)

    def test_reg6_rates(self):
        self.assertEqual(e.REG6_SPECIAL_RATES["shabbaton"], D("0.35"))
        self.assertEqual(e.REG6_SPECIAL_RATES["gemel_leave_sick_holiday"], D("0.25"))


class TwoRatesCertificate(unittest.TestCase):
    def test_cumulative_split_and_catch_up(self):
        prev = {"cum_taxable": D(0), "cum_tax": D(0), "cum_deposits": D(0), "cum_life": D(0)}
        # חודש 1: 8,000 בשיעור 10% עד 12,000 מצטבר
        it, new = e.income_tax(2026, 1, "two_rates", D(8000), 0, prev, 0, 0, fixed_rate=("0.10", "12000", "0.47"))
        self.assertEqual(it["value"], 800)
        self.assertEqual(it["status"], e.ACCOUNTANT)
        # חודש 2: מצטבר 16,000 -> 1,200 + 0.47*4,000 = 3,080 ; החודש = 2,280
        it2, new2 = e.income_tax(2026, 2, "two_rates", D(8000), 0, new, 0, 0, fixed_rate=("0.10", "12000", "0.47"))
        self.assertEqual(it2["value"], 2280)
        self.assertEqual(new2["cum_tax"], 3080)

    def test_invalid_certificate_is_manual(self):
        prev = {"cum_taxable": D(0), "cum_tax": D(0), "cum_deposits": D(0), "cum_life": D(0)}
        it, _ = e.income_tax(2026, 1, "two_rates", D(8000), 0, prev, 0, 0, fixed_rate=None)
        self.assertEqual(it["status"], e.MANUAL)
