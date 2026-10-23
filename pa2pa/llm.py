"""Minimal client for the local model server (scripts/serve.ps1). Standard library only.

    python -m pa2pa.llm              # smoke test: one short exchange
"""
import json
import urllib.request

SERVER = "http://127.0.0.1:8081"


def chat(messages, template_kwargs=None, temperature=0.7, seed=None, max_tokens=None, timeout=600):
    """One chat completion. Returns {"content", "reasoning", "usage"}.

    template_kwargs are variables of the model's chat template, which is where each model takes its thinking switch:
    Qwen3.5 {"enable_thinking": False}; gpt-oss {"reasoning_effort": "low" | "medium" | "high"}.
    """
    body = {"messages": messages, "temperature": temperature}
    if template_kwargs:
        body["chat_template_kwargs"] = template_kwargs
    if seed is not None:
        body["seed"] = seed
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(SERVER + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = json.load(res)
    message = data["choices"][0]["message"]
    return {"content": message.get("content") or "", "reasoning": message.get("reasoning_content") or "",
            "usage": data.get("usage", {})}


def model():
    """The name of the model the server is running (serve.ps1's -Model)."""
    with urllib.request.urlopen(SERVER + "/v1/models", timeout=5) as res:
        return json.load(res)["data"][0]["id"]


def ready():
    """Whether the server has loaded the model and takes requests."""
    try:
        with urllib.request.urlopen(SERVER + "/health", timeout=2) as res:
            return res.status == 200
    except OSError:
        return False


if __name__ == "__main__":
    if not ready():
        raise SystemExit(f"No server at {SERVER}; start it with scripts/serve.ps1")
    print("model:", model())
    reply = chat([{"role": "system", "content": "You are a seller of a used bicycle. Your floor is $120."},
                  {"role": "user", "content": "Would you take $90 for it?"}], seed=0)
    print("reasoning:", reply["reasoning"][:300])
    print("content:", reply["content"])
    print("usage:", reply["usage"])
