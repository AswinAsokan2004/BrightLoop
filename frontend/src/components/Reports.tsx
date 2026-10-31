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
import FinanceOverview from "./FinanceOverview"
export function Reports({ overview = false }: { overview?: boolean }) {
  return <FinanceOverview overview={overview} />
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
