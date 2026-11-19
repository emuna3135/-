"""
מחולל קובץ XML לממשק מעסיקים - דיווח שוטף (גרסה 006) של רשות שוק ההון, ביטוח וחיסכון.

מקור: קובץ ה-XSD הרשמי mimshak_maasikim_shotef_xsd_schema_006.xsd ואקסל האפיון "Employer interface V 6.xlsx"
(gov.il/BlobFolder/dynamiccollectorresultitem/info_0030/he/), נקראו 19.11.2026. ראו PENSION_XML_SPEC_NOTES.md.

העיקרון: המחולל לא ממציא נתונים. כל שדה חובה שחסר מדווח ברשימת missing, ואז לא נוצר קובץ (None).
התאמת הערכים לסכמה (אורך, ספרות, ערכי enum, תבנית) נבדקת כאן מול טבלה שהועתקה מה-XSD; אין כאן החלפה של הבדיקה
הרשמית של המסלקה (סביבת TEST: KOD-SVIVAT-AVODA=1).
"""
import re
import uuid
from datetime import datetime
from decimal import Decimal
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# מבנה הסכמה. שורה = שם|מינימום|מקסימום|סוג|פיצ'רים. הזחה (שני רווחים לרמה) = קינון.
# פיצ'רים: e=ערכים חוקיים, m=אורך מקסימלי, p=תבנית (regex), lo=מינימום, hi=מקסימום, td=totalDigits, fd=fractionDigits
# ---------------------------------------------------------------------------
GUID = r"[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}"
SCHEMA_TEXT = f"""
MimshakMaasikim|1|1|struct|
  KoteretKovetz|1|1|struct|
    SUG-MIMSHAK|1|1|int|e=12
    MISPAR-GIRSAT-XML|1|1|string|e=006
    TAARICH-BITZUA|1|1|string|p=\\d{{14}}
    KOD-SVIVAT-AVODA|1|1|int|e=1,2
    MISPAR-HAKOVETZ|1|1|string|m=34
    MISPAR-SIDURI|1|1|int|lo=0;td=4
    NetuneiGoremSholech|1|1|struct|
      KOD-SHOLECH|1|1|int|e=1,2,3,4,5,6
      SUG-MEZAHE-SHOLECH|1|1|int|e=1,2,3,4,5,7,8,9,10,11,12,13
      MISPAR-ZIHUI-SHOLECH|1|1|string|m=16
      SHEM-GOREM-SHOLECH|1|1|string|m=100
      SHEM-PRATI-ISH-KESHER-SHOLECH|1|1|string|m=20
      SHEM-MISHPACHA-ISH-KESHER-SHOLECH|1|1|string|m=20
      MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH|1|1|string|m=11;p=[0-9]+
      E-MAIL-ISH-KESHER-SHOLECH|1|1|string|m=50
      MISPAR-CELLULARI-ISH-KESHER-SHOLECH|1|1|string|m=15;p=[0-9]+
    NetuneiGoremNimaan|1|1|struct|
      KOD-NIMAAN|1|1|int|e=1,2,3,6
      SUG-MEZAHE-NIMAAN|1|1|int|e=1,2,3,4,5,7,8,9,10,11,12,13
      MISPAR-ZIHUI-NIMAAN|1|1|string|m=16
      MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN|1|1|string|m=16
  GufHamimshak|1|1|struct|
    YeshutGoremPoneLemislaka|1|n|struct|
      SUG-PONE|1|1|int|e=3,4,5,6
      SUG-KOD-MEZAHE-PONE|1|1|int|e=1,2,3,4,5,7,8,9,10,11,12,13
      MISPAR-MEZAHE-PONE|1|1|string|m=16
      SHEM-GOREM-PONE|1|1|string|m=50
      MISPAR-MEZAHE-METAFEL|1|1|string|m=16
      SHEM-PRATI-PONE-LEMISLAKA|1|1|string|m=20
      SHEM-MISHPACHA-PONE-LEMISLAKA|1|1|string|m=20
      MISPAR-TELEPHONE-KAVI-PONE-LEMISLAKA|1|1|string|m=11;p=[0-9]+
      E-MAIL-PONE-LEMISLAKA|1|1|string|m=50
      MISPAR-CELLULARI|1|1|string|m=15;p=[0-9]+
      PirteiHaavaratKsafim|1|n|struct|
        KOD-MEZAHE-KUPA-H-P|1|1|string|p=[0-9]{{30}}
        SUG-MAFKID|1|1|int|e=1,2,3
        SUG-MEZAHE-MAASIK|1|1|int|e=1,2,3,4,5,7,8,9,10,11,12,13
        MISPAR-ZIHUY-MAASIK|1|1|string|m=16
        MISPAR-TIK-NIKUIM-MAASIK|1|1|string|m=9
        KOD-MEZAHE-MAASIK-ETZEL-YATZRAN|1|1|string|m=16
        KOD-MASAV|1|1|string|m=16
        SCHUM-HAFKADA-KOLEL|1|1|decimal|lo=0;td=15;fd=2
        SHEM-MAASIK|1|1|string|m=100
        SHEM-PRATI-ISH-KESHER-MAASIK|1|1|string|m=20
        SHEM-MISHPACHA-ISH-KESHER-MAASIK|1|1|string|m=20
        MISPAR-TELEPHONE-KAVI-ISH-KESHER-MAASIK|1|1|string|m=20
        E-MAIL-ISH-KESHER-MAASIK|1|1|string|m=50
        MISPAR-CELLULARI-ISH-KESHER-MAASIK|1|1|string|m=15
        SUG-PEULA|1|1|int|e=1,2,3,7
        KOD-EMTZAI-TASHLUM|1|1|int|e=1,3,4,5,6,7,9
        SACH-HAFKADA-KUPA-H-P|1|1|decimal|lo=0;td=15;fd=2
        TAARICH-ERECH-HAFKADA-LEKUPA|1|1|date|
        TAARICH-ERECH-HAFKADA-CHESHBON-NEHEMANUT|1|1|date|
        MISPAR-ASMACHTA-LEAHAVARAT-KSAFIM|1|1|string|m=50
        MISPAR-ZIHUI|1|1|string|p={GUID}
        MISPAR-BANK-MAASIK|1|1|int|lo=0
        MISPAR-SNIF-MAASIK|1|1|string|p=[0-9]{{3}}
        MISPAR-CHESHBON-MAASIK|1|1|string|p=[0-9]{{20}}
        SUG-CHESHBON|1|1|string|p=[0-9]{{3}}
        SUG-KARTIS-MAASIK|0|1|int|e=1,2,3,4,5
        SUG-CHESHBON-MAASIK|1|1|int|e=1,2
        SUG-CHESHBON-KOLET-TASHLUM|1|1|int|e=1,2
        MISPAR-BANK-KOLET|1|1|int|lo=0
        MISPAR-SNIF-KOLET|1|1|string|p=[0-9]{{3}}
        MISPAR-CHESHBON-KOLET|1|1|string|p=[0-9]{{20}}
        MISPAR-ZIHUI-KODEM|1|1|string|p={GUID}
        MISPAR-MISLAKA|1|1|string|p={GUID}
        MISPAR-MISLAKA-KODEM|1|1|string|p={GUID}
        ZihuiShemMismachBeramatEirua|0|n|struct|
          SHEM-KOVETZ-SHEL-MISMACH-BERAMAT-EIRUA-VEBERAMAT-LAKOACH|1|1|string|m=100
          SUG-MISMACH|1|1|int|e=5
        PirteiKupa|1|n|struct|
          SUG-KUPA|1|1|int|e=1,2,3,4
          SUG-KEREN-PENSIA|1|1|int|e=1,2
          SHEM-KUPA-ETZEL-MAASIK|1|1|string|m=100
          MISPAR-KUPA-ETZEL-MAASIK|1|1|string|m=12
          PirteiOved|1|n|struct|
            SUG-MEZAHE-OVED|1|1|int|e=1,2
            MISPAR-MEZAHE|1|1|string|m=16
            SHEM-PRATI|1|1|string|m=20
            SHEM-MISHPACHA|1|1|string|m=20
            TAARICH-LEIDA|1|1|date|
            MISPAR-OVED-ETZEL-MAASIK|1|1|string|m=20
            KOD-MEZAHE-MAASIK-ETZEL-YATZRAN|0|1|string|m=16
            SHEM-YISHUV|1|1|string|m=20
            SHEM-RECHOV|1|1|string|m=50
            MISPAR-BAIT|1|1|string|m=8
            MISPAR-DIRA|1|1|int|lo=0;hi=99999;td=3
            MIKUD|1|1|int|lo=0;td=7
            TA-DOAR|1|1|int|lo=0;hi=99999;td=10
            E-MAIL|1|1|string|m=50
            MISPAR-CELLULARI|1|1|string|m=15
            MIN|1|1|int|e=1,2
            MOED-TCHILAT-AHASAKAT-OVED|1|1|date|
            HASHAVA-KIBUTZI|0|1|int|e=1,2
            HATZHARAT-OVED|0|1|int|e=1,2
            SEIF-ARBA-ESRE-LAOVED|1|1|int|e=1,2,3,4,5
            SEIF-ARBA-ESRE-TAHRIH-KNISA-LETOKEF|1|1|date|
            ChodeshMaskoretVestatusOved|1|n|struct|
              CHODESH-MASKORET|1|1|date|
              MAHAMAD-HAFKADA-BEKUPA|1|1|int|e=1,2,3
              SUG-TAKBUL|1|1|int|e=1,2,4,6,8
              ROVED-SACHAR|1|1|int|e=1,3,5,6,7
              SIBAT-BAKASH-LECHZER-KSAFIM|0|1|int|e=1,2,3,4,5,6,7,8,9,10
              SACHAR-MEDUVACH|1|1|decimal|lo=0;td=15;fd=2
              STATUS-OVED-BECHODESH-MASKORET|1|1|int|e=1,2,3,4,5,8,9,10,11,12,14,17,18
              TAARICH-TCHILAT-STATUS|1|1|date|
              CHELKIUT-MISRA|1|1|decimal|lo=1;hi=100;td=5;fd=2
              YEMEI-AVODA-BECHODESH|1|1|int|lo=0;hi=31;td=2
              MISPAR-POLISA-O-HESHBON|1|1|string|m=20
              HAFKADA-ACHRONA|1|1|int|e=1,2
              PizulHafrashotOvedBeKupa|0|n|struct|
                SUG-HAFRASHA|1|1|int|e=1,2,3,4,5,6,7,8
                SHIUR-HAFRASHA|1|1|decimal|td=4;fd=2
                SCHUM-HAFRASHA|1|1|decimal|lo=0;td=15;fd=2
                SACH-TASHLUMIM-PTURIM|1|1|decimal|td=15;fd=2
                MISPAR-MEZAHE-RESHUMA|1|1|string|p={GUID}
                MISPAR-MEZAHE-RESHUMA-KODEM|1|1|string|p={GUID}
              SachHafrashaLeKupaBechodeshMaskoretOved|1|1|struct|
                SACH-HAFRASHA-BECHODESH-MASKORET|1|1|decimal|lo=0;td=15;fd=2
            SachHafrashaLeOvedBekupa|1|1|struct|
              SACH-HAFRASHA-LEOVED-BEKUPA|1|1|decimal|lo=0;td=15;fd=2
          SachHafrashaLeKupaMaasik|0|1|struct|
            SACH-HAFRASHA-LEKUPA-BERAMAT-MAASIK|1|1|decimal|lo=0;td=15;fd=2
            SACH-HAFKADA-LEKUPA-BERAMAT-MAASIK|1|1|decimal|lo=0;td=15;fd=2
            MISPAR-AMITIM-BERAMAT-MAASIK|1|1|int|lo=0;td=6
  ReshumatSgira|1|1|struct|
    MISPAR-KUPOT-YATZRANIM-BAKOVETZ|1|1|int|td=6
    MISPAR-MAASIKIM|1|1|int|td=6
    MISPAR-RESHUMOT|1|1|int|lo=0;td=15
    MISPAR-AMITIM|1|1|int|lo=0;td=6
    SACH-HAFRASHOT-BAKOVETZ|1|1|decimal|lo=0;td=15;fd=2
    SACH-HAFKADOT-BAKOVETZ|1|1|decimal|lo=0;td=15;fd=2
"""

