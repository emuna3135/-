"""קובץ פנסיה (ממשק מעסיקים, דיווח שוטף חודשי, גרסה 006) מנתוני המערכת. פונקציות טהורות. המערכת רק יוצרת קובץ XML; לא שולחת דבר.

מקור המבנה: ה-XSD הרשמי של רשות שוק ההון (pension_xml.SCHEMA). המערכת ממלאת בעצמה רק מה שמחושב בתלושים (סכומי הפרשה, שכר, שיעורים)
ופרטי עובד שבכרטיס; פרטי הקופה והבנק וקודי המזהים נלקחים מגיליון 'פנסיה' בתבנית ומגיליון 'מעביד'. שדה חובה שאין לו מקור לא מומצא:
הוא מופיע ברשימת 'נדרש טיפול ידני', והקובץ שיוצא אז הוא טיוטה בלבד (לא תקף לשליחה).
קרן השתלמות עדיין לא נתמכת (אין בתלוש השמור סכום הפקדת עובד להשתלמות).
"""
import re
from datetime import date, datetime
from decimal import Decimal

import pension_xml as px

LABELS = {
    "KOD-MEZAHE-KUPA-H-P": "קוד מזהה קופה (30 ספרות)", "SUG-KUPA": "סוג קופה", "SUG-KEREN-PENSIA": "סוג קרן פנסיה",
    "SHEM-KUPA-ETZEL-MAASIK": "שם הקופה אצל המעסיק", "MISPAR-KUPA-ETZEL-MAASIK": "מספר קופה אצל המעסיק",
    "KOD-NIMAAN": "סוג הגוף הנמען", "SUG-MEZAHE-NIMAAN": "סוג מזהה הגוף הנמען", "MISPAR-ZIHUI-NIMAAN": "מזהה הגוף הנמען",
    "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN": "מזהה הנמען אצל היצרן",
    "KOD-MEZAHE-MAASIK-ETZEL-YATZRAN": "מזהה המעסיק אצל הגוף המוסדי", "KOD-MASAV": "קוד מס\"ב",
    "KOD-EMTZAI-TASHLUM": "אמצעי תשלום", "MISPAR-BANK-MAASIK": "בנק המעסיק", "MISPAR-SNIF-MAASIK": "סניף המעסיק",
    "MISPAR-CHESHBON-MAASIK": "חשבון המעסיק (20 ספרות)", "SUG-CHESHBON": "סוג חשבון (3 ספרות)",
    "SUG-CHESHBON-MAASIK": "חשבון המעסיק ישראלי/זר", "SUG-CHESHBON-KOLET-TASHLUM": "חשבון הקולט ישראלי/זר",
    "MISPAR-BANK-KOLET": "בנק הקולט", "MISPAR-SNIF-KOLET": "סניף הקולט", "MISPAR-CHESHBON-KOLET": "חשבון הקולט (20 ספרות)",
    "MISPAR-ZIHUI-KODEM": "מזהה דיווח קודם", "MISPAR-MISLAKA": "מזהה מסלקה", "MISPAR-MISLAKA-KODEM": "מזהה מסלקה קודם",
    "MISPAR-MEZAHE-RESHUMA-KODEM": "מזהה רשומת הפרשה קודמת", "MISPAR-POLISA-O-HESHBON": "מספר פוליסה או חשבון",
    "MISPAR-OVED-ETZEL-MAASIK": "מספר עובד אצל המעסיק", "SEIF-ARBA-ESRE-LAOVED": "סעיף 14",
    "SEIF-ARBA-ESRE-TAHRIH-KNISA-LETOKEF": "תאריך כניסת סעיף 14 לתוקף", "MAHAMAD-HAFKADA-BEKUPA": "מעמד הפקדה",
    "E-MAIL": "אימייל העובד", "MISPAR-CELLULARI": "נייד", "MISPAR-BAIT": "מספר בית", "MISPAR-DIRA": "מספר דירה",
    "MIKUD": "מיקוד (7 ספרות)", "TA-DOAR": "תא דואר", "YEMEI-AVODA-BECHODESH": "ימי עבודה בחודש",
    "SHEM-YISHUV": "עיר", "SHEM-RECHOV": "רחוב", "SHEM-PRATI": "שם פרטי", "SHEM-MISHPACHA": "שם משפחה",
    "TAARICH-LEIDA": "תאריך לידה", "MIN": "מין", "MOED-TCHILAT-AHASAKAT-OVED": "תאריך תחילת עבודה",
    "MISPAR-ZIHUY-MAASIK": "מספר זיהוי מעביד", "SUG-MEZAHE-MAASIK": "סוג מזהה מעביד", "SUG-MEZAHE-SHOLECH": "סוג מזהה מעביד",
    "MISPAR-ZIHUI-SHOLECH": "מספר זיהוי מעביד", "SUG-KOD-MEZAHE-PONE": "סוג מזהה מעביד", "MISPAR-MEZAHE-PONE": "מספר זיהוי מעביד",
    "MISPAR-MEZAHE-METAFEL": "מזהה מתפעל", "MISPAR-TIK-NIKUIM-MAASIK": "תיק ניכויים",
    "TAARICH-ERECH-HAFKADA-LEKUPA": "תאריך ערך ההפקדה", "TAARICH-ERECH-HAFKADA-CHESHBON-NEHEMANUT": "תאריך ערך ההפקדה",
    "MISPAR-ASMACHTA-LEAHAVARAT-KSAFIM": "מספר אסמכתא להעברה",
}
CONTACT_KEYS = ("SHEM-PRATI-ISH-KESHER-SHOLECH", "SHEM-MISHPACHA-ISH-KESHER-SHOLECH", "E-MAIL-ISH-KESHER-SHOLECH",
                "MISPAR-CELLULARI-ISH-KESHER-SHOLECH", "SHEM-PRATI-PONE-LEMISLAKA", "SHEM-MISHPACHA-PONE-LEMISLAKA",
                "E-MAIL-PONE-LEMISLAKA", "MISPAR-CELLULARI", "SHEM-PRATI-ISH-KESHER-MAASIK", "SHEM-MISHPACHA-ISH-KESHER-MAASIK",
                "E-MAIL-ISH-KESHER-MAASIK", "MISPAR-CELLULARI-ISH-KESHER-MAASIK")
