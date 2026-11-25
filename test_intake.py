import unittest
import intake


class Classify(unittest.TestCase):
    def test_101_text(self):
        t = "כרטיס עובד 0101 בקשה להקלה ולתיאום מס על ידי המעביד פרטים על הכנסות אחרות נקודות זיכוי"
        self.assertEqual(intake.classify_text(t)["kind"], "form101")

    def test_attendance_text(self):
        t = "כרטיס עובד נוכחות תאריך כניסה יציאה הפסקה סה\"כ שעות שעות נוספות"
        self.assertEqual(intake.classify_text(t)["kind"], "attendance")

    def test_reversed_hebrew(self):
        t = "כרטיס עובד 0101 בקשה להקלה ולתיאום מס נקודות זיכוי הכנסות אחרות"[::-1]
        self.assertEqual(intake.classify_text(t)["kind"], "form101")

    def test_not_guessing(self):
        self.assertEqual(intake.classify_text("כרטיס עובד")["kind"], "unknown")      # סימן אחד בלבד
        self.assertEqual(intake.classify_text("")["kind"], "unknown")
        mixed = "כרטיס עובד נקודות זיכוי הכנסות אחרות כניסה יציאה הפסקה שעות עבודה"
        self.assertEqual(intake.classify_text(mixed)["kind"], "unknown")             # פער קטן מדי

    def test_files(self):
        self.assertEqual(intake.classify(b"")["kind"], "unknown")
        self.assertEqual(intake.classify(b"PK\x03\x04xx", "a.xlsx")["kind"], "excel")
        self.assertEqual(intake.classify(b"PK\x03\x04xx", "a.zip")["kind"], "unknown")
        self.assertEqual(intake.classify(b"\x89PNG\r\n\x1a\nxx")["kind"], "image")
        self.assertEqual(intake.classify(b"hello")["kind"], "unknown")
        self.assertEqual(intake.classify(b"%PDF-broken")["kind"], "unknown")


if __name__ == "__main__":
    unittest.main()
