const assert = require('node:assert/strict');

// ---------- 最小 DOM 桩 ----------
function makeElement(tag) {
  const el = {
    tagName: String(tag || '').toUpperCase(),
    attrs: {},
    children: [],
    parentNode: null,
    listeners: {},
    style: {},
    className: '',
    textContent: '',
    innerHTML: '',
    disabled: false,
    classList: { add() {}, remove() {}, toggle() {} },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; },
    appendChild(child) { child.parentNode = this; this.children.push(child); return child; },
    remove() {
      if (!this.parentNode) return;
      this.parentNode.children = this.parentNode.children.filter((c) => c !== this);
      this.parentNode = null;
    },
    addEventListener(name, fn) { (this.listeners[name] = this.listeners[name] || []).push(fn); },
    click() { (this.listeners.click || []).forEach((fn) => fn()); },
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; },
    querySelectorAll(sel) {
      const out = [];
      const walk = (node) => node.children.forEach((c) => { if (matches(c, sel)) out.push(c); walk(c); });
      walk(this);
      return out;
    },
  };
  return el;
}
function matches(el, sel) {
  const last = sel.trim().split(/\s+/).pop();
  if (last.startsWith('.')) return String(el.className).split(/\s+/).includes(last.slice(1));
  if (last.startsWith('[')) return el.getAttribute(last.slice(1, -1)) !== null;
  return false;
}

function setup({ hostname = 'andyng04.github.io', mode = 'full', context = null, withMeta = true, pageId = '2609.03454v1' } = {}) {
  const root = makeElement('body');
  const metaRight = makeElement('div');
  metaRight.className = 'paper-meta-right';
  // 正文区（.markdown-section）当前渲染的是哪篇论文：用 PDF 链接里的 arXiv 编号表示。
  const section = { innerHTML: `<a href="https://arxiv.org/pdf/${pageId}">PDF</a>` };
  metaRight.closest = (sel) => (sel === '.markdown-section' ? section : null);
  if (withMeta) root.appendChild(metaRight);
  const docListeners = {};
  const byId = {};
  global.window = {
    location: { hostname, href: `https://${hostname}/daily-paper-reader/#/x`, protocol: 'https:' },
    localStorage: { getItem: () => null, setItem() {} },
    DPR_ACCESS_MODE: mode,
    DPRSidebar: { getDailyPaperContext: () => context },
  };
  global.requestAnimationFrame = (fn) => fn();
  global.document = {
    readyState: 'complete',
    head: makeElement('head'),
    body: root,
    createElement: makeElement,
    getElementById: (id) => byId[id] || null,
    addEventListener(name, fn) { (docListeners[name] = docListeners[name] || []).push(fn); },
    querySelector: (sel) => (sel.endsWith('.paper-meta-right') ? (withMeta ? metaRight : null) : root.querySelector(sel)),
    querySelectorAll: (sel) => root.querySelectorAll(sel),
  };
  for (const id of ['dpr-workflow-overlay', 'dpr-workflow-panel', 'dpr-workflow-status', 'dpr-workflow-runs', 'dpr-workflow-recent']) {
    byId[id] = makeElement('div');
  }
  global.fetch = () => { throw new Error('unexpected fetch'); };
  delete require.cache[require.resolve('../app/workflows.runner.js')];
  delete require.cache[require.resolve('../app/deep-read.entry.js')];
  require('../app/workflows.runner.js');
  return { metaRight, docListeners, byId, section };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 5));

