# -*- coding: utf-8 -*-
"""
agentsec-labs 模型提供商管理：本地 Ollama + 云端 API 双模。

支持：
  - Ollama（本地，默认）
  - OpenAI 兼容（OpenAI / DeepSeek / Groq / Together / OpenRouter / 自定义）
  - Anthropic（Claude 系列）

配置持久化到 providers.json，Web 首页可配置。
"""
import json
import urllib.request
from pathlib import Path

PILABS_DIR = Path(__file__).resolve().parent
CONFIG_FILE = PILABS_DIR / "providers.json"

# ---------- 预置提供商模板 ----------
PRESETS = {
    "local": {
        "name": "本地 Ollama",
        "type": "ollama",
        "url": "http://localhost:11434",
        "key": "",
        "model": "qwen2.5-coder:7b",
        "note": "推荐：免费、低延迟，无需 API Key",
    },
    "openai": {
        "name": "OpenAI",
        "type": "openai",
        "url": "https://api.openai.com/v1",
        "key": "",
        "model": "gpt-4o-mini",
        "note": "需要 sk- 开头的 API Key",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "type": "anthropic",
        "url": "https://api.anthropic.com/v1",
        "key": "",
        "model": "claude-sonnet-4-20250514",
        "note": "需要 Anthropic API Key",
    },
    "deepseek": {
        "name": "DeepSeek",
        "type": "openai",
        "url": "https://api.deepseek.com/v1",
        "key": "",
        "model": "deepseek-chat",
        "note": "性价比高，OpenAI 兼容格式",
    },
    "groq": {
        "name": "Groq",
        "type": "openai",
        "url": "https://api.groq.com/openai/v1",
        "key": "",
        "model": "llama-3.1-8b-instant",
        "note": "超快推理，免费额度，OpenAI 兼容",
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "openai",
        "url": "https://openrouter.ai/api/v1",
        "key": "",
        "model": "google/gemini-flash-1.5",
        "note": "一个 Key 访问多家模型",
    },
    "custom": {
        "name": "自定义（OpenAI 兼容）",
        "type": "openai",
        "url": "",
        "key": "",
        "model": "",
        "note": "任何 OpenAI 兼容端点（vLLM / LiteLLM / OneAPI 等）",
    },
}


# ---------- 配置读写 ----------
def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"active": "local", "providers": dict(PRESETS)}


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_active():
    cfg = load_config()
    pid = cfg.get("active", "local")
    prov = cfg.get("providers", {}).get(pid, PRESETS["local"])
    return pid, prov


def set_active(pid):
    cfg = load_config()
    if pid in cfg.get("providers", {}):
        cfg["active"] = pid
        save_config(cfg)


# 已知的安全模型名（每个提供商的可用模型）
_SAFE_MODELS = {
    "local": {"qwen2.5-coder:7b"},
    "openai": {"gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini", "o1-preview"},
    "anthropic": {"claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"},
    "deepseek": {"deepseek-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner", "deepseek-coder"},
    "groq": {"llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"},
    "openrouter": set(),  # 太多，不做限制
    "custom": set(),      # 自定义端点，不做限制
}


def update_provider(pid, url="", key="", model=""):
    cfg = load_config()
    if "providers" not in cfg:
        cfg["providers"] = dict(PRESETS)
    p = cfg["providers"].get(pid, dict(PRESETS.get(pid, PRESETS["custom"])))
    if url:
        p["url"] = url
    if key:
        p["key"] = key
    if model:
        model = model.strip().lower()
        # 校验：如果该提供商有已知安全模型列表，检查是否在列表内
        safe = _SAFE_MODELS.get(pid, set())
        if safe and model not in safe:
            # 不在安全列表 → 拒绝写入，保持原值
            print(f"[providers] BLOCKED invalid model '{model}' for '{pid}'. Safe: {sorted(safe)}")
            return  # 不保存
        p["model"] = model
    cfg["providers"][pid] = p
    save_config(cfg)


