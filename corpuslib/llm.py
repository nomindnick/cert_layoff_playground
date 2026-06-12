"""LLM access for prototypes: local ollama only.

There is deliberately NO cloud backend here. `claude -p` shell calls bill at
API rates (not the subscription), so code never calls Claude directly. When
cloud-model help is wanted (e.g. the GPU is occupied by a corpus run), the
pattern is **subagent fan-out, orchestrated by the main Claude Code session**:
code writes batch input files (the data a prompt would inject), the session
spawns Agent-tool subagents to process them, subagents write output files,
code validates and merges. See cert_layoff_lab's annotate_summary.py
(--skeleton / --merge) for the worked example of this pattern. A
subagent-produced result validates the IDEA, not local-model feasibility --
FINDINGS must record which backend ran.

Before heavy local runs, check what's already on the GPU (gpu_status()):
a corpus extraction run will be swallowing most of it.
"""

import json
import urllib.request

OLLAMA_BASE = "http://localhost:11434"


def generate(backend, prompt, system=None, json_schema=None, num_ctx=None, timeout=1800):
    """Return the model's text completion (or parsed object if json_schema given).

    backend: "ollama:<model>" (the prefix is kept so FINDINGS/logs are explicit
    about provenance, and so a different runtime could be added later).
    """
    kind, _, model = backend.partition(":")
    if kind != "ollama":
        raise ValueError(f"unknown backend {backend!r} (only ollama:<model> is supported)")
    options = {}
    # Lesson (lab REFINEMENTS #1): never let a fixed context budget silently
    # truncate an outlier-length prompt.
    est_tokens = len(prompt) // 3 + 1024
    options["num_ctx"] = max(num_ctx or 0, 16384, est_tokens + 4096)
    body = {"model": model, "prompt": prompt, "stream": False, "options": options}
    if system:
        body["system"] = system
    if json_schema:
        body["format"] = json_schema
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.loads(resp.read())
    text = out["response"]
    return json.loads(text) if json_schema else text


def gpu_status():
    """Models currently resident on the GPU, per ollama. Check before heavy runs."""
    with urllib.request.urlopen(f"{OLLAMA_BASE}/api/ps", timeout=10) as resp:
        models = json.loads(resp.read()).get("models", [])
    return [
        {
            "model": m.get("name"),
            "size_gb": round(m.get("size", 0) / 1e9, 1),
            "until": m.get("expires_at"),
        }
        for m in models
    ]
