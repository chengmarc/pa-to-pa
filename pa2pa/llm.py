"""Minimal client for the local gpt-oss-20b server (scripts/serve.ps1). Standard library only.

    python scripts/llm.py            # smoke test: one short exchange
"""
import json
import urllib.request

SERVER = "http://127.0.0.1:8081"


def chat(messages, reasoning_effort="low", temperature=1.0, seed=None, max_tokens=None, timeout=600):
    """One chat completion. Returns {"content", "reasoning", "usage"}.

    reasoning_effort ("low" | "medium" | "high") is a variable of gpt-oss's chat template, so it goes in
    chat_template_kwargs rather than as an OpenAI parameter.
    """
    body = {
        "model": "gpt-oss-20b",
        "messages": messages,
        "temperature": temperature,
        "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
    }
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
    reply = chat([{"role": "system", "content": "You are a seller of a used bicycle. Your floor is $120."},
                  {"role": "user", "content": "Would you take $90 for it?"}], seed=0)
    print("reasoning:", reply["reasoning"][:300])
    print("content:", reply["content"])
    print("usage:", reply["usage"])
