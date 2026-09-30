const assert = require('node:assert/strict');

const {
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
  supportsDeepSeekWebSearch,
  buildAnthropicMessagesEndpoint,
  toAnthropicMessages,
  buildWebSearchChatPayload,
  createWebSearchStreamState,
  applyWebSearchStreamEvent,
  formatWebSearchSources,
} = require('../app/llm-config-utils.js');

function testNormalizeBaseUrlForStorage() {
  assert.equal(
    normalizeBaseUrlForStorage('https://api.example.com/v1/chat/completions'),
    'https://api.example.com/v1',
  );
  assert.equal(
    normalizeBaseUrlForStorage('https://api.example.com/v1/'),
    'https://api.example.com/v1',
  );
}

function testBuildChatCompletionsEndpoint() {
  assert.equal(
    buildChatCompletionsEndpoint('https://api.example.com/v1'),
    'https://api.example.com/v1/chat/completions',
  );
  assert.equal(
    buildChatCompletionsEndpoint('https://api.example.com/custom-root'),
    'https://api.example.com/custom-root/v1/chat/completions',
  );
}

function testSanitizeModelList() {
  assert.deepEqual(
    sanitizeModelList(['deepseek-v4-flash', ' deepseek-v4-flash ', 'deepseek-v4-pro', 'custom-model', 'extra'], 3),
    ['deepseek-v4-flash', 'deepseek-v4-pro', 'custom-model'],
  );
}

function testResolveChatModelsAndSummary() {
  const secret = {
    summarizedLLM: {
      apiKey: 'sk-summary',
      baseUrl: 'https://api.example.com/v1',
      model: 'gpt-4.1-mini',
    },
    chatLLMs: [
      {
        apiKey: 'sk-chat',
        baseUrl: 'https://api.example.com/v1/',
        models: ['gpt-4.1-mini', 'claude-sonnet-4'],
      },
    ],
  };

  const chatModels = resolveChatModels(secret);
  assert.equal(chatModels.length, 2);
  assert.deepEqual(chatModels.map((item) => item.name), [
    'gpt-4.1-mini',
    'claude-sonnet-4',
  ]);

  const summary = resolveSummaryLLM(secret);
  assert.equal(summary.model, 'gpt-4.1-mini');
  assert.equal(summary.baseUrl, 'https://api.example.com/v1');
}

function testInferProviderType() {
  assert.equal(
    inferProviderType({
      summarizedLLM: {
        apiKey: 'sk',
        baseUrl: 'https://api.deepseek.com',
        model: 'deepseek-v4-flash',
      },
    }),
    'deepseek',
  );
  assert.equal(
    inferProviderType({
      summarizedLLM: {
        apiKey: 'sk',
        baseUrl: 'https://example.com/v1',
        model: 'other-model',
      },
    }),
    'deepseek',
  );
}

function testGetDeepSeekPreset() {
  assert.deepEqual(
    getDeepSeekPreset('deepseek'),
    {
      key: 'deepseek',
      label: 'DeepSeek 官方',
      baseUrl: 'https://api.deepseek.com',
      models: ['deepseek-v4-flash', 'deepseek-v4-pro'],
    },
  );
  assert.equal(getDeepSeekPreset('other-a'), null);
  assert.equal(getDeepSeekPreset('other-b'), null);
  assert.equal(getDeepSeekPreset('other-c'), null);
  assert.equal(getDeepSeekPreset('other-d'), null);
}

function testInferChatApiProfile() {
  assert.equal(
    inferChatApiProfile('https://api.deepseek.com', 'deepseek-v4-flash'),
    'deepseek',
  );
  assert.equal(inferChatApiProfile('https://example.com/v1', 'other-model'), 'unsupported');
  assert.equal(inferChatApiProfile('https://example.com/v1', 'other-model'), 'unsupported');
}

function testResolveJsonResponseMode() {
  assert.equal(
    resolveJsonResponseMode({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-flash',
    }),
    'json_object',
  );
  assert.equal(
    resolveJsonResponseMode({
      baseUrl: 'https://example.com/v1',
      model: 'other-model',
      preferSchema: false,
    }),
    'json_object',
  );
}

