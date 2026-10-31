import { useState } from "react"
import {
  api,
  text,
  title,
  today,
  type Row,
  type Page,
  type User,
} from "../lib/api"
import {
  Badge,
  Button,
  Card,
  Details,
  Dialog,
  ErrorMessage,
  Form,
  Table,
  useLoad,
  choices,
} from "./ui"
type Summary = {
  active_subscriptions: number
  mrr: string
  arr: string
  invoiced_total: string
  revenue_collected: string
  outstanding_amount: string
  overdue_amount: string
  overdue_count: number
  subscriptions_by_state: Record<string, number>
}
export function Reports({ overview = false }: { overview?: boolean }) {
  const [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [customer, setCustomer] = useState(""),
    [plan, setPlan] = useState(""),
    [revision, setRevision] = useState(0)
  const params = new URLSearchParams()
  if (from) params.set("date_from", from)
  if (to) params.set("date_to", to)
  if (customer) params.set("customer_id", customer)
  if (plan) params.set("plan_id", plan)
  const summary = useLoad<Summary>(`/reports/summary?${params}`, revision),
    monthly = useLoad<{ month: string; invoiced: string; collected: string }[]>(
      `/reports/revenue-by-month?${params}`,
      revision,
    )
  const data = summary.data
  return (
    <div className="space-y-5">
      <div className="flex justify-between">
        <div>
          <h1 className="text-3xl font-bold text-navy-900">
            {overview ? "Overview" : "Revenue reports"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Live subscription and collections activity.
          </p>
        </div>
        <Button secondary onClick={() => setRevision((r) => r + 1)}>
          Refresh
        </Button>
      </div>
      <Card>
        <div className="flex flex-wrap gap-3">
          <label className="text-xs text-slate-500">
            From
            <input
              aria-label="Report from date"
              className="mt-1 block rounded border p-2 text-sm"
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-500">
            To
            <input
              aria-label="Report to date"
              className="mt-1 block rounded border p-2 text-sm"
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-500">
            Customer ID
            <input
              className="mt-1 block w-32 rounded border p-2 text-sm"
              type="number"
              min="1"
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-500">
            Plan ID
            <input
              className="mt-1 block w-32 rounded border p-2 text-sm"
              type="number"
              min="1"
              value={plan}
              onChange={(e) => setPlan(e.target.value)}
            />
          </label>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Dates filter invoices and payments. Subscription counts and MRR
          reflect the current portfolio. Use one currency across your workspace:
          backend reports aggregate currencies together.
        </p>
      </Card>
      <ErrorMessage error={summary.error || monthly.error} />
      {summary.loading ? (
        <p role="status">Loading reports…</p>
      ) : (
        data && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                ["Active subscriptions", data.active_subscriptions],
                ["Monthly recurring amount", data.mrr],
                ["Collected", data.revenue_collected],
                ["Outstanding", data.outstanding_amount],
                ["Annual recurring amount", data.arr],
                ["Invoiced", data.invoiced_total],
                ["Overdue amount", data.overdue_amount],
                ["Overdue invoices", data.overdue_count],
              ].map(([label, value]) => (
                <Card key={label}>
                  <p className="text-sm text-slate-500">{label}</p>
                  <p className="mt-3 break-words text-2xl font-bold text-navy-900">
                    {value}
                  </p>
                </Card>
              ))}
            </div>
            <div className="grid gap-5 xl:grid-cols-2">
              <Card>
                <h2 className="mb-4 font-bold">Revenue by month</h2>
                {monthly.loading ? (
                  <p>Loading…</p>
                ) : (
                  <Table
                    rows={(monthly.data || []).map((row, i) => ({
                      ...row,
                      id: i,
                    }))}
                    columns={[
                      { key: "month", label: "Month" },
                      { key: "invoiced", label: "Invoiced" },
                      { key: "collected", label: "Collected" },
                    ]}
                  />
                )}
              </Card>
              <Card>
                <h2 className="mb-4 font-bold">Subscription health</h2>
                {Object.entries(data.subscriptions_by_state).map(
                  ([state, count]) => (
                    <div
                      key={state}
                      className="mb-3 flex justify-between border-b pb-2"
                    >
                      <Badge value={state} />
                      <span>{count}</span>
                    </div>
                  ),
                )}
              </Card>
            </div>
          </>
        )
      )}
    </div>
  )
}
export function Payments() {
  const [page, setPage] = useState(1),
    [method, setMethod] = useState(""),
    [from, setFrom] = useState(""),
    [to, setTo] = useState("")
  const params = new URLSearchParams({ page: String(page), size: "20" })
  if (method) params.set("method", method)
  if (from) params.set("date_from", from)
  if (to) params.set("date_to", to)
  const result = useLoad<Page>(`/payments?${params}`)
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold text-navy-900">Payments</h1>
      <p className="text-sm text-slate-500">
        Record full or partial payments from an invoice.
      </p>
      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <select
            aria-label="Payment method filter"
            className="rounded border p-2"
            value={method}
            onChange={(e) => {
              setMethod(e.target.value)
              setPage(1)
            }}
          >
            <option value="">All methods</option>
            {choices([
              "cash",
              "bank_transfer",
              "card",
              "upi",
              "cheque",
              "online_gateway",
            ]).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <input
            aria-label="Payments from date"
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value)
              setPage(1)
            }}
            className="rounded border p-2"
          />
          <input
            aria-label="Payments to date"
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value)
              setPage(1)
            }}
            className="rounded border p-2"
          />
        </div>
        <ErrorMessage error={result.error} />
        {result.loading ? (
          <p>Loading…</p>
        ) : (
          <Table
            rows={result.data?.items || []}
            columns={[
              "id",
              "invoice_id",
              "customer_id",
              "payment_date",
              "method",
              "amount",
              "reference",
              "status",
            ].map((key) => ({ key, label: title(key) }))}
          />
        )}
        <div className="mt-4 flex justify-between">
          <span>{result.data?.total || 0} payments</span>
          <div className="flex gap-2">
            <Button
              secondary
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <Button
              secondary
              disabled={page * 20 >= (result.data?.total || 0)}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
