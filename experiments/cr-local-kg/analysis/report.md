# cr-local-kg — Results & Findings

## Feasibility (Tasks 2–3)

Headless `opencode` → local `ollama` → `gemma4` is **working for the control
condition**. The treatment (KG) condition is blocked on an MCP credential.

### Hardware / model

- **GPU:** RTX 5070, 12 GB VRAM. System: 31 GB RAM (~8 GB free).
- **The `gemma4:12b-96k` tag is impractical here.** Loaded at its default
  128k–256k context, gemma4 spills to an **86% CPU / 14% GPU** split (KV cache
  doesn't fit 12 GB) → ~1–3 tok/s, and a single short request exceeded a 180s
  timeout. The 96k-context variant has the same problem.
- **Fix — `gemma4:12b-cr` (num_ctx 65536).** Created via Modelfile
  (`FROM gemma4:12b` + `PARAMETER num_ctx 65536`, temperature 0.7). Loads at
  **8.1 GB model / ~10.3 GB total VRAM, 100% GPU** (1.4 GB free), and runs at
  **~60 tok/s generation / ~511 tok/s prompt eval** warm. Tested 32k → 64k:
  identical speed and model size (gemma's sliding-window + flash-attn keep the
  KV cache tiny; ollama pre-allocates the full 64k KV at load, so VRAM is
  steady-state). 64k chosen over 32k for treatment-context headroom (largest
  module ≈1.5k LOC ≈ ~20k tokens + system prompt + 24 KG tool defs + reasoning +
  tool results across turns). **96k still spills to CPU** — 64k is the max
  context that stays fully GPU-resident on 12 GB. Retains `tools` + `thinking`.
- **Cold load ≈ 160s; warm step ≈ 7s.** Early opencode "hangs" were the model
  being **evicted between sparse calls and cold-loading past the timeout**, not
  an opencode bug. During a back-to-back sweep the model stays warm; we also pin
  it with a `keep_alive: -1` warmup before sweeps (`ollama ps` → `Forever`).

### opencode integration (control) — WORKING

- Provider config: a custom `ollama` provider (`npm: @ai-sdk/openai-compatible`,
  which opencode ships **bundled** — no install) pointing at
  `http://localhost:11434/v1`, model `gemma4:12b-cr` with `tools: true`.
  `OPENCODE_CONFIG=opencode-control.json opencode run --format json --model
  ollama/gemma4:12b-cr --dir <scratch> "..."` returns the assistant text
  (verified: prompt "Reply OK" → `OK`, LLM step ~6.8s warm).
- **Run with `--dir` = a small empty scratch dir, NOT the repo.** opencode
  snapshots/​watches its working dir at startup; pointing it at the big
  `skill-md-research` tree stalled it. We don't need the repo as a working dir —
  `build-prompt.ts` inlines file contents into the prompt, and the KG is a
  *remote* MCP. (Implication for the plan: `run-condition.sh` should use a
  scratch `--dir`, not the pinned repo.)
- gemma4 is a **thinking** model: reasoning lands in `reasoning_content` (`/v1`)
  / `message.thinking` (native). The final answer still arrives as normal
  content; the findings parser should read the content channel, not reasoning.

### opencode treatment (aictrl KG MCP) — BLOCKED on auth

- opencode connects to `https://aictrl.dev/aictrl/mcp` but the server returns
  **`401` with `www-authenticate: Bearer resource="…session-control…/mcp"`** —
  the hardcoded token reused from `kg-ab-test/opencode-treatment.json` is no
  longer accepted. opencode then initiates an **OAuth** flow (dynamic client
  registration → browser redirect to `aictrl.dev/oauth/authorize`), which cannot
  complete in a headless run, so the KG tools never attach and gemma answers
  without `query_context`.
- **Resolution is a credential decision (see below).** Everything else in the
  treatment path is identical to the working control path.

### Tool-calling (the core bet) — VALIDATED at the model level

- Independent of the MCP-auth issue, gemma4 **does emit tool calls.** Native
  `/api/chat` with a function definition produced a correct
  `tool_call: get_callers({symbol:"computeRiskScore"})`. So once a KG MCP is
  attached, gemma is capable of driving it. (Whether a 12B model uses 24 KG
  tools *well* across real reviews is the experiment's actual question.)

### Open decision — how to authenticate the treatment KG MCP

1. **Fresh static bearer / API key** that the aictrl MCP accepts directly →
   drop into `opencode-treatment.json`, zero further setup.
2. **Complete the OAuth flow once interactively**, let opencode cache the token,
   then run the sweep headless against the production KG.
3. **Local aictrl backend + Neo4j** (cr-loop style, `X-Executor-Secret` header,
   no OAuth) — most control/reproducibility, heaviest setup, and the KG must be
   indexed for the pinned commit `6b6bb39b`.
