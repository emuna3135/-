import datetime, unittest
from decimal import Decimal as D
import masav as M


def pay(i=1, **kw):
    d = dict(bank="12", branch="345", account="123456", id_number="000000018", name="דנה כהן", amount="1234.56", ref=i)
    d.update(kw)
    return d


def build(pays, **kw):
    return M.build(pays, "12345678", "54321", "חברה בדויה", datetime.date(2026, 12, 9), created=datetime.date(2026, 12, 1), **kw)


class Masav(unittest.TestCase):
    def test_layout_positions(self):
        data, s = build([pay()], reverse_names=False)
        lines = data.decode("cp862").split("\r\n")
        h, t, tot, eof = lines[0], lines[1], lines[2], lines[3]
        self.assertEqual(len(h), 128); self.assertEqual(h[0], "K"); self.assertEqual(h[1:9], "12345678")
        self.assertEqual(h[9:11], "00"); self.assertEqual(h[11:17], "261209"); self.assertEqual(h[17], "0")
        self.assertEqual(h[18:21], "001"); self.assertEqual(h[21], "0"); self.assertEqual(h[22:28], "261201")
        self.assertEqual(h[28:33], "54321"); self.assertEqual(h[33:39], "000000"); self.assertEqual(h[125:128], "KOT")
        self.assertEqual(len(t), 128); self.assertEqual(t[0], "1"); self.assertEqual(t[1:9], "12345678")
        self.assertEqual(t[17:19], "12"); self.assertEqual(t[19:22], "345"); self.assertEqual(t[22:26], "0000")
        self.assertEqual(t[26:35], "000123456"); self.assertEqual(t[35], "0"); self.assertEqual(t[36:45], "000000018")
        self.assertEqual(t[61:74], "0000000123456"); self.assertEqual(t[105:108], "006"); self.assertEqual(t[126:128], "  ")
        self.assertEqual(len(tot), 128); self.assertEqual(tot[0], "5"); self.assertEqual(tot[21:36], "000000000123456")
        self.assertEqual(tot[51:58], "0000001"); self.assertEqual(eof, "9" * 128)
        self.assertEqual(data.count(b"\r\n"), 4)

    def test_balanced(self):
        data, s = build([pay(1), pay(2, amount="100.05", id_number="000000026"), pay(3, amount="0.01", id_number="000000034")])
        self.assertEqual(M.verify(data), []); self.assertEqual(s["total"], D("1334.62")); self.assertEqual(s["count"], 3)

    def test_errors_collected(self):
        with self.assertRaises(ValueError) as c:
            build([pay(id_number="123456789"), pay(2, amount="0"), pay(3, amount="10.005"), pay(4, bank="123"), pay(5, account="12a")])
        self.assertEqual(str(c.exception).count("תנועה"), 5)

    def test_empty(self):
        with self.assertRaises(ValueError): build([])

    def test_verify_detects_tamper(self):
        data, _ = build([pay()])
        lines = data.decode("cp862").split("\r\n")
        lines[1] = lines[1][:61] + "0000000123457" + lines[1][74:]
        bad = "\r\n".join(lines).encode("cp862")
        self.assertIn("סכום התנועות אינו שווה לסיכום", M.verify(bad))

    def test_notes_flag_unverified(self):
        _, s = build([pay()])
        self.assertTrue(any("אימות" in n for n in s["notes"]))


if __name__ == "__main__":
    unittest.main()
