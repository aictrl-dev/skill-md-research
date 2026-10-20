# Headless coding-agent CLI benchmark

This folder holds the runner, data and charts behind the article
[Which coding-agent CLI is best for headless workflow automation?](https://aictrl.dev/blog/headless-coding-agent-cli-benchmark).

It measures the overhead a coding-agent CLI adds when a workflow starts it in a fresh container for every job:

- start-up to the first response
- harness time between model turns
- peak memory over a 50-read session
- image footprint
- tokens sent: system prompt, tool definitions, first request and the whole session

A local scripted model replies after a fixed 50 ms, so the numbers measure each CLI, not a model. This benchmark does not measure task quality or how many turns a real model takes.

**Measured 20 October 2026:**

| CLI | Version |
| --- | --- |
| aictrl | `@aictrl/cli` 0.5.4 |
| pi | `@earendil-works/pi-coding-agent` 1.3.0 |
| Codex | `@openai/codex` 0.163.0 |
| OpenCode | `@opencode/cli` 2.1.0 |
| Hermes Agent | v0.22.2 |
| Goose | 1.55.0 |

## Contents

| Path | What it is |
| --- | --- |
| `harness/compare-v054.ts` | Campaign runner: fresh `docker run` per attempt, interleaved order, discarded warmups, validation of every request and result |
| `harness/stub.ts` | Scripted OpenAI-compatible model (Chat Completions and Responses API) that timestamps every request |
| `harness/token-capture-v054.ts`, `token-stub.ts` | Separate capture campaign that keeps request bodies for offline token counting |
| `harness/token-capture-v054-minimal.ts` | The same capture with aictrl restricted to pi's four tools |
| `harness/count_tokens.py` | Reference token counts with tiktoken `o200k_base` |
| `harness/build-images.sh`, `footprint.sh` | Image builds and footprint records |
| `harness/build-aictrl-0.5.4.sh` | Our build of the aictrl 0.5.4 image. It checks image IDs against the recorded ones, so it only runs on the original host |
| `docker/` | Dockerfiles for the base images and each CLI |
| `campaign-source/` | Exact runner sources used by the 20 October campaign; hashes are in `results/seven-way-0.5.4-provenance.json` |
| `results/` | Campaign results, token captures and counts, build and host records |
| `article-data/` | The article's extracted measurements, session and token metrics, CSV, charts, `build.py` and `methodology.md` |

The campaign file `results/seven-way-0.5.4.json` also contains OpenCode 1.19.3 (v1). The article leaves v1 out because upstream development is v2-only. `results/build-images.json` records every image built for the benchmark, including earlier versions.

Raw per-run logs (stdout, stderr and per-request timing; about 270 MB per campaign) are attached to a GitHub release, not stored in git.

## Reproduce

You need Docker, Bun and Python 3 with `tiktoken` and `matplotlib`.

```bash
# Images: base images and the pinned comparators, then aictrl 0.5.4 and OpenCode 2.1.0
harness/build-images.sh pi-1.3-node22 codex hermes goose
for pkg in aictrl-npm-0.5.4=@aictrl/cli@0.5.4 opencode-v2=@opencode/cli@2.1.0; do
  docker build -t aictrl-harness-bench:${pkg%%=*} --build-arg BASE=aictrl-harness-bench:base \
    --build-arg PKG=${pkg#*=} -f docker/npm.Dockerfile docker
done

# Performance campaign: 20 single-response and 5 fifty-read attempts per CLI
HARNESSES=aictrl-npm-0.5.4,pi-1.3-node22,codex,opencode-v2,hermes,goose \
  WARMUP=2 ONLY=version,trivial,short,long LONG_STEPS=50 \
  bun harness/compare-v054.ts results/my-campaign.json 20 5 50

# Token capture and reference counts
HARNESSES=aictrl-npm-0.5.4,pi-1.3-node22,codex,opencode-v2,hermes,goose \
  WARMUP=0 ONLY=trivial,long LONG_STEPS=50 \
  bun harness/token-capture-v054.ts results/my-tokens.json 5 5 50
python3 harness/count_tokens.py results/my-tokens.json results/my-token-counts.json

# Tests for the validation rules
bun test harness/validation.test.ts
```

`article-data/methodology.md` defines every metric, the quantile rule and each CLI's configuration. Note in particular that pi, Goose and Hermes ran with reduced toolsets, while aictrl, OpenCode and Codex ran with their default tools.

Absolute start-up times move between campaigns on a shared host, so compare them only within one campaign.

## Disclosure

aictrl builds one of the measured CLIs.

## Licence

- Code (`harness/`, `docker/`, `campaign-source/`, `article-data/build.py`): MIT, see [`LICENSE`](LICENSE).
- Data, charts and text (`results/`, `article-data/` except `build.py`, this README): CC BY 4.0, see [`LICENSE-DATA`](LICENSE-DATA).
