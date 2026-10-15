<div class="dpr-home-notice-card dpr-home-panel">
  <div class="dpr-home-notice-header dpr-home-panel-header">
    <h3 class="dpr-home-notice-title">公告与更新</h3>
    <a class="dpr-home-notice-tutorial" href="#/tutorial/README">使用教程 <span aria-hidden="true">›</span></a>
  </div>
  <div class="dpr-home-notice-entry">
    <time class="dpr-home-notice-date" datetime="2026-10-05">10.05</time>
    <div>
      <strong class="dpr-home-notice-entry-title">medRxiv 自动更新已恢复</strong>
      <span class="dpr-home-notice-entry-summary">修复超长摘要导致的向量生成失败，维护任务现会限制单条 embedding 文本长度并分片写入。受影响范围已重新同步，公开读取、关键词检索与语义检索均已验证。</span>
    </div>
  </div>
  <div class="dpr-home-notice-entry">
    <time class="dpr-home-notice-date" datetime="2026-09-16">09.16</time>
    <div>
      <strong class="dpr-home-notice-entry-title">日报跨日重复推荐已修复</strong>
      <span class="dpr-home-notice-entry-summary">历史推荐现按原始召回标签与 arXiv 论文标识去重，暂停词条不再参与评分；同一专题次日不会重复推荐相同论文。已有历史页面保留，不自动删除。</span>
    </div>
  </div>
  <div class="dpr-home-notice-entry">
    <time class="dpr-home-notice-date" datetime="2026-09-09">09.09</time>
    <div>
      <strong class="dpr-home-notice-entry-title">90天/365天 arXiv 专题回溯</strong>
      <span class="dpr-home-notice-entry-summary">支持分片召回、断点评审与分页查看，核心论文与待复核结果分开展示。DeepSeek 费用按实际用量计算，不下载全量 PDF。</span>
    </div>
  </div>
  <div class="dpr-home-site-stats" data-dpr-site-stats hidden aria-live="polite">
    <span>今天有 <strong class="dpr-home-site-stat-value" data-dpr-daily-readers>--</strong> 人在看论文</span>
    <span class="dpr-home-site-stat-separator" aria-hidden="true">·</span>
    <span>昨天有 <strong class="dpr-home-site-stat-value" data-dpr-yesterday-readers>--</strong> 人在看论文</span>
    <span class="dpr-home-site-stat-separator" aria-hidden="true">·</span>
    <span>已有 <strong class="dpr-home-site-stat-value" data-dpr-fork-count>--</strong> 人加入 Daily Paper Reader</span>
    <span class="dpr-home-history">
      <button type="button" class="dpr-home-history-trigger" data-dpr-history-trigger aria-label="查看最近 14 天阅读趋势"><span aria-hidden="true">🔍</span></button>
      <span class="dpr-home-history-popover" data-dpr-history-popover role="tooltip">
        <span class="dpr-home-history-header">近 14 天阅读趋势</span>
        <span class="dpr-home-history-meta">
          <span data-dpr-history-range>--</span>
          <span>峰值 <strong data-dpr-history-peak>--</strong></span>
        </span>
        <span class="dpr-home-history-chart" data-dpr-history-chart></span>
      </span>
    </span>
  </div>
</div>

<div class="dpr-home-dashboard-grid">
<section class="dpr-home-dashboard-card dpr-home-report-card">
  <div class="dpr-home-dashboard-header">
    <div>
      <span class="dpr-home-dashboard-kicker">2026-10-15</span>
      <h3 class="dpr-home-dashboard-title">今日汇总</h3>
    </div>
    <strong class="dpr-home-dashboard-count">共 35 篇</strong>
  </div>
  <dl class="dpr-home-dashboard-stats">
    <div class="dpr-home-dashboard-stat"><dt>累计更新</dt><dd>1 次</dd></div>
    <div class="dpr-home-dashboard-stat"><dt>精读</dt><dd>15</dd></div>
    <div class="dpr-home-dashboard-stat"><dt>速读</dt><dd>20</dd></div>
  </dl>
  <p class="dpr-home-dashboard-body">最近更新：2026-10-15 18:25:51 UTC<br>状态：成功</p>
</section>
<section class="dpr-home-dashboard-card dpr-home-brief-card">
  <div class="dpr-home-dashboard-header">
    <div>
      <span class="dpr-home-dashboard-kicker">合并后生成</span>
      <h3 class="dpr-home-dashboard-title">今日简报</h3>
    </div>
    <strong class="dpr-home-dashboard-count">AI</strong>
  </div>
  <div class="dpr-home-dashboard-body">
