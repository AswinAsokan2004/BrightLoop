import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  Check,
  Clock3,
  FileText,
  History,
  ReceiptText,
  ShieldCheck,
} from "lucide-react";
import { money, title, type Page, type Row } from "../lib/api";
import {
  availableActions,
  displayDate,
  lineSubtotal,
  quoteExpired,
  renewalDisabled,
  sumAmounts,
  type StateAction,
  type Subscription,
} from "../lib/subscriptions";
import { Badge, Button, Card, ErrorMessage, useLoad } from "./ui";
import AddonManager from "./AddonManager";

type Props = {
  subscription: Subscription;
  portal: boolean;
  revision: number;
  busy: boolean;
  error: string;
  notice: string;
  createdInvoice: Row | null;
  back: () => void;
  edit: () => void;
  renew: () => void;
  invoice: () => void;
  remove: () => void;
  changeState: (action: StateAction) => void;
  addonsChanged: () => void;
};
const steps = ["draft", "quotation", "confirmed", "active", "closed"] as const;
const cycle = (sub: Subscription) => {
  const unit: Record<string, string> = {
    daily: "day",
    weekly: "week",
    monthly: "month",
    yearly: "year",
  };
  const count = sub.plan.billing_interval;
  return `Every ${count === 1 ? "" : `${count} `}${unit[sub.plan.billing_period]}${count === 1 ? "" : "s"}`;
};
function Datum({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-medium text-navy-900">
        {children}
      </dd>
    </div>
  );
}
export default function SubscriptionDetails(props: Props) {
  const { subscription: sub, portal, revision, busy } = props;
  const [tab, setTab] = useState<
    "overview" | "invoices" | "activity" | "addons"
  >(() => {
    const initial = new URLSearchParams(location.search).get("tab");
    return initial === "invoices" ||
      initial === "activity" ||
      (portal && initial === "addons")
      ? initial
      : "overview";
  });
  const [invoicePage, setInvoicePage] = useState(1);
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (tab === "overview") params.delete("tab");
    else params.set("tab", tab);
    const query = params.toString();
    history.replaceState(
      null,
      "",
      `${location.pathname}${query ? `?${query}` : ""}`,
    );
  }, [tab]);
  const sections = portal
    ? (["overview", "invoices", "addons", "activity"] as const)
    : (["overview", "invoices", "activity"] as const);
  const invoices = useLoad<Page>(
    `${portal ? "/portal" : ""}/invoices?subscription_id=${sub.id}&page=${invoicePage}&size=10`,
    revision,
  );
  const actions = availableActions(sub, portal),
    expired = quoteExpired(sub);
  const primaryAction = actions.find((action) =>
    ["quotation", "confirmed", "active"].includes(action.state),
  );
  const secondaryActions = actions.filter((action) => action !== primaryAction);
  const current = sub.state === "paused" ? "active" : sub.state;
  const visited = new Set(sub.state_logs.map((log) => log.to_state));
  const subtotal = sumAmounts(sub.lines.map(lineSubtotal)),
    discount = sumAmounts(sub.lines.map((line) => line.discount_amount));
  const invoicePath = (id: number) =>
    `${portal ? "/portal" : ""}/invoices/${id}`;
  const editAllowed = !portal && ["draft", "quotation"].includes(sub.state);
  return (
    <article
      aria-label="Quotation and subscription details"
      className="space-y-6"
    >
      <button
        onClick={props.back}
        className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-teal-800"
      >
        <ArrowLeft className="size-4" />
        Back to subscriptions
      </button>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">
            {portal ? "Your subscription" : "Quotation & subscription"}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-navy-900">
              {sub.number}
            </h1>
            <Badge value={sub.state} />
            {expired && <Badge value="expired" />}
          </div>
          <p className="mt-2 text-sm text-slate-500">
            {sub.customer_name} <span aria-hidden="true">·</span>{" "}
            {sub.plan_name}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {primaryAction && (
            <Button
              disabled={busy || !!primaryAction.disabled}
              onClick={() => props.changeState(primaryAction)}
            >
              {primaryAction.label}
            </Button>
          )}
          {editAllowed && (
            <Button secondary disabled={busy} onClick={props.edit}>
              {sub.state === "quotation" ? "Edit quotation" : "Edit draft"}
            </Button>
          )}
          {!portal && ["active", "paused"].includes(sub.state) && (
            <Button
              secondary
              disabled={busy || !!renewalDisabled(sub)}
              onClick={props.renew}
            >
              Renew subscription
            </Button>
          )}
          {!portal && sub.state === "active" && (
            <Button
              disabled={busy || !sub.next_invoice_date}
              onClick={props.invoice}
            >
              Invoice next period
            </Button>
          )}
        </div>
      </header>
      {primaryAction?.disabled && (
        <p className="text-sm text-amber-800">{primaryAction.disabled}</p>
      )}
      <ErrorMessage error={props.error} />
      {props.notice && (
        <div
          role="status"
          className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900"
        >
          {props.notice}
          {props.createdInvoice && (
            <>
              {" "}
              <a
                className="font-bold underline"
                href={invoicePath(props.createdInvoice.id)}
              >
                View {String(props.createdInvoice.number)}
              </a>
            </>
          )}
        </div>
      )}
      <section
        aria-label="Subscription lifecycle"
        className="rounded-xl border border-slate-200 bg-white p-5"
      >
        <ol className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {steps.map((step, index) => {
            const isCurrent = current === step,
              completed = visited.has(step) && !isCurrent;
            return (
              <li
                key={step}
                aria-current={isCurrent ? "step" : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-3 ${isCurrent ? "bg-teal-50 ring-1 ring-teal-200" : ""}`}
              >
                <span
                  className={`grid size-8 shrink-0 place-items-center rounded-full text-sm font-bold ${isCurrent ? "bg-teal-700 text-white" : completed ? "bg-teal-100 text-teal-800" : "bg-slate-100 text-slate-400"}`}
                >
                  {completed ? <Check className="size-4" /> : index + 1}
                </span>
                <div
                  className={`text-sm font-semibold ${isCurrent ? "text-teal-900" : "text-slate-500"}`}
                >
                  {title(step)}
                  {step === "active" && sub.state === "paused" && (
                    <span className="block text-xs font-normal">
                      Currently paused
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </section>
      {sub.state === "quotation" && (
        <div
          className={`flex items-start gap-3 rounded-xl border px-5 py-4 ${expired ? "border-rose-200 bg-rose-50 text-rose-900" : "border-amber-200 bg-amber-50 text-amber-950"}`}
        >
          <Clock3 className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-semibold">
              {expired
                ? "Quotation expired"
                : sub.quotation_valid_until
                  ? `Quotation valid through ${displayDate(sub.quotation_valid_until)}`
                  : "Quotation validity has not been set"}
            </p>
            <p className="mt-1 text-sm">
              {expired
                ? "Return this quotation to draft, review its terms, and create a new quotation before confirming."
                : "Review the customer, line items and payment terms before confirmation. Confirming locks the commercial terms."}
            </p>
          </div>
        </div>
      )}
      {sub.state === "closed" && (
        <div className="rounded-xl border border-slate-200 bg-slate-100 p-4 text-sm">
          <p className="font-semibold text-navy-900">
            This subscription is closed.
          </p>
          <p className="mt-1">
            {sub.close_reason ||
              "Billing has stopped. The contract and its invoices remain available for reference."}
          </p>
        </div>
      )}
      <div
        role="tablist"
        aria-label="Subscription sections"
        className="flex gap-2 overflow-x-auto border-b border-slate-200"
      >
        {sections.map((name) => {
          const Icon =
            name === "overview"
              ? FileText
              : name === "invoices"
                ? ReceiptText
                : History;
          return (
            <button
              key={name}
              role="tab"
              id={`tab-${name}`}
              aria-selected={tab === name}
              tabIndex={tab === name ? 0 : -1}
              onKeyDown={(event) => {
                const names: readonly (typeof name)[] = sections;
                const index = names.indexOf(name);
                const next =
                  event.key === "ArrowRight"
                    ? names[(index + 1) % names.length]
                    : event.key === "ArrowLeft"
                      ? names[(index + names.length - 1) % names.length]
                      : event.key === "Home"
                        ? names[0]
                        : event.key === "End"
                          ? names[names.length - 1]
                          : null;
                if (next) {
                  event.preventDefault();
                  setTab(next);
                  document.getElementById(`tab-${next}`)?.focus();
                }
              }}
              aria-controls={`panel-${name}`}
              onClick={() => setTab(name)}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold ${tab === name ? "border-teal-700 text-teal-800" : "border-transparent text-slate-500 hover:text-navy-900"}`}
            >
              <Icon className="size-4" />
              {name === "addons" ? "Add-ons" : title(name)}
              {name === "invoices" && invoices.data && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">
                  {invoices.data.total}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {tab === "overview" && (
        <section
          role="tabpanel"
          id="panel-overview"
          aria-labelledby="tab-overview"
          className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]"
        >
          <div className="min-w-0 space-y-6">
            <div className="grid gap-5 md:grid-cols-2">
              <Card>
                <h2 className="mb-4 text-base font-bold text-navy-900">
                  Customer
                </h2>
                <p className="font-semibold text-navy-900">
                  {sub.customer_name}
                </p>
                {sub.customer.company_name &&
                  sub.customer.name !== sub.customer.company_name && (
                    <p className="mt-1 text-sm text-slate-600">
                      {sub.customer.name}
                    </p>
                  )}
                <a
                  className="mt-2 inline-block break-all text-sm text-teal-800 hover:underline"
                  href={`mailto:${sub.customer.email}`}
                >
                  {sub.customer.email}
                </a>
                {sub.customer.phone && (
                  <p className="mt-1 text-sm">{sub.customer.phone}</p>
                )}
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  {[
                    sub.customer.address_line1,
                    sub.customer.address_line2,
                    sub.customer.city,
                    sub.customer.state,
                    sub.customer.postal_code,
                    sub.customer.country,
                  ]
                    .filter(Boolean)
                    .join(", ") || "No billing address on file."}
                </p>
                {sub.customer.tax_id && (
                  <p className="mt-2 text-xs text-slate-500">
                    Tax ID: {sub.customer.tax_id}
                  </p>
                )}
              </Card>
              <Card>
                <h2 className="mb-4 text-base font-bold text-navy-900">
                  Contract details
                </h2>
                <dl className="grid grid-cols-2 gap-4">
                  <Datum label="Plan">{sub.plan_name}</Datum>
                  <Datum label="Schedule">{cycle(sub)}</Datum>
                  <Datum label="Start date">
                    {displayDate(sub.start_date)}
                  </Datum>
                  <Datum label="Expiry date">
                    {sub.expiry_date
                      ? displayDate(sub.expiry_date)
                      : "No expiry"}
                  </Datum>
                  <Datum label="Payment terms">
                    {sub.payment_term.name}{" "}
                    <span className="block text-xs font-normal text-slate-500">
                      {sub.payment_term.due_days === 0
                        ? "Due immediately"
                        : `${sub.payment_term.due_days} days after invoice`}
                    </span>
                  </Datum>
                  <Datum label="Currency">{sub.currency}</Datum>
                  {sub.quotation_template && (
                    <Datum label="Template">
                      {sub.quotation_template.name}
                    </Datum>
                  )}
                  {sub.salesperson && (
                    <Datum label="Sales contact">{sub.salesperson.name}</Datum>
                  )}
                </dl>
              </Card>
            </div>
            <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 p-5">
                <h2 className="font-bold text-navy-900">Product lines</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Agreed quantities and prices, with the saved tax and discount
                  breakdown.
                </p>
              </div>
              <div className="overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      {[
                        "Product / variant",
                        "Qty",
                        "Unit price",
                        "Discount",
                        "Taxes",
                        "Tax amount",
                        "Amount",
                      ].map((label) => (
                        <th
                          className="whitespace-nowrap px-4 py-3 font-semibold"
                          key={label}
                        >
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sub.lines.map((line) => (
                      <tr
                        key={line.id}
                        className="border-t border-slate-100 align-top"
                      >
                        <td className="min-w-48 px-4 py-4">
                          <div className="font-semibold text-navy-900">
                            {line.product.name}
                          </div>
                          {line.variant && (
                            <div className="mt-1 text-xs text-teal-700">
                              {line.variant.name}
                            </div>
                          )}
                          {line.description &&
                            line.description !== line.product.name &&
                            line.description !== line.variant?.name && (
                              <p className="mt-1 text-xs text-slate-500">
                                {line.description}
                              </p>
                            )}
                        </td>
                        <td className="px-4 py-4">{line.quantity}</td>
                        <td className="whitespace-nowrap px-4 py-4">
                          {money(line.unit_price, sub.currency)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-4">
                          {money(line.discount_amount, sub.currency)}
                        </td>
                        <td className="min-w-36 px-4 py-4">
                          {line.taxes.length ? (
                            line.taxes.map((tax) => (
                              <div key={tax.id} className="mb-1 text-xs">
                                {tax.name}{" "}
                                <span className="text-slate-500">
                                  (
                                  {tax.tax_type === "percent"
                                    ? `${tax.rate}%`
                                    : `${money(tax.rate, sub.currency)}/unit`}
                                  {tax.is_inclusive ? ", included" : ""})
                                </span>
                              </div>
                            ))
                          ) : (
                            <span className="text-slate-400">No tax</span>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-4">
                          {money(line.tax_amount, sub.currency)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-4 font-semibold text-navy-900">
                          {money(line.total_amount, sub.currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            {sub.notes && (
              <Card>
                <h2 className="mb-3 font-bold text-navy-900">Notes</h2>
                <p className="whitespace-pre-wrap text-sm leading-6 text-slate-600">
                  {sub.notes}
                </p>
              </Card>
            )}
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <ShieldCheck className="size-5 text-teal-700" />
                <h2 className="font-bold text-navy-900">Plan policies</h2>
              </div>
              <ul className="grid gap-3 text-sm sm:grid-cols-2">
                {[
                  [sub.plan.pausable, "Pausing allowed", "Pausing unavailable"],
                  [
                    sub.plan.closable,
                    "Early closure allowed",
                    "Early closure unavailable",
                  ],
                  [
                    sub.plan.renewable,
                    "Renewal allowed",
                    "Renewal unavailable",
                  ],
                  [
                    sub.plan.auto_close,
                    "Closes automatically after expiry",
                    "Closure managed by the team",
                  ],
                ].map(([value, yes, no], index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span
                      className={`mt-1 size-2 shrink-0 rounded-full ${value ? "bg-teal-600" : "bg-slate-300"}`}
                    />
                    {String(value ? yes : no)}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-slate-500">
                Minimum quantity: {sub.plan.min_quantity}.{" "}
                {sub.plan.trial_days
                  ? `Trial: ${sub.plan.trial_days} days.`
                  : "No trial configured."}
              </p>
            </Card>
          </div>
          <aside className="space-y-5">
            <Card>
              <h2 className="mb-4 font-bold text-navy-900">
                Recurring price preview
              </h2>
              <dl className="space-y-3 text-sm">
                {[
                  ["Subtotal", subtotal],
                  ["Discounts", discount],
                  ["Untaxed", sub.recurring_untaxed],
                  ["Tax", sub.recurring_tax],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-3">
                    <dt className="text-slate-500">{label}</dt>
                    <dd>
                      {label === "Discounts" && discount !== "0.00" ? "− " : ""}
                      {money(value, sub.currency)}
                    </dd>
                  </div>
                ))}
                <div className="flex justify-between gap-3 border-t pt-4 text-lg font-bold text-navy-900">
                  <dt>Total</dt>
                  <dd>{money(sub.recurring_total, sub.currency)}</dd>
                </div>
              </dl>
              <p className="mt-2 text-xs text-teal-800">{cycle(sub)}</p>
              <p className="mt-4 text-xs leading-5 text-slate-500">
                Preview from the last saved calculation. Final invoices
                recalculate applicable discounts and taxes at billing time.
              </p>
            </Card>
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <CalendarDays className="size-4 text-teal-700" />
                <h2 className="font-bold text-navy-900">Billing schedule</h2>
              </div>
              <dl className="space-y-4">
                <Datum label="Next invoice">
                  {sub.state === "paused"
                    ? "Billing paused"
                    : sub.state === "closed"
                      ? "Billing stopped"
                      : sub.next_invoice_date
                        ? displayDate(sub.next_invoice_date)
                        : "Not scheduled"}
                </Datum>
                <Datum label="Last invoiced">
                  {sub.last_invoiced_date
                    ? displayDate(sub.last_invoiced_date)
                    : "No invoices generated"}
                </Datum>
                {sub.trial_end_date && (
                  <Datum label="Trial ends">
                    {displayDate(sub.trial_end_date)}
                  </Datum>
                )}
              </dl>
            </Card>
            {secondaryActions.length > 0 && (
              <Card>
                <h2 className="mb-4 font-bold text-navy-900">Next actions</h2>
                <div className="flex flex-col items-start gap-3">
                  {secondaryActions.map((action) => (
                    <div key={action.state}>
                      <Button
                        secondary={
                          action.state === "closed" ||
                          action.state === "draft" ||
                          action.state === "paused"
                        }
                        disabled={busy || !!action.disabled}
                        onClick={() => props.changeState(action)}
                      >
                        {action.label}
                      </Button>
                      {action.disabled && (
                        <p className="mt-2 text-xs leading-5 text-slate-500">
                          {action.disabled}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}
            {!portal &&
              ["active", "paused"].includes(sub.state) &&
              renewalDisabled(sub) && (
                <p className="px-1 text-xs text-slate-500">
                  {renewalDisabled(sub)}
                </p>
              )}
            {!portal && sub.state === "draft" && (
              <button
                disabled={busy}
                onClick={props.remove}
                className="px-1 text-sm font-medium text-rose-700 hover:underline disabled:opacity-50"
              >
                Delete draft
              </button>
            )}
          </aside>
        </section>
      )}
      {tab === "invoices" && (
        <section
          role="tabpanel"
          id="panel-invoices"
          aria-labelledby="tab-invoices"
        >
          <Card>
            <div className="mb-5">
              <h2 className="font-bold text-navy-900">Related invoices</h2>
              <p className="mt-1 text-sm text-slate-500">
                Only invoices generated for {sub.number}.
              </p>
            </div>
            <ErrorMessage error={invoices.error} />
            {invoices.loading ? (
              <p role="status">Loading invoices…</p>
            ) : invoices.data?.items.length ? (
              <div className="overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-xs uppercase text-slate-500">
                      {[
                        "Invoice",
                        "Issued",
                        "Due",
                        "Status",
                        "Total",
                        "Outstanding",
                      ].map((label) => (
                        <th key={label} className="p-3">
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.data.items.map((row) => (
                      <tr key={row.id} className="border-b last:border-0">
                        <td className="p-3">
                          <a
                            className="inline-flex items-center gap-1 font-semibold text-teal-800 hover:underline"
                            href={invoicePath(row.id)}
                          >
                            {String(row.number)}
                            <ArrowUpRight className="size-3" />
                          </a>
                        </td>
                        <td className="whitespace-nowrap p-3">
                          {displayDate(String(row.invoice_date))}
                        </td>
                        <td className="whitespace-nowrap p-3">
                          {displayDate(String(row.due_date))}
                        </td>
                        <td className="p-3">
                          <Badge
                            value={
                              row.is_overdue ? "overdue" : String(row.state)
                            }
                          />
                        </td>
                        <td className="whitespace-nowrap p-3">
                          {money(row.total, String(row.currency))}
                        </td>
                        <td className="whitespace-nowrap p-3">
                          {money(row.amount_due, String(row.currency))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              !invoices.error && (
                <div className="rounded-xl border border-dashed border-slate-200 py-10 text-center">
                  <ReceiptText className="mx-auto mb-3 size-8 text-slate-300" />
                  <p className="font-semibold text-navy-900">No invoices yet</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {sub.state === "active" && !portal
                      ? "Generate the next period’s invoice or wait for the scheduled billing run."
                      : "Invoices appear here once the subscription is active and billing has run."}
                  </p>
                </div>
              )
            )}
            <div className="mt-4 flex items-center justify-between text-sm">
              <span>{invoices.data?.total || 0} invoices</span>
              <div className="flex items-center gap-3">
                <Button
                  secondary
                  disabled={invoicePage === 1 || invoices.loading}
                  onClick={() => setInvoicePage((page) => page - 1)}
                >
                  Previous
                </Button>
                <span>Page {invoicePage}</span>
                <Button
                  secondary
                  disabled={
                    invoicePage * 10 >= (invoices.data?.total || 0) ||
                    invoices.loading
                  }
                  onClick={() => setInvoicePage((page) => page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </Card>
        </section>
      )}
      {tab === "addons" && portal && (
        <section
          role="tabpanel"
          id="panel-addons"
          aria-labelledby="tab-addons"
          className="mt-5"
        >
          <AddonManager
            subscriptionId={sub.id}
            revision={revision}
            onChanged={props.addonsChanged}
          />
        </section>
      )}
      {tab === "activity" && (
        <section
          role="tabpanel"
          id="panel-activity"
          aria-labelledby="tab-activity"
        >
          <Card>
            <h2 className="mb-5 font-bold text-navy-900">State history</h2>
            <ol className="space-y-0">
              {[...sub.state_logs].reverse().map((log) => (
                <li
                  key={log.id}
                  className="relative border-l border-slate-200 pb-7 pl-6 last:pb-0"
                >
                  <span className="absolute -left-1.5 top-1 size-3 rounded-full border-2 border-white bg-teal-600" />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-navy-900">
                      {log.from_state === log.to_state
                        ? "Subscription updated"
                        : log.from_state
                          ? `${title(log.from_state)} → ${title(log.to_state)}`
                          : `Created as ${title(log.to_state)}`}
                    </p>
                    <time
                      className="text-xs text-slate-500"
                      dateTime={log.created_at}
                    >
                      {new Date(log.created_at).toLocaleString()}
                    </time>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {log.changed_by_user?.name || "Automatic system action"}
                  </p>
                  {log.reason && (
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">
                      {log.reason}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </Card>
        </section>
      )}
    </article>
  );
}
