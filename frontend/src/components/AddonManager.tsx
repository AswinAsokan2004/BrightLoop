import { useEffect, useState, type FormEvent } from "react";
import { api, money, today } from "../lib/api";
import { Button, Card, Dialog, ErrorMessage, useLoad } from "./ui";

type Item = {
  product_id: number;
  variant_id: number | null;
  name: string;
  variant_name: string | null;
  quantity: number;
  unit_price: string;
};
type Offer = Omit<Item, "quantity"> & {
  taxes: {
    name: string;
    rate: string;
    tax_type: string;
    is_inclusive: boolean;
  }[];
};
type Workspace = {
  eligible: boolean;
  reason: string | null;
  currency: string;
  effective_date: string | null;
  items: Item[];
};
type Quote = {
  currency: string;
  effective_date: string;
  fingerprint: string;
  before_items: Item[];
  after_items: Item[];
  before_total: string;
  after_total: string;
  delta: string;
  subtotal: string;
  discount_total: string;
  tax_total: string;
};
type Change = {
  id: number;
  effective_date: string;
  before_items: Item[];
  after_items: Item[];
  before_total: string;
  after_total: string;
  created_at: string;
  changed_by_user: { name: string } | null;
};
type Page<T> = { items: T[]; total: number; page: number; size: number };
type Cart = Omit<Item, "quantity"> & { quantity: string };
const key = (i: { product_id: number; variant_id: number | null }) =>
  `${i.product_id}:${i.variant_id || 0}`;
const label = (i: { name: string; variant_name: string | null }) =>
  i.variant_name ? `${i.name} — ${i.variant_name}` : i.name;
const describe = (items: Item[]) =>
  items.length
    ? items.map((i) => `${label(i)} × ${i.quantity}`).join("; ")
    : "None";
