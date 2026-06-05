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

### opencode treatment (aictrl KG MCP) — WORKING

- **Auth header is `X-API-Key`, not `Authorization: Bearer`.** A plain bearer
  returns `401` + `www-authenticate` (which made opencode fall back to an
  un-completable OAuth flow). With `X-API-Key: <aictrl key>` the gateway
  (`https://aictrl.dev/aictrl/mcp`) returns `200` and `initialize` succeeds. The
  key is read from a gitignored `.env.local` (`AICTRL_MCP_TOKEN`) via opencode's
  `{env:…}` interpolation — no secret in git.
- opencode connects over StreamableHTTP (no OAuth) and exposes **6 tools**:
  `query_context` (the KG entry point), `update_backlog`, and four review-write
  tools (`record_review_started`, `record_finding`, `record_finding_verdict`,
  `record_review_completed`). The old "24 KG tools" figure is stale.
- **gemma4 calls the KG through opencode**: the treatment smoke shows gemma
  invoking `aictrl_query_context` (twice) before answering. Core bet confirmed at
  the integration level (it also emits tool calls natively, e.g.
  `get_callers({symbol:"computeRiskScore"})`).

### KG is populated for the aictrl code domain — risk #2 RESOLVED

Direct `query_context` calls return real, accurate data matching our task files:

| query | result |
|---|---|
| `code/search checkOrgMember` | `server/lib/authorization.ts` (fn, exported) — our module 205 |
| `code/search PullRequestManager` | methods in `server/services/pull-request-manager.ts` |
| `code/callers computeRiskScore` | defined `server/services/risk-scoring.ts:33` (task 101), **called by `runSecurityScan` @ `server/services/security-scanner.ts:224`** |

The cross-file caller data is exactly what the treatment condition needs. (Note:
`search` results have `lines:null`; `callers` include line numbers.)

### CRITICAL FINDING — gemma4 thinking swallows output; opencode can't disable it

Pilot reviews on real task files exposed a blocker and its fix:

- **With thinking ON (the only mode opencode gives), gemma returns nothing.**
  Reviewing module 205 (authorization, which contains a real privilege-escalation
  bug) via opencode took **127–236 s** and produced `[]` — gemma reasons at length
  in the hidden thinking channel, then emits an empty `content`. Setting
  `options.think:false` in the opencode model config does **not** help: opencode's
  openai-compatible `/v1` path forces reasoning on (still 235 s → `[]`).
- **With thinking OFF (native ollama `/api/chat`, `think:false`), gemma is a
  genuinely good reviewer.** The same 205 review took **11 s** and produced
  substantive findings — including line 308 *"checkOrgAdminBySession returns
  authorized:true when session.organizationId is missing → authorization
  bypass"*, **which is exactly the gold TRUE finding 205-C1.**

**opencode CANNOT disable thinking for this model — confirmed exhaustively.**
Three approaches all leave thinking on (review → `[]`, 150–300 s):
`options.think:false`, model-level `thinking:{type:disabled}`, and the schema's
real field model-level `reasoning:false`. Root cause is architectural: opencode
drives ollama over the **OpenAI-compatible `/v1`** endpoint, which has **no
thinking parameter** — ollama's `think` flag exists only on its **native
`/api/chat`**. `reasoning:false` only affects providers with native AI-SDK
reasoning (Anthropic/OpenAI), not the openai-compatible→ollama transport.

**Decision: drive ollama's native `/api/chat` (with `think:false`) directly,
not opencode.** Native chat supports `think:false` **and** tool-calling together.
Bonus: native `options.seed` gives reproducible per-rep seeds (better than
opencode's temperature-only variance). The runner therefore
becomes a thin native-ollama loop:
- **control:** `/api/chat` with `think:false`, no tools, inlined code → findings.
- **treatment:** same + `tools:[query_context]`; on a `tool_call`, POST to the
  aictrl MCP (`X-API-Key`) and feed the result back until gemma returns content.
- The opencode configs (`opencode-{control,treatment}.json`) and the `review`
  agent are kept as reference but are **not** the execution path. The reviewer
  prompt (`prompts/review.md`), `build-prompt.ts`, the findings parser, the
  scorer, and the registry are all unchanged.

### Design note (carried into the native runner)

- **Restrict the treatment agent to `query_context` only.** The MCP also exposes
  `record_*` write tools that mutate the *production* code-review store; the
  reviewer agent must not be able to call them. Configure opencode tool
  allow/deny (or a minimal custom agent) so only `query_context` (control: no MCP
  tools at all) is available, and so gemma can't wander into `record_finding`.
- gemma4 is a **thinking** model: reasoning lands in `reasoning_content`/​
  `message.thinking`; the findings parser must read the content channel.
