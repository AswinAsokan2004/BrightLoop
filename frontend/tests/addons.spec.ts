import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
const api = "http://127.0.0.1:8100/api";
async function seed(request: APIRequestContext) {
  const auth = await request.post(`${api}/auth/login`, {
    data: { email: "integration@example.com", password: "Integration!Pass123" },
  });
  const headers = {
    Authorization: `Bearer ${(await auth.json()).access_token}`,
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
  const tag = String(Date.now());
  const plan = await call("/plans", {
    name: `Add-on plan ${tag}`,
    code: `AD-${tag}`,
    price: "100.00",
    billing_period: "monthly",
    start_date: "2020-01-01",
    pausable: true,
  });
  const tax = await call("/taxes", {
    name: "Storage GST",
    tax_type: "percent",
    rate: "18.00",
  });
  const addon = await call("/products", {
    name: `Portal storage ${tag}`,
    product_type: "addon",
    sales_price: "20.00",
    cost_price: "2.00",
    tax_ids: [tax.id],
  });
  const attribute = await call("/attributes", {
    name: `Storage tier ${tag}`,
    values: [{ value: "Large", extra_price: "5.00" }],
  });
  const variant = await call(`/products/${addon.id}/variants`, {
    name: "Large storage",
    sku: `ADDON-${tag}`,
    attribute_value_ids: [attribute.values[0].id],
  });
  const date = new Date(),
    expiry = new Date();
  expiry.setFullYear(expiry.getFullYear() + 1);
  const sub = await call("/subscriptions", {
    customer_id: 1,
    plan_id: plan.id,
    payment_term_id: 1,
    start_date: date.toLocaleDateString("en-CA"),
    expiry_date: expiry.toLocaleDateString("en-CA"),
    lines: [{ product_id: 1, quantity: 1 }],
  });
  for (const state of ["quotation", "confirmed", "active"])
    await call(`/subscriptions/${sub.id}/state`, { state });
  const invoice = await call(`/subscriptions/${sub.id}/invoices`);
  return { sub, addon, variant, invoice, call };
}
async function signIn(page: Page, subId: number) {
  await page.goto(`/portal/subscriptions/${subId}`);
  await page.getByLabel("Email", { exact: true }).fill("customer@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Customer!Pass123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("tab", { name: "Add-ons", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Manage add-ons", exact: true }),
  ).toBeVisible();
}
test("customer reviews variant pricing, confirms next-period add-ons and removes them without changing invoices", async ({
  page,
  request,
}, testInfo) => {
  const { sub, addon, variant, invoice, call } = await seed(request);
  const original = await call(`/invoices/${invoice.id}`, undefined, "GET");
  const forbidden: string[] = [];
  let writes = 0;
  page.on("request", (req) => {
    if (/\/api\/(products|plans|customers|users)(\/|\?)/.test(req.url()))
      forbidden.push(req.url());
    if (
      req.method() === "PUT" &&
      req.url().endsWith(`/subscriptions/${sub.id}/addons`)
    )
      writes++;
  });
  await signIn(page, sub.id);
  const manager = page.getByRole("region", {
    name: "Subscription add-ons",
    exact: true,
  });
  await manager.getByLabel("Search add-ons").fill(addon.name);
  const name = `${addon.name} — ${variant.name}`;
  await manager
    .getByRole("button", { name: `Add ${name}`, exact: true })
    .click();
  await manager.getByLabel(`Quantity for ${name}`, { exact: true }).fill("2");
  await manager
    .getByRole("button", { name: "Review add-on changes", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Review add-on changes",
    exact: true,
  });
  await expect(dialog.getByText("INR 159.00", { exact: true })).toBeVisible();
  await expect(
    dialog.getByText(/No prorated charge or credit is created/),
  ).toBeVisible();
  expect(writes).toBe(0);
  await dialog
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  expect(writes).toBe(0);
  await manager
    .getByRole("button", { name: "Review add-on changes", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Confirm add-on changes", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await expect(manager.getByText(/Add-on selection saved/)).toBeVisible();
  expect(writes).toBe(1);
  await expect(
    manager.getByLabel(`Quantity for ${name}`, { exact: true }),
  ).toHaveValue("2");
  await expect(
    manager.getByRole("button", { name: "Review add-on changes", exact: true }),
  ).toBeDisabled();
  const updated = await call(`/subscriptions/${sub.id}`, undefined, "GET");
  expect(
    updated.lines.filter((line: { is_addon: boolean }) => line.is_addon),
  ).toHaveLength(1);
  expect(
    updated.lines.find((line: { is_addon: boolean }) => !line.is_addon)
      .unit_price,
  ).toBe("100.00");
  expect(await call(`/invoices/${invoice.id}`, undefined, "GET")).toEqual(
    original,
  );
  const newInvoice = await call(`/subscriptions/${sub.id}/invoices`);
  expect(newInvoice.total).toBe("159.00");
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "Add-ons", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    manager.getByLabel(`Quantity for ${name}`, { exact: true }),
  ).toHaveValue("2");
  await page.screenshot({
    path: testInfo.outputPath("customer-addons.png"),
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
    path: testInfo.outputPath("customer-addons-mobile.png"),
    fullPage: true,
  });
  await manager
    .getByRole("button", { name: `Remove ${name}`, exact: true })
    .click();
  await manager
    .getByRole("button", { name: "Review add-on changes", exact: true })
    .click();
  await expect(
    dialog
      .getByText("New estimated period total", { exact: true })
      .locator("..")
      .getByText("INR 100.00", { exact: true }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Confirm add-on changes", exact: true })
    .click();
  await expect(
    manager.getByText("No customer-managed add-ons enabled.", { exact: true }),
  ).toBeVisible();
  expect(
    (await call(`/subscriptions/${sub.id}`, undefined, "GET")).lines.filter(
      (line: { is_addon: boolean }) => line.is_addon,
    ),
  ).toHaveLength(0);
  expect(
    (await call(`/invoices/${newInvoice.id}`, undefined, "GET")).total,
  ).toBe("159.00");
  expect(forbidden).toEqual([]);
});
test("a changed catalog price requires a fresh preview before confirmation", async ({
  page,
  request,
}) => {
  const { sub, addon, call } = await seed(request);
  await signIn(page, sub.id);
  const manager = page.getByRole("region", {
    name: "Subscription add-ons",
    exact: true,
  });
  await manager.getByLabel("Search add-ons").fill(addon.name);
  await manager
    .getByRole("button", { name: `Add ${addon.name}`, exact: true })
    .click();
  await manager
    .getByRole("button", { name: "Review add-on changes", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Review add-on changes",
    exact: true,
  });
  await expect(dialog.getByText("INR 123.60", { exact: true })).toBeVisible();
  await call(`/products/${addon.id}`, { sales_price: "30.00" }, "PATCH");
  await dialog
    .getByRole("button", { name: "Confirm add-on changes", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await expect(manager.getByRole("alert")).toContainText(
    "Review a fresh add-on preview",
  );
  await manager
    .getByRole("button", { name: "Review add-on changes", exact: true })
    .click();
  await expect(dialog.getByText("INR 135.40", { exact: true })).toBeVisible();
  await dialog
    .getByRole("button", { name: "Confirm add-on changes", exact: true })
    .click();
  await expect(manager.getByText(/Add-on selection saved/)).toBeVisible();
});
test("paused subscriptions keep add-on management read-only and avoid catalog requests", async ({
  page,
  request,
}) => {
  const { sub, call } = await seed(request);
  await call(`/subscriptions/${sub.id}/state`, { state: "paused" });
  const catalogs: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/addon-options")) catalogs.push(req.url());
  });
  await signIn(page, sub.id);
  const manager = page.getByRole("region", {
    name: "Subscription add-ons",
    exact: true,
  });
  await expect(
    manager.getByText(
      "Resume or activate this subscription before changing add-ons.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(manager.getByLabel("Search add-ons")).toHaveCount(0);
  await expect(
    manager.getByRole("button", { name: "Review add-on changes", exact: true }),
  ).toHaveCount(0);
  expect(catalogs).toEqual([]);
});
