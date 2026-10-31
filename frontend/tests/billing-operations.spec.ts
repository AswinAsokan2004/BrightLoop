import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
const api = "http://127.0.0.1:8100/api";
const day = (offset = 0) => {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toLocaleDateString("en-CA");
};
async function seed(request: APIRequestContext) {
  const response = await request.post(`${api}/auth/login`, {
    data: { email: "integration@example.com", password: "Integration!Pass123" },
  });
  const headers = {
    Authorization: `Bearer ${(await response.json()).access_token}`,
  };
  async function call(path: string, data: unknown) {
    const result = await request.post(`${api}${path}`, { headers, data });
    expect(result.ok(), await result.text()).toBeTruthy();
    return result.json();
  }
  const tag = String(Date.now());
  const plan = await call("/plans", {
    name: `Billing daily ${tag}`,
    code: `BILL-${tag}`,
    price: "100.00",
    billing_period: "daily",
    start_date: "2020-01-01",
    auto_close: true,
    pausable: true,
  });
  const subs = [];
  for (let i = 0; i < 2; i++) {
    const sub = await call("/subscriptions", {
      customer_id: 1,
      plan_id: plan.id,
      payment_term_id: 1,
      start_date: day(-2),
      expiry_date: day(-1),
      lines: [{ product_id: 1, quantity: 1 }],
    });
    for (const state of [
      "quotation",
      "confirmed",
      "active",
      ...(i === 1 ? ["paused"] : []),
    ])
      await call(`/subscriptions/${sub.id}/state`, { state });
    subs.push(sub);
  }
  return { subs, call };
}
async function signIn(page: Page) {
  await page.goto("/billing");
  await page
    .getByLabel("Email", { exact: true })
    .fill("integration@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill("Integration!Pass123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Billing operations", exact: true }),
  ).toBeVisible();
}
test("billing previews catch-up and closures, requires confirmation, and links run results to invoices", async ({
  page,
  request,
}, testInfo) => {
  const { subs } = await seed(request);
  let submissions = 0;
  page.on("request", (req) => {
    if (req.method() === "POST" && req.url().endsWith("/api/billing/run"))
      submissions++;
  });
  await signIn(page);
  const preview = page.getByRole("region", {
    name: "Billing preview",
    exact: true,
  });
  const row = preview.getByRole("row").filter({ hasText: subs[0].number });
  await expect(row).toBeVisible();
  await expect(row.getByRole("cell", { name: "2", exact: true })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("billing-preview.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(async () => (await page.locator("aside").boundingBox())?.x)
    .toBe(-256);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: testInfo.outputPath("billing-preview-mobile.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect
    .poll(async () => (await page.locator("aside").boundingBox())?.x)
    .toBe(0);

  await preview
    .getByRole("button", { name: "Automatic closures", exact: true })
    .click();
  await expect(
    preview.getByRole("link", { name: subs[1].number, exact: true }),
  ).toBeVisible();
  await page.getByLabel("Billing run date").fill(day(1));
  await expect(
    page.getByRole("button", { name: "Run billing", exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole("status")).toContainText("Date changed");
  await page.getByLabel("Billing run date").fill(day());
  await page
    .getByRole("button", { name: "Preview billing", exact: true })
    .click();
  await page.getByRole("button", { name: "Run billing", exact: true }).click();
  const confirmation = page.getByRole("dialog", {
    name: "Run billing",
    exact: true,
  });
  await expect(
    confirmation.getByText(/One subscription may produce multiple/),
  ).toBeVisible();
  expect(submissions).toBe(0);
  await confirmation
    .getByRole("button", { name: "Go back", exact: true })
    .click();
  expect(submissions).toBe(0);
  await page.getByRole("button", { name: "Run billing", exact: true }).click();
  await confirmation
    .getByRole("button", { name: "Generate draft invoices", exact: true })
    .click();
  const results = page.getByRole("article", {
    name: "Billing run details",
    exact: true,
  });
  await expect(results).toBeVisible();
  await expect(page).toHaveURL(/\/billing\/runs\/\d+/);
  expect(submissions).toBe(1);
  const invoices = results.getByRole("region", {
    name: "Generated invoices",
    exact: true,
  });
  await expect(
    invoices.getByRole("link", { name: subs[0].number, exact: true }),
  ).toHaveCount(2);
  await expect(invoices.getByText("Draft", { exact: true })).toHaveCount(2);
  await page.reload();
  await expect(
    invoices.getByRole("link", { name: subs[0].number, exact: true }),
  ).toHaveCount(2);
  await page.screenshot({
    path: testInfo.outputPath("billing-run.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(async () => (await page.locator("aside").boundingBox())?.x)
    .toBe(-256);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: testInfo.outputPath("billing-run-mobile.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await invoices.getByRole("link", { name: /INV\// }).first().click();
  await expect(
    page.getByRole("article", { name: "Invoice details" }),
  ).toBeVisible();
  await page.goBack();
  await expect(results).toBeVisible();
  await results
    .getByRole("button", { name: "Preview this date again", exact: true })
    .click();
  await expect(page.getByLabel("Billing run date")).toHaveValue(day());
  await expect(
    preview.getByRole("link", { name: subs[0].number, exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Run billing", exact: true }).click();
  await confirmation
    .getByRole("button", { name: "Generate draft invoices", exact: true })
    .click();
  await expect(
    results
      .getByRole("region", { name: "Generated invoices" })
      .getByRole("link", { name: /INV\// }),
  ).toHaveCount(0);
});
test("billing run failures identify subscriptions and support a reviewed retry date", async ({
  page,
  request,
}) => {
  const { subs, call } = await seed(request);
  const run = await call("/billing/run", { run_date: day() });
  await page.route(`**/api/billing/runs/${run.id}`, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.errors_count = 1;
    body.status = "completed";
    await route.fulfill({ response, json: body });
  });
  await page.route(`**/api/billing/runs/${run.id}/failures?*`, (route) =>
    route.fulfill({
      json: {
        items: [
          {
            subscription_id: subs[0].id,
            subscription_number: subs[0].number,
            customer_name: "Browser Customer",
            message: "Correct the subscription billing setup",
          },
        ],
        total: 1,
        page: 1,
        size: 10,
      },
    }),
  );
  await signIn(page);
  await page.goto(`/billing/runs/${run.id}`);
  await expect(page.getByRole("alert")).toContainText(
    "1 subscription failures",
  );
  const failures = page.getByRole("region", {
    name: "Billing failures",
    exact: true,
  });
  await expect(
    failures.getByText("Correct the subscription billing setup", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    failures.getByRole("link", { name: subs[0].number, exact: true }),
  ).toHaveAttribute("href", `/subscriptions/${subs[0].id}`);
  await page
    .getByRole("button", { name: "Preview this date again", exact: true })
    .click();
  await expect(page.getByLabel("Billing run date")).toHaveValue(day());
  await expect(
    page.getByRole("heading", { name: "Billing operations", exact: true }),
  ).toBeVisible();
});
test("billing request failures advise checking history and allow preview refresh", async ({
  page,
  request,
}) => {
  await seed(request);
  await page.route("**/api/billing/run", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Test billing unavailable" }),
    }),
  );
  await signIn(page);
  await page.getByRole("button", { name: "Run billing", exact: true }).click();
  await page
    .getByRole("dialog", { name: "Run billing", exact: true })
    .getByRole("button", { name: "Generate draft invoices", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Refresh run history before retrying",
  );
  await expect(
    page.getByRole("heading", { name: "Run history", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Refresh billing", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Run billing", exact: true }),
  ).toBeEnabled();
});
