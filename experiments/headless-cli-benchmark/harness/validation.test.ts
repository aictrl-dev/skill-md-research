import { describe, expect, test } from "bun:test"
import { fixtureCall, fixtureEvidence, fixtureLines, fixturePath, scriptProgress, Stub, type Req } from "./stub"
import { assistantTexts, gooseResponse, hermesResponse, validateFixture } from "./compare-v054"

const toolResult = (content: string, id = "call_0") => ({ role: "tool", tool_call_id: id, content })
const evidence = (content: string, scenario: "short" | "long" = "short", id = "call_0") =>
  fixtureEvidence({ messages: [toolResult(content, id)] }, "chat", scenario)[0]
const req = (toolResults: ReturnType<typeof fixtureEvidence>, callId?: string): Req => ({
  at: 0, epoch: 0, path: "/v1/chat/completions", api: "chat", kind: "main", step: toolResults.length,
  bytes: 0, codeUnits: 0, toolResults, response: callId ? { kind: "tool", callId } : { kind: "text", text: "Done." },
})

describe("fixture evidence", () => {
  test("requires all repeated short lines and every numbered long line in order", () => {
    const full = fixtureLines("short").join("\n")
    expect(evidence(full).complete).toBe(true)
    expect(evidence("alpha beta gamma\n").complete).toBe(false)
    const numbered = fixtureLines("long").map((s, i) => `${i + 1}: ${s}`).join("\n")
    expect(evidence(`<file>\n${numbered}\n</file>`, "long").complete).toBe(true)
    expect(evidence(numbered.replace(fixtureLines("long")[420], "missing"), "long").complete).toBe(false)
  })
  test("progress is retry-stable and survives pruning older tool results", () => {
    const last = evidence("alpha beta gamma", "short", "call_49_208")
    expect(scriptProgress([last])).toBe(50)
    expect(scriptProgress([last])).toBe(50)
    expect(() => scriptProgress([{ ...last, callId: "foreign_id" }])).toThrow("lost all scripted call IDs")
  })
  test("respects explicit native flags including guardrail errors hidden behind is_error false", () => {
    const full = JSON.stringify({ content: fixtureLines("short").join("\n"), truncated: false })
    expect(evidence(full)).toMatchObject({ complete: true, truncationNotice: false, errorNotice: false })
    expect(evidence(JSON.stringify({ error: "BLOCKED", guardrail_refusal: true, is_error: false }))).toMatchObject({ errorNotice: true, nativeGuardrailRefusal: true })
    expect(evidence(JSON.stringify({ status: "unchanged", dedup: true, content_returned: false }))).toMatchObject({ complete: false, nativeSuppressed: true })
    expect(evidence(JSON.stringify({ content: "alpha beta gamma", truncated: true })).truncationNotice).toBe(true)
  })
  test("captures truncation and tool errors without retaining content", () => {
    const e = evidence(fixtureLines("long").slice(0, 10).join("\n") + "\n[output truncated]", "long")
    expect(e.firstMarker).toBe(true)
    expect(e.lastMarker).toBe(false)
    expect(e.truncationNotice).toBe(true)
    expect(e.complete).toBe(false)
    expect(e).not.toHaveProperty("content")
    expect(e.sha256).toHaveLength(64)
    expect(evidence("Error: cat: permission denied").errorNotice).toBe(true)
  })
  test("distinguishes valid shortened reads from equivalent retained content and invalid reads", () => {
    const full = fixtureLines("short").join("\n")
    const complete = [0, 1, 2].map((i) => evidence(full, "short", `call_${i}`))
    const campaign = (results: typeof complete) => [req([], "call_0"), req(results.slice(0, 1), "call_1"), req(results.slice(0, 2), "call_2"), req(results)]
    expect(validateFixture(campaign(complete), "short").contentClass).toBe("equivalent-content")
    const shortened = complete.map((_, i) => evidence("alpha beta gamma\n[truncated]", "short", `call_${i}`))
    expect(validateFixture(campaign(shortened), "short")).toMatchObject({ readSuccess: true, contentClass: "truncated-or-pruned" })
    const failed = [...complete]; failed[1] = evidence("Error: no such file", "short", "call_1")
    expect(validateFixture(campaign(failed), "short").readSuccess).toBe(false)
  })
})

