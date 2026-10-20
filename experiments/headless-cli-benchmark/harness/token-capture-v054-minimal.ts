// Generated from token-capture-v054.ts: aictrl 0.5.4 with a reduced toolset (read, bash, edit, write), to match pi's default tools.
/**
 * Six released CLI harnesses, cached-image fresh-container startup benchmark.
 *
 * Every repetition is a fresh `docker run --rm` of ${IMAGE_PREFIX}:<harness> (harness/build-images.sh):
 * runtime-specific minimal Debian bases, a non-root user with an empty HOME, the same CPU/memory limits, --network host.
 * A scripted stub (harness/stub.ts) on the host answers chat-completions and Responses API
 * requests after a fixed latency and timestamps each one. Times are host-clock ms from just
 * before `docker run`. Harnesses are interleaved rep by rep; WARMUP reps are discarded.
 *
 *   bun harness/compare.ts results/<name>.json [reps=15] [longReps=5] [latencyMs=50]
 *   python3 -I harness/table.py results/<name>.json
 *
 * Env: HARNESSES=aictrl-npm,pi-1.3-node22,codex,opencode,hermes,goose  ONLY=version,trivial,short,long,net
 *      LONG_STEPS=50  CPUS=2  MEMORY=2g
 */
import fs from "fs"
import path from "path"
import { gzipSync } from "node:zlib"
import { MARKER, PROTOCOL_VERSION, Stub, type Req, type Scenario } from "./token-stub"

const ROOT = path.resolve(import.meta.dir, "..")
const OUT = process.argv[2] ?? path.join(ROOT, "results", "compare.json")
const REPS = Number(process.env.REPS ?? process.argv[3] ?? 20)
const LONG_REPS = Number(process.env.LONG_REPS ?? process.argv[4] ?? 5)
const LATENCY = Number(process.argv[5] ?? 50)
const WARMUP = Number(process.env.WARMUP ?? 2)
const LONG_STEPS = Number(process.env.LONG_STEPS ?? 50)
const CPUS = process.env.CPUS ?? "2"
const MEMORY = process.env.MEMORY ?? "2g"
const ONLY = process.env.ONLY?.split(",")
const IMAGE_PREFIX = process.env.IMAGE_PREFIX ?? "aictrl-harness-bench"
const TIMEOUT_MS = Number(process.env.TIMEOUT_MS ?? 180_000)
const LOG_DIR = OUT.replace(/\.json$/, "") + "-logs"
const CAMPAIGN = `hbench-${process.pid}-${Date.now()}`
let runIndex = 0

for (const [label, value, minimum] of [["REPS", REPS, 1], ["LONG_REPS", LONG_REPS, 1], ["LONG_STEPS", LONG_STEPS, 1], ["WARMUP", WARMUP, 0], ["LATENCY", LATENCY, 0], ["TIMEOUT_MS", TIMEOUT_MS, 1]] as const) {
  if (!Number.isSafeInteger(value) || value < minimum) throw new Error(`${label} must be an integer >= ${minimum}`)
}
if (ONLY?.some((s) => !["version", "trivial", "short", "long", "net"].includes(s))) throw new Error(`Unknown ONLY scenario: ${ONLY}`)

const stub = new Stub(LATENCY)
// Capture-only campaign: retain local fixture requests for offline reference tokenization.
// Never use capture campaign timing or memory to replace the frozen earlier datasets.
stub.keepBodies = true
stub.longSteps = LONG_STEPS
const BASE_URL = `http://127.0.0.1:${stub.port}/v1`

// ---- harness definitions ----------------------------------------------------------------
type Event = Record<string, any>
type Harness = {
  name: string
  image: string
  argv: (prompt: string) => string[]
  version: string[]
  env: Record<string, string>
  /** Env vars that only switch off update checks / telemetry / catalog fetches. */
  phoneHomeOff: string[]
  files: { path: string; content: string }[]
  /** Config files with the phone-home switches removed (defaults run), when they live in a file. */
  defaultsFiles?: { path: string; content: string }[]
  /** First assistant output in the JSON stream: text or a tool call. */
  isResponse: (e: Event) => boolean
}

const opencodeStyleConfig = {
  provider: {
    fixture: {
      npm: "@ai-sdk/openai-compatible",
      options: { apiKey: "fixture", baseURL: BASE_URL },
      models: { fixture: { name: "fixture", tool_call: true, limit: { context: 200_000, output: 1000 } } },
    },
  },
  permission: { "*": "allow" },
}
const opencodeStyleResponse = (e: Event) => e.type === "text" || e.type === "tool_use"

const aictrl = (name: string): Harness => ({
  name,
  image: `${IMAGE_PREFIX}:${name}`,
  argv: (prompt) => ["aictrl", "run", "--format", "json", "--model", "fixture/fixture", prompt],
  version: ["aictrl", "--version"],
  env: { AICTRL_CONFIG_CONTENT: JSON.stringify(opencodeStyleConfig) },
  phoneHomeOff: [],
  files: [],
  isResponse: opencodeStyleResponse,
})

