import unittest

import sources_catalog as sc


class Catalog(unittest.TestCase):
    def test_statuses_valid(self):
        for r in sc.catalog():
            self.assertIn(r["status"], {"law", "acc", "manual"}, r["rule"])

    def test_every_law_row_has_a_named_source(self):
        for r in sc.catalog():
            if r["status"] == "law":
                self.assertTrue(r["law"], r["rule"])

    def test_cumulative_is_not_law(self):
        row = [r for r in sc.catalog() if "מצטבר" in r["rule"]][0]
        self.assertEqual(row["status"], "acc")

    def test_unresolved_rules_are_manual(self):
        for name in ("המרת ימי חופשה", "מחלק שעות"):
            row = [r for r in sc.catalog() if name in r["rule"]][0]
            self.assertEqual(row["status"], "manual")


if __name__ == "__main__":
    unittest.main()