function testResolveMaxOutputTokens() {
  assert.equal(isDeepSeekV4Model('deepseek-v4-flash'), true);
  assert.equal(isDeepSeekV4Model('deepseek-v4-pro'), true);
  assert.equal(isDeepSeekV4Model('deepseek-chat'), false);
  assert.equal(
    resolveMaxOutputTokens({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-flash',
    }),
    393216,
  );
  assert.equal(
    resolveMaxOutputTokens({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-pro',
    }),
    393216,
  );
  assert.equal(
    resolveMaxOutputTokens({
      baseUrl: 'https://example.com/v1',
      model: 'other-model',
    }),
    null,
  );
}

function testShouldUseXApiKeyHeader() {
  assert.equal(
    shouldUseXApiKeyHeader({
      baseUrl: 'https://example.com/v1',
      model: 'other-model',
    }),
    true,
  );
  assert.equal(
    shouldUseXApiKeyHeader({
      baseUrl: 'https://example.com/v1',
      model: 'other-model',
    }),
    true,
  );
}

function testBuildStreamingChatPayload() {
  assert.deepEqual(
    buildStreamingChatPayload({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-flash',
      messages: [{ role: 'user', content: 'hi' }],
    }),
    {
      model: 'deepseek-v4-flash',
      messages: [{ role: 'user', content: 'hi' }],
      stream: true,
      max_tokens: 393216,
    },
  );

  assert.deepEqual(
    buildStreamingChatPayload({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-pro',
      messages: [{ role: 'user', content: 'hi' }],
    }),
    {
      model: 'deepseek-v4-pro',
      messages: [{ role: 'user', content: 'hi' }],
      stream: true,
      max_tokens: 393216,
    },
  );

}

function testBuildConnectivityTestPayload() {
  assert.deepEqual(
    buildConnectivityTestPayload({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-pro',
    }),
    {
      model: 'deepseek-v4-pro',
      messages: [
        { role: 'system', content: 'Reply with exactly: hello world' },
        { role: 'user', content: 'hello world' },
      ],
      temperature: 0,
      max_tokens: 256,
    },
  );

  assert.deepEqual(
    buildConnectivityTestPayload({
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-flash',
    }),
    {
      model: 'deepseek-v4-flash',
      messages: [
        { role: 'system', content: 'Reply with exactly: hello world' },
        { role: 'user', content: 'hello world' },
      ],
      temperature: 0,
      max_tokens: 256,
    },
  );

}

function testWebSearchHelpers() {
  assert.equal(supportsDeepSeekWebSearch({ baseUrl: 'https://api.deepseek.com', model: 'deepseek-v4-pro' }), true);
  assert.equal(supportsDeepSeekWebSearch({ baseUrl: 'https://api.deepseek.com/v1', model: 'deepseek-v4-flash' }), true);
  // 自定义代理地址不保证有 /anthropic 接口，不启用
  assert.equal(supportsDeepSeekWebSearch({ baseUrl: 'https://proxy.example.com/v1', model: 'deepseek-v4-pro' }), false);
  assert.equal(buildAnthropicMessagesEndpoint('https://api.deepseek.com'), 'https://api.deepseek.com/anthropic/v1/messages');
  assert.equal(buildAnthropicMessagesEndpoint('https://api.deepseek.com/v1/'), 'https://api.deepseek.com/anthropic/v1/messages');
  assert.equal(buildAnthropicMessagesEndpoint('https://api.deepseek.com/anthropic'), 'https://api.deepseek.com/anthropic/v1/messages');

  const converted = toAnthropicMessages([
    { role: 'system', content: 'S1' },
    { role: 'assistant', content: 'dangling' },
    { role: 'user', content: 'paper' },
    { role: 'user', content: 'q1' },
    { role: 'assistant', content: 'a1' },
    { role: 'user', content: '' },
    { role: 'user', content: 'q2' },
  ]);
  assert.equal(converted.system, 'S1');
  assert.deepEqual(converted.messages, [
    { role: 'user', content: 'paper\n\nq1' },
    { role: 'assistant', content: 'a1' },
    { role: 'user', content: 'q2' },
  ]);

  const payload = buildWebSearchChatPayload({ model: 'deepseek-v4-pro', messages: [{ role: 'system', content: 'S' }, { role: 'user', content: 'hi' }] });
  assert.equal(payload.stream, true);
  assert.equal(payload.system, 'S');
  assert.ok(payload.max_tokens > 0);
  assert.deepEqual(payload.tools, [{ type: 'web_search_20250305', name: 'web_search', max_uses: 5 }]);
  assert.equal(payload.tool_choice, undefined, '不强制搜索，由模型自己决定');
}