for _k in CONTACT_KEYS:
    LABELS.setdefault(_k, "איש קשר של המעביד (בגיליון 'מעביד')")
LABELS["MISPAR-CELLULARI"] = "נייד"


def _val(x):
    return x.get("value") if isinstance(x, dict) else x


def _dec(x):
    return Decimal(str(x or 0)).quantize(Decimal("0.01"))


def _latest(year, month, stubs):
    out = {}
    for s in stubs:
        if s.get("year") == year and s.get("month") == month:
            out[str(s.get("emp_id_number"))] = s
    return out


def _pct(rate):
    return Decimal(str(rate)) * 100 if rate is not None else None


def _oved(emp, row, stub, year, month):
    first = date(year, month, 1)
    sd = emp.get("start_date")
    if isinstance(sd, str) and sd:
        sd = date.fromisoformat(sd)
    bd = emp.get("birth_date")
    if isinstance(bd, str) and bd:
        bd = date.fromisoformat(bd)
    pe = _dec(stub.get("pension_employee"))
    er = _dec(_val((stub.get("employer") or {}).get("pension")))
    sv = _dec(_val((stub.get("employer") or {}).get("severance")))
    rates = ((2, pe, emp.get("pension_employee_rate")), (3, er, emp.get("employer_pension_rate")),
             (1, sv, emp.get("employer_severance_rate")))
    pz = [{"SUG-HAFRASHA": code, "SHIUR-HAFRASHA": _pct(rate), "SCHUM-HAFRASHA": amt, "SACH-TASHLUMIM-PTURIM": 0}
          for code, amt, rate in rates if amt > 0]
    total = pe + er + sv
    seif = row.get("seif14")
    node = {
        "SUG-MEZAHE-OVED": 1, "MISPAR-MEZAHE": str(emp["id_number"]).zfill(9),
        "SHEM-PRATI": emp.get("first_name"), "SHEM-MISHPACHA": emp.get("family_name"), "TAARICH-LEIDA": bd,
        "MISPAR-OVED-ETZEL-MAASIK": row.get("emp_no"), "SHEM-YISHUV": emp.get("city"), "SHEM-RECHOV": emp.get("street"),
        "MISPAR-BAIT": row.get("house_no"), "MISPAR-DIRA": row.get("apartment", 0), "MIKUD": row.get("mikud"),
        "TA-DOAR": row.get("po_box", 0), "E-MAIL": row.get("email"), "MISPAR-CELLULARI": row.get("mobile"),
        "MIN": {"M": 1, "F": 2}.get(emp.get("gender")), "MOED-TCHILAT-AHASAKAT-OVED": sd,
        "SEIF-ARBA-ESRE-LAOVED": seif,
        "SEIF-ARBA-ESRE-TAHRIH-KNISA-LETOKEF": sd if seif in (1, 2) else None,
        "ChodeshMaskoretVestatusOved": [{
            "CHODESH-MASKORET": first, "MAHAMAD-HAFKADA-BEKUPA": row.get("maamad"), "SUG-TAKBUL": 1, "ROVED-SACHAR": 1,
            "SACHAR-MEDUVACH": _dec(stub.get("pension_base")), "STATUS-OVED-BECHODESH-MASKORET": 1,
            "TAARICH-TCHILAT-STATUS": first, "CHELKIUT-MISRA": emp.get("position_scope_percent", 100),
            "YEMEI-AVODA-BECHODESH": row.get("work_days"), "MISPAR-POLISA-O-HESHBON": row.get("policy"),
            "HAFKADA-ACHRONA": 2,
            "PizulHafrashotOvedBeKupa": [dict(z, **{"MISPAR-MEZAHE-RESHUMA-KODEM": row.get("prev_record_id")}) for z in pz],
            "SachHafrashaLeKupaBechodeshMaskoretOved": {"SACH-HAFRASHA-BECHODESH-MASKORET": total}}],
        "SachHafrashaLeOvedBekupa": {"SACH-HAFRASHA-LEOVED-BEKUPA": total},
    }
    return node, total


