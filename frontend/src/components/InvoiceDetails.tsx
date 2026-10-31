import { useState } from "react";
import {
  api,
  text,
  title,
  money,
  printInvoice,
  today,
  type Row,
  type User,
} from "../lib/api";
import { navigate } from "../lib/navigation";
import {
  Badge,
  Button,
  Card,
  Dialog,
  ErrorMessage,
  Form,
  Table,
  useLoad,
  choices,
} from "./ui";

export default function InvoiceDetails({
  id,
  user,
}: {
  id: number;
  user: User;
}) {
  const portal = user.role === "customer",
    base = portal ? "/portal/invoices" : "/invoices";
  const [revision, setRevision] = useState(0),
    [pay, setPay] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [pending, setPending] = useState<"confirm" | "cancel" | "send" | null>(
      null,
    );
  const selected = id;
  const detail = useLoad<Row>(`${base}/${id}`, revision, true),
    invoice = detail.data;
  const contract = useLoad<Row>(
    invoice
      ? `${portal ? "/portal" : ""}/subscriptions/${invoice.subscription_id}`
      : null,
  );
  const customer = contract.data?.customer as Row | undefined;
  const actionLabels = {
    confirm: "Confirm invoice",
    cancel: "Cancel invoice",
    send: "Send email",
  };
  async function action() {
    if (!pending) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api(`/invoices/${id}/${pending}`, "POST");
      setNotice(
        pending === "send"
          ? "Invoice email queued. Delivery depends on the server email configuration."
          : pending === "confirm"
            ? "Invoice confirmed."
            : "Invoice cancelled.",
      );
      setPending(null);
      setRevision((r) => r + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function print() {
    setError("");
    try {
      await printInvoice(`${base}/${id}/print`);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const link = (path: string, label: string) => (
    <a
      className="font-semibold text-teal-700 underline"
      href={path}
      onClick={(e) => {
        if (
          !e.ctrlKey &&
          !e.metaKey &&
          !e.shiftKey &&
          !e.altKey &&
          e.button === 0
        ) {
          e.preventDefault();
          navigate(path);
        }
      }}
    >
      {label}
    </a>
  );
  return (
    <article aria-label="Invoice details" className="space-y-5">
      <Button secondary onClick={() => navigate(base)}>
        Back to invoices
      </Button>
      <ErrorMessage error={detail.error || error} />
      {notice && (
        <p role="status" className="rounded-lg bg-teal-50 p-3 text-teal-800">
          {notice}
        </p>
      )}
      {detail.loading && !invoice && <p role="status">Loading invoice…</p>}
      {invoice && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm text-slate-500">Invoice</p>
              <h1 className="text-3xl font-bold text-navy-900">
                {text(invoice, "number")}
              </h1>
              <div className="mt-3 flex gap-2">
                <Badge value={text(invoice, "state")} />
                {Boolean(invoice.is_overdue) && <Badge value="overdue" />}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button secondary onClick={() => void print()}>
                Print / Save as PDF
              </Button>
              {!portal && invoice.state === "draft" && (
                <Button
                  disabled={busy || detail.loading}
                  onClick={() => setPending("confirm")}
                >
                  Confirm invoice
                </Button>
              )}
              {!portal && invoice.state === "confirmed" && (
                <Button
                  disabled={busy || detail.loading}
                  onClick={() => setPay(true)}
                >
                  Record payment
                </Button>
              )}
              {!portal &&
                ["confirmed", "paid"].includes(text(invoice, "state")) && (
                  <Button
                    secondary
                    disabled={busy || detail.loading}
                    onClick={() => setPending("send")}
                  >
                    Send email
                  </Button>
                )}
              {!portal &&
                ["draft", "confirmed"].includes(text(invoice, "state")) &&
                /^0(?:\.0+)?$/.test(String(invoice.amount_paid)) && (
                  <Button
                    secondary
                    disabled={busy || detail.loading}
                    onClick={() => setPending("cancel")}
                  >
                    Cancel invoice
                  </Button>
                )}
            </div>
          </div>
          {Boolean(invoice.is_overdue) && (
            <p className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-rose-800">
              This invoice is overdue. Outstanding balance:{" "}
              {money(invoice.amount_due, text(invoice, "currency"))}.
            </p>
          )}
          {invoice.state === "cancelled" && (
            <p className="rounded-lg bg-slate-100 p-3">
              This invoice is cancelled. Its billing period remains invoiced.
            </p>
          )}
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Invoice total", invoice.total],
              ["Amount paid", invoice.amount_paid],
              ["Remaining balance", invoice.amount_due],
            ].map(([label, value]) => (
              <Card key={String(label)}>
                <p className="text-sm text-slate-500">{String(label)}</p>
                <p className="mt-2 text-2xl font-bold text-navy-900">
                  {money(value, text(invoice, "currency"))}
                </p>
              </Card>
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <h2 className="mb-3 font-bold">Bill to</h2>
              <ErrorMessage error={contract.error} />
              {contract.loading && <p>Loading customer…</p>}
              {customer && (
                <>
                  <p className="font-semibold">{text(customer, "name")}</p>
                  <p>{text(customer, "company_name")}</p>
                  <p>{text(customer, "email")}</p>
                  <p>{text(customer, "phone")}</p>
                  <p>
                    {[
                      customer.address_line1,
                      customer.address_line2,
                      customer.city,
                      customer.state,
                      customer.postal_code,
                      customer.country,
                    ]
                      .filter(Boolean)
                      .join(", ")}
                  </p>
                </>
              )}
              <p className="mt-4">
                Subscription:{" "}
                {link(
                  `${portal ? "/portal" : ""}/subscriptions/${invoice.subscription_id}`,
                  contract.data
                    ? text(contract.data, "number")
                    : `Subscription #${invoice.subscription_id}`,
                )}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Customer contact details reflect the current customer record.
              </p>
            </Card>
            <Card>
              <h2 className="mb-3 font-bold">Billing dates</h2>
              <dl className="grid grid-cols-2 gap-3">
                {[
                  ["Invoice date", invoice.invoice_date],
                  ["Due date", invoice.due_date],
                  ["Period start", invoice.period_start],
                  ["Period end", invoice.period_end],
                  ["Currency", invoice.currency],
                ].map(([label, value]) => (
                  <div key={String(label)}>
                    <dt className="text-sm text-slate-500">{String(label)}</dt>
                    <dd className="font-medium">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
          <Card>
            <h2 className="mb-4 font-bold">Invoice lines</h2>
            <div className="overflow-x-auto">
              <Table
                rows={(invoice.lines || []) as Row[]}
                columns={[
                  { key: "description", label: "Product / description" },
                  { key: "quantity", label: "Quantity" },
                  ...["unit_price", "discount_amount", "untaxed_amount"].map(
                    (key) => ({
                      key,
                      label: title(key),
                      render: (r: Row) =>
                        money(r[key], text(invoice, "currency")),
                    }),
                  ),
                  {
                    key: "taxes",
                    label: "Taxes",
                    render: (r: Row) => (
                      <span>
                        {((r.taxes || []) as Row[])
                          .map(
                            (t) =>
                              `${t.tax_name} (${t.rate}): ${money(t.amount, text(invoice, "currency"))}`,
                          )
                          .join("; ") || "No tax"}
                      </span>
                    ),
                  },
                  ...["tax_amount", "total_amount"].map((key) => ({
                    key,
                    label: title(key),
                    render: (r: Row) =>
                      money(r[key], text(invoice, "currency")),
                  })),
                ]}
              />
            </div>
            <dl className="ml-auto mt-5 max-w-sm space-y-2">
              {[
                ["Subtotal", invoice.subtotal],
                ["Discount", invoice.discount_total],
                ["Untaxed total", invoice.untaxed_total],
                ["Tax", invoice.tax_total],
                ["Total", invoice.total],
              ].map(([label, value]) => (
                <div className="flex justify-between gap-4" key={String(label)}>
                  <dt>{String(label)}</dt>
                  <dd className="font-semibold">
                    {money(value, text(invoice, "currency"))}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>
          <Card>
            <h2 className="mb-4 font-bold">Payment history</h2>
            <div className="overflow-x-auto">
              <Table
                rows={(invoice.payments || []) as Row[]}
                columns={[
                  { key: "payment_date", label: "Date" },
                  {
                    key: "method",
                    label: "Method",
                    render: (r) => title(text(r, "method")),
                  },
                  {
                    key: "amount",
                    label: "Amount",
                    render: (r) => money(r.amount, text(invoice, "currency")),
                  },
                  { key: "reference", label: "Reference" },
                  { key: "note", label: "Note" },
                  {
                    key: "status",
                    label: "Status",
                    render: (r) => <Badge value={text(r, "status")} />,
                  },
                ]}
              />
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 font-bold">Invoice activity</h2>
            <dl className="grid gap-3 sm:grid-cols-2">
              {[
                "created_at",
                "confirmed_at",
                "sent_at",
                "paid_at",
                "cancelled_at",
              ]
                .filter((key) => invoice[key])
                .map((key) => (
                  <div key={key}>
                    <dt className="text-sm text-slate-500">{title(key)}</dt>
                    <dd>{new Date(String(invoice[key])).toLocaleString()}</dd>
                  </div>
                ))}
            </dl>
          </Card>
        </>
      )}
      {pending && (
        <Dialog
          title={actionLabels[pending]}
          close={() => {
            if (!busy) setPending(null);
          }}
        >
          <p className="mb-4">
            {pending === "cancel"
              ? "Cancel this invoice? Its billing period will remain invoiced."
              : pending === "confirm"
                ? "Confirm this invoice to allow payment recording."
                : "Send this invoice to the customer’s registered email address?"}
          </p>
          <ErrorMessage error={error} />
          <div className="flex gap-2">
            <Button disabled={busy} onClick={() => void action()}>
              {actionLabels[pending]}
            </Button>
            <Button secondary disabled={busy} onClick={() => setPending(null)}>
              Go back
            </Button>
          </div>
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
              await api(`/invoices/${selected}/payments`, "POST", values);
              setPay(false);
              setNotice("Payment recorded.");
              setRevision((r) => r + 1);
            }}
            cancel={() => setPay(false)}
          />
        </Dialog>
      )}
    </article>
  );
}
