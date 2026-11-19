import copy
import re
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime
import pension_xml as px

G = "0A1B2C3D-0000-4000-8000-0123456789AB"


def month(status=1, amount="650.00"):
    pz = [] if status in px.STATUS_STOPS_DEPOSITS else [
        {"SUG-HAFRASHA": 2, "SHIUR-HAFRASHA": "6.00", "SCHUM-HAFRASHA": amount, "SACH-TASHLUMIM-PTURIM": "0",
         "MISPAR-MEZAHE-RESHUMA-KODEM": G}]
    return {"CHODESH-MASKORET": date(2026, 10, 1), "MAHAMAD-HAFKADA-BEKUPA": 1, "SUG-TAKBUL": 1, "ROVED-SACHAR": 1,
            "SACHAR-MEDUVACH": "10000", "STATUS-OVED-BECHODESH-MASKORET": status, "TAARICH-TCHILAT-STATUS": date(2026, 10, 1),
            "CHELKIUT-MISRA": "100", "YEMEI-AVODA-BECHODESH": 22, "MISPAR-POLISA-O-HESHBON": "12345",
            "HAFKADA-ACHRONA": 2, "PizulHafrashotOvedBeKupa": pz,
            "SachHafrashaLeKupaBechodeshMaskoretOved": {"SACH-HAFRASHA-BECHODESH-MASKORET": amount}}


def employee(i, status=1):
    return {"SUG-MEZAHE-OVED": 1, "MISPAR-MEZAHE": f"30000000{i}", "SHEM-PRATI": "דנה", "SHEM-MISHPACHA": "לוי",
            "TAARICH-LEIDA": date(1990, 5, 17), "MISPAR-OVED-ETZEL-MAASIK": str(i), "SHEM-YISHUV": "חיפה",
            "SHEM-RECHOV": "הנשיא", "MISPAR-BAIT": "5", "MISPAR-DIRA": 3, "MIKUD": 3300000, "TA-DOAR": 0,
            "E-MAIL": "a@b.co", "MISPAR-CELLULARI": "0501234567", "MIN": 2, "MOED-TCHILAT-AHASAKAT-OVED": date(2020, 1, 1),
            "SEIF-ARBA-ESRE-LAOVED": 1, "SEIF-ARBA-ESRE-TAHRIH-KNISA-LETOKEF": date(2020, 1, 1),
            "ChodeshMaskoretVestatusOved": [month(status)],
            "SachHafrashaLeOvedBekupa": {"SACH-HAFRASHA-LEOVED-BEKUPA": "650.00"}}


