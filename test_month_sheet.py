import io, re, unittest
from openpyxl import load_workbook
import upload_template


class MonthSheet(unittest.TestCase):
    def test_rows_and_text_ids(self):
        data = upload_template.build_month_sheet([("000000018", "דנה כהן"), ("123456782", "אבי לוי")], 2026, 12)
        ws = load_workbook(io.BytesIO(data)).worksheets[0]
        self.assertEqual([c.value for c in ws[1]], upload_template.MONTH_SHEET_HEAD)
        self.assertEqual(ws["A2"].value, "000000018")        # אפסים מובילים נשמרים
        self.assertEqual(ws["C2"].value, 2026)
        self.assertEqual(ws["D3"].value, 12)
        self.assertEqual([ws.cell(2, c).value for c in range(5, 11)], [0, 0, 0, 0, 0, None])

    def test_headers_known_to_reader(self):
        src = open("main_api.py", encoding="utf-8").read()   # main_api לא נטען בסביבה בלי bcrypt: בודקים מול הטקסט
        flat = {h for h in upload_template.MONTH_SHEET_HEAD if '"' + h + '"' in src}
        for h in upload_template.MONTH_SHEET_HEAD:
            self.assertIn(h, flat, h)


if __name__ == "__main__":
    unittest.main()