# ---------------------------------------------------------------------------
# פירוש הקודים, מתוך אקסל האפיון הרשמי (גיליון "ממשק מעסיקים - דיווח שוטף", עמודת הבהרות)
# ---------------------------------------------------------------------------
KOD_SVIVAT_AVODA = {1: "TEST", 2: "PRODUCTION"}
SUG_MEZAHE = {1: "ח.פ", 2: "ח.צ", 3: "ת.ז", 4: "דרכון", 5: "עוסק מורשה", 7: "עמותה", 8: "אגודה שיתופית",
              9: "חברה ממשלתית", 10: "איגוד", 11: "שותפות", 12: "מספר בעל רישיון", 13: "יישות ללא רשם"}
KOD_SHOLECH = {1: "יצרן", 2: "מסלקה", 3: "מפיץ", 4: "חוסך", 5: "מעסיק", 6: "מתפעל"}
SUG_MAFKID = {1: "מעסיק", 2: "עצמאי", 3: "מעסיק קטן"}
SUG_PEULA = {1: "דיווח רגיל/שוטף", 2: "תיקון תנועות ללא הפקדה נוספת", 3: "הפקדה נוספת ותיקון תנועות",
             7: "תיקון תשלומים פטורים"}
KOD_EMTZAI_TASHLUM = {1: "העברה בנקאית", 3: "כרטיס אשראי", 4: "שובר תשלום", 5: "סליקה באמצעות מסלקה פנסיונית",
                      6: "הרשאה לחיוב חשבון/הוראת קבע", 7: "סליקה באמצעות מס\"ב",
                      9: "הרשאה לחיוב חשבון על סמך קובץ דיווח שהועבר לגוף מוסדי"}
