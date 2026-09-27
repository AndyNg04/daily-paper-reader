"""src/deep_read_paper.py：单篇论文「速读区 → 精读区」升级链路（fork 专用）。"""

import difflib
import html
import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest

from src import deep_read_paper as drp
from src.daily_report_state import bootstrap_daily_state_from_sidebar, save_daily_state

ROOT = Path(__file__).resolve().parents[1]
RANGE = "20260828-20260926"
DEEP_HEADING = "## 论文详细总结（自动生成）"


# ---------------------------------------------------------------------------
# 合成夹具：与真实 docs/_sidebar.md、论文 Markdown、_daily_state.json 同格式
# ---------------------------------------------------------------------------


def entry(route, title, score="7.0", tag="ai-hci-mh"):
    arxiv_id = route.split("/")[-1].split("-")[0]
    payload = {
        "title": title,
        "link": f"https://arxiv.org/abs/{arxiv_id}",
        "score": score,
        "tags": [{"kind": "query", "label": tag}],
        "evidence": "心理健康问答中的选择性检索",
    }
    data = html.escape(json.dumps(payload, ensure_ascii=False), quote=True)
    return (
        '      * <a class="dpr-sidebar-item-link dpr-sidebar-item-structured" '
        f'href="#/{route}" data-sidebar-item="{data}">{html.escape(title)}</a>\n'
    )


T_RANGE = entry(f"{RANGE}/2609.03454v1-when-retrieval-helps", "When Retrieval Helps")
C_V12 = entry(f"{RANGE}/2609.03454v12-other-version-prefix", "Other v12 Paper")
A = entry(f"{RANGE}/2608.28165v1-crabos", "CrabOS", score="9.0")
B = entry(f"{RANGE}/2608.30110v1-can-llms", "Can LLMs", score="9.0")
# \u2028 出现在 ensure_ascii=False 的 JSON 里时，不能被当成换行切开
D = entry(f"{RANGE}/2609.02797v1-dutch-books", "Dutch Books\u2028for LMs", score="6.0")
E_DAY = entry("202609/26/2609.00506v1-recalibrategpt", "RecalibrateGPT", score="9.0")
T_DAY = entry("202609/26/2609.03454v1-when-retrieval-helps", "When Retrieval Helps")
F_DAY = entry("202609/26/2609.05552v1-agent-model", "Agent Model", score="6.5")
G = entry("202608/23/2608.11111v1-quick-only-g", "Quick Only G")
H = entry("202608/23/2608.22222v1-quick-only-h", "Quick Only H")
I_ = entry("202608/16/2608.33333v1-deep-i", "Deep I", score="8.5")
J = entry("202608/16/2608.44444v1-lonely-quick-j", "Lonely Quick J")

HEAD = (
    '* <a class="dpr-sidebar-root-link" href="#/">首页</a>\n'
    "* Daily Papers\n"
)
CONFERENCE = (
    "* Conference Papers\n"
    "  * ICML 2025 <!--dpr-conference:icml-2025-->\n"
    "    * 精读区\n"
    '      * <a class="dpr-sidebar-item-link" href="#/conference/icml/2025/x">X</a>\n'
)


def day_block_20260926(quick=(T_DAY, F_DAY)):
    return "  * 2026-09-26 <!--dpr-date:20260926-->\n    * 精读区\n" + E_DAY + "    * 速读区\n" + "".join(quick)


def range_block(deep=(A, B), quick=(C_V12, T_RANGE, D)):
    out = f"  * 2026-08-28 ~ 2026-09-26 <!--dpr-date:{RANGE}-->\n"
    if deep:
        out += "    * 精读区\n" + "".join(deep)
    if quick:
        out += "    * 速读区\n" + "".join(quick)
    return out


def quick_only_block(deep=(), quick=(G, H)):
    out = "  * 2026-08-23 <!--dpr-date:20260823-->\n"
    if deep:
        out += "    * 精读区\n" + "".join(deep)
    if quick:
        out += "    * 速读区\n" + "".join(quick)
    return out


def lonely_block(deep=(I_,), quick=(J,)):
    # 历史格式：没有 <!--dpr-date--> marker 的日期标题
    out = "  * 2026-08-16\n    * 精读区\n" + "".join(deep)
    if quick:
        out += "    * 速读区\n" + "".join(quick)
    return out


def sidebar(**blocks):
    return (
        HEAD
        + blocks.get("day", day_block_20260926())
        + blocks.get("range", range_block())
        + blocks.get("quick_only", quick_only_block())
        + blocks.get("lonely", lonely_block())
        + CONFERENCE
    )


SIDEBAR = sidebar()


