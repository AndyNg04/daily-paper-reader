// 论文页「升级为精读」入口（fork 专用，独立文件以减少与上游同步冲突）。
// 只在当前论文位于日报日期块「速读区」时显示；数据来自 DPRSidebar 已解析的 docs/_sidebar.md，
// 触发走 DPRWorkflowRunner.runDeepReadPaper（GitHub Actions deep-read-paper.yml / 本地调试后端）。
window.DPRDeepReadEntry = (function () {
  const ROW_CLASS = 'dpr-deep-read-row';
  const submitted = new Set();
  let pending = false;

  const runner = () => window.DPRWorkflowRunner || null;
  const keyOf = (ctx) => `${ctx.paperDate}|${ctx.paperId}`;

  // 与其它危险/付费入口一致：访客与未解锁状态不开放；本地调试页由本地后端执行，不依赖密钥。
  const accessAllowed = () => {
    const r = runner();
    if (!r || typeof r.runDeepReadPaper !== 'function') return false;
    if (typeof r.isLocalDebugPage === 'function' && r.isLocalDebugPage()) return true;
    return String(window.DPR_ACCESS_MODE || '') === 'full';
  };

  const resolveContext = () => {
    const sidebar = window.DPRSidebar;
    if (!sidebar || typeof sidebar.getDailyPaperContext !== 'function') return null;
    const ctx = sidebar.getDailyPaperContext();
    return ctx && ctx.section === 'quick' ? ctx : null;
  };

  const buildConfirmText = (ctx, title, local) => [
    '确认把这篇论文升级为精读？',
    '',
    ...(title ? [`论文：${title}`] : []),
    `arXiv：${ctx.paperId}`,
    `日期块：${ctx.paperDate}`,
    '',
    local
      ? '本地调试模式：本地后端会运行 deep_read_paper.py generate + promote，调用 DeepSeek 生成精读长总结（产生 API 费用），把侧边栏条目移到精读区，直接改写本地 docs/（不提交 git）。'
      : '将触发 GitHub Actions「deep-read-paper」：调用 DeepSeek 生成精读长总结（产生 API 费用），把侧边栏条目从速读区移到精读区，并直接提交推送到仓库默认分支；Pages 重新部署后生效，通常需要几分钟。',
  ].join('\n');

  const applyButtonState = (btn, ctx) => {
    const done = submitted.has(keyOf(ctx));
    btn.disabled = pending || done;
    btn.textContent = done ? '已提交精读任务' : pending ? '提交中…' : '升级为精读';
    btn.title = done ? '任务已提交，可在工作流面板查看进度；完成并重新部署后刷新页面。' : '生成精读长总结并移到精读区';
  };

  const refreshButtons = () => {
    document.querySelectorAll(`.${ROW_CLASS} [data-dpr-deep-read]`).forEach((btn) => {
      applyButtonState(btn, { paperId: btn.getAttribute('data-paper-id'), paperDate: btn.getAttribute('data-paper-date') });
    });
  };

  const onClick = async (ctx) => {
    if (pending || submitted.has(keyOf(ctx))) return;
    pending = true;
    refreshButtons();
    try {
      const r = runner();
      const titleEl = document.querySelector('.paper-title-row .paper-title-en');
      const title = titleEl ? String(titleEl.textContent || '').trim() : '';
      const local = !!(r && typeof r.isLocalDebugPage === 'function' && r.isLocalDebugPage());
      if (!r || !window.confirm(buildConfirmText(ctx, title, local))) return;
      const accepted = await r.runDeepReadPaper({ paperId: ctx.paperId, paperDate: ctx.paperDate });
      if (accepted === true) submitted.add(keyOf(ctx));
    } catch (error) {
      console.error('[DPR DeepRead] 触发失败:', error);
    } finally {
      pending = false;
      refreshButtons();
    }
  };

  const render = () => {
    const ctx = accessAllowed() ? resolveContext() : null;
    const metaRight = document.querySelector('.markdown-section .paper-meta-right');
    document.querySelectorAll(`.${ROW_CLASS}`).forEach((row) => {
      if (!ctx || row.parentNode !== metaRight || row.getAttribute('data-href') !== ctx.href) row.remove();
    });
    if (!ctx || !metaRight || metaRight.querySelector(`.${ROW_CLASS}`)) return;
    const row = document.createElement('p');
    row.className = `paper-meta-link-row paper-meta-pdf-row ${ROW_CLASS}`;
    row.setAttribute('data-href', ctx.href);
    row.innerHTML = '<span class="paper-meta-link-label"><strong>精读</strong>:</span> ';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'dpr-deep-read-btn';
    btn.setAttribute('data-dpr-deep-read', '1');
    btn.setAttribute('data-paper-id', ctx.paperId);
    btn.setAttribute('data-paper-date', ctx.paperDate);
    btn.addEventListener('click', () => onClick(ctx));
    applyButtonState(btn, ctx);
    row.appendChild(btn);
    metaRight.appendChild(row);
  };

  const ensureStyle = () => {
    if (document.getElementById('dpr-deep-read-style')) return;
    const style = document.createElement('style');
    style.id = 'dpr-deep-read-style';
    style.textContent = `
      .dpr-deep-read-btn { flex: 0 0 auto; min-height: 30px; border: 1px solid rgba(39, 174, 96, 0.3); border-radius: 999px;
        background: #f1fbf5; color: #1e8449; cursor: pointer; font-size: 12px; font-weight: 600; line-height: 1.2; padding: 5px 10px; }
      .dpr-deep-read-btn:hover:not(:disabled) { background: #e3f6ea; border-color: rgba(39, 174, 96, 0.45); }
      .dpr-deep-read-btn:disabled { cursor: default; opacity: 0.65; }
    `;
    document.head.appendChild(style);
  };

  const schedule = () => setTimeout(render, 0);
  const init = () => {
    ensureStyle();
    ['dpr-docsify-ready', 'dpr-sidebar-updated', 'dpr-access-mode-changed'].forEach((name) => {
      document.addEventListener(name, schedule);
    });
    schedule();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  return { render, __test: { buildConfirmText, resolveContext, accessAllowed, onClick, submitted } };
})();
