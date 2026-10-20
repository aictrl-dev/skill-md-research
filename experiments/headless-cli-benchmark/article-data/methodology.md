# Measurement notes

Measurements: 20 October 2026, six native released installations in one campaign (`results/seven-way-0.5.4.json`). The campaign also measured OpenCode 1.19.3 (v1); it is excluded from the article because upstream development is now v2-only, and its rows stay in the raw data.

## Environment and workload

- Host: AMD Ryzen 7 8700F, 8 cores / 16 logical CPUs, approximately 31 GiB RAM; Ubuntu 24.04.5, kernel 7.0.0-31, Docker 29.8.0, cgroup v2, overlay2. Other host workloads and shared caches were not controlled. Exact capture and base-image digests: `results/build-host.json`.
- Fresh non-root container and empty HOME/XDG directories per attempt; cached images, no clearing of host filesystem caches. Two-CPU quota, 2 GiB memory/swap limit, host networking. This measures fresh-container startup, not image pulls, cloud scheduling or cold host caches.
- aictrl 0.5.4, pi 1.3.0, Codex 0.163.0, OpenCode 2.1.0 (npm `@opencode/cli`), Hermes source tag v0.22.2 at d923a5eb487a17c0a68801bba9ef0f56c81040a8, Goose 1.55.0. Hermes' archive installation reports `vunknown`; the source commit, not that version string, establishes the pin.
- pi runs on Node 22; aictrl/Codex/OpenCode installations use the Node 20 base (native packaged executables may use their own embedded engine). Hermes core runs on Python 3.14.8. Goose uses its GNU native release and required native libraries. These are supported installation profiles, not a language experiment. See `build-images.json` for full versions, image IDs and footprints (`build-aictrl-0.5.4.json` and `build-opencode-v2.json` for the two images added on 20 October; every other image ID is unchanged from 19 October); Hermes realized dependencies are in `build-hermes-pip-freeze.txt`.
- Local scripted model, fixed 50 ms reply delay. Chat Completions for five contenders, Responses API for Codex. Fixture credentials only; no real-model inference. Standard OpenAI discovery endpoints return an immediate local model list, while alternative protocol probes return 404.
- Trivial: one answer. Short exploratory task: three reads. Long: fifty distinct paths, each containing the same 48,000-byte / 800-line fixture, followed by `Done.`. Distinct paths preserve native unchanged-file deduplication behavior while requiring actual reads. Tools are native file readers, or shell `cat` for Codex/Goose.
- Two discarded warmups per scenario, forward/reverse interleaving across repetitions. Startup has 20 measured attempts per contender. The long task has five measured attempts per contender. CLI/Docker exits, native completion events, expected request counts, final answer, tool errors and fixture delivery/retention are checked. A 180-second timeout is a failure, never a zero or replacement sample.

## One campaign, protocol version 3

Every scenario comes from one interleaved campaign with protocol version 3: a unique completion ID per HTTP response and current Unix creation time, consistent across chunks within that response. Earlier protocol versions reused completion IDs and are not used here. The runner is `harness/compare-v054.ts`. Its sources are archived in `campaign-source/`, with hashes in `results/seven-way-0.5.4-provenance.json`. All 20 startup and five long attempts completed for every contender, with no recorded failures, including warmups.

`article-data/sources/measurements.json` records source hashes, scenario lineage and attempt/completion counts. Summary memory quantiles use completed runs; always consult completion counts. The chart gold mark ranks the observed statistic, with no significance claim.

Startup medians shifted between campaigns: Goose, Codex, pi and Hermes, whose images are unchanged, measured 140 to 230 ms faster on 20 October than on 19 October. A separate paired startup run of aictrl 0.5.3, aictrl 0.5.4 and pi (`results/smoke-v054/paired-053-054-startup.json`, 20 attempts each) measured medians of 489, 503 and 460 ms. Cross-campaign comparisons of absolute startup times are therefore unreliable; compare within a campaign.

Response evidence distinguishes planned, body-created and handler-returning timestamps. Returning a buffered Response to Bun does not prove TCP delivery or client receipt. Do not infer transport success solely from the stub's planned response.

## Timing

Host monotonic clock starts immediately before spawning `docker run`. `firstRequest` is arrival of the first task request at the local stub. `firstResponse` is the host's receipt of a complete matching native JSONL event:

