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
      <span class="dpr-home-dashboard-kicker">2026-11-01</span>
      <h3 class="dpr-home-dashboard-title">今日汇总</h3>
    </div>
    <strong class="dpr-home-dashboard-count">共 25 篇</strong>
  </div>
  <dl class="dpr-home-dashboard-stats">
    <div class="dpr-home-dashboard-stat"><dt>累计更新</dt><dd>1 次</dd></div>
    <div class="dpr-home-dashboard-stat"><dt>精读</dt><dd>7</dd></div>
    <div class="dpr-home-dashboard-stat"><dt>速读</dt><dd>18</dd></div>
  </dl>
  <p class="dpr-home-dashboard-body">最近更新：2026-11-01 19:25:32 UTC<br>状态：成功</p>
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
<p>2026-11-01 论文日报出炉：完成 25 篇推荐梳理，含精读 7 篇、速读 18 篇。</p>
<p>今天优先关注两个均获 9.0/10 的方向：借鉴推荐系统设计 LLM 智能体长期记忆，以及 AI 角色定位与自动驾驶接管中人类决策行为的关系。</p>
<p>普通读者建议先按兴趣选读上述一篇，再从语音情绪识别、陌生世界学习或“先提问再回答”的证据推理中挑一个方向速读。</p>
  </div>
</section>
<section class="dpr-home-dashboard-card dpr-home-deep-card">
  <div class="dpr-home-dashboard-header">
    <div>
      <span class="dpr-home-dashboard-kicker">今日累计</span>
      <h3 class="dpr-home-dashboard-title">精读推荐</h3>
    </div>
    <strong class="dpr-home-dashboard-count">7 篇</strong>
  </div>
  <div class="dpr-home-dashboard-body">
<ul class="dpr-home-dashboard-paper-list"><li><span class="dpr-home-dashboard-paper-title" title="Agent Memory as Recommendation: Recommender-System Design for Long-Term Memory of LLM Agents">Agent Memory as Recommendation: Recommender-System Design for Long-Term Memory of LLM Agents</span></li><li><span class="dpr-home-dashboard-paper-title" title="Advisor, Co-pilot, or Guardian? AI Role Framing and Human Decision Behavior in Automated Vehicle Takeovers">Advisor, Co-pilot, or Guardian? AI Role Framing and Human Decision Behavior in Automated Vehicle Takeovers</span></li><li><span class="dpr-home-dashboard-paper-title" title="LogicTree: Object-Oriented Writing for Structured Human-AI Academic Authoring">LogicTree: Object-Oriented Writing for Structured Human-AI Academic Authoring</span></li></ul>
  </div>
  <div class="dpr-home-dashboard-tags"><span class="dpr-home-dashboard-tag">human-ai <strong>4</strong></span><span class="dpr-home-dashboard-tag">personal-agent <strong>2</strong></span><span class="dpr-home-dashboard-tag">social-computing <strong>1</strong></span></div>
</section>
<section class="dpr-home-dashboard-card dpr-home-skim-card">
  <div class="dpr-home-dashboard-header">
    <div>
      <span class="dpr-home-dashboard-kicker">今日累计</span>
      <h3 class="dpr-home-dashboard-title">速读推荐</h3>
    </div>
    <strong class="dpr-home-dashboard-count">18 篇</strong>
  </div>
  <div class="dpr-home-dashboard-body">
<ul class="dpr-home-dashboard-paper-list"><li><span class="dpr-home-dashboard-paper-title" title="EmoNet: A Lightweight Attention-Based CNN for Speech Emotion Recognition">EmoNet: A Lightweight Attention-Based CNN for Speech Emotion Recognition</span></li><li><span class="dpr-home-dashboard-paper-title" title="How Humans Learn Unfamiliar Worlds: A Think-Aloud Dataset on ARC-AGI-3">How Humans Learn Unfamiliar Worlds: A Think-Aloud Dataset on ARC-AGI-3</span></li><li><span class="dpr-home-dashboard-paper-title" title="Ask Before You Answer: A Question-Driven Evidence Reasoning Architecture (QERA) for In-Context Learning">Ask Before You Answer: A Question-Driven Evidence Reasoning Architecture (QERA) for In-Context Learning</span></li></ul>
  </div>
  <div class="dpr-home-dashboard-tags"><span class="dpr-home-dashboard-tag">human-ai <strong>7</strong></span><span class="dpr-home-dashboard-tag">personal-agent <strong>5</strong></span><span class="dpr-home-dashboard-tag">ai-hci-mh <strong>2</strong></span><span class="dpr-home-dashboard-tag">llm-econ <strong>1</strong></span><span class="dpr-home-dashboard-tag">llm-social-sim <strong>1</strong></span><span class="dpr-home-dashboard-tag">social-computing <strong>1</strong></span></div>
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