SUG_KUPA = {1: "קופת ביטוח", 2: "קרן פנסיה", 3: "קופת גמל", 4: "קרן השתלמות"}
SUG_KEREN_PENSIA = {1: "מקיפה", 2: "יסוד"}
MAAMAD_HAFKADA = {1: "שכיר", 2: "עצמאי", 3: "בעל שליטה"}
SUG_TAKBUL = {1: "שוטף", 2: "חד פעמי", 4: "הפרשים", 6: "חד פעמי - השלמת פיצויים עד שכר מבוטח כפול וותק",
              8: "חד פעמי - הפקדה לפיצויים מעל שכר מבוטח כפול וותק"}
ROVED_SACHAR = {1: "שכר יסוד", 3: "דמי הבראה", 5: "שעות נוספות", 6: "החזר הוצאות", 7: "אחר"}
STATUS_OVED = {1: "חודשי/רגיל", 2: "שעתי/יומי", 3: "היעדר שכר", 4: "עונתי", 5: "עזיבת עבודה", 8: "חופשה ללא תשלום",
               9: "פטירה", 10: "עובד החל להפקיד בקופה אחרת", 11: "מעבר ממשרד למשרד", 12: "פרישה לפנסיה",
               14: "עובד/עמית חדש", 17: "עזיבת עבודה - עובד זכאי לכספי פיצויים", 18: "תשלום + דיווח עזיבת עבודה עתידי"}
