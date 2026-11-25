"""
מעבדת בדיקות עם עובדים בדויים בלבד (ת.ז. נוצרות עם ספרת ביקורת תקינה; אין קשר לאנשים אמיתיים).
מריצה: טופס 101 (coerce+validate) -> נקודות זיכוי -> 12 תלושי 2026 מצטברים -> בדיקות נגד מקורות בלתי תלויים.
הערה: לא עוברת דרך main_api (אין fastapi בסביבה); משחזרת את compute() ברמת המנוע. חיווט ה-API נבדק בפריסה.
"""
import sys, random, json, datetime
from decimal import Decimal as D
sys.path.insert(0, ".")
import engine as pe, card, proposals, components, deductions, labor_rules as L
import simulator_results_2026 as sim

YEAR = 2026
rng = random.Random(20261125)


def make_id(n):
    s = f"{n:08d}"
    tot = 0
    for i, ch in enumerate(s):
        x = int(ch) * (1 if i % 2 == 0 else 2)
        tot += x - 9 if x > 9 else x
    return s + str((10 - tot % 10) % 10)


# --- מקרי נקודות מתוך סימולטור רשות המסים (מקור בלתי תלוי) ---
def sim_cases():
    out = []
    for g, married, flag, cust, noncust, total in sim.R:
        out.append(dict(gender=g, married=married, flag=flag, cust=cust, noncust=noncust, expected=total))
    return out


def raw101(idn, gender, married, flag, cust, noncust):
    """שדות כפי שהיו נקראים מטופס 101 (גולמיים, כולל מחרוזות)."""
    return {"id_number": idn, "tax_year": YEAR, "signed_on": f"{YEAR}-01-05", "income_type": "main",
            "other_income": False, "other_credits_claimed": False,
            "marital": "married" if married else "single",
            "custody_birth_years": [YEAR - a for a in cust], "noncustody_birth_years": [YEAR - a for a in noncust],
            "family_flags": (list(flag) if isinstance(flag, (tuple, list)) else [flag]) if flag else [], "city": "תל אביב"}


def points_via_101(idn, gender, married, flag, cust, noncust, month=1):
    raw = raw101(idn, gender, married, flag, cust, noncust)
    clean, errs, ign = proposals.coerce(proposals.KIND_FORM101, raw)
    val = proposals.validate(proposals.KIND_FORM101, clean, ctx={"id_number": idn, "is_resident": True, "gender": gender},
                             today=datetime.date(YEAR, 1, 20))
    y = proposals.form101_to_employee_year(clean)
    pts, st, note = card.points_from_form101(YEAR, True, gender, y, month)
    return pts, st, note, errs, val


def indep_tax(taxable_cum, months, points, deposits_cum):
    """חישוב מס מצטבר בלתי תלוי: מדרגות 2026 x חודשים, פחות נקודות x242 x חודשים, פחות 35% הפקדות עד תקרה; מעוגל לשקל."""
    br = [(7010, .10), (10060, .14), (19000, .20), (25100, .31), (46690, .35), (60130, .47), (None, .50)]
    g = D(str(taxable_cum)); tax = D(0); prev = D(0)
    for up, r in br:
        top = g if up is None else min(g, D(up) * months)
        if top > prev:
            tax += (top - prev) * D(str(r))
        if up is None or g <= D(up) * months:
            break
        prev = D(up) * months
    cr = D(str(points)) * 242 * months + min(D(str(deposits_cum)), D(679) * months) * D("0.35")
    return tax - cr


def indep_ni_health(g):
    g = D(str(g)); cap = D(51910); g = min(g, cap); t = D(7703)
    lo, hi = min(g, t), max(g - t, D(0))
    return lo * D("0.0104") + hi * D("0.07"), lo * D("0.0323") + hi * D("0.0517")


def payslip(emp, month, prev):
    base = D(str(emp["base"]))
    hourly = base / D(182)
    ot = hourly * D("1.25") * D(str(emp["ot125"])) + hourly * D("1.5") * D(str(emp["ot150"]))
    bonus = D(str(emp["bonus"]) if month in emp["bonus_months"] else 0)
    core = base + ot + bonus
    ex, ex_pen, lines, open_ = components.extras_for_paystub(emp["components"], f"2026-{month:02d}", emp["pension_codes"])
    cash = core + ex
    pbase = base + ex_pen + (ot if emp["pen_ot"] else 0) + (bonus if emp["pen_bonus"] else 0)
    ben = {}
    if emp["phone"]:
        ben["phone"] = pe.phone_benefit(emp["phone"])["value"]
    if emp["car_price"]:
        c = pe.car_benefit(emp["car_price"], "regular", False, year=YEAR)
        if c["value"] is None:
            raise ValueError("car")
        ben["car"] = c["value"]
    nc = sum(ben.values(), D(0))
    gross = cash + nc
    ded = deductions.month_deductions(emp["deductions"], YEAR, month)
    pts = emp["points"]
    r = pe.compute_month(year=YEAR, month=month, gross=gross, taxable_gross=gross, points=pts, mode="cumulative", prev=prev,
                         pension_employee_rate=D(str(emp["pen_rate"])), study_fund_employee_rate=D(str(emp["sf_rate"])),
                         pension_base=pbase, noncash_benefits=nc, other_deductions=ded["amount"],
                         employer_pension_rate=D("0.065"), employer_severance_rate=D("0.06"), employer_study_fund_rate=D("0.075"))
    return dict(month=month, gross=gross, ot=ot, bonus=bonus, noncash=nc, pbase=pbase, ded=ded["amount"], r=r, cash=cash, ex=ex)


