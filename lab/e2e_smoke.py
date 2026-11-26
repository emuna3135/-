"""הרצה מקצה לקצה של main_api מול SQLite זמני, נתונים בדיוניים בלבד (TestClient, ללא רשת)."""
import os, sys, json, tempfile
sys.path.insert(0, ".")
d = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{d}/t.db")
from cryptography.fernet import Fernet
os.environ.setdefault("FIELD_KEY", Fernet.generate_key().decode())
from fastapi.testclient import TestClient
import main_api
from lab import synthetic_lab as S

c = TestClient(main_api.app)
res = []
def chk(name, r, ok=(200,)):
    good = r.status_code in ok
    res.append((name, r.status_code, good))
    if not good:
        print("FAIL", name, r.status_code, r.text[:300])
    return r

r = chk("health", c.get("/health"))
r = chk("register", c.post("/auth/register", json={"email": "fict@example.test", "password": "Aq9!zXv#2026kLm", "full_name": "בדיוני"}))
tok = r.json().get("access_token")
H = {"Authorization": f"Bearer {tok}"}
chk("login", c.post("/auth/login", json={"email": "fict@example.test", "password": "Aq9!zXv#2026kLm"}))
r = chk("company", c.post("/companies", json={"name": "חברה בדיונית", "tax_id": None}, headers=H))
cid = r.json()["id"]
chk("companies", c.get("/companies", headers=H))
chk("profile put", c.put(f"/companies/{cid}/profile", headers=H, json=dict(file_no="912345678", agid=0, legal_status=1, tax_file_no="123456", name="חברה בדיונית", phone="31234567", employer_tax=1)))
ids = []
for i in range(3):
    r = chk(f"employee{i}", c.post(f"/companies/{cid}/employees", headers=H, json=dict(
        id_number=S.make_id(500000 + i), full_name=f"עובד בדיוני {i}", gender="F" if i % 2 else "M", start_date="2026-01-01",
        base_salary=9000 + 1500 * i, bank_code="12", bank_branch="600", bank_account_no=str(1000000 + i),
        family_name="בדיוני", first_name=f"עובד{i}", street="הרצל", city="תל אביב", zip="61000")))
    if r.status_code == 200: ids.append(r.json()["id"])
chk("employees list", c.get(f"/companies/{cid}/employees", headers=H))
for e in ids:
    chk("form101", c.put(f"/companies/{cid}/employees/{e}/form101/2026", headers=H, json=dict(signed_on="2026-01-02", marital="married", custody_birth_years=[2018])))
    for m in range(1, 11):
        chk(f"calculate m{m}", c.post(f"/companies/{cid}/employees/{e}/calculate", headers=H, json=dict(year=2026, month=m, ot_hours_125=5 if m == 10 else 0)))
chk("paystubs", c.get(f"/companies/{cid}/paystubs", headers=H))
chk("payslip", c.post(f"/companies/{cid}/employees/{ids[0]}/payslip", headers=H, json=dict(year=2026, month=10)), ok=(200, 422))
chk("balances", c.post(f"/companies/{cid}/balances", headers=H, json=dict(kind="vacation", year_of_service=2, opening=3, used=1)))
chk("payments-summary", c.get(f"/companies/{cid}/payments-summary?year=2026&month=10", headers=H))
chk("masav", c.post(f"/companies/{cid}/masav", headers=H, json=dict(year=2026, month=10, institution_code="12345678", sending_code="12345", pay_date="2026-11-09", institution_name="חברה בדיונית")), ok=(200, 422))
chk("form102-tax", c.post(f"/companies/{cid}/form102-tax", headers=H, json=dict(year=2026, month=10, represent_number="123456789", taxpayer_number="123456789", register_number="12")), ok=(200,))
chk("employer-cost", c.get(f"/companies/{cid}/reports/employer-cost?year=2026&month=10", headers=H), ok=(200, 422))
chk("month-status", c.get(f"/companies/{cid}/month-status?year=2026&month=10", headers=H))
chk("month-sheet", c.get(f"/companies/{cid}/month-sheet?year=2026&month=10", headers=H))
chk("sources", c.get("/sources", headers=H))
chk("params", c.get(f"/companies/{cid}/params", headers=H))
chk("audit-log", c.get(f"/companies/{cid}/audit-log", headers=H))
chk("126 check", c.post(f"/companies/{cid}/reports/126/check", headers=H, json=dict(year=2026, hebrew_visual=False, encoding="cp1255")), ok=(200,))
chk("106 check", c.post(f"/companies/{cid}/reports/106/check", headers=H, json=dict(year=2026)), ok=(200, 422))
chk("templates", c.get("/templates", headers=H))
chk("upload-template", c.get("/upload-template"))
bad = [x for x in res if not x[2]]
print(len(res), "קריאות;", len(bad), "כשלו")
for n, s_, g in res:
    if not g or "calculate" not in n: print(("OK  " if g else "FAIL"), s_, n)

r = c.post(f"/companies/{cid}/form102-tax", headers=H, json=dict(year=2026, month=10, represent_number="123456789", taxpayer_number="123456789", register_number="12"))
o = r.json()
print("102:", o["status"], o["summary"], o["input"]["PaymentAmount"])
assert o["summary"]["employees"] == 3
s126 = c.post(f"/companies/{cid}/reports/126/check", headers=H, json=dict(year=2026, hebrew_visual=False, encoding="cp1255"))
print("126 check:", s126.status_code, str(s126.json())[:300])
