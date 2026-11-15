import unittest
from types import SimpleNamespace as NS
import proposals
import ai_extractor as ax

PDF = b"%PDF-1.4 fake"


class FakeClient:
    def __init__(self, tool_input=None, blocks=None):
        self.calls = []
        self._blocks = blocks if blocks is not None else [NS(type="tool_use", name="report_form101", input=tool_input)]
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return NS(content=self._blocks)


ENV_OK = {"ALLOW_EXTERNAL_AI": "true", "ANTHROPIC_API_KEY": "k"}


class Extractor(unittest.TestCase):
    def test_blocked_without_permission(self):
        with self.assertRaises(proposals.ExtractorNotConfigured):
            ax.AnthropicForm101Extractor(client=FakeClient({}), env={})

    def test_blocked_without_key(self):
        with self.assertRaises(proposals.ExtractorNotConfigured):
            ax.AnthropicForm101Extractor(env={"ALLOW_EXTERNAL_AI": "true"})

    def test_get_extractor_default_still_manual(self):
        self.assertEqual(proposals.get_extractor(env={}).name, "manual")

    def test_get_extractor_anthropic_blocked_by_default(self):
        with self.assertRaises(proposals.ExtractorNotConfigured):
            proposals.get_extractor("anthropic", env={})

    def test_whitelist_filters_injected_fields(self):
        c = FakeClient({"id_number": "123456782", "tax_year": 2026, "income_type": "main",
                        "other_income": False, "other_credits_claimed": False, "signed_on": None,
                        "unclear": [], "manual_points": 99, "ignore_rules": "yes"})
        e = ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract("form101", PDF, "a.pdf")
        self.assertNotIn("manual_points", e.fields)
        self.assertNotIn("ignore_rules", e.fields)
        self.assertNotIn("signed_on", e.fields)            # null לא נכנס
        self.assertEqual(e.fields["tax_year"], 2026)

    def test_goes_through_schema_and_validation(self):
        c = FakeClient({"id_number": "123456789", "tax_year": 2026, "income_type": "bogus",
                        "other_income": False, "other_credits_claimed": False, "unclear": []})
        e = ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract("form101", PDF, "a.pdf")
        prop, val = proposals.build_proposal("form101", e.fields, e.source, e.notes)
        self.assertIn("income_type", val.errors)           # ערך לא תקין חוסם אישור

    def test_forced_tool_and_only_document_sent(self):
        c = FakeClient({"unclear": []})
        ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract("form101", PDF, "a.pdf")
        kw = c.calls[0]
        self.assertEqual(kw["tool_choice"], {"type": "tool", "name": "report_form101"})
        self.assertEqual(len(kw["tools"]), 1)
        self.assertEqual(kw["messages"][0]["content"][0]["type"], "document")

    def test_no_tool_result_means_manual(self):
        c = FakeClient(blocks=[NS(type="text", text="hi")])
        e = ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract("form101", PDF, "a.pdf")
        self.assertEqual(e.fields, {})

    def test_bad_file_rejected_before_sending(self):
        c = FakeClient({})
        with self.assertRaises(ValueError):
            ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract("form101", b"MZ-exe", "a.exe")
        self.assertEqual(c.calls, [])

    def test_unclear_reported(self):
        c = FakeClient({"unclear": ["signed_on"]})
        e = ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract("form101", PDF, "a.pdf")
        self.assertTrue(any("signed_on" in n for n in e.notes))

    def test_other_kinds_not_supported(self):
        with self.assertRaises(proposals.ExtractorNotConfigured):
            ax.AnthropicForm101Extractor(client=FakeClient({}), env=ENV_OK).extract("form106", PDF, "a.pdf")


class FamilyDerivation(unittest.TestCase):
    def _run(self, extra):
        base = {"id_number": "123456782", "tax_year": 2026, "income_type": "main"}
        base.update(extra)
        ex = ax.AnthropicForm101Extractor(client=FakeClient(base), env=ENV_OK)
        return ex.extract(proposals.KIND_FORM101, PDF, "f.pdf")

    def test_children_split_by_custody(self):
        r = self._run({"marital": "married", "other_credits_claimed": False, "checked_items": [],
                       "children": [{"birth_year": 2016, "in_custody": True},
                                    {"birth_year": 2010, "in_custody": False}]})
        self.assertEqual(r.fields["custody_birth_years"], [2016])
        self.assertEqual(r.fields["noncustody_birth_years"], [2010])
        self.assertFalse(r.fields["other_credits_claimed"])

    def test_items_map_to_flags_and_others_force_manual(self):
        r = self._run({"checked_items": ["9", "13"], "children": []})
        self.assertEqual(r.fields["family_flags"], ["niptar", "teen"])
        r5 = self._run({"checked_items": ["5", "6"]})
        self.assertEqual(r5.fields["family_flags"], ["benef", "nomesh"])
        self.assertFalse(r5.fields["other_credits_claimed"])
        r12 = self._run({"checked_items": ["12"]})
        self.assertTrue(r12.fields["alimony_ex_spouse"])
        self.assertFalse(r12.fields["other_credits_claimed"])
        self.assertFalse(r.fields["other_credits_claimed"])
        r = self._run({"checked_items": ["14"]})
        self.assertTrue(r.fields["other_credits_claimed"])

    def test_unclear_child_forces_manual(self):
        r = self._run({"children": [{"birth_year": None, "in_custody": True}]})
        self.assertTrue(r.fields["other_credits_claimed"])
        self.assertTrue(any("ילד" in n for n in r.notes))

    def test_unknown_item_ignored_and_injected_flags_filtered(self):
        r = self._run({"checked_items": ["99", "13"], "family_flags": ["hacker"]})
        self.assertEqual(r.fields["family_flags"], ["teen"])


if __name__ == "__main__":
    unittest.main()


class AliyahItem(unittest.TestCase):
    def test_item4_with_date_supported_without_date_manual(self):
        def run(extra):
            c = FakeClient(dict({"id_number": "123456782", "tax_year": 2026}, **extra))
            return ax.AnthropicForm101Extractor(client=c, env=ENV_OK).extract(proposals.KIND_FORM101, PDF, "f.pdf")
        r = run({"checked_items": ["4"], "aliyah_date": "2026-03-10"})
        self.assertEqual(r.fields["aliyah_date"], "2026-03-10")
        self.assertFalse(r.fields["other_credits_claimed"])
        self.assertTrue(run({"checked_items": ["4"]}).fields["other_credits_claimed"])
        self.assertTrue(run({"checked_items": ["4", "15"], "aliyah_date": "2026-03-10"}).fields["other_credits_claimed"])
