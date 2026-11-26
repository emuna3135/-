import unittest
import form102_tax as F


def stub(i, gross, tax, y=2026, m=10, **kw):
    d = {"emp_id_number": f"00000000{i}", "emp_name": f"עובד {i}", "year": y, "month": m, "gross": gross, "income_tax": tax}
    d.update(kw)
    return d


def build(stubs, **kw):
    a = dict(represent_number="123456789", taxpayer_number="987654321", register_number="01")
    a.update(kw)
    return F.build(2026, 10, stubs, **a)


class Form102Tax(unittest.TestCase):
    def test_official_field_names_and_lengths(self):
        r = build([stub(1, 10000, 500.4), stub(2, 8000.5, 0)], payment_method=1)
        i = r["input"]
        self.assertEqual(set(i), {"RepresentNumber", "TaxpayerNumber", "Period", "ActionCode", "RegisterNumber",
                                  "DeductionTypeCount", "DeductionTypeList", "PaymentAmount", "PaymentDate", "PaymentMethod"})
        self.assertEqual(len(i["RepresentNumber"]), 9); self.assertEqual(len(i["TaxpayerNumber"]), 9)
        self.assertEqual(i["Period"], "202610"); self.assertEqual(i["ActionCode"], 1)
        self.assertEqual(i["DeductionTypeCount"], len(i["DeductionTypeList"]))
        L = i["DeductionTypeList"][0]
        self.assertEqual(L["DeductionType"], "00"); self.assertEqual(L["NonEmployment"], 0)
        self.assertEqual((L["EmployeesNumber"], L["Payments"], L["Charges"]), (2, 18001, 500))
        self.assertEqual(i["PaymentAmount"], L["Charges"])   # שגיאה 119
        self.assertEqual(r["status"], "ready_for_review")

    def test_payments_include_zero_tax_employee(self):
        # ההדרכה הרשמית: לרשום את כל המשכורות גם אם לא נוכה מס
        r = build([stub(1, 4000, 0)], payment_method=0)
        self.assertEqual(r["input"]["DeductionTypeList"][0]["Payments"], 4000)
        self.assertEqual(r["input"]["DeductionTypeList"][0]["EmployeesNumber"], 1)
        self.assertEqual(r["status"], "ready_for_review")

    def test_later_stub_replaces_earlier_for_same_employee(self):
        r = build([stub(1, 9000, 300), stub(1, 10000, 400)], payment_method=1)
        L = r["input"]["DeductionTypeList"][0]
        self.assertEqual((L["EmployeesNumber"], L["Payments"], L["Charges"]), (1, 10000, 400))

    def test_other_months_ignored(self):
        r = build([stub(1, 9000, 300, m=9), stub(2, 5000, 100)], payment_method=1)
        self.assertEqual(r["input"]["DeductionTypeList"][0]["EmployeesNumber"], 1)

    def test_whole_shekel_rounding_is_flagged_and_exact_kept(self):
        r = build([stub(1, 1000.50, 100.50)], payment_method=1)
        self.assertEqual(r["summary"]["payments"], 1001); self.assertEqual(r["summary"]["charges"], 101)
        self.assertEqual(r["summary"]["exact_before_rounding"]["payments"], "1000.5")
        self.assertTrue(any("עיגול" in n for n in r["notes"]))

    def test_missing_tax_blocks(self):
        r = build([stub(1, 10000, None)], payment_method=1)
        self.assertEqual(r["status"], "blocked")
        self.assertTrue(any("לא חושב" in p for p in r["problems"]))

    def test_negative_blocks(self):
        r = build([stub(1, 10000, -5)], payment_method=1)
        self.assertEqual(r["status"], "blocked")

    def test_charges_above_payments_error_118(self):
        r = build([stub(1, 100, 500)], payment_method=1)
        self.assertTrue(any("118" in p for p in r["problems"]))

    def test_non_employment(self):
        r = build([], non_employment=True, payment_method=0)
        L = r["input"]["DeductionTypeList"][0]
        self.assertEqual((L["NonEmployment"], L["EmployeesNumber"], L["Payments"], L["Charges"]), (1, 0, 0, 0))
        self.assertEqual(r["input"]["PaymentAmount"], 0)
        self.assertEqual(r["status"], "ready_for_review")

    def test_no_stubs_without_explicit_non_employment_blocks(self):
        r = build([], payment_method=0)
        self.assertEqual(r["status"], "blocked")

    def test_payment_method_consistency(self):
        self.assertEqual(build([stub(1, 10000, 500)], payment_method=0)["status"], "blocked")
        self.assertEqual(build([stub(1, 10000, 0)], payment_method=1)["status"], "blocked")
        self.assertEqual(build([stub(1, 10000, 60000 - 1)], payment_method=2)["status"], "blocked")

    def test_bad_identifiers_rejected(self):
        for kw in ({"represent_number": "12a"}, {"taxpayer_number": "0"}, {"register_number": "00"},
                   {"represent_number": "0000000000"}, {"payment_method": 7}, {"payment_date": "2026-11-19"}):
            with self.assertRaises(ValueError, msg=str(kw)):
                build([stub(1, 1000, 10)], **kw)

    def test_amount_equal_to_file_number_blocked(self):
        r = build([stub(1, 987654321, 5)], payment_method=1, taxpayer_number="987654321")
        self.assertTrue(any("229" in p for p in r["problems"]))

    def test_sources_present(self):
        r = build([stub(1, 1000, 10)], payment_method=1)
        self.assertEqual(len(r["sources"]), 2)
        self.assertTrue(any("אימות מול שע\"ם" in n for n in r["notes"]))


if __name__ == "__main__":
    unittest.main()