STATUS_STOPS_DEPOSITS = {3, 4, 5, 8, 9, 10, 11, 12, 17}   # לפי הערה 1 בשדה 74: אין לדווח פיצול הפרשות
SUG_HAFRASHA = {1: "פיצויים", 2: "תגמולי עובד", 3: "תגמולי מעביד", 4: "תגמולים 47", 5: "א.כ.ע עובד", 6: "א.כ.ע מעביד",
                7: "שונות עובד", 8: "שונות מעביד"}
SEIF_14 = {1: "כן, מתחילת העסקה", 2: "כן, מתאריך אחר", 3: "העובד לא חתום", 4: "לא חל יותר", 5: "קושי משפטי"}


class Node:
    def __init__(self, name, lo, hi, kind, facets):
        self.name, self.lo, self.hi, self.kind, self.facets, self.children = name, int(lo), (None if hi == "n" else int(hi)), kind, facets, []


def _parse(text):
    root, stack = None, []
    for line in text.strip("\n").split("\n"):
        depth = (len(line) - len(line.lstrip(" "))) // 2
        name, lo, hi, kind, fac = line.strip().split("|")
        facets = {}
        for part in filter(None, fac.split(";")):
            k, v = part.split("=", 1)
            facets[k] = v
        node = Node(name, lo, hi, kind, facets)
        if depth == 0:
            root = node
        else:
            stack[depth - 1].children.append(node)
        del stack[depth:]
        stack.append(node)
    return root


