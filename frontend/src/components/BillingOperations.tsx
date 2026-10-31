import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  money,
  text,
  title,
  today,
  type Page,
  type Row,
} from "../lib/api";
import { navigate } from "../lib/navigation";
import {
  Badge,
  Button,
  Card,
  Dialog,
  ErrorMessage,
  Table,
  useLoad,
} from "./ui";

type Preview = Page & {
  run_date: string;
  due_subscriptions: number;
  auto_close_subscriptions: number;
};
function Link({ path, label }: { path: string; label: string }) {
  return (
    <a
      className="font-semibold text-teal-700 underline"
      href={path}
      onClick={(e) => {
        if (
          e.button === 0 &&
          !e.metaKey &&
          !e.ctrlKey &&
          !e.altKey &&
          !e.shiftKey
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
function Pagination({
  label,
  page,
  total,
  change,
  loading = false,
}: {
  label: string;
  page: number;
  total: number;
  change: (n: number) => void;
  loading?: boolean;
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
export default function BillingOperations() {
  const [path, setPath] = useState(location.pathname + location.search);
  useEffect(() => {
    const update = () => setPath(location.pathname + location.search);
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);
  const match = path.split("?")[0].match(/^\/billing\/runs\/(\d+)\/?$/);
  return match ? (
    <BillingRunDetails key={match[1]} id={Number(match[1])} />
  ) : (
    <BillingDashboard
      key={path}
      initialDate={
        new URLSearchParams(location.search).get("run_date") || today()
      }
    />
  );
}
function BillingDashboard({ initialDate }: { initialDate: string }) {
  const [draftDate, setDraftDate] = useState(initialDate),
    [runDate, setRunDate] = useState(initialDate),
    [kind, setKind] = useState("due"),
    [page, setPage] = useState(1),
    [historyPage, setHistoryPage] = useState(1),
    [revision, setRevision] = useState(0),
    [confirm, setConfirm] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const preview = useLoad<Preview>(
    `/billing/preview?run_date=${encodeURIComponent(runDate)}&kind=${kind}&page=${page}&size=10`,
    revision,
  );
  const runs = useLoad<Page>(
    `/billing/runs?page=${historyPage}&size=10`,
    revision,
  );
  const stale = draftDate !== runDate;
  function loadPreview(e: FormEvent) {
    e.preventDefault();
    setRunDate(draftDate);
    setPage(1);
    setRevision((r) => r + 1);
    setError("");
    history.replaceState(
      null,
      "",
      `/billing?run_date=${encodeURIComponent(draftDate)}`,
    );
  }
  async function run() {
    if (busy || !preview.data || stale) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<Row>("/billing/run", "POST", {
        run_date: runDate,
      });
      navigate(`/billing/runs/${result.id}`);
    } catch (e) {
      setConfirm(false);
      setError(
        `${(e as Error).message}. The server may still be processing this request. Refresh run history before retrying; existing invoice periods will not be created twice.`,
      );
      setRevision((r) => r + 1);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-navy-900">
            Billing operations
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Preview due work, generate draft invoices and review each run.
          </p>
        </div>
        <Button
          secondary
          disabled={busy}
          onClick={() => {
            setRevision((r) => r + 1);
            setError("");
          }}
        >
          Refresh billing
        </Button>
      </div>
      <Card>
        <form onSubmit={loadPreview} className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            Billing date
            <input
              aria-label="Billing run date"
              type="date"
              className="mt-1 block rounded border p-2"
              required
              value={draftDate}
              disabled={busy}
              onChange={(e) => setDraftDate(e.target.value)}
            />
          </label>
          <Button type="submit" secondary disabled={busy || !draftDate}>
            Preview billing
          </Button>
          <Button
            disabled={busy || preview.loading || !preview.data || stale}
            onClick={() => {
              setError("");
              setConfirm(true);
            }}
          >
            Run billing
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-500">
          A run processes all due active subscriptions through the selected
          date, including missed periods. It also closes expired active or
          paused subscriptions when their plans require automatic closure.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          The preview is a snapshot. Billing rechecks eligibility and existing
          periods; concurrent work, discounts and corrections can change the
          final results. Cancelled invoice periods remain billed.
        </p>
        {stale && (
          <p role="status" className="mt-3 text-amber-800">
            Date changed. Preview this date before running billing.
          </p>
        )}
        <ErrorMessage error={error || preview.error} />
      </Card>
      {preview.loading && <p role="status">Loading billing preview…</p>}
      {preview.data && (
        <section aria-label="Billing preview" className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Preview date", runDate],
              ["Due subscriptions", preview.data.due_subscriptions],
              ["Automatic closures", preview.data.auto_close_subscriptions],
            ].map(([label, value]) => (
              <Card key={String(label)}>
                <p className="text-sm text-slate-500">{String(label)}</p>
                <p className="mt-2 text-2xl font-bold text-navy-900">
                  {String(value)}
                </p>
              </Card>
            ))}
          </div>
          <Card>
            <div className="mb-4 flex flex-wrap gap-2">
              <Button
                secondary={kind !== "due"}
                onClick={() => {
                  setKind("due");
                  setPage(1);
                }}
              >
                Due subscriptions
              </Button>
              <Button
                secondary={kind !== "closing"}
                onClick={() => {
                  setKind("closing");
                  setPage(1);
                }}
              >
                Automatic closures
              </Button>
            </div>
            <h2 className="mb-2 font-bold">
              {kind === "due"
                ? "Due subscriptions"
                : "Subscriptions closing automatically"}
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              {kind === "due"
                ? "Periods to check includes catch-up periods. Already invoiced periods are skipped; a schedule past expiry may be cleared without creating an invoice."
                : "These subscriptions close after any active billing catch-up. Paused subscriptions are not invoiced."}
            </p>
            <div className="overflow-x-auto [&_table]:min-w-[800px]">
              <Table
                rows={preview.data.items}
                columns={[
                  {
                    key: "number",
                    label: "Subscription",
                    render: (r) => (
                      <Link
                        path={`/subscriptions/${r.id}`}
                        label={text(r, "number")}
                      />
                    ),
                  },
                  { key: "customer_name", label: "Customer" },
                  { key: "plan_name", label: "Plan" },
                  {
                    key: "state",
                    label: "State",
                    render: (r) => <Badge value={text(r, "state")} />,
                  },
                  { key: "next_invoice_date", label: "Next billing date" },
                  {
                    key: "billing_period",
                    label: "Schedule",
                    render: (r) =>
                      `${r.billing_interval} × ${title(text(r, "billing_period"))}`,
                  },
                  { key: "first_period_end", label: "First period ends" },
                  { key: "due_periods", label: "Periods to check" },
                  { key: "expiry_date", label: "Expiry" },
                ]}
              />
            </div>
            <Pagination
              label="candidates"
              page={page}
              total={preview.data.total}
              change={setPage}
              loading={preview.loading}
            />
          </Card>
        </section>
      )}
      <Card>
        <h2 className="mb-4 font-bold">Run history</h2>
        <ErrorMessage error={runs.error} />
        {runs.loading ? (
          <p role="status">Loading run history…</p>
        ) : (
          <div className="overflow-x-auto [&_table]:min-w-[700px]">
            <Table
              rows={runs.data?.items || []}
              columns={[
                {
                  key: "id",
                  label: "Run",
                  render: (r) => (
                    <Link
                      path={`/billing/runs/${r.id}`}
                      label={`Run #${r.id}`}
                    />
                  ),
                },
                { key: "run_date", label: "Billing date" },
                {
                  key: "status",
                  label: "Status",
                  render: (r) => <Badge value={text(r, "status")} />,
                },
                { key: "subscriptions_processed", label: "Processed" },
                { key: "invoices_created", label: "Invoices created" },
                { key: "errors_count", label: "Failures" },
              ]}
            />
          </div>
        )}
        <Pagination
          label="runs"
          page={historyPage}
          total={runs.data?.total || 0}
          change={setHistoryPage}
          loading={runs.loading}
        />
      </Card>
      {confirm && preview.data && (
        <Dialog
          title="Run billing"
          close={() => {
            if (!busy) setConfirm(false);
          }}
        >
          <p className="mb-4">
            Generate draft invoices through <strong>{runDate}</strong> for all
            eligible subscriptions?
          </p>
          <ul className="mb-4 list-disc pl-5 text-sm">
            <li>
              {preview.data.due_subscriptions} due subscriptions in the preview.
            </li>
            <li>
              {preview.data.auto_close_subscriptions} subscriptions eligible for
              automatic closure.
            </li>
            <li>
              One subscription may produce multiple missed-period invoices.
            </li>
          </ul>
          <p className="mb-4 text-sm">
            This creates draft invoices and can automatically close expired
            subscriptions. Invoice confirmation, sending and payment recording
            are separate actions.
          </p>
          {busy && (
            <p role="status" className="mb-4 text-teal-800">
              Processing billing… Please wait for the results.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => void run()}>
              Generate draft invoices
            </Button>
            <Button secondary disabled={busy} onClick={() => setConfirm(false)}>
              Go back
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
function BillingRunDetails({ id }: { id: number }) {
  const query = new URLSearchParams(location.search);
  const [revision, setRevision] = useState(0),
    [invoicePage, setInvoicePage] = useState(
      Math.max(1, Number(query.get("invoice_page")) || 1),
    ),
    [failurePage, setFailurePage] = useState(
      Math.max(1, Number(query.get("failure_page")) || 1),
    );
  useEffect(() => {
    history.replaceState(
      null,
      "",
      `/billing/runs/${id}?invoice_page=${invoicePage}&failure_page=${failurePage}`,
    );
  }, [id, invoicePage, failurePage]);
  const run = useLoad<Row>(`/billing/runs/${id}`, revision);
  const invoices = useLoad<Page>(
    run.data
      ? `/billing/runs/${id}/invoices?page=${invoicePage}&size=10`
      : null,
    revision,
  );
  const failures = useLoad<Page>(
    run.data
      ? `/billing/runs/${id}/failures?page=${failurePage}&size=10`
      : null,
    revision,
  );
  const data = run.data;
  return (
    <article aria-label="Billing run details" className="space-y-5">
      <div className="flex flex-wrap justify-between gap-3">
        <Button
          secondary
          onClick={() =>
            navigate(data ? `/billing?run_date=${data.run_date}` : "/billing")
          }
        >
          Back to billing
        </Button>
        <Button
          secondary
          disabled={run.loading}
          onClick={() => setRevision((r) => r + 1)}
        >
          Refresh run
        </Button>
      </div>
      <ErrorMessage error={run.error} />
      {run.loading && <p role="status">Loading billing run…</p>}
      {data && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-3xl font-bold text-navy-900">
                Billing run #{id}
              </h1>
              <p className="mt-2 text-sm text-slate-500">
                Billing through {text(data, "run_date")}
              </p>
            </div>
            <Badge value={text(data, "status")} />
          </div>
          {Number(data.errors_count) > 0 && (
            <p
              role="alert"
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900"
            >
              This run recorded {String(data.errors_count)} subscription
              failures. Review the affected subscriptions below, even if the run
              status is Completed.
            </p>
          )}
          {data.status === "running" && (
            <p
              role="status"
              className="rounded-lg bg-teal-50 p-3 text-teal-800"
            >
              This run is marked as running. Refresh to check for results before
              starting another run.
            </p>
          )}
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Subscriptions processed", data.subscriptions_processed],
              ["Draft invoices created", data.invoices_created],
              ["Subscription failures", data.errors_count],
            ].map(([label, value]) => (
              <Card key={String(label)}>
                <p className="text-sm text-slate-500">{String(label)}</p>
                <p className="mt-2 text-2xl font-bold text-navy-900">
                  {String(value)}
                </p>
              </Card>
            ))}
          </div>
          <Card>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-sm text-slate-500">Started</dt>
                <dd>
                  {data.started_at
                    ? new Date(String(data.started_at)).toLocaleString()
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Finished</dt>
                <dd>
                  {data.finished_at
                    ? new Date(String(data.finished_at)).toLocaleString()
                    : "Not recorded"}
                </dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-slate-500">
              Processed counts successful subscription checks, including checks
              that create no new invoice. Invoice rows below show their current
              status.
            </p>
          </Card>
          <section aria-label="Generated invoices">
            <Card>
              <h2 className="mb-4 font-bold">Generated invoices</h2>
              <ErrorMessage error={invoices.error} />
              {invoices.loading ? (
                <p role="status">Loading generated invoices…</p>
              ) : (
                <div className="overflow-x-auto [&_table]:min-w-[750px]">
                  <Table
                    rows={invoices.data?.items || []}
                    columns={[
                      {
                        key: "number",
                        label: "Invoice",
                        render: (r) => (
                          <Link
                            path={`/invoices/${r.id}`}
                            label={text(r, "number")}
                          />
                        ),
                      },
                      { key: "customer_name", label: "Customer" },
                      {
                        key: "subscription_number",
                        label: "Subscription",
                        render: (r) => (
                          <Link
                            path={`/subscriptions/${r.subscription_id}`}
                            label={text(r, "subscription_number")}
                          />
                        ),
                      },
                      { key: "period_start", label: "Period start" },
                      { key: "period_end", label: "Period end" },
                      {
                        key: "state",
                        label: "Status",
                        render: (r) => <Badge value={text(r, "state")} />,
                      },
                      {
                        key: "total",
                        label: "Total",
                        render: (r) => money(r.total, text(r, "currency")),
                      },
                    ]}
                  />
                </div>
              )}
              <Pagination
                label="invoices"
                page={invoicePage}
                total={invoices.data?.total || 0}
                change={setInvoicePage}
                loading={invoices.loading}
              />
            </Card>
          </section>
          <section aria-label="Billing failures">
            <Card>
              <h2 className="mb-3 font-bold">Subscription failures</h2>
              <p className="mb-4 text-sm text-slate-500">
                Open each affected subscription and correct the reported issue.
                Then preview the same billing date and run billing again. The
                retry checks all eligible subscriptions, skips already invoiced
                periods and catches up remaining periods.
              </p>
              <ErrorMessage error={failures.error} />
              {failures.loading ? (
                <p role="status">Loading subscription failures…</p>
              ) : (
                <div className="overflow-x-auto [&_table]:min-w-[650px]">
                  <Table
                    rows={(failures.data?.items || []).map((r, index) => ({
                      ...r,
                      id: index,
                    }))}
                    columns={[
                      {
                        key: "subscription_number",
                        label: "Subscription",
                        render: (r) =>
                          r.subscription_id ? (
                            <Link
                              path={`/subscriptions/${r.subscription_id}`}
                              label={
                                text(r, "subscription_number") ||
                                `Subscription #${r.subscription_id}`
                              }
                            />
                          ) : (
                            <span>Run error</span>
                          ),
                      },
                      { key: "customer_name", label: "Customer" },
                      {
                        key: "message",
                        label: "Reported issue",
                        render: (r) => (
                          <p className="max-w-xl whitespace-pre-wrap break-words">
                            {text(r, "message")}
                          </p>
                        ),
                      },
                    ]}
                  />
                </div>
              )}
              <Pagination
                label="failures"
                page={failurePage}
                total={failures.data?.total || 0}
                change={setFailurePage}
                loading={failures.loading}
              />
              <div className="mt-4">
                <Button
                  secondary
                  disabled={data.status === "running"}
                  onClick={() => navigate(`/billing?run_date=${data.run_date}`)}
                >
                  Preview this date again
                </Button>
              </div>
            </Card>
          </section>
        </>
      )}
    </article>
  );
}
