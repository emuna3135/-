import unittest
import intake


FORM = " ".join(intake.FORM101_MARKERS)


class Classify(unittest.TestCase):
    def test_101_text(self):
        self.assertEqual(intake.classify_text(FORM)["kind"], "form101")
        part = " ".join(intake.FORM101_MARKERS[:13])          # גם טופס חלקי (13 סימנים) מזוהה
        self.assertEqual(intake.classify_text(part)["kind"], "form101")
        self.assertEqual(intake.classify_text(" ".join(intake.FORM101_MARKERS[:11]))["kind"], "unknown")   # 11 לא מספיק

    def test_instructions_not_a_form(self):
        r = intake.classify_text(FORM + " נספח א הוראות בדבר אופן מילוי השדות חובה/רשות")
        self.assertEqual(r["kind"], "unknown")

    def test_attendance_text(self):
        t = "כרטיס עובד נוכחות תאריך כניסה יציאה הפסקה סה\"כ שעות שעות נוספות"
        self.assertEqual(intake.classify_text(t)["kind"], "attendance")

    def test_reversed_hebrew(self):
        self.assertEqual(intake.classify_text(FORM[::-1])["kind"], "form101")
        self.assertEqual(intake.classify_text(FORM.replace(" ", "").replace('"', ""))["kind"], "form101")   # בלי רווחים

    def test_not_guessing(self):
        self.assertEqual(intake.classify_text("כרטיס עובד")["kind"], "unknown")      # סימן אחד בלבד
        self.assertEqual(intake.classify_text("")["kind"], "unknown")
        mixed = "כרטיס עובד נקודות זיכוי הכנסות אחרות תאריך לידה כניסה יציאה הפסקה שעות עבודה"
        self.assertEqual(intake.classify_text(mixed)["kind"], "attendance")

    def test_files(self):
        self.assertEqual(intake.classify(b"")["kind"], "unknown")
        self.assertEqual(intake.classify(b"PK\x03\x04xx", "a.xlsx")["kind"], "excel")
        self.assertEqual(intake.classify(b"PK\x03\x04xx", "a.zip")["kind"], "unknown")
        self.assertEqual(intake.classify(b"\x89PNG\r\n\x1a\nxx")["kind"], "image")
        self.assertEqual(intake.classify(b"hello")["kind"], "unknown")
        self.assertEqual(intake.classify(b"%PDF-broken")["kind"], "unknown")


if __name__ == "__main__":
    unittest.main()


class ExcelInspect(unittest.TestCase):
    def _wb(self, sheets):
        import io
        from openpyxl import Workbook
        wb = Workbook(); wb.remove(wb.active)
        for name, header in sheets.items():
            ws = wb.create_sheet(name); ws.append(header); ws.append(["x"] * len(header))
        b = io.BytesIO(); wb.save(b); return b.getvalue()

    def test_employees_workbook(self):
        import employee_import
        r = intake.inspect_excel(self._wb({employee_import.SHEET_EMPLOYEES: ["תעודת זהות", "שם"]}))
        self.assertEqual(r["kind"], "employees_workbook")

    def test_attendance_candidate_headers_only(self):
        r = intake.inspect_excel(self._wb({"דוח": ["תאריך", "כניסה", "יציאה", "סה\"כ שעות"]}))
        self.assertEqual(r["kind"], "attendance_candidate")
        self.assertNotIn("x", sum(r["headers"].values(), []))

    def test_unknown_and_broken(self):
        self.assertEqual(intake.inspect_excel(self._wb({"a": ["foo", "bar"]}))["kind"], "unknown")
        self.assertEqual(intake.inspect_excel(b"not excel")["kind"], "unknown")
