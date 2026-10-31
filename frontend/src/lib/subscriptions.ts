import type { Row } from "./api";

export type State =
  | "draft"
  | "quotation"
  | "confirmed"
  | "active"
  | "paused"
  | "closed";
export type Named = { id: number; name: string };
export type PlanPolicy = Named & {
  billing_period: string;
  billing_interval: number;
  min_quantity: number;
  start_date: string;
  end_date: string | null;
  active: boolean;
  auto_close: boolean;
  closable: boolean;
  pausable: boolean;
  renewable: boolean;
  trial_days: number;
};
export type SubscriptionLine = Row & {
  product: Named;
  variant: Named | null;
  description: string | null;
  quantity: number;
  unit_price: string;
  discount_amount: string;
  untaxed_amount: string;
  tax_amount: string;
  total_amount: string;
  taxes: {
    id: number;
    name: string;
    rate: string;
    tax_type: string;
    is_inclusive: boolean;
  }[];
};
export type StateLog = {
  id: number;
  from_state: State | null;
  to_state: State;
  reason: string | null;
  created_at: string;
  changed_by_user: Named | null;
};
export type Subscription = Row & {
  number: string;
  state: State;
  customer_name: string;
  plan_name: string;
  currency: string;
  start_date: string;
  expiry_date: string | null;
  next_invoice_date: string | null;
  last_invoiced_date: string | null;
  trial_end_date: string | null;
  quotation_valid_until: string | null;
  recurring_untaxed: string;
  recurring_tax: string;
  recurring_total: string;
  notes: string | null;
  close_reason: string | null;
  closed_at: string | null;
  paused_at: string | null;
  customer: Named & {
    company_name: string | null;
    email: string;
    phone: string | null;
    address_line1: string | null;
    address_line2: string | null;
    city: string | null;
    state: string | null;
    postal_code: string | null;
    country: string | null;
    tax_id: string | null;
  };
  plan: PlanPolicy;
  payment_term: Named & { due_days: number };
  salesperson: Named | null;
  quotation_template: (Named & { validity_days: number }) | null;
  lines: SubscriptionLine[];
  state_logs: StateLog[];
};
export type StateAction = { state: State; label: string; disabled?: string };
export function localDay() {
  const day = new Date();
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}
export function quoteExpired(
  subscription: Pick<Subscription, "state" | "quotation_valid_until">,
  day = localDay(),
) {
  return (
    subscription.state === "quotation" &&
    !!subscription.quotation_valid_until &&
    subscription.quotation_valid_until < day
  );
}
export function availableActions(
  sub: Subscription,
  portal: boolean,
  day = localDay(),
): StateAction[] {
  const expired = !!sub.expiry_date && sub.expiry_date < day;
  const close: StateAction = {
    state: "closed",
    label: "Close subscription",
    disabled:
      !sub.plan.closable && !expired
        ? "This plan does not allow closure before expiry."
        : undefined,
  };
  switch (sub.state) {
    case "draft":
      return portal
        ? []
        : [
            {
              state: "quotation",
              label: "Create quotation",
              disabled: sub.lines.length
                ? undefined
                : "Add at least one product line first.",
            },
          ];
    case "quotation":
      return portal
        ? []
        : [
            {
              state: "confirmed",
              label: "Confirm quotation",
              disabled: quoteExpired(sub, day)
                ? "This quotation has expired. Return it to draft and create a new quotation."
                : sub.lines.reduce((sum, line) => sum + line.quantity, 0) <
                    sub.plan.min_quantity
                  ? `This plan requires at least ${sub.plan.min_quantity} units.`
                  : !sub.plan.active ||
                      sub.start_date < sub.plan.start_date ||
                      (!!sub.plan.end_date &&
                        sub.start_date > sub.plan.end_date)
                    ? "The plan is unavailable on this subscription’s start date."
                    : undefined,
            },
            { state: "draft", label: "Return to draft" },
            { state: "closed", label: "Close quotation" },
          ];
    case "confirmed":
      return portal
        ? []
        : [
            { state: "active", label: "Activate subscription" },
            { state: "closed", label: "Close subscription" },
          ];
    case "active":
      return [
        {
          state: "paused",
          label: "Pause subscription",
          disabled: sub.plan.pausable
            ? undefined
            : "This plan does not allow pausing.",
        },
        close,
      ];
    case "paused":
      return [{ state: "active", label: "Resume subscription" }, close];
    default:
      return [];
  }
}
export function renewalDisabled(sub: Subscription) {
  return !sub.plan.renewable
    ? "This plan does not allow renewal."
    : !sub.expiry_date
      ? "This subscription has no expiry date to extend."
      : undefined;
}
export function displayDate(value: string | null | undefined) {
  if (!value) return "Not set";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
export function cents(value: string): bigint {
  const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(value);
  if (!match) throw new Error("Invalid currency amount");
  return (
    (BigInt(match[2]) * 100n + BigInt((match[3] || "").padEnd(2, "0"))) *
    (match[1] ? -1n : 1n)
  );
}
function decimal(value: bigint) {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  return `${negative ? "-" : ""}${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`;
}
export function sumAmounts(values: string[]) {
  return decimal(values.reduce((sum, value) => sum + cents(value), 0n));
}
export function lineSubtotal(
  line: Pick<SubscriptionLine, "unit_price" | "quantity">,
) {
  return decimal(cents(line.unit_price) * BigInt(line.quantity));
}