(async () => {
  // ---------- runner：输入校验与构造 ----------
  setup();
  const runner = window.DPRWorkflowRunner;
  const build = runner.__test.buildDeepReadRequest;
  assert.deepEqual(build({ paperId: ' 2609.03454v1 ', paperDate: '20260828-20260926' }), {
    key: 'deep-read-paper', inputs: { paper_id: '2609.03454v1', paper_date: '20260828-20260926' },
  });
  assert.deepEqual(build({ paperId: '2609.12345v12', paperDate: '20260926' }).inputs, { paper_id: '2609.12345v12', paper_date: '20260926' });
  const badInputs = [
    { paperId: '2609.03454', paperDate: '20260926' },
    { paperId: '2609.03454v0', paperDate: '20260926' },
    { paperId: '2609.123v1', paperDate: '20260926' },
    { paperId: '2609.03454v1 x', paperDate: '20260926' },
    { paperId: '2609.03454v1', paperDate: '2026-09-26' },
    { paperId: '2609.03454v1', paperDate: '20260926-' },
    { paperId: '2609.03454v1', paperDate: '20260926-2026092' },
    { paperId: '2609.03454v1', paperDate: '' },
    {},
  ];
  for (const bad of badInputs) assert.throws(() => build(bad), undefined, JSON.stringify(bad));
  assert.throws(() => build());

  // 非法输入：不发任何请求，只在面板报错。
  let env = setup();
  assert.equal(await window.DPRWorkflowRunner.runDeepReadPaper({ paperId: '2609.03454', paperDate: '20260926' }), false);
  assert.match(env.byId['dpr-workflow-status'].textContent, /带版本号/);

  // GitHub Pages 上没有 Token：与其它 runner 入口一样在面板提示，不触发 dispatch。
  env = setup({ hostname: 'andyng04.github.io' });
  assert.equal(await window.DPRWorkflowRunner.runDeepReadPaper({ paperId: '2609.03454v1', paperDate: '20260828-20260926' }), false);
  assert.match(env.byId['dpr-workflow-status'].textContent, /未检测到 GitHub Token/);

  // 本地调试页：POST 到本地后端，workflowKey/workflowFile/inputs 与后端映射一致。
  env = setup({ hostname: 'localhost' });
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url, init });
    if (String(url).endsWith('/api/local/workflows/dispatch')) {
      return { ok: true, status: 200, json: async () => ({ ok: true, run: { id: 'r1', run_number: 1, status: 'queued' } }) };
    }
    return { ok: true, status: 200, json: async () => ({ ok: true, run: { id: 'r1', status: 'completed', conclusion: 'success', command: [] }, log: '' }) };
  };
  const origSetInterval = global.setInterval;
  global.setInterval = () => 0;
  try {
    assert.equal(await window.DPRWorkflowRunner.runDeepReadPaper({ paperId: '2609.03454v1', paperDate: '20260828-20260926' }), true);
  } finally {
    global.setInterval = origSetInterval;
  }
  assert.equal(calls[0].url, 'https://localhost:8567/api/local/workflows/dispatch');
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.workflowKey, 'deep-read-paper');
  assert.equal(body.workflowFile, 'deep-read-paper.yml');
  assert.deepEqual(body.inputs, { paper_id: '2609.03454v1', paper_date: '20260828-20260926' });

  // ---------- 论文页入口 ----------
  const quick = { paperId: '2609.03454v1', paperDate: '20260828-20260926', section: 'quick', href: '#/20260828-20260926/2609.03454v1-x' };
  const loadEntry = () => { require('../app/deep-read.entry.js'); return window.DPRDeepReadEntry; };

  env = setup({ context: quick });
  loadEntry();
  await flush();
  let rows = env.metaRight.querySelectorAll('.dpr-deep-read-row');
  assert.equal(rows.length, 1, '速读区论文显示入口');
  let btn = rows[0].querySelector('[data-dpr-deep-read]');
  assert.equal(btn.textContent, '升级为精读');
  assert.equal(btn.getAttribute('data-paper-id'), '2609.03454v1');
  assert.equal(btn.getAttribute('data-paper-date'), '20260828-20260926');
  window.DPRDeepReadEntry.render();
  assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 1, '重复渲染不重复插入');

  // 精读区 / 非日报论文 / 访客模式 / 非论文页：都不显示。
  for (const opts of [
    { context: { ...quick, section: 'deep' } },
    { context: null },
    { context: quick, mode: 'guest' },
    { context: quick, mode: 'locked' },
  ]) {
    env = setup(opts);
    loadEntry();
    await flush();
    assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 0, JSON.stringify(opts));
  }
  env = setup({ context: quick, withMeta: false });
  loadEntry();
  await flush();
  assert.equal(document.querySelectorAll('.dpr-deep-read-row').length, 0);
  // 本地调试页不依赖解锁状态（由本地后端执行）。
  env = setup({ context: quick, mode: 'guest', hostname: '127.0.0.1' });
  loadEntry();
  await flush();
  assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 1);

  // 路由切到精读区论文后，已插入的入口被移除。
  env = setup({ context: quick });
  loadEntry();
  await flush();
  window.DPRSidebar.getDailyPaperContext = () => ({ ...quick, section: 'deep' });
  env.docListeners['dpr-sidebar-updated'].forEach((fn) => fn());
  await flush();
  assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 0);

  // 路由已切到新论文、正文仍是上一篇（侧栏先广播更新）：不把新论文的入口挂到旧正文上。
  env = setup({ context: quick, pageId: '2609.11111v1' });
  loadEntry();
  await flush();
  assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 0, '正文不属于当前论文时不显示');
  env.section.innerHTML = '<a href="https://arxiv.org/pdf/2609.03454v1">PDF</a>';
  env.docListeners['dpr-docsify-ready'].forEach((fn) => fn());
  await flush();
  assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 1, '正文渲染完成后显示');

  // 点击时路由已变：不弹确认、不触发，并移除旧按钮。
  env = setup({ context: quick });
  let staleDispatched = 0;
  window.DPRWorkflowRunner.runDeepReadPaper = async () => { staleDispatched += 1; return true; };
  window.confirm = () => { throw new Error('should not confirm'); };
  loadEntry();
  await flush();
  const staleBtn = env.metaRight.querySelector('[data-dpr-deep-read]');
  window.DPRSidebar.getDailyPaperContext = () => ({ ...quick, paperId: '2609.22222v1', href: '#/20260828-20260926/2609.22222v1-y' });
  staleBtn.click();
  await flush();
  assert.equal(staleDispatched, 0);
  assert.equal(env.metaRight.querySelectorAll('.dpr-deep-read-row').length, 0);

  // 取消确认：不触发。
  env = setup({ context: quick });
  let dispatched = [];
  window.DPRWorkflowRunner.runDeepReadPaper = async (opts) => { dispatched.push(opts); return true; };
  let confirmText = '';
  window.confirm = (text) => { confirmText = text; return false; };
  loadEntry();
  await flush();
  btn = env.metaRight.querySelector('[data-dpr-deep-read]');
  btn.click();
  await flush();
  assert.equal(dispatched.length, 0);
  assert.match(confirmText, /2609\.03454v1/);
  assert.match(confirmText, /20260828-20260926/);
  assert.match(confirmText, /DeepSeek/);
  assert.match(confirmText, /推送/);
  assert.equal(btn.disabled, false);
  assert.equal(btn.textContent, '升级为精读');

  // 确认后只触发一次，连点被忽略；成功后按钮锁定。
  let resolveDispatch;
  window.confirm = () => true;
  window.DPRWorkflowRunner.runDeepReadPaper = (opts) => { dispatched.push(opts); return new Promise((r) => { resolveDispatch = r; }); };
  btn.click();
  btn.click();
  assert.equal(btn.disabled, true);
  assert.equal(btn.textContent, '提交中…');
  btn.click();
  await flush();
  assert.equal(dispatched.length, 1);
  assert.deepEqual(dispatched[0], { paperId: '2609.03454v1', paperDate: '20260828-20260926' });
  resolveDispatch(true);
  await flush();
  assert.equal(btn.disabled, true);
  assert.equal(btn.textContent, '已提交精读任务');
  btn.click();
  await flush();
  assert.equal(dispatched.length, 1, '已提交的论文不再重复触发');
  window.DPRDeepReadEntry.render();
  assert.equal(env.metaRight.querySelector('[data-dpr-deep-read]').textContent, '已提交精读任务');

  // runner 返回 false（例如没有 Token）：按钮恢复可点。
  env = setup({ context: quick });
  window.confirm = () => true;
  window.DPRWorkflowRunner.runDeepReadPaper = async () => false;
  loadEntry();
  await flush();
  btn = env.metaRight.querySelector('[data-dpr-deep-read]');
  btn.click();
  await flush();
  assert.equal(btn.disabled, false);
  assert.equal(btn.textContent, '升级为精读');

  console.log('deep read entry tests passed');

  // ---------- GitHub 模式运行中检查 ----------
  assert.equal(
    window.DPRWorkflowRunner.__test.deepReadRunTitle({ paper_id: '2609.03454v1', paper_date: '20260828-20260926' }),
    'deep read 2609.03454v1 (20260828-20260926)',
  );
  const runGuardScenario = async ({ deepRuns = [], dailyRuns = [] }) => {
    const genv = setup({ hostname: 'andyng04.github.io' });
    window.location.pathname = '/daily-paper-reader/';
    window.localStorage = { getItem: (k) => (k === 'github_token_data' ? JSON.stringify({ token: 'ghp_TEST' }) : null), setItem() {} };
    const origInterval = global.setInterval;
    global.setInterval = () => 0;
    const urls = [];
    global.fetch = async (url, init) => {
      const u = String(url);
      urls.push(((init && init.method) || 'GET') + ' ' + u);
      const j = (o) => ({ ok: true, status: 200, json: async () => o, text: async () => JSON.stringify(o) });
      if (/\/repos\/AndyNg04\/daily-paper-reader$/i.test(u)) return j({ fork: true, default_branch: 'main' });
      if (/deep-read-paper\.yml\/runs\?per_page=5/.test(u)) return j({ workflow_runs: deepRuns });
      if (/daily-paper-reader\.yml\/runs\?per_page=5/.test(u)) return j({ workflow_runs: dailyRuns });
      if (/dispatches$/.test(u)) return { ok: true, status: 204, json: async () => ({}), text: async () => '' };
      if (/runs\?event=workflow_dispatch/.test(u)) return j({ workflow_runs: [{ id: 42, run_number: 5, created_at: new Date(Date.now() + 1000).toISOString(), status: 'queued' }] });
      if (/actions\/runs\/42/.test(u)) return j({ id: 42, status: 'queued', jobs: [] });
      return j({ workflow_runs: [] });
    };
    try {
      await window.DPRWorkflowRunner.runDeepReadPaper({ paperId: '2609.03454v1', paperDate: '20260828-20260926' });
    } finally {
      global.setInterval = origInterval;
    }
    return { dispatched: urls.some((u) => /^POST .*deep-read-paper\.yml\/dispatches$/.test(u)), status: genv.byId['dpr-workflow-status'].textContent };
  };
  let g = await runGuardScenario({});
  assert.equal(g.dispatched, true, '空闲时派发');
  g = await runGuardScenario({ deepRuns: [{ id: 9, status: 'in_progress', display_title: 'deep read 2609.99999v1 (20260926)' }] });
  assert.equal(g.dispatched, true, '其它论文的精读任务不拦截');
  g = await runGuardScenario({ deepRuns: [{ id: 9, status: 'queued', display_title: 'deep read 2609.03454v1 (20260828-20260926)' }] });
  assert.equal(g.dispatched, false, '同一篇正在运行时拦截');
  g = await runGuardScenario({ dailyRuns: [{ id: 7, run_number: 2, status: 'in_progress' }] });
  assert.equal(g.dispatched, false, '日报运行中拦截');
  assert.match(g.status, /日报工作流正在运行/);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
