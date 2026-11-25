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
