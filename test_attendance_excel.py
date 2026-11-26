import io
import datetime
import unittest
import openpyxl
import attendance_excel as A


def wb_bytes(rows, header=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in ([header] if header else []) + rows:
        ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()


H = ["תאריך", "יום", "כניסה", "יציאה", "סה\"כ", "שעות רגילות", "שעות 125%"]
D = lambda d: datetime.date(2026, 1, d)
T = lambda s: s


class AttendanceExcel(unittest.TestCase):
    def test_basic_verified(self):
        rows = [[D(4), "א", "08:00", "17:00", "09:00", "08:00", "01:00"],
                [D(5), "ב", "08:00", "16:00", "08:00", "08:00", "00:00"],
                ["סה\"כ", None, None, None, "17:00", "16:00", "01:00"]]
        r = A.parse_workbook(wb_bytes(rows, H))
        e = r["employees"][0]
        self.assertEqual(e["totals"]["presence_min"], 17 * 60)
        self.assertEqual(e["totals"]["overtime_min"]["125"], 60)
        self.assertEqual(e["working_days"], 2)
        self.assertEqual(r["verification"], "מאומת מול שורת הסיכום של הדוח")
        self.assertEqual(r["warnings"], [])

    def test_summary_mismatch_is_flagged(self):
        rows = [[D(4), "א", "08:00", "17:00", "09:00", "08:00", "01:00"], ["סה\"כ", None, None, None, "10:00", "08:00", "01:00"]]
        r = A.parse_workbook(wb_bytes(rows, H))
        self.assertEqual(r["verification"], "סכום הימים שונה מסיכום הדוח")
        self.assertTrue(any("540" in w and "600" in w for w in r["warnings"]))

    def test_span_vs_total_warns(self):
        rows = [[D(4), "א", "08:00", "17:00", "08:00", "08:00", None]]
        r = A.parse_workbook(wb_bytes(rows, H))
        self.assertTrue(any("שונה מסה\"כ" in w for w in r["warnings"]))

    def test_unknown_column_warned_not_dropped(self):
        rows = [[D(4), "א", "08:00", "17:00", "09:00", "08:00", "01:00", "x"]]
        r = A.parse_workbook(wb_bytes(rows, H + ["בונוס נוכחות"]))
        self.assertTrue(any("בונוס נוכחות" in w and "לא זוהתה" in w for w in r["warnings"]))

    def test_bad_time_not_guessed(self):
        rows = [[D(4), "א", "08:00", "17:00", "8.5", "08:00", None]]
        r = A.parse_workbook(wb_bytes(rows, H))
        self.assertTrue(any("אינו שעה" in w for w in r["warnings"]))
        self.assertEqual(r["employees"][0]["totals"]["presence_min"], 0)

    def test_excel_time_cells_and_text_dates(self):
        rows = [["04/01/2026", "א", datetime.time(8, 0), datetime.time(17, 30), datetime.time(9, 30), None, None]]
        r = A.parse_workbook(wb_bytes(rows, H))
        self.assertEqual(r["employees"][0]["totals"]["presence_min"], 570)
        self.assertEqual(r["employees"][0]["days"][0]["date"], "2026-01-04")

    def test_custom_mapping_with_foreign_headers(self):
        h = ["Date", "In", "Out", "Hours"]
        rows = [[D(4), "08:00", "16:00", "08:00"]]
        with self.assertRaises(ValueError):
            A.parse_workbook(wb_bytes(rows, h))                        # בלי מיפוי: לא מנחשים
        r = A.parse_workbook(wb_bytes(rows, h), mapping={"date": "A", "entry": "B", "exit": "C", "total": "D"})
        self.assertEqual(r["employees"][0]["totals"]["presence_min"], 480)

    def test_overnight_shift_flagged(self):
        rows = [[D(4), "א", "22:00", "06:00", "08:00", None, None]]
        r = A.parse_workbook(wb_bytes(rows, H))
        self.assertTrue(any("חוצה חצות" in w for w in r["warnings"]))
        self.assertEqual(r["employees"][0]["totals"]["presence_min"], 480)

    def test_multi_employee_no_auto_verification(self):
        h = ["תעודת זהות", "שם עובד"] + H
        rows = [["000000018", "א", D(4), "א", "08:00", "16:00", "08:00", None, None],
                ["000000026", "ב", D(4), "א", "09:00", "16:00", "07:00", None, None]]
        r = A.parse_workbook(wb_bytes(rows, h))
        self.assertEqual(len(r["employees"]), 2)
        self.assertEqual(r["employees"][1]["totals"]["presence_min"], 420)

    def test_not_attendance_file(self):
        with self.assertRaises(ValueError):
            A.parse_workbook(wb_bytes([[1, 2, 3]], ["a", "b", "c"]))


if __name__ == "__main__":
    unittest.main()
