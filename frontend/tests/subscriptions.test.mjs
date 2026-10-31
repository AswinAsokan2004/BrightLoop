import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import ts from "typescript";
const source = await fs.readFile(
  new URL("../src/lib/subscriptions.ts", import.meta.url),
  "utf8",
);
const js = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2021,
    module: ts.ModuleKind.ESNext,
  },
}).outputText;
const {
  availableActions,
  quoteExpired,
  renewalDisabled,
  sumAmounts,
  lineSubtotal,
} = await import(
  `data:text/javascript;base64,${Buffer.from(js).toString("base64")}`
);
const fixture = () => ({
  state: "active",
  start_date: "2026-01-01",
  expiry_date: "2027-01-01",
  quotation_valid_until: "2026-10-31",
  plan: {
    active: true,
    start_date: "2020-01-01",
    end_date: null,
    pausable: false,
    closable: false,
    renewable: true,
    min_quantity: 5,
  },
  lines: [{ quantity: 5 }],
});
test("quotation validity includes its final day and excludes accepted quotations", () => {
  const sub = { ...fixture(), state: "quotation" };
  assert.equal(quoteExpired(sub, "2026-10-31"), false);
  assert.equal(quoteExpired(sub, "2026-11-01"), true);
  assert.equal(quoteExpired({ ...sub, state: "active" }, "2026-11-01"), false);
  assert.match(
    availableActions(sub, false, "2026-11-01")[0].disabled,
    /expired/,
  );
});
test("plan policies prevent pause and early closure but allow closure after expiry", () => {
  const sub = fixture();
  assert.match(
    availableActions(sub, true, "2026-10-31")[0].disabled,
    /pausing/,
  );
  assert.match(
    availableActions(sub, true, "2026-10-31")[1].disabled,
    /before expiry/,
  );
  assert.equal(
    availableActions(sub, true, "2027-01-02")[1].disabled,
    undefined,
  );
});
test("customers cannot confirm or initially activate contracts and closed records have no actions", () => {
  assert.deepEqual(
    availableActions({ ...fixture(), state: "draft" }, true),
    [],
  );
  assert.deepEqual(
    availableActions({ ...fixture(), state: "confirmed" }, true),
    [],
  );
  assert.deepEqual(
    availableActions({ ...fixture(), state: "closed" }, false),
    [],
  );
  assert.equal(
    availableActions({ ...fixture(), state: "paused" }, true)[0].label,
    "Resume subscription",
  );
});
test("confirmation checks minimum quantities and plan availability", () => {
  const sub = {
    ...fixture(),
    state: "quotation",
    quotation_valid_until: "2027-01-01",
    lines: [{ quantity: 1 }],
  };
  assert.match(
    availableActions(sub, false, "2026-10-31")[0].disabled,
    /at least 5/,
  );
  assert.match(
    availableActions(
      {
        ...sub,
        lines: [{ quantity: 5 }],
        plan: { ...sub.plan, active: false },
      },
      false,
      "2026-10-31",
    )[0].disabled,
    /unavailable/,
  );
});
test("renewal requires a renewable plan and an expiry date", () => {
  assert.equal(renewalDisabled(fixture()), undefined);
  assert.match(
    renewalDisabled({ ...fixture(), expiry_date: null }),
    /no expiry/,
  );
  assert.match(
    renewalDisabled({
      ...fixture(),
      plan: { ...fixture().plan, renewable: false },
    }),
    /does not allow/,
  );
});
test("preview totals use exact cents for large values and discounts", () => {
  assert.equal(sumAmounts(["9999999999.99", "0.01"]), "10000000000.00");
  assert.equal(sumAmounts(["0.10", "0.20"]), "0.30");
  assert.equal(lineSubtotal({ unit_price: "1760.00", quantity: 5 }), "8800.00");
  assert.equal(sumAmounts(["10.00", "-3.01"]), "6.99");
});