def full():
    h = {"KOD-MEZAHE-KUPA-H-P": "5" * 9 + "0" * 21, "SUG-MAFKID": 1, "SUG-MEZAHE-MAASIK": 1, "MISPAR-ZIHUY-MAASIK": "515000000",
         "MISPAR-TIK-NIKUIM-MAASIK": "912345678", "KOD-MEZAHE-MAASIK-ETZEL-YATZRAN": "1", "KOD-MASAV": "12345678",
         "SCHUM-HAFKADA-KOLEL": "1300", "SHEM-MAASIK": "חברת דמו", "SHEM-PRATI-ISH-KESHER-MAASIK": "רות",
         "SHEM-MISHPACHA-ISH-KESHER-MAASIK": "כהן", "MISPAR-TELEPHONE-KAVI-ISH-KESHER-MAASIK": "035551234",
         "E-MAIL-ISH-KESHER-MAASIK": "x@y.co", "MISPAR-CELLULARI-ISH-KESHER-MAASIK": "0501111111", "SUG-PEULA": 1,
         "KOD-EMTZAI-TASHLUM": 7, "SACH-HAFKADA-KUPA-H-P": "1300", "TAARICH-ERECH-HAFKADA-LEKUPA": date(2026, 11, 15),
         "TAARICH-ERECH-HAFKADA-CHESHBON-NEHEMANUT": date(2026, 11, 15), "MISPAR-ASMACHTA-LEAHAVARAT-KSAFIM": "A1",
         "MISPAR-BANK-MAASIK": 12, "MISPAR-SNIF-MAASIK": "600", "MISPAR-CHESHBON-MAASIK": "0" * 18 + "12", "SUG-CHESHBON": "001",
         "SUG-CHESHBON-MAASIK": 1, "SUG-CHESHBON-KOLET-TASHLUM": 1, "MISPAR-BANK-KOLET": 10, "MISPAR-SNIF-KOLET": "100",
         "MISPAR-CHESHBON-KOLET": "0" * 18 + "99", "MISPAR-ZIHUI-KODEM": G, "MISPAR-MISLAKA": G, "MISPAR-MISLAKA-KODEM": G,
         "PirteiKupa": [{"SUG-KUPA": 2, "SUG-KEREN-PENSIA": 1, "SHEM-KUPA-ETZEL-MAASIK": "פנסיה", "MISPAR-KUPA-ETZEL-MAASIK": "1",
                         "PirteiOved": [employee(1), employee(2)]}]}
    return {"KoteretKovetz": {"KOD-SVIVAT-AVODA": 1, "MISPAR-HAKOVETZ": "1", "MISPAR-SIDURI": 1,
                              "NetuneiGoremSholech": {"KOD-SHOLECH": 5, "SUG-MEZAHE-SHOLECH": 1, "MISPAR-ZIHUI-SHOLECH": "515000000",
                                                      "SHEM-GOREM-SHOLECH": "חברת דמו", "SHEM-PRATI-ISH-KESHER-SHOLECH": "רות",
                                                      "SHEM-MISHPACHA-ISH-KESHER-SHOLECH": "כהן",
                                                      "MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH": "035551234",
                                                      "E-MAIL-ISH-KESHER-SHOLECH": "x@y.co",
                                                      "MISPAR-CELLULARI-ISH-KESHER-SHOLECH": "0501111111"},
                              "NetuneiGoremNimaan": {"KOD-NIMAAN": 2, "SUG-MEZAHE-NIMAAN": 1, "MISPAR-ZIHUI-NIMAAN": "512345678",
                                                     "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN": "7"}},
            "GufHamimshak": {"YeshutGoremPoneLemislaka": [{
                "SUG-PONE": 5, "SUG-KOD-MEZAHE-PONE": 1, "MISPAR-MEZAHE-PONE": "515000000", "SHEM-GOREM-PONE": "חברת דמו",
                "MISPAR-MEZAHE-METAFEL": "1", "SHEM-PRATI-PONE-LEMISLAKA": "רות", "SHEM-MISHPACHA-PONE-LEMISLAKA": "כהן",
                "MISPAR-TELEPHONE-KAVI-PONE-LEMISLAKA": "035551234", "E-MAIL-PONE-LEMISLAKA": "x@y.co",
                "MISPAR-CELLULARI": "0501111111", "PirteiHaavaratKsafim": [h]}]}}


