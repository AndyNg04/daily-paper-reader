(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.DPRLLMConfigUtils = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const DEFAULT_DEEPSEEK_BASE_URL = 'https://api.deepseek.com';
  const DEFAULT_DEEPSEEK_CHAT_MODELS = [
    'deepseek-v4-flash',
    'deepseek-v4-pro',
  ];
  const DEEPSEEK_V4_MAX_OUTPUT_TOKENS = 393216;
  const DEEPSEEK_PRESETS = Object.freeze({
    deepseek: Object.freeze({
      key: 'deepseek',
      label: 'DeepSeek 官方',
      baseUrl: 'https://api.deepseek.com',
      models: Object.freeze(['deepseek-v4-flash', 'deepseek-v4-pro']),
    }),
  });

  const normalizeText = (value) => String(value || '').trim();

  const normalizeBaseUrlForStorage = (value) => {
    let text = normalizeText(value).replace(/\/+$/g, '');
    if (!text) return '';
    text = text.replace(/\/chat\/completions$/i, '');
    return text.replace(/\/+$/g, '');
  };

  const buildChatCompletionsEndpoint = (value) => {
    const raw = normalizeText(value).replace(/\/+$/g, '');
    if (!raw) return '';
    if (/\/chat\/completions$/i.test(raw)) return raw;
    const normalized = normalizeBaseUrlForStorage(raw);
    if (!normalized) return '';
    if (/\/v\d+$/i.test(normalized)) {
      return `${normalized}/chat/completions`;
    }
    return `${normalized}/v1/chat/completions`;
  };

  const sanitizeModelList = (values, maxCount = 3) => {
    const rawList = Array.isArray(values) ? values : [values];
    const out = [];
    const seen = new Set();
    for (const value of rawList) {
      const parts = String(value || '')
        .split(/[\n,]+/)
        .map((item) => normalizeText(item))
        .filter(Boolean);
      for (const name of parts) {
        const key = name.toLowerCase();
        if (!key || seen.has(key)) continue;
        seen.add(key);
        out.push(name);
        if (out.length >= Math.max(Number(maxCount) || 0, 1)) {
          return out;
        }
      }
    }
    return out;
  };

  const resolveChatModels = (secret) => {
    const safeSecret = secret && typeof secret === 'object' ? secret : {};
    const chatList = Array.isArray(safeSecret.chatLLMs) ? safeSecret.chatLLMs : [];
    const models = [];
    const seen = new Set();
    chatList.forEach((item) => {
      if (!item || typeof item !== 'object') return;
      const baseUrl = normalizeBaseUrlForStorage(item.baseUrl || '');
      const apiKey = normalizeText(item.apiKey || '');
      const modelNames = sanitizeModelList(item.models || [], 99);
      if (!baseUrl || !apiKey || !modelNames.length) return;
      modelNames.forEach((name) => {
        const dedupeKey = `${name.toLowerCase()}\u0000${baseUrl}\u0000${apiKey}`;
        if (seen.has(dedupeKey)) return;
        seen.add(dedupeKey);
        models.push({
          name,
          apiKey,
          baseUrl,
        });
      });
    });
    return models;
  };

  const resolveSummaryLLM = (secret) => {
    const safeSecret = secret && typeof secret === 'object' ? secret : {};
    const summarized = safeSecret.summarizedLLM || {};
    const baseUrl = normalizeBaseUrlForStorage(summarized.baseUrl || '');
    const apiKey = normalizeText(summarized.apiKey || '');
    const model = normalizeText(summarized.model || '');
    if (baseUrl && apiKey && model) {
      return { baseUrl, apiKey, model };
    }

    const chatModels = resolveChatModels(safeSecret);
    if (!chatModels.length) return null;
    return {
      baseUrl: normalizeBaseUrlForStorage(chatModels[0].baseUrl || ''),
      apiKey: normalizeText(chatModels[0].apiKey || ''),
      model: normalizeText(chatModels[0].name || ''),
    };
  };

  const inferProviderType = (secret) => {
    const safeSecret = secret && typeof secret === 'object' ? secret : {};
    const llmProvider = safeSecret.llmProvider || {};
    const explicit = normalizeText(llmProvider.type || llmProvider.provider || '').toLowerCase();
    if (explicit === 'deepseek') {
      return 'deepseek';
    }
    return 'deepseek';
  };

  const getDeepSeekPreset = (key) => {
    const presetKey = normalizeText(key).toLowerCase();
    const preset = DEEPSEEK_PRESETS[presetKey];
    if (!preset) return null;
    return {
      key: preset.key,
      label: preset.label,
      baseUrl: preset.baseUrl,
      models: [...preset.models],
    };
  };

  const inferChatApiProfile = (baseUrl, model) => {
    const normalizedBaseUrl = normalizeBaseUrlForStorage(baseUrl || '').toLowerCase();
    const normalizedModel = normalizeText(model || '').toLowerCase();
    if (/(^|\/\/)(api\.)?deepseek\.com(?:$|\/)/i.test(normalizedBaseUrl)) {
      return 'deepseek';
    }
    if (normalizedModel.startsWith('deepseek-')) {
      return 'deepseek';
    }
    return 'unsupported';
  };

  const resolveJsonResponseMode = ({ baseUrl, model, preferSchema = true }) => {
    return 'json_object';
  };

  const isDeepSeekV4Model = (model) => {
    const normalizedModel = normalizeText(model || '').toLowerCase();
    return normalizedModel === 'deepseek-v4-flash' || normalizedModel === 'deepseek-v4-pro';
  };

  const resolveMaxOutputTokens = ({ baseUrl, model } = {}) => {
    const profile = inferChatApiProfile(baseUrl, model);
    if (profile === 'deepseek' && isDeepSeekV4Model(model)) {
      return DEEPSEEK_V4_MAX_OUTPUT_TOKENS;
    }
    return null;
  };

  const shouldUseXApiKeyHeader = ({ baseUrl, model }) => {
    return true;
  };

  const buildStreamingChatPayload = ({ baseUrl, model, messages }) => {
    const payload = {
      model: normalizeText(model),
      messages: Array.isArray(messages) ? messages : [],
      stream: true,
    };
    const maxTokens = resolveMaxOutputTokens({ baseUrl, model });
    if (maxTokens) {
      payload.max_tokens = maxTokens;
    }
    return payload;
  };

  // ---------- DeepSeek 联网搜索（Anthropic 兼容接口） ----------
  // DeepSeek 的 OpenAI 兼容接口没有搜索；它的 Anthropic 兼容接口原生支持 web_search 服务端工具：
  // 模型自己决定要不要搜，搜索、读网页都在 DeepSeek 服务器上完成，只用同一个 DeepSeek key。
  const DEEPSEEK_WEB_SEARCH_TOOL = Object.freeze({
    type: 'web_search_20250305',
    name: 'web_search',
    max_uses: 5,
  });
  const WEB_SEARCH_MAX_TOKENS = 32768;

  const supportsDeepSeekWebSearch = ({ baseUrl, model } = {}) =>
    inferChatApiProfile(baseUrl, model) === 'deepseek'
    && /(^|\/\/)(api\.)?deepseek\.com(?:$|\/)/i.test(normalizeBaseUrlForStorage(baseUrl || ''));

  const buildAnthropicMessagesEndpoint = (baseUrl) => {
    const normalized = normalizeBaseUrlForStorage(baseUrl || '').replace(/\/(v\d+|anthropic)$/i, '');
    if (!normalized) return '';
    return `${normalized}/anthropic/v1/messages`;
  };

  // OpenAI 风格 messages → Anthropic：system 单独放；连续同角色的消息合并，保证 user/assistant 交替。
  const toAnthropicMessages = (messages) => {
    const systemParts = [];
    const out = [];
    (Array.isArray(messages) ? messages : []).forEach((m) => {
      if (!m || typeof m !== 'object') return;
      const content = String(m.content || '');
      if (m.role === 'system') {
        if (content.trim()) systemParts.push(content);
        return;
      }
      const role = m.role === 'assistant' ? 'assistant' : 'user';
      if (!content.trim()) return;
      const last = out[out.length - 1];
      if (last && last.role === role) {
        last.content += `\n\n${content}`;
      } else {
        out.push({ role, content });
      }
    });
    while (out.length && out[0].role !== 'user') out.shift();
    return { system: systemParts.join('\n\n'), messages: out };
  };

  const buildWebSearchChatPayload = ({ model, messages }) => {
    const converted = toAnthropicMessages(messages);
    const payload = {
      model: normalizeText(model),
      max_tokens: WEB_SEARCH_MAX_TOKENS,
      stream: true,
      messages: converted.messages,
      tools: [{ ...DEEPSEEK_WEB_SEARCH_TOOL }],
    };
    if (converted.system) payload.system = converted.system;
    return payload;
  };

  const createWebSearchStreamState = () => ({ blocks: {}, sources: [], queries: [] });

  const addSource = (state, url, title) => {
    const safeUrl = normalizeText(url);
    if (!/^https?:\/\//i.test(safeUrl)) return;
    if (state.sources.some((s) => s.url === safeUrl)) return;
    state.sources.push({ url: safeUrl, title: normalizeText(title) || safeUrl });
  };

  // 处理一条 Anthropic 流式事件，返回这次新增的 { thinking, text }。
  // 搜索动作以一行提示写进 thinking，引用的网页收集到 state.sources。
  const applyWebSearchStreamEvent = (state, event) => {
    const out = { thinking: '', text: '' };
    if (!event || typeof event !== 'object') return out;
    const index = event.index;
    if (event.type === 'content_block_start') {
      const block = event.content_block || {};
      state.blocks[index] = { type: block.type, json: '' };
      if (block.type === 'web_search_tool_result' && Array.isArray(block.content)) {
        block.content.forEach((r) => r && addSource(state, r.url, r.title));
      }
      if (block.type === 'text' && Array.isArray(block.citations)) {
        block.citations.forEach((c) => c && addSource(state, c.url, c.title));
      }
      if (block.type === 'text' && block.text) out.text += block.text;
      if (block.type === 'thinking' && block.thinking) out.thinking += block.thinking;
      return out;
    }
    if (event.type === 'content_block_delta') {
      const delta = event.delta || {};
      if (delta.type === 'text_delta') out.text += delta.text || '';
      else if (delta.type === 'thinking_delta') out.thinking += delta.thinking || '';
      else if (delta.type === 'input_json_delta' && state.blocks[index]) {
        state.blocks[index].json += delta.partial_json || '';
      } else if (delta.type === 'citations_delta' && delta.citation) {
        addSource(state, delta.citation.url, delta.citation.title);
      }
      return out;
    }
    if (event.type === 'content_block_stop') {
      const block = state.blocks[index];
      if (block && block.type === 'server_tool_use') {
        let query = '';
        try {
          query = normalizeText((JSON.parse(block.json || '{}') || {}).query);
        } catch {
          query = '';
        }
        state.queries.push(query);
        out.thinking += `\n\n🔍 联网搜索${query ? `：${query}` : ''}\n\n`;
      }
      return out;
    }
    if (event.type === 'error') {
      const err = event.error || {};
      throw new Error(normalizeText(err.message) || '联网搜索流返回错误');
    }
    return out;
  };

  const formatWebSearchSources = (state, maxCount = 8) => {
    const list = (state && Array.isArray(state.sources) ? state.sources : []).slice(0, maxCount);
    if (!list.length) return '';
    const esc = (t) => String(t).replace(/([\[\]])/g, '\\$1');
    return ['', '', '**参考来源**', ...list.map((s, i) => `${i + 1}. [${esc(s.title)}](${s.url})`)].join('\n');
  };

  const buildConnectivityTestPayload = ({ baseUrl, model }) => {
    const normalizedModel = normalizeText(model);
    return {
      model: normalizedModel,
      messages: [
        {
          role: 'system',
          content: 'Reply with exactly: hello world',
        },
        {
          role: 'user',
          content: 'hello world',
        },
      ],
      temperature: 0,
      max_tokens: 256,
    };
  };

  return {
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_CHAT_MODELS,
    DEEPSEEK_PRESETS,
    normalizeText,
    normalizeBaseUrlForStorage,
    buildChatCompletionsEndpoint,
    sanitizeModelList,
    resolveChatModels,
    resolveSummaryLLM,
    inferProviderType,
    getDeepSeekPreset,
    inferChatApiProfile,
    resolveJsonResponseMode,
    isDeepSeekV4Model,
    resolveMaxOutputTokens,
    shouldUseXApiKeyHeader,
    buildStreamingChatPayload,
    buildConnectivityTestPayload,
    DEEPSEEK_WEB_SEARCH_TOOL,
    supportsDeepSeekWebSearch,
    buildAnthropicMessagesEndpoint,
    toAnthropicMessages,
    buildWebSearchChatPayload,
    createWebSearchStreamState,
    applyWebSearchStreamEvent,
    formatWebSearchSources,
  };
});
