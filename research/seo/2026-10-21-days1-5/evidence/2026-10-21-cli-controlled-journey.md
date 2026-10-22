# Controlled content → CLI setup check — 21 October 2026

**PASS for installing and starting the pinned CLI; real provider execution and acquisition measurement remain unverified.** The SWE-EVO article's primary CTA leads to `/agent#quickstart`, a standalone CLI path. It does not require visiting the application signup page to install the CLI or reach its help/preflight commands.

This internally controlled check is excluded from qualified-visitor/conversion conclusions. No real provider call, accepted model result, repository change, application account, cloud executor start, or signup/identity/consent verification is established here.

## Published artifact and isolation

Read `website/public/agent.html` lines 1223–1320. Its GitHub Actions example pins `@aictrl/cli@0.5.4`; the terminal example currently uses an unpinned install and requires a provider key and `provider/model` selection. This check deliberately exercised the pinned release.

- Disposable directory: `/tmp/aictrl-seo-cli-journey-20261021-XNak0a`.
- Node `v20.20.2`, npm `10.8.2`, Linux x64/glibc.
- npm used an empty environment, explicit public registry, empty task-specific user/global npmrc files, and a task-specific cache. Installation was local to `install/`, with lifecycle scripts disabled; no global or shared installation changed.
- CLI invocations used an empty environment with `PATH=/usr/bin:/bin`, task-specific `AICTRL_TEST_HOME` and all four XDG storage directories, and `AICTRL_DISABLE_PROJECT_CONFIG=true`. No existing provider key, auth file, or application credential was supplied.
- A small task-local seccomp launcher denied `socket` and `connect` syscalls for the CLI process tree. `strace -f -e trace=%file,%network` verified no host-home or `auth.json` path references during the four recorded invocations. Each trace contained two denied AF_UNIX socket attempts and no successful network operation. Configuration/cache files were confined to the disposable paths.
- Bubblewrap namespace isolation was unavailable (`Operation not permitted` / UID-map denial), so it was not counted as isolation evidence; the source-supported path overrides, cleared environment, seccomp filter, and actual traces were used instead.

## Commands and results

The npm prefix below is the exact option set used for the three npm commands; `journey_dir` denotes the disposable directory above:

```bash
/usr/bin/env -i PATH=/usr/bin:/bin npm \
  --userconfig "$journey_dir/user.npmrc" \
  --globalconfig "$journey_dir/global.npmrc" \
  --cache "$journey_dir/npm-cache" \
  --registry https://registry.npmjs.org \
  <arguments below>
```

| Arguments / command | Exit | Observed result |
| --- | ---: | --- |
| `view @aictrl/cli@0.5.4 name version bin engines scripts dependencies optionalDependencies dist repository gitHead --json` | 0 | Registry version 0.5.4, public repository `https://github.com/aictrl-dev/cli`, wrapper plus platform-specific optional packages. |
| `install --prefix "$journey_dir/install" --ignore-scripts --no-audit --no-fund @aictrl/cli@0.5.4` | 0 | Two packages installed: wrapper and `@aictrl/cli-linux-x64-baseline`, both 0.5.4. |
| `audit signatures --prefix "$journey_dir/install"` | 0 | **Two verified registry signatures and two verified attestations.** Registry declares SLSA v1 provenance. |
| `strace -f -e trace=%file,%network -o "$journey_dir/version.trace" "$journey_dir/run-isolated.sh" --version` | 0 | `0.5.4`. |
| Same traced launcher with `--help` | 0 | Supported command catalog, including `aictrl run [message..]`. |
| Same traced launcher with `run --help` | 0 | Confirms `--model`, `--format json`, `--output-schema`, `--output-schema-retries`, `--output-result`, `--dir`, and `--skill`. |
| Same traced launcher with `run --format json --model anthropic/test --output-schema invalid.schema.json 'Controlled validation only'` | **2, expected** | Schema `{ "type": "array" }` rejected with `OUTPUT_SCHEMA_CONFIG`: root must have type `object`. No model setup/request occurred. |

The invalid-schema check was run from the disposable `work/` directory. The bundled `src/cli/cmd/run.ts` validates the output schema before its provider/session bootstrap; `src/session/output-schema.ts` enforces the object root. Its local JSON stdout contained invocation-start/error/complete diagnostics for a validation failure. These are **local CLI diagnostics**, not an analytics capture or evidence of a model/executor run. No analytics destination, event definition, setting, or identity mapping was changed.

Registry tarball integrity values matched the installed lockfile; npm's signature/attestation verification covered both installed packages:

```text
@aictrl/cli@0.5.4
sha512-fhWgMKwLYXYPtS5uZu6Yy1iPVkkhChdvI8vfUA26KsAfjNYV6+cLDXovSaWdFArS+mC+fHiJrHrkyZCx2kSBIg==

@aictrl/cli-linux-x64-baseline@0.5.4
sha512-YckvmwTV/+lJxB3wZMmXkroj6XWYqSS/PuNOAyD7RudiqSUV4zE5WuQJ6JKAUmQb7PzVmJpY22V/4WNYrl6ydA==

Installed native binary SHA-256:
f12a54259ae0d77d85fd6d0cfefe1dcc742b95a617ca71e48f4fdfb2575182ee
```

These are public package integrity identifiers, not credentials. The registry tarball is [cli-0.5.4.tgz](https://registry.npmjs.org/@aictrl/cli/-/cli-0.5.4.tgz); its [provenance endpoint](https://registry.npmjs.org/-/npm/v1/attestations/@aictrl%2fcli@0.5.4) is listed in the registry metadata.

## Supported path and remaining break

The installed README and the native package's bundled source map confirm the documented `aictrl run` command and provider/model selection. Provider credentials come from the selected provider's environment variables or its own credential store. The inspected standalone startup/run path contains no application-signup gate. Actual model use still needs valid provider access and a supported model; neither was exercised.

Permissions in the Actions example are **configuration**, not a `--permission` CLI flag: `AICTRL_CONFIG_CONTENT` accepts `permission` rules, including the documented deny-all rule with explicit `read`, `glob`, and `grep` exceptions. The bundled source also supports `AICTRL_DISABLE_PROJECT_CONFIG` and `AICTRL_MODEL_STREAM_IDLE_TIMEOUT_MS`. Help/startup validation proves these interfaces exist; it does not prove a real model run obeyed a particular tool policy.

The terminal example's `findings.schema.json` is a user-supplied input: the README requires an object-root JSON Schema, and a successful structured result requires the model to produce a validating file. The controlled rejection confirms the configuration failure is surfaced before a request; it is not a successful findings result.

The verified path stops at **installed CLI → startup/help → deterministic configuration rejection**. Remaining requirements are a separately authorized controlled provider run with scoped credentials, a concrete successful result and checks, and a defined way to measure attributable qualified CLI adoption under the current telemetry/consent policy. A page visit, package download, this internal installation, app signup, and cloud executor activation are different observations. None can be substituted for another or counted as a qualified visitor/conversion from this check.

All task-local metadata, logs, extracted bundled sources, launcher source/binary and syscall traces remain under the disposable directory. Relevant files: `registry-metadata.json`, `install.log`, `signatures.log`, `version.log`, `help.log`, `run-help.log`, `schema-invalid.log`, `trace-summary.json`, `run-isolated.sh`, `no-network.c`, and the four `.trace` files. No repository source or existing evidence report was modified. This report remains uncommitted for the parent to bundle with account evidence.