| Harness | First response predicate |
| --- | --- |
| aictrl / OpenCode | `text` or `tool_use` event (OpenCode 2.1.0 keeps this event shape in `run --format json`) |
| pi | Text/tool-call `message_update`, or `tool_execution_start` |
| Codex | Non-error, non-reasoning `item.started` or `item.completed` |
| Hermes | Nonempty `text` or `tool_use` |
| Goose | Assistant `message` containing text or `toolRequest` |

Lifecycle, initialization and thinking events are excluded. Event contracts differ on tool execution, so the headline uses the trivial text task. This is not universal model time to first token. `exitAt` observes CLI exit; raw `wall` additionally includes evidence-log writes, so neither `wall` nor version-command wall is published as pure startup/runtime.

Quantiles: sorted sample at `ceil(p*n)-1`. At n=20, median is the 10th ordered sample (lower middle), p90 the 18th. At n=5, median is the third and p90 the maximum. Connecting lines are not confidence intervals. Wide host tails and small samples limit stable ranking claims.

## Memory, context and footprint

- Cgroup `memory.peak` measures container-accounted memory in MiB (bytes / 2^20), including charged cache. Shared page-cache ownership can move the cost between containers. It is not process RSS.
- `/usr/bin/time` maximum RSS is the largest measured process, reported in KiB and converted by dividing by 1024. Separately, sampled summed RSS polls every 250 ms, can double-count shared pages and miss spikes. Both are preserved; they are not interchangeable with cgroup peak.
- For every read, ordered source-line coverage and explicit native error/truncation flags are checked in the next model request. Content hashes and start/end coverage are recorded; hashes are not compared with a canonical expected hash because native wrappers differ. All results are checked again in the final request. Full delivery and retention is `equivalent-content`; shortened/pruned results are labeled separately. Codex's native output cap leaves a substantially smaller final request: its memory result is a different retained-context workload.
- Stub usage is artificial (100 prompt tokens), so normal token-driven compaction is not exercised. This is neither a leak diagnosis nor a production-context memory prediction.
- Image increment is uncompressed local Docker image size minus the corresponding runtime base, including installation layers/dependencies. Bases differ. Installed package-directory bytes are a separate measure; neither quantity is compressed transfer size, executable size, build duration or pull latency. `build-images.json` records total/base/increment and installed sizes.
- First request sizes are real UTF-8 bytes (`Buffer.byteLength`), including instructions, tool schemas, messages and API serialization. UTF-16 string lengths are retained separately. Toolsets differ; bytes are not token counts or cost.

## Native configuration

Exact adapters and environment switches are in `harness/compare.ts`. Codex disables update checks/analytics/plugin sync and bypasses approval/sandbox/repository checks inside its fixture container. pi receives offline/version/telemetry switches. OpenCode runs `opencode run --standalone --auto --format json`: `--standalone` gives each container a private in-process server instead of the background service, and `--auto` approves permissions the config does not deny (the config already allows all). It receives the update and model-fetch switches its binary recognizes; the LSP-download switch carried over from the v1 adapter does not appear in the 2.1.0 binary and has no effect. These are configured headless installations, not untouched defaults or a sandbox-security comparison.

**Toolsets differ.** pi uses its four default tools (`read`, `bash`, `edit`, `write`) with an empty HOME, so no extensions, packages or subagent extension. Goose runs `--no-profile --with-builtin developer`: only the Developer extension, no recipes or sub-recipes. Hermes runs `--toolsets file,terminal`; its default enables 17 toolsets, including web, browser, memory, todo and delegation. aictrl, OpenCode 2.1.0 and Codex run their default tools, each including a subagent tool (`task`, `subagent`, `multi_agent_v1`). Token results favor the reduced configurations. A supplementary capture (`harness/token-capture-v054-minimal.ts`, `results/token-capture-0.5.4-minimal.json`, 5 + 5 sessions, 0 failures) runs aictrl 0.5.4 with `glob`, `grep`, `task`, `webfetch` and `skill` set to permission `deny`, which removes them from the request; a `tools: { name: false }` map was ignored in a probe. Its estimates are in `article-data/sources/token-estimates-aictrl-minimal.json`; it is not part of the medal tables.

