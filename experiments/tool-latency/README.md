# Tool Dispatch Latency Benchmark

Reproducible benchmark measuring tool call overhead across three AI coding CLIs: **Claude Code**, **OpenCode**, and **Gemini CLI**.

## Motivation

During our KG A/B experiment, we discovered that Claude Code adds ~4 seconds of overhead per tool call, while OpenCode completes the same local operations (grep, read, glob) in <10ms. This 100-1000x difference dominates the cost of MCP-assisted workflows. This benchmark isolates and quantifies tool dispatch latency as the root cause.

## CLIs Under Test

| CLI | Version | Model | Notes |
|-----|---------|-------|-------|
| Claude Code | 2.1.68 | Claude Sonnet 4 | `--dangerously-skip-permissions` |
| OpenCode | 1.2.15 | Claude Sonnet 4 | Same model as Claude Code |
| Gemini CLI | 0.29.7 | auto-gemini-3 | Different model (confound acknowledged) |

Claude Code and OpenCode use the same underlying model (Sonnet 4). Gemini uses its own model. Tool dispatch overhead should be model-independent since it happens after the LLM decision.

## Test Cases

| ID | Tool Type | Task | CLIs |
|----|-----------|------|------|
| T0 | none (calibration) | "What is 2+2?" | all |
| T1 | file_read_small | Read `tsconfig.json` (17 lines) | all |
| T2 | file_read_large | Read `server/state/types.ts` (~2900 lines) | all |
| T3 | grep | Search "StateManager" in `server/` | all |
| T4 | glob | Find `*.ts` in `server/mcp/` | all |
| T5 | bash_echo | `echo hello` | all |
| T6 | bash_ls | `ls -la server/mcp/` | all |
| T7 | mcp_search | KG code search "StateManager" | claude, opencode |
| T8 | mcp_read | KG code read `server/state/types.ts` | claude, opencode |

## Measurement Method

| CLI | Method | Precision |
|-----|--------|-----------|
| **OpenCode** | `part.state.time.{start,end}` epoch ms on each `tool_use` event | <1ms per-tool |
| **Gemini** | ISO timestamp diff between `functionCall` and `functionResponse` events | ~1ms per-tool |
| **Claude Code** | `duration_ms - duration_api_ms` from `result` event = session overhead | ~100ms session-level |

### Claude Code Caveat

Claude Code does not expose per-tool timestamps. We measure session-level overhead (`cli_overhead_ms = duration_ms - duration_api_ms`) and subtract a T0 calibration baseline (no tools) to estimate tool dispatch time. This is a **session-adjusted estimate**, not a direct measurement.

## Controls

- **3 runs** per test per CLI (configurable via `--runs`)
- **Interleaved execution**: T1-claude, T1-opencode, T1-gemini, T1-claude(r2)... to minimize temporal bias
- **5s cooldown** between runs
- **Same machine**: AMD Ryzen 7 8700F, 32GB RAM, Linux 6.17.0, NVMe SSD
- **Same codebase**: `kg-blog-update` (~30K LOC TypeScript)

## Reproduction

```bash
# Prerequisites
# - claude (Claude Code CLI) >= 2.1.x
# - opencode >= 1.2.x
# - gemini (Gemini CLI) >= 0.29.x
# - jq >= 1.6

# 1. Verify prompts
./run-benchmark.sh --dry-run

# 2. Pilot single test
./run-benchmark.sh --cli opencode --test T1 --runs 1
./run-benchmark.sh --cli gemini --test T1 --runs 1
./run-benchmark.sh --cli claude --test T1 --runs 1

# 3. Parse
bash parsers/parse-opencode.sh
bash parsers/parse-gemini.sh
bash parsers/parse-claude.sh

# 4. Full run
./run-benchmark.sh --runs 3

# 5. Re-parse and analyze
bash parsers/parse-opencode.sh
bash parsers/parse-gemini.sh
bash parsers/parse-claude.sh
bash analysis/analyze.sh
cat analysis/summary.csv
```

## Limitations

1. **Claude Code measurement granularity**: No per-tool timestamps; session-adjusted estimates only
2. **Gemini model confound**: Uses a different model than Claude Code/OpenCode; tool dispatch should be model-independent but LLM decision time differs
3. **MCP tests (T7-T8)**: Require a running MCP server; network latency is a confound vs. local tools
4. **Single machine**: Results may vary on different hardware/OS configurations
5. **CLI startup**: Each invocation includes process startup; this is realistic for how tools are used but adds noise

## System Specs

- **CPU**: AMD Ryzen 7 8700F (8 cores, 16 threads)
- **RAM**: 32GB DDR5
- **Storage**: NVMe SSD
- **OS**: Ubuntu 24.04, Linux 6.17.0
- **Node.js**: v22.x