def build_files(profile, year, month, employees, pension_rows, stubs, *, env, value_date, asmachta, serial=1, now=None):
    """מחזיר רשימת קבצים: [{name, xml, draft, missing, errors, employees, total}] (קובץ לכל גוף נמען) + issues כלליים."""
    pen = (profile or {}).get("pension") or {}
    issues = []
    if not pension_rows:
        return [], [{"level": "block", "scope": "", "text": "לא הוזנו פרטי קופות. ממלאים את גיליון 'פנסיה' בתבנית ומעלים"}]
    emps = {str(e["id_number"]): e for e in employees}
    stub_by = _latest(year, month, stubs)
    groups = {}
    for row in pension_rows:
        idn = str(row["id_number"])
        if idn not in emps:
            issues.append({"level": "warn", "scope": f'ת"ז {idn[-4:].rjust(9, "*")}', "text": "מופיע בגיליון 'פנסיה' אך אינו קיים בעובדים; לא נכלל"})
            continue
        if row.get("fund_type") is None:
            issues.append({"level": "block", "scope": f'ת"ז *****{idn[-4:]}', "text": "חסר סוג קופה (קרן השתלמות עדיין לא נתמכת)"})
            continue
        if idn not in stub_by:
            continue                                   # אין תלוש לחודש הזה: אין הפקדה
        key = (row.get("nimaan_kind"), row.get("nimaan_id_type"), row.get("nimaan_id"), row.get("nimaan_at_producer"))
        groups.setdefault(key, {}).setdefault(row.get("fund_code") or "", []).append(row)
    if not groups:
        issues.append({"level": "block", "scope": "", "text": f"אין תלושים לחודש {month:02d}/{year} של העובדים שבגיליון 'פנסיה'"})
        return [], issues
    files = []
    for n, (nk, funds) in enumerate(sorted(groups.items(), key=lambda kv: str(kv[0])), 1):
        hafkadot, fund_rows = [], []
        for code, rows in funds.items():
            r0 = rows[0]
            ovdim, total, kinds = [], Decimal(0), []
            for row in rows:
                node, t = _oved(emps[str(row["id_number"])], row, stub_by[str(row["id_number"])], year, month)
                ovdim.append(node)
                total += t
            fund_rows.append(rows)
            hafkadot.append({
                "KOD-MEZAHE-KUPA-H-P": code or None, "SUG-MAFKID": 1, "SUG-MEZAHE-MAASIK": pen.get("employer_id_type"),
                "MISPAR-ZIHUY-MAASIK": pen.get("employer_id"), "MISPAR-TIK-NIKUIM-MAASIK": profile.get("file_no"),
                "KOD-MEZAHE-MAASIK-ETZEL-YATZRAN": r0.get("employer_at_producer"), "KOD-MASAV": r0.get("masav"),
                "SCHUM-HAFKADA-KOLEL": total, "SHEM-MAASIK": profile.get("name"),
                "SHEM-PRATI-ISH-KESHER-MAASIK": pen.get("contact_first"), "SHEM-MISHPACHA-ISH-KESHER-MAASIK": pen.get("contact_last"),
                "MISPAR-TELEPHONE-KAVI-ISH-KESHER-MAASIK": profile.get("phone"), "E-MAIL-ISH-KESHER-MAASIK": pen.get("contact_email"),
                "MISPAR-CELLULARI-ISH-KESHER-MAASIK": pen.get("contact_mobile"), "SUG-PEULA": 1,
                "KOD-EMTZAI-TASHLUM": r0.get("pay_method"), "SACH-HAFKADA-KUPA-H-P": total,
                "TAARICH-ERECH-HAFKADA-LEKUPA": value_date, "TAARICH-ERECH-HAFKADA-CHESHBON-NEHEMANUT": value_date,
                "MISPAR-ASMACHTA-LEAHAVARAT-KSAFIM": asmachta,
                "MISPAR-BANK-MAASIK": r0.get("bank"), "MISPAR-SNIF-MAASIK": r0.get("branch"),
                "MISPAR-CHESHBON-MAASIK": r0.get("account"), "SUG-CHESHBON": r0.get("account_type"),
                "SUG-CHESHBON-MAASIK": r0.get("employer_acc_kind"), "SUG-CHESHBON-KOLET-TASHLUM": r0.get("collector_acc_kind"),
                "MISPAR-BANK-KOLET": r0.get("collector_bank"), "MISPAR-SNIF-KOLET": r0.get("collector_branch"),
                "MISPAR-CHESHBON-KOLET": r0.get("collector_account"), "MISPAR-ZIHUI-KODEM": r0.get("prev_id"),
                "MISPAR-MISLAKA": r0.get("mislaka"), "MISPAR-MISLAKA-KODEM": r0.get("mislaka_prev"),
                "PirteiKupa": [{"SUG-KUPA": r0.get("fund_type"), "SUG-KEREN-PENSIA": r0.get("pension_kind"),
                                "SHEM-KUPA-ETZEL-MAASIK": r0.get("fund_name"), "MISPAR-KUPA-ETZEL-MAASIK": r0.get("fund_no"),
                                "PirteiOved": ovdim}]})
        contact = {"first": pen.get("contact_first"), "last": pen.get("contact_last"), "email": pen.get("contact_email"),
                   "mobile": pen.get("contact_mobile")}
        data = {
            "KoteretKovetz": {
                "KOD-SVIVAT-AVODA": 1 if env == "test" else 2,
                "MISPAR-HAKOVETZ": f'{profile.get("file_no")}{year}{month:02d}{n:02d}', "MISPAR-SIDURI": serial,
                "NetuneiGoremSholech": {
                    "KOD-SHOLECH": 5, "SUG-MEZAHE-SHOLECH": pen.get("employer_id_type"), "MISPAR-ZIHUI-SHOLECH": pen.get("employer_id"),
                    "SHEM-GOREM-SHOLECH": profile.get("name"), "SHEM-PRATI-ISH-KESHER-SHOLECH": contact["first"],
                    "SHEM-MISHPACHA-ISH-KESHER-SHOLECH": contact["last"],
                    "MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH": profile.get("phone"),
                    "E-MAIL-ISH-KESHER-SHOLECH": contact["email"], "MISPAR-CELLULARI-ISH-KESHER-SHOLECH": contact["mobile"]},
                "NetuneiGoremNimaan": {"KOD-NIMAAN": nk[0], "SUG-MEZAHE-NIMAAN": nk[1], "MISPAR-ZIHUI-NIMAAN": nk[2],
                                       "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN": nk[3]}},
            "GufHamimshak": {"YeshutGoremPoneLemislaka": [{
                "SUG-PONE": 5, "SUG-KOD-MEZAHE-PONE": pen.get("employer_id_type"), "MISPAR-MEZAHE-PONE": pen.get("employer_id"),
                "SHEM-GOREM-PONE": profile.get("name"), "MISPAR-MEZAHE-METAFEL": pen.get("operator_id"),
                "SHEM-PRATI-PONE-LEMISLAKA": contact["first"], "SHEM-MISHPACHA-PONE-LEMISLAKA": contact["last"],
                "MISPAR-TELEPHONE-KAVI-PONE-LEMISLAKA": profile.get("phone"), "E-MAIL-PONE-LEMISLAKA": contact["email"],
                "MISPAR-CELLULARI": contact["mobile"], "PirteiHaavaratKsafim": hafkadot}]}}
        res = px.build(data, fill=True, now=now)
        draft_xml = res["xml"]
        if draft_xml is None:                          # טיוטה: מה שיש, בלי שדות חסרים (אינה תקפה לשליחה)
            out, miss, err = [], [], []
            data2 = px.autofill(data, now)
            px._emit(px.SCHEMA, data2, px.SCHEMA.name, out, miss, err, 0)
            draft_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(out) + "\n"
        files.append({"name": f"pension-{year}{month:02d}-{n}" + ("" if res["xml"] else "-DRAFT") + ".xml",
                      "xml": draft_xml, "draft": res["xml"] is None, "missing": res["missing"], "errors": res["errors"],
                      "fund_rows": fund_rows,
                      "employees": sum(len(r) for r in fund_rows),
                      "total": float(sum(_dec(h["SCHUM-HAFKADA-KOLEL"]) for h in hafkadot))})
    return files, issues


