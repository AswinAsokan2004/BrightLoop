import { useEffect, useState } from "react";
import {
  api,
  options,
  text,
  today,
  money,
  type Page,
  type Row,
  type User,
} from "../lib/api";
import { navigate } from "../lib/navigation";
import {
  displayDate,
  type StateAction,
  type Subscription,
} from "../lib/subscriptions";
import {
  Badge,
  Button,
  Card,
  clean,
  Dialog,
  ErrorMessage,
  Form,
  references,
  Table,
  useLoad,
  type Field,
} from "./ui";
import { emptyLine, LinesEditor, serializeLines } from "./Resources";
import SubscriptionDetails from "./SubscriptionDetails";
const states = [
  "draft",
  "quotation",
  "confirmed",
  "active",
  "paused",
  "closed",
];
const selectedFromUrl = () => {
  const match = location.pathname.match(/\/subscriptions\/(\d+)\/?$/);
  return match ? Number(match[1]) : null;
};
type Confirmation =
  | { kind: "state"; action: StateAction }
  | { kind: "invoice" | "delete" };
export default function Subscriptions({ user }: { user: User }) {
  const portal = user.role === "customer",
    base = portal ? "/portal/subscriptions" : "/subscriptions";
  const [page, setPage] = useState(1),
    [query, setQuery] = useState(""),
    [state, setState] = useState(""),
    [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<number | null>(selectedFromUrl),
    [form, setForm] = useState<"new" | "template" | "edit" | "renew" | null>(
      null,
    );
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [createdInvoice, setCreatedInvoice] = useState<Row | null>(null);
  const [refs, setRefs] = useState<Record<string, Row[]>>({}),
    [refError, setRefError] = useState(""),
    [refsLoading, setRefsLoading] = useState(false);
  useEffect(() => {
    const back = () => {
      setSelected(selectedFromUrl());
      setForm(null);
      setConfirmation(null);
      setError("");
      setNotice("");
      setCreatedInvoice(null);
    };
    window.addEventListener("popstate", back);
    return () => window.removeEventListener("popstate", back);
  }, []);
  const params = new URLSearchParams({ page: String(page), size: "20" });
  if (state) params.set("state", state);
  if (query && !portal) params.set("q", query);
  const result = useLoad<Page>(selected ? null : `${base}?${params}`, revision);
  const detail = useLoad<Subscription>(
    selected ? `${base}/${selected}` : null,
    revision,
    true,
  );
  const sub = detail.data?.id === selected ? detail.data : null;
  useEffect(() => {
    if (!form || form === "renew" || portal) return;
    let current = true;
    setRefError("");
    setRefsLoading(true);
    Promise.all([
      options("/customers"),
      options("/plans"),
      options("/products"),
      api<Row[]>("/payment-terms"),
      options("/quotation-templates"),
    ])
      .then(([customers, plans, products, terms, templates]) => {
        if (current) setRefs({ customers, plans, products, terms, templates });
      })
      .catch((e) => {
        if (current) setRefError(e.message);
      })
      .finally(() => {
        if (current) setRefsLoading(false);
      });
    return () => {
      current = false;
    };
  }, [form, portal]);
  async function mutate(
    path: string,
    body: unknown,
    message: string,
    method = "POST",
  ) {
    setBusy(true);
    setError("");
    setNotice("");
    setCreatedInvoice(null);
    try {
      const result = await api<Row | undefined>(path, method, body);
      setForm(null);
      setConfirmation(null);
      setRevision((r) => r + 1);
      setNotice(message);
      return result;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setBusy(false);
    }
  }
  function changeState(action: StateAction) {
    if (action.disabled || busy) return;
    if (action.state === "quotation" || action.state === "draft") {
      void mutate(
        `${base}/${selected}/state`,
        { state: action.state },
        action.state === "quotation"
          ? "Quotation created. Review its validity before confirming."
          : "Returned to draft. You can now revise the quotation.",
      ).catch(() => {});
    } else setConfirmation({ kind: "state", action });
  }
  const confirmLabel =
    confirmation?.kind === "state"
      ? confirmation.action.label
      : confirmation?.kind === "invoice"
        ? "Generate draft invoice"
        : "Delete draft";
  const confirmExplanation =
    confirmation?.kind === "invoice"
      ? `Generate a draft invoice for the next unbilled period beginning ${displayDate(sub?.next_invoice_date)}. This can invoice a future period. Prices, taxes and discounts are recalculated by the backend.`
      : confirmation?.kind === "delete"
        ? "Permanently delete this draft and its lines. This cannot be undone."
        : confirmation?.kind === "state"
          ? {
              confirmed:
                "Accept this quotation and move it to Confirmed. Its plan, dates and product lines can no longer be edited after confirmation.",
              active:
                sub?.state === "paused"
                  ? "Resume the subscription at its next eligible billing date. Paused periods are not billed retroactively."
                  : "Activate this subscription and schedule recurring billing. Activation does not itself create an invoice.",
              paused:
                "Pause future recurring billing. Existing invoices and outstanding balances remain payable.",
              closed:
                "Stop future billing and close this record permanently. Existing invoices and payments are retained.",
              draft: "Return this quotation to draft.",
              quotation: "Create a quotation from this draft.",
            }[confirmation.action.state]
          : "";
  return (
    <>
      {selected ? (
        sub ? (
          <SubscriptionDetails
            key={selected}
            subscription={sub}
            portal={portal}
            revision={revision}
            busy={busy || detail.loading}
            error={error || detail.error}
            notice={notice}
            createdInvoice={createdInvoice}
            back={() => navigate(base)}
            edit={() => setForm("edit")}
            renew={() => setForm("renew")}
            invoice={() => setConfirmation({ kind: "invoice" })}
            remove={() => setConfirmation({ kind: "delete" })}
            changeState={changeState}
          />
        ) : (
          <div className="space-y-5">
            <Button secondary onClick={() => navigate(base)}>
              Back to subscriptions
            </Button>
            {detail.loading ? (
              <Card>
                <p role="status">Loading subscription details…</p>
              </Card>
            ) : (
              <ErrorMessage error={detail.error || "Subscription not found."} />
            )}
          </div>
        )
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-3xl font-bold text-navy-900">
                {portal ? "Your subscriptions" : "Subscriptions"}
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Open a record to review its quotation, billing and history.
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
          {notice && (
            <p role="status" className="text-sm text-teal-800">
              {notice}
            </p>
          )}
          <Card>
            <div className="mb-4 flex flex-wrap gap-3">
              {!portal && (
                <input
                  aria-label="Search subscriptions"
                  className="rounded-lg border p-2"
                  placeholder="Search number…"
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setPage(1);
                  }}
                />
              )}
              <select
                aria-label="Subscription state"
                className="rounded-lg border p-2"
                value={state}
                onChange={(e) => {
                  setState(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All states</option>
                {states.map((s) => (
                  <option key={s} value={s}>
                    {s[0].toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <ErrorMessage error={result.error} />
            {result.loading ? (
              <p role="status">Loading subscriptions…</p>
            ) : (
              <Table
                rows={result.data?.items || []}
                columns={[
                  { key: "number", label: "Subscription" },
                  { key: "customer_name", label: "Customer" },
                  { key: "plan_name", label: "Plan" },
                  {
                    key: "state",
                    label: "State",
                    render: (r) => <Badge value={text(r, "state")} />,
                  },
                  {
                    key: "recurring_total",
                    label: "Recurring",
                    render: (r) =>
                      money(r.recurring_total, text(r, "currency")),
                  },
                  {
                    key: "next_invoice_date",
                    label: "Next invoice",
                    render: (r) =>
                      r.next_invoice_date
                        ? displayDate(String(r.next_invoice_date))
                        : "Not scheduled",
                  },
                ]}
                select={(r) => navigate(`${base}/${r.id}`)}
              />
            )}
            <div className="mt-4 flex items-center justify-between text-sm">
              <span>{result.data?.total || 0} subscriptions</span>
              <div className="flex items-center gap-3">
                <Button
                  secondary
                  disabled={page === 1 || result.loading}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <span>Page {page}</span>
                <Button
                  secondary
                  disabled={
                    page * 20 >= (result.data?.total || 0) || result.loading
                  }
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
      {confirmation && sub && (
        <Dialog
          title={confirmLabel}
          close={() => {
            if (!busy) setConfirmation(null);
          }}
        >
          <p className="mb-5 text-sm leading-6 text-slate-600">
            {confirmExplanation}
          </p>
          <Form
            key={confirmLabel}
            fields={
              confirmation.kind === "state" &&
              confirmation.action.state === "closed"
                ? [
                    {
                      key: "reason",
                      label: "Reason for closing",
                      type: "textarea",
                    },
                  ]
                : []
            }
            label={confirmLabel}
            cancel={() => setConfirmation(null)}
            submit={async (values) => {
              if (confirmation.kind === "state")
                await mutate(
                  `${base}/${selected}/state`,
                  {
                    state: confirmation.action.state,
                    ...(values.reason ? { reason: values.reason } : {}),
                  },
                  `${confirmation.action.label} completed.`,
                );
              else if (confirmation.kind === "invoice") {
                const result = await mutate(
                  `/subscriptions/${selected}/invoices`,
                  undefined,
                  "Draft invoice generated. Confirm it before recording payment.",
                );
                if (result) setCreatedInvoice(result);
              } else {
                await mutate(
                  `/subscriptions/${selected}`,
                  undefined,
                  "Draft subscription deleted.",
                  "DELETE",
                );
                navigate(base);
                setNotice("Draft subscription deleted.");
              }
            }}
          />
        </Dialog>
      )}
      {form && (
        <Dialog
          title={
            form === "renew"
              ? "Renew subscription"
              : form === "edit"
                ? sub?.state === "quotation"
                  ? "Edit quotation"
                  : "Edit draft"
                : form === "template"
                  ? "Create from template"
                  : "Create subscription"
          }
          close={() => {
            if (!busy) setForm(null);
          }}
        >
          <ErrorMessage error={refError} />
          {form === "renew" && sub ? (
            <>
              <p className="mb-4 text-sm text-slate-500">
                Current expiry: {displayDate(sub.expiry_date)}. Renewal extends
                this contract; it does not replace existing invoices.
              </p>
              <Form
                fields={[
                  {
                    key: "new_expiry_date",
                    label: "New expiry date",
                    type: "date",
                    required: true,
                    min: sub.expiry_date
                      ? new Date(
                          Date.parse(`${sub.expiry_date}T00:00:00Z`) + 86400000,
                        )
                          .toISOString()
                          .slice(0, 10)
                      : undefined,
                  },
                ]}
                label="Renew subscription"
                submit={async (values) => {
                  await mutate(
                    `/subscriptions/${selected}/renew`,
                    values,
                    `Subscription renewed through ${displayDate(String(values.new_expiry_date))}.`,
                  );
                }}
                cancel={() => setForm(null)}
              />
            </>
          ) : refsLoading ? (
            <p role="status">
              Loading available customers, products and plans…
            </p>
          ) : (
            !refError && (
              <SubscriptionForm
                key={`${form}-${selected}`}
                mode={form}
                initial={form === "edit" ? sub : null}
                refs={refs}
                save={async (body) => {
                  const created = await mutate(
                    form === "edit"
                      ? `/subscriptions/${selected}`
                      : form === "template"
                        ? "/subscriptions/from-template"
                        : "/subscriptions",
                    body,
                    form === "edit"
                      ? "Changes saved. Pricing preview has been recalculated."
                      : "Subscription created.",
                    form === "edit" ? "PATCH" : "POST",
                  );
                  if (form !== "edit" && created)
                    navigate(`${base}/${created.id}`);
                }}
                cancel={() => setForm(null)}
              />
            )
          )}
        </Dialog>
      )}
    </>
  );
}
function SubscriptionForm({
  mode,
  initial,
  refs,
  save,
  cancel,
}: {
  mode: string;
  initial: Row | null;
  refs: Record<string, Row[]>;
  save: (body: unknown) => Promise<void>;
  cancel: () => void;
}) {
  const [lines, setLines] = useState(() =>
    initial
      ? (initial.lines as Row[]).map((l) => ({
          product_id: String(l.product_id),
          variant_id: l.variant_id ? String(l.variant_id) : "",
          quantity: String(l.quantity),
          unit_price: String(l.unit_price),
          description:
            l.description == null ? undefined : String(l.description),
          tax_ids: ((l.taxes || []) as Row[]).map((tax) => tax.id),
        }))
      : [emptyLine()],
  );
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
  ];
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
        ]);
        if (!values.expiry_date && initial?.expiry_date)
          body.expiry_date = null;
        if (mode !== "template") body.lines = serializeLines(lines);
        await save(body);
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
  );
}