/** Codex config; `quiet` adds the switches for update checks, analytics and the curated-plugin sync. */
function codexConfig(quiet: boolean) {
  const lines = [`model = "fixture"`, `model_provider = "fixture"`]
  if (quiet) lines.push(`check_for_update_on_startup = false`, ``, `[analytics]`, `enabled = false`, ``, `[features]`, `plugins = false`)
  lines.push(``, `[model_providers.fixture]`, `name = "fixture"`, `base_url = "${BASE_URL}"`, `wire_api = "responses"`, `env_key = "FIXTURE_API_KEY"`, ``)
  return lines.join("\n")
}

const PI_OUTPUT = new Set(["text_start", "text_delta", "text_end", "toolcall_start", "toolcall_delta", "toolcall_end"])

const HARNESSES: Record<string, Harness> = {
  "aictrl-main": aictrl("aictrl-main"),
  "aictrl-npm": aictrl("aictrl-npm"),
  pi: {
    name: "pi",
    image: `${IMAGE_PREFIX}:pi`,
    argv: (prompt) => ["pi", "--mode", "json", "--model", "fixture/fixture", prompt],
    version: ["pi", "--version"],
    env: { PI_OFFLINE: "1", PI_SKIP_VERSION_CHECK: "1", PI_TELEMETRY: "0" },
    phoneHomeOff: ["PI_OFFLINE", "PI_SKIP_VERSION_CHECK", "PI_TELEMETRY"],
    files: [
      {
        path: "/home/runner/.pi/agent/models.json",
        content: JSON.stringify({
          providers: {
            fixture: {
              baseUrl: BASE_URL,
              api: "openai-completions",
              apiKey: "fixture",
              models: [{ id: "fixture", name: "fixture", contextWindow: 200_000, maxTokens: 1000 }],
            },
          },
        }),
      },
    ],
    isResponse: (e) =>
      (e.type === "message_update" && PI_OUTPUT.has(e.assistantMessageEvent?.type)) || e.type === "tool_execution_start",
  },
  codex: {
    name: "codex",
    image: `${IMAGE_PREFIX}:codex`,
    argv: (prompt) => ["codex", "exec", "--json", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check", prompt],
    version: ["codex", "--version"],
    env: { FIXTURE_API_KEY: "fixture" },
    phoneHomeOff: ["check_for_update_on_startup", "analytics.enabled", "features.plugins"],
    files: [{ path: "/home/runner/.codex/config.toml", content: codexConfig(true) }],
    defaultsFiles: [{ path: "/home/runner/.codex/config.toml", content: codexConfig(false) }],
    isResponse: (e) => (e.type === "item.started" || e.type === "item.completed") && e.item?.type !== "error" && e.item?.type !== "reasoning",
  },
  opencode: {
    name: "opencode",
    image: `${IMAGE_PREFIX}:opencode`,
    argv: (prompt) => ["opencode", "run", "--format", "json", "--model", "fixture/fixture", prompt],
    version: ["opencode", "--version"],
    env: {
      OPENCODE_CONFIG_CONTENT: JSON.stringify(opencodeStyleConfig),
      OPENCODE_DISABLE_AUTOUPDATE: "1",
      OPENCODE_DISABLE_MODELS_FETCH: "1",
      OPENCODE_DISABLE_LSP_DOWNLOAD: "1",
    },
    phoneHomeOff: ["OPENCODE_DISABLE_AUTOUPDATE", "OPENCODE_DISABLE_MODELS_FETCH", "OPENCODE_DISABLE_LSP_DOWNLOAD"],
    files: [],
    isResponse: opencodeStyleResponse,
  },
}
// Pi 1.3 is the released Node 22 comparator; diagnostic/private branches are excluded.
HARNESSES["pi-1.3-node22"] = { ...HARNESSES.pi, name: "pi-1.3-node22", image: `${IMAGE_PREFIX}:pi-1.3-node22` }
HARNESSES.hermes = {
  name: "hermes", image: `${IMAGE_PREFIX}:hermes`,
  argv: (prompt) => ["hermes", "chat", "--oneshot", "-q", prompt, "--provider", "custom", "--model", "fixture",
    "--toolsets", "file,terminal", "--ignore-user-config", "--ignore-rules", "--format", "stream-json"],
  version: ["hermes", "--version"],
  env: { HERMES_HOME: "/home/runner/.hermes", TERMINAL_ENV: "local", CUSTOM_BASE_URL: BASE_URL,
    OPENAI_BASE_URL: BASE_URL, OPENAI_API_KEY: "fixture" },
  phoneHomeOff: [], files: [], isResponse: hermesResponse,
}
HARNESSES.goose = {
  name: "goose", image: `${IMAGE_PREFIX}:goose`,
  argv: (prompt) => ["goose", "run", "--provider", "openai", "--model", "fixture", "--no-profile",
    "--with-builtin", "developer", "--output-format", "stream-json", "--max-tool-repetitions", "100", "--max-turns", "100", "-t", prompt],
  version: ["goose", "--version"],
  env: { OPENAI_API_KEY: "fixture", OPENAI_BASE_URL: BASE_URL, OPENAI_BASE_PATH: "v1/chat/completions",
    GOOSE_MODE: "auto", GOOSE_CONTEXT_LIMIT: "200000", GOOSE_DISABLE_KEYRING: "1",
    GOOSE_DISABLE_SESSION_NAMING: "true", GOOSE_TELEMETRY_ENABLED: "false" },
  phoneHomeOff: ["GOOSE_DISABLE_SESSION_NAMING", "GOOSE_TELEMETRY_ENABLED"], files: [], isResponse: gooseResponse,
}
export function hermesResponse(e: Event): boolean {
  return e.type === "tool_use" || (e.type === "text" && typeof e.text === "string" && e.text.trim().length > 0)
}
export function gooseResponse(e: Event): boolean {
  const m = e.message
  return e.type === "message" && m?.role === "assistant" && (m.content ?? []).some((c: any) =>
    c.type === "toolRequest" || (c.type === "text" && typeof c.text === "string" && c.text.trim().length > 0))
}
HARNESSES["aictrl-npm-0.5.3"] = aictrl("aictrl-npm-0.5.3")
HARNESSES["aictrl-npm-0.5.4"] = aictrl("aictrl-npm-0.5.4")
// OpenCode v2 is a separate npm package (@opencode/cli). `run` attaches to a background service by
// default; --standalone gives each container a private in-process server, matching v1's one-shot run.
// --auto approves permissions the config does not deny (the config already allows "*").
const MINIMAL_OFF = ["glob", "grep", "task", "webfetch", "skill"]
// Permission "deny" removes a tool from the request; a `tools: { name: false }` map was ignored in a probe.
HARNESSES["aictrl-0.5.4-minimal"] = {
  ...aictrl("aictrl-npm-0.5.4"),
  name: "aictrl-0.5.4-minimal",
  env: { AICTRL_CONFIG_CONTENT: JSON.stringify({ ...opencodeStyleConfig, permission: { "*": "allow", ...Object.fromEntries(MINIMAL_OFF.map((t) => [t, "deny"])) } }) },
}
HARNESSES["opencode-v2"] = {
  ...HARNESSES.opencode,
  name: "opencode-v2",
  image: `${IMAGE_PREFIX}:opencode-v2`,
  argv: (prompt) => ["opencode", "run", "--standalone", "--auto", "--format", "json", "--model", "fixture/fixture", prompt],
}
// OpenCode 2.1.0 probes: the same reduction to read/shell/edit/write, via permission deny and via a `tools` map.
const OPENCODE_V2_OFF = ["glob", "grep", "question", "skill", "subagent", "webfetch", "websearch", "execute"]
HARNESSES["opencode-v2-deny"] = {
  ...HARNESSES["opencode-v2"],
  name: "opencode-v2-deny",
  env: { ...HARNESSES["opencode-v2"].env, OPENCODE_CONFIG_CONTENT: JSON.stringify({ ...opencodeStyleConfig, permission: { "*": "allow", ...Object.fromEntries(OPENCODE_V2_OFF.map((t) => [t, "deny"])) } }) },
}
HARNESSES["opencode-v2-tools-off"] = {
  ...HARNESSES["opencode-v2"],
  name: "opencode-v2-tools-off",
  env: { ...HARNESSES["opencode-v2"].env, OPENCODE_CONFIG_CONTENT: JSON.stringify({ ...opencodeStyleConfig, tools: Object.fromEntries(OPENCODE_V2_OFF.map((t) => [t, false])) }) },
}
// Feature-parity probes: switch on the subagent support pi and Goose ship but leave off in the benchmark profile.
// pi's subagent tool is the example extension in its npm package; each subagent runs as a separate pi process.
const PI_SUBAGENT = "/usr/local/lib/node_modules/@earendil-works/pi-coding-agent/examples/extensions/subagent/index.ts"
HARNESSES["pi-1.3-subagent"] = {
  ...HARNESSES["pi-1.3-node22"],
  name: "pi-1.3-subagent",
  argv: (prompt) => { const argv = HARNESSES["pi-1.3-node22"].argv(prompt); return [...argv.slice(0, -1), "-e", PI_SUBAGENT, argv[argv.length - 1]] },
}
// aictrl with pi's four tools plus its subagent tool (`task`), to compare with pi-1.3-subagent.
HARNESSES["aictrl-0.5.4-subagent"] = {
  ...aictrl("aictrl-npm-0.5.4"),
  name: "aictrl-0.5.4-subagent",
  env: { AICTRL_CONFIG_CONTENT: JSON.stringify({ ...opencodeStyleConfig, permission: { "*": "allow", ...Object.fromEntries(MINIMAL_OFF.filter((t) => t !== "task").map((t) => [t, "deny"])) } }) },
}
// Goose without --no-profile loads its default platform extensions (summon provides subagents) next to Developer.
HARNESSES["goose-defaults"] = {
  ...HARNESSES.goose,
  name: "goose-defaults",
  argv: (prompt) => HARNESSES.goose.argv(prompt).filter((a) => a !== "--no-profile"),
}
// OpenTelemetry export probe: every CLI gets the standard OTLP environment pointing at harness/otlp-receiver.ts
// (127.0.0.1:14318, OTLP/HTTP JSON). Where a CLI needs its own switch, it is set too; nothing else changes.
const OTLP_PORT = Number(process.env.OTLP_PORT ?? 14318)
const otelEnv = (service: string) => ({
  OTEL_EXPORTER_OTLP_ENDPOINT: `http://127.0.0.1:${OTLP_PORT}`, OTEL_EXPORTER_OTLP_PROTOCOL: "http/json",
  OTEL_TRACES_EXPORTER: "otlp", OTEL_LOGS_EXPORTER: "otlp", OTEL_METRICS_EXPORTER: "otlp", OTEL_SERVICE_NAME: service,
})
const withOtel = (base: Harness, name: string, extra: Partial<Harness> = {}): Harness =>
  ({ ...base, ...extra, name, env: { ...base.env, ...(extra.env ?? {}), ...otelEnv(name) } })
// aictrl and OpenCode: the documented `experimental.openTelemetry` switch for AI SDK spans.
const otelConfig = { ...opencodeStyleConfig, experimental: { openTelemetry: true } }
HARNESSES["aictrl-otel"] = withOtel(aictrl("aictrl-npm-0.5.4"), "aictrl-otel", { env: { AICTRL_CONFIG_CONTENT: JSON.stringify(otelConfig) } })
HARNESSES["opencode-v2-otel"] = withOtel(HARNESSES["opencode-v2"], "opencode-v2-otel", { env: { ...HARNESSES["opencode-v2"].env, OPENCODE_CONFIG_CONTENT: JSON.stringify(otelConfig) } })
HARNESSES["pi-otel"] = withOtel(HARNESSES["pi-1.3-node22"], "pi-otel")
HARNESSES["goose-otel"] = withOtel(HARNESSES.goose, "goose-otel")
HARNESSES["hermes-otel"] = withOtel(HARNESSES.hermes, "hermes-otel")
// Codex: the [otel] table in config.toml (log events and traces over OTLP/HTTP JSON).
HARNESSES["codex-otel"] = withOtel(HARNESSES.codex, "codex-otel", { files: [{ path: "/home/runner/.codex/config.toml", content: codexConfig(true) + [
  ``, `[otel]`, `environment = "probe"`, `log_user_prompt = false`,
  `exporter = { otlp-http = { endpoint = "http://127.0.0.1:${OTLP_PORT}/v1/logs", protocol = "json" } }`,
  `trace_exporter = { otlp-http = { endpoint = "http://127.0.0.1:${OTLP_PORT}/v1/traces", protocol = "json" } }`, ``].join("\n") }] })
const NAMES = (process.env.HARNESSES ?? "aictrl-npm-0.5.4,pi-1.3-node22,codex,opencode,opencode-v2,hermes,goose").split(",")
const SELECTED = NAMES.map((n) => HARNESSES[n] ?? (() => { throw new Error(`unknown harness ${n}`) })())

const PROMPTS: Record<Exclude<Scenario, "version">, string> = {
  trivial: `${MARKER} trivial: reply with the single word Done.`,
  short: `${MARKER} short: read notes-0.txt, notes-1.txt and notes-2.txt once each in order, then reply Done.`,
  long: `${MARKER} long: read big-0.txt through big-${LONG_STEPS - 1}.txt once each in increasing numeric order (${LONG_STEPS} distinct files), then reply Done.`,
}
const EXPECTED_MAIN: Record<string, number> = { trivial: 1, short: 4, long: LONG_STEPS + 1 }

// ---- one container ----------------------------------------------------------------------
type Line = { at: number; text: string }

async function lines(stream: ReadableStream<Uint8Array>, into: Line[]) {
  const decoder = new TextDecoder()
  let buffer = ""
  for await (const chunk of stream) {
    const at = performance.now()
    buffer += decoder.decode(chunk, { stream: true })
    let i: number
    while ((i = buffer.indexOf("\n")) >= 0) {
      into.push({ at, text: buffer.slice(0, i) })
      buffer = buffer.slice(i + 1)
    }
  }
  if (buffer) into.push({ at: performance.now(), text: buffer })
}

function dockerArgs(h: Harness, env: Record<string, string>, files = h.files, name: string) {
  const args = ["docker", "run", "--rm", "--name", name, "--label", `aictrl.harness-benchmark=${CAMPAIGN}`, "--network", "host", "--cpus", CPUS, "--memory", MEMORY, "--memory-swap", MEMORY]
  for (const [k, v] of Object.entries(env)) args.push("-e", `${k}=${v}`)
  files.forEach((f, i) => {
    args.push("-e", `BENCH_CFG${i + 1}_PATH=${f.path}`, "-e", `BENCH_CFG${i + 1}_B64=${Buffer.from(f.content).toString("base64")}`)
  })
  return args
}

async function container(h: Harness, kind: Scenario, opts: { trace?: boolean; env?: Record<string, string>; files?: Harness["files"] } = {}) {
  stub.reset(kind)
  const runId = `${String(++runIndex).padStart(5, "0")}-${h.name}-${kind}`
  const containerName = `${CAMPAIGN}-${runIndex}`
  const out: Line[] = []
  const err: Line[] = []
  const argv =
    kind === "version"
      ? [...dockerArgs(h, {}, h.files, containerName), h.image, ...h.version]
      : [...dockerArgs(h, opts.env ?? h.env, opts.files ?? h.files, containerName), h.image, "measure.sh", kind === "long" ? "1" : "0", opts.trace ? "1" : "0", "--", ...h.argv(PROMPTS[kind])]
  const start = performance.now()
  const proc = Bun.spawn(argv, { stdin: "ignore", stdout: "pipe", stderr: "pipe" })
  let timedOut = false
  const timer = setTimeout(async () => {
    timedOut = true
    // The exact owned name avoids killing another user's container or another campaign.
    const cleanup = Bun.spawn(["docker", "rm", "-f", containerName], { stdout: "ignore", stderr: "ignore" })
    await cleanup.exited
    proc.kill()
  }, TIMEOUT_MS)
  try { await Promise.all([lines(proc.stdout, out), lines(proc.stderr, err), proc.exited]) }
  finally { clearTimeout(timer) }
  fs.mkdirSync(LOG_DIR, { recursive: true })
  fs.writeFileSync(path.join(LOG_DIR, `${runId}.stdout.jsonl`), out.map((l) => l.text).join("\n") + "\n")
  fs.writeFileSync(path.join(LOG_DIR, `${runId}.stderr.log`), err.map((l) => l.text).join("\n") + "\n")
  fs.writeFileSync(path.join(LOG_DIR, `${runId}.requests.jsonl`), stub.log.map(({ body, ...r }) => JSON.stringify(r)).join("\n") + "\n")
  fs.writeFileSync(path.join(LOG_DIR, `${runId}.requests-with-bodies.jsonl.gz`), gzipSync(stub.log.map((r) => JSON.stringify(r)).join("\n") + "\n"), { mode: 0o600 })
  const wall = performance.now() - start
  return { h, kind, start, wall, out, err, requests: [...stub.log], exit: proc.exitCode, timedOut, runId }
}
type Result = Awaited<ReturnType<typeof container>>

function metrics(r: Result) {
  const rel = (at: number | undefined) => (at === undefined ? null : at - r.start)
  const begin = r.out.findIndex((l) => l.text === "@@RUN")
  const end = r.out.findIndex((l) => l.text.startsWith("@@EXIT "))
  const own = r.out.slice(begin + 1, end >= 0 ? end : undefined)
  const events = own.flatMap((l) => {
    if (!l.text.startsWith("{")) return []
    try {
      return [{ at: l.at, e: JSON.parse(l.text) as Event }]
    } catch {
      return []
    }
  })
  const main = r.requests.filter((q) => q.kind === "main")
  const errNum = (prefix: string) => {
    const l = r.err.find((x) => x.text.startsWith(prefix))
    return l ? Number(l.text.slice(prefix.length).trim()) : null
  }
  return {
    firstRequestAny: rel(r.requests[0]?.at),
    firstRequest: rel(main[0]?.at),
    firstStdout: rel(own[0]?.at),
    firstResponse: rel(events.find((x) => r.h.isResponse(x.e))?.at),
    exitAt: rel(end >= 0 ? r.out[end].at : undefined),
    wall: r.wall,
    exit: end >= 0 ? Number(r.out[end].text.split(" ")[1]) : null,
    dockerExit: r.exit, timedOut: r.timedOut, runId: r.runId,
    maxRssKB: errNum("@@TIME "),
    peakCgroupMiB: errNum("@@PEAK ") === null ? null : errNum("@@PEAK ")! / 2 ** 20,
    mainRequests: main.length,
    auxRequests: r.requests.filter((q) => q.kind === "aux").length,
    discoveryRequests: r.requests.filter((q) => q.kind === "discovery").map((q) => q.path),
    otherRequests: r.requests.filter((q) => q.kind === "other").map((q) => q.path),
    stubErrors: r.requests.filter((q) => q.error).map((q) => q.error),
    requestBytes: main.map((q) => q.bytes),
    requestCodeUnits: main.map((q) => q.codeUnits),
    finalRequestBytes: main.at(-1)?.bytes ?? null,
    finalRequestCodeUnits: main.at(-1)?.codeUnits ?? null,
    finalRequestToolResults: main.at(-1)?.toolResults ?? [],
    fixture: validateFixture(main, r.kind),
    finalDone: events.some(({ e }) => assistantTexts(e).some((t) => /^Done\.?$/.test(t.trim()))) && main.at(-1)?.response?.text === "Done.",
    nativeResult: events.filter(({ e }) => e.type === "result" || e.type === "complete").map(({ e }) => ({ type: e.type, exitCode: e.exit_code ?? null, error: !!e.error })),
    outputToolResults: events.filter(({ e }) => e.type === "tool_result").map(({ e }) => ({ name: e.name, bytes: typeof e.output === "string" ? Buffer.byteLength(e.output, "utf8") : null, truncatedPreview: typeof e.output === "string" && e.output.endsWith("..."), isError: e.is_error === true })),
    outputErrors: events.filter(({ e }) => e.type === "error" || e.is_error === true || e.type === "turn.failed" ||
      (e.type === "result" && ((e.subtype && e.subtype !== "success") || e.exit_code !== undefined && e.exit_code !== 0 || e.error))).map(({ e }) => e.type),
  }
}

/** Extract only assistant text from native events; never accept echoed user prompts. */
export function assistantTexts(e: Event): string[] {
  const strings = (cs: any[]) => cs.filter((c) => c?.type === "text" || c?.type === "output_text").map((c) => c.text).filter((t): t is string => typeof t === "string")
  if (e.type === "result" && e.exit_code === 0 && typeof e.text === "string") return [e.text]
  if (e.type === "text") return [e.text ?? e.part?.text].filter((t): t is string => typeof t === "string")
  if (e.type === "item.completed" && e.item?.type === "agent_message") return typeof e.item.text === "string" ? [e.item.text] : []
  if ((e.type === "message" || e.type === "message_end") && e.message?.role === "assistant") return strings(e.message.content ?? [])
  return []
}

export function validateFixture(requests: Req[], scenario: Scenario) {
  const wanted = scenario === "short" ? 3 : scenario === "long" ? LONG_STEPS : 0
  const final = requests.at(-1)?.toolResults ?? []
  const issued = requests.flatMap((r) => r.response?.kind === "tool" ? [r.response.callId!] : [])
  const perCall = issued.map((callId, i) => {
    // Responses adds a sequence suffix to call IDs; encounter order remains fixed.
    const next = requests[i + 1]?.toolResults ?? []
    const result = next.find((e) => e.callId === callId || e.callId.startsWith(callId + "_")) ?? next.at(i)
    return { callId, observed: !!result, ...result }
  })
  const readSuccess = issued.length === wanted && perCall.length === wanted && perCall.every((x) => x.firstMarker && !x.errorNotice)
  return { wanted, issued: issued.length, readSuccess, perCall,
    contentClass: !readSuccess ? "invalid" : perCall.every((x) => x.complete) && final.length === wanted && final.every((x) => x.complete)
      ? "equivalent-content" : "truncated-or-pruned",
    retainedFinalResults: final.length,
    retainedCompleteResults: final.filter((x) => x.complete).length,
    truncationNotices: final.filter((x) => x.truncationNotice).length }
}

/** Long run: memory samples against the tool step reached at each sample. */
function memory(r: Result) {
  const samples = r.err
    .filter((l) => l.text.startsWith("MEM "))
    .map((l) => {
      const [, epoch, cgroup, rss] = l.text.split(/\s+/)
      return { epoch: Number(epoch), cgroupMiB: Number(cgroup) / 2 ** 20, rssMiB: Number(rss) / 1024 }
    })
  const main = r.requests.filter((q) => q.kind === "main")
  const step = (epoch: number) => main.filter((q) => q.epoch <= epoch).length - 1
  const points = samples.map((s) => ({ ...s, step: step(s.epoch) })).filter((p) => p.step >= 1)
  const slope = (key: "rssMiB" | "cgroupMiB") => {
    if (points.length < 3) return null
    const mx = points.reduce((a, x) => a + x.step, 0) / points.length
    const my = points.reduce((a, x) => a + x[key], 0) / points.length
    const num = points.reduce((a, x) => a + (x.step - mx) * (x[key] - my), 0)
    const den = points.reduce((a, x) => a + (x.step - mx) ** 2, 0)
    return den ? num / den : null
  }
  return {
    peakSampledCgroupMiB: samples.length ? Math.max(...samples.map((s) => s.cgroupMiB)) : null,
    peakSampledRssMiB: samples.length ? Math.max(...samples.map((s) => s.rssMiB)) : null,
    slopeCgroupMiBPerStep: slope("cgroupMiB"),
    slopeRssMiBPerStep: slope("rssMiB"),
    lastRequestBytes: main.at(-1)?.bytes ?? null,
    points: points.map((p) => [p.epoch, p.step, +p.rssMiB.toFixed(1), +p.cgroupMiB.toFixed(1)]),
  }
}

/** Size of the first main request: system prompt, tool definitions, messages (chars, ~tokens = chars/4). */
function payload(req: Req | undefined) {
  if (!req?.body) return null
  const json = JSON.parse(req.body)
  const len = (x: unknown) => (x === undefined ? 0 : typeof x === "string" ? x.length : JSON.stringify(x).length)
  let system = 0
  let messages = 0
  if (req.api === "chat") {
    for (const m of json.messages ?? []) (m.role === "system" || m.role === "developer" ? (system += len(m.content)) : (messages += len(m)))
  } else {
    system += len(json.instructions)
    for (const m of Array.isArray(json.input) ? json.input : [json.input])
      m?.role === "system" || m?.role === "developer" ? (system += len(m.content)) : (messages += len(m))
  }
  const tools = len(json.tools)
  const toolNames = (json.tools ?? []).map((t: any) => t.function?.name ?? t.name ?? t.type)
  const toolSizes = Object.fromEntries((json.tools ?? []).map((t: any) => [t.function?.name ?? t.name ?? t.type, len(t)]))
  return { bytes: req.bytes, codeUnits: req.codeUnits, systemChars: system, toolChars: tools, messageChars: messages, approxTokens: Math.round((system + tools + messages) / 4), toolNames, toolSizes }
}

// ---- network attempts (strace) ----------------------------------------------------------
function decodeDnsName(buf: string) {
  // strace prints the datagram as a C string with octal/hex escapes; the QNAME starts at byte 12.
  const bytes: number[] = []
  for (let i = 0; i < buf.length; i++) {
    if (buf[i] !== "\\") { bytes.push(buf.charCodeAt(i)); continue }
    const rest = buf.slice(i + 1)
    const oct = /^[0-7]{1,3}/.exec(rest)
    const hex = /^x[0-9a-fA-F]{2}/.exec(rest)
    const simple: Record<string, number> = { n: 10, r: 13, t: 9, v: 11, f: 12, '"': 34, "\\": 92 }
    if (oct) { bytes.push(parseInt(oct[0], 8)); i += oct[0].length }
    else if (hex) { bytes.push(parseInt(hex[0].slice(1), 16)); i += 3 }
    else { bytes.push(simple[rest[0]] ?? rest.charCodeAt(0)); i += 1 }
  }
  const labels: string[] = []
  for (let p = 12; p < bytes.length && bytes[p] > 0; p += bytes[p] + 1) labels.push(String.fromCharCode(...bytes.slice(p + 1, p + 1 + bytes[p])))
  return labels.join(".")
}

function network(r: Result) {
  const seen = new Map<string, number>()
  const bump = (key: string) => seen.set(key, (seen.get(key) ?? 0) + 1)
  for (const l of r.err.filter((x) => x.text.startsWith("@@NET "))) {
    const t = l.text.slice(6)
    const addr = /sin6?_addr=inet_pton\(AF_INET6?, "([^"]+)"\)|inet_addr\("([^"]+)"\)/.exec(t)
    const port = /htons\((\d+)\)/.exec(t)
    const host = addr ? (addr[1] ?? addr[2]) : null
    if (host && ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(host) && Number(port?.[1]) === stub.port) continue
    if (/\bconnect\(/.test(t)) {
      if (host && port) bump(`connect ${host}:${port[1]}`)
      continue
    }
    // DNS queries: any datagram whose payload decodes to a QNAME (connected UDP sockets carry no address).
    for (const m of t.matchAll(/"((?:[^"\\]|\\.)*)"/g)) {
      const name = decodeDnsName(m[1])
      if (/^[a-z0-9-]+(\.[a-z0-9-]+)+$/i.test(name)) bump(`dns ${name}`)
    }
  }
  return Object.fromEntries(seen)
}