Hermes enables native file/terminal tools, ignores user config/rules and uses its custom provider; it does not use the optional Codex runtime. Goose uses its own OpenAI provider and built-in Developer tools, ordinary session persistence, automatic permission mode, disabled session naming/telemetry and 100-step repetition/turn guards for the synthetic workload. It does not delegate through ACP. See the folder README for exact commands and validation semantics.

The scripted model fixes the tool sequence. It cannot establish natural model-turn efficiency, task quality, inference latency or total model cost. aictrl's batching guidance is a design choice; a direct real-model comparison and isolated batching ablation are still needed.

## Session calls, turnaround and token accounting

The scripted endpoint reports fixed dummy usage (100 input / 10 output tokens per call). These values are control inputs to the harness, not measured consumption, and never appear as token statistics. The script imposes 51 main calls; auxiliary requests are counted separately. Those counts do not measure natural task planning.

**Session time and its breakdown** (`article-data/sources/session-metrics.json`, built by `build.py` from the campaign's 50-read rows and request logs). Elapsed time is CLI `exitAt`, before log persistence. Each session is split using the stub's timestamps, aligned to the run clock through the first main request, which both clocks record:

- start-up: launch to the first main request;
- model: each main request's arrival to its handler returning the buffered response (the 50 ms delay plus serialization);
- harness work between turns: one main response returned to the next main request arriving. It includes response transfer and parsing, the tool call, and building the next request. Auxiliary calls are excluded from the gap series;
- shut-down: last main response returned to CLI exit.

Components are medians taken separately, so their sum approximates rather than equals the median session. Per-turn figures are the median and p90 of all 250 gaps (50 per session × 5).

**Token estimates** (`article-data/sources/token-estimates.json`). A separate capture campaign (`harness/token-capture-v054.ts`, generated from `compare-v054.ts` with request-body retention; `results/token-capture-0.5.4.json`) ran five single-response and five 50-read sessions per harness, no warmups, with the same images, limits and stub. All 60 attempts completed. Its timings and memory are not used. `harness/count_tokens.py` (tiktoken 0.12.0, `o200k_base` for every harness) tokenizes canonical compact sorted JSON of the model-facing request fields (instructions/messages/input/tools/response format), excluding model name, transport and stream settings. Outputs encode returned text or canonical JSON of the tool name and arguments. Repeated history is counted again on every request, and session sums include auxiliary calls. Results: `results/token-accounting-0.5.4.json`.

The first-request breakdown splits the first main request of each single-response capture into the system prompt (text of system/developer messages and any `instructions` field), tool definitions (canonical JSON of the `tools` array) and the remainder of the canonical count: task message, injected context (for example Codex's environment context) and JSON framing. System prompt and tool definitions were identical in all five captures for every harness. Codex's total varied by a few tokens through its environment context, so the remainder uses the median total.

These are reference-token estimates, not provider-reported input/output usage. API-specific framing, a different model tokenizer, prompt caching and reasoning change billing. Scripted output does not represent model-generated coding answers. Ground-truth usage, natural turn counts and task success require the same real model behind a logging proxy, preserving each request/response and its usage report, including cache and reasoning breakdowns. See [OpenAI's token-counting definitions](https://developers.openai.com/api/docs/guides/token-counting).

## Reproduction

After the campaign completes:

```bash
python3 build.py --source-dir .. --campaign ../results/seven-way-0.5.4.json \
  --tokens ../results/token-accounting-0.5.4.json \
  --tokens-minimal ../results/token-accounting-0.5.4-minimal.json
```

The token inputs come from:

```bash
HARNESSES=aictrl-npm-0.5.4,pi-1.3-node22,codex,opencode-v2,hermes,goose WARMUP=0 ONLY=trivial,long LONG_STEPS=50 \
  bun harness/token-capture-v054.ts results/token-capture-0.5.4.json 5 5 50
python3 harness/count_tokens.py results/token-capture-0.5.4.json results/token-accounting-0.5.4.json
```

The import step also reads the raw per-run logs, published as release archives; extract them into `results/` first. Subsequent `python3 build.py` rebuilds the chart PNG/SVG pairs, CSV and HTML from the saved numeric extract without containers or model calls. Requires matplotlib and Python-Markdown; `--tokens` also needs tiktoken. The folder README covers image builds and experiment commands.