SCHEMA = _parse(SCHEMA_TEXT)


def _digits(s):
    return len(re.sub(r"\D", "", s))


def _format_leaf(node, value, path, errors):
    """מחזיר מחרוזת תקנית או None (ושגיאה) לפי הסוג והפיצ'רים."""
    f, k = node.facets, node.kind
    try:
        if k == "int":
            if isinstance(value, bool) or (isinstance(value, float) and value != int(value)):
                raise ValueError("לא מספר שלם")
            s = str(int(value))
        elif k == "decimal":
            d = Decimal(str(value))
            if "fd" in f:
                d = d.quantize(Decimal(1).scaleb(-int(f["fd"])))
            s = format(d, "f")
        elif k == "date":
            s = value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)
            datetime.strptime(s, "%Y-%m-%d")
        else:
            s = str(value)
    except Exception:
        errors.append(f"{path}: ערך לא תקין ({value!r}) לסוג {k}")
        return None
    if "e" in f and s not in f["e"].split(","):
        errors.append(f"{path}: הערך {s} אינו מבין הערכים המותרים {f['e']}")
        return None
    if "m" in f and len(s) > int(f["m"]):
        errors.append(f"{path}: אורך {len(s)} חורג מהמותר ({f['m']})")
        return None
    if "p" in f and not re.fullmatch(f["p"], s):
        errors.append(f"{path}: הערך אינו תואם לתבנית {f['p']}")
        return None
    if k in ("int", "decimal"):
        n = Decimal(s)
        if "lo" in f and n < Decimal(f["lo"]):
            errors.append(f"{path}: {s} קטן מ-{f['lo']}")
            return None
        if "hi" in f and n > Decimal(f["hi"]):
            errors.append(f"{path}: {s} גדול מ-{f['hi']}")
            return None
        if "td" in f and _digits(s.lstrip("-")) > int(f["td"]):
            errors.append(f"{path}: יותר מ-{f['td']} ספרות")
            return None
    if node.name == "TAARICH-BITZUA":
        try:
            datetime.strptime(s, "%Y%m%d%H%M%S")
        except ValueError:
            errors.append(f"{path}: תאריך ושעה לא חוקיים")
            return None
    return s


def _emit(node, data, path, out, missing, errors, indent):
    pad = "  " * indent
    if node.kind == "struct":
        items = data if isinstance(data, list) else ([data] if data else [])
        if not items:
            if node.lo >= 1:
                missing.append(path)
            return
        if node.hi == 1 and len(items) > 1:
            errors.append(f"{path}: מותר מופע אחד")
        for i, item in enumerate(items):
            p = f"{path}[{i}]" if node.hi != 1 else path
            out.append(f"{pad}<{node.name}>")
            for child in node.children:
                _emit(child, (item or {}).get(child.name), f"{p}/{child.name}", out, missing, errors, indent + 1)
            out.append(f"{pad}</{node.name}>")
        return
    if data is None or data == "":
        if node.lo >= 1:
            missing.append(path)
        return
    values = data if isinstance(data, list) else [data]
    for v in values:
        s = _format_leaf(node, v, path, errors)
        if s is not None:
            out.append(f"{pad}<{node.name}>{escape(s)}</{node.name}>")


