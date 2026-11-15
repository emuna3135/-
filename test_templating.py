import copy
import os
import unittest

import payslip as ps
import templating as T

HERE = os.path.dirname(os.path.abspath(__file__))


def sample_d(**over):
    res = {"year": 2026, "month": 1, "gross": 7826.92, "overtime_pay": 426.92, "income_tax": 107.0, "net": 6906.30,
           "items": {"income_tax": {"value": 107.0}, "national_insurance": {"value": 88.79}, "health": {"value": 255.21},
                     "pension_employee": {"value": 469.62}, "study_fund_employee": {"value": 0}},
           "employer": {"pension": 508.75}, "benefits": {}, "overall_status": "מאומת", "unresolved": [],
           "points": 2.25, "taxable": 7826.92, "cumulative_taxable": 7826.92, "cumulative_tax": 107,
           "cumulative_ni_base": 7826.92, "pension_base": 7826.92}
    emp = {"full_name": "בדוי", "id_number": "300000007", "start_date": "2022-03-01", "bank_account": "x"}
    extras = {"employer_address": "כתובת", "worked": "22 ימים", "vacation": "0 / 5", "sick": "0 / 2",
              "regular_hour_value": 40.66}
    extras.update(over)
    d, miss, reasons = ps.prepare(res, extras, emp, {"name": "משרד", "tax_id": "512345674"})
    return d, miss


def tiny(el):
    return {"name": "t", "elements": [el]}


class Validation(unittest.TestCase):
    def test_family_a_valid(self):
        T.load(os.path.join(HERE, "templates", "family_a.json"))

    def test_digits_in_static_text_rejected(self):
        with self.assertRaises(T.TemplateError):
            T.validate(tiny({"type": "text", "at": [10, 10], "text": "סכום 123"}))

    def test_placeholder_digits_ok_but_unknown_field_rejected(self):
        T.validate(tiny({"type": "text", "at": [10, 10], "text": "חודש {period}"}))
        with self.assertRaises(T.TemplateError):
            T.validate(tiny({"type": "text", "at": [10, 10], "text": "{no_such_field}"}))

    def test_unknown_table_source_and_column(self):
        with self.assertRaises(T.TemplateError):
            T.validate(tiny({"type": "table", "rect": [10, 10, 100, 50], "source": "x",
                             "columns": [{"header": "א", "col": "label", "w": 50}]}))
        with self.assertRaises(T.TemplateError):
            T.validate(tiny({"type": "table", "rect": [10, 10, 100, 50], "source": "payments",
                             "columns": [{"header": "א", "col": "rate", "w": 50}]}))

    def test_out_of_page_and_wide_columns(self):
        with self.assertRaises(T.TemplateError):
            T.validate(tiny({"type": "box", "rect": [150, 10, 100, 50]}))
        with self.assertRaises(T.TemplateError):
            T.validate(tiny({"type": "table", "rect": [10, 10, 40, 50], "source": "payments",
                             "columns": [{"header": "א", "col": "label", "w": 30}, {"header": "ב", "col": "amount", "w": 30}]}))


class Render(unittest.TestCase):
    def test_renders_pdf_and_no_missing(self):
        d, _ = sample_d()
        spec = T.load(os.path.join(HERE, "templates", "family_a.json"))
        pdf, missing = T.render(spec, d)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(missing, [])

    def test_missing_value_is_reported_not_invented(self):
        d, _ = sample_d()
        d["employer_address"] = None
        spec = T.load(os.path.join(HERE, "templates", "family_a.json"))
        _, missing = T.render(spec, d)
        self.assertIn("employer_address", missing)

    def test_table_overflow_raises(self):
        d, _ = sample_d()
        d["payments"] = [("רכיב", 1.0)] * 60
        spec = T.load(os.path.join(HERE, "templates", "family_a.json"))
        with self.assertRaises(T.TemplateOverflow):
            T.render(spec, d)


if __name__ == "__main__":
    unittest.main()
