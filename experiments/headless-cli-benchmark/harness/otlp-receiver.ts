/**
 * Minimal OTLP/HTTP receiver for the OpenTelemetry export probe.
 * Accepts POST /v1/traces, /v1/logs and /v1/metrics, answers 200 with an empty JSON body,
 * and appends one JSON line per request: arrival time, path, content type, size, the
 * service.name resource attribute, and span/log/metric names when the body is OTLP JSON.
 *
 *   bun harness/otlp-receiver.ts <out.jsonl> [port=14318]
 */
import fs from "fs"

const OUT = process.argv[2] ?? "otlp-requests.jsonl"
const PORT = Number(process.argv[3] ?? 14318)

function attr(attrs: any[] | undefined, key: string) {
  const v = attrs?.find((a) => a.key === key)?.value
  return v?.stringValue ?? v?.intValue ?? v?.boolValue
}

function summarize(path: string, json: any) {
  const groups = json?.resourceSpans ?? json?.resourceLogs ?? json?.resourceMetrics ?? []
  const services = new Set<string>()
  const names: string[] = []
  const attributes = new Set<string>()
  for (const g of groups) {
    const svc = attr(g.resource?.attributes, "service.name")
    if (svc) services.add(String(svc))
    for (const scope of g.scopeSpans ?? g.scopeLogs ?? g.scopeMetrics ?? []) {
      for (const item of scope.spans ?? scope.logRecords ?? scope.metrics ?? []) {
        names.push(item.name ?? attr(item.attributes, "event.name") ?? item.body?.stringValue?.slice(0, 60) ?? "?")
        for (const a of item.attributes ?? []) attributes.add(a.key)
      }
    }
  }
  return { services: [...services], count: names.length, names, attributeKeys: [...attributes].sort() }
}

Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",
  async fetch(req) {
    const url = new URL(req.url)
    const body = new Uint8Array(await req.arrayBuffer())
    const type = req.headers.get("content-type") ?? ""
    let summary: Record<string, unknown> = {}
    if (type.includes("json")) {
      try { summary = summarize(url.pathname, JSON.parse(new TextDecoder().decode(body))) } catch (e) { summary = { parseError: String(e) } }
    }
    if (process.env.OTLP_KEEP_BODIES) fs.writeFileSync(`${OUT}.${Date.now()}${url.pathname.replaceAll("/", "-")}.bin`, body)
    fs.appendFileSync(OUT, JSON.stringify({ at: Date.now(), method: req.method, path: url.pathname, contentType: type, bytes: body.length, userAgent: req.headers.get("user-agent"), ...summary }) + "\n")
    return new Response("{}", { headers: { "content-type": "application/json" } })
  },
})
console.log(`otlp receiver on 127.0.0.1:${PORT} -> ${OUT}`)