<p>2026-10-15 论文日报已更新：共推荐 35 篇，分为精读 15 篇、速读 20 篇，聚焦 AI 在真实场景中的应用与治理。</p>
<p>最值得关注的是两篇获评 9.0/10 的精读：以本体支撑 GraphRAG 的临床自杀风险评估，以及通过注视唤起、可见状态支持同场协作的 AR 助手。</p>
<p>普通读者可先从 8.0/10 的《Who Can Say No?》入手，了解前沿 AI 的控制与问责议题，再按兴趣深入医疗或 AR 方向。</p>
  </div>
</section>
<section class="dpr-home-dashboard-card dpr-home-deep-card">
  <div class="dpr-home-dashboard-header">
    <div>
      <span class="dpr-home-dashboard-kicker">今日累计</span>
      <h3 class="dpr-home-dashboard-title">精读推荐</h3>
    </div>
    <strong class="dpr-home-dashboard-count">15 篇</strong>
  </div>
  <div class="dpr-home-dashboard-body">
<ul class="dpr-home-dashboard-paper-list"><li><span class="dpr-home-dashboard-paper-title" title="BEACON-SP: Ontology-Grounded GraphRAG Framework for Clinical Suicide Risk Assessment">BEACON-SP: Ontology-Grounded GraphRAG Framework for Clinical Suicide Risk Assessment</span></li><li><span class="dpr-home-dashboard-paper-title" title="Beyond Activation: Gaze Invocation with Visible Status for an Embodied AR Assistant in Co-Located Collaboration">Beyond Activation: Gaze Invocation with Visible Status for an Embodied AR Assistant in Co-Located Collaboration</span></li><li><span class="dpr-home-dashboard-paper-title" title="Terrarium: Growing Personal Assistants via Scalable Synthesis of App Worlds">Terrarium: Growing Personal Assistants via Scalable Synthesis of App Worlds</span></li></ul>
  </div>
  <div class="dpr-home-dashboard-tags"><span class="dpr-home-dashboard-tag">human-ai <strong>5</strong></span><span class="dpr-home-dashboard-tag">personal-agent <strong>5</strong></span><span class="dpr-home-dashboard-tag">ai-hci-mh <strong>3</strong></span><span class="dpr-home-dashboard-tag">interaction <strong>1</strong></span><span class="dpr-home-dashboard-tag">social-rl <strong>1</strong></span></div>
</section>
<section class="dpr-home-dashboard-card dpr-home-skim-card">
  <div class="dpr-home-dashboard-header">
    <div>
      <span class="dpr-home-dashboard-kicker">今日累计</span>
      <h3 class="dpr-home-dashboard-title">速读推荐</h3>
    </div>
    <strong class="dpr-home-dashboard-count">20 篇</strong>
  </div>
  <div class="dpr-home-dashboard-body">
<ul class="dpr-home-dashboard-paper-list"><li><span class="dpr-home-dashboard-paper-title" title="Structured pre-generation elicitation versus single-shot prompting in AI-assisted enterprise decision-making: a randomised online experiment">Structured pre-generation elicitation versus single-shot prompting in AI-assisted enterprise decision-making: a randomised online experiment</span></li><li><span class="dpr-home-dashboard-paper-title" title="Who Can Say No? Control, Accountability and the Pace of Frontier AI">Who Can Say No? Control, Accountability and the Pace of Frontier AI</span></li><li><span class="dpr-home-dashboard-paper-title" title="Collective Autonomous Vehicle Routing Needs Social Awareness for Coexistence with Human Drivers">Collective Autonomous Vehicle Routing Needs Social Awareness for Coexistence with Human Drivers</span></li></ul>
  </div>
  <div class="dpr-home-dashboard-tags"><span class="dpr-home-dashboard-tag">human-ai <strong>6</strong></span><span class="dpr-home-dashboard-tag">personal-agent <strong>6</strong></span><span class="dpr-home-dashboard-tag">ai-hci-mh <strong>3</strong></span><span class="dpr-home-dashboard-tag">social-rl <strong>3</strong></span><span class="dpr-home-dashboard-tag">ai-social-psych <strong>1</strong></span><span class="dpr-home-dashboard-tag">interaction <strong>1</strong></span></div>
</section>
</div>

<div class="dpr-home-promo-card dpr-home-panel">
  <div class="dpr-home-panel-header">
    <h3 class="dpr-home-promo-title">社区与支持</h3>
  </div>
  <p class="dpr-home-promo-copy">欢迎通过 Star、Fork、Issue 或 PR 一起完善 Daily Paper Reader。</p>
  <div class="dpr-home-promo-meta">
    <span>QQ群 <strong>583867967</strong></span>
    <span class="dpr-home-promo-separator" aria-hidden="true">·</span>
    <span>已有 <strong>1,491</strong> 人参与交流</span>
  </div>
</div>