describe("native adapters", () => {
  test("uses distinct paths with identical payloads for every requested read", () => {
    expect(fixturePath("short", 0)).toBe("/workspace/notes-0.txt")
    expect(fixturePath("short", 2)).toBe("/workspace/notes-2.txt")
    expect(fixturePath("long", 49)).toBe("/workspace/big-49.txt")
  })
  test("maps Goose namespaced shell and Hermes whole-file read arguments", () => {
    expect(fixtureCall([{ name: "developer__shell", params: { properties: { command: { type: "string" } } }, kind: "function" }], "/workspace/big.txt", 0).args).toEqual({ command: "cat /workspace/big.txt" })
    expect(fixtureCall([{ name: "read_file", params: { properties: { path: {}, offset: {}, limit: {} } }, kind: "function" }], "/workspace/big.txt", 0).args).toEqual({ path: "/workspace/big.txt", offset: 1, limit: 2000 })
  })
  test("ignores lifecycle, thinking, tool results and echoed user text", () => {
    expect(hermesResponse({ type: "system", subtype: "init" })).toBe(false)
    expect(hermesResponse({ type: "tool_use", name: "read_file" })).toBe(true)
    expect(hermesResponse({ type: "text", text: "Done." })).toBe(true)
    for (const role of ["user", "tool"]) expect(gooseResponse({ type: "message", message: { role, content: [{ type: "text", text: "Done." }] } })).toBe(false)
    expect(gooseResponse({ type: "message", message: { role: "assistant", content: [{ type: "thinking", thinking: "Done." }] } })).toBe(false)
    expect(gooseResponse({ type: "message", message: { role: "assistant", content: [{ type: "toolRequest" }] } })).toBe(true)
    expect(assistantTexts({ type: "message", message: { role: "user", content: [{ type: "text", text: "Done." }] } })).toEqual([])
    expect(assistantTexts({ type: "result", exit_code: 0, text: "Done." })).toEqual(["Done."])
    expect(assistantTexts({ type: "result", exit_code: 1, text: "Done." })).toEqual([])
  })
})

test("wire bytes and code units differ for UTF-8 input", async () => {
  const stub = new Stub(0)
  try {
    const body = JSON.stringify({ messages: [{ role: "user", content: "BENCHTASK trivial 🥇" }], tools: [{ type: "function", function: { name: "read", parameters: {} } }] })
    const response = await fetch(`http://127.0.0.1:${stub.port}/v1/chat/completions`, { method: "POST", body })
    expect(response.status).toBe(200)
    await response.text()
    expect(stub.log[0].bytes).toBe(Buffer.byteLength(body, "utf8"))
    expect(stub.log[0].codeUnits).toBe(body.length)
    expect(stub.log[0].bytes).toBeGreaterThan(stub.log[0].codeUnits)
  } finally { stub.server.stop(true) }
})

test("supports standard OpenAI model discovery without pretending other protocols are available", async () => {
  const stub = new Stub(50)
  try {
    for (const endpoint of ["/v1/models", "/models"]) {
      const response = await fetch(`http://127.0.0.1:${stub.port}${endpoint}`)
      expect(response.status).toBe(200)
      expect(await response.json()).toMatchObject({ object: "list", data: [{ id: "fixture", context_length: 200000 }] })
    }
    const detail = await fetch(`http://127.0.0.1:${stub.port}/v1/models/fixture`)
    expect(await detail.json()).toMatchObject({ object: "model", id: "fixture" })
    expect((await fetch(`http://127.0.0.1:${stub.port}/api/tags`)).status).toBe(404)
    expect(stub.log.filter((r) => r.kind === "discovery")).toHaveLength(3)
  } finally { stub.server.stop(true) }
})

test("chat completions have unique response IDs, stable per-response chunks and current creation times", async () => {
  const stub = new Stub(0)
  stub.reset("short")
  try {
    const firstCreated = Math.floor(Date.now() / 1000)
    const responses: any[][] = []
    for (const content of ["BENCHTASK short", "BENCHTASK short", "Auxiliary title request"]) {
      const body = JSON.stringify({ messages: [{ role: "user", content }], tools: [{ type: "function", function: { name: "read", parameters: { properties: { path: { type: "string" } } } } }] })
      const response = await fetch(`http://127.0.0.1:${stub.port}/v1/chat/completions`, { method: "POST", body })
      expect(response.status).toBe(200)
      const sse = await response.text()
      const chunks = sse.split("\n").filter((l) => l.startsWith("data: ") && l !== "data: [DONE]").map((l) => JSON.parse(l.slice(6)))
      expect(chunks).toHaveLength(2)
      expect(new Set(chunks.map((c) => c.id)).size).toBe(1)
      expect(chunks.every((c) => c.created >= firstCreated && c.created <= Math.floor(Date.now() / 1000))).toBe(true)
      const delivery = stub.log.at(-1)!.responseDelivery!
      expect(delivery.stage).toBe("handler-returning")
      expect(delivery.completionId).toBe(chunks[0].id)
      expect(delivery.completionCreated).toBe(chunks[0].created)
      expect(delivery.bodyBytes).toBe(Buffer.byteLength(sse, "utf8"))
      expect(delivery.bodyCreatedAt!).toBeGreaterThanOrEqual(delivery.plannedAt)
      expect(delivery.handlerReturningAt!).toBeGreaterThanOrEqual(delivery.bodyCreatedAt!)
      responses.push(chunks)
    }
    expect(new Set(responses.map((cs) => cs[0].id)).size).toBe(3)
    expect(responses[0][0].choices[0].delta.tool_calls[0].id).toBe("call_0")
    expect(responses[1][0].choices[0].delta.tool_calls[0].id).toBe("call_0")
    expect(stub.log.map((r) => r.kind)).toEqual(["main", "main", "aux"])
  } finally { stub.server.stop(true) }
})