export default function AddonManager({
  subscriptionId,
  revision,
  onChanged,
}: {
  subscriptionId: number;
  revision: number;
  onChanged: () => void;
}) {
  const base = `/portal/subscriptions/${subscriptionId}`;
  const [localRevision, setLocalRevision] = useState(0),
    [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [page, setPage] = useState(1),
    [historyPage, setHistoryPage] = useState(1),
    [cart, setCart] = useState<Cart[]>([]),
    [quote, setQuote] = useState<Quote | null>(null),
    [reviewItems, setReviewItems] = useState<
      { product_id: number; variant_id: number | null; quantity: number }[]
    >([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const workspace = useLoad<Workspace>(
      `${base}/addons`,
      revision + localRevision,
    ),
    data = workspace.data;
  const options = useLoad<Page<Offer>>(
    data?.eligible
      ? `${base}/addon-options?q=${encodeURIComponent(query)}&page=${page}&size=10`
      : null,
    revision + localRevision,
  );
  const history = useLoad<Page<Change>>(
    `${base}/addon-history?page=${historyPage}&size=10`,
    revision + localRevision,
  );
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);
  useEffect(() => {
    if (data)
      setCart(
        data.items.map((item) => ({
          ...item,
          quantity: String(item.quantity),
        })),
      );
  }, [data]);
  const canonical = (
    items: {
      product_id: number;
      variant_id: number | null;
      quantity: string | number;
    }[],
  ) =>
    JSON.stringify(
      items
        .map((i) => ({ key: key(i), quantity: String(i.quantity) }))
        .sort((a, b) => a.key.localeCompare(b.key)),
    );
  const changed = data ? canonical(cart) !== canonical(data.items) : false;
  async function review(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    if (
      cart.some(
        (i) =>
          !/^\d+$/.test(i.quantity) ||
          Number(i.quantity) < 1 ||
          Number(i.quantity) > 10000,
      )
    ) {
      setError("Each add-on quantity must be a whole number from 1 to 10000.");
      return;
    }
    const items = cart.map((i) => ({
      product_id: i.product_id,
      variant_id: i.variant_id,
      quantity: Number(i.quantity),
    }));
    setBusy(true);
    try {
      const result = await api<Quote>(`${base}/addons/preview`, "POST", {
        items,
      });
      setReviewItems(items);
      setQuote(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function confirm() {
    if (!quote || busy) return;
    setBusy(true);
    setError("");
    try {
      await api(`${base}/addons`, "PUT", {
        items: reviewItems,
        fingerprint: quote.fingerprint,
      });
      setNotice(
        `Add-on selection saved for the unbilled period starting ${quote.effective_date}. No prorated charge or credit was created.`,
      );
      setQuote(null);
      setHistoryPage(1);
      setLocalRevision((r) => r + 1);
      onChanged();
    } catch (e) {
      setQuote(null);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const amount = (value: string) => money(value, data?.currency || "");
  return (
    <section aria-label="Subscription add-ons" className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-navy-900">Manage add-ons</h2>
          <p className="mt-1 text-sm text-slate-500">
            Choose what to include in your next unbilled period.
          </p>
        </div>
        <Button
          secondary
          disabled={busy || workspace.loading}
          onClick={() => {
            setQuote(null);
            setError("");
            setNotice("");
            setLocalRevision((r) => r + 1);
          }}
        >
          Reload add-ons
        </Button>
      </div>
      <ErrorMessage error={workspace.error || error} />
      {notice && (
        <p role="status" className="rounded-lg bg-teal-50 p-3 text-teal-800">
          {notice}
        </p>
      )}
      {workspace.loading && <p role="status">Loading add-ons…</p>}
      {data && (
        <>
          <Card>
            <h3 className="mb-3 font-bold">
              Enabled for the next unbilled period
            </h3>
            {data.items.length ? (
              <ul className="space-y-2">
                {data.items.map((i) => (
                  <li
                    key={key(i)}
                    className="flex flex-wrap justify-between gap-2"
                  >
                    <span>
                      {label(i)} × {i.quantity}
                    </span>
                    <span>{amount(i.unit_price)} per unit</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">
                No customer-managed add-ons enabled.
              </p>
            )}
            <p className="mt-4 text-sm">
              {data.eligible
                ? `Changes apply to the unbilled period starting ${data.effective_date}. No proration; existing invoices stay unchanged.`
                : data.reason}
            </p>
            {data.eligible &&
              data.effective_date &&
              data.effective_date < today() && (
                <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
                  The next unbilled period is in the past. Changes apply to
                  remaining catch-up periods from {data.effective_date},
                  including overdue billing periods that have not yet been
                  invoiced.
                </p>
              )}
          </Card>
          {data.eligible && (
            <>
              <Card>
                <h3 className="mb-3 font-bold">Available add-ons</h3>
                <input
                  aria-label="Search add-ons"
                  maxLength={150}
                  placeholder="Search products or variants"
                  className="mb-4 w-full rounded border p-2 text-sm"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <ErrorMessage error={options.error} />
                <p className="mb-4 text-xs text-slate-500">
                  Unit prices are shown before applicable taxes and automatic
                  discounts. Base contract items cannot be changed here.
                </p>
                {options.loading ? (
                  <p role="status">Loading available add-ons…</p>
                ) : options.data?.items.length ? (
                  <ul className="grid gap-3 md:grid-cols-2">
                    {options.data.items.map((item) => (
                      <li
                        key={key(item)}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4"
                      >
                        <div className="min-w-0">
                          <p className="break-words font-semibold">
                            {label(item)}
                          </p>
                          <p className="mt-1 text-sm">
                            {amount(item.unit_price)} per unit / billing period
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {item.taxes.length
                              ? item.taxes
                                  .map(
                                    (t) =>
                                      `${t.name}: ${t.rate}${t.tax_type === "percent" ? "%" : " per unit"}${t.is_inclusive ? " (inclusive)" : ""}`,
                                  )
                                  .join("; ")
                              : "No active catalog taxes"}
                          </p>
                        </div>
                        <Button
                          secondary
                          disabled={
                            busy || cart.some((i) => key(i) === key(item))
                          }
                          onClick={() => {
                            setError("");
                            setCart((current) => [
                              ...current,
                              { ...item, quantity: "1" },
                            ]);
                          }}
                        >
                          {cart.some((i) => key(i) === key(item))
                            ? "Selected"
                            : `Add ${label(item)}`}
                        </Button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">
                    No matching recurring add-ons are available. Your team
                    controls which products are offered.
                  </p>
                )}
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-sm">
                    {options.data?.total || 0} offers · Page {page}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      secondary
                      disabled={page === 1 || options.loading}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous offers
                    </Button>
                    <Button
                      secondary
                      disabled={
                        page * 10 >= (options.data?.total || 0) ||
                        options.loading
                      }
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next offers
                    </Button>
                  </div>
                </div>
              </Card>
              <Card>
                <form onSubmit={review}>
                  <h3 className="mb-3 font-bold">
                    Your next billing selection
                  </h3>
                  <p className="mb-4 text-xs text-slate-500">
                    Existing enabled add-ons keep their stored unit price. Newly
                    enabled add-ons use current catalog prices. Changes are
                    saved only after review and confirmation.
                  </p>
                  {cart.length ? (
                    <ul className="space-y-3">
                      {cart.map((item) => (
                        <li
                          key={key(item)}
                          className="flex flex-wrap items-end justify-between gap-3 rounded-lg border p-3"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="break-words font-semibold">
                              {label(item)}
                            </p>
                            <p className="mt-1 text-sm">
                              {amount(item.unit_price)} per unit
                            </p>
                          </div>
                          <label className="text-sm">
                            Quantity
                            <input
                              aria-label={`Quantity for ${label(item)}`}
                              type="number"
                              min={1}
                              max={10000}
                              step={1}
                              required
                              disabled={busy}
                              className="mt-1 block w-24 rounded border p-2"
                              value={item.quantity}
                              onChange={(e) => {
                                const value = e.target.value;
                                setCart((rows) =>
                                  rows.map((row) =>
                                    key(row) === key(item)
                                      ? { ...row, quantity: value }
                                      : row,
                                  ),
                                );
                              }}
                            />
                          </label>
                          <Button
                            secondary
                            disabled={busy}
                            onClick={() =>
                              setCart((rows) =>
                                rows.filter((row) => key(row) !== key(item)),
                              )
                            }
                          >
                            Remove {label(item)}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">
                      No add-ons selected. Your base contract lines remain in
                      place.
                    </p>
                  )}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button type="submit" disabled={busy || !changed}>
                      Review add-on changes
                    </Button>
                    <Button
                      secondary
                      disabled={busy || !changed}
                      onClick={() => {
                        setCart(
                          data.items.map((item) => ({
                            ...item,
                            quantity: String(item.quantity),
                          })),
                        );
                        setError("");
                      }}
                    >
                      Discard changes
                    </Button>
                  </div>
                </form>
              </Card>
            </>
          )}
        </>
      )}
      <Card>
        <h3 className="mb-4 font-bold">Add-on change history</h3>
        <ErrorMessage error={history.error} />
        {history.loading ? (
          <p role="status">Loading add-on history…</p>
        ) : history.data?.items.length ? (
          <ul className="space-y-4">
            {history.data.items.map((change) => (
              <li key={change.id} className="rounded-lg border p-4">
                <p className="font-semibold">
                  Unbilled period starting {change.effective_date}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {new Date(change.created_at).toLocaleString()} ·{" "}
                  {change.changed_by_user?.name || "Account user"}
                </p>
                <p className="mt-3 break-words text-sm">
                  Before: {describe(change.before_items)}
                </p>
                <p className="mt-2 break-words text-sm">
                  After: {describe(change.after_items)}
                </p>
                <p className="mt-2 text-sm">
                  Estimated period total: {amount(change.before_total)} →{" "}
                  {amount(change.after_total)}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No add-on changes recorded.</p>
        )}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <span className="text-sm">
            {history.data?.total || 0} changes · Page {historyPage}
          </span>
          <div className="flex gap-2">
            <Button
              secondary
              disabled={historyPage === 1 || history.loading}
              onClick={() => setHistoryPage((p) => p - 1)}
            >
              Previous changes
            </Button>
            <Button
              secondary
              disabled={
                historyPage * 10 >= (history.data?.total || 0) ||
                history.loading
              }
              onClick={() => setHistoryPage((p) => p + 1)}
            >
              Next changes
            </Button>
          </div>
        </div>
      </Card>
      {quote && (
        <Dialog
          title="Review add-on changes"
          close={() => {
            if (!busy) setQuote(null);
          }}
        >
          <p className="mb-3">
            Apply this selection to the unbilled period starting{" "}
            <strong>{quote.effective_date}</strong>?
          </p>
          <p className="mb-3 text-sm">Before: {describe(quote.before_items)}</p>
          <p className="mb-4 text-sm">After: {describe(quote.after_items)}</p>
          <dl className="space-y-2 text-sm">
            {[
              ["Current estimated period total", quote.before_total],
              ["New subtotal", quote.subtotal],
              ["Automatic discounts", quote.discount_total],
              ["Taxes", quote.tax_total],
              ["New estimated period total", quote.after_total],
              ["Change per billing period", quote.delta],
            ].map(([name, value]) => (
              <div key={name} className="flex flex-wrap justify-between gap-2">
                <dt>{name}</dt>
                <dd className="font-semibold">
                  {money(value, quote.currency)}
                </dd>
              </div>
            ))}
          </dl>
          <p className="my-4 text-sm text-slate-500">
            No prorated charge or credit is created. Existing invoices stay
            unchanged. Taxes and discount availability are recalculated when the
            invoice is generated, so these totals are estimates.
          </p>
          {quote.effective_date < today() && (
            <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
              This applies to unbilled catch-up periods starting{" "}
              {quote.effective_date}, which is in the past.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => void confirm()}>
              Confirm add-on changes
            </Button>
            <Button secondary disabled={busy} onClick={() => setQuote(null)}>
              Keep editing
            </Button>
          </div>
        </Dialog>
      )}
    </section>
  );
}