def gen_employees(n=30):
    emps = []
    for i in range(n):
        g = rng.choice("FM")
        married = rng.random() < .55
        nk = rng.choice([0, 0, 1, 2, 2, 3])
        ages = sorted(rng.choice([0, 1, 2, 3, 4, 5, 8, 12, 17]) for _ in range(nk))
        emp = dict(idn=make_id(100000 + i), gender=g, married=married, cust=ages, noncust=[], flag=None,
                   base=rng.choice([6000, 6443.85, 8000, 9500, 12000, 15000, 22000, 35000, 60000]),
                   ot125=rng.choice([0, 0, 8, 12]), ot150=rng.choice([0, 0, 4]),
                   bonus=rng.choice([0, 0, 1500, 8000]), bonus_months=[3, 12],
                   phone=rng.choice([0, 0, 250]), car_price=rng.choice([0, 0, 0, 160000, 240000]),
                   components=[], pension_codes=[], pen_ot=False, pen_bonus=False,
                   pen_rate=rng.choice([0.06, 0.06, 0.055]), sf_rate=rng.choice([0, 0.025]),
                   deductions=[])
        if rng.random() < .3:
            emp["deductions"] = [dict(code="L1", kind="advance", monthly="500", start="2026-02", total="2000")]
        emps.append(emp)
    return emps


def run():
    findings, rows = [], []
    # 1) נקודות: כל מקרי הסימולטור דרך שכבת 101
    bad = 0
    for i, c in enumerate(sim_cases()):
        pts, st, note, errs, val = points_via_101(make_id(900000 + i), c["gender"], c["married"], c["flag"], c["cust"], c["noncust"])
        if errs:
            findings.append(("101-coerce", f"{c}: {errs}")); bad += 1
        elif pts is None:
            findings.append(("points-manual", f"{c['gender']} married={c['married']} flag={c['flag']} cust={c['cust']}: MANUAL ({note[:60]})")); bad += 1
        elif D(str(pts)) != D(str(c["expected"])):
            findings.append(("points-mismatch", f"{c}: got {pts} expected {c['expected']}")); bad += 1
    n_sim = len(sim_cases())
    # 2) תלושים
    table = []
    inv = dict(net_mismatch=0, tax_mismatch=0, ni_mismatch=0, cum_mismatch=0, manual=0, total=0)
    for e in gen_employees():
        pts, st, note, errs, val = points_via_101(e["idn"], e["gender"], e["married"], e["flag"], e["cust"], e["noncust"])
        if pts is None or errs:
            findings.append(("employee-points-manual", f"{e['idn']} {e['gender']} kids={e['cust']}: {note[:70]} {errs}"))
            continue
        e["points"] = pts
        prev = None
        cum_taxable = D(0); cum_dep = D(0); tax_sum = 0
        for m in range(1, 13):
            if m == 1:
                prev = None
            p = payslip(e, m, prev)
            r = p["r"]; inv["total"] += 1
            items = r["items"]
            if any(v["value"] is None for v in items.values()):
                inv["manual"] += 1; continue
            table.append([e["idn"], e["gender"], "נשוי" if e["married"] else "לא נשוי", len(e["cust"]), pts, m,
                          float(pe.r2(p["gross"])), float(p["noncash"]), float(p["pbase"]), float(items["income_tax"]["value"]), float(pe.r2(items["national_insurance"]["value"])),
                          float(pe.r2(items["health"]["value"])), float(items["pension_employee"]["value"]), float(r["net"]),
                          float(pe.r2(p["gross"] - sum((pe.r2(v["value"]) for v in items.values()), D(0)) - p["noncash"] - p["ded"])),
                          r["overall_status"]])
            # נתיב מצטבר: התלוש הבא נשען על ה-cum שהמנוע החזיר
            prev = r.get("cum") or r.get("cumulative")
            tax = D(str(items["income_tax"]["value"]))
            tax_sum += tax
            cum_taxable += p["gross"]; cum_dep += D(str(items["pension_employee"]["value"]))
            # בדיקה בלתי תלויה: מס מצטבר
            exp = indep_tax(cum_taxable, m, pts, cum_dep)
            exp = max(exp, D(0))
            if abs(D(str(round(exp))) - tax_sum) > 1:
                inv["tax_mismatch"] += 1
                rows.append(("tax", e["idn"], m, float(exp), float(tax_sum)))
            ni, h = indep_ni_health(p["gross"])
            if abs(D(str(items["national_insurance"]["value"])) - ni) > D("0.005") or abs(D(str(items["health"]["value"])) - h) > D("0.005"):
                inv["ni_mismatch"] += 1
                rows.append(("ni", e["idn"], m, float(ni), float(items["national_insurance"]["value"])))
            # net = gross - שורות מוצגות (מעוגלות לאגורה)
            shown = sum((pe.r2(v["value"]) for v in items.values()), D(0)) + p["noncash"] + p["ded"]
            if abs(pe.r2(p["gross"] - shown) - D(str(r["net"]))) > 0:
                inv["net_mismatch"] += 1
                rows.append(("net", e["idn"], m, float(pe.r2(p["gross"] - shown)), float(r["net"])))
    run.table = table
    return dict(sim_total=n_sim, sim_bad=bad, inv=inv, findings=findings, rows=rows[:40])


if __name__ == "__main__":
    out = run()
    from collections import Counter
    print("sim:", out["sim_total"], "bad:", out["sim_bad"]); print("inv:", out["inv"])
    print(Counter(k for k, _ in out["findings"]))
    for f in out["findings"][:12]: print(f)
    for r in out["rows"][:10]: print(r)
