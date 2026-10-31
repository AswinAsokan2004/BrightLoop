import { useEffect, useState } from "react";
import { text, title, money, type Page, type User } from "../lib/api";
import { Badge, Button, Card, ErrorMessage, Table, useLoad } from "./ui";
import InvoiceDetails from "./InvoiceDetails";
import { navigate } from "../lib/navigation";
export default function Invoices({ user }: { user: User }) {
  const portal = user.role === "customer",
    base = portal ? "/portal/invoices" : "/invoices";
  const [page, setPage] = useState(1),
    [filter, setFilter] = useState(""),
    [query, setQuery] = useState(""),
    [selected, setSelected] = useState<number | null>(() => invoiceId());
  function invoiceId() {
    const match = location.pathname.match(/\/invoices\/(\d+)\/?$/);
    return match ? Number(match[1]) : null;
  }
  useEffect(() => {
    const update = () => setSelected(invoiceId());
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);
  const params = new URLSearchParams({ page: String(page), size: "20" });
  if (filter === "outstanding" || filter === "overdue")
    params.set(filter, "true");
  else if (filter) params.set("state", filter);
  if (query && !portal) params.set("q", query);
  const result = useLoad<Page>(selected ? null : `${base}?${params}`);
  if (selected)
    return <InvoiceDetails key={selected} id={selected} user={user} />;
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
                setQuery(e.target.value);
                setPage(1);
              }}
            />
          )}
          <select
            aria-label="Invoice filter"
            className="rounded border p-2"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setPage(1);
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
              navigate(`${base}/${r.id}`);
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
    </div>
  );
}
