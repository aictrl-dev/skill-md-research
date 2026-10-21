# Same native candidate: default tools versus an explicit subset

On 21 October 2026, five native executions per arm completed the same scripted three-file Read task. Offering four tools instead of nine reduced cumulative reference input tokens from **15,150 to 9,390 (38.02%)**. These are offline token estimates over captured requests, including repeated history; they are not provider billing, coding-quality or speed measurements.

| Median reference tokens | Default | `--tools read,bash,edit,write` | Reduction |
|---|---:|---:|---:|
| First main input | 3,459 | 2,019 | 41.63% |
| Session input | 15,150 | 9,390 | 38.02% |
| Session output | 59 | 59 | 0% |
| Session total | 15,209 | 9,449 | 37.87% |

All five values within each arm equal the listed medians. There were no warmups, failed positive attempts or excluded positive samples. Default requests offered bash/read/glob/grep/edit/write/task/webfetch/skill; selected requests offered exactly bash/read/edit/write. The task needs Read only, so the result does not establish equivalent capability for other tasks.

## Protocol and retained evidence

The same native binary, non-GPT `fixture/fixture` model, permissive `{ "*": "allow" }` permissions, scripted 50ms provider delay, 2 CPU/2GiB limit and fresh non-root HOME were used in both arms. Arm order alternated. Every run exited 0 with four main requests, three ordered distinct actual Read executions (20 complete fixture lines each) and native final `Done`. All 40 request bodies and 30 Read executions were independently inspected. No auxiliary, discovery, other requests or retries occurred; the accounting retains main and auxiliary requests when present.

- [campaign.json](campaign.json): protocol, arm results, schema catalogs and 12 successful cleanup checks.
- [campaign-logs/](campaign-logs/): exact argv/config, native NDJSON/stderr, request records and gzip raw bodies.
- [reference-tokens.json](reference-tokens.json): tiktoken 0.12.0 / `o200k_base` accounting, using an isolated interpreter and preseeded decoder cache with socket connections blocked.
- [selector-comparison.json](selector-comparison.json): token deltas, acceptance result and campaign/accounting hashes.
- [candidate-inputs.json](candidate-inputs.json), [source](source-manifest.json), [generated](generated-manifest.json), [dependencies](dependencies-manifest.json), [build](build-manifest.json): bound native and build provenance. The four bound manifests were bundled after capture; all original 55 capture artifacts remained byte-for-byte unchanged.
- [adapter and rerun instructions](../../harness/selector246-README.md), [capture source](../../harness/token-capture-selector246.ts), [counter wrapper](../../harness/count_selector246.py). The historical canonical counter and all 89 previous benchmark files are unchanged.

## Candidate provenance and reproduction limits

This is an **unreleased candidate** for [CLI issue246](https://github.com/aictrl-dev/cli/issues/246), based on [guidance PR252](https://github.com/aictrl-dev/cli/pull/252). The executable was built from reviewed, pinned bytes **before** the feature commit was created. The source owner subsequently verified that the committed product files and README matched those reviewed bytes after normal commit/push hooks; this is a source-to-capture correspondence, not a claim that Git supplied the build input at compilation time.

Candidate source: [CLI commit `2db98b35f281a9b478082d915f451a326ce8ee5c`](https://github.com/aictrl-dev/cli/commit/2db98b35f281a9b478082d915f451a326ce8ee5c). Canonical build source: [`packages/cli/script/build.ts`](https://github.com/aictrl-dev/cli/blob/2db98b35f281a9b478082d915f451a326ce8ee5c/packages/cli/script/build.ts).

- Native version: `0.0.0-selector246-e807e4aacf5c`.
- Native SHA256: `c60d37a2d91de46abbbddccf10fdb0bb0c4940df9c2295ce42ba715344986874` (105,347,040 bytes).
- Local candidate image: `sha256:a8bd06679cfeed73feaee94f86b4e2c16c3913aaa86f5d1c36e61069dbede5be`.
- Frozen matching local base: `sha256:115e6dd65ebfb52349873367e6c80a3739e333314effc54293fb00a6b49e8978`.
- Compiler: Bun 1.4.3, canonical full Linux-x64-baseline build with `bun run packages/cli/script/build.ts --single`, `AICTRL_VERSION=0.0.0-selector246-e807e4aacf5c`, `AICTRL_CHANNEL=benchmark`, and `AICTRL_RELEASE` omitted. Offline build used copied frozen dependencies and compiler cache; no install, source regeneration, provider credentials or host HOME.

The build manifest preserves original local paths as provenance. This repository does **not** distribute the binary, source/dependency snapshot, private build driver, local image/base or complete original build environment. Their hashes are identifiers, not download URLs. Repeating the native capture requires constructing a compatible image and matching inputs; the captured data can be inspected independently. One successful build was performed; bit-identical rebuilds are unproven. The first build failed because staged `EVENTS.md` was missing, then succeeded after adding that exact tracked build input without changing product source.

## Additional local native failure checks

Separate fault-only instrumentation imported the unchanged capture runner and used the same real native image and Docker. These are QA controls, not positive samples. Their raw campaigns are retained locally and are not bundled in this positive-results directory.

| Fault | Observed rejection | Cleanup |
|---|---|---|
| Wrong catalog: actual `--tools read` where default catalog was expected | Native exited 0/Done; harness and counter rejected the missing catalog evidence | Exact-label final Docker query exited 0 with no containers |
| First actual Read targets a missing fixture | Native later exited 0/Done; harness and counter rejected missing Read0 evidence | Exact-label final Docker query exited 0 with no containers |
| Stub withholds responses | The real unchanged 180,000ms deadline expired; native exit 137 / timedOut true; harness exit 1 after 184.517 seconds including cleanup; counter rejected | Four retained cleanup entries plus independent final empty exact-label query |

Local fault audit SHA256: `d0311bab6fefd4f816e642306bce634703f0eb8a879dc39b82dac1c70cec7411`. Scoped TypeScript strict/noEmit and Python parsing checks passed; missing pin/hash, absent build cleanup and existing-output guards rejected their respective inputs. None of these checks establishes an OS egress sandbox. Capture retains the historical host-network/loopback-stub topology; selected Bash is not a sandbox. No paid model inference occurred. No quality, bill/cache savings, general speed improvement or release-readiness claim follows from this campaign.