function testWebSearchStream() {
  const state = createWebSearchStreamState();
  const events = [
    { type: 'message_start', message: {} },
    { type: 'content_block_start', index: 0, content_block: { type: 'thinking', thinking: '' } },
    { type: 'content_block_delta', index: 0, delta: { type: 'thinking_delta', thinking: '想一想' } },
    { type: 'content_block_stop', index: 0 },
    { type: 'content_block_start', index: 1, content_block: { type: 'server_tool_use', id: 'x', name: 'web_search', input: {} } },
    { type: 'content_block_delta', index: 1, delta: { type: 'input_json_delta', partial_json: '{"query":"ELEP' } },
    { type: 'content_block_delta', index: 1, delta: { type: 'input_json_delta', partial_json: 'HANT sycophancy"}' } },
    { type: 'content_block_stop', index: 1 },
    { type: 'content_block_start', index: 2, content_block: { type: 'web_search_tool_result', content: [
      { type: 'web_search_result', url: 'https://arxiv.org/abs/2505.13995', title: 'ELEPHANT [paper]' },
      { type: 'web_search_result', url: 'javascript:alert(1)', title: 'bad' },
    ] } },
    { type: 'content_block_stop', index: 2 },
    { type: 'content_block_start', index: 3, content_block: { type: 'text', text: '' } },
    { type: 'content_block_delta', index: 3, delta: { type: 'text_delta', text: '答案' } },
    { type: 'content_block_delta', index: 3, delta: { type: 'citations_delta', citation: { url: 'https://arxiv.org/abs/2505.13995', title: 'dup' } } },
    { type: 'content_block_delta', index: 3, delta: { type: 'citations_delta', citation: { url: 'https://example.org/b', title: 'B' } } },
    { type: 'content_block_stop', index: 3 },
    { type: 'message_delta', delta: { stop_reason: 'end_turn' } },
    { type: 'message_stop' },
  ];
  let thinking = '';
  let text = '';
  events.forEach((e) => {
    const piece = applyWebSearchStreamEvent(state, e);
    thinking += piece.thinking;
    text += piece.text;
  });
  assert.equal(text, '答案');
  assert.match(thinking, /想一想/);
  assert.match(thinking, /🔍 联网搜索：ELEPHANT sycophancy/);
  assert.deepEqual(state.queries, ['ELEPHANT sycophancy']);
  assert.deepEqual(state.sources.map((s) => s.url), ['https://arxiv.org/abs/2505.13995', 'https://example.org/b']);
  const md = formatWebSearchSources(state);
  assert.match(md, /\*\*参考来源\*\*/);
  assert.match(md, /1\. \[ELEPHANT \\\[paper\\\]\]\(https:\/\/arxiv\.org\/abs\/2505\.13995\)/);
  assert.equal(formatWebSearchSources(createWebSearchStreamState()), '');
  assert.throws(() => applyWebSearchStreamEvent(state, { type: 'error', error: { message: 'overloaded' } }), /overloaded/);
}

testNormalizeBaseUrlForStorage();
testBuildChatCompletionsEndpoint();
testSanitizeModelList();
testResolveChatModelsAndSummary();
testInferProviderType();
testGetDeepSeekPreset();
testInferChatApiProfile();
testResolveJsonResponseMode();
testResolveMaxOutputTokens();
testShouldUseXApiKeyHeader();
testBuildStreamingChatPayload();
testBuildConnectivityTestPayload();
testWebSearchHelpers();
testWebSearchStream();

console.log('llm config utils tests passed');
