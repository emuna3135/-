import unittest
import engine as e
import payslip as p


def sample(year=2025, month=5, gross="10000", **kw):
    r = e.compute_month(year=year, month=month, gross=gross, points="2.75",
                        pension_employee_rate="0.06", employer_pension_rate="0.065",
                        employer_severance_rate="0.06", **kw)
    res = {"year": year, "month": month, "gross": float(gross), "overtime_pay": 0, "taxable": float(gross),
           "items": {k: {"value": (float(v["value"]) if v["value"] is not None else None),
                         "status": v["status"]} for k, v in r["items"].items()},
           "income_tax": float(r["items"]["income_tax"]["value"] or 0),
           "net": float(r["net"]) if r["net"] is not None else None,
           "overall_status": r["overall_status"], "unresolved": r["unresolved"],
           "employer": {k: (float(v["value"]) if v["value"] is not None else None) for k, v in r["employer"].items()},
           "pension_base": float(gross), "cumulative_taxable": float(gross) * month, "cumulative_tax": 0,
           "cumulative_ni_base": float(gross) * month}
    return res


EMP = {"full_name": "דליה", "id_number": "123456782", "start_date": "2022-03-01",
       "position_scope_percent": 100, "bank_account": "x"}
FULL = {"employer_address": "הרצל 1", "worked": "22 ימים", "vacation": "1 / 12", "sick": "0 / 18",
        "regular_hour_value": 54.95}
CO = {"name": "חברה", "tax_id": "514000000"}


class Visual(unittest.TestCase):
    def test_hebrew_reversed(self):
        self.assertEqual(p.visual("שלום"), "םולש")

    def test_numbers_keep_order(self):
        self.assertEqual(p.visual("12/2025"), "12/2025")
        self.assertEqual(p.visual("1,234.56"), "1,234.56")

    def test_mixed(self):
        self.assertEqual(p.visual("מס (35%)"), "(35%) סמ")
        self.assertEqual(p.visual("ת.ז 123"), "123 ז.ת")


class Rules(unittest.TestCase):
    def test_min_wage_verified_periods(self):
        self.assertEqual(p.min_wage(2025, 1), ("5880.02", "32.30"))   # לפני העלאת 1.4.2025
        self.assertEqual(p.min_wage(2025, 3), ("5880.02", "32.30"))
        self.assertEqual(p.min_wage(2025, 4), ("6247.67", "34.32"))
        self.assertEqual(p.min_wage(2025, 5), ("6247.67", "34.32"))
        self.assertEqual(p.min_wage(2026, 3), ("6247.67", "34.32"))
        self.assertEqual(p.min_wage(2026, 4), ("6443.85", "35.40"))
        self.assertIsNone(p.min_wage(2023, 5))   # לא אומת -> חסר

    def test_missing_fields_flagged(self):
        d, miss, _ = p.prepare(sample(), {}, EMP, CO)
        self.assertIn("כתובת מקום העבודה/העסק", miss)
        self.assertIn("ימי חופשה: ניצול ויתרה", miss)

    def test_complete_has_no_missing(self):
        d, miss, _ = p.prepare(sample(), FULL, EMP, CO)
        self.assertEqual(miss, [])

    def test_section24_new_fields_required(self):
        res = sample()
        res["cumulative_ni_base"] = None
        _, miss, _ = p.prepare(res, {k: v for k, v in FULL.items() if k != "regular_hour_value"}, EMP, CO)
        self.assertIn("ערך שעת עבודה רגילה", miss)
        self.assertIn("שכר חייב בביטוח לאומי מצטבר", miss)

    def test_seniority(self):
        from dateutil.relativedelta import relativedelta
        import datetime
        for sd, y, m in [("2022-03-01", 2025, 5), ("2025-11-16", 2026, 10), ("2026-10-20", 2026, 10)]:
            s = datetime.date.fromisoformat(sd)
            end = datetime.date(y, m, __import__("calendar").monthrange(y, m)[1])
            rd = relativedelta(end, s)
            self.assertEqual(p.seniority(sd, y, m), f"{rd.years} שנים {rd.months} חודשים")
        self.assertIsNone(p.seniority(None, 2026, 10))
        self.assertIsNone(p.seniority("2027-01-01", 2026, 10))

    def test_override_seniority(self):
        d, _, _ = p.prepare(sample(), dict(FULL, seniority_override="5 שנים"), EMP, CO)
        self.assertEqual(d["seniority"], "5 שנים")

    def test_old_year_missing_min_wage(self):
        r = sample(year=2023)
        _, miss, _ = p.prepare(r, FULL, EMP, CO)
        self.assertIn("שכר מינימום לחודש ולשעה לתקופה", miss)


class Render(unittest.TestCase):
    def test_draft_when_missing_even_if_approved(self):
        pdf, miss, reasons, draft = p.render(sample(), {}, EMP, CO, approved=True)
        self.assertTrue(draft); self.assertTrue(pdf.startswith(b"%PDF"))

    def test_draft_when_not_approved_and_not_fully_by_law(self):
        res = sample()
        res["overall_status"] = e.ACCOUNTANT      # מרכיב לפי רואת חשבון -> נדרש אישור חשב לפני הפקה סופית
        _, _, reasons, draft = p.render(res, FULL, EMP, CO, approved=False)
        self.assertTrue(draft)

    def test_final_when_fully_by_law_even_unapproved(self):
        # מאומת מול תלוש אינו קריטריון נפרד: חישוב שכולו עפ"י החוק וללא חסרים אינו טיוטה
        _, miss, _, draft = p.render(sample(), FULL, EMP, CO, approved=False)
        self.assertEqual(miss, [])
        self.assertFalse(draft)

    def test_final_when_approved_and_complete(self):
        _, miss, _, draft = p.render(sample(), FULL, EMP, CO, approved=True)
        self.assertFalse(draft); self.assertEqual(miss, [])

    def test_unresolved_tax_stays_draft(self):
        r = sample(year=2027, month=4)
        _, _, _, draft = p.render(r, FULL, EMP, CO, approved=True)
        self.assertTrue(draft)   # אין נטו -> לא ניתן לאשר

    def test_net_equals_gross_minus_deductions(self):
        d, _, _ = p.prepare(sample(), FULL, EMP, CO)
        self.assertAlmostEqual(d["net"], d["gross"] - d["total_deductions"], places=2)


if __name__ == "__main__":
    unittest.main()
