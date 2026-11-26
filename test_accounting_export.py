import csv
import io
import unittest
from decimal import Decimal as D

import accounting_export as ax


def stub(name="בדוי", gross=10000.0, tax=700.0, ni=300.1234, health=400.5678, pen=600.0, net=None,
         er=(650.0, 600.0, 0.0, 400.0), ded=0.0):
    if net is None:
        net = round(gross - tax - ni - health - pen - ded, 2)
    return {"emp_name": name, "emp_id_number": "*****1234", "gross": gross, "income_tax": tax, "national_insurance": ni,
            "health": health, "pension_employee": pen, "net": net,
            "employer": {"pension": er[0], "severance": er[1], "study_fund": er[2], "national_insurance": er[3]}}


class TestExport(unittest.TestCase):
    def test_balanced_summary(self):
        rows, issues = ax.build_rows([stub(), stub("אחר", gross=12000.0, ni=350.5, health=420.25, net=None)], {})
        self.assertEqual(sum(r["debit"] for r in rows), sum(r["credit"] for r in rows))
        self.assertFalse([i for i in issues if i["level"] == "block"])

    def test_rounding_line_visible(self):
        rows, issues = ax.build_rows([stub()], {})
        self.assertEqual(sum(r["debit"] for r in rows), sum(r["credit"] for r in rows))
        self.assertTrue(any("עיגול" in i["text"] for i in issues) or not any(r["key"] == "rounding" for r in rows))

    def test_manual_stub_excluded(self):
        bad = stub()
        bad["national_insurance"] = None
        rows, issues = ax.build_rows([bad], {})
        self.assertEqual(rows, [])
        self.assertEqual(issues[0]["level"], "block")

    def test_per_employee_groups(self):
        rows, _ = ax.build_rows([stub("א"), stub("ב")], {}, per_employee=True)
        self.assertEqual({r["employee"] for r in rows}, {"א", "ב"})

    def test_missing_account_warns(self):
        _, issues = ax.build_rows([stub()], {"gross": "600"})
        self.assertTrue(any("מספר חשבון" in i["text"] for i in issues))

    def test_files(self):
        rows, _ = ax.build_rows([stub()], {"gross": "600"})
        for t in ax.TEMPLATES:
            data, name, mime = ax.build_file(rows, t, "חשבשבת", 2026, 3, "בדוי בע\"מ")
            self.assertTrue(data and name.endswith(("xlsx", "csv")))
        data, _, _ = ax.build_file(rows, "csv_utf8", "x", 2026, 3)
        got = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
        self.assertEqual(got[0][5:], ["חובה", "זכות"])
        self.assertEqual(sum(D(r[5]) for r in got[1:]), sum(D(r[6]) for r in got[1:]))
        self.assertEqual(got[1][0], "31/03/2026")

    def test_unknown_template(self):
        with self.assertRaises(ValueError):
            ax.build_file([], "nope", "", 2026, 1)


if __name__ == "__main__":
    unittest.main()


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os, sys, tempfile
        d = tempfile.mkdtemp()
        os.environ["DATABASE_URL"] = "sqlite:///" + d + "/a.db"
        os.environ["REQUIRE_2FA"] = "false"
        os.environ["JWT_SECRET"] = "x" * 40
        from cryptography.fernet import Fernet
        os.environ["FIELD_KEY"] = Fernet.generate_key().decode()
        sys.modules.pop("main_api", None)
        import main_api
        from fastapi.testclient import TestClient
        cls.c = TestClient(main_api.app)
        r = cls.c.post("/auth/register", json={"email": "acct.qa@example.com", "password": "Zebra-Orchid-Lantern-2026!", "full_name": "בדיקה"})
        cls.H = {"Authorization": "Bearer " + r.json()["access_token"]}
        cls.cid = cls.c.post("/companies", json={"name": "חברה בדויה", "tax_id": "000000000"}, headers=cls.H).json()["id"]

    def test_flow(self):
        p = {"emp_id_number": "900000019", "emp_name": "בדוי", "year": 2026, "month": 1, "base_salary": 12000,
             "credit_points": 2.25, "employee_pension_rate": 0.06, "employer_pension_rate": 0.065, "employer_severance_rate": 0.06}
        r = self.c.post(f"/companies/{self.cid}/calculate-paystub", json=p, headers=self.H)
        self.assertEqual(r.status_code, 200, r.text)
        b = {"year": 2026, "month": 1, "software": "בדיקה", "template": "xlsx", "accounts": {"gross": "600"}}
        chk = self.c.post(f"/companies/{self.cid}/reports/accounting/check", json=b, headers=self.H).json()
        self.assertEqual(chk["stubs"], 1)
        self.assertAlmostEqual(chk["debit"], chk["credit"], places=2)
        f = self.c.post(f"/companies/{self.cid}/reports/accounting/file", json=b, headers=self.H)
        self.assertEqual(f.status_code, 200)
        self.assertIn("journal-", f.headers["content-disposition"])
        empty = self.c.post(f"/companies/{self.cid}/reports/accounting/file", json=dict(b, month=5), headers=self.H)
        self.assertEqual(empty.status_code, 422)
