import { useState } from "react"
import {
  api,
  text,
  title,
  money,
  printInvoice,
  today,
  type Page,
  type Row,
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
export default function Invoices({ user }: { user: User }) {
  const portal = user.role === "customer",
    base = portal ? "/portal/invoices" : "/invoices"
  const [page, setPage] = useState(1),
    [filter, setFilter] = useState(""),
    [query, setQuery] = useState(""),
    [revision, setRevision] = useState(0),
    [selected, setSelected] = useState<number | null>(() => {
      const match = location.pathname.match(/\/invoices\/(\d+)\/?$/)
      return match ? Number(match[1]) : null
    }),
    [pay, setPay] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("")
  const params = new URLSearchParams({ page: String(page), size: "20" })
  if (filter === "outstanding" || filter === "overdue")
    params.set(filter, "true")
  else if (filter) params.set("state", filter)
  if (query && !portal) params.set("q", query)
  const result = useLoad<Page>(`${base}?${params}`, revision),
    detail = useLoad<Row>(selected ? `${base}/${selected}` : null, revision),
    invoice = detail.data
  async function action(suffix: string) {
    setBusy(true)
    setError("")
    setNotice("")
    try {
      await api(`/invoices/${selected}/${suffix}`, "POST")
      setRevision((r) => r + 1)
      if (suffix === "send")
        setNotice(
          "Invoice email queued. Delivery depends on the server email configuration.",
        )
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  async function print() {
    setError("")
    try {
      await printInvoice(`${base}/${selected}/print`)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold text-navy-900">
        {portal ? "Your invoices" : "Invoices"}
      </h1>
      <p className="text-sm text-slate-500">
        {portal
          ? "View balances and print your invoices."
          : "Generate invoices from a subscription or run billing. Confirm before collecting payment."}
      </p>
      <Card>
        <div className="mb-4 flex gap-3">
          {!portal && (
            <input
              aria-label="Search invoices"
              placeholder="Search invoice number…"
              className="rounded border p-2"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setPage(1)
              }}
            />
          )}
          <select
            aria-label="Invoice filter"
            className="rounded border p-2"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value)
              setPage(1)
            }}
          >
            <option value="">All invoices</option>
            {[
              "draft",
              "confirmed",
              "paid",
              "cancelled",
              "outstanding",
              ...(!portal ? ["overdue"] : []),
            ].map((s) => (
              <option key={s} value={s}>
                {title(s)}
              </option>
            ))}
          </select>
        </div>
        <ErrorMessage error={result.error} />
        {result.loading ? (
          <p>Loading…</p>
        ) : (
          <Table
            rows={result.data?.items || []}
            columns={[
              { key: "number", label: "Invoice" },
              { key: "invoice_date", label: "Issued" },
              { key: "due_date", label: "Due" },
              {
                key: "state",
                label: "State",
                render: (r) => (
                  <Badge value={r.is_overdue ? "overdue" : text(r, "state")} />
                ),
              },
              {
                key: "total",
                label: "Total",
                render: (r) => money(r.total, text(r, "currency")),
              },
              {
                key: "amount_due",
                label: "Outstanding",
                render: (r) => money(r.amount_due, text(r, "currency")),
              },
            ]}
            select={(r) => {
              setSelected(r.id)
              setError("")
              setNotice("")
            }}
          />
        )}
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm">{result.data?.total || 0} invoices</span>
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
      {selected && (
        <Dialog
          title={invoice ? text(invoice, "number") : "Invoice"}
          close={() => setSelected(null)}
        >
          <ErrorMessage error={detail.error || error} />
          {notice && (
            <p role="status" className="mb-3 text-sm text-teal-700">
              {notice}
            </p>
          )}
          {detail.loading ? (
            <p>Loading…</p>
          ) : (
            invoice && (
              <>
                <Details row={invoice} />
                <h3 className="mt-5 font-semibold">Invoice lines</h3>
                <Table
                  rows={(invoice.lines || []) as Row[]}
                  columns={[
                    "description",
                    "quantity",
                    "unit_price",
                    "discount_amount",
                    "tax_amount",
                    "total_amount",
                  ].map((key) => ({ key, label: title(key) }))}
                />
                <div className="mt-5 flex flex-wrap gap-2">
                  <Button secondary onClick={() => void print()}>
                    Print / Save as PDF
                  </Button>
                  {!portal && invoice.state === "draft" && (
                    <Button
                      disabled={busy}
                      onClick={() => void action("confirm")}
                    >
                      Confirm invoice
                    </Button>
                  )}
                  {!portal && invoice.state === "confirmed" && (
                    <Button disabled={busy} onClick={() => setPay(true)}>
                      Record payment
                    </Button>
                  )}
                  {!portal &&
                    ["confirmed", "paid"].includes(text(invoice, "state")) && (
                      <Button
                        secondary
                        disabled={busy}
                        onClick={() => void action("send")}
                      >
                        Send email
                      </Button>
                    )}
                  {!portal &&
                    ["draft", "confirmed"].includes(text(invoice, "state")) &&
                    String(invoice.amount_paid) === "0.00" && (
                      <Button
                        secondary
                        disabled={busy}
                        onClick={() => {
                          if (
                            window.confirm(
                              "Cancel this invoice? Its billing period will remain invoiced.",
                            )
                          )
                            void action("cancel")
                        }}
                      >
                        Cancel invoice
                      </Button>
                    )}
                </div>
                <h3 className="mt-6 font-semibold">Payments</h3>
                <Table
                  rows={(invoice.payments || []) as Row[]}
                  columns={[
                    "payment_date",
                    "method",
                    "amount",
                    "reference",
                    "status",
                  ].map((key) => ({ key, label: title(key) }))}
                />
              </>
            )
          )}
        </Dialog>
      )}
      {pay && invoice && (
        <Dialog title="Record payment" close={() => setPay(false)}>
          <p className="mb-4">
            Outstanding: {money(invoice.amount_due, text(invoice, "currency"))}
          </p>
          <Form
            fields={[
              {
                key: "method",
                label: "Payment method",
                options: choices([
                  "cash",
                  "bank_transfer",
                  "card",
                  "upi",
                  "cheque",
                  "online_gateway",
                ]),
                required: true,
                value: "bank_transfer",
              },
              {
                key: "amount",
                label: "Amount",
                type: "number",
                min: "0.01",
                step: "0.01",
                required: true,
                value: String(invoice.amount_due),
              },
              {
                key: "payment_date",
                label: "Payment date",
                type: "date",
                required: true,
                value: today(),
              },
              { key: "reference", label: "Reference" },
              { key: "note", label: "Note", type: "textarea" },
            ]}
            submit={async (values) => {
              await api(`/invoices/${selected}/payments`, "POST", values)
              setPay(false)
              setRevision((r) => r + 1)
            }}
            cancel={() => setPay(false)}
          />
        </Dialog>
      )}
    </div>
  )
}
