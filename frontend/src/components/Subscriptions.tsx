import { useEffect, useState } from "react"
import {
  api,
  options,
  text,
  title,
  today,
  money,
  type Page,
  type Row,
  type User,
} from "../lib/api"
import {
  Badge,
  Button,
  Card,
  clean,
  Details,
  Dialog,
  ErrorMessage,
  Form,
  references,
  Table,
  useLoad,
  choices,
  type Field,
} from "./ui"
import { emptyLine, LinesEditor, serializeLines } from "./Resources"
const transitions: Record<string, string[]> = {
  draft: ["quotation"],
  quotation: ["draft", "confirmed", "closed"],
  confirmed: ["active", "closed"],
  active: ["paused", "closed"],
  paused: ["active", "closed"],
  closed: [],
}
export default function Subscriptions({ user }: { user: User }) {
  const portal = user.role === "customer",
    base = portal ? "/portal/subscriptions" : "/subscriptions"
  const [page, setPage] = useState(1),
    [query, setQuery] = useState(""),
    [state, setState] = useState(""),
    [revision, setRevision] = useState(0),
    [selected, setSelected] = useState<number | null>(() => {
      const match = location.pathname.match(/\/subscriptions\/(\d+)\/?$/)
      return match ? Number(match[1]) : null
    }),
    [form, setForm] = useState<"new" | "template" | "edit" | "renew" | null>(
      null,
    ),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false)
  const [refs, setRefs] = useState<Record<string, Row[]>>({}),
    [refError, setRefError] = useState(""),
    [refsLoading, setRefsLoading] = useState(false)
  const result = useLoad<Page>(
    `${base}?page=${page}&size=20&state=${state}${
      !portal ? `&q=${encodeURIComponent(query)}` : ""
    }`
      .replace("&state=&", "&")
      .replace(/&state=$/, ""),
    revision,
  )
  const detail = useLoad<Row>(selected ? `${base}/${selected}` : null, revision)
  useEffect(() => {
    if (!form || portal) return
    let current = true
    setRefError("")
    setRefsLoading(true)
    Promise.all([
      options("/customers"),
      options("/plans"),
      options("/products"),
      api<Row[]>("/payment-terms"),
      options("/quotation-templates"),
    ])
      .then(([customers, plans, products, terms, templates]) => {
        if (current) setRefs({ customers, plans, products, terms, templates })
      })
      .catch((e) => {
        if (current) setRefError(e.message)
      })
      .finally(() => {
        if (current) setRefsLoading(false)
      })
    return () => {
      current = false
    }
  }, [form, portal])
  function refresh() {
    setRevision((r) => r + 1)
    setForm(null)
  }
  async function action(path: string, body?: unknown, method = "POST") {
    setBusy(true)
    setError("")
    try {
      await api(path, method, body)
      refresh()
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    } finally {
      setBusy(false)
    }
  }
  const sub = detail.data,
    subState = sub ? text(sub, "state") : ""
  const allowed = (transitions[subState] || []).filter(
    (s) =>
      !portal ||
      ["paused", "closed"].includes(s) ||
      (s === "active" && subState === "paused"),
  )
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-navy-900">
            {portal ? "Your subscriptions" : "Subscriptions"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Contracts, lifecycle and recurring billing.
          </p>
        </div>
        {!portal && (
          <div className="flex gap-2">
            <Button secondary onClick={() => setForm("template")}>
              From template
            </Button>
            <Button onClick={() => setForm("new")}>New subscription</Button>
          </div>
        )}
      </div>
      <ErrorMessage error={error} />
      <Card>
        <div className="mb-4 flex gap-3">
          {!portal && (
            <input
              aria-label="Search subscriptions"
              className="rounded border p-2"
              placeholder="Search number…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setPage(1)
              }}
            />
          )}
          <select
            aria-label="Subscription state"
            className="rounded border p-2"
            value={state}
            onChange={(e) => {
              setState(e.target.value)
              setPage(1)
            }}
          >
            <option value="">All states</option>
            {Object.keys(transitions).map((s) => (
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
              { key: "number", label: "Subscription" },
              { key: "customer_id", label: "Customer ID" },
              { key: "plan_id", label: "Plan ID" },
              {
                key: "state",
                label: "State",
                render: (r) => <Badge value={text(r, "state")} />,
              },
              {
                key: "recurring_total",
                label: "Recurring",
                render: (r) => money(r.recurring_total, text(r, "currency")),
              },
              { key: "next_invoice_date", label: "Next invoice" },
            ]}
            select={(r) => {
              setSelected(r.id)
              setError("")
            }}
          />
        )}
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm">
            {result.data?.total || 0} subscriptions
          </span>
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
          title={sub ? text(sub, "number") : "Subscription"}
          close={() => {
            setSelected(null)
            setError("")
          }}
        >
          <ErrorMessage error={detail.error || error} />
          {detail.loading ? (
            <p>Loading…</p>
          ) : (
            sub && (
              <>
                <Details row={sub} />
                <div className="mt-5">
                  <h3 className="font-semibold">Product lines</h3>
                  <Table
                    rows={(sub.lines || []) as Row[]}
                    columns={[
                      "description",
                      "quantity",
                      "unit_price",
                      "discount_amount",
                      "tax_amount",
                      "total_amount",
                    ].map((key) => ({ key, label: title(key) }))}
                  />
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  {allowed.map((next) => (
                    <Button
                      secondary
                      key={next}
                      disabled={busy}
                      onClick={() => {
                        const reason =
                          next === "closed"
                            ? window.prompt("Reason for closing (optional)")
                            : undefined
                        if (reason === null) return
                        void action(`${base}/${selected}/state`, {
                          state: next,
                          ...(reason ? { reason } : {}),
                        })
                      }}
                    >
                      {next === "active" && subState === "paused"
                        ? "Resume"
                        : title(next)}
                    </Button>
                  ))}
                  {!portal && ["draft", "quotation"].includes(subState) && (
                    <Button secondary onClick={() => setForm("edit")}>
                      Edit
                    </Button>
                  )}
                  {!portal && subState === "draft" && (
                    <Button
                      secondary
                      disabled={busy}
                      onClick={() => {
                        if (window.confirm("Delete this draft subscription?"))
                          void action(
                            `${base}/${selected}`,
                            undefined,
                            "DELETE",
                          ).then((deleted) => { if (deleted) setSelected(null) })
                      }}
                    >
                      Delete draft
                    </Button>
                  )}
                  {!portal && subState === "active" && (
                    <Button
                      disabled={busy}
                      onClick={() =>
                        void action(`${base}/${selected}/invoices`)
                      }
                    >
                      Invoice next period
                    </Button>
                  )}
                  {!portal && ["active", "paused"].includes(subState) && (
                    <Button secondary onClick={() => setForm("renew")}>
                      Renew
                    </Button>
                  )}
                </div>
                <h3 className="mb-2 mt-6 font-semibold">State history</h3>
                <Table
                  rows={(sub.state_logs || []) as Row[]}
                  columns={[
                    "from_state",
                    "to_state",
                    "reason",
                    "created_at",
                  ].map((key) => ({ key, label: title(key) }))}
                />
              </>
            )
          )}
        </Dialog>
      )}
      {form && (
        <Dialog
          title={
            form === "renew"
              ? "Renew subscription"
              : form === "edit"
                ? "Edit subscription"
                : form === "template"
                  ? "Create from template"
                  : "Create subscription"
          }
          close={() => setForm(null)}
        >
          <ErrorMessage error={refError} />
          {form === "renew" ? (
            <Form
              fields={[
                {
                  key: "new_expiry_date",
                  label: "New expiry date",
                  type: "date",
                  required: true,
                },
              ]}
              submit={async (values) => {
                await api(`/subscriptions/${selected}/renew`, "POST", values)
                refresh()
              }}
              cancel={() => setForm(null)}
            />
          ) : refsLoading ? (
            <p>Loading available customers, products and plans…</p>
          ) : (
            !refError && (
              <SubscriptionForm
                key={`${form}-${selected}`}
                mode={form}
                initial={form === "edit" ? sub : null}
                refs={refs}
                save={async (body) => {
                  await api(
                    form === "edit"
                      ? `/subscriptions/${selected}`
                      : form === "template"
                        ? "/subscriptions/from-template"
                        : "/subscriptions",
                    form === "edit" ? "PATCH" : "POST",
                    body,
                  )
                  refresh()
                }}
                cancel={() => setForm(null)}
              />
            )
          )}
        </Dialog>
      )}
    </div>
  )
}
function SubscriptionForm({
  mode,
  initial,
  refs,
  save,
  cancel,
}: {
  mode: string
  initial: Row | null
  refs: Record<string, Row[]>
  save: (body: unknown) => Promise<void>
  cancel: () => void
}) {
  const [lines, setLines] = useState(() =>
    initial
      ? (initial.lines as Row[]).map((l) => ({
          product_id: String(l.product_id),
          variant_id: l.variant_id ? String(l.variant_id) : "",
          quantity: String(l.quantity),
          unit_price: String(l.unit_price),
        }))
      : [emptyLine()],
  )
  const fields: Field[] = [
    ...(mode !== "edit"
      ? [
          {
            key: "customer_id",
            label: "Customer",
            options: references(refs.customers || []),
            required: true,
          },
        ]
      : []),
    mode === "template"
      ? {
          key: "template_id",
          label: "Quotation template",
          options: references(refs.templates || []),
          required: true,
        }
      : {
          key: "plan_id",
          label: "Plan",
          options: references(refs.plans || []),
          required: true,
        },
    {
      key: "payment_term_id",
      label: "Payment terms",
      options: references(refs.terms || []),
      required: true,
    },
    {
      key: "start_date",
      label: "Start date",
      type: "date",
      value: today(),
      required: true,
    },
    { key: "expiry_date", label: "Expiry date", type: "date" },
    { key: "currency", label: "Currency", value: "INR", required: true },
    ...(mode !== "template"
      ? [{ key: "notes", label: "Notes", type: "textarea" }]
      : []),
  ]
  return (
    <Form
      fields={fields}
      initial={initial || {}}
      submit={async (values) => {
        const body = clean(values, [
          "customer_id",
          "plan_id",
          "template_id",
          "payment_term_id",
        ])
        if (!values.expiry_date && initial?.expiry_date) body.expiry_date = null
        if (mode !== "template") body.lines = serializeLines(lines)
        await save(body)
      }}
      cancel={cancel}
    >
      {mode !== "template" && (
        <LinesEditor
          products={refs.products || []}
          lines={lines}
          setLines={setLines}
        />
      )}
    </Form>
  )
}
