import datetime
import unittest

import import_preview as ip

TODAY = datetime.date(2026, 11, 26)


def emp(**kw):
    r = {"תעודת זהות": "000000018", "שם מלא": "בדוי", "מין": "M", "תאריך לידה": "1990-01-01", "תאריך תחילת עבודה": "2020-01-01",
         "שכר יסוד": 9000, "אחוז פנסיה עובד": 0.06}
    r.update(kw)
    return r


def prev(rows, f101=None):
    return ip.build({"עובדים": rows, "טופס 101": f101 or []}, today=TODAY)


class TestPreview(unittest.TestCase):
    def test_missing_employees_sheet(self):
        self.assertIn("error", ip.build({}, today=TODAY))

    def test_good_row_warns_only_about_missing_101(self):
        r = prev([emp()])["employees"][0]
        self.assertEqual(r["status"], "warn")
        self.assertTrue(any("טופס 101" in i["text"] for i in r["issues"]))
        self.assertEqual(r["id"], "*****0018")            # לא מוצגת ת"ז מלאה

    def test_bad_id_blocks(self):
        r = prev([emp(**{"תעודת זהות": "123456789"})])
        self.assertEqual(r["employees"][0]["status"], "error")
        self.assertFalse(r["ready"])

    def test_parse_error_is_row_error_not_crash(self):
        r = prev([emp(מין="לא ידוע")])["employees"][0]
        self.assertEqual(r["status"], "error")

    def test_minor_gets_category_info(self):
        r = prev([emp(**{"תאריך לידה": "2010-05-05"})])["employees"][0]
        self.assertTrue(any("קטגוריה" in i["text"] for i in r["issues"]))

    def test_retirement_age_without_pension_answer_warns(self):
        r = prev([emp(**{"תאריך לידה": "1958-02-02"})])["employees"][0]
        self.assertTrue(any("קצבת זקנה" in i["text"] for i in r["issues"] if i["level"] == "warn"))

    def test_missing_birth_warns(self):
        r = prev([emp(**{"תאריך לידה": None})])["employees"][0]
        self.assertTrue(any("תאריך לידה" in i["text"] for i in r["issues"] if i["level"] == "warn"))

    def test_foreign_without_country_warns(self):
        f = [{"תעודת זהות": "000000018", "שנת מס": 2026, "תאריך חתימה": "2026-01-05", "סוג הכנסה": "משרה עיקרית", "סוג עובד": "עובד זר חוקי",
              "חודשי שהייה בישראל": 12}]
        r = prev([emp()], f)["employees"][0]
        self.assertTrue(any("מדינת מוצא" in i["text"] for i in r["issues"] if i["level"] == "warn"))

    def test_existing_marked(self):
        r = ip.build({"עובדים": [emp()]}, existing_ids={"000000018"}, today=TODAY)["employees"][0]
        self.assertTrue(any("קיים" in i["text"] for i in r["issues"]))

    def test_counts_and_ready(self):
        f = [{"תעודת זהות": "000000018", "שנת מס": 2026, "תאריך חתימה": "2026-01-05", "סוג הכנסה": "משרה עיקרית"}]
        r = prev([emp()], f)
        self.assertEqual(r["counts"]["total"], 1)
        self.assertTrue(r["ready"])


if __name__ == "__main__":
    unittest.main()


class TestPreviewApi(unittest.TestCase):
    def test_endpoint_does_not_save(self):
        import io, os, sys, tempfile
        d = tempfile.mkdtemp()
        os.environ.update(DATABASE_URL="sqlite:///" + d + "/p.db", REQUIRE_2FA="false", JWT_SECRET="x" * 40)
        from cryptography.fernet import Fernet
        os.environ["FIELD_KEY"] = Fernet.generate_key().decode()
        sys.modules.pop("main_api", None)
        import main_api
        import upload_template as ut
        from fastapi.testclient import TestClient
        c = TestClient(main_api.app)
        r = c.post("/auth/register", json={"email": "prev.qa@example.com", "password": "Zebra-Orchid-Lantern-2026!", "full_name": "בדיקה"})
        H = {"Authorization": "Bearer " + r.json()["access_token"]}
        cid = c.post("/companies", json={"name": "חברה בדויה", "tax_id": "000000000"}, headers=H).json()["id"]
        files = {"file": ("t.xlsx", ut.build_template(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        res = c.post(f"/companies/{cid}/employees/upload-excel/preview", files=files, headers=H)
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["counts"]["total"], 1)
        self.assertEqual(c.get(f"/companies/{cid}/employees", headers=H).json(), [])      # לא נשמר דבר
        bad = c.post(f"/companies/{cid}/employees/upload-excel/preview", files={"file": ("t.txt", b"x", "text/plain")}, headers=H)
        self.assertEqual(bad.status_code, 400)