def to_issues(files, base_issues):
    """רשימת בעיות בעברית: לכל שדה חסר, פעם אחת לכל קופה/עובד (בלי ת"ז מלאה)."""
    issues = list(base_issues)
    for f in files:
        seen = set()
        for path in f["missing"]:
            leaf = path.split("/")[-1].split("[")[0]
            m = re.findall(r"\[(\d+)\]", path)
            scope = "מעביד"
            if "PirteiHaavaratKsafim" in path:
                j = int(re.search(r"PirteiHaavaratKsafim\[(\d+)\]", path).group(1)) if "PirteiHaavaratKsafim[" in path else 0
                k = re.search(r"PirteiOved\[(\d+)\]", path)
                rows = f["fund_rows"][j] if j < len(f["fund_rows"]) else []
                if k and int(k.group(1)) < len(rows):
                    scope = 'ת"ז *****' + str(rows[int(k.group(1))]["id_number"])[-4:]
                elif rows:
                    scope = "קופה " + str(rows[0].get("fund_name") or rows[0].get("fund_code") or j + 1)
            text = LABELS.get(leaf, leaf)
            if (scope, text) in seen:
                continue
            seen.add((scope, text))
            issues.append({"level": "block", "scope": scope, "text": f"חסר: {text} (נדרש טיפול ידני)"})
        for e in f["errors"]:
            issues.append({"level": "block", "scope": "", "text": re.sub(r"\d{9}", lambda mo: "*****" + mo.group(0)[-4:], e)})
    return issues


def run(profile, year, month, employees, pension_rows, stubs, *, env, value_date, asmachta):
    files, base = build_files(profile, year, month, employees, pension_rows, stubs, env=env,
                              value_date=value_date, asmachta=asmachta)
    issues = to_issues(files, base)
    return files, issues, not any(i["level"] == "block" for i in issues)