// ---- driver -----------------------------------------------------------------------------
function stats(values: (number | null | undefined)[]) {
  const v = values.filter((x): x is number => typeof x === "number" && Number.isFinite(x)).sort((a, b) => a - b)
  const q = (p: number) => v.length ? v[Math.min(v.length - 1, Math.ceil(p * v.length) - 1)] : null
  return { n: v.length, median: q(0.5), p90: q(0.9) }
}
const fmt = (s: ReturnType<typeof stats>, d = 0) => `${s.median?.toFixed(d)}/${s.p90?.toFixed(d)}`

async function main() {
const raw: Record<string, Record<string, any[]>> = {}
const failures: unknown[] = []
const payloads: Record<string, unknown> = {}
const net: Record<string, unknown> = {}
const want = (k: string) => !ONLY || ONLY.includes(k)
const checkpoint = () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true })
  const tmp = OUT + ".tmp"
  fs.writeFileSync(tmp, JSON.stringify({ schemaVersion: 2, protocolVersion: PROTOCOL_VERSION, HARNESSES: SELECTED.map((h) => h.name), REPS, LONG_REPS, LONG_STEPS, LATENCY, WARMUP, CPUS, MEMORY, TIMEOUT_MS, imagePrefix: IMAGE_PREFIX, campaignMetadata: { campaign: CAMPAIGN, purpose: "capture-only token accounting: aictrl 0.5.4 with a reduced toolset matching pi's default four tools; keep performance phases separate", requestBodyCapture: "gzip JSONL written after container exit; tokenize offline", chatCompletionIds: "unique-per-response", chatCompletionCreated: "current Unix epoch seconds", responseDeliveryEvidence: "planned/body-created/handler-returning timestamps; no TCP delivery or client receipt acknowledgment", timeoutMs: TIMEOUT_MS, quantiles: "nearest-rank, stable numeric ascending order", imageState: "cached images, fresh container and HOME per repetition", fixtureContract: "distinct equal-content file paths: notes-0..2 (340 bytes), big-0..49 (48000 bytes); each read once", modelDiscovery: "OpenAI GET /v1/models and /models plus /fixture detail, immediate fixture200k metadata; other protocol probes404", wireBytes: "Buffer.byteLength(body, utf8); codeUnits retained separately", outputLogs: path.basename(LOG_DIR) }, units: { memory: "MiB", requestBody: "UTF-8 bytes", stringLength: "UTF-16 code units" }, raw, payloads, net, failures }, null, 1))
  fs.renameSync(tmp, OUT)
}

