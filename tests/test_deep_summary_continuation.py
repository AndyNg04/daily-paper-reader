"""精读长总结被 max_tokens 截断时的多轮续写（fork 修复）。"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
spec = importlib.util.spec_from_file_location(
    "deep_summary_generator", Path(__file__).resolve().parents[1] / "src/6.generate_docs.py"
)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def _paper_files(tmp_path):
    md = tmp_path / "p.md"
    md.write_text("---\ntitle: T\n---\n\n## Abstract\nA\n", encoding="utf-8")
    txt = tmp_path / "p.txt"
    txt.write_text("PAPER FULL TEXT", encoding="utf-8")
    return str(md), str(txt)


def test_truncated_summary_is_continued_with_paper_context(tmp_path, monkeypatch):
    md, txt = _paper_files(tmp_path)
    replies = iter(["## 1. 问题\n- 第一段被截", "断的句子\n## 2. 方法", "- 方法细节\n（完）"])
    calls = []

    def fake_call(client, messages, temperature, max_tokens, response_format=None):
        calls.append(messages)
        return next(replies)

    monkeypatch.setattr(gen, "call_llm_text", fake_call)
    out = gen.generate_deep_summary(md, txt, client=Mock(kwargs={}))
    assert out == "## 1. 问题\n- 第一段被截断的句子\n## 2. 方法\n- 方法细节\n（完）"
    assert len(calls) == 3
    # 续写请求带着原文和已输出内容（assistant 轮），而不是只有上一次输出。
    for cont in calls[1:]:
        assert any("PAPER FULL TEXT" in m["content"] for m in cont)
        assert cont[-2]["role"] == "assistant"
    assert calls[2][-2]["content"] == "## 1. 问题\n- 第一段被截断的句子\n## 2. 方法"


def test_returns_longest_merged_text_when_never_complete(tmp_path, monkeypatch):
    md, txt = _paper_files(tmp_path)
    monkeypatch.setattr(gen, "call_llm_text", lambda *a, **k: "片段")
    monkeypatch.setattr(gen.time, "sleep", lambda s: None)
    out = gen.generate_deep_summary(md, txt, client=Mock(kwargs={}), max_retries=2)
    # 原实现只返回第一段；现在返回续写拼接后的完整文本（1 + 续写轮数）。
    assert out == "片段" * (1 + gen.DEEP_SUMMARY_MAX_CONTINUATIONS)


def test_empty_continuation_stops_rounds(tmp_path, monkeypatch):
    md, txt = _paper_files(tmp_path)
    replies = iter(["前半", "", "重来一次（完）"])
    monkeypatch.setattr(gen, "call_llm_text", lambda *a, **k: next(replies))
    assert gen.generate_deep_summary(md, txt, client=Mock(kwargs={})) == "重来一次（完）"


def test_join_continuation():
    assert gen.join_continuation("截", "断") == "截断"
    assert gen.join_continuation("段落", "## 3. 实验") == "段落\n## 3. 实验"
    assert gen.join_continuation("段落", "- 列表") == "段落\n- 列表"
    assert gen.join_continuation("段落", "2. 编号") == "段落\n2. 编号"
    assert gen.join_continuation("段落", "（完）") == "段落\n（完）"


def test_incomplete_existing_summary_is_regenerated():
    head = "---\ntitle: T\n---\n\n## Abstract\nA\n\n---\n\n## 论文详细总结（自动生成）\n\n"
    assert gen.deep_summary_complete(head + "内容\n（完）\n")
    assert not gen.deep_summary_complete(head + "- 主实验：2 个 Counsel")
    assert not gen.deep_summary_complete("---\ntitle: T\n---\n\n## Abstract\nA\n")
