import unittest
import attendance_pdf as a


def W(text, x0, top, w=20):
    return {"text": text, "x0": x0, "x1": x0 + w, "top": top}


def base_words(rows, report_regular="5:00", report_total="5:00"):
    ws = [W("01/11/2026", 183, 37), W("30/11/2026", 183, 51), W("313520660", 487, 37, 40), W("50", 355, 65),
          W("ש.רגילו", 288, 89), W("סה\"כ", 386, 89), W("יציאה", 417, 93), W("כניסה", 449, 93), W("קוד", 40, 89),
          W(".125%", 225, 101), W(".150%", 193, 101), W(".100%", 257, 101)]
    top = 116
    for date, inn, out, tot, reg, ot125 in rows:
        ws.append(W(date, 569, top))
        ws.append(W("רגיל", 496, top))
        if inn: ws.append(W(inn, 449, top))
        if out: ws.append(W(out, 417, top))
        if tot: ws.append(W(tot, 388, top))
        if reg: ws.append(W(reg, 292, top))
        if ot125: ws.append(W(ot125, 228, top))
        top += 14
    ws.append(W(report_regular, 289, top + 20))
    ws.append(W(report_total, 384, top + 20))
    return ws


class AttendanceTests(unittest.TestCase):
    def test_basic_and_verified(self):
        r = a.parse_words(base_words([("01/11", "08:00", "10:00", "2:00", "2:00", None),
                                      ("02/11", "08:00", "11:00", "3:00", "3:00", None)]))
        self.assertEqual(r["totals"]["regular_min"], 300)
        self.assertEqual(r["verification"], "מאומת מול סיכום הדוח")
        self.assertEqual(r["period_from"], "01/11/2026")
        self.assertEqual(r["id_number"], "313520660")
        self.assertEqual(r["warnings"], [])

    def test_mismatch_with_report_total_warns(self):
        r = a.parse_words(base_words([("01/11", "08:00", "10:00", "2:00", "2:00", None)], "3:00", "3:00"))
        self.assertEqual(r["verification"], "סכום הימים שונה מסיכום הדוח")

    def test_wrapped_shift_two_rows_same_date(self):
        ws = base_words([("03/11", None, "16:33", "2:58", "2:58", None)], "2:58", "2:58")
        ws.append(W("03/11", 569, 130)); ws.append(W("16:33", 449, 130)); ws.append(W("19:31", 417, 130))
        ws.sort(key=lambda w: w["top"])
        for w in ws:   # שורת הסיכום ירדה: מזיזים מתחת לשורה השנייה
            if w["top"] > 140: w["top"] += 14
        r = a.parse_words(ws)
        d = r["days"][0]
        self.assertEqual((d["first_in"], d["last_out"], d["presence_min"]), ("16:33", "19:31", 178))
        self.assertTrue(d["span_matches_presence"])

    def test_overtime_column_by_header_position(self):
        r = a.parse_words(base_words([("01/11", "08:00", "11:00", "3:00", "2:00", "1:00")], "2:00", "3:00"))
        self.assertEqual(r["totals"]["overtime_min"]["125"], 60)

    def test_unclassified_time_not_silently_dropped(self):
        ws = base_words([("01/11", "08:00", "10:00", "2:00", "2:00", None)], "2:00", "2:00")
        ws.append(W("1:15", 120, 116))     # שעה בעמודה שאינה מוכרת
        r = a.parse_words(ws)
        self.assertTrue(any("1:15" in w for w in r["warnings"]))
        self.assertEqual(r["totals"]["regular_min"], 120)

    def test_open_day_warns(self):
        r = a.parse_words(base_words([("01/11", "08:00", None, None, None, None)], "0:00", "0:00"))
        self.assertTrue(any("יום פתוח" in w for w in r["warnings"]))

    def test_not_a_card_report(self):
        with self.assertRaises(ValueError):
            a.parse_words([W("שלום", 100, 100)])

    def test_hours_decimal_no_rounding_of_minutes(self):
        self.assertEqual(str(a.hours_decimal(208)), "3.4667")


if __name__ == "__main__":
    unittest.main()
