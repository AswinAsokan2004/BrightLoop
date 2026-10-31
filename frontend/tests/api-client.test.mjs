import { test } from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs/promises"
import ts from "typescript"
const source = (
  await fs.readFile(new URL("../src/lib/api.ts", import.meta.url), "utf8")
).replace("import.meta.env.VITE_API_BASE_URL", "''")
const js = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2021,
    module: ts.ModuleKind.ESNext,
  },
}).outputText
let serial = 0
async function client() {
  const store = new Map()
  globalThis.sessionStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
    removeItem: (key) => store.delete(key),
  }
  globalThis.window = new EventTarget()
  return import(
    `data:text/javascript;base64,${Buffer.from(js + `\n// ${serial++}`).toString("base64")}`
  )
}
const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
test("parallel unauthorized requests rotate the refresh token once and retry with the replacement", async () => {
  const api = await client()
  api.setTokens({ access_token: "old", refresh_token: "refresh-old" })
  let refreshes = 0
  globalThis.fetch = async (url, init) => {
    if (url === "/api/auth/refresh") {
      refreshes++
      await new Promise((resolve) => setTimeout(resolve, 15))
      assert.deepEqual(JSON.parse(init.body), { refresh_token: "refresh-old" })
      return json({ access_token: "new", refresh_token: "refresh-new" })
    }
    return init.headers.Authorization === "Bearer new"
      ? json({ amount: "1234567890.12" })
      : json({ detail: "Expired" }, 401)
  }
  const results = await Promise.all([
    api.api("/one"),
    api.api("/two"),
    api.api("/three"),
  ])
  assert.equal(refreshes, 1)
  assert.equal(results[0].amount, "1234567890.12")
})
test("failed refresh clears the session and emits an expiration event", async () => {
  const api = await client()
  api.setTokens({ access_token: "old", refresh_token: "bad" })
  let expired = 0
  window.addEventListener("session-expired", () => expired++)
  globalThis.fetch = async () =>
    json({ detail: "Invalid or expired token" }, 401)
  await assert.rejects(api.api("/protected"), /Invalid or expired token/)
  assert.equal(api.hasSession(), false)
  assert.equal(expired, 1)
})
test("validation details preserve field names and public calls carry no bearer token", async () => {
  const api = await client()
  api.setTokens({ access_token: "private", refresh_token: "refresh" })
  globalThis.fetch = async (url, init) => {
    assert.equal(init.headers.Authorization, undefined)
    return json(
      {
        detail: [
          {
            loc: ["body", "lines", 0, "quantity"],
            msg: "Must be greater than zero",
          },
        ],
      },
      422,
    )
  }
  await assert.rejects(
    api.api("/auth/signup", "POST", {}, false),
    /lines.0.quantity: Must be greater than zero/,
  )
})
test("204 deletes work without JSON and logout always clears local authentication", async () => {
  const api = await client()
  api.setTokens({ access_token: "private", refresh_token: "refresh" })
  globalThis.fetch = async () => new Response(null, { status: 204 })
  assert.equal(await api.api("/products/1", "DELETE"), undefined)
  await api.logout()
  assert.equal(api.hasSession(), false)
})
test("pagination collects every reference page without truncating at 100", async () => {
  const api = await client()
  globalThis.fetch = async (url) =>
    json(
      url.includes("page=1&")
        ? {
            items: Array.from({ length: 100 }, (_, id) => ({ id })),
            total: 101,
          }
        : { items: [{ id: 100 }], total: 101 },
    )
  assert.equal((await api.options("/products")).length, 101)
})
test("network failure has an actionable error and a failed login leaves no session", async () => {
  const api = await client()
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch")
  }
  await assert.rejects(
    api.login("a@example.com", "password"),
    /Cannot reach the API/,
  )
  assert.equal(api.hasSession(), false)
})
