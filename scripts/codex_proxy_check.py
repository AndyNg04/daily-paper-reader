#!/usr/bin/env python3
"""检查 Codex proxy 能否替代 DeepSeek（fork 专用，由 codex-proxy-check workflow 调用）。

逐项用项目自己的 LLMClient 按真实调用方式发请求：普通对话、JSON mode、json_schema、
assistant 续写、max_tokens 截断、DeepSeek 专用 thinking 参数、长输入耗时。
只打印结果摘要，不打印任何凭证。
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from llm import LLMClient  # noqa: E402

BASE = os.environ["DEEPSEEK_BASE_URL"]
KEY = os.environ["DEEPSEEK_API_KEY"]
results: list[tuple[str, str, bool, str]] = []


def record(model: str, name: str, fn) -> None:
    start = time.time()
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {str(exc)[:300]}"
        traceback.print_exc(limit=1)
    detail = f"{detail}（{time.time() - start:.1f}s）"
    results.append((model, name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {model} | {name} | {detail}", flush=True)


def client(model: str, **kwargs) -> LLMClient:
    c = LLMClient(api_key=KEY, model=model, base_url=BASE)
    c.kwargs.update(kwargs)
    return c


def check_model(model: str) -> None:
    def plain():
        r = client(model, temperature=0.3, max_tokens=256).chat(
            [{"role": "user", "content": "只回答一个阿拉伯数字：1+1 等于几？"}])
        return "2" in r["content"], f"content={r['content'][:40]!r} finish={r['finish_reason']} tokens={r['tokens']}"

    def json_object():
        r = client(model, temperature=0.1).chat(
            [{"role": "system", "content": "只输出 JSON。"},
             {"role": "user", "content": '输出 JSON：{"score": 整数1到5, "reason": 字符串}，评价 "attention is all you need" 这篇论文。'}],
            response_format={"type": "json_object"})
        data = LLMClient.parse_json_content(r["content"])
        return isinstance(data, dict) and "score" in data, f"keys={sorted(data) if isinstance(data, dict) else type(data).__name__}"

    schema = {"type": "object", "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
              "required": ["tags"], "additionalProperties": False}
    # 与真实调用方（如 Step 4）一致：默认格式（json_object → prompt_only）不会把 schema 发给模型，
    # 所以字段名要写在提示词里。
    schema_prompt = [{"role": "user", "content":
                      '给论文《Attention Is All You Need》打 3 个英文关键词标签，输出 JSON：{"tags": [字符串, ...]}。'}]

    def structured_result(r):
        data = r.get("parsed") if isinstance(r, dict) else None
        ok = isinstance(data, dict) and isinstance(data.get("tags"), list) and r.get("parse_error") is None
        return ok, f"format={r.get('response_format_used')} parsed={json.dumps(data, ensure_ascii=False)[:80]} error={r.get('parse_error')}"

    def json_schema():
        return structured_result(client(model, temperature=0.1).chat_structured(
            schema_prompt, schema_name="tags", schema=schema))

    def json_schema_native():
        # 仅供参考：强制先发 json_schema（DPR_LLM_STRUCTURED_FORMAT=json_schema），看 proxy 是否原生支持。
        old = os.environ.get("DPR_LLM_STRUCTURED_FORMAT")
        os.environ["DPR_LLM_STRUCTURED_FORMAT"] = "json_schema"
        try:
            return structured_result(client(model, temperature=0.1).chat_structured(
                schema_prompt, schema_name="tags", schema=schema))
        finally:
            if old is None:
                os.environ.pop("DPR_LLM_STRUCTURED_FORMAT", None)
            else:
                os.environ["DPR_LLM_STRUCTURED_FORMAT"] = old

    def continuation():
        # 精读总结的续写方式（6.generate_docs.generate_deep_summary）：最后一轮是 assistant 已输出的内容。
        msgs = [
            {"role": "user", "content": "按顺序列出 1 到 10 的中文数字，每行一个，最后单独一行写（完）。"},
            {"role": "assistant", "content": "一\n二\n三\n四"},
            {"role": "user", "content": "请紧接着最后一个字继续写完，不要重复已经写过的内容，写完后单独一行写（完）。"},
        ]
        r = client(model, temperature=0.3, max_tokens=512).chat(msgs)
        text = r["content"]
        ok = "（完）" in text and "五" in text and not text.lstrip().startswith("一")
        return ok, f"content={text[:60]!r}"

    def truncation():
        r = client(model, temperature=0.3, max_tokens=64).chat(
            [{"role": "user", "content": "写一篇 800 字的中文短文，主题是深度学习的历史。"}])
        return True, f"finish={r['finish_reason']} len={len(r['content'])}（只观察 max_tokens 是否生效）"

    def thinking_param():
        # starter_pack_reading.py 会给 DeepSeek 传 thinking={"type": "disabled"}。
        r = client(model, max_tokens=64, thinking={"type": "disabled"}).chat(
            [{"role": "user", "content": "只回答 OK"}])
        return bool(r["content"].strip()), f"content={r['content'][:20]!r}"

    def long_input(repeat: int):
        def run():
            filler = ("Transformers use self-attention to model token interactions. " * repeat)
            r = client(model, temperature=0.3, max_tokens=4096).chat(
                [{"role": "system", "content": "你是论文阅读助手。"},
                 {"role": "user", "content": f"下面是一段很长的论文正文：\n{filler}\n\n用 5 条中文要点总结，最后单独一行写（完）。"}])
            return "（完）" in r["content"], f"prompt_tokens={r['tokens']['prompt']} len={len(r['content'])} finish={r['finish_reason']}"
        return run

    for name, fn in [("普通对话", plain), ("JSON mode", json_object), ("json_schema", json_schema),
                     ("json_schema 原生（参考）", json_schema_native),
                     ("assistant 续写", continuation), ("max_tokens 截断", truncation),
                     ("thinking 参数", thinking_param), ("长输入 ~9k", long_input(900)),
                     ("长输入 ~40k（整篇论文量级）", long_input(4000))]:
        record(model, name, fn)


def main() -> int:
    resp = requests.get(f"{BASE}/models", headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
    resp.raise_for_status()
    ids = sorted(m.get("id", "") for m in resp.json().get("data", []))
    print("可用模型：", json.dumps(ids, ensure_ascii=False), flush=True)
    models = []
    extra = [m.strip() for m in os.getenv("CODEX_CHECK_EXTRA_MODELS", "").split(",")]
    for m in (os.getenv("SUMMARY_MODEL", ""), os.getenv("DEEPSEEK_FILTER_MODEL", ""), *extra):
        if m and m not in models:
            models.append(m)
    for m in models:
        check_model(m)
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Codex proxy 兼容性检查\n\n")
            fh.write(f"可用模型：`{', '.join(ids)}`\n\n| 模型 | 检查项 | 结果 | 说明 |\n|---|---|---|---|\n")
            for model, name, ok, detail in results:
                fh.write(f"| {model} | {name} | {'✅' if ok else '❌'} | {detail.replace('|', '/')} |\n")
    required = [ok for _, name, ok, _ in results if "（参考）" not in name]
    return 0 if all(required) else 1


if __name__ == "__main__":
    sys.exit(main())