const noop: Harness = { ...HARNESSES["aictrl-main"], name: "noop(base)", image: `${IMAGE_PREFIX}:base`, version: ["true"] }

const plan: [Scenario, number][] = [
  ["version", REPS],
  ["trivial", REPS],
  ["short", REPS],
  ["long", LONG_REPS],
]
for (const [kind, reps] of plan.filter(([k]) => want(k))) {
  const list = kind === "version" ? [noop, ...SELECTED] : SELECTED
  raw[kind] = Object.fromEntries(list.map((h) => [h.name, []]))
  for (let rep = -WARMUP; rep < reps; rep++) {
    for (const h of rep % 2 === 0 ? list : [...list].reverse()) {
      const r = await container(h, kind)
      if (kind === "version") {
        if (r.exit !== 0 || r.timedOut) failures.push({ h: h.name, kind, rep, out: r.out.map((l) => l.text), err: r.err.map((l) => l.text).slice(-20) })
        if (rep >= 0) raw[kind][h.name].push({ wall: r.wall, version: r.out.find((l) => l.text.trim())?.text ?? r.err.find((l) => l.text.trim())?.text ?? null, valid: r.exit === 0 && !r.timedOut, dockerExit: r.exit, timedOut: r.timedOut, runId: r.runId })
        checkpoint()
        continue
      }
      const m = metrics(r)
      const sample: Record<string, unknown> = { ...m }
      if (kind === "long") sample.memory = memory(r)
      if (!payloads[h.name] && kind === "trivial") payloads[h.name] = payload(r.requests.find((q) => q.kind === "main"))
      const ok = m.exit === 0 && m.dockerExit === 0 && !m.timedOut && m.mainRequests === EXPECTED_MAIN[kind] && m.firstResponse !== null && m.maxRssKB !== null && m.maxRssKB > 0 && m.peakCgroupMiB !== null && m.peakCgroupMiB > 0 && m.finalDone && m.fixture.readSuccess && m.outputErrors.length === 0 && m.stubErrors.length === 0 && (h.name !== "hermes" || m.nativeResult.some((e) => e.type === "result" && e.exitCode === 0)) && (h.name !== "goose" || m.nativeResult.some((e) => e.type === "complete"))
      sample.valid = ok
      if (!ok)
        failures.push({
          h: h.name, kind, rep, metrics: m,
          out: r.out.map((l) => l.text.slice(0, 400)).slice(-25),
          err: r.err.map((l) => l.text.slice(0, 400)).filter((t) => !t.startsWith("MEM")).slice(-25),
        })
      if (rep >= 0) raw[kind][h.name].push(sample)
      checkpoint()
    }
  }
  for (const h of list) {
    const xs = raw[kind][h.name].filter((s) => s.valid !== false)
    const pick = (f: (s: any) => number | null) => stats(xs.map(f))
    if (kind === "version") {
      console.log(`version  ${h.name.padEnd(12)} wall ${fmt(pick((s) => s.wall))}  ${xs[0]?.version ?? ""}`)
      continue
    }
    const line = [
      `${kind.padEnd(8)} ${h.name.padEnd(12)}`,
      `req ${fmt(pick((s) => s.firstRequest))}`,
      `stdout ${fmt(pick((s) => s.firstStdout))}`,
      `resp ${fmt(pick((s) => s.firstResponse))}`,
      `exit ${fmt(pick((s) => s.exitAt))}`,
      `rss ${fmt(pick((s) => s.maxRssKB === null ? null : s.maxRssKB / 1024))}MiB`,
      `cg ${fmt(pick((s) => s.peakCgroupMiB))}MiB`,
      `aux ${xs[0]?.auxRequests} other ${JSON.stringify(xs[0]?.otherRequests ?? [])}`,
    ]
    if (kind === "long")
      line.push(
        `| peak cg ${fmt(pick((s) => s.memory.peakSampledCgroupMiB))} rss ${fmt(pick((s) => s.memory.peakSampledRssMiB))} slope cg ${fmt(pick((s) => s.memory.slopeCgroupMiBPerStep), 2)} rss ${fmt(pick((s) => s.memory.slopeRssMiBPerStep), 2)} MiB/step, last req ${fmt(pick((s) => s.memory.lastRequestBytes === null ? null : s.memory.lastRequestBytes / 1024))} KiB`,
      )
    console.log(line.join("  "))
  }
}

