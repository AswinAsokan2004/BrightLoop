export type User = {
  id: number
  name: string
  email: string
  role: "admin" | "staff" | "customer"
  customer_id: number | null
}
export type Tokens = { access_token: string; refresh_token: string }
export type Row = { id: number; [key: string]: unknown }
export type Page = { items: Row[]; total: number; page: number; size: number }
const storageKey = "brightloop.session"
const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "")
let tokens: Tokens | null = readTokens()
let refreshing: Promise<void> | null = null
function readTokens(): Tokens | null {
  try {
    return JSON.parse(sessionStorage.getItem(storageKey) || "null")
  } catch {
    return null
  }
}
export function setTokens(value: Tokens | null) {
  tokens = value
  if (value) sessionStorage.setItem(storageKey, JSON.stringify(value))
  else sessionStorage.removeItem(storageKey)
}
export function hasSession() {
  return !!tokens
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
  }
}
async function errorFor(response: Response) {
  let message = `Request failed (${response.status})`
  try {
    const data = await response.json()
    if (typeof data.detail === "string") message = data.detail
    else if (Array.isArray(data.detail))
      message = data.detail
        .map(
          (item: { loc: string[]; msg: string }) =>
            `${item.loc.filter((x) => x !== "body").join(".")}: ${item.msg}`,
        )
        .join("; ")
  } catch {
    if (response.status >= 500)
      message =
        "The API is unavailable. Check that the backend and PostgreSQL are running."
  }
  return new ApiError(message, response.status)
}
async function fetchApi(
  path: string,
  method: string,
  body?: unknown,
  token?: string,
) {
  try {
    return await fetch(`${base}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(
      "Cannot reach the API. Start the backend and check the API URL.",
      0,
    )
  }
}
export async function api<T = Row>(
  path: string,
  method = "GET",
  body?: unknown,
  authenticated = true,
): Promise<T> {
  const attempted = tokens?.access_token
  let response = await fetchApi(
    path,
    method,
    body,
    authenticated ? attempted : undefined,
  )
  if (response.status === 401 && authenticated && tokens) {
    // Reuse the replacement if another request already refreshed this access token.
    if (attempted === tokens.access_token) {
      if (!refreshing)
        refreshing = (async () => {
          const current = tokens
          const refreshed = await fetchApi("/auth/refresh", "POST", {
            refresh_token: current?.refresh_token,
          })
          if (!refreshed.ok) throw await errorFor(refreshed)
          const replacement: Tokens = await refreshed.json()
          if (tokens === current) setTokens(replacement)
        })()
          .catch((error) => {
            setTokens(null)
            window.dispatchEvent(new Event("session-expired"))
            throw error
          })
          .finally(() => {
            refreshing = null
          })
      await refreshing
    }
    response = await fetchApi(path, method, body, tokens?.access_token)
  }
  if (!response.ok) {
    if (authenticated && response.status === 401) {
      setTokens(null)
      window.dispatchEvent(new Event("session-expired"))
    }
    throw await errorFor(response)
  }
  if (response.status === 204) return undefined as T
  if (response.headers.get("content-type")?.includes("text/html"))
    return (await response.text()) as T
  return response.json()
}
export async function login(email: string, password: string) {
  const pair = await api<Tokens>(
    "/auth/login",
    "POST",
    { email, password },
    false,
  )
  setTokens(pair)
  try {
    return await api<User>("/auth/me")
  } catch (error) {
    setTokens(null)
    throw error
  }
}
export async function logout() {
  const current = tokens
  setTokens(null)
  if (current)
    await api(
      "/auth/logout",
      "POST",
      { refresh_token: current.refresh_token },
      false,
    )
}
export async function options(path: string): Promise<Row[]> {
  const rows: Row[] = []
  for (let page = 1; ; page++) {
    const result = await api<Page>(`${path}?page=${page}&size=100`)
    rows.push(...result.items)
    if (rows.length >= result.total || !result.items.length) return rows
  }
}
export async function printInvoice(path: string) {
  const popup = window.open("", "_blank")
  if (!popup) throw new Error("Allow popups to open the printable invoice.")
  popup.document.body.textContent = "Loading invoice…"
  try {
    const html = await api<string>(path)
    popup.document.open()
    popup.document.write(html)
    popup.document.close()
  } catch (error) {
    popup.close()
    throw error
  }
}
export const text = (row: Row, key: string) =>
  row[key] == null ? "" : String(row[key])
export const title = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
export const today = () => new Date().toLocaleDateString("en-CA")
export function money(value: unknown, currency = "INR") {
  // Formatting only. All calculations and persisted amounts remain backend Decimal strings.
  const amount = String(value ?? "0")
  return `${currency} ${amount}`
}
