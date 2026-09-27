#!/usr/bin/env python
"""单篇论文「速读区 → 精读区」升级（fork 专用，供 .github/workflows/deep-read-paper.yml 调用）。

复用 `src/6.generate_docs.py` 已有的单篇模式（--paper-id/--paper-section deep/--paper-date）
生成精读长总结，本模块只负责上游单篇模式没有覆盖的部分：

- resolve   严格校验输入，定位侧边栏 href 指向的那份已有 Markdown（不改任何文件）
- generate  以子进程调用生成器，并独立判定成功（生成器失败时也会以 exit 0 返回）；
            front matter 已引用的图/表目录只读，生成器对它们的改动会被还原
- apply     把 generate 留下的产物按「三方比较」写回到最新的 origin 工作区
- promote   把侧边栏条目从 速读区 挪到同一日期块的 精读区，并同步 _daily_state.json、
            日报 README.md 的两节列表与计数、papers.meta.json 的 section（纯文本，无 LLM）
- paths     列出需要提交的路径（供 workflow 精确 git add）
- check     检查 Markdown 是否已经包含精读总结

模块只依赖标准库，生成器通过子进程调用，因此 resolve 可以在安装依赖之前运行。

已知不处理的部分：首页 docs/README.md（只有该日期块是最新一期时才相关，下一次日报运行会重建）、
日报 README 中 LLM 写的「今日简报（AI）」段落里的篇数描述；PR #1 之后 long-range 回溯块
（<id>.md，无 slug）不支持单篇精读，resolve 会直接报错。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOCS_DIR = ROOT_DIR / "docs"
GENERATOR_SCRIPT = ROOT_DIR / "src" / "6.generate_docs.py"

# 与 src/6.generate_docs.py 保持一致：upsert_auto_block(md, "论文详细总结（自动生成）", summary)
DEEP_SUMMARY_HEADING = "论文详细总结（自动生成）"
DEEP_SUMMARY_END_MARKER = "（完）"
# 生成器单篇模式吞掉异常后只打印这一行，然后以 exit 0 返回。
GENERATOR_ERROR_MARKER = "[ERROR] 单篇论文生成失败"

# 只接受 arXiv 新式编号；版本号可省略（此时要求目录里只有一个版本）。
PAPER_ID_RE = re.compile(r"(?P<base>\d{4}\.\d{4,5})(?P<version>v[1-9]\d*)?")
DATE_TOKEN_RE = re.compile(r"(?P<start>\d{8})(?:-(?P<end>\d{8}))?")
SAFE_OUTPUT_RE = re.compile(r"[A-Za-z0-9._/-]+")

DEEP_SECTION = "精读区"
QUICK_SECTION = "速读区"
DEEP_HEADER_RE = re.compile(r"^ {4}\*\s+精读区\s*$")
QUICK_HEADER_RE = re.compile(r"^ {4}\*\s+速读区\s*$")
DAILY_ROOT_RE = re.compile(r"^\*\s*Daily Papers")
# 与前端 dpr-sidebar.js 的解析一致：0-3 个空格缩进的 `* ` 行结束当前日期块
# （覆盖 update_sidebar 的 `  * ` 与顶层 `* ` 两种结束条件）。
BLOCK_END_RE = re.compile(r"^ {0,3}\*\s")

SIDEBAR_MOVED = "moved"
SIDEBAR_ALREADY_DEEP = "already_deep"
SIDEBAR_NOT_FOUND = "not_found"
SIDEBAR_DEDUPED = "deduped"
SKIPPED = "skipped"


class DeepReadError(ValueError):
    """面向用户的错误：CLI 打印 `[ERROR] ...` 并以非零状态退出。"""


def log(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    log(f"[WARN] {message}")
    if os.getenv("GITHUB_ACTIONS") == "true":
        # message 只包含内部生成的文本，不含原始用户输入，避免伪造 workflow 命令。
        log(f"::warning::{message}")


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------


def validate_paper_id(value: str) -> str:
    """校验 arXiv 新式编号（如 2609.03454v1 / 2609.03454），返回去掉首尾空白后的值。"""
    text = str(value if value is not None else "").strip()
    if not PAPER_ID_RE.fullmatch(text):
        raise DeepReadError(
            f"paper_id 格式不合法：{text!r}；需要 arXiv 新式编号，例如 2609.03454v1（版本号可省略）。"
        )
    return text


def is_versioned_paper_id(paper_id: str) -> bool:
    match = PAPER_ID_RE.fullmatch(paper_id)
    return bool(match and match.group("version"))


def validate_date_token(value: str) -> str:
    """校验日报目录 token：单日 YYYYMMDD 或区间 YYYYMMDD-YYYYMMDD（与 <!--dpr-date:...--> 一致）。"""
    text = str(value if value is not None else "").strip()
    match = DATE_TOKEN_RE.fullmatch(text)
    if not match:
        raise DeepReadError(
            f"paper_date 格式不合法：{text!r}；需要 YYYYMMDD 或 YYYYMMDD-YYYYMMDD。"
        )
    days = [match.group("start")] + ([match.group("end")] if match.group("end") else [])
    parsed = []
    for day in days:
        try:
            parsed.append(datetime.strptime(day, "%Y%m%d"))
        except ValueError:
            raise DeepReadError(f"paper_date 不是有效日期：{text!r}。") from None
    if len(parsed) == 2 and parsed[1] < parsed[0]:
        raise DeepReadError(f"paper_date 区间起止颠倒：{text!r}。")
    return text


def route_dir_for(date_token: str) -> str:
    """docs 下的目录（也是 docsify 路由前缀），与 6.generate_docs.prepare_paper_paths 一致。"""
    token = validate_date_token(date_token)
    if "-" in token:
        return token
    return f"{token[:6]}/{token[6:]}"


def format_date_label(date_token: str) -> str:
    token = validate_date_token(date_token)
    match = DATE_TOKEN_RE.fullmatch(token)
    assert match
    start, end = match.group("start"), match.group("end")
    label = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    if end:
        label += f" ~ {end[:4]}-{end[4:6]}-{end[6:]}"
    return label


def slugify(title: str) -> str:
    """与 6.generate_docs.slugify 完全一致（由测试锁定）。"""
    s = (title or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    return s or "paper"


def safe_asset_key(value: str) -> str:
    """与 paper_figures._safe_asset_key 完全一致（由测试锁定）。"""
    text = str(value or "").strip()
    if not text:
        return "paper"
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    text = text.strip("-._")
    return text or "paper"


# ---------------------------------------------------------------------------
# 论文 Markdown 定位
# ---------------------------------------------------------------------------


def _paper_file_re(paper_id: str) -> re.Pattern:
    pid = validate_paper_id(paper_id)
    version = "" if is_versioned_paper_id(pid) else r"v[1-9]\d*"
    # 生成器的文件名固定为 <id>-<slug>.md；`-` 作为分界，避免 v1 误匹配 v12。
    return re.compile(re.escape(pid) + version + r"-[^/\\]+\.md")


def find_paper_markdown(docs_dir: os.PathLike | str, date_token: str, paper_id: str) -> Path:
    """在 docs/<route_dir>/ 中找到该论文唯一的 Markdown，找不到或不唯一都报错。"""
    token = validate_date_token(date_token)
    pid = validate_paper_id(paper_id)
    day_dir = Path(docs_dir) / route_dir_for(token)
    if not day_dir.is_dir():
        raise DeepReadError(f"日报目录不存在：{day_dir}（paper_date={token}）。")
    pattern = _paper_file_re(pid)
    matches = sorted(
        p for p in day_dir.iterdir() if p.is_file() and pattern.fullmatch(p.name)
    )
    if not matches:
        version = "" if is_versioned_paper_id(pid) else r"(?:v[1-9]\d*)?"
        slugless = re.compile(re.escape(pid) + version + r"\.md")
        bare = sorted(p.name for p in day_dir.iterdir() if p.is_file() and slugless.fullmatch(p.name))
        if bare:
            # PR #1 之后的 long-range 回溯块（long_range_native）写的是 <id>.md、路由 <token>/<id>，
            # 而 6.generate_docs.py 单篇模式只会写 <id>-<slug>.md，会生成另一份文件。
            raise DeepReadError(
                f"{day_dir} 中的 {bare[0]} 没有标题 slug（long-range 回溯块的文件格式），"
                "单篇精读不支持这类日期块：生成器单篇模式只会写 <id>-<slug>.md，不会更新这份文件。"
            )
        raise DeepReadError(f"在 {day_dir} 中找不到论文 {pid} 的 Markdown。")
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise DeepReadError(
            f"论文 {pid} 在 {day_dir} 中匹配到多个 Markdown：{names}；请填写带版本号的 paper_id。"
        )
    return matches[0]


def parse_front_matter(md_text: str) -> Dict[str, str]:
    """极简 front matter 解析（只取标量字段），规则与 6.generate_docs._parse_front_matter 对齐。"""
    text = (md_text or "").lstrip()
    if not text.startswith("---"):
        return {}
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    meta: Dict[str, str] = {}
    for line in text[3:end].strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key, raw = key.strip(), raw.strip()
        if not key:
            continue
        if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
            raw = raw[1:-1]
        meta[key] = (
            raw.replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
        )
    return meta


@dataclass(frozen=True)
class PaperTarget:
    date_token: str
    route_dir: str
    paper_id: str  # 带版本号，取自已有文件名
    basename: str  # <paper_id>-<slug>
    slug: str
    md_path: Path
    title: str  # front matter 中的标题
    generator_title: str  # 传给 --paper-title，保证生成器算出的文件名就是 md_path

    @property
    def txt_path(self) -> Path:
        return self.md_path.with_suffix(".txt")

    @property
    def route(self) -> str:
        return f"{self.route_dir}/{self.basename}"

    @property
    def href(self) -> str:
        return f"#/{self.route}"

    def artifact_rel_paths(self) -> List[str]:
        """生成器可能写入的、属于这篇论文的路径（相对 docs 目录）。"""
        key = safe_asset_key(self.paper_id)
        return [
            f"{self.route}.md",
            f"{self.route}.txt",
            f"assets/figures/arxiv/{key}",
            f"assets/tables/arxiv/{key}",
        ]

    def protected_asset_rel_paths(self, md_text: str) -> List[str]:
        """原文 front matter 已引用的图表目录：升级时只读，生成器对它们的改动一律丢弃。

        生成器只要缺 figures_json/tables_json 任一项就会重跑 ensure_paper_media；而
        PaperCropper 只找到图、没找到表的论文没有 tables/meta.json，缓存不命中，workflow 里
        （PAPERCROPPER_DISABLE=1）会退回 PyMuPDF 位图提取，覆盖原来 PaperCropper 裁出的
        fig-NNN.webp / meta.json。front matter 里的 figures_json 不会被改写（已存在），
        页面会拿旧的尺寸描述去显示新图。所以：front matter 已有 figures_json → 图目录只读；
        已有 tables_json → 表目录只读。缺失的那一项仍允许生成器新增（此时它会同时写入
        对应的 *_json，文件与 front matter 保持一致）。
        """
        meta = parse_front_matter(md_text)
        key = safe_asset_key(self.paper_id)
        out: List[str] = []
        if str(meta.get("figures_json") or "").strip():
            out.append(f"assets/figures/arxiv/{key}")
        if str(meta.get("tables_json") or "").strip():
            out.append(f"assets/tables/arxiv/{key}")
        return out


def resolve_target(docs_dir: os.PathLike | str, date_token: str, paper_id: str) -> PaperTarget:
    token = validate_date_token(date_token)
    md_path = find_paper_markdown(docs_dir, token, paper_id)
    basename = md_path.name[: -len(".md")]
    match = re.match(r"(\d{4}\.\d{4,5}v[1-9]\d*)-(.+)$", basename)
    if not match:  # pragma: no cover - _paper_file_re 已保证
        raise DeepReadError(f"无法从文件名解析 arXiv 编号：{md_path.name}")
    versioned_id, slug = match.group(1), match.group(2)
    meta = parse_front_matter(md_path.read_text(encoding="utf-8"))
    source = str(meta.get("source") or "").strip().lower()
    if source and source != "arxiv":
        raise DeepReadError(
            f"{md_path.name} 的 source={source!r}；单篇精读只支持 arXiv 论文（生成器通过 arXiv API 取元数据）。"
        )
    title = str(meta.get("title") or "").strip()
    if title and slugify(title) == slug:
        generator_title = title
    else:
        # 生成器用 slugify(title) 拼文件名；slug 只含 [a-z0-9-]，slugify(slug) == slug，
        # 用它兜底可以保证写回同一个文件（标题只会在缺中文标题/速览时进入 LLM 提示词）。
        generator_title = slug
        warn(
            f"front matter 标题的 slug 与文件名不一致（{slugify(title)!r} != {slug!r}），"
            "改用文件名 slug 作为 --paper-title，保证写回原文件。"
        )
    if slugify(generator_title) != slug:
        raise DeepReadError(
            f"{md_path.name} 的文件名不是生成器 slugify 规则能复现的格式，单篇模式会写到另一个文件，已放弃。"
        )
    return PaperTarget(
        date_token=token,
        route_dir=route_dir_for(token),
        paper_id=versioned_id,
        basename=basename,
        slug=slug,
        md_path=md_path,
        title=title,
        generator_title=generator_title,
    )


# ---------------------------------------------------------------------------
# 精读总结检测
# ---------------------------------------------------------------------------

_DEEP_HEADING_LINE_RE = re.compile(
    r"^## " + re.escape(DEEP_SUMMARY_HEADING) + r"[ \t\r]*$", re.MULTILINE
)


def deep_block_tail(md_text: str) -> Optional[str]:
    """返回最后一个精读总结标题之后的内容（strip 后）；没有标题时返回 None。"""
    last = None
    for last in _DEEP_HEADING_LINE_RE.finditer(md_text or ""):
        pass
    if last is None:
        return None
    return (md_text or "")[last.end():].strip()


def has_deep_block(md_text: str) -> bool:
    return bool(deep_block_tail(md_text))


def deep_block_complete(md_text: str) -> bool:
    tail = deep_block_tail(md_text)
    return bool(tail) and DEEP_SUMMARY_END_MARKER in tail


# 6.generate_docs.upsert_glance_block_in_text 在 `## Abstract` 前插入的正文速览块：
#   f"{before.rstrip()}\n\n## 速览\n{glance}\n\n---\n\n{after}"
_INSERTED_GLANCE_RE = re.compile(r"\n\n## 速览\n.*?\n\n---\n\n(?=## Abstract)", re.S)
_FRONT_MATTER_GLANCE_KEYS = ("tldr", "motivation", "method", "result", "conclusion")


def strip_inserted_glance(base_text: str, new_text: str) -> Tuple[str, bool]:
    """去掉生成器（PR #1 合并前的 main）给已有文章新插入的正文 `## 速览` 块。

    现在的文章把速览放在 front matter（tldr/motivation/...），前端已渲染为速览卡片；
    main 上的 process_paper 只要正文里没有 `## 速览` 就会再插一份，页面上速览会出现两次。
    只在「原文没有正文速览 + front matter 已有速览字段 + 新文本恰好多出一个标准格式的速览块」
    时删除；其余情况原样返回。PR #1 之后生成器不再插入，这里自然是空操作。
    """
    if "## 速览" in (base_text or ""):
        return new_text, False
    meta = parse_front_matter(base_text)
    if not any(str(meta.get(key) or "").strip() for key in _FRONT_MATTER_GLANCE_KEYS):
        return new_text, False
    if new_text.count("## 速览") != 1:
        return new_text, False
    matches = list(_INSERTED_GLANCE_RE.finditer(new_text))
    if len(matches) != 1:
        return new_text, False
    match = matches[0]
    return new_text[: match.start()] + "\n\n" + new_text[match.end():], True


# ---------------------------------------------------------------------------
# 侧边栏：速读区 → 精读区
# ---------------------------------------------------------------------------


def _split_lines(text: str) -> List[str]:
    # 只按 "\n" 切分（保留 "\r"），不能用 str.splitlines：标题 JSON 里可能出现   等字符。
    return re.findall(r"[^\n]*\n|[^\n]+$", text)


def _strip_eol(line: str) -> str:
    if line.endswith("\n"):
        line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
    return line


def _eol_of(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _find_day_block(lines: Sequence[str], date_token: str) -> Optional[Tuple[int, int]]:
    """返回 (heading_idx, end_idx)；块内容为 lines[heading_idx + 1:end_idx]。"""
    marker = f"<!--dpr-date:{date_token}-->"
    legacy_heading = f"  * {format_date_label(date_token)}"
    daily_idx = next(
        (i for i, line in enumerate(lines) if DAILY_ROOT_RE.match(_strip_eol(line))), None
    )
    if daily_idx is None:
        return None
    heading_idx = None
    for i in range(daily_idx + 1, len(lines)):
        line = _strip_eol(lines[i])
        if line.startswith("* "):
            break
        if line.startswith("  * ") and not line.startswith("    "):
            if marker in line or line == legacy_heading:
                heading_idx = i
                break
    if heading_idx is None:
        return None
    end = heading_idx + 1
    while end < len(lines) and not BLOCK_END_RE.match(_strip_eol(lines[end])):
        end += 1
    return heading_idx, end


def _entry_href_re(route_dir: str, paper_id: str) -> re.Pattern:
    pid = validate_paper_id(paper_id)
    version = "" if is_versioned_paper_id(pid) else r"v[1-9]\d*"
    return re.compile(
        r'href="#/' + re.escape(route_dir) + "/" + re.escape(pid) + version + r'(?=[-"])'
    )


def _section_header(line: str) -> Optional[str]:
    text = _strip_eol(line)
    if DEEP_HEADER_RE.match(text):
        return "deep"
    if QUICK_HEADER_RE.match(text):
        return "quick"
    return None


def _href_of(line: str) -> str:
    match = re.search(r'href="([^"]*)"', line)
    return match.group(1) if match else ""


def _drop_empty_quick_header(block: List[str]) -> None:
    """速读区标题下已没有非空行时删除该标题（与 update_sidebar 只在非空时输出标题一致）。"""
    quick_idx = next((i for i, line in enumerate(block) if _section_header(line) == "quick"), None)
    if quick_idx is None:
        return
    quick_end = next(
        (i for i in range(quick_idx + 1, len(block)) if _section_header(block[i])), len(block)
    )
    if not any(block[i].strip() for i in range(quick_idx + 1, quick_end)):
        del block[quick_idx]


def promote_sidebar_entry(sidebar_text: str, date_token: str, paper_id: str) -> Tuple[str, str]:
    """把 <!--dpr-date:date_token--> 块中该论文的条目从 速读区 移到 精读区 末尾。

    返回 (new_text, status)，status ∈ {moved, already_deep, deduped, not_found}。
    - 只在该日期块内查找；同一论文出现在其他日期块时不受影响。
    - 条目行原样移动（字节不变）；精读区缺失时在 速读区 前新建 `    * 精读区`；
      速读区被移空时删除其标题行。其余内容（含 CRLF、结尾有无换行）逐字节保留。
    - 幂等：已在精读区时返回 already_deep 且文本不变。
    - 修复：同一 href 在精读区恰好 1 条、速读区还有残留副本时（同 token 日报重跑与本次
      推送交错、`rebase -X theirs` 留下的状态），删除速读区副本并返回 deduped。
      其他多次命中（例如裸编号同时命中 v1 与 v12）仍然报错。
    """
    token = validate_date_token(date_token)
    route_dir = route_dir_for(token)
    href_re = _entry_href_re(route_dir, paper_id)
    text = sidebar_text or ""
    lines = _split_lines(text)
    if not lines:
        return text, SIDEBAR_NOT_FOUND
    first_eol = next((_eol_of(line) for line in lines if _eol_of(line)), "\n")
    missing_final_eol = not _eol_of(lines[-1])
    if missing_final_eol:
        lines[-1] += first_eol

    found = _find_day_block(lines, token)
    if found is None:
        return text, SIDEBAR_NOT_FOUND
    heading_idx, end_idx = found
    block = list(lines[heading_idx + 1:end_idx])

    matches: List[Tuple[int, str]] = []
    section = "deep"  # 与 _extract_day_block_papers / 前端一致：无标题时默认精读区
    for i, line in enumerate(block):
        header = _section_header(line)
        if header:
            section = header
            continue
        if line.lstrip().startswith("*") and href_re.search(line):
            matches.append((i, section))
    if not matches:
        return text, SIDEBAR_NOT_FOUND

    def finish(new_block: List[str], status: str) -> Tuple[str, str]:
        new_text = "".join(lines[: heading_idx + 1] + new_block + lines[end_idx:])
        if missing_final_eol and new_text.endswith(first_eol):
            new_text = new_text[: -len(first_eol)]
        return new_text, status

    if len(matches) > 1:
        hrefs = {_href_of(block[i]) for i, _ in matches}
        deep_hits = [i for i, kind in matches if kind == "deep"]
        quick_hits = [i for i, kind in matches if kind == "quick"]
        if len(hrefs) == 1 and len(deep_hits) == 1 and quick_hits:
            for i in sorted(quick_hits, reverse=True):
                del block[i]
            _drop_empty_quick_header(block)
            return finish(block, SIDEBAR_DEDUPED)
        raise DeepReadError(
            f"侧边栏 {token} 块中论文 {paper_id} 出现了 {len(matches)} 次，无法确定要移动哪一条。"
        )
    entry_idx, entry_section = matches[0]
    if entry_section == "deep":
        return text, SIDEBAR_ALREADY_DEEP

    moved = block.pop(entry_idx)
    headers = [(i, _section_header(line)) for i, line in enumerate(block)]
    headers = [(i, kind) for i, kind in headers if kind]
    deep_idx = next((i for i, kind in headers if kind == "deep"), None)
    quick_idx = next((i for i, kind in headers if kind == "quick"), None)
    assert quick_idx is not None  # 条目在速读区，必然存在速读区标题

    if deep_idx is None:
        eol = _eol_of(block[quick_idx]) or first_eol
        block[quick_idx:quick_idx] = [f"    * {DEEP_SECTION}{eol}", moved]
    else:
        section_end = next((i for i, _ in headers if i > deep_idx), len(block))
        last = deep_idx
        for i in range(deep_idx + 1, section_end):
            if block[i].strip():
                last = i
        block.insert(last + 1, moved)
    _drop_empty_quick_header(block)
    return finish(block, SIDEBAR_MOVED)


def promote_daily_state(state_text: str, route: str, paper_id: str) -> Tuple[str, str]:
    """把 _daily_state.json 中该论文的 section 改为 deep。

    daily_report_state._merge_record 让 deep 具有粘性：同一 token 重跑日报时，
    update_sidebar(replace_existing=True) 会按这里的 section 重建日期块，
    不同步的话论文会被放回速读区。输出格式与 save_daily_state 相同（indent=2, ensure_ascii=False）。
    """
    try:
        data = json.loads(state_text)
    except json.JSONDecodeError as exc:
        raise DeepReadError(f"_daily_state.json 不是合法 JSON：{exc}") from None
    papers = data.get("papers") if isinstance(data, dict) else None
    if not isinstance(papers, list):
        raise DeepReadError("_daily_state.json 缺少 papers 列表。")
    records = [p for p in papers if isinstance(p, dict)]
    hits = [p for p in records if str(p.get("route") or "").strip() == route]
    if not hits:
        hits = [p for p in records if str(p.get("paper_id") or "").strip() == paper_id]
    if not hits:
        return state_text, SIDEBAR_NOT_FOUND
    if all(str(p.get("section") or "").strip().lower() == "deep" for p in hits):
        return state_text, SIDEBAR_ALREADY_DEEP
    for record in hits:
        record["section"] = "deep"
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n", SIDEBAR_MOVED


def promote_papers_meta(meta_text: str, route: str) -> Tuple[str, str]:
    """把 papers.meta.json（write_day_meta_index_json，paper_id 字段存的是 route）中该论文的 section 改为 deep。

    只有当文件能按生成器格式（indent=2, ensure_ascii=False, 结尾换行）逐字节复现时才改写，
    否则返回 skipped，避免把手工/旧格式文件整体重排。
    """
    try:
        data = json.loads(meta_text)
    except json.JSONDecodeError:
        return meta_text, SKIPPED
    if json.dumps(data, ensure_ascii=False, indent=2) + "\n" != meta_text:
        return meta_text, SKIPPED
    papers = data.get("papers") if isinstance(data, dict) else None
    if not isinstance(papers, list):
        return meta_text, SKIPPED
    hits = [p for p in papers if isinstance(p, dict) and str(p.get("paper_id") or "").strip() == route]
    if not hits:
        return meta_text, SIDEBAR_NOT_FOUND
    if all(str(p.get("section") or "").strip().lower() == "deep" for p in hits):
        return meta_text, SIDEBAR_ALREADY_DEEP
    for record in hits:
        record["section"] = "deep"
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n", SIDEBAR_MOVED


_REPORT_ITEM_RE = re.compile(r"^(\d+)\. ")
_REPORT_EMPTY_DEEP = "- 本次无精读推荐。"
_REPORT_EMPTY_QUICK = "- 本次无速读推荐。"


def _report_section(lines: Sequence[str], heading: str) -> Optional[Tuple[int, int]]:
    """返回 (heading_idx, end_idx)；节内容为 lines[heading_idx + 1:end_idx]。"""
    idx = next((i for i, line in enumerate(lines) if _strip_eol(line) == heading), None)
    if idx is None:
        return None
    end = idx + 1
    while end < len(lines):
        text = _strip_eol(lines[end])
        if text.startswith("## ") or text == "---":
            break
        end += 1
    return idx, end


def _renumber(line: str, number: int) -> str:
    return _REPORT_ITEM_RE.sub(f"{number}. ", line, count=1)


def promote_day_report(readme_text: str, route: str) -> Tuple[str, str]:
    """把日报 README（build_day_report_markdown 的格式）中该论文的列表项从「## 速读区」移到「## 精读区」末尾。

    纯文本操作：条目行除序号外字节不变，两节重新编号，同步更新头部「- 精读区：N / - 速读区：M」
    两行计数；「今日简报（AI）」段落是 LLM 生成的文字，不改。
    返回 (new_text, status)，status ∈ {moved, already_deep, deduped, not_found, skipped}。
    """
    text = readme_text or ""
    lines = _split_lines(text)
    if not lines:
        return text, SKIPPED
    first_eol = next((_eol_of(line) for line in lines if _eol_of(line)), "\n")
    missing_final_eol = not _eol_of(lines[-1])
    if missing_final_eol:
        lines[-1] += first_eol
    deep = _report_section(lines, "## 精读区")
    quick = _report_section(lines, "## 速读区")
    if deep is None or quick is None or not deep[1] <= quick[0]:
        return text, SKIPPED
    link = f"](/{route})"

    def items(start: int, end: int) -> List[int]:
        return [i for i in range(start + 1, end) if _REPORT_ITEM_RE.match(lines[i])]

    deep_hits = [i for i in items(*deep) if link in lines[i]]
    quick_hits = [i for i in items(*quick) if link in lines[i]]
    if not quick_hits:
        return text, (SIDEBAR_ALREADY_DEEP if deep_hits else SIDEBAR_NOT_FOUND)
    if len(quick_hits) > 1 or len(deep_hits) > 1:
        return text, SKIPPED

    moved = lines[quick_hits[0]]
    quick_body = [lines[i] for i in range(quick[0] + 1, quick[1]) if i != quick_hits[0]]
    deep_body = list(lines[deep[0] + 1:deep[1]])
    status = SIDEBAR_DEDUPED if deep_hits else SIDEBAR_MOVED
    if not deep_hits:
        deep_body = [line for line in deep_body if _strip_eol(line) != _REPORT_EMPTY_DEEP]
        positions = [i for i, line in enumerate(deep_body) if _REPORT_ITEM_RE.match(line)]
        insert_at = positions[-1] + 1 if positions else 0
        deep_body.insert(insert_at, moved)

    def renumber_all(body: List[str]) -> Tuple[List[str], int]:
        count = 0
        out = []
        for line in body:
            if _REPORT_ITEM_RE.match(line):
                count += 1
                line = _renumber(line, count)
            out.append(line)
        return out, count

    deep_body, deep_count = renumber_all(deep_body)
    quick_body, quick_count = renumber_all(quick_body)
    if quick_count == 0 and not any(_strip_eol(line) == _REPORT_EMPTY_QUICK for line in quick_body):
        quick_body.insert(0, _REPORT_EMPTY_QUICK + (_eol_of(moved) or first_eol))

    new_lines = (
        lines[: deep[0] + 1] + deep_body + lines[deep[1]: quick[0] + 1] + quick_body + lines[quick[1]:]
    )
    counts = {"- 精读区：": deep_count, "- 速读区：": quick_count}
    for i in range(deep[0]):
        stripped = _strip_eol(new_lines[i])
        for prefix in list(counts):
            if stripped.startswith(prefix) and stripped[len(prefix):].isdigit():
                new_lines[i] = f"{prefix}{counts.pop(prefix)}" + _eol_of(new_lines[i])
                break
    new_text = "".join(new_lines)
    if missing_final_eol and new_text.endswith(first_eol):
        new_text = new_text[: -len(first_eol)]
    return new_text, status


# ---------------------------------------------------------------------------
# 文件读写
# ---------------------------------------------------------------------------


def _read_text_exact(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _write_text_exact(path: Path, text: str) -> None:
    _write_bytes_atomic(path, text.encode("utf-8"))


def _iter_files(root: Path, rel: str) -> List[str]:
    base = root / rel
    if base.is_file():
        return [rel]
    if base.is_dir():
        return sorted(
            p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file()
        )
    return []


def snapshot_artifacts(docs_dir: Path, rel_paths: Sequence[str], dest: Path) -> List[str]:
    """把 rel_paths（文件或目录）复制到 dest，返回复制的文件列表（相对路径）。"""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    copied: List[str] = []
    for rel in rel_paths:
        for file_rel in _iter_files(docs_dir, rel):
            target = dest / file_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(docs_dir / file_rel, target)
            copied.append(file_rel)
    return copied


def _read_bytes_or_none(path: Path) -> Optional[bytes]:
    return path.read_bytes() if path.is_file() else None


def apply_artifacts(docs_dir: Path, stash: Path, target: PaperTarget) -> str:
    """把 stash/gen 中相对 stash/base 发生变化的文件写回 docs_dir（逐文件三方比较）。

    - 当前文件仍等于 base（没人动过）→ 写入生成结果；
    - 当前文件已等于生成结果 → 跳过；
    - 否则视为并发修改：若当前 Markdown 已有精读总结（例如同一篇被另一次运行升级），
      直接沿用当前版本（返回 superseded）；否则报错，绝不覆盖别人的改动。
    """
    base_root, gen_root = stash / "base", stash / "gen"
    if not gen_root.is_dir():
        raise DeepReadError(f"找不到生成产物目录：{gen_root}（generate 步骤是否成功？）")
    files = set()
    for root in (base_root, gen_root):
        if root.is_dir():
            files.update(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    plan: List[Tuple[str, bytes]] = []
    conflicts: List[str] = []
    for rel in sorted(files):
        base = _read_bytes_or_none(base_root / rel)
        gen = _read_bytes_or_none(gen_root / rel)
        cur = _read_bytes_or_none(docs_dir / rel)
        if gen is None or gen == base or cur == gen:
            continue
        if cur == base:
            plan.append((rel, gen))
        else:
            conflicts.append(rel)
    if conflicts:
        md_rel = f"{target.route}.md"
        cur_md = docs_dir / md_rel
        if cur_md.is_file() and has_deep_block(_read_text_exact(cur_md)):
            log(f"[INFO] 远端 {md_rel} 已包含精读总结（并发升级），沿用远端版本。")
            return "superseded"
        raise DeepReadError(
            "检测到并发修改，放弃覆盖：" + ", ".join(conflicts) + "；请稍后重新运行本 workflow。"
        )
    for rel, data in plan:
        _write_bytes_atomic(docs_dir / rel, data)
        log(f"[INFO] 写回 {rel}")
    return "applied" if plan else "unchanged"


# ---------------------------------------------------------------------------
# 生成器调用
# ---------------------------------------------------------------------------


def restore_protected_assets(docs_dir: Path, saved_root: Path, rel_dirs: Sequence[str]) -> List[str]:
    """把 rel_dirs 恢复成 saved_root 中保存的样子（删掉新增文件、还原被改写的文件）。

    返回发生变化并被还原的文件（相对 docs_dir）。saved_root 中不存在的目录视为「原本没有」。
    """
    restored: List[str] = []
    for rel in rel_dirs:
        saved = {f: (saved_root / f).read_bytes() for f in _iter_files(saved_root, rel)}
        current = set(_iter_files(docs_dir, rel))
        for f in sorted(current - set(saved)):
            (docs_dir / f).unlink()
            restored.append(f)
        for f, data in sorted(saved.items()):
            if _read_bytes_or_none(docs_dir / f) != data:
                _write_bytes_atomic(docs_dir / f, data)
                restored.append(f)
        target_dir = docs_dir / rel
        if target_dir.is_dir():
            # 自底向上删掉因还原而变空、原本不存在的子目录
            for sub in sorted((p for p in target_dir.rglob("*") if p.is_dir()), reverse=True):
                if not any(sub.iterdir()) and not (saved_root / sub.relative_to(docs_dir)).is_dir():
                    sub.rmdir()
            if not any(target_dir.iterdir()) and not (saved_root / rel).is_dir():
                target_dir.rmdir()
    return sorted(set(restored))


def _matching_markdowns(target: PaperTarget, docs_dir: Path) -> List[str]:
    day_dir = docs_dir / target.route_dir
    pattern = re.compile(re.escape(target.paper_id) + r"-[^/\\]+\.md")
    return sorted(p.name for p in day_dir.iterdir() if p.is_file() and pattern.fullmatch(p.name))


_ABSTRACT_RE = re.compile(r"^## Abstract[ \t]*\n(.*?)(?=^## |^---[ \t]*$|\Z)", re.S | re.M)


def local_arxiv_meta(md_text: str, paper_id: str) -> Optional[Dict[str, object]]:
    """从已有论文 Markdown 还原 6.generate_docs.fetch_arxiv_paper_meta 需要的元数据。

    GitHub Actions 的出口 IP 经常被 export.arxiv.org 限流（HTTP 429），而升级精读的论文
    Markdown 里已经保存了标题、作者、日期、PDF 链接和英文摘要。字段不全（或 PDF 链接与
    编号不符）时返回 None，由调用方回落到真实的 arXiv API。
    """
    meta = parse_front_matter(md_text)
    title = " ".join(str(meta.get("title") or "").split())
    pdf = str(meta.get("pdf") or "").strip()
    body = (md_text or "").replace("\r\n", "\n")
    match = _ABSTRACT_RE.search(body)
    abstract = " ".join(match.group(1).split()) if match else ""
    if not (title and abstract and pdf) or not pdf.rstrip("/").endswith(paper_id):
        return None
    authors = [a.strip() for a in str(meta.get("authors") or "").split(",") if a.strip()]
    published = re.sub(r"\D", "", str(meta.get("date") or ""))[:8]
    try:
        tags = json.loads(meta.get("tags") or "[]")
    except ValueError:
        tags = []
    llm_tags = [str(tag) for tag in tags if str(tag).strip()] if isinstance(tags, list) else []
    return {
        "id": paper_id,
        "title": title,
        "abstract": abstract,
        "published": published,
        "authors": authors,
        "link": pdf,
        "pdf_url": pdf,
        "llm_tags": llm_tags,
    }


def run_generator_with_local_meta(generator: Path, meta_md: Path, generator_args: Sequence[str]) -> int:
    """在本进程加载生成器，把 fetch_arxiv_paper_meta 换成「优先用已有 Markdown」，再调 main()。

    生成器源码不改（上游文件）；只有已有 Markdown 缺字段时才请求 arXiv API。
    """
    generator = Path(generator).resolve()
    md_text = _read_text_exact(Path(meta_md))
    sys.argv = [str(generator), *generator_args]
    if str(generator.parent) not in sys.path:
        sys.path.insert(0, str(generator.parent))
    spec = importlib.util.spec_from_file_location("dpr_generate_docs_single", generator)
    if spec is None or spec.loader is None:
        raise DeepReadError(f"无法加载生成器：{generator}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    real_fetch = getattr(module, "fetch_arxiv_paper_meta", None)
    if callable(real_fetch):
        def fetch_with_local_meta(arxiv_id: str):
            wanted = str(arxiv_id or "").strip().rsplit("/", 1)[-1]
            meta = local_arxiv_meta(md_text, wanted)
            if meta is not None:
                log(f"[INFO] 使用已有 Markdown 中的论文元数据（不请求 arXiv API）：{wanted}")
                return meta
            log("[WARN] 已有 Markdown 元数据不完整，改为请求 arXiv API。")
            return real_fetch(arxiv_id)

        module.fetch_arxiv_paper_meta = fetch_with_local_meta
    main_fn = getattr(module, "main", None)
    if callable(main_fn):
        main_fn()
    return 0


def build_generator_command(
    target: PaperTarget, docs_dir: Path, generator: Path = GENERATOR_SCRIPT
) -> List[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "run-generator",
        "--generator",
        str(generator),
        "--meta-md",
        str(target.md_path),
        "--",
        "--docs-dir",
        str(Path(docs_dir).resolve()),
        "--paper-id",
        target.paper_id,
        "--paper-section",
        "deep",
        "--paper-date",
        target.date_token,
        "--paper-title",
        target.generator_title,
    ]


def run_generator(cmd: Sequence[str]) -> Tuple[int, str]:
    """运行生成器，实时转发输出，同时收集输出用于判定失败标记。"""
    proc = subprocess.Popen(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT_DIR),
    )
    chunks: List[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        chunks.append(line)
    return proc.wait(), "".join(chunks)


def generate(
    docs_dir: Path,
    date_token: str,
    paper_id: str,
    stash: Optional[Path] = None,
    generator: Path = GENERATOR_SCRIPT,
) -> PaperTarget:
    target = resolve_target(docs_dir, date_token, paper_id)
    _require_sidebar_entry(docs_dir, target)
    rel_paths = target.artifact_rel_paths()
    if stash is not None:
        snapshot_artifacts(docs_dir, rel_paths, stash / "base")

    if has_deep_block(_read_text_exact(target.md_path)):
        log(f"[INFO] {target.md_path.name} 已包含精读总结，跳过生成器，只需移动侧边栏。")
    else:
        if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("SUMMARY_API_KEY")):
            raise DeepReadError("未配置 DEEPSEEK_API_KEY / SUMMARY_API_KEY，无法生成精读总结。")
        original_md = _read_text_exact(target.md_path)
        before = _matching_markdowns(target, docs_dir)
        cmd = build_generator_command(target, docs_dir, generator)
        protected = target.protected_asset_rel_paths(original_md)
        with tempfile.TemporaryDirectory(prefix="deep-read-assets-") as saved:
            saved_root = Path(saved)
            snapshot_artifacts(docs_dir, protected, saved_root)
            log("[INFO] 运行生成器：" + shlex.join(cmd[cmd.index("--") + 1 :]))
            try:
                code, output = run_generator(cmd)
            finally:
                restored = restore_protected_assets(docs_dir, saved_root, protected)
        if restored:
            log(
                "[INFO] front matter 已引用的图表目录保持原样，丢弃生成器的改动："
                + ", ".join(restored)
            )
        if code != 0:
            raise DeepReadError(f"生成器退出码 {code}。")
        if GENERATOR_ERROR_MARKER in output:
            raise DeepReadError("生成器报告单篇论文生成失败（见上方日志）。")
        after = _matching_markdowns(target, docs_dir)
        if after != before:
            raise DeepReadError(
                f"生成器改变了 {target.route_dir} 中该论文的 Markdown 集合：{before} -> {after}；"
                "预期只更新已有文件。"
            )
        md_text = _read_text_exact(target.md_path)
        if not has_deep_block(md_text):
            raise DeepReadError(
                f"生成器返回成功，但 {target.md_path.name} 中没有「## {DEEP_SUMMARY_HEADING}」内容"
                "（常见原因：LLM 调用失败或额度不足）。"
            )
        stripped, changed = strip_inserted_glance(original_md, md_text)
        if changed:
            _write_text_exact(target.md_path, stripped)
            log("[INFO] 已去掉生成器新插入的正文「## 速览」块（front matter 已有速览，避免页面重复）。")
        log(f"[OK] 精读总结已写入 {target.md_path.name}")
    if not deep_block_complete(_read_text_exact(target.md_path)):
        warn(f"{target.md_path.name} 的精读总结缺少「{DEEP_SUMMARY_END_MARKER}」结束标记，可能被截断。")
    if stash is not None:
        snapshot_artifacts(docs_dir, rel_paths, stash / "gen")
    return target


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _sidebar_path(docs_dir: Path) -> Path:
    return docs_dir / "_sidebar.md"


def _state_path(docs_dir: Path, target: PaperTarget) -> Path:
    return docs_dir / target.route_dir / "_daily_state.json"


def _require_sidebar_entry(docs_dir: Path, target: PaperTarget) -> str:
    sidebar = _sidebar_path(docs_dir)
    if not sidebar.is_file():
        raise DeepReadError(f"找不到侧边栏文件：{sidebar}")
    _, status = promote_sidebar_entry(_read_text_exact(sidebar), target.date_token, target.paper_id)
    if status == SIDEBAR_NOT_FOUND:
        raise DeepReadError(
            f"侧边栏 <!--dpr-date:{target.date_token}--> 块中找不到 {target.href}；"
            "请确认 paper_date 是论文所在的日期块。"
        )
    return status


def _day_readme_path(docs_dir: Path, target: PaperTarget) -> Path:
    return docs_dir / target.route_dir / "README.md"


def _papers_meta_path(docs_dir: Path, target: PaperTarget) -> Path:
    return docs_dir / target.route_dir / "papers.meta.json"


def _sync_optional_file(path: Path, transform, label: str) -> str:
    """对可选的日期目录文件做纯文本升级；文件不存在返回 absent。"""
    if not path.is_file():
        log(f"[INFO] {label}：absent")
        return "absent"
    old = _read_text_exact(path)
    new, status = transform(old)
    if new != old:
        _write_text_exact(path, new)
    log(f"[INFO] {label}：{status}")
    if status in (SIDEBAR_NOT_FOUND, SKIPPED):
        warn(f"{path.name} 未同步（{status}），保持原样。")
    return status


def promote(docs_dir: Path, date_token: str, paper_id: str) -> Tuple[str, str]:
    target = resolve_target(docs_dir, date_token, paper_id)
    sidebar = _sidebar_path(docs_dir)
    if not sidebar.is_file():
        raise DeepReadError(f"找不到侧边栏文件：{sidebar}")
    old = _read_text_exact(sidebar)
    new, sidebar_status = promote_sidebar_entry(old, target.date_token, target.paper_id)
    if sidebar_status == SIDEBAR_NOT_FOUND:
        raise DeepReadError(
            f"侧边栏 <!--dpr-date:{target.date_token}--> 块中找不到 {target.href}。"
        )
    if new != old:
        _write_text_exact(sidebar, new)
    log(f"[INFO] 侧边栏：{sidebar_status}（{target.href}）")

    state_path = _state_path(docs_dir, target)
    state_status = "absent"
    if state_path.is_file():
        old_state = _read_text_exact(state_path)
        new_state, state_status = promote_daily_state(old_state, target.route, target.paper_id)
        if new_state != old_state:
            _write_text_exact(state_path, new_state)
        if state_status == SIDEBAR_NOT_FOUND:
            warn(f"{state_path.name} 中没有 {target.route}，跳过同步。")
    log(f"[INFO] _daily_state.json：{state_status}")

    # 日报页（README.md）与下载索引（papers.meta.json）只做纯文本同步；首页 docs/README.md 不动。
    _sync_optional_file(
        _day_readme_path(docs_dir, target),
        lambda text: promote_day_report(text, target.route),
        "日报 README",
    )
    _sync_optional_file(
        _papers_meta_path(docs_dir, target),
        lambda text: promote_papers_meta(text, target.route),
        "papers.meta.json",
    )
    return sidebar_status, state_status


def commit_paths(docs_dir: Path, target: PaperTarget) -> List[str]:
    """需要提交的路径（存在的才输出），相对当前工作目录。"""
    candidates = [docs_dir / rel for rel in target.artifact_rel_paths()]
    candidates += [
        _sidebar_path(docs_dir),
        _state_path(docs_dir, target),
        _day_readme_path(docs_dir, target),
        _papers_meta_path(docs_dir, target),
    ]
    return [os.path.relpath(p) for p in candidates if p.exists()]


def _write_github_output(path: str, target: PaperTarget) -> None:
    values = {
        "paper_id": target.paper_id,
        "paper_date": target.date_token,
        "route": target.route,
    }
    for key, value in values.items():
        if not SAFE_OUTPUT_RE.fullmatch(value):  # pragma: no cover - 已由校验保证
            raise DeepReadError(f"输出值包含非法字符：{key}")
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _add_target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR), help="docs 目录（默认仓库 docs/）。")
    parser.add_argument("--paper-id", required=True, help="arXiv 编号，如 2609.03454v1。")
    parser.add_argument("--paper-date", required=True, help="日期目录 token：YYYYMMDD 或 YYYYMMDD-YYYYMMDD。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把速读区论文升级为精读（fork 专用）。")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("resolve", help="校验输入并定位论文 Markdown（不改文件）。")
    _add_target_args(p)
    p.add_argument("--github-output", default=None, help="把 paper_id/paper_date/route 追加到该文件。")

    p = sub.add_parser("generate", help="调用 6.generate_docs.py 单篇模式并校验结果。")
    _add_target_args(p)
    p.add_argument("--stash", default=None, help="保存 base/gen 快照的目录（供 apply 使用）。")
    p.add_argument("--generator", default=str(GENERATOR_SCRIPT), help=argparse.SUPPRESS)

    p = sub.add_parser("apply", help="把 generate 的产物三方比较后写回 docs。")
    _add_target_args(p)
    p.add_argument("--stash", required=True)

    p = sub.add_parser("promote", help="把侧边栏条目移到精读区并同步 _daily_state.json。")
    _add_target_args(p)

    p = sub.add_parser("paths", help="列出需要提交的路径。")
    _add_target_args(p)

    p = sub.add_parser("check", help="检查 Markdown 是否已有精读总结（有则 exit 0）。")
    _add_target_args(p)

    # 内部使用：由 generate 以子进程调用，参数在 -- 之后原样传给生成器。
    p = sub.add_parser("run-generator", help=argparse.SUPPRESS)
    p.add_argument("--generator", required=True)
    p.add_argument("--meta-md", required=True)
    p.add_argument("generator_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-generator":
        rest = list(args.generator_args)
        if rest and rest[0] == "--":
            rest = rest[1:]
        return run_generator_with_local_meta(Path(args.generator), Path(args.meta_md), rest)
    docs_dir = Path(args.docs_dir)
    try:
        if args.command == "resolve":
            target = resolve_target(docs_dir, args.paper_date, args.paper_id)
            sidebar_status = _require_sidebar_entry(docs_dir, target)
            md_text = _read_text_exact(target.md_path)
            info = {
                "paper_id": target.paper_id,
                "paper_date": target.date_token,
                "md_path": os.path.relpath(target.md_path),
                "generator_title": target.generator_title,
                "has_deep_block": has_deep_block(md_text),
                "sidebar": sidebar_status,
            }
            log("[INFO] 目标论文：" + json.dumps(info, ensure_ascii=False))
            if args.github_output:
                _write_github_output(args.github_output, target)
        elif args.command == "generate":
            generate(
                docs_dir,
                args.paper_date,
                args.paper_id,
                stash=Path(args.stash) if args.stash else None,
                generator=Path(args.generator),
            )
        elif args.command == "apply":
            target = resolve_target(docs_dir, args.paper_date, args.paper_id)
            status = apply_artifacts(docs_dir, Path(args.stash), target)
            log(f"[INFO] 产物写回：{status}")
        elif args.command == "promote":
            promote(docs_dir, args.paper_date, args.paper_id)
        elif args.command == "paths":
            target = resolve_target(docs_dir, args.paper_date, args.paper_id)
            for path in commit_paths(docs_dir, target):
                print(path)
        elif args.command == "check":
            target = resolve_target(docs_dir, args.paper_date, args.paper_id)
            md_text = _read_text_exact(target.md_path)
            complete = deep_block_complete(md_text)
            present = has_deep_block(md_text)
            log(f"[INFO] 精读总结：present={present} complete={complete}（{target.md_path.name}）")
            return 0 if present else 1
    except DeepReadError as exc:
        log(f"[ERROR] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
