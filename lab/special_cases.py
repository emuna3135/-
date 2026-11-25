"""
מקרים חריגים מול חישוב בלתי תלוי שנגזר מנוסח רשמי:
- תקנות מס הכנסה (ניכוי ממשכורת ומשכר עבודה), התשנ"ג-1993 (btl.gov.il/Laws1/02_0103_100076.pdf, נקרא 25.11.2026): תוספת א' ו-ב', תקנה 4.
- עולה: §35 + עלון רשות המסים (כפי שמתועד ב-card.olim_points); חייל משוחרר: §39א (36 חודשים מהחודש שאחרי השחרור).
"""
import sys, datetime
from decimal import Decimal as D, ROUND_HALF_UP, ROUND_FLOOR
sys.path.insert(0, ".")
import engine as pe, card, special_payslips as sp

BR = [(7010, "0.10"), (10060, "0.14"), (19000, "0.20"), (25100, "0.31"), (46690, "0.35"), (60130, "0.47"), (None, "0.50")]


def shekel(x):
    """'כל שבר של שקל העולה על 49 אגורות יראוהו כשקל אחד' = עיגול half-up לשקל."""
    return D(str(x)).quantize(D("1"), rounding=ROUND_HALF_UP)


def annual_tax(annual, points):
    tax, prev = D(0), D(0)
    for up, r in BR:
        top = annual if up is None else min(annual, D(up) * 12)
        if top > prev:
            tax += (top - prev) * D(r)
        if up is None or annual <= D(up) * 12:
            break
        prev = D(up) * 12
    return max(tax - D(str(points)) * 242 * 12, D(0))


def ref_monthly(m, points):          # תוספת א'. שכר עם אגורות אינו מעוגל לפני החישוב: כך מתנהג סימולטור רשות המסים (test_engine.OfficialSimulatorTests),
    w = D(str(m))                    # אף שנוסח תוספת א' (5) מדבר גם על עיגול שבר שקל בשכר. הסתירה מתועדת ב-DATA_LEDGER ב364
    return shekel(annual_tax(w * 12, points) / 12)


def ref_daily(w, points):            # תוספת ב' (אותו עיגול כמו בחודשי; אין סימולטור יומי לאימות)
    w = D(str(w))
    return shekel(annual_tax(w * 300, points) / 300)


def ref_irregular_monthly(reg, irr, points):   # תקנה 4(א)
    return (ref_monthly(D(str(reg)) + D(str(irr)) / 12, points) - ref_monthly(reg, points)) * 12


def ref_olim(aliyah, year, month):
    k = (year - aliyah.year) * 12 + month - aliyah.month + 1
    if k < 1:
        return D(0)
    sched = [(12, 1), (30, 3), (42, 2), (54, 1)] if aliyah >= datetime.date(2022, 1, 1) else [(18, 3), (30, 2), (42, 1)]
    for upto, v in sched:
        if k <= upto:
            return D(v)
    return D(0)


def ref_soldier(discharge, full, year, month):
    k = (year - discharge.year) * 12 + month - discharge.month
    return D(2 if full else 1) if 1 <= k <= 36 else D(0)


def run():
    out = {"daily": [], "monthly_rounding": [], "irregular": [], "olim": [], "soldier": [], "n": 0}
    for pts in ("2.25", "2.75", "4.75"):
        for w in ("250", "280.4", "300.49", "300.50", "402.4", "500", "760.01", "1004", "1500", "1867.6", "2500", "4000"):
            out["n"] += 1
            got = pe.daily_wage_deduction(D(w), pts)["value"]
            exp = ref_daily(w, pts)
            if D(str(got)) != exp:
                out["daily"].append((w, pts, int(got), int(exp)))
        for m in ("5000", "7010.49", "7010.50", "9999.99", "12345.67", "19000", "25100.49", "40000", "60130", "80000"):
            out["n"] += 1
            got = pe.monthly_deduction_by_regulation(D(m), pts)
            exp = ref_monthly(m, pts)
            if D(str(got)) != exp:
                out["monthly_rounding"].append((m, pts, int(got), int(exp)))
        for reg, irr in (("8000", "1500"), ("12000", "8000"), ("12345.67", "5000"), ("30000", "50000"), ("6000", "20000")):
            out["n"] += 1
            got = sp.irregular_tax_reg4(2026, D(reg), D(irr), pts)["value"]
            exp = ref_irregular_monthly(reg, irr, pts)
            if D(str(got)) != exp:
                out["irregular"].append((reg, irr, pts, int(got), int(exp)))
            got2 = pe.irregular_salary_tax(D(reg), D(irr), pts)["value"]
            if D(str(got2)) != exp:
                out["irregular"].append(("engine", reg, irr, pts, int(got2), int(exp)))
    for ali in (datetime.date(2021, 6, 15), datetime.date(2022, 1, 1), datetime.date(2024, 3, 10), datetime.date(2025, 12, 31)):
        for y in (2026,):
            for m in range(1, 13):
                out["n"] += 1
                got = D(str(card.olim_points(ali, y, m)[0]))
                if got != ref_olim(ali, y, m):
                    out["olim"].append((str(ali), y, m, float(got), float(ref_olim(ali, y, m))))
    for dis in (datetime.date(2023, 12, 20), datetime.date(2025, 7, 2), datetime.date(2026, 3, 31)):
        for full in (True, False):
            for m in range(1, 13):
                out["n"] += 1
                got = D(str(card.discharged_soldier_points(dis, full, 2026, m)[0]))
                if got != ref_soldier(dis, full, 2026, m):
                    out["soldier"].append((str(dis), full, m, float(got), float(ref_soldier(dis, full, 2026, m))))
    return out


if __name__ == "__main__":
    o = run()
    print("cases", o["n"])
    for k in ("daily", "monthly_rounding", "irregular", "olim", "soldier"):
        print(k, len(o[k]), o[k][:6])
