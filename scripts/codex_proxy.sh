#!/usr/bin/env bash
# 在 GitHub Actions 里运行 CLIProxyAPI，把 Codex（ChatGPT 订阅）额度暴露成本机的
# OpenAI 兼容接口（fork 专用）。
#
#   codex_proxy.sh login   设备码登录，凭证写到 $CODEX_PROXY_ROOT/auth/
#   codex_proxy.sh start   安装 $CODEX_AUTH_JSON，后台启动 proxy，并把 LLM 相关环境变量
#                          写进 $GITHUB_ENV（没有 GITHUB_ENV 时打印到 stdout）
#   codex_proxy.sh stop    停止 proxy
#
# 安全：仓库公开，日志公开。proxy 只监听 127.0.0.1，本地访问 key 每次随机生成并打码；
# 凭证目录在仓库之外（RUNNER_TEMP），不会被 git add、cache 或 artifact 带走。
set -euo pipefail

CPA_VERSION="7.3.20"
CPA_SHA256="f267c31953ebf71315d5e78cd5284f2866b1ea8cc92589a00df88ff68c95d149"
CPA_ASSET="CLIProxyAPI_${CPA_VERSION}_linux_amd64_no-plugin.tar.gz"
CPA_URL="https://github.com/router-for-me/CLIProxyAPI/releases/download/v${CPA_VERSION}/${CPA_ASSET}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CODEX_PROXY_ROOT:-${RUNNER_TEMP:-/tmp}/codex-proxy}"
BIN="$ROOT/cli-proxy-api"
AUTH_DIR="$ROOT/auth"
CONFIG="$ROOT/config.yaml"
PORT="${CODEX_PROXY_PORT:-8317}"

log() { echo "[codex-proxy] $*"; }
die() {
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then echo "::error::[codex-proxy] $*" >&2; else echo "[codex-proxy] $*" >&2; fi
  exit 1
}

install_bin() {
  mkdir -p "$ROOT" "$AUTH_DIR"
  chmod 700 "$ROOT" "$AUTH_DIR"
  if [ -x "$BIN" ]; then return 0; fi
  local tarball="$ROOT/$CPA_ASSET"
  curl -fsSL --retry 3 -o "$tarball" "$CPA_URL" || die "下载 CLIProxyAPI v${CPA_VERSION} 失败"
  echo "${CPA_SHA256}  ${tarball}" | sha256sum -c --quiet - || die "CLIProxyAPI 安装包 sha256 不匹配"
  tar -xzf "$tarball" -C "$ROOT" cli-proxy-api
  rm -f "$tarball"
  chmod 700 "$BIN"
  log "已安装 CLIProxyAPI v${CPA_VERSION}"
}

write_config() {
  local key="$1"
  umask 077
  cat > "$CONFIG" <<EOF
host: "127.0.0.1"
port: ${PORT}
auth-dir: "${AUTH_DIR}"
api-keys:
  - "${key}"
remote-management:
  allow-remote: false
  secret-key: ""
  disable-control-panel: true
debug: false
logging-to-file: false
usage-statistics-enabled: false
request-log: false
EOF
}

cmd_login() {
  install_bin
  write_config "$(openssl rand -hex 24)"
  # 设备码登录：日志里会出现网址和验证码，到网页上登录 ChatGPT 并输入验证码。
  # 验证码 15 分钟内有效；别人拿到验证码也只能登录他自己的账号。
  (cd "$ROOT" && "$BIN" -config "$CONFIG" -codex-device-login -no-browser < /dev/null)
  python3 "$SCRIPT_DIR/codex_auth.py" status --dir "$AUTH_DIR" || die "登录没有生成 codex 凭证"
}

cmd_start() {
  install_bin
  python3 "$SCRIPT_DIR/codex_auth.py" install --dir "$AUTH_DIR" --digest-out "$ROOT/installed.sha256"
  local key
  key="$(openssl rand -hex 24)"
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then echo "::add-mask::${key}"; fi
  write_config "$key"
  # proxy 在 auth-dir/logs 下写错误日志（含请求头）；它和凭证一样只在 RUNNER_TEMP，不上传。
  (
    cd "$ROOT" || exit 1
    nohup "$BIN" -config "$CONFIG" > "$ROOT/proxy.log" 2>&1 &
    echo $! > "$ROOT/proxy.pid"
  )

  local base="http://127.0.0.1:${PORT}/v1" ok=""
  for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null -H "Authorization: Bearer ${key}" "${base}/models" 2>/dev/null; then ok=1; break; fi
    if ! kill -0 "$(cat "$ROOT/proxy.pid")" 2>/dev/null; then break; fi
    sleep 1
  done
  if [ -z "$ok" ]; then
    # 只打印最后几行、并去掉可能的 token/邮箱，避免公开日志泄露。
    tail -n 20 "$ROOT/proxy.log" | sed -E 's/(eyJ|rt_|sk-)[A-Za-z0-9._-]+/***/g; s/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+/***@***/g' >&2 || true
    die "proxy 没有启动成功"
  fi
  log "proxy 已在 ${base} 启动"

  local strong="${CODEX_MODEL:-gpt-6-sol}" fast="${CODEX_FAST_MODEL:-gpt-6-luna}"
  # 推理强度用 OpenAI 给 GPT-6 Sol/Luna 的官方默认值 medium，写成 CLIProxyAPI 的
  # "模型(强度)" 后缀显式指定，不依赖 proxy 自己的默认值。模型名已带后缀时不再追加。
  local effort="${CODEX_REASONING_EFFORT:-medium}"
  case "$strong" in *\)) ;; *) strong="${strong}(${effort})" ;; esac
  case "$fast" in *\)) ;; *) fast="${fast}(${effort})" ;; esac
  local out="${GITHUB_ENV:-/dev/stdout}"
  {
    echo "CODEX_PROXY_ROOT=${ROOT}"
    echo "CODEX_PROXY_BASE_URL=${base}"
    # 项目里所有 LLM 调用都读这几组变量（DeepSeek 命名是历史原因）。
    for name in DEEPSEEK_API_KEY SUMMARY_API_KEY; do echo "${name}=${key}"; done
    for name in DEEPSEEK_BASE_URL SUMMARY_BASE_URL LLM_PRIMARY_BASE_URL; do echo "${name}=${base}"; done
    # 精读/速读总结（Step 6）用强模型；筛选、查询改写等量大的环节用快模型。
    echo "SUMMARY_MODEL=${strong}"
    for name in DEEPSEEK_MODEL DEEPSEEK_FILTER_MODEL DEEPSEEK_REWRITE_MODEL; do echo "${name}=${fast}"; done
  } >> "$out"
  log "模型：总结 ${strong}，其他环节 ${fast}"
}

cmd_stop() {
  if [ -f "$ROOT/proxy.pid" ]; then kill "$(cat "$ROOT/proxy.pid")" 2>/dev/null || true; rm -f "$ROOT/proxy.pid"; fi
}

case "${1:-}" in
  login) cmd_login ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  *) die "用法: $0 login|start|stop" ;;
esac