def _count(data):
    """ספירות ל-ReshumatSgira מתוך העץ: קופות/יצרנים, מעסיקים, רשומות (שורות חודש-עובד), עמיתים."""
    kupot, employers, records, amitim = set(), set(), 0, set()
    fr = fd = Decimal(0)
    for pone in _as_list(data.get("GufHamimshak", {}).get("YeshutGoremPoneLemislaka")):
        for h in _as_list(pone.get("PirteiHaavaratKsafim")):
            employers.add(h.get("MISPAR-ZIHUY-MAASIK"))
            kupot.add(h.get("KOD-MEZAHE-KUPA-H-P"))
            fd += Decimal(str(h.get("SCHUM-HAFKADA-KOLEL") or 0))
            for k in _as_list(h.get("PirteiKupa")):
                for o in _as_list(k.get("PirteiOved")):
                    amitim.add((h.get("MISPAR-ZIHUY-MAASIK"), o.get("MISPAR-MEZAHE")))
                    for m in _as_list(o.get("ChodeshMaskoretVestatusOved")):
                        records += 1
                        for pz in _as_list(m.get("PizulHafrashotOvedBeKupa")):
                            fr += Decimal(str(pz.get("SCHUM-HAFRASHA") or 0))
    return {"MISPAR-KUPOT-YATZRANIM-BAKOVETZ": len(kupot), "MISPAR-MAASIKIM": len(employers), "MISPAR-RESHUMOT": records,
            "MISPAR-AMITIM": len(amitim), "SACH-HAFRASHOT-BAKOVETZ": fr, "SACH-HAFKADOT-BAKOVETZ": fd}


def _as_list(x):
    return x if isinstance(x, list) else ([x] if x else [])


def autofill(data, now=None):
    """משלים רק מה שהמערכת קובעת בעצמה: קבועי גרסה, חותמת זמן, מזהי GUID (גרסה 4) וספירות הסגירה. לא נוגע בערכים קיימים."""
    now = now or datetime.now()
    kot = data.setdefault("KoteretKovetz", {})
    kot.setdefault("SUG-MIMSHAK", 12)
    kot.setdefault("MISPAR-GIRSAT-XML", "006")
    kot.setdefault("TAARICH-BITZUA", now.strftime("%Y%m%d%H%M%S"))
    for pone in _as_list(data.get("GufHamimshak", {}).get("YeshutGoremPoneLemislaka")):
        for h in _as_list(pone.get("PirteiHaavaratKsafim")):
            h.setdefault("MISPAR-ZIHUI", str(uuid.uuid4()).upper())
            for k in _as_list(h.get("PirteiKupa")):
                for o in _as_list(k.get("PirteiOved")):
                    for m in _as_list(o.get("ChodeshMaskoretVestatusOved")):
                        for pz in _as_list(m.get("PizulHafrashotOvedBeKupa")):
                            pz.setdefault("MISPAR-MEZAHE-RESHUMA", str(uuid.uuid4()).upper())
    data.setdefault("ReshumatSgira", {})
    for key, val in _count(data).items():
        data["ReshumatSgira"].setdefault(key, val)
    return data


def build(data, fill=True, now=None):
    """
    data: עץ מקונן לפי שמות האלמנטים ב-XSD (מבנה חוזר = רשימה). מחזיר dict:
    xml (מחרוזת או None אם יש חסרים/שגיאות), missing (נתיבי שדות חובה חסרים), errors (ערכים שאינם תואמים לסכמה).
    """
    if fill:
        data = autofill(data, now)
    out, missing, errors = [], [], []
    _emit(SCHEMA, data, SCHEMA.name, out, missing, errors, 0)
    # הערת סעיף 1 בשדה 74: סטטוס שמלמד על הפסקת הפקדות -> אין לדווח פיצול הפרשות
    for pone in _as_list(data.get("GufHamimshak", {}).get("YeshutGoremPoneLemislaka")):
        for h in _as_list(pone.get("PirteiHaavaratKsafim")):
            for k in _as_list(h.get("PirteiKupa")):
                for o in _as_list(k.get("PirteiOved")):
                    for m in _as_list(o.get("ChodeshMaskoretVestatusOved")):
                        if m.get("STATUS-OVED-BECHODESH-MASKORET") in STATUS_STOPS_DEPOSITS and m.get("PizulHafrashotOvedBeKupa"):
                            errors.append(f"עובד {o.get('MISPAR-MEZAHE')}: סטטוס {m.get('STATUS-OVED-BECHODESH-MASKORET')} "
                                          "מלמד על הפסקת הפקדות - אין לדווח פיצול הפרשות (אקסל האפיון, שדה 74, הערה 1)")
    xml = None
    if not missing and not errors:
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(out) + "\n"
    return {"xml": xml, "missing": missing, "errors": errors}
