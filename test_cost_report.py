import unittest
from decimal import Decimal as D
import cost_report as C


def stub(m, emp="1", gross=10000, ni=450.55, pen=650, sev=600, sf=0, **kw):
    s = dict(year=2026, month=m, emp_id_number=emp, emp_name="x", gross=gross,
             employer={"national_insurance": {"value": ni}, "pension": {"value": pen},
                       "severance": {"value": sev}, "study_fund": {"value": sf}})
    s.update(kw)
    return s


class Cost(unittest.TestCase):
    def test_row_total(self):
        r = C.employer_cost(2026, [stub(1)])
        self.assertEqual(r["rows"][0]["total"], D("11700.55")); self.assertEqual(r["rows"][0]["status"], "complete")

    def test_employee_and_grand_totals(self):
        r = C.employer_cost(2026, [stub(1), stub(2), stub(1, emp="2", gross=5000)])
        self.assertEqual(r["by_employee"][0]["months"], 2); self.assertEqual(r["total"]["employees"], 2)
        self.assertEqual(r["total"]["total"], D("11700.55") * 2 + D("6700.55"))

    def test_missing_component_is_partial_not_zero_silently(self):
        s = stub(1); s["employer"]["national_insurance"] = {"value": None}
        r = C.employer_cost(2026, [s])
        self.assertEqual(r["rows"][0]["status"], "partial"); self.assertEqual(r["rows"][0]["missing"], ["national_insurance"])
        self.assertEqual(r["total"]["partial_months"], 1)

    def test_later_stub_wins_other_year_ignored(self):
        r = C.employer_cost(2026, [stub(1, gross=1), stub(1, gross=9000), stub(1, year=2025)])
        self.assertEqual(len(r["rows"]), 1); self.assertEqual(r["rows"][0]["gross"], D("9000.00"))

    def test_rounding_half_up_to_agora(self):
        r = C.employer_cost(2026, [stub(1, gross=100.005, ni=0.004, pen=0, sev=0)])
        self.assertEqual(r["rows"][0]["gross"], D("100.01"))


if __name__ == "__main__":
    unittest.main()