class PensionXml(unittest.TestCase):
    def test_full_report_builds_and_parses(self):
        r = px.build(full(), now=datetime(2026, 11, 19, 10, 0, 0))
        self.assertEqual((r["missing"], r["errors"]), ([], []))
        root = ET.fromstring(r["xml"].encode("utf8"))
        self.assertEqual(root.tag, "MimshakMaasikim")
        self.assertEqual([c.tag for c in root], ["KoteretKovetz", "GufHamimshak", "ReshumatSgira"])
        k = root.find("KoteretKovetz")
        self.assertEqual(k.findtext("SUG-MIMSHAK"), "12"); self.assertEqual(k.findtext("MISPAR-GIRSAT-XML"), "006")
        self.assertEqual(k.findtext("TAARICH-BITZUA"), "20261119100000")
        s = root.find("ReshumatSgira")
        self.assertEqual(s.findtext("MISPAR-AMITIM"), "2"); self.assertEqual(s.findtext("MISPAR-RESHUMOT"), "2")
        self.assertEqual(s.findtext("SACH-HAFRASHOT-BAKOVETZ"), "1300.00"); self.assertEqual(s.findtext("SACH-HAFKADOT-BAKOVETZ"), "1300.00")
        self.assertEqual(s.findtext("MISPAR-MAASIKIM"), "1"); self.assertEqual(s.findtext("MISPAR-KUPOT-YATZRANIM-BAKOVETZ"), "1")
        guid = r"[A-F0-9]{8}(-[A-F0-9]{4}){3}-[A-F0-9]{12}"
        self.assertTrue(re.fullmatch(guid, root.find(".//PirteiHaavaratKsafim/MISPAR-ZIHUI").text))
        self.assertEqual(len({e.text for e in root.iter("MISPAR-MEZAHE-RESHUMA")}), 2)   # מזהה ייחודי לכל רשומה

    def test_element_order_follows_schema(self):
        r = px.build(full())
        tags = re.findall(r"<([A-Za-z0-9-]+)>", r["xml"])
        i = tags.index("PirteiOved")
        seg = tags[i:i + 4]
        self.assertEqual(seg[1], "SUG-MEZAHE-OVED")
        self.assertLess(tags.index("SUG-KUPA"), tags.index("PirteiOved"))

    def test_missing_required_blocks_file(self):
        d = full()
        del d["GufHamimshak"]["YeshutGoremPoneLemislaka"][0]["PirteiHaavaratKsafim"][0]["MISPAR-CHESHBON-MAASIK"]
        d["GufHamimshak"]["YeshutGoremPoneLemislaka"][0]["PirteiHaavaratKsafim"][0]["KOD-MEZAHE-KUPA-H-P"] = None
        r = px.build(d)
        self.assertIsNone(r["xml"])
        self.assertTrue(any(p.endswith("MISPAR-CHESHBON-MAASIK") for p in r["missing"]))
        self.assertTrue(any(p.endswith("KOD-MEZAHE-KUPA-H-P") for p in r["missing"]))

    def test_value_validation(self):
        d = full()
        h = d["GufHamimshak"]["YeshutGoremPoneLemislaka"][0]["PirteiHaavaratKsafim"][0]
        h["KOD-MEZAHE-KUPA-H-P"] = "123"        # חייב 30 ספרות
        h["SUG-PEULA"] = 4                      # לא ב-enum
        h["SHEM-MAASIK"] = "x" * 101            # ארוך מדי
        h["PirteiKupa"][0]["PirteiOved"][0]["MIN"] = 3
        r = px.build(d)
        self.assertIsNone(r["xml"]); self.assertEqual(len(r["errors"]), 4)

    def test_stopped_deposit_status_rejects_split(self):
        d = full()
        m = d["GufHamimshak"]["YeshutGoremPoneLemislaka"][0]["PirteiHaavaratKsafim"][0]["PirteiKupa"][0]["PirteiOved"][0]["ChodeshMaskoretVestatusOved"][0]
        m["STATUS-OVED-BECHODESH-MASKORET"] = 5          # עזיבת עבודה
        r = px.build(d)
        self.assertTrue(any("הפסקת הפקדות" in e for e in r["errors"]))

    def test_autofill_does_not_override(self):
        d = full(); d["KoteretKovetz"]["TAARICH-BITZUA"] = "20250101000000"
        self.assertIn("<TAARICH-BITZUA>20250101000000<", px.build(d)["xml"])

    def test_xml_escaping(self):
        d = full(); d["GufHamimshak"]["YeshutGoremPoneLemislaka"][0]["SHEM-GOREM-PONE"] = 'א&ב <"ג">'
        x = px.build(d)["xml"]; self.assertIn("א&amp;ב &lt;", x); ET.fromstring(x.encode("utf8"))

    def test_schema_parsed(self):
        names = []
        def walk(n):
            names.append(n.name); [walk(c) for c in n.children]
        walk(px.SCHEMA)
        self.assertEqual(len(names), 135)   # מספר האלמנטים ב-XSD v006 (שוטף), נספר מהקובץ הרשמי ב-19.11.2026
