"""קובץ אקסל לדוגמה "כמו שחשבת שכר מקבלת מלקוח": 30 עובדים בדיוניים מגוונים, חודש ינואר 2026 (חודש ראשון, בלי מצטבר קודם).
בפורמט התבנית של המערכת (upload_template). נתונים בדויים בלבד, ת.ז. עם ספרת ביקורת בטווח המעבדה.
הרצה: python3 lab/sample_client_excel.py -> lab/sample_client_30.xlsx"""
import sys, io, random
sys.path.insert(0, ".")
import openpyxl
import upload_template as UT
from lab import synthetic_lab as S

rng = random.Random(2026)
FIRST_F = ["דנה", "מיכל", "רונית", "נועה", "שירה", "אורית", "תמר", "יעל", "הדס", "לימור", "ענת", "מירב"]
FIRST_M = ["יוסי", "אבי", "דוד", "עומר", "אלון", "רועי", "גיל", "משה", "ניר", "איתי", "עידן", "שלומי"]
LAST = ["כהן", "לוי", "מזרחי", "פרץ", "ביטון", "אברהם", "דהן", "אוחיון", "שרעבי", "גולן", "חדד", "בן דוד", "סבן", "אזולאי"]
STREETS = ["הרצל", "ביאליק", "הנביאים", "אלנבי", "רוטשילד", "סוקולוב", "הגפן", "הרימון"]
CITIES = [("תל אביב", "61000"), ("חיפה", "33000"), ("באר שבע", "84000"), ("ירושלים", "91000"), ("נתניה", "42000"), ("אשדוד", "77000")]
BASES = [6443.85, 7200, 8500, 9500, 11000, 12500, 14000, 16500, 19000, 23000, 28000, 35000, 45000]
SPECIAL = [("niptar", "הורה יחיד"), ("mezonut", "משלם מזונות"), ("nomesh", "חי בנפרד ללא משק בית משותף")]


def make(n=30, month=1, year=2026):
    emps, used = [], set()
    for i in range(n):
        g = rng.choice("FM")
        while True:      # שמות ייחודיים, כדי שבמסכים אפשר יהיה להבדיל בין עובדים
            first = rng.choice(FIRST_F if g == "F" else FIRST_M)
            last = rng.choice(LAST)
            if (first, last) not in used:
                used.add((first, last)); break
        married = rng.random() < .55
        flag = None
        if not married and rng.random() < .15:
            flag = rng.choice(SPECIAL[:1])
        nk = rng.choice([0, 0, 1, 2, 2, 3, 4])
        cust = sorted(rng.choice([2008, 2012, 2015, 2018, 2020, 2022, 2024, 2025]) for _ in range(nk))
        idn = S.make_id(700000 + i)
        base = rng.choice(BASES)
        scope = rng.choice([100, 100, 100, 100, 80, 50])
        city, zipc = rng.choice(CITIES)
        start = f"{rng.choice([2015, 2018, 2020, 2022, 2024, 2025])}-{rng.randint(1, 12):02d}-01"
        emps.append(dict(idn=idn, g=g, first=first, last=last, married=married, flag=flag, cust=cust, base=base, scope=scope,
                         street=f"{rng.choice(STREETS)} {rng.randint(1, 80)}", city=city, zip=zipc, start=start,
                         pen=rng.choice([0.06, 0.06, 0.06, 0.055]), sf=rng.choice([0, 0, 0.025]),
                         ot125=rng.choice([0, 0, 0, 6, 10, 14]), ot150=rng.choice([0, 0, 0, 3, 5]),
                         bonus=rng.choice([0, 0, 0, 0, 1000, 2500, 5000]), life=rng.choice([0, 0, 0, 0, 120, 250]),
                         tax_free=rng.choice([0, 0, 0, 0, 0, 150]), other=rng.choice([0, 0, 0, 0, 200, 450])))
    return emps


def build(path="lab/sample_client_30.xlsx", n=30, month=1, year=2026):
    wb = openpyxl.load_workbook(io.BytesIO(UT.build_template()))
    emps = make(n, month, year)
    ws_m, ws_e, ws_f, ws_p = wb["תלושים לטעינה"], wb["עובדים"], wb["טופס 101"], wb["מעביד"]
    for ws in (ws_m, ws_e, ws_f):
        ws.delete_rows(2, ws.max_row)
    skipped = []
    for e in emps:
        pts, st, note, errs, val = S.points_via_101(e["idn"], e["g"], e["married"], ("niptar",) if e["flag"] else None, [year - y for y in e["cust"]], [])
        if pts is None or errs:
            skipped.append((e["idn"], note[:60])); continue
        full = f"{e['first']} {e['last']}"
        hourly = round(e["base"] / 182, 2)
        ws_m.append([e["idn"], full, e["base"], e["ot125"], e["ot150"], e["bonus"], float(pts), year, month, e["tax_free"], e["pen"], e["sf"], e["life"],
                     "cumulative", "22 ימים", "0 / 10", "0 / 8", "העברה בנקאית", hourly, None, None, None, None, None])
        ws_e.append([e["idn"], full, e["g"], f"{rng.randint(1965, 2003)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}", e["start"], "כן", e["base"],
                     e["pen"], 0.065, 0.06, e["scope"], e["last"], e["first"], e["street"], e["city"], e["zip"]])
        marital = "נשוי/אה" if e["married"] else rng.choice(["רווק/ה", "רווק/ה", "גרוש/ה"])
        ws_f.append([e["idn"], full, year, f"{year}-01-05", "משרה עיקרית", "לא", "כאן", marital,
                     ", ".join(map(str, e["cust"])) or None, None, "הורה יחיד" if e["flag"] else None])
    for ws, cols in ((ws_m, (1,)), (ws_e, (1, 16)), (ws_f, (1,))):
        for row in ws.iter_rows(min_row=2):
            for c in cols:
                row[c - 1].number_format = "@"
    ws_p.delete_rows(2, ws_p.max_row)
    ws_p.append(["חברה בדיונית בע\"מ", "912345678", "515000000", "035551234", "חברה", "חייב", 0, None, "515000000", "ח.פ", "000000000", "רות", "כהן", "demo@example.test", "0501111111"])
    wb["פנסיה"].delete_rows(2, wb["פנסיה"].max_row)
    wb.save(path)
    return len(emps) - len(skipped), skipped


if __name__ == "__main__":
    k, sk = build()
    print(k, "עובדים;", len(sk), "דולגו", sk)
