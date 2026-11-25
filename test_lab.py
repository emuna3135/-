import sys, unittest
sys.path.insert(0, "lab")
import synthetic_lab as lab


class Lab(unittest.TestCase):
    def test_lab(self):
        out = lab.run()
        self.assertEqual(out["sim_bad"], 0)                 # כל 123 מקרי הסימולטור דרך שכבת 101
        self.assertEqual(out["inv"]["tax_mismatch"], 0)     # מס מצטבר מול חישוב בלתי תלוי
        self.assertEqual(out["inv"]["ni_mismatch"], 0)      # ב"ל ובריאות מול חישוב בלתי תלוי
        self.assertEqual(out["inv"]["manual"], 0)
        self.assertEqual(out["findings"], [])


class Special(unittest.TestCase):
    def test_special_cases(self):
        import special_cases as sc
        o = sc.run()
        for k in ("daily", "monthly_rounding", "irregular", "olim", "soldier"):
            self.assertEqual(o[k], [], k)
        self.assertGreaterEqual(o["n"], 200)


class EdgeMatrix(unittest.TestCase):
    """מטריצת tax_mode לפי טופס 101 (דברי הסבר 4-5, הערות 7-8) ובסיס פנסיה/הלוואות דרך payslip()."""
    def test_tax_mode_matrix(self):
        import card
        T = card.tax_mode
        self.assertEqual(T(False)[0], "no_coordination")
        self.assertEqual(T(True, "additional")[0], "no_coordination")
        self.assertEqual(T(True, salary_kind="partial", other_income=False)[0], "cumulative")
        self.assertEqual(T(True, salary_kind="partial", other_income=True)[0], "no_coordination")
        self.assertEqual(T(True, other_income=True, other_income_credit="here")[0], "cumulative")
        self.assertEqual(T(True, other_income=True, other_income_credit="elsewhere")[0], "no_coordination")
        self.assertEqual(T(True, other_income=True)[0], "no_coordination")
        self.assertEqual(T(True)[0], "cumulative")
        self.assertEqual(T(True, salary_kind="zzz")[0], "manual")

    def _emp(self, **kw):
        e = dict(idn="x", gender="M", married=True, cust=[], noncust=[], flag=None, base=10000, ot125=10, ot150=0,
                 bonus=3000, bonus_months=[3], phone=0, car_price=0, components=[], pension_codes=[],
                 pen_ot=False, pen_bonus=False, pen_rate=0.06, sf_rate=0, deductions=[], points=2.25)
        e.update(kw)
        return e

    def test_pension_base_flags(self):
        from decimal import Decimal as D
        base = lab.payslip(self._emp(), 3, None)
        self.assertEqual(base["pbase"], D(10000))                 # ברירת מחדל: שכר יסוד בלבד
        both = lab.payslip(self._emp(pen_ot=True, pen_bonus=True), 3, None)
        self.assertEqual(both["pbase"], D(10000) + both["ot"] + D(3000))
        self.assertEqual(D(str(both["r"]["items"]["pension_employee"]["value"])), lab.pe.r2(both["pbase"] * D("0.06")))

    def test_loan_deduction_ends_and_net_effect(self):
        from decimal import Decimal as D
        loan = [dict(code="L", kind="advance", monthly="500", start="2026-02", total="1200")]
        nets = [lab.payslip(self._emp(deductions=loan, bonus=0, ot125=0), m, None)["ded"] for m in (1, 2, 3, 4, 5)]
        self.assertEqual(nets, [D(0), D("500.00"), D("500.00"), D("200.00"), D(0)])


class DailyWorker(unittest.TestCase):
    def test_daily_mode_month_tax(self):
        import engine as pe, special_cases as sc
        from decimal import Decimal as D
        for w, n, pts in ((400, 22, "2.25"), (760.01, 20, "2.75"), (1200, 15, "2.25"), (250, 10, "4.75")):
            gross = D(w) * n
            r = pe.compute_month(year=2026, month=1, gross=gross, points=pts, mode="daily", prev=None,
                                 pension_base=gross, daily=(w, n))
            tax = r["items"]["income_tax"]
            self.assertEqual(D(str(tax["value"])), sc.ref_daily(w, pts) * n)
            self.assertEqual(tax["status"], pe.BY_LAW)
            self.assertEqual(r["cum"]["cum_tax"] if "cum" in r else sc.ref_daily(w, pts) * n, sc.ref_daily(w, pts) * n)

    def test_daily_missing_inputs_manual(self):
        import engine as pe
        r = pe.compute_month(year=2026, month=1, gross=5000, points="2.25", mode="daily", prev=None, daily=None)
        self.assertEqual(r["items"]["income_tax"]["status"], pe.MANUAL)
        self.assertIsNone(r["net"])