export function Billing() {
  const [revision, setRevision] = useState(0),
    [page, setPage] = useState(1),
    [runDate, setRunDate] = useState(today()),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<Row | null>(null)
  const runs = useLoad<Page>(`/billing/runs?page=${page}&size=20`, revision)
  async function run() {
    setBusy(true)
    setError("")
    try {
      setSelected(await api<Row>("/billing/run", "POST", { run_date: runDate }))
      setRevision((r) => r + 1)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold text-navy-900">Billing runs</h1>
      <p className="text-sm text-slate-500">
        Create draft invoices for all due active subscriptions, including missed
        periods.
      </p>
      <Card>
        <div className="flex flex-wrap gap-3">
          <input
            aria-label="Billing run date"
            type="date"
            className="rounded border p-2"
            value={runDate}
            onChange={(e) => setRunDate(e.target.value)}
          />
          <Button disabled={busy || !runDate} onClick={() => void run()}>
            {busy ? "Running billing…" : "Run billing"}
          </Button>
        </div>
        <ErrorMessage error={error} />
      </Card>
      <Card>
        <ErrorMessage error={runs.error} />
        {runs.loading ? (
          <p>Loading…</p>
        ) : (
          <Table
            rows={runs.data?.items || []}
            columns={[
              "id",
              "run_date",
              "status",
              "subscriptions_processed",
              "invoices_created",
              "errors_count",
            ].map((key) => ({ key, label: title(key) }))}
            select={setSelected}
          />
        )}
        <div className="mt-4 flex gap-2">
          <Button
            secondary
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <Button
            secondary
            disabled={page * 20 >= (runs.data?.total || 0)}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </Card>
      {selected && (
        <Dialog
          title={`Billing run ${selected.id}`}
          close={() => setSelected(null)}
        >
          <Details row={selected} />
          {!!selected.error_log && (
            <pre className="mt-4 whitespace-pre-wrap text-sm text-rose-700">
              {String(selected.error_log)}
            </pre>
          )}
        </Dialog>
      )}
    </div>
  )
}
export function Profile({ user }: { user: User }) {
  const profile = useLoad<Row>("/portal/profile")
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold text-navy-900">Welcome, {user.name}</h1>
      <p className="text-sm text-slate-500">
        View your billing profile, subscriptions and invoices using the
        navigation.
      </p>
      <Card>
        <ErrorMessage error={profile.error} />
        {profile.loading ? (
          <p>Loading…</p>
        ) : (
          profile.data && <Details row={profile.data} />
        )}
      </Card>
    </div>
  )
}