if (want("net")) {
  // One traced trivial run per harness with its phone-home switches on (as benchmarked) and off (defaults).
  for (const h of SELECTED) {
    const traced = await container(h, "trivial", { trace: true })
    const tracedMetrics = metrics(traced)
    if (tracedMetrics.exit !== 0 || traced.exit !== 0 || traced.timedOut || !tracedMetrics.finalDone || !tracedMetrics.firstResponse) failures.push({ h: h.name, kind: "net", metrics: tracedMetrics })
    const benchmarked = network(traced)
    const defaults = Object.fromEntries(Object.entries(h.env).filter(([k]) => !h.phoneHomeOff.includes(k)))
    let untuned = benchmarked
    if (h.phoneHomeOff.length) {
      const defaultsRun = await container(h, "trivial", { trace: true, env: defaults, files: h.defaultsFiles })
      const dm = metrics(defaultsRun)
      if (dm.exit !== 0 || defaultsRun.exit !== 0 || defaultsRun.timedOut || !dm.finalDone || dm.firstResponse === null || dm.stubErrors.length) failures.push({ h: h.name, kind: "net-defaults", metrics: dm })
      untuned = network(defaultsRun)
    }
    net[h.name] = { benchmarked, defaults: untuned, switchedOff: h.phoneHomeOff }
    checkpoint()
    console.log(`net      ${h.name.padEnd(12)} benchmarked ${JSON.stringify(benchmarked)}  defaults ${JSON.stringify(untuned)}`)
  }
}

for (const [name, p] of Object.entries(payloads)) console.log(`payload  ${name.padEnd(12)} ${JSON.stringify(p)}`)

checkpoint()
console.log(`failures: ${failures.length}`)
console.log(`wrote ${OUT}`)
if (failures.length) process.exitCode = 1
}
if (import.meta.main) {
  try { await main() } finally { stub.server.stop(true) }
} else stub.server.stop(true)
