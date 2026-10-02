import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


def load_module():
    root = Path(__file__).resolve().parents[1]
    if "fitz" not in sys.modules:
        fitz_stub = types.ModuleType("fitz")
        fitz_stub.open = lambda *args, **kwargs: None
        sys.modules["fitz"] = fitz_stub
    if "llm" not in sys.modules:
        llm_stub = types.ModuleType("llm")

        class DummyDeepSeekClient:
            def __init__(self, *args, **kwargs):
                pass

        llm_stub.DeepSeekClient = DummyDeepSeekClient
        llm_stub.resolve_max_output_tokens = lambda default=393216: default
        sys.modules["llm"] = llm_stub
    spec = importlib.util.spec_from_file_location("gen6_aff_mod", root / "src" / "6.generate_docs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GLANCE = {
    "tldr": "这是一段足够长的中文速览摘要。",
    "motivation": "动机。",
    "method": "方法。",
    "result": "结果。",
    "conclusion": "结论。",
}


class AffiliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def run_glance(self, response, front_text):
        captured = {}

        def fake(client, messages, **kwargs):
            captured["messages"] = messages
            captured["schema"] = kwargs["schema"]
            return response

        original = self.mod.call_llm_structured_json
        self.mod.call_llm_structured_json = fake
        try:
            out = self.mod.generate_glance_overview("T", "A", client=object(), front_text=front_text)
        finally:
            self.mod.call_llm_structured_json = original
        return out, captured

    def test_format_first_and_corresponding(self):
        f = self.mod.format_affiliations
        self.assertEqual(
            f({"first_author": "Jingruo Chen", "first_author_affiliation": "Cornell University",
               "corresponding_author": "Susan Fussell", "corresponding_affiliation": "Cornell University"}),
            "一作 Jingruo Chen（Cornell University）；通讯 Susan Fussell（Cornell University）",
        )
        self.assertEqual(
            f({"first_author": "A", "first_author_affiliation": "MIT",
               "corresponding_author": "a", "corresponding_affiliation": ""}),
            "一作兼通讯 A（MIT）",
        )
        # 没有标注通讯作者：只显示一作；只抽到通讯机构、没有姓名时不显示
        self.assertEqual(
            f({"first_author": "A", "first_author_affiliation": "MIT",
               "corresponding_author": "", "corresponding_affiliation": "Stanford"}),
            "一作 A（MIT）",
        )
        self.assertEqual(f({"first_author": "", "first_author_affiliation": "",
                            "corresponding_author": "", "corresponding_affiliation": ""}), "")

    def test_glance_extracts_affiliations_in_same_call(self):
        response = dict(GLANCE, first_author="A", first_author_affiliation="MIT",
                        corresponding_author="B", corresponding_affiliation="Stanford")
        out, captured = self.run_glance(response, "Title\nA (MIT), B* (Stanford)\n*Corresponding author")
        self.assertIn("**Affiliations**：一作 A（MIT）；通讯 B（Stanford）", out)
        payload = json.loads(captured["messages"][1]["content"])
        self.assertIn("pdf_first_page", payload)
        self.assertIn("corresponding_author", captured["schema"]["required"])
        self.assertIn("不要默认是最后一位作者", captured["messages"][2]["content"])

    def test_glance_without_front_text_is_unchanged(self):
        out, captured = self.run_glance(dict(GLANCE), "")
        self.assertNotIn("Affiliations", out)
        self.assertNotIn("pdf_first_page", json.loads(captured["messages"][1]["content"]))
        self.assertNotIn("first_author", captured["schema"]["properties"])

    def test_front_text_is_truncated(self):
        _, captured = self.run_glance(dict(GLANCE), "x" * 10000)
        payload = json.loads(captured["messages"][1]["content"])
        self.assertEqual(len(payload["pdf_first_page"]), self.mod.AFFILIATION_FRONT_CHARS)

    def test_markdown_front_matter_gets_affiliations(self):
        paper = {
            "title": "T", "authors": ["A", "B"], "abstract": "abs",
            "_glance_overview": "**TLDR**：t。 \\\n**Motivation**：m。\n**Affiliations**：一作 A（MIT）；通讯 B（Stanford）",
        }
        md = self.mod.build_markdown_content(paper, "quick", "", "", [])
        fm = md.split("---")[1]
        self.assertIn("affiliations: 一作 A（MIT）；通讯 B（Stanford）", fm)
        self.assertLess(fm.index("authors:"), fm.index("affiliations:"))
        self.assertNotIn("Affiliations", md.split("---", 2)[2])

    def test_read_front_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "p.txt"
            p.write_text("y" * 9000, encoding="utf-8")
            self.assertEqual(len(self.mod.read_front_text(str(p))), self.mod.AFFILIATION_FRONT_CHARS)
            self.assertEqual(self.mod.read_front_text(str(Path(d) / "missing.txt")), "")


if __name__ == "__main__":
    unittest.main()


class TranslateModelTest(unittest.TestCase):
    def test_translation_uses_dedicated_model_when_configured(self):
        import os
        from unittest.mock import patch
        mod = load_module()
        used = []

        def fake_structured(client, messages, **kwargs):
            used.append(client)
            return {"title_zh": "标题", "abstract_zh": "摘要"}

        class FakeClient:
            def __init__(self, api_key, model, base_url):
                self.model = model

        summary_client = object()
        with patch.object(mod, "call_llm_structured_json", fake_structured), \
                patch.object(mod, "DeepSeekClient", FakeClient), \
                patch.object(mod, "TRANSLATE_MODEL", "gpt-6-luna(medium)"), \
                patch.object(mod, "DEEPSEEK_API_KEY", "k"):
            mod.translate_title_and_abstract_to_zh("T", "A", client=summary_client)
        self.assertIsNot(used[-1], summary_client)
        self.assertEqual(used[-1].model, "gpt-6-luna(medium)")

        with patch.object(mod, "call_llm_structured_json", fake_structured), \
                patch.object(mod, "TRANSLATE_MODEL", ""):
            mod.translate_title_and_abstract_to_zh("T", "A", client=summary_client)
        self.assertIs(used[-1], summary_client)
