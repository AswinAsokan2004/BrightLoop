import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
test.setTimeout(60000);
const api = "http://127.0.0.1:8100/api";
let sequence = 0;
const day = () => new Date().toLocaleDateString("en-CA");
const future = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 1);
  return d.toLocaleDateString("en-CA");
};
async function seed(
  request: APIRequestContext,
  values: {
    customer?: boolean;
    closable?: boolean;
    pausable?: boolean;
    state?: "quotation" | "active";
  } = {},
) {
  const response = await request.post(`${api}/auth/login`, {
    data: { email: "integration@example.com", password: "Integration!Pass123" },
  });
  expect(response.ok()).toBeTruthy();
  const token = (await response.json()).access_token;
  const headers = { Authorization: `Bearer ${token}` };
  async function call(path: string, data?: unknown, method = "POST") {
    const result = await request.fetch(`${api}${path}`, {
      method,
      headers,
      data,
    });
    expect(result.ok(), await result.text()).toBeTruthy();
    return result.json();
  }
  const tag = `WORKSPACE-${Date.now()}-${sequence++}`;
  const customer = values.customer
    ? { id: 1, name: "Browser Customer" }
    : await call("/customers", {
        name: "Northwind Studio",
        company_name: "Northwind Studio",
        email: `${tag.toLowerCase()}@example.com`,
        city: "Bengaluru",
        country: "IN",
      });
  const plan = await call("/plans", {
    name: "Workspace monthly",
    code: tag,
    price: "1200.00",
    billing_period: "monthly",
    start_date: "2020-01-01",
    pausable: values.pausable ?? true,
    closable: values.closable ?? false,
    renewable: true,
    min_quantity: 5,
  });
  const tax = await call("/taxes", {
    name: "Workspace GST",
    tax_type: "percent",
    rate: "18",
  });
  const product = await call("/products", {
    name: "Workspace CRM",
    product_type: "service",
    sales_price: "1200.00",
    tax_ids: [tax.id],
  });
  const attribute = await call("/attributes", {
    name: tag,
    values: [{ value: "Odoo", extra_price: "560.00" }],
  });
  const variant = await call(`/products/${product.id}/variants`, {
    sku: tag,
    attribute_value_ids: [attribute.values[0].id],
    name: "Odoo edition",
  });
  await call("/discounts", {
    name: tag,
    discount_type: "percent",
    value: "10.00",
    scope: "product",
    min_quantity: 5,
    product_ids: [product.id],
    start_date: "2020-01-01",
  });
  const template = await call("/quotation-templates", {
    name: "Workspace quotation template",
    plan_id: plan.id,
    validity_days: 30,
    lines: [{ product_id: product.id, variant_id: variant.id, quantity: 5 }],
  });
  let sub = await call("/subscriptions/from-template", {
    template_id: template.id,
    customer_id: customer.id,
    payment_term_id: 1,
    start_date: day(),
    expiry_date: future(),
    currency: "INR",
  });
  await call(
    `/subscriptions/${sub.id}`,
    {
      notes: "Five CRM seats with the agreed Odoo edition.",
      lines: [
        {
          product_id: product.id,
          variant_id: variant.id,
          quantity: 5,
          unit_price: "1760.00",
          description: "Negotiated Odoo contract",
          tax_ids: [tax.id],
        },
      ],
    },
    "PATCH",
  );
  if (values.state === "active")
    for (const state of ["confirmed", "active"])
      sub = await call(`/subscriptions/${sub.id}/state`, { state });
  return { sub, call, tax, product, variant };
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
async function confirm(page: Page, name: string) {
  await page
    .getByRole("article")
    .getByRole("button", { name, exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name, exact: true });
  await dialog.getByRole("button", { name, exact: true }).click();
  await expect(dialog).toHaveCount(0);
}
test("full quotation workspace shows named context, exact prices, edit preservation, invoices and activity", async ({
  page,
  request,
}, testInfo) => {
  const { sub, call, tax } = await seed(request);
  await signIn(page);
  await page.goto(`/subscriptions/${sub.id}`);
  const workspace = page.getByRole("article", {
    name: "Quotation and subscription details",
  });
  await expect(
    workspace.getByRole("heading", { name: sub.number, exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByText("Northwind Studio", { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByText("Workspace monthly", { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByText("Odoo edition", { exact: true }),
  ).toBeVisible();
  await expect(workspace.getByText(/Quotation valid through/)).toBeVisible();
  await expect(
    workspace.getByText("INR 9345.60", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    workspace.getByText("Workspace GST", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: sub.number, exact: true }),
  ).toBeVisible();
  await workspace
    .getByRole("button", { name: "Edit quotation", exact: true })
    .click();
  const edit = page.getByRole("dialog", {
    name: "Edit quotation",
    exact: true,
  });
  await edit.getByRole("button", { name: "Save", exact: true }).click();
  await expect(edit).toHaveCount(0);
  const persisted = await call(`/subscriptions/${sub.id}`, undefined, "GET");
  expect(persisted.lines[0].description).toBe("Negotiated Odoo contract");
  expect(persisted.lines[0].taxes[0].id).toBe(tax.id);
  await confirm(page, "Confirm quotation");
  await confirm(page, "Activate subscription");
  await expect(
    workspace.getByRole("button", { name: "Close subscription", exact: true }),
  ).toBeDisabled();
  await workspace
    .getByRole("button", { name: "Invoice next period", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Generate draft invoice" })
    .getByRole("button", { name: "Generate draft invoice", exact: true })
    .click();
  await expect(workspace.getByRole("status")).toContainText(
    "Draft invoice generated",
  );
  await workspace.getByRole("tab", { name: /Invoices/ }).click();
  const invoice = workspace
    .getByRole("tabpanel", { name: /Invoices/ })
    .getByRole("link", { name: /INV\// });
  await expect(invoice).toHaveCount(1);
  await invoice.click();
  await expect(page).toHaveURL(/\/invoices\/\d+$/);
  await expect(page.getByRole("dialog", { name: /INV\// })).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: sub.number, exact: true }),
  ).toBeVisible();
  await workspace.getByRole("tab", { name: "Activity", exact: true }).click();
  await expect(
    workspace.getByText("Quotation → Confirmed", { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByText("Integration Admin", { exact: true }).first(),
  ).toBeVisible();
  await workspace.getByRole("tab", { name: "Overview", exact: true }).click();
  await page.screenshot({
    path: testInfo.outputPath("subscription-workspace.png"),
    fullPage: true,
  });
  await workspace
    .getByRole("button", { name: "Back to subscriptions", exact: true })
    .click();
  await expect(page).toHaveURL(/\/subscriptions$/);
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: sub.number, exact: true }),
  ).toBeVisible();
});
test("pause, resume, renewal and closure use confirmed actions and preserve history", async ({
  page,
  request,
}) => {
  const { sub, call } = await seed(request, {
    state: "active",
    closable: true,
  });
  await signIn(page);
  await page.goto(`/subscriptions/${sub.id}`);
  await confirm(page, "Pause subscription");
  await expect(page.getByText("Billing paused", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Invoice next period", exact: true }),
  ).toHaveCount(0);
  await confirm(page, "Resume subscription");
  await page
    .getByRole("button", { name: "Renew subscription", exact: true })
    .click();
  const renewal = page.getByRole("dialog", {
    name: "Renew subscription",
    exact: true,
  });
  const newDate = new Date();
  newDate.setFullYear(newDate.getFullYear() + 2);
  const newExpiry = newDate.toLocaleDateString("en-CA");
  await renewal.getByLabel("New expiry date", { exact: true }).fill(newExpiry);
  await renewal
    .getByRole("button", { name: "Renew subscription", exact: true })
    .click();
  await expect(renewal).toHaveCount(0);
  expect(
    (await call(`/subscriptions/${sub.id}`, undefined, "GET")).expiry_date,
  ).toBe(newExpiry);
  await page
    .getByRole("article")
    .getByRole("button", { name: "Close subscription", exact: true })
    .click();
  const close = page.getByRole("dialog", {
    name: "Close subscription",
    exact: true,
  });
  await close
    .getByLabel("Reason for closing", { exact: true })
    .fill("Contract completed by agreement");
  await close
    .getByRole("button", { name: "Close subscription", exact: true })
    .click();
  await expect(close).toHaveCount(0);
  await expect(
    page.getByText("This subscription is closed.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Renew subscription", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("tab", { name: "Activity", exact: true }).click();
  await expect(
    page
      .getByRole("tabpanel", { name: "Activity" })
      .getByText("Contract completed by agreement", { exact: true }),
  ).toBeVisible();
});
test("expired quotation is visibly blocked and can return to draft", async ({
  page,
  request,
}) => {
  const { sub } = await seed(request);
  await page.route(`**/api/subscriptions/${sub.id}`, async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch(),
      body = await response.json();
    if (body.state === "quotation") body.quotation_valid_until = "2020-01-01";
    await route.fulfill({ response, json: body });
  });
  await signIn(page);
  await page.goto(`/subscriptions/${sub.id}`);
  await expect(
    page.getByText("Quotation expired", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Confirm quotation", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Return to draft", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Create quotation", exact: true }),
  ).toBeVisible();
});
test("customer workspace uses only scoped reads and contract policies", async ({
  page,
  request,
}) => {
  const { sub, call } = await seed(request, {
    state: "active",
    customer: true,
    pausable: false,
    closable: false,
  });
  const invoice = await call(`/subscriptions/${sub.id}/invoices`);
  const forbiddenReads: string[] = [];
  page.on("request", (req) => {
    if (/\/api\/(plans|customers|products|users)(\/|\?)/.test(req.url()))
      forbiddenReads.push(req.url());
  });
  await signIn(page, true);
  await page.goto(`/portal/subscriptions/${sub.id}`);
  await expect(
    page.getByRole("heading", { name: sub.number, exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Pause subscription", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Close subscription", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Renew subscription", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Invoice next period", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("tab", { name: /Invoices/ }).click();
  const link = page.getByRole("link", { name: invoice.number });
  await expect(link).toHaveAttribute("href", `/portal/invoices/${invoice.id}`);
  expect(forbiddenReads).toEqual([]);
});
