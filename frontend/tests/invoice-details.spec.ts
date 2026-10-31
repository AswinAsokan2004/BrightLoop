import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
const api = "http://127.0.0.1:8100/api";
async function seed(request: APIRequestContext, foreign = false) {
  const login = await request.post(`${api}/auth/login`, {
    data: { email: "integration@example.com", password: "Integration!Pass123" },
  });
  const headers = {
    Authorization: `Bearer ${(await login.json()).access_token}`,
  };
  async function call(path: string, data?: unknown, method = "POST") {
    const response = await request.fetch(`${api}${path}`, {
      headers,
      data,
      method,
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  }
  const customer = foreign
    ? await call("/customers", {
        name: "Other Invoice Customer",
        email: `invoice-${Date.now()}@example.com`,
      })
    : { id: 1 };
  let subscription = await call("/subscriptions", {
    customer_id: customer.id,
    plan_id: 1,
    payment_term_id: 1,
    start_date: "2026-01-01",
    expiry_date: "2030-01-01",
    lines: [{ product_id: 1, quantity: 1 }],
  });
  for (const state of ["quotation", "confirmed", "active"])
    subscription = await call(`/subscriptions/${subscription.id}/state`, {
      state,
    });
  const invoice = await call(`/subscriptions/${subscription.id}/invoices`);
  return { invoice, subscription, call };
}
async function signIn(page: Page, customer = false) {
  await page.goto("/");
  await page
    .getByLabel("Email", { exact: true })
    .fill(customer ? "customer@example.com" : "integration@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(customer ? "Customer!Pass123" : "Integration!Pass123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}
async function confirm(page: Page, label: string) {
  await page
    .getByRole("article", { name: "Invoice details" })
    .getByRole("button", { name: label, exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: label, exact: true });
  await dialog.getByRole("button", { name: label, exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

test("invoice route supports reload, partial/full payment, named customer and subscription navigation", async ({
  page,
  request,
}, testInfo) => {
  const { invoice, subscription } = await seed(request);
  await signIn(page);
  await page.goto(`/invoices/${invoice.id}`);
  let workspace = page.getByRole("article", { name: "Invoice details" });
  await expect(
    workspace.getByRole("heading", { name: invoice.number, exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByText("Browser Customer", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    workspace.getByRole("heading", { name: invoice.number, exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("invoice-workspace.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    workspace.getByRole("heading", { name: invoice.number, exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: testInfo.outputPath("invoice-workspace-mobile.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await confirm(page, "Confirm invoice");
  await workspace
    .getByRole("button", { name: "Record payment", exact: true })
    .click();
  let payment = page.getByRole("dialog", {
    name: "Record payment",
    exact: true,
  });
  await payment.getByLabel("Amount", { exact: true }).fill("101.00");
  await payment.getByRole("button", { name: "Save", exact: true }).click();
  await expect(payment.getByRole("alert")).toBeVisible();
  await expect(payment.getByLabel("Amount", { exact: true })).toHaveValue("101.00");
  await payment.getByLabel("Amount", { exact: true }).fill("40.00");
  await payment.getByLabel("Note", { exact: true }).fill("First instalment");
  await payment.getByRole("button", { name: "Save", exact: true }).click();
  await expect(payment).toHaveCount(0);
  await expect(
    workspace.getByText("First instalment", { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByRole("button", { name: "Cancel invoice", exact: true }),
  ).toHaveCount(0);
  await workspace
    .getByRole("button", { name: "Record payment", exact: true })
    .click();
  payment = page.getByRole("dialog", { name: "Record payment", exact: true });
  await expect(payment.getByLabel("Amount", { exact: true })).toHaveValue(
    "60.00",
  );
  await payment.getByRole("button", { name: "Save", exact: true }).click();
  await expect(payment).toHaveCount(0);
  await expect(
    workspace.getByText("Paid", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    workspace.getByRole("button", { name: "Record payment", exact: true }),
  ).toHaveCount(0);
  await workspace
    .getByRole("link", { name: subscription.number, exact: true })
    .click();
  await expect(page).toHaveURL(`/subscriptions/${subscription.id}`);
  await page.goBack();
  await expect(
    workspace.getByRole("heading", { name: invoice.number, exact: true }),
  ).toBeVisible();
  await workspace
    .getByRole("button", { name: "Back to invoices", exact: true })
    .click();
  await expect(page).toHaveURL(/\/invoices$/);
  await page.goBack();
  await expect(workspace).toBeVisible();
});

test("invoice cancellation requires confirmation and cancelled invoices have no payment actions", async ({
  page,
  request,
}) => {
  const { invoice } = await seed(request);
  await signIn(page);
  await page.goto(`/invoices/${invoice.id}`);
  await page
    .getByRole("button", { name: "Cancel invoice", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Cancel invoice" })
    .getByRole("button", { name: "Go back" })
    .click();
  await expect(page.getByText("Draft", { exact: true })).toBeVisible();
  await confirm(page, "Cancel invoice");
  await expect(
    page.getByText(
      "This invoice is cancelled. Its billing period remains invoiced.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Confirm invoice", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Record payment", exact: true }),
  ).toHaveCount(0);
});

test("customer invoice workspace uses scoped reads, hides write actions and rejects foreign invoices", async ({
  page,
  request,
}) => {
  const own = await seed(request),
    foreign = await seed(request, true);
  const forbidden: string[] = [];
  page.on("request", (req) => {
    if (/\/api\/(customers|subscriptions|invoices)(\/|\?)/.test(req.url()))
      forbidden.push(req.url());
  });
  await signIn(page, true);
  await page.goto(`/portal/invoices/${own.invoice.id}`);
  const workspace = page.getByRole("article", { name: "Invoice details" });
  await expect(
    workspace.getByRole("heading", { name: own.invoice.number, exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByRole("link", { name: own.subscription.number, exact: true }),
  ).toHaveAttribute("href", `/portal/subscriptions/${own.subscription.id}`);
  for (const name of [
    "Confirm invoice",
    "Cancel invoice",
    "Record payment",
    "Send email",
  ])
    await expect(
      workspace.getByRole("button", { name, exact: true }),
    ).toHaveCount(0);
  const popupOpened = page.waitForEvent("popup");
  await workspace.getByRole("button", { name: "Print / Save as PDF" }).click();
  const popup = await popupOpened;
  await expect(popup.getByRole("heading", { name: `Invoice ${own.invoice.number}`, exact: true })).toBeVisible();
  await popup.close();
  await page.goto(`/portal/invoices/${foreign.invoice.id}`);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: foreign.invoice.number, exact: true }),
  ).toHaveCount(0);
  expect(forbidden).toEqual([]);
});

test("invoice email confirmation handles failures and retry without sending real email", async ({ page, request }) => {
  const { invoice, call } = await seed(request);
  await call(`/invoices/${invoice.id}/confirm`);
  let attempts = 0;
  await page.route(`**/api/invoices/${invoice.id}/send`, async route => {
    expect(route.request().method()).toBe("POST");
    attempts++;
    await route.fulfill(attempts === 1
      ? { status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Test email service unavailable" }) }
      : { status: 200, contentType: "application/json", body: JSON.stringify(invoice) });
  });
  await signIn(page);
  await page.goto(`/invoices/${invoice.id}`);
  const workspace = page.getByRole("article", { name: "Invoice details" });
  await expect(workspace.getByText(/This invoice is overdue/)).toBeVisible();
  await workspace.getByRole("button", { name: "Send email", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Send email", exact: true });
  expect(attempts).toBe(0);
  await dialog.getByRole("button", { name: "Go back" }).click();
  expect(attempts).toBe(0);
  await workspace.getByRole("button", { name: "Send email", exact: true }).click();
  await dialog.getByRole("button", { name: "Send email", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Test email service unavailable");
  expect(attempts).toBe(1);
  await dialog.getByRole("button", { name: "Send email", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(workspace.getByRole("status")).toContainText("Invoice email queued");
  expect(attempts).toBe(2);
  await expect(workspace.getByRole("heading", { name: invoice.number, exact: true })).toBeVisible();
});
