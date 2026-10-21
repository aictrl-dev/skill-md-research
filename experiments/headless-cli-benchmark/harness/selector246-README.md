# Same-candidate tool-selection capture

Executed on 21 October 2026: five fresh native runs per arm passed. The captured subset reduced cumulative reference input tokens by 38.02% on the scripted three-Read task. See the [actual campaign, source provenance and limitations](../results/selector246-20261021-actual-1/README.md). Existing benchmark source and all 89 historical benchmark files remain unchanged. This local measurement does not establish release readiness or close issue246.

This adapter compares one unmerged native candidate in two arms: default tools and `--tools read,bash,edit,write`. Both use the same permissive permissions, non-GPT `fixture/fixture` model, inert fixtures, scripted50ms latency, two CPUs and2GiB memory. Five repetitions per arm, alternating arm order, zero warmups; every repetition uses a fresh non-root container and HOME. This is offline reference-token evidence, not natural coding quality, billing/cache savings or a timing comparison against previous campaigns.

## Required candidate input

Do not copy or build the active source worktree until its owner releases the final tested source/generated/dependency pin. The private offline build driver verifies a complete separate snapshot, invokes the canonical full baseline build without installs/network and produces a new candidate image plus `candidate-inputs.json`:

```json
{
  "imageId": "sha256:<64-hex immutable candidate ID>",
  "matchingBaseId": "sha256:115e6dd65ebfb52349873367e6c80a3739e333314effc54293fb00a6b49e8978",
  "binaryPath": "/usr/local/bin/aictrl",
  "binarySha256": "<64-hex actual native binary SHA256>",
  "version": "0.0.0-selector246-<source manifest prefix>",
  "source": {"path": "source-manifest.json", "sha256": "<64-hex>"},
  "generated": {"path": "generated-manifest.json", "sha256": "<64-hex>"},
  "dependencies": {"path": "dependencies-manifest.json", "sha256": "<64-hex>"},
  "build": {"path": "build-manifest.json", "sha256": "<64-hex>"}
}
```

Paths resolve relative to the input JSON. All files must exist and hash correctly. The build manifest must bind image/binary/version/base and the three source pins, with `complete:true`. Candidate image preflight verifies frozen base layer ancestry, Linux amd64, runner/workspace identity, native version/hash, empty HOME, UID10001 and all55 exact fixture hashes. Released0.5.4 is not an acceptable candidate substitute.

## Repeating the capture

From `experiments/headless-cli-benchmark`, with an available candidate image and matching verified build inputs:

```bash
bun harness/token-capture-selector246.ts /owned/build/candidate-inputs.json results/selector246-NEW-CAMPAIGN
/owned/tokenizer-env/bin/python3 -I -B harness/count_selector246.py results/selector246-NEW-CAMPAIGN/campaign.json --cache /owned/verified-tiktoken-cache
```

The output directory must not exist. Use an explicitly pinned isolated interpreter with tiktoken0.12.0 and an explicit pre-seeded cache; isolated Python mode excludes the user site, so a package visible to ordinary `python3` may be unavailable to `python3 -I`. Record interpreter, dependency and decoder-cache hashes. Socket connection attempts fail. The wrapper invokes unchanged `count_tokens.py` canonical accounting and records first-main, cumulative session input/output/total estimates and deltas. Acceptance fails unless first-main input, total session input and session total all decrease. Every attempted session must succeed; failed/incomplete captures remain on disk and cannot be silently overwritten or excluded.

Raw native stdout/stderr, exact argv/config, all stub request records and gzip raw request bodies are retained. Four main requests must contain exactly the ordered three real Read results, each with20 complete fixture lines, and native final Done. Every selected main request must offer exactly bash/edit/read/write; the default must include those plus more tools. Auxiliary requests/retries/discovery are retained; token accounting includes every main/aux request and repeated history.

The runner retains the historical host-network/loopback-stub topology. It **does not impose OS egress isolation**, and selected Bash is not a sandbox. No host credentials/HOME are forwarded to the container; Docker's host process gets a fresh empty HOME and fixed PATH. Containers get fixed resource limits, ignored stdin, external deadline and exact-name cleanup. Verify cleanup/error handling in QA before treating the prepared adapter as exercised.

## Historical prepared validation (before native execution)

The initial preparation checked Bun TypeScript syntax transformation and Python AST parsing without executing the campaign/build modules. Native compilation, Docker capture, offline token counting, manifest guards and actual schema/Read/deadline fault checks subsequently passed; the campaign README records their scope. No dependencies are installed by these files.
