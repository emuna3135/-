import unittest
from decimal import Decimal as D
import card
import demo_cumulative as dc
import employee_import as ei
import engine as pe
import secure


class DemoCumulative(unittest.TestCase):
    def setUp(self):
        self.sheets = ei.read_sheets(dc.build())

    def test_sheets_parse_and_ids_valid(self):
        self.assertEqual(len(self.sheets["תלושים לטעינה"]), 30)
        for r in self.sheets["עובדים"]:
            ei.parse_employee(r)
            self.assertTrue(secure.valid_israeli_id(str(r["תעודת זהות"])))
        for r in self.sheets["טופס 101"]:
            ei.parse_form101(r)

    def test_chain_bonus_month_spikes_then_returns(self):
        prev = dict(pe.ZERO_PREV)
        taxes = []
        for m in range(1, 11):
            g = D(12000) + (D(15000) if m == 6 else 0)
            r = pe.compute_month(year=2026, month=m, gross=g, taxable_gross=g, points="2.75", mode="cumulative",
                                 prev=prev, pension_employee_rate="0.06")
            prev = r["cumulative"]
            taxes.append(r["items"]["income_tax"]["value"])
        self.assertGreater(taxes[5], taxes[4] * 3)
        self.assertEqual(taxes[6], taxes[4])
        self.assertEqual(prev["cum_tax"], sum(taxes))

    def test_prev_cumulative_headers_in_template(self):
        import upload_template as ut
        self.assertIn("מצטבר קודם: מס", ut.MONTH_HEAD)


if __name__ == "__main__":
    unittest.main()
