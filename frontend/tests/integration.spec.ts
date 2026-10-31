import { test, expect, type Page } from "@playwright/test"
// Run against an isolated backend with the documented test accounts (see README).
async function signIn(
  page: Page,
  email = "integration@example.com",
  password = "Integration!Pass123",
) {
  await page.goto("/")
  await page.getByLabel("Email", { exact: true }).fill(email)
  await page.getByLabel("Password", { exact: true }).fill(password)
  await page.getByRole("button", { name: "Sign in", exact: true }).click()
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible()
}
async function navigate(page: Page, name: string) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click()
}
test("admin creates a contract, invoices, collects payment and reloads persisted data", async ({
  page,
}) => {
  const failures: string[] = []
  page.on("pageerror", (error) => failures.push(error.message))
  await signIn(page)
  await expect(
    page.getByRole("heading", { name: "Finance overview", exact: true }),
  ).toBeVisible()
  await navigate(page, "Customers")
  await page.getByRole("button", { name: "Add customer" }).click()
  let dialog = page.getByRole("dialog")
  await dialog
    .getByLabel("Name", { exact: true })
    .fill("UI Integration Customer")
  await dialog
    .getByLabel("Email", { exact: true })
    .fill("ui-customer@example.com")
  await dialog.getByRole("button", { name: "Save", exact: true }).click()
  await expect(dialog).toHaveCount(0)
  await expect(
    page.getByRole("cell", { name: "UI Integration Customer", exact: true }),
  ).toBeVisible()
  await page.reload()
  await navigate(page, "Customers")
  await expect(
    page.getByRole("cell", { name: "UI Integration Customer", exact: true }),
  ).toBeVisible()
  await navigate(page, "Subscriptions")
  await page.getByRole("button", { name: "New subscription" }).click()
  dialog = page.getByRole("dialog")
  await dialog
    .getByLabel("Customer", { exact: true })
    .selectOption({ label: "UI Integration Customer" })
  await dialog
    .getByLabel("Plan", { exact: true })
    .selectOption({ label: "Monthly" })
  await dialog
    .getByLabel("Payment terms", { exact: true })
    .selectOption({ label: "Immediate" })
  await dialog
    .getByRole("combobox", { name: "Product", exact: true })
    .selectOption({ label: "Test CRM" })
  await dialog.getByRole("button", { name: "Save", exact: true }).click()
  await expect(dialog).toHaveCount(0)
  const workspace=page.getByRole("article",{name:"Quotation and subscription details"})
  await expect(workspace).toBeVisible()
  await workspace.getByRole("button",{name:"Create quotation",exact:true}).click()
  for (const name of ["Confirm quotation","Activate subscription"]) {
    await workspace.getByRole("button",{name,exact:true}).click()
    const confirmation=page.getByRole("dialog",{name,exact:true})
    await confirmation.getByRole("button",{name,exact:true}).click()
    await expect(confirmation).toHaveCount(0)
  }
  const invoiceRequest=page.waitForResponse(r=>r.url().includes("/invoices")&&r.request().method()==="POST")
  await workspace.getByRole("button",{name:"Invoice next period",exact:true}).click()
  await page.getByRole("dialog",{name:"Generate draft invoice"}).getByRole("button",{name:"Generate draft invoice",exact:true}).click()
  const invoiceResponse = await invoiceRequest
  expect(invoiceResponse.status()).toBe(201)
  const createdInvoice = await invoiceResponse.json()
  await navigate(page,"Invoices")
  await page.getByRole("row").filter({ hasText: createdInvoice.number }).click()
  dialog = page.getByRole("article", { name: "Invoice details" })
  await dialog.getByRole("button", { name: "Confirm invoice", exact: true }).click()
  await page.getByRole("dialog", { name: "Confirm invoice" }).getByRole("button", { name: "Confirm invoice", exact: true }).click()
  await dialog
    .getByRole("button", { name: "Record payment", exact: true })
    .click()
  const payment = page.getByRole("dialog", {
    name: "Record payment",
    exact: true,
  })
  await payment.getByRole("button", { name: "Save", exact: true }).click()
  await expect(payment).toHaveCount(0)
  await expect(dialog.getByText("Paid", { exact: true })).toBeVisible()
  const popupPromise = page.waitForEvent("popup")
  await dialog.getByRole("button", { name: "Print / Save as PDF" }).click()
  const popup = await popupPromise
  await expect(
    popup.getByRole("heading", { name: /Invoice INV/ }),
  ).toBeVisible()
  await popup.close()
  await dialog.getByRole("button", { name: "Back to invoices" }).click()
  await navigate(page, "Payments")
  await expect(
    page.getByRole("cell", { name: "100.00", exact: true }),
  ).toBeVisible()
  await navigate(page, "Reports")
  await expect(
    page.getByRole("heading", { name: "Revenue reports" }),
  ).toBeVisible()
  await expect(page.getByRole("alert")).toHaveCount(0)
  await navigate(page, "Billing")
  await page.getByRole("button", { name: "Run billing", exact: true }).click()
  const billingConfirmation = page.getByRole("dialog", { name: "Run billing", exact: true })
  await billingConfirmation.getByRole("button", { name: "Generate draft invoices", exact: true }).click()
  await expect(page.getByRole("article", { name: "Billing run details" })).toBeVisible()
  await navigate(page, "Settings")
  await page.getByRole("button", { name: "Team", exact: true }).click()
  await expect(
    page.getByRole("cell", { name: "integration@example.com" }),
  ).toBeVisible()
  expect(failures).toEqual([])
})
test("customer sees only the portal; staff has no catalog write controls", async ({
  page,
}) => {
  await signIn(page, "customer@example.com", "Customer!Pass123")
  await expect(
    page.getByRole("heading", { name: "Welcome, Customer Account" }),
  ).toBeVisible()
  await expect(
    page
      .getByRole("navigation")
      .getByRole("button", { name: "Customers", exact: true }),
  ).toHaveCount(0)
  await navigate(page, "Subscriptions")
  await expect(
    page.getByRole("heading", { name: "Your subscriptions" }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "New subscription" }),
  ).toHaveCount(0)
  await navigate(page, "Invoices")
  await expect(page.getByRole("alert")).toHaveCount(0)
  await page.getByRole("button", { name: "Sign out" }).click()
  await signIn(page, "staff@example.com", "Staff!Pass123")
  await navigate(page, "Products")
  await expect(
    page.getByRole("cell", { name: "Test CRM", exact: true }),
  ).toBeVisible()
  await expect(page.getByRole("button", { name: "Add product" })).toHaveCount(0)
})
test("server validation is shown in the form and a failed save retains input", async ({
  page,
}) => {
  await signIn(page)
  await navigate(page, "Plans")
  await page.getByRole("button", { name: "Add plan" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("Name", { exact: true }).fill("Invalid dates")
  await dialog.getByLabel("Code", { exact: true }).fill("INVALID-DATES")
  await dialog.getByLabel("Available from", { exact: true }).fill("2026-12-01")
  await dialog.getByLabel("Available until", { exact: true }).fill("2026-01-01")
  await dialog.getByRole("button", { name: "Save", exact: true }).click()
  await expect(dialog.getByRole("alert")).toContainText(
    "end_date must be on or after start_date",
  )
  await expect(dialog.getByLabel("Name", { exact: true })).toHaveValue(
    "Invalid dates",
  )
})

test("invalid login shows an error and allows retry with the correct password", async ({ page }) => {
  await page.goto("/")
  await page.getByLabel("Email", { exact: true }).fill("integration@example.com")
  await page.getByLabel("Password", { exact: true }).fill("Wrong!Password123")
  const rejected = page.waitForResponse(response =>
    response.url().endsWith("/api/auth/login") && response.request().method() === "POST")
  await page.getByRole("button", { name: "Sign in", exact: true }).click()
  expect((await rejected).status()).toBe(401)
  await expect(page.getByText("Invalid email or password", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0)
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue("integration@example.com")
  await page.getByLabel("Password", { exact: true }).fill("Integration!Pass123")
  await page.getByRole("button", { name: "Sign in", exact: true }).click()
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible()
  await expect(page.getByText("Invalid email or password", { exact: true })).toHaveCount(0)
})