def paper_markdown(title="When Retrieval Helps", source="arxiv", deep_summary=None, media=("figures", "tables")):
    text = textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        title_zh: 检索何时有益
        authors: "Hyunseo Oh, Chong-Kwon Kim"
        date: 2026-09-03
        pdf: "https://arxiv.org/pdf/2609.03454v1"
        tags: ["query:ai-hci-mh"]
        score: 7.0
        tldr: 选择性检索
        source: {source}
        figures_json: "[{{\\"url\\": \\"assets/figures/arxiv/2609.03454v1/fig-001.webp\\"}}]"
        tables_json: "[{{\\"url\\": \\"assets/tables/arxiv/2609.03454v1/table-001.webp\\"}}]"
        motivation: m
        method: me
        result: r
        conclusion: c
        ---

        ## 摘要
        中文摘要。

        ## Abstract
        English abstract."""
    )
    for kind in ("figures", "tables"):
        if kind not in media:
            text = "\n".join(line for line in text.split("\n") if not line.startswith(f"{kind}_json:"))
    if deep_summary is not None:
        text = text.rstrip() + f"\n\n---\n\n{DEEP_HEADING}\n\n{deep_summary}".rstrip() + "\n"
    return text


def state_payload(sections):
    papers = []
    for pid, route, section, score in sections:
        papers.append(
            {
                "paper_id": pid,
                "route": route,
                "title": route.split("/")[-1],
                "section": section,
                "tags": [{"kind": "query", "label": "ai-hci-mh"}],
                "score": score,
                "evidence": "证据",
                "first_seen_at": "2026-09-26 13:55:16 UTC",
                "updated_at": "2026-09-26 13:55:16 UTC",
            }
        )
    return {
        "date": RANGE,
        "date_label": "2026-08-28 ~ 2026-09-26",
        "generated_at": "2026-09-26 13:55:16 UTC",
        "recommend_exists": True,
        "run_count": 1,
        "papers": papers,
    }


RANGE_STATE = state_payload(
    [
        ("2608.28165v1", f"{RANGE}/2608.28165v1-crabos", "deep", 9.0),
        ("2609.03454v1", f"{RANGE}/2609.03454v1-when-retrieval-helps", "quick", 7.0),
        ("2609.02797v1", f"{RANGE}/2609.02797v1-dutch-books", "quick", 6.0),
    ]
)


def report_line(n, title, route, score="7.0/10"):
    suffix = f"（{score}）" if score else ""
    return f"{n}. [{title}](/{route}) {suffix}\n"


def day_readme(deep_lines, quick_lines, deep_count=None, quick_count=None):
    """与 6.generate_docs.build_day_report_markdown 同格式（由 test_promote_day_report_matches_upstream_builder 锁定）。"""
    deep_count = len(deep_lines) if deep_count is None else deep_count
    quick_count = len(quick_lines) if quick_count is None else quick_count
    return (
        "# 日报 · 2026-08-28 ~ 2026-09-26\n\n"
        "- 最近生成时间：2026-09-26 13:55:16 UTC\n"
        "- 今日累计更新：1 次\n"
        f"- 今日累计推荐总数：{deep_count + quick_count}\n"
        f"- 精读区：{deep_count}\n"
        f"- 速读区：{quick_count}\n\n"
        "## 今日简报（AI）\n精读1篇、速读2篇。\n\n"
        "## 精读区\n" + ("".join(deep_lines) or "- 本次无精读推荐。\n") + "\n"
        "## 速读区\n" + ("".join(quick_lines) or "- 本次无速读推荐。\n") + "\n"
        "---\n使用键盘方向键可在日报/论文之间快速切换。\n"
    )


R_A = (f"{RANGE}/2608.28165v1-crabos", "CrabOS")
R_T = (f"{RANGE}/2609.03454v1-when-retrieval-helps", "When Retrieval Helps")
R_D = (f"{RANGE}/2609.02797v1-dutch-books", "Dutch Books")
DAY_README = day_readme(
    [report_line(1, R_A[1], R_A[0], "9.0/10")],
    [report_line(1, R_T[1], R_T[0]), report_line(2, R_D[1], R_D[0], "6.0/10")],
)
DAY_README_PROMOTED = day_readme(
    [report_line(1, R_A[1], R_A[0], "9.0/10"), report_line(2, R_T[1], R_T[0])],
    [report_line(1, R_D[1], R_D[0], "6.0/10")],
)


def papers_meta_text(promoted=False):
    papers = [
        {"paper_id": R_A[0], "section": "deep", "title_en": R_A[1], "tldr": "中文"},
        {"paper_id": R_T[0], "section": "deep" if promoted else "quick", "title_en": R_T[1], "tldr": "中文"},
        {"paper_id": R_D[0], "section": "quick", "title_en": R_D[1], "tldr": "中文"},
    ]
    payload = {"label": "2026-08-28 ~ 2026-09-26", "count": 3, "papers": papers, "errors": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def make_docs(tmp_path, md_text=None, with_state=True):
    docs = tmp_path / "docs"
    day = docs / RANGE
    day.mkdir(parents=True)
    (docs / "_sidebar.md").write_text(SIDEBAR, encoding="utf-8", newline="")
    (day / "2609.03454v1-when-retrieval-helps.md").write_text(md_text or paper_markdown(), encoding="utf-8")
    (day / "2609.03454v1-when-retrieval-helps.txt").write_text("full text " * 200, encoding="utf-8")
    (day / "2609.03454v12-other-version-prefix.md").write_text(paper_markdown("Other v12 Paper"), encoding="utf-8")
    (day / "2609.02797v1-dutch-books.md").write_text(paper_markdown("Dutch Books"), encoding="utf-8")
    (day / "README.md").write_text(DAY_README, encoding="utf-8")
    (day / "papers.meta.json").write_text(papers_meta_text(), encoding="utf-8")
    if with_state:
        save_daily_state(str(day / "_daily_state.json"), RANGE_STATE)
    fig = docs / "assets" / "figures" / "arxiv" / "2609.03454v1"
    fig.mkdir(parents=True)
    (fig / "meta.json").write_text('{"figures": []}\n', encoding="utf-8")
    return docs


@pytest.fixture(scope="module")
def gen():
    """真实加载 src/6.generate_docs.py，用于锁定与上游实现的一致性。"""
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    spec = importlib.util.spec_from_file_location("gen6_deep_read_contract", ROOT / "src" / "6.generate_docs.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2609.03454v1", "2609.03454v1"),
        ("2609.03454", "2609.03454"),
        ("  2609.03454v12 ", "2609.03454v12"),
        ("1501.0001v3", "1501.0001v3"),
    ],
)
def test_validate_paper_id_accepts_modern_arxiv_ids(value, expected):
    assert drp.validate_paper_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "2609.03454v",
        "2609.03454v0",
        "2609.034541",
        "2609.03454V1",
        "cs/0112017",
        "https://arxiv.org/abs/2609.03454v1",
        "../2609.03454v1",
        "2609.03454v1-slug",
        "2609.03454v1\n::error::pwned",
        "2609.03454v1;rm -rf /",
        "$(id)",
    ],
)
def test_validate_paper_id_rejects_everything_else(value):
    with pytest.raises(drp.DeepReadError):
        drp.validate_paper_id(value)


@pytest.mark.parametrize("value", ["20260926", RANGE, " 20260926 ", "20240229"])
def test_validate_date_token_accepts_day_and_range(value):
    assert drp.validate_date_token(value) == value.strip()


@pytest.mark.parametrize(
    "value",
    ["", "2026-09-26", "20260931", "20230229", "20260926-20260828", "20260828-", "20260828_20260926", "202609/26", "2026092"],
)
def test_validate_date_token_rejects_invalid(value):
    with pytest.raises(drp.DeepReadError):
        drp.validate_date_token(value)


def test_route_dir_matches_generator_layout(gen):
    assert drp.route_dir_for(RANGE) == RANGE
    assert drp.route_dir_for("20260926") == "202609/26"
    for token in (RANGE, "20260926"):
        md_path, _, route = gen.prepare_paper_paths("/d", token, "Some Title", "2609.03454v1")
        assert route == f"{drp.route_dir_for(token)}/2609.03454v1-some-title"
        assert md_path == f"/d/{drp.route_dir_for(token)}/2609.03454v1-some-title.md"


def test_slugify_and_asset_key_match_upstream(gen):
    from src.paper_figures import _safe_asset_key

    titles = [
        "When Retrieval Helps: Selective Retrieval for Single-Turn Mental-Health QA",
        "InsightToast: Proactive Information Retrieval & Glanceable Visualization",
        "  Ünïcödé   Title\twith\nwhitespace ",
        "",
        "???",
    ]
    for title in titles:
        assert drp.slugify(title) == gen.slugify(title)
    for key in ["2609.03454v1", "a/b c", "", "..x.."]:
        assert drp.safe_asset_key(key) == _safe_asset_key(key)


# ---------------------------------------------------------------------------
# 定位论文 Markdown
# ---------------------------------------------------------------------------


def test_find_paper_markdown_is_version_safe(tmp_path):
    docs = make_docs(tmp_path)
    day = docs / RANGE
    (day / "2609.0345v1-four-digit.md").write_text(paper_markdown("Four Digit"), encoding="utf-8")

    assert drp.find_paper_markdown(docs, RANGE, "2609.03454v1").name == "2609.03454v1-when-retrieval-helps.md"
    assert drp.find_paper_markdown(docs, RANGE, "2609.03454v12").name == "2609.03454v12-other-version-prefix.md"
    assert drp.find_paper_markdown(docs, RANGE, "2609.0345v1").name == "2609.0345v1-four-digit.md"
    assert drp.find_paper_markdown(docs, RANGE, "2609.0345").name == "2609.0345v1-four-digit.md"
    with pytest.raises(drp.DeepReadError, match="多个"):
        drp.find_paper_markdown(docs, RANGE, "2609.03454")  # v1 与 v12 同时存在
    with pytest.raises(drp.DeepReadError, match="找不到"):
        drp.find_paper_markdown(docs, RANGE, "2609.03454v2")


def test_find_paper_markdown_bare_id_resolves_single_version(tmp_path):
    docs = make_docs(tmp_path)
    (docs / RANGE / "2609.03454v12-other-version-prefix.md").unlink()
    assert drp.find_paper_markdown(docs, RANGE, "2609.03454").name == "2609.03454v1-when-retrieval-helps.md"


def test_find_paper_markdown_single_day_layout_and_missing_dir(tmp_path):
    docs = tmp_path / "docs"
    day = docs / "202609" / "26"
    day.mkdir(parents=True)
    (day / "2609.00506v1-recalibrategpt.md").write_text(paper_markdown("RecalibrateGPT"), encoding="utf-8")
    assert drp.find_paper_markdown(docs, "20260926", "2609.00506v1") == day / "2609.00506v1-recalibrategpt.md"
    with pytest.raises(drp.DeepReadError, match="日报目录不存在"):
        drp.find_paper_markdown(docs, "20260925", "2609.00506v1")
    # 只有 .txt、没有 .md 时不能算找到
    (day / "2609.00507v1-only-text.txt").write_text("x", encoding="utf-8")
    with pytest.raises(drp.DeepReadError, match="找不到"):
        drp.find_paper_markdown(docs, "20260926", "2609.00507v1")


def test_resolve_target_fields(tmp_path):
    docs = make_docs(tmp_path)
    target = drp.resolve_target(docs, RANGE, " 2609.03454v1 ")
    assert target.paper_id == "2609.03454v1"
    assert target.basename == "2609.03454v1-when-retrieval-helps"
    assert target.slug == "when-retrieval-helps"
    assert target.title == "When Retrieval Helps"
    assert target.generator_title == "When Retrieval Helps"
    assert target.route == f"{RANGE}/2609.03454v1-when-retrieval-helps"
    assert target.href == f"#/{RANGE}/2609.03454v1-when-retrieval-helps"
    assert target.txt_path == docs / RANGE / "2609.03454v1-when-retrieval-helps.txt"
    assert target.artifact_rel_paths() == [
        f"{RANGE}/2609.03454v1-when-retrieval-helps.md",
        f"{RANGE}/2609.03454v1-when-retrieval-helps.txt",
        "assets/figures/arxiv/2609.03454v1",
        "assets/tables/arxiv/2609.03454v1",
    ]


def test_resolve_target_falls_back_to_slug_when_title_drifted(tmp_path, gen):
    docs = make_docs(tmp_path, md_text=paper_markdown(title="When Retrieval Helps (Revised Title)"))
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    assert target.generator_title == "when-retrieval-helps"
    # 生成器按 slugify(--paper-title) 拼文件名：兜底值必须指回原文件
    md_path, _, _ = gen.prepare_paper_paths(str(docs), RANGE, target.generator_title, target.paper_id)
    assert Path(md_path) == target.md_path


def test_resolve_target_rejects_filenames_the_generator_cannot_reproduce(tmp_path):
    docs = make_docs(tmp_path)
    (docs / RANGE / "2609.03454v1-when-retrieval-helps.md").rename(docs / RANGE / "2609.03454v1-When_Retrieval.md")
    with pytest.raises(drp.DeepReadError, match="slugify"):
        drp.resolve_target(docs, RANGE, "2609.03454v1")


def test_resolve_target_rejects_non_arxiv_source(tmp_path):
    docs = make_docs(tmp_path, md_text=paper_markdown(source="biorxiv"))
    with pytest.raises(drp.DeepReadError, match="arXiv"):
        drp.resolve_target(docs, RANGE, "2609.03454v1")


# ---------------------------------------------------------------------------
# 精读总结检测
# ---------------------------------------------------------------------------


def test_deep_block_detection(gen):
    quick = paper_markdown()
    complete = paper_markdown(deep_summary="## 1. 核心问题\n\n- 内容\n\n（完）")
    partial = paper_markdown(deep_summary="## 1. 核心问题\n\n- 被截断的内容")
    heading_only = quick.rstrip() + f"\n\n---\n\n{DEEP_HEADING}\n\n"
    crlf = complete.replace("\n", "\r\n")

    assert not drp.has_deep_block(quick)
    assert drp.has_deep_block(complete) and drp.deep_block_complete(complete)
    assert drp.has_deep_block(partial) and not drp.deep_block_complete(partial)
    assert not drp.has_deep_block(heading_only)
    assert drp.has_deep_block(crlf) and drp.deep_block_complete(crlf)
    inline = quick + f"\n正文里提到 {DEEP_HEADING} 不算标题\n"
    assert not drp.has_deep_block(inline)

    # 与上游 extract_section_tail（生成器判断「已有精读总结」的依据）保持一致
    for text in (quick, complete, partial, heading_only, crlf):
        assert drp.has_deep_block(text) == bool(gen.extract_section_tail(text, "论文详细总结（自动生成）"))


def test_deep_heading_constant_matches_generator_source():
    source = (ROOT / "src" / "6.generate_docs.py").read_text(encoding="utf-8")
    assert f'"{drp.DEEP_SUMMARY_HEADING}"' in source or f"'{drp.DEEP_SUMMARY_HEADING}'" in source
    assert drp.GENERATOR_ERROR_MARKER in source


# ---------------------------------------------------------------------------
# 侧边栏移动
# ---------------------------------------------------------------------------


def test_promote_moves_entry_within_its_block_only():
    new, status = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.03454v1")
    assert status == drp.SIDEBAR_MOVED
    expected = sidebar(range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, D)))
    assert new == expected
    # 同一篇论文在单日块 20260926 里的条目保持在速读区
    assert day_block_20260926() in new


def test_promote_diff_is_a_pure_move():
    new, _ = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.03454v1")
    diff = [
        line
        for line in difflib.unified_diff(SIDEBAR.split("\n"), new.split("\n"), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    assert sorted(diff) == sorted(["+" + T_RANGE.rstrip("\n"), "-" + T_RANGE.rstrip("\n")])


def test_promote_is_idempotent_and_already_deep_is_noop():
    once, _ = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.03454v1")
    twice, status = drp.promote_sidebar_entry(once, RANGE, "2609.03454v1")
    assert status == drp.SIDEBAR_ALREADY_DEEP
    assert twice == once
    same, status = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2608.28165v1")
    assert (same, status) == (SIDEBAR, drp.SIDEBAR_ALREADY_DEEP)


def test_promote_not_found_when_paper_only_in_other_block():
    new, status = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.00506v1")
    assert (new, status) == (SIDEBAR, drp.SIDEBAR_NOT_FOUND)


def test_single_day_token_skips_range_block_with_same_start_date():
    # 真实 docs/_sidebar.md 中 20260615-20260624 排在单日块 20260615 之前；
    # marker 必须整段匹配（含 `-->`），否则会停在区间块上返回 not_found。
    range_first = (
        "  * 2026-08-23 ~ 2026-08-30 <!--dpr-date:20260823-20260830-->\n    * 速读区\n"
        + entry("20260823-20260830/2608.11111v1-quick-only-g", "Quick Only G")
    )
    text = sidebar(quick_only=range_first + quick_only_block())
    new, status = drp.promote_sidebar_entry(text, "20260823", "2608.11111v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(quick_only=range_first + quick_only_block(deep=(G,), quick=(H,)))
    assert range_first in new
    # 反过来，区间 token 也只命中区间块
    new, status = drp.promote_sidebar_entry(text, "20260823-20260830", "2608.11111v1")
    assert status == drp.SIDEBAR_MOVED
    assert quick_only_block() in new


def test_promote_only_searches_daily_papers_section():
    stray = "  * 2026-09-30 <!--dpr-date:20260930-->\n    * 速读区\n" + entry(
        "202609/30/2609.77777v1-stray", "Stray"
    )
    text = SIDEBAR + stray  # 位于 `* Conference Papers` 之后，不属于日报
    assert drp.promote_sidebar_entry(text, "20260930", "2609.77777v1") == (text, drp.SIDEBAR_NOT_FOUND)


def test_promote_is_version_safe():
    new, status = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.03454v12")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(range=range_block(deep=(A, B, C_V12), quick=(T_RANGE, D)))
    with pytest.raises(drp.DeepReadError, match="2 次"):
        drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.03454")  # 裸编号同时命中 v1 与 v12
    new, status = drp.promote_sidebar_entry(SIDEBAR, "20260926", "2609.03454")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(day=day_block_20260926(quick=(F_DAY,)).replace(E_DAY, E_DAY + T_DAY))


def test_promote_creates_missing_deep_header_before_quick():
    new, status = drp.promote_sidebar_entry(SIDEBAR, "20260823", "2608.11111v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(quick_only=quick_only_block(deep=(G,), quick=(H,)))


def test_promote_removes_emptied_quick_header_and_supports_legacy_heading():
    new, status = drp.promote_sidebar_entry(SIDEBAR, "20260816", "2608.44444v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(lonely=lonely_block(deep=(I_, J), quick=()))
    assert "    * 速读区\n" + J not in new


def test_promote_preserves_crlf_and_unicode_separators():
    crlf = SIDEBAR.replace("\n", "\r\n")
    new, status = drp.promote_sidebar_entry(crlf, RANGE, "2609.03454v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, D))).replace("\n", "\r\n")
    # 需要新建「精读区」标题时，新行也用 CRLF
    new, status = drp.promote_sidebar_entry(crlf, "20260823", "2608.11111v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(quick_only=quick_only_block(deep=(G,), quick=(H,))).replace("\n", "\r\n")
    assert "\n" not in new.replace("\r\n", "")
    # 含 \u2028 的条目本身也能被移动且字节不变
    new, status = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.02797v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == sidebar(range=range_block(deep=(A, B, D), quick=(C_V12, T_RANGE)))


def test_promote_preserves_missing_trailing_newline_when_moving_last_line():
    text = HEAD + range_block()
    assert text.endswith(D)
    no_eol = text[:-1]
    new, status = drp.promote_sidebar_entry(no_eol, RANGE, "2609.02797v1")
    assert status == drp.SIDEBAR_MOVED
    assert new == (HEAD + range_block(deep=(A, B, D), quick=(C_V12, T_RANGE)))[:-1]
    assert not new.endswith("\n")


def test_promoted_sidebar_agrees_with_upstream_parsers(tmp_path, gen):
    new, _ = drp.promote_sidebar_entry(SIDEBAR, RANGE, "2609.03454v1")
    path = tmp_path / "_sidebar.md"
    path.write_text(new, encoding="utf-8")

    state = bootstrap_daily_state_from_sidebar(str(path), RANGE)
    sections = {p["route"]: p["section"] for p in state["papers"]}
    assert sections[f"{RANGE}/2609.03454v1-when-retrieval-helps"] == "deep"
    assert sections[f"{RANGE}/2609.03454v12-other-version-prefix"] == "quick"
    assert sections[f"{RANGE}/2608.28165v1-crabos"] == "deep"
    day_state = bootstrap_daily_state_from_sidebar(str(path), "20260926")
    assert {p["route"]: p["section"] for p in day_state["papers"]}["202609/26/2609.03454v1-when-retrieval-helps"] == "quick"

    lines = new.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if f"<!--dpr-date:{RANGE}-->" in line)
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("  * ") and not lines[i].startswith("    * "))
    deep_lines, quick_lines = gen._extract_day_block_papers(lines[start + 1:end])
    assert T_RANGE in deep_lines and T_RANGE not in quick_lines


# ---------------------------------------------------------------------------
# _daily_state.json 同步
# ---------------------------------------------------------------------------


def test_promote_daily_state_flips_only_section_and_keeps_format(tmp_path):
    path = tmp_path / "_daily_state.json"
    save_daily_state(str(path), RANGE_STATE)
    old = path.read_text(encoding="utf-8")
    route = f"{RANGE}/2609.03454v1-when-retrieval-helps"
    new, status = drp.promote_daily_state(old, route, "2609.03454v1")
    assert status == drp.SIDEBAR_MOVED
    changed = [
        line
        for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    assert changed == ['-      "section": "quick",', '+      "section": "deep",']
    # 与 save_daily_state 的输出格式逐字节一致
    expected = json.loads(old)
    expected["papers"][1]["section"] = "deep"
    save_daily_state(str(path), expected)
    assert new == path.read_text(encoding="utf-8")

    again, status = drp.promote_daily_state(new, route, "2609.03454v1")
    assert (again, status) == (new, drp.SIDEBAR_ALREADY_DEEP)


def test_promote_daily_state_matches_by_paper_id_and_reports_not_found():
    text = json.dumps(RANGE_STATE, ensure_ascii=False, indent=2) + "\n"
    new, status = drp.promote_daily_state(text, f"{RANGE}/renamed-route", "2609.03454v1")
    assert status == drp.SIDEBAR_MOVED
    assert [p["section"] for p in json.loads(new)["papers"]] == ["deep", "deep", "quick"]
    same, status = drp.promote_daily_state(text, f"{RANGE}/nope", "2609.99999v1")
    assert (same, status) == (text, drp.SIDEBAR_NOT_FOUND)
    with pytest.raises(drp.DeepReadError):
        drp.promote_daily_state("{not json", "r", "p")


# ---------------------------------------------------------------------------
# CLI：resolve / promote / paths
# ---------------------------------------------------------------------------


def test_cli_resolve_writes_github_output(tmp_path, capsys):
    docs = make_docs(tmp_path)
    out = tmp_path / "gh_output"
    code = drp.main(["resolve", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE, "--github-output", str(out)])
    assert code == 0
    assert out.read_text(encoding="utf-8") == (
        f"paper_id=2609.03454v1\npaper_date={RANGE}\nroute={RANGE}/2609.03454v1-when-retrieval-helps\n"
    )
    assert '"sidebar": "moved"' in capsys.readouterr().out


def test_cli_resolve_rejects_bad_input_without_echoing_raw_newlines(tmp_path, capsys):
    docs = make_docs(tmp_path)
    code = drp.main(["resolve", "--docs-dir", str(docs), "--paper-id", "2609.03454v1\n::error::x", "--paper-date", RANGE])
    assert code == 1
    out = capsys.readouterr().out
    assert out.startswith("[ERROR] ")
    assert "\n::error::" not in out


def test_cli_resolve_fails_early_when_sidebar_block_lacks_paper(tmp_path, capsys):
    docs = make_docs(tmp_path)
    (docs / "_sidebar.md").write_text(sidebar(range=range_block(quick=(C_V12, D))), encoding="utf-8")
    code = drp.main(["resolve", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE])
    assert code == 1
    assert "找不到" in capsys.readouterr().out


def test_cli_promote_updates_sidebar_and_state_idempotently(tmp_path):
    docs = make_docs(tmp_path)
    args = ["promote", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE]
    assert drp.main(args) == 0
    sidebar_after = (docs / "_sidebar.md").read_bytes()
    state_after = (docs / RANGE / "_daily_state.json").read_bytes()
    assert sidebar_after.decode("utf-8") == sidebar(range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, D)))
    assert [p["section"] for p in json.loads(state_after)["papers"]] == ["deep", "deep", "quick"]
    assert (docs / RANGE / "README.md").read_text(encoding="utf-8") == DAY_README_PROMOTED
    assert (docs / RANGE / "papers.meta.json").read_text(encoding="utf-8") == papers_meta_text(promoted=True)

    assert drp.main(args) == 0
    assert (docs / "_sidebar.md").read_bytes() == sidebar_after
    assert (docs / RANGE / "_daily_state.json").read_bytes() == state_after
    assert (docs / RANGE / "README.md").read_text(encoding="utf-8") == DAY_README_PROMOTED
    assert (docs / RANGE / "papers.meta.json").read_text(encoding="utf-8") == papers_meta_text(promoted=True)


def test_cli_promote_not_found_exits_nonzero_and_leaves_files(tmp_path):
    docs = make_docs(tmp_path)
    (docs / "_sidebar.md").write_text(sidebar(range=range_block(quick=(C_V12, D))), encoding="utf-8")
    before = (docs / "_sidebar.md").read_bytes()
    state_before = (docs / RANGE / "_daily_state.json").read_bytes()
    assert drp.main(["promote", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE]) == 1
    assert (docs / "_sidebar.md").read_bytes() == before
    assert (docs / RANGE / "_daily_state.json").read_bytes() == state_before
    assert (docs / RANGE / "README.md").read_text(encoding="utf-8") == DAY_README


def test_cli_promote_without_state_file(tmp_path, capsys):
    docs = make_docs(tmp_path, with_state=False)
    assert drp.main(["promote", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE]) == 0
    assert "_daily_state.json：absent" in capsys.readouterr().out


def test_cli_paths_lists_existing_paper_files_only(tmp_path, monkeypatch, capsys):
    make_docs(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert drp.main(["paths", "--docs-dir", "docs", "--paper-id", "2609.03454v1", "--paper-date", RANGE]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"docs/{RANGE}/2609.03454v1-when-retrieval-helps.md",
        f"docs/{RANGE}/2609.03454v1-when-retrieval-helps.txt",
        "docs/assets/figures/arxiv/2609.03454v1",
        "docs/_sidebar.md",
        f"docs/{RANGE}/_daily_state.json",
        f"docs/{RANGE}/README.md",
        f"docs/{RANGE}/papers.meta.json",
    ]


def test_cli_check(tmp_path):
    docs = make_docs(tmp_path)
    args = ["check", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE]
    assert drp.main(args) == 1
    (docs / RANGE / "2609.03454v1-when-retrieval-helps.md").write_text(
        paper_markdown(deep_summary="内容\n\n（完）"), encoding="utf-8"
    )
    assert drp.main(args) == 0


# ---------------------------------------------------------------------------
# generate：子进程调用生成器 + 独立判定成功
# ---------------------------------------------------------------------------

FAKE_GENERATOR = textwrap.dedent(
    """\
    import argparse, json, os, re, sys
    p = argparse.ArgumentParser()
    for name in ("--docs-dir", "--paper-id", "--paper-section", "--paper-date", "--paper-title"):
        p.add_argument(name)
    a = p.parse_args()
    mode = os.environ["FAKE_MODE"]
    with open(os.environ["FAKE_ARGV_LOG"], "w", encoding="utf-8") as fh:
        json.dump(sys.argv[1:], fh)
    slug = re.sub(r"[^a-z0-9\\-]+", "", re.sub(r"\\s+", "-", a.paper_title.strip().lower())) or "paper"
    day = os.path.join(a.docs_dir, a.paper_date)
    md = os.path.join(day, f"{a.paper_id}-{slug}.md")
    # 模拟 backfill_history_day_reports 的副作用
    os.makedirs(os.path.join(a.docs_dir, "202609", "01"), exist_ok=True)
    if mode in ("ok", "error_marker", "new_file"):
        # error_marker / new_file 也写入精读总结，确保对应的独立检查本身能拦住失败
        with open(md, "a", encoding="utf-8") as fh:
            fh.write("\\n\\n---\\n\\n## 论文详细总结（自动生成）\\n\\n内容\\n\\n（完）\\n")
    if mode == "ok":
        fig = os.path.join(a.docs_dir, "assets", "figures", "arxiv", a.paper_id)
        os.makedirs(fig, exist_ok=True)
        with open(os.path.join(fig, "fig-001.webp"), "wb") as fh:
            fh.write(b"webp")
        print("[OK] 单篇论文已生成")
    elif mode == "partial":
        with open(md, "a", encoding="utf-8") as fh:
            fh.write("\\n\\n---\\n\\n## 论文详细总结（自动生成）\\n\\n被截断\\n")
    elif mode == "error_marker":
        print("[2026-09-27 00:00:00] [ERROR] 单篇论文生成失败：arXiv API 请求失败")
    elif mode == "new_file":
        with open(os.path.join(day, f"{a.paper_id}-different-slug.md"), "w", encoding="utf-8") as fh:
            fh.write("## 论文详细总结（自动生成）\\n\\nx\\n")
    elif mode == "glance":
        # 模拟 PR #1 之前 main 的 process_paper：正文没有 `## 速览` 时插入一份，再追加精读总结
        with open(md, encoding="utf-8") as fh:
            txt = fh.read()
        idx = txt.find("## Abstract")
        txt = f"{txt[:idx].rstrip()}\\n\\n## 速览\\n**TLDR**：模拟 \\\\\\n**Conclusion**：模拟\\n\\n---\\n\\n{txt[idx:]}"
        txt += "\\n\\n---\\n\\n## 论文详细总结（自动生成）\\n\\n内容\\n\\n（完）\\n"
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(txt)
    elif mode == "remedia":
        # 模拟 PAPERCROPPER_DISABLE=1 时 ensure_paper_media 退回 PyMuPDF：改写已有图目录，
        # 另外新建表目录（原文没有 tables_json 时允许新增）
        with open(md, "a", encoding="utf-8") as fh:
            fh.write("\\n\\n---\\n\\n## 论文详细总结（自动生成）\\n\\n内容\\n\\n（完）\\n")
        fig = os.path.join(a.docs_dir, "assets", "figures", "arxiv", a.paper_id)
        os.makedirs(os.path.join(fig, "sub"), exist_ok=True)
        for name, data in (("fig-001.webp", b"pymupdf"), ("meta.json", b'{"extractor": "pymupdf-images"}'),
                           ("fig-002.webp", b"new"), ("sub/x.webp", b"x")):
            with open(os.path.join(fig, name), "wb") as fh:
                fh.write(data)
        tab = os.path.join(a.docs_dir, "assets", "tables", "arxiv", a.paper_id)
        os.makedirs(tab, exist_ok=True)
        with open(os.path.join(tab, "table-001.webp"), "wb") as fh:
            fh.write(b"table")
        if os.environ.get("FAKE_THEN_FAIL"):
            print("[ERROR] 单篇论文生成失败：模拟")
    elif mode == "crash":
        sys.exit(3)
    elif mode == "must_not_run":
        sys.exit(99)
    """
)


def run_generate(tmp_path, monkeypatch, mode, paper_id="2609.03454v1", md_text=None, api_key="sk-test", setup=None):
    docs = make_docs(tmp_path, md_text=md_text)
    if setup is not None:
        setup(docs)
    fake = tmp_path / "fake_generator.py"
    fake.write_text(FAKE_GENERATOR, encoding="utf-8")
    argv_log = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_MODE", mode)
    monkeypatch.setenv("FAKE_ARGV_LOG", str(argv_log))
    monkeypatch.delenv("SUMMARY_API_KEY", raising=False)
    if api_key:
        monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
    else:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    stash = tmp_path / "stash"
    code = drp.main(
        [
            "generate", "--docs-dir", str(docs), "--paper-id", paper_id, "--paper-date", RANGE,
            "--stash", str(stash), "--generator", str(fake),
        ]
    )
    argv = json.loads(argv_log.read_text(encoding="utf-8")) if argv_log.exists() else None
    return code, docs, stash, argv


def test_generate_success_passes_versioned_id_and_front_matter_title(tmp_path, monkeypatch):
    code, docs, stash, argv = run_generate(tmp_path, monkeypatch, "ok", paper_id="2609.03454v1")
    assert code == 0
    assert argv[argv.index("--paper-id") + 1] == "2609.03454v1"
    assert argv[argv.index("--paper-section") + 1] == "deep"
    assert argv[argv.index("--paper-date") + 1] == RANGE
    assert argv[argv.index("--paper-title") + 1] == "When Retrieval Helps"
    assert argv[argv.index("--docs-dir") + 1] == str(docs.resolve())
    md_rel = f"{RANGE}/2609.03454v1-when-retrieval-helps.md"
    assert not drp.has_deep_block((stash / "base" / md_rel).read_text(encoding="utf-8"))
    assert drp.has_deep_block((stash / "gen" / md_rel).read_text(encoding="utf-8"))
    # front matter 已有 figures_json：图目录只读，生成器新写的图被丢弃
    assert not (stash / "gen" / "assets/figures/arxiv/2609.03454v1/fig-001.webp").exists()
    assert not (docs / "assets/figures/arxiv/2609.03454v1/fig-001.webp").exists()


def test_generate_keeps_new_media_when_front_matter_has_none(tmp_path, monkeypatch):
    md = paper_markdown(media=())
    code, docs, stash, _ = run_generate(tmp_path, monkeypatch, "ok", md_text=md)
    assert code == 0
    assert (stash / "gen" / "assets/figures/arxiv/2609.03454v1/fig-001.webp").read_bytes() == b"webp"
    assert not (stash / "base" / "assets/figures/arxiv/2609.03454v1/fig-001.webp").exists()


PAPERCROPPER_FIG = b"papercropper-fig"
PAPERCROPPER_META = b'{"extractor": "papercropper", "figures": [{"width": 1253, "height": 1004}]}'


def with_papercropper_figures(docs):
    fig = docs / "assets" / "figures" / "arxiv" / "2609.03454v1"
    (fig / "fig-001.webp").write_bytes(PAPERCROPPER_FIG)
    (fig / "meta.json").write_bytes(PAPERCROPPER_META)


@pytest.mark.parametrize("then_fail", [False, True])
def test_generate_never_rewrites_media_already_referenced_by_front_matter(tmp_path, monkeypatch, capsys, then_fail):
    # 真实形态（main 上约 8% 的速读论文，例如 2604.27882v1）：有 figures_json、没有 tables_json，
    # 图目录是 PaperCropper 裁的图，没有 tables 目录 → 生成器会重跑图表提取并改写图目录。
    if then_fail:
        monkeypatch.setenv("FAKE_THEN_FAIL", "1")
    md = paper_markdown(media=("figures",))
    code, docs, stash, _ = run_generate(tmp_path, monkeypatch, "remedia", md_text=md, setup=with_papercropper_figures)
    fig_rel = "assets/figures/arxiv/2609.03454v1"
    fig = docs / fig_rel
    # 无论成功失败，本地图目录都被还原（包括删掉新增文件/子目录）
    assert sorted(p.name for p in fig.iterdir()) == ["fig-001.webp", "meta.json"]
    assert (fig / "fig-001.webp").read_bytes() == PAPERCROPPER_FIG
    assert (fig / "meta.json").read_bytes() == PAPERCROPPER_META
    if then_fail:
        assert code == 1
        return
    assert code == 0
    assert "丢弃生成器的改动" in capsys.readouterr().out
    for f in ("fig-001.webp", "meta.json"):
        assert (stash / "gen" / fig_rel / f).read_bytes() == (stash / "base" / fig_rel / f).read_bytes()
    assert not (stash / "gen" / fig_rel / "fig-002.webp").exists()
    # 原文没有 tables_json：新增的表格照常保留
    assert (stash / "gen" / "assets/tables/arxiv/2609.03454v1/table-001.webp").read_bytes() == b"table"

    # apply 到新检出的工作区：图目录不变，新表格与精读总结写入
    reset_docs_to_base(docs, stash)
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    assert drp.apply_artifacts(docs, stash, target) == "applied"
    assert (fig / "fig-001.webp").read_bytes() == PAPERCROPPER_FIG
    assert (fig / "meta.json").read_bytes() == PAPERCROPPER_META
    assert not (fig / "fig-002.webp").exists()
    assert (docs / "assets/tables/arxiv/2609.03454v1/table-001.webp").read_bytes() == b"table"
    assert drp.has_deep_block(target.md_path.read_text(encoding="utf-8"))


def test_protected_asset_rel_paths_follow_front_matter(tmp_path):
    docs = make_docs(tmp_path)
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    fig, tab = "assets/figures/arxiv/2609.03454v1", "assets/tables/arxiv/2609.03454v1"
    assert target.protected_asset_rel_paths(paper_markdown()) == [fig, tab]
    assert target.protected_asset_rel_paths(paper_markdown(media=("figures",))) == [fig]
    assert target.protected_asset_rel_paths(paper_markdown(media=("tables",))) == [tab]
    assert target.protected_asset_rel_paths(paper_markdown(media=())) == []
    assert target.protected_asset_rel_paths(paper_markdown(media=()).replace("tldr:", 'figures_json: ""\ntldr:')) == []


def test_generate_bare_id_is_expanded_before_calling_generator(tmp_path, monkeypatch):
    code, _, _, argv = run_generate(tmp_path, monkeypatch, "ok", paper_id="2609.02797")
    assert code == 0
    assert argv[argv.index("--paper-id") + 1] == "2609.02797v1"
    assert argv[argv.index("--paper-title") + 1] == "Dutch Books"


@pytest.mark.parametrize(
    "mode, message",
    [
        ("error_marker", "生成器报告单篇论文生成失败"),
        ("new_file", "生成器改变了"),
        ("crash", "生成器退出码 3"),
    ],
)
def test_generate_fails_when_generator_fails(tmp_path, monkeypatch, capsys, mode, message):
    code, docs, stash, _ = run_generate(tmp_path, monkeypatch, mode)
    assert code == 1
    assert f"[ERROR] {message}" in capsys.readouterr().out
    assert not (stash / "gen").exists()


def test_generate_fails_when_generator_silently_writes_nothing(tmp_path, monkeypatch, capsys):
    code, _, stash, _ = run_generate(tmp_path, monkeypatch, "noop")
    assert code == 1
    assert "没有「## 论文详细总结（自动生成）」" in capsys.readouterr().out
    assert not (stash / "gen").exists()


def test_generate_warns_on_truncated_summary(tmp_path, monkeypatch, capsys):
    code, _, _, _ = run_generate(tmp_path, monkeypatch, "partial")
    assert code == 0
    assert "（完）" in capsys.readouterr().out


def test_generate_requires_llm_key(tmp_path, monkeypatch, capsys):
    code, _, _, argv = run_generate(tmp_path, monkeypatch, "ok", api_key=None)
    assert code == 1
    assert argv is None
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().out


def test_generate_skips_generator_when_already_deep(tmp_path, monkeypatch):
    md = paper_markdown(deep_summary="内容\n\n（完）")
    code, _, stash, argv = run_generate(tmp_path, monkeypatch, "must_not_run", md_text=md, api_key=None)
    assert code == 0
    assert argv is None
    md_rel = f"{RANGE}/2609.03454v1-when-retrieval-helps.md"
    assert (stash / "base" / md_rel).read_bytes() == (stash / "gen" / md_rel).read_bytes()


# ---------------------------------------------------------------------------
# apply：把产物三方比较后写回最新 origin
# ---------------------------------------------------------------------------


def prepared_stash(tmp_path, monkeypatch):
    # 原文没有 figures_json/tables_json：生成器新增的图允许写回
    code, docs, stash, _ = run_generate(tmp_path, monkeypatch, "ok", md_text=paper_markdown(media=()))
    assert code == 0
    return docs, stash


def reset_docs_to_base(docs, stash):
    """模拟 workflow：reset 到 origin 后 docs 回到生成前的状态。"""
    for path in (stash / "gen").rglob("*"):
        if path.is_file():
            rel = path.relative_to(stash / "gen")
            base = stash / "base" / rel
            if base.exists():
                (docs / rel).write_bytes(base.read_bytes())
            else:
                (docs / rel).unlink()


def test_apply_writes_generated_files_onto_fresh_checkout(tmp_path, monkeypatch):
    docs, stash = prepared_stash(tmp_path, monkeypatch)
    reset_docs_to_base(docs, stash)
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    assert drp.apply_artifacts(docs, stash, target) == "applied"
    assert drp.has_deep_block(target.md_path.read_text(encoding="utf-8"))
    assert (docs / "assets/figures/arxiv/2609.03454v1/fig-001.webp").read_bytes() == b"webp"
    assert drp.apply_artifacts(docs, stash, target) == "unchanged"


def test_apply_refuses_to_clobber_concurrent_edit(tmp_path, monkeypatch):
    docs, stash = prepared_stash(tmp_path, monkeypatch)
    reset_docs_to_base(docs, stash)
    md = docs / RANGE / "2609.03454v1-when-retrieval-helps.md"
    md.write_text(md.read_text(encoding="utf-8") + "\n别人刚改过\n", encoding="utf-8")
    concurrent = md.read_bytes()
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    with pytest.raises(drp.DeepReadError, match="并发修改"):
        drp.apply_artifacts(docs, stash, target)
    assert md.read_bytes() == concurrent
    assert not (docs / "assets/figures/arxiv/2609.03454v1/fig-001.webp").exists()


def test_apply_keeps_remote_version_when_already_upgraded_elsewhere(tmp_path, monkeypatch):
    docs, stash = prepared_stash(tmp_path, monkeypatch)
    reset_docs_to_base(docs, stash)
    md = docs / RANGE / "2609.03454v1-when-retrieval-helps.md"
    md.write_text(paper_markdown(deep_summary="另一轮运行写的总结\n\n（完）"), encoding="utf-8")
    remote = md.read_bytes()
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    assert drp.apply_artifacts(docs, stash, target) == "superseded"
    assert md.read_bytes() == remote


def test_apply_ignores_remote_changes_to_files_the_generator_left_alone(tmp_path, monkeypatch):
    docs, stash = prepared_stash(tmp_path, monkeypatch)
    reset_docs_to_base(docs, stash)
    txt = docs / RANGE / "2609.03454v1-when-retrieval-helps.txt"
    meta = docs / "assets/figures/arxiv/2609.03454v1/meta.json"
    rel_txt = f"{RANGE}/2609.03454v1-when-retrieval-helps.txt"
    assert (stash / "gen" / rel_txt).read_bytes() == (stash / "base" / rel_txt).read_bytes()
    txt.write_text("远端日报刚更新的全文\n", encoding="utf-8")
    meta.write_text('{"figures": [], "remote": true}\n', encoding="utf-8")
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    assert drp.apply_artifacts(docs, stash, target) == "applied"
    assert txt.read_text(encoding="utf-8") == "远端日报刚更新的全文\n"
    assert meta.read_text(encoding="utf-8") == '{"figures": [], "remote": true}\n'
    assert drp.has_deep_block(target.md_path.read_text(encoding="utf-8"))


def test_apply_requires_generate_snapshot(tmp_path):
    docs = make_docs(tmp_path)
    target = drp.resolve_target(docs, RANGE, "2609.03454v1")
    with pytest.raises(drp.DeepReadError, match="generate"):
        drp.apply_artifacts(docs, tmp_path / "missing-stash", target)


# ---------------------------------------------------------------------------
# 侧边栏修复：同 token 日报重跑 + rebase -X theirs 留下的重复条目
# ---------------------------------------------------------------------------


def test_promote_repairs_duplicate_left_by_daily_rerun_race():
    # 真实复现过的形态：精读区末尾一份、速读区还有一份（后面跟着日报重跑新加的论文）
    NEW = entry(f"{RANGE}/2609.99999v1-new-paper", "New Paper")
    corrupted = sidebar(range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, D, T_RANGE, NEW)))
    new, status = drp.promote_sidebar_entry(corrupted, RANGE, "2609.03454v1")
    assert status == drp.SIDEBAR_DEDUPED
    assert new == sidebar(range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, D, NEW)))
    again, status = drp.promote_sidebar_entry(new, RANGE, "2609.03454v1")
    assert (again, status) == (new, drp.SIDEBAR_ALREADY_DEEP)


def test_promote_dedup_removes_emptied_quick_header():
    corrupted = sidebar(quick_only=quick_only_block(deep=(G,), quick=(G,)))
    new, status = drp.promote_sidebar_entry(corrupted, "20260823", "2608.11111v1")
    assert status == drp.SIDEBAR_DEDUPED
    assert new == sidebar(quick_only=quick_only_block(deep=(G,), quick=()))


@pytest.mark.parametrize(
    "block",
    [
        range_block(deep=(A, T_RANGE, T_RANGE), quick=(D,)),  # 精读区两份：不知道哪份是对的
        range_block(deep=(A,), quick=(T_RANGE, D, T_RANGE)),  # 只在速读区重复
    ],
)
def test_promote_still_refuses_other_duplicates(block):
    with pytest.raises(drp.DeepReadError, match="2 次"):
        drp.promote_sidebar_entry(sidebar(range=block), RANGE, "2609.03454v1")


def test_promote_refuses_two_deep_copies_plus_quick_copy():
    # 精读区两份 + 速读区一份：进入修复分支的前提（精读区恰好 1 份）不成立，必须报错
    text = sidebar(range=range_block(deep=(A, T_RANGE, T_RANGE), quick=(T_RANGE, D)))
    with pytest.raises(drp.DeepReadError, match="3 次"):
        drp.promote_sidebar_entry(text, RANGE, "2609.03454v1")


def test_promote_bare_id_never_dedups_across_versions():
    # 裸编号：精读区 v1 + 速读区 v12 是两篇不同的论文（href 不同），不能把 v12 当残留删掉
    text = sidebar(range=range_block(deep=(A, T_RANGE), quick=(C_V12, D)))
    with pytest.raises(drp.DeepReadError, match="2 次"):
        drp.promote_sidebar_entry(text, RANGE, "2609.03454")
    # 带版本号时只命中 v1，已在精读区，v12 条目不受影响
    assert drp.promote_sidebar_entry(text, RANGE, "2609.03454v1") == (text, drp.SIDEBAR_ALREADY_DEEP)
    assert drp.promote_sidebar_entry(text, RANGE, "2609.03454v12")[0].count("2609.03454v12-other-version-prefix") == 1


def test_promote_headerless_legacy_block_counts_as_deep():
    # 真实 docs/_sidebar.md 末尾有无分区标题的旧格式块（2017-06-12 Attention Is All You Need）
    legacy = entry("201706/12/1706.03762v1-attention-is-all-you-need", "Attention Is All You Need")
    text = sidebar(lonely="  * 2017-06-12\n" + legacy)
    assert drp.promote_sidebar_entry(text, "20170612", "1706.03762v1") == (text, drp.SIDEBAR_ALREADY_DEEP)


def test_cli_resolve_and_promote_accept_duplicated_block(tmp_path, capsys):
    docs = make_docs(tmp_path)
    (docs / "_sidebar.md").write_text(
        sidebar(range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, T_RANGE, D))), encoding="utf-8"
    )
    base = ["--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE]
    assert drp.main(["resolve", *base]) == 0
    assert '"sidebar": "deduped"' in capsys.readouterr().out
    assert drp.main(["promote", *base]) == 0
    assert (docs / "_sidebar.md").read_text(encoding="utf-8") == sidebar(
        range=range_block(deep=(A, B, T_RANGE), quick=(C_V12, D))
    )
    assert [p["section"] for p in json.loads((docs / RANGE / "_daily_state.json").read_text(encoding="utf-8"))["papers"]] == [
        "deep", "deep", "quick"
    ]


# ---------------------------------------------------------------------------
# long-range 回溯块（PR #1 之后：<id>.md，无 slug）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("paper_id", ["2601.00001v1", "2601.00001"])
def test_long_range_slugless_markdown_is_rejected_with_clear_message(tmp_path, paper_id):
    docs = tmp_path / "docs"
    day = docs / "20260101-20260301"
    day.mkdir(parents=True)
    (day / "2601.00001v1.md").write_text(paper_markdown("Long Range"), encoding="utf-8")
    with pytest.raises(drp.DeepReadError, match="long-range"):
        drp.resolve_target(docs, "20260101-20260301", paper_id)


# ---------------------------------------------------------------------------
# 正文速览去重（PR #1 之前的 main）
# ---------------------------------------------------------------------------


def test_strip_inserted_glance_undoes_upstream_insertion(gen):
    base = paper_markdown()
    assert "## 速览" not in base
    inserted = gen.upsert_glance_block_in_text(base, "**TLDR**：x \\\n**Conclusion**：y\n\n---\n\n## 不是标题")
    assert inserted != base
    deep = inserted.rstrip() + f"\n\n---\n\n{DEEP_HEADING}\n\n内容\n\n（完）\n"
    stripped, changed = drp.strip_inserted_glance(base, deep)
    # 注意：速览里自带 `---` 与 `## ` 时 count("## 速览") 仍为 1，但正则取到最近的 `---` + `## Abstract`
    assert changed
    assert stripped == base.rstrip() + f"\n\n---\n\n{DEEP_HEADING}\n\n内容\n\n（完）\n"
    assert "## 速览" not in stripped and drp.has_deep_block(stripped)


def test_strip_inserted_glance_keeps_glance_when_it_is_the_only_one(gen):
    no_front_glance = "\n".join(
        line for line in paper_markdown().split("\n")
        if not line.startswith(("tldr:", "motivation:", "method:", "result:", "conclusion:"))
    )
    inserted = gen.upsert_glance_block_in_text(no_front_glance, "**TLDR**：x")
    assert drp.strip_inserted_glance(no_front_glance, inserted) == (inserted, False)


def test_strip_inserted_glance_keeps_existing_body_glance(gen):
    # 原文已有正文速览且 front matter 也有速览字段：这份速览是用户已经看到的，不能删
    base = gen.upsert_glance_block_in_text(paper_markdown(), "**TLDR**：x")
    assert "## 速览" in base and drp.parse_front_matter(base).get("tldr")
    deep = base.rstrip() + f"\n\n---\n\n{DEEP_HEADING}\n\n内容\n\n（完）\n"
    assert drp.strip_inserted_glance(base, deep) == (deep, False)


def test_generate_strips_body_glance_inserted_on_old_main(tmp_path, monkeypatch, capsys):
    code, docs, stash, _ = run_generate(tmp_path, monkeypatch, "glance")
    assert code == 0
    md_rel = f"{RANGE}/2609.03454v1-when-retrieval-helps.md"
    text = (docs / md_rel).read_text(encoding="utf-8")
    assert "## 速览" not in text and drp.deep_block_complete(text)
    assert text.startswith(paper_markdown().rstrip())
    assert (stash / "gen" / md_rel).read_text(encoding="utf-8") == text
    assert "正文「## 速览」" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 日报 README / papers.meta.json
# ---------------------------------------------------------------------------


def upstream_report(gen, deep, quick):
    def rows(items):
        return [(route, title, [("score", score)] if score else []) for route, title, score in items]

    return gen.build_day_report_markdown(
        date_str=RANGE,
        date_label=None,
        deep_entries=rows(deep),
        quick_entries=rows(quick),
        recommend_exists=True,
        generated_at="2026-09-26 13:55:16 UTC",
        summary="精读1篇、速读2篇。",
    )


def test_promote_day_report_matches_upstream_builder(gen):
    a, t, d = (R_A + ("9.0",)), (R_T + ("7.0",)), (R_D + ("",))
    before = upstream_report(gen, [a], [t, d])
    new, status = drp.promote_day_report(before, R_T[0])
    assert status == drp.SIDEBAR_MOVED
    assert new == upstream_report(gen, [a, t], [d])
    assert drp.promote_day_report(new, R_T[0]) == (new, drp.SIDEBAR_ALREADY_DEEP)
    # 空精读区（占位行）→ 第一条；速读区被移空 → 占位行
    only_quick = upstream_report(gen, [], [t])
    new, status = drp.promote_day_report(only_quick, R_T[0])
    assert status == drp.SIDEBAR_MOVED
    assert new == upstream_report(gen, [t], [])
    # 测试夹具 day_readme() 与上游格式一致
    assert DAY_README == upstream_report(gen, [R_A + ("9.0",)], [t, R_D + ("6.0",)])


def test_promote_day_report_crlf_duplicates_and_unknown_formats():
    crlf = DAY_README.replace("\n", "\r\n")
    new, status = drp.promote_day_report(crlf, R_T[0])
    assert (new, status) == (DAY_README_PROMOTED.replace("\n", "\r\n"), drp.SIDEBAR_MOVED)
    dup = day_readme(  # 计数也是旧的：总数 3 不变，两节计数按实际条目重算
        [report_line(1, R_A[1], R_A[0], "9.0/10"), report_line(2, R_T[1], R_T[0])],
        [report_line(1, R_T[1], R_T[0]), report_line(2, R_D[1], R_D[0], "6.0/10")],
        deep_count=1,
        quick_count=2,
    )
    new, status = drp.promote_day_report(dup, R_T[0])
    assert (new, status) == (DAY_README_PROMOTED, drp.SIDEBAR_DEDUPED)
    assert drp.promote_day_report(DAY_README, f"{RANGE}/2609.99999v1-x") == (DAY_README, drp.SIDEBAR_NOT_FOUND)
    assert drp.promote_day_report("# 日报\n", R_T[0]) == ("# 日报\n", drp.SKIPPED)
    # 版本前缀不能误中（v1 vs v12）
    v12 = DAY_README.replace(R_T[0], f"{RANGE}/2609.03454v12-other-version-prefix")
    assert drp.promote_day_report(v12, R_T[0]) == (v12, drp.SIDEBAR_NOT_FOUND)


def test_promote_papers_meta_flips_section_only_for_generator_format():
    old = papers_meta_text()
    new, status = drp.promote_papers_meta(old, R_T[0])
    assert (new, status) == (papers_meta_text(promoted=True), drp.SIDEBAR_MOVED)
    assert drp.promote_papers_meta(new, R_T[0]) == (new, drp.SIDEBAR_ALREADY_DEEP)
    assert drp.promote_papers_meta(old, f"{RANGE}/nope") == (old, drp.SIDEBAR_NOT_FOUND)
    compact = json.dumps(json.loads(old), ensure_ascii=False)
    assert drp.promote_papers_meta(compact, R_T[0]) == (compact, drp.SKIPPED)
    assert drp.promote_papers_meta("{bad", R_T[0]) == ("{bad", drp.SKIPPED)


def test_cli_promote_leaves_unrecognised_readme_alone(tmp_path, capsys):
    docs = make_docs(tmp_path)
    (docs / RANGE / "README.md").write_text("# 自定义日报\n", encoding="utf-8")
    (docs / RANGE / "papers.meta.json").unlink()
    assert drp.main(["promote", "--docs-dir", str(docs), "--paper-id", "2609.03454v1", "--paper-date", RANGE]) == 0
    assert (docs / RANGE / "README.md").read_text(encoding="utf-8") == "# 自定义日报\n"
    out = capsys.readouterr().out
    assert "日报 README：skipped" in out and "papers.meta.json：absent" in out
