"""Minimal client for the models in models.json: local llama-servers (python pa-to-pa.pyw serve) or hosted
OpenAI-compatible APIs. Standard library only."""
import json
import os
import urllib.request

from .paths import SRC


def models():
    """models.json: {name: {label, url, template_kwargs, [api_key_env, model], [local], [slot]}}."""
    data = json.loads((SRC / "models.json").read_text(encoding="utf-8"))
    return {name: m for name, m in data.items() if not name.startswith("_")}


def _request(model, path, body=None, timeout=600):
    m = models()[model]
    headers = {"Content-Type": "application/json"}
    if m.get("api_key_env"):
        headers["Authorization"] = "Bearer " + os.environ.get(m["api_key_env"], "")
    req = urllib.request.Request(m["url"] + path, data=body and json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.load(res)


def chat(model, messages, temperature=0.7, seed=None, max_tokens=None, timeout=600):
    """One chat completion from the named model. Returns {"content", "reasoning", "usage"}.
    The model's template_kwargs (e.g. Qwen3.5's enable_thinking) go with every request."""
    m = models()[model]
    body = {"model": m.get("model", model), "messages": messages, "temperature": temperature}
    if m.get("template_kwargs"):
        body["chat_template_kwargs"] = m["template_kwargs"]
    if seed is not None:
        body["seed"] = seed
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    data = _request(model, "/chat/completions", body, timeout)
    message = data["choices"][0]["message"]
    return {"content": message.get("content") or "", "reasoning": message.get("reasoning_content") or "",
            "usage": data.get("usage", {})}


def label(model):
    """The model's name on the page: its label in models.json, else its id."""
    return models().get(model, {}).get("label", model)


def why_not(model):
    """Why the named model can't take requests right now, or None if it can: a slot isn't set up yet; a hosted API
    needs its key set; a local server must have loaded it."""
    m = models().get(model)
    if m is None:
        return f"{model} isn't in models.json"
    if m.get("slot"):
        return m["slot"]
    if m.get("api_key_env"):
        return None if os.environ.get(m["api_key_env"]) else f"Set {m['api_key_env']} to its API key."
    try:
        _request(model, "/models", timeout=2)
        return None
    except OSError:
        return (f"Not running yet: it loads about 10 s after launch (log: logs/server-{model}.log). "
                f"To start it by hand: python pa-to-pa.pyw serve {model}")


def ready(model):
    return why_not(model) is None