# ---------- 统一 chat 接口 ----------
def chat(messages, num_ctx=None, temperature=0.7, timeout=300):
    """根据当前活跃提供商调用对应 API。返回助手回复文本。"""
    pid, prov = get_active()
    ptype = prov.get("type", "ollama")
    url = prov.get("url", "").rstrip("/")
    key = prov.get("key", "")
    model = prov.get("model", "").strip().lower()  # 自动转小写（API模型名大小写敏感，全部小写是安全默认）

    if ptype == "ollama":
        return _chat_ollama(url, model, messages, temperature, timeout)
    elif ptype == "openai":
        return _chat_openai(url, key, model, messages, temperature, timeout)
    elif ptype == "anthropic":
        return _chat_anthropic(url, key, model, messages, temperature, timeout)
    else:
        raise ValueError(f"未知提供商类型: {ptype}")


_UA = "agentsec-labs/1.0"
_RETRY_DELAYS = [2, 5, 10]  # 重试等待秒数


def _urlopen_with_retry(req, timeout, retries=3):
    """带重试的 urlopen：网络断连时自动等待重试。"""
    last_err = None
    for i in range(retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError:
            raise  # HTTP 错误不重试（4xx/5xx 是服务端问题）
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            last_err = e
            if i < retries:
                delay = _RETRY_DELAYS[min(i, len(_RETRY_DELAYS)-1)]
                print(f"[providers] 连接断开，{delay}s 后重试 ({i+1}/{retries}): {e}")
                import time as _time
                _time.sleep(delay)
                # 重建 Request（旧的可能已被消费）
                req = urllib.request.Request(
                    req.full_url, data=req.data,
                    headers={k: v for k, v in req.header_items()})
            else:
                raise RuntimeError(
                    f"网络连接失败（已重试{retries}次）: {e}\n"
                    f"可能原因: ①API 被限流 ②网络不稳定 ③防火墙拦截。等 30 秒后再试。"
                ) from e


def _chat_ollama(base, model, messages, temp, timeout):
    payload = json.dumps({
        "model": model, "messages": messages, "stream": False,
        "options": {"temperature": temp},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/chat", data=payload,
        headers={"Content-Type": "application/json", "User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
            return resp.get("message", {}).get("content", "") or ""
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise RuntimeError(f"Ollama HTTP {e.code}: {e.reason} | {body}") from e


def _chat_openai(base, key, model, messages, temp, timeout):
    oai_msgs = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "tool":
            oai_msgs.append({"role": "user", "content": f"TOOL_RESULT: {content}\n\n请继续。"})
        else:
            oai_msgs.append({"role": role, "content": content})
    payload = json.dumps({
        "model": model, "messages": oai_msgs, "stream": False,
        "temperature": temp, "max_tokens": 2048,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}",
                 "User-Agent": _UA,
                 "Accept": "application/json"})
    try:
        with _urlopen_with_retry(req, timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
            return resp.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise RuntimeError(f"API HTTP {e.code}: {e.reason} | {body}") from e


def _chat_anthropic(base, key, model, messages, temp, timeout):
    system = ""
    chat_msgs = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system = content
        elif role == "tool":
            chat_msgs.append({"role": "user", "content": f"TOOL_RESULT: {content}\n\n请继续。"})
        else:
            chat_msgs.append({"role": role, "content": content})
    payload = json.dumps({
        "model": model, "messages": chat_msgs, "system": system,
        "max_tokens": 4096, "temperature": temp,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/messages", data=payload,
        headers={"Content-Type": "application/json",
                 "x-api-key": key,
                 "anthropic-version": "2023-06-01",
                 "User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
            texts = [b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"]
            return "".join(texts)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise RuntimeError(f"Anthropic HTTP {e.code}: {e.reason} | {body}") from e


# ---------- 连接测试 ----------
def get_timeout():
    """云端模型延迟更高，自动增加超时。"""
    _, prov = get_active()
    if prov.get("type", "ollama") == "ollama":
        return 300
    return 600  # 云端最多等10分钟

def test_connection(pid=None):
    """测试指定（或当前）提供商是否可用。"""
    if pid:
        cfg = load_config()
        prov = cfg.get("providers", {}).get(pid, {})
    else:
        _, prov = get_active()
    try:
        reply = chat([{"role": "user", "content": "回复OK"}], timeout=30)
        return {"ok": True, "reply": reply[:50]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
