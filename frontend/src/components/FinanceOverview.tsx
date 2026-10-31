import { useEffect, useRef, useState, type FormEvent } from "react";
import { money, text, title, type Row } from "../lib/api";
import { navigate } from "../lib/navigation";
import { Badge, Button, Card, ErrorMessage, Table, useLoad } from "./ui";

type Finance = {
  currency: string;
  currencies: string[];
  active_subscriptions: number;
  mrr: string;
  invoiced_total: string;
  revenue_collected: string;
  outstanding_amount: string;
  outstanding_count: number;
  overdue_amount: string;
  overdue_count: number;
  invoices: Row[];
  invoice_count: number;
  payments: Row[];
  payment_count: number;
  subscriptions: Row[];
  monthly: { month: string; invoiced: string; collected: string }[];
};
type Filters = {
  date_from: string;
  date_to: string;
  customer_id: string;
  plan_id: string;
  currency: string;
};
const empty: Filters = {
  date_from: "",
  date_to: "",
  customer_id: "",
  plan_id: "",
  currency: "",
};
function NamedFilter({
  kind,
  value,
  change,
}: {
  kind: "customer" | "plan";
  value: string;
  change: (value: string) => void;
}) {
  const [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [page, setPage] = useState(1),
    [selected, setSelected] = useState<Row | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);
  const options = useLoad<{ items: Row[]; has_more: boolean }>(
    `/reports/options?kind=${kind}&q=${encodeURIComponent(query)}&page=${page}`,
  );
  const chosen = useLoad<Row>(
    value ? `/${kind === "customer" ? "customers" : "plans"}/${value}` : null,
  );
  const selectedRow =
    selected && String(selected.id) === value ? selected : chosen.data;
  const rows = options.data?.items || [];
  return (
    <fieldset className="min-w-0 rounded-lg border p-3">
      <legend className="px-1 text-sm font-semibold">{title(kind)}</legend>
      <input
        className="mb-2 w-full rounded border p-2 text-sm"
        aria-label={`Search ${kind} names`}
        placeholder={`Search ${kind} names`}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <select
        className="w-full rounded border bg-white p-2 text-sm"
        aria-label={`Filter by ${kind}`}
        value={value}
        onChange={(e) => {
          setSelected(
            rows.find((r) => String(r.id) === e.target.value) || null,
          );
          change(e.target.value);
        }}
      >
        <option value="">
          All {kind === "customer" ? "customers" : "plans"}
        </option>
        {selectedRow && !rows.some((r) => r.id === selectedRow.id) && (
          <option value={String(selectedRow.id)}>
            {text(selectedRow, "name")}
          </option>
        )}
        {rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {text(row, "name")}
          </option>
        ))}
      </select>
      <ErrorMessage error={options.error} />
      {options.loading && (
        <p className="text-xs" role="status">
          Loading {kind} names…
        </p>
      )}
      {!options.loading && rows.length === 0 && (
        <p className="text-xs">No matching {kind} names.</p>
      )}
      <div className="mt-2 flex justify-between gap-2">
        <Button
          secondary
          disabled={page === 1 || options.loading}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous names
        </Button>
        <Button
          secondary
          disabled={!options.data?.has_more || options.loading}
          onClick={() => setPage((p) => p + 1)}
        >
          More names
        </Button>
      </div>
    </fieldset>
  );
}
function RecordLink({ path, label }: { path: string; label: string }) {
  return (
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
}
function Pages({
  label,
  page,
  total,
  change,
  loading,
}: {
  label: string;
  page: number;
  total: number;
  change: (n: number) => void;
  loading: boolean;
}) {
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <span className="text-sm">
        {total} {label} · Page {page}
      </span>
      <div className="flex gap-2">
        <Button
          secondary
          disabled={page === 1 || loading}
          onClick={() => change(page - 1)}
        >
          Previous {label}
        </Button>
        <Button
          secondary
          disabled={page * 10 >= total || loading}
          onClick={() => change(page + 1)}
        >
          Next {label}
        </Button>
      </div>
    </div>
  );
}
export default function FinanceOverview({
  overview = false,
}: {
  overview?: boolean;
}) {
  const initialParams = new URLSearchParams(location.search);
  const initialFilters = Object.fromEntries(
    Object.keys(empty).map((key) => [key, initialParams.get(key) || ""]),
  ) as Filters;
  const initialPage = (key: string) =>
    Math.max(1, Number(initialParams.get(key)) || 1);
  const [draft, setDraft] = useState<Filters>(initialFilters),
    [filters, setFilters] = useState<Filters>(initialFilters),
    [revision, setRevision] = useState(0),
    [reset, setReset] = useState(0),
    [error, setError] = useState(""),
    [invoiceView, setInvoiceView] = useState(
      initialParams.get("invoice_view") || "overdue",
    ),
    [invoicePage, setInvoicePage] = useState(initialPage("invoice_page")),
    [paymentPage, setPaymentPage] = useState(initialPage("payment_page")),
    [subscriptionPage, setSubscriptionPage] = useState(
      initialPage("subscription_page"),
    );
  const [invoiceFocus, setInvoiceFocus] = useState(false);
  const invoicesRef = useRef<HTMLElement>(null),
    paymentsRef = useRef<HTMLElement>(null),
    subscriptionsRef = useRef<HTMLElement>(null);
  const params = new URLSearchParams({
    invoice_view: invoiceView,
    invoice_page: String(invoicePage),
    payment_page: String(paymentPage),
    subscription_page: String(subscriptionPage),
  });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const queryString = params.toString();
  useEffect(() => {
    history.replaceState(null, "", `${location.pathname}?${queryString}`);
  }, [queryString]);
  const result = useLoad<Finance>(`/reports/finance?${params}`, revision),
    data = result.data;
  function resetPages() {
    setInvoicePage(1);
    setPaymentPage(1);
    setSubscriptionPage(1);
  }
  function apply(e: FormEvent) {
    e.preventDefault();
    if (draft.date_from && draft.date_to && draft.date_from > draft.date_to) {
      setError("From date must be on or before To date");
      return;
    }
    setError("");
    setFilters({ ...draft });
    resetPages();
    setRevision((r) => r + 1);
  }
  function invoiceDrill(view: string) {
    if (view === invoiceView && invoicePage === 1)
      invoicesRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    else {
      setInvoiceFocus(true);
      setInvoiceView(view);
      setInvoicePage(1);
    }
  }
  useEffect(() => {
    if (invoiceFocus && data && !result.loading) {
      const frame = requestAnimationFrame(() => {
        invoicesRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
        setInvoiceFocus(false);
      });
      return () => cancelAnimationFrame(frame);
    }
  }, [invoiceFocus, data, result.loading]);
  const amount = (value: unknown) => money(value, data?.currency || "");
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-navy-900">
            {overview ? "Finance overview" : "Revenue reports"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Subscriptions, collections and invoices in one place.
          </p>
        </div>
        <Button
          secondary
          disabled={result.loading}
          onClick={() => setRevision((r) => r + 1)}
        >
          Refresh
        </Button>
      </div>
      <Card>
        <form onSubmit={apply} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <NamedFilter
              key={`customer-${reset}`}
              kind="customer"
              value={draft.customer_id}
              change={(value) =>
                setDraft((d) => ({ ...d, customer_id: value }))
              }
            />
            <NamedFilter
              key={`plan-${reset}`}
              kind="plan"
              value={draft.plan_id}
              change={(value) => setDraft((d) => ({ ...d, plan_id: value }))}
            />
            <div className="space-y-3">
              <label className="block text-sm">
                From
                <input
                  aria-label="Report from date"
                  type="date"
                  value={draft.date_from}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, date_from: e.target.value }))
                  }
                  className="mt-1 block w-full rounded border p-2"
                />
              </label>
              <label className="block text-sm">
                To
                <input
                  aria-label="Report to date"
                  type="date"
                  value={draft.date_to}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, date_to: e.target.value }))
                  }
                  className="mt-1 block w-full rounded border p-2"
                />
              </label>
            </div>
            <label className="block text-sm">
              Currency
              <select
                aria-label="Report currency"
                value={draft.currency}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, currency: e.target.value }))
                }
                className="mt-1 block w-full rounded border bg-white p-2"
              >
                <option value="">
                  Automatic{data ? ` (${data.currency})` : ""}
                </option>
                {Array.from(
                  new Set([
                    ...(data?.currencies || []),
                    ...(draft.currency ? [draft.currency] : []),
                  ]),
                ).map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex gap-2">
            <Button type="submit">Apply filters</Button>
            <Button
              secondary
              onClick={() => {
                setDraft(empty);
                setFilters(empty);
                setInvoiceView("overdue");
                setReset((r) => r + 1);
                resetPages();
                setError("");
                setRevision((r) => r + 1);
              }}
            >
              Clear filters
            </Button>
          </div>
        </form>
        <ErrorMessage error={error} />
        <p className="mt-4 text-xs text-slate-500">
          Dates apply to invoice issue dates and payment receipt dates. Active
          subscriptions and monthly recurring revenue reflect the current
          portfolio. Totals use one currency at a time; no currency conversion
          is applied.
        </p>
      </Card>
      <ErrorMessage error={result.error} />
      {result.loading && <p role="status">Loading finance overview…</p>}
      {data && (
        <>
          <p className="text-sm font-semibold">
            Showing {data.currency} · {filters.date_from || "All dates"}
            {filters.date_to ? ` through ${filters.date_to}` : ""}
          </p>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[
              {
                label: "Active subscriptions",
                value: String(data.active_subscriptions),
                action: () =>
                  subscriptionsRef.current?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  }),
              },
              {
                label: "Revenue collected",
                value: amount(data.revenue_collected),
                action: () =>
                  paymentsRef.current?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  }),
              },
              {
                label: "Outstanding balance",
                value: amount(data.outstanding_amount),
                action: () => invoiceDrill("outstanding"),
              },
              {
                label: "Overdue amount",
                value: amount(data.overdue_amount),
                action: () => invoiceDrill("overdue"),
              },
              {
                label: "Invoiced total",
                value: amount(data.invoiced_total),
                action: () => invoiceDrill("billed"),
              },
            ].map((card) => (
              <button
                key={card.label}
                onClick={card.action}
                className="rounded-xl border border-slate-200 bg-white p-5 text-left hover:border-teal-600 focus-visible:outline-teal-700"
              >
                <span className="text-sm text-slate-500">{card.label}</span>
                <span className="mt-3 block break-words text-2xl font-bold text-navy-900">
                  {card.value}
                </span>
                <span className="mt-2 block text-xs text-teal-700">
                  View records →
                </span>
              </button>
            ))}
            <Card>
              <p className="text-sm text-slate-500">
                Monthly recurring revenue
              </p>
              <p className="mt-3 text-2xl font-bold text-navy-900">
                {amount(data.mrr)}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Normalized untaxed subscription value
              </p>
            </Card>
          </div>
          <section
            ref={invoicesRef}
            aria-label="Invoice balances"
            className="scroll-mt-24"
          >
            <Card>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-bold">Invoice balances</h2>
                  <p className="text-sm text-slate-500">
                    {data.overdue_count} overdue · {data.outstanding_count}{" "}
                    outstanding
                  </p>
                </div>
                <select
                  aria-label="Finance invoice view"
                  className="rounded border bg-white p-2"
                  value={invoiceView}
                  onChange={(e) => {
                    setInvoiceView(e.target.value);
                    setInvoicePage(1);
                  }}
                >
                  <option value="overdue">Overdue invoices</option>
                  <option value="outstanding">Outstanding invoices</option>
                  <option value="billed">Confirmed and paid invoices</option>
                    <option value="all">All invoices (including drafts)</option>
                </select>
              </div>
              <div className="overflow-x-auto [&_table]:min-w-[640px]">
                <Table
                  rows={data.invoices}
                  columns={[
                    {
                      key: "number",
                      label: "Invoice",
                      render: (r) => (
                        <RecordLink
                          path={`/invoices/${r.id}`}
                          label={text(r, "number")}
                        />
                      ),
                    },
                    { key: "customer_name", label: "Customer" },
                    { key: "due_date", label: "Due date" },
                    {
                      key: "state",
                      label: "Status",
                      render: (r) => <Badge value={text(r, "state")} />,
                    },
                    {
                      key: "total",
                      label: "Total",
                      render: (r) => amount(r.total),
                    },
                    {
                      key: "amount_due",
                      label: "Balance",
                      render: (r) => amount(r.amount_due),
                    },
                  ]}
                />
              </div>
              <Pages
                label="invoices"
                page={invoicePage}
                total={data.invoice_count}
                change={setInvoicePage}
                loading={result.loading}
              />
            </Card>
          </section>
          <section
            ref={paymentsRef}
            aria-label="Recent payments"
            className="scroll-mt-24"
          >
            <Card>
              <h2 className="mb-4 font-bold">Recent payments</h2>
              <div className="overflow-x-auto [&_table]:min-w-[640px]">
                <Table
                  rows={data.payments}
                  columns={[
                    { key: "payment_date", label: "Date" },
                    { key: "customer_name", label: "Customer" },
                    {
                      key: "invoice_number",
                      label: "Invoice",
                      render: (r) => (
                        <RecordLink
                          path={`/invoices/${r.invoice_id}`}
                          label={text(r, "invoice_number")}
                        />
                      ),
                    },
                    {
                      key: "method",
                      label: "Method",
                      render: (r) => title(text(r, "method")),
                    },
                    {
                      key: "amount",
                      label: "Amount",
                      render: (r) => amount(r.amount),
                    },
                    { key: "reference", label: "Reference" },
                  ]}
                />
              </div>
              <Pages
                label="payments"
                page={paymentPage}
                total={data.payment_count}
                change={setPaymentPage}
                loading={result.loading}
              />
            </Card>
          </section>
          <section
            ref={subscriptionsRef}
            aria-label="Active subscriptions"
            className="scroll-mt-24"
          >
            <Card>
              <h2 className="mb-4 font-bold">Active subscriptions</h2>
              <div className="overflow-x-auto [&_table]:min-w-[640px]">
                <Table
                  rows={data.subscriptions}
                  columns={[
                    {
                      key: "number",
                      label: "Subscription",
                      render: (r) => (
                        <RecordLink
                          path={`/subscriptions/${r.id}`}
                          label={text(r, "number")}
                        />
                      ),
                    },
                    { key: "customer_name", label: "Customer" },
                    { key: "plan_name", label: "Plan" },
                    {
                      key: "recurring_untaxed",
                      label: "Untaxed amount per billing period",
                      render: (r) => amount(r.recurring_untaxed),
                    },
                  ]}
                />
              </div>
              <Pages
                label="subscriptions"
                page={subscriptionPage}
                total={data.active_subscriptions}
                change={setSubscriptionPage}
                loading={result.loading}
              />
            </Card>
          </section>
          <Card>
            <h2 className="mb-4 font-bold">Revenue by month</h2>
            <div className="overflow-x-auto [&_table]:min-w-[640px]">
              <Table
                rows={data.monthly.map((r, id) => ({ ...r, id }))}
                columns={[
                  { key: "month", label: "Month" },
                  {
                    key: "invoiced",
                    label: "Invoiced",
                    render: (r) => amount(r.invoiced),
                  },
                  {
                    key: "collected",
                    label: "Collected",
                    render: (r) => amount(r.collected),
                  },
                ]}
              />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
