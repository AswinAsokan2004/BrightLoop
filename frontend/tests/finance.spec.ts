import { test, expect } from "@playwright/test";
test("finance filters, currency isolation, pagination and invoice drill-down persist across reload/back", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(90000);
  const api = "http://127.0.0.1:8100/api";
  const login = await request.post(`${api}/auth/login`, {
    data: { email: "integration@example.com", password: "Integration!Pass123" },
  });
  const headers = {
    Authorization: `Bearer ${(await login.json()).access_token}`,
  };
  async function call(path: string, data: unknown) {
    const response = await request.post(`${api}${path}`, { headers, data });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  }
  const tag = String(Date.now());
  const customer = await call("/customers", {
    name: `Finance Customer ${tag}`,
    email: `finance-${tag}@example.com`,
  });
  const plan = await call("/plans", {
    name: `Finance Plan ${tag}`,
    code: `FIN-${tag}`,
    price: "100.00",
    billing_period: "monthly",
    start_date: "2020-01-01",
  });
  for (let i = 0; i < 12; i++) {
    const sub = await call("/subscriptions", {
      customer_id: customer.id,
      plan_id: plan.id,
      payment_term_id: 1,
      start_date: "2026-01-01",
      expiry_date: "2030-01-01",
      currency: i === 11 ? "USD" : "INR",
      lines: [{ product_id: 1, quantity: i === 11 ? 2 : 1 }],
    });
    for (const state of ["quotation", "confirmed", "active"])
      await call(`/subscriptions/${sub.id}/state`, { state });
    const invoice = await call(`/subscriptions/${sub.id}/invoices`, {});
    await call(`/invoices/${invoice.id}/confirm`, {});
    if (i === 0) {
      await call(`/invoices/${invoice.id}/payments`, {
        method: "bank_transfer",
        amount: "40.00",
        payment_date: new Date().toLocaleDateString("en-CA"),
        reference: "FINANCE-RECEIPT",
      });
    }
  }
  await page.goto("/reports");
  await page
    .getByLabel("Email", { exact: true })
    .fill("integration@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill("Integration!Pass123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Revenue reports", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Search customer names").fill(customer.name);
  await expect(
    page
      .getByLabel("Filter by customer")
      .getByRole("option", { name: customer.name, exact: true }),
  ).toHaveCount(1);
  await page.getByLabel("Filter by customer").selectOption(String(customer.id));
  await page.getByLabel("Search plan names").fill(plan.name);
  await expect(
    page
      .getByLabel("Filter by plan")
      .getByRole("option", { name: plan.name, exact: true }),
  ).toHaveCount(1);
  await page.getByLabel("Filter by plan").selectOption(String(plan.id));
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  const active = page.getByRole("button", { name: /^Active subscriptions/ });
  await expect(active).toContainText("11");
  await expect(
    page.getByRole("button", { name: /^Revenue collected/ }),
  ).toContainText("INR 40.00");
  await expect(
    page.getByRole("button", { name: /^Outstanding balance/ }),
  ).toContainText("INR 1060.00");
  await expect(
    page
      .getByRole("region", { name: "Recent payments", exact: true })
      .getByText("FINANCE-RECEIPT", { exact: true }),
  ).toBeVisible();
  const invoices = page.getByRole("region", {
    name: "Invoice balances",
    exact: true,
  });
  await expect(invoices.getByRole("link")).toHaveCount(10);
  await page
    .getByRole("button", { name: "Next invoices", exact: true })
    .click();
  await expect(invoices.getByRole("link")).toHaveCount(1);
  await page.reload();
  await expect(invoices.getByRole("link")).toHaveCount(1);
  await expect(page.getByLabel("Filter by customer")).toHaveValue(
    String(customer.id),
  );
  await invoices.getByRole("link").click();
  await expect(
    page.getByRole("article", { name: "Invoice details" }),
  ).toBeVisible();
  await page.goBack();
  await expect(invoices.getByRole("link")).toHaveCount(1);
  await expect(page.getByLabel("Filter by plan")).toHaveValue(String(plan.id));
  await page.getByRole("button", { name: /^Outstanding balance/ }).click();
  await expect(page.getByLabel("Finance invoice view")).toHaveValue(
    "outstanding",
  );
  await expect(invoices.getByRole("link")).toHaveCount(10);
  await page.getByLabel("Report currency").selectOption("USD");
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(active).toContainText("1");
  await expect(
    page.getByRole("button", { name: /^Revenue collected/ }),
  ).toContainText("USD 0.00");
  await expect(
    page.getByRole("button", { name: /^Invoiced total/ }),
  ).toContainText("USD 200.00");
  await page.getByLabel("Report from date").fill("2030-02-01");
  await page.getByLabel("Report to date").fill("2030-01-01");
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "From date must be on or before To date",
  );
  await page.getByLabel("Report to date").fill("2030-03-01");
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(invoices.getByRole("link")).toHaveCount(0);
  await expect(active).toContainText("1");
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await expect(page.getByLabel("Filter by customer")).toHaveValue("");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "Revenue reports", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: testInfo.outputPath("finance-mobile.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect.poll(async () => (await page.locator("aside").boundingBox())?.x).toBe(0);
  await page.screenshot({
    path: testInfo.outputPath("finance-overview.png"),
    fullPage: true,
  });
});


test("finance request errors are visible and refresh recovers", async ({ page }) => {
  let fail = true;
  await page.route("**/api/reports/finance?*", async route => {
    if (fail) await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Finance temporarily unavailable" }) });
    else await route.continue();
  });
  await page.goto("/reports");
  await page.getByLabel("Email", { exact: true }).fill("integration@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Integration!Pass123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Finance temporarily unavailable");
  await expect(page.getByRole("button", { name: /^Revenue collected/ })).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Revenue collected/ })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});
