import { useEffect, useState } from "react"
import { Variants } from "./CatalogExtras"
import {
  api,
  options,
  text,
  today,
  type Page,
  type Row,
  type User,
} from "../lib/api"
import {
  Badge,
  Button,
  Card,
  clean,
  Details,
  Dialog,
  ErrorMessage,
  Form,
  references,
  Table,
  useLoad,
  choices,
  type Field,
  type Values,
} from "./ui"
type ResourceName = "Customers" | "Products" | "Plans" | "Discounts" | "Quotations" | "Taxes" | "Payment terms" | "Team"
type Config = {
  path: string
  fields: Field[]
  columns: string[]
  numbers?: string[]
  arrays?: string[]
  admin?: boolean
  unpaged?: boolean
  search?: boolean
  editable?: boolean
}
const field = (
  key: string,
  label: string,
  type = "text",
  value?: unknown,
  required = true,
): Field => ({ key, label, type, value, required })
const flag = (key: string, label: string, value = false): Field =>
  field(key, label, "checkbox", value, false)
const select = (
  key: string,
  label: string,
  values: string[],
  value?: string,
): Field => ({ key, label, options: choices(values), value, required: true })
const amount = (key: string, label: string, value = "0"): Field => ({
  ...field(key, label, "number", value),
  min: "0",
  step: "0.01",
})
function configuration(name: ResourceName): Config {
  switch (name) {
    case "Customers":
      return {
        path: "/customers",
        search: true,
        editable: true,
        columns: ["name", "email", "company_name", "phone"],
        fields: [
          field("name", "Name"),
          field("email", "Email", "email"),
          field("company_name", "Company", "text", undefined, false),
          field("phone", "Phone", "text", undefined, false),
          field("address_line1", "Address", "text", undefined, false),
          field("city", "City", "text", undefined, false),
          field("state", "State", "text", undefined, false),
          field("postal_code", "Postal code", "text", undefined, false),
          field("country", "Country code", "text", undefined, false),
          field("tax_id", "Tax ID", "text", undefined, false),
        ],
      }
    case "Products":
      return {
        path: "/products",
        admin: true,
        search: true,
        editable: true,
        arrays: ["tax_ids"],
        columns: ["name", "product_type", "sales_price", "active"],
        fields: [
          field("name", "Name"),
          select(
            "product_type",
            "Product type",
            ["service", "goods", "addon"],
            "service",
          ),
          amount("sales_price", "Sales price"),
          amount("cost_price", "Cost price"),
          field("notes", "Notes", "textarea", undefined, false),
          flag("is_recurring", "Recurring", true),
          {
            key: "tax_ids",
            label: "Taxes",
            multiple: true,
            options: [],
            value: [],
          },
        ],
      }
    case "Plans":
      return {
        path: "/plans",
        admin: true,
        editable: true,
        numbers: ["billing_interval", "min_quantity", "trial_days"],
        columns: [
          "name",
          "code",
          "billing_period",
          "billing_interval",
          "price",
          "active",
        ],
        fields: [
          field("name", "Name"),
          field("code", "Code"),
          amount("price", "Reference price"),
          select(
            "billing_period",
            "Billing period",
            ["daily", "weekly", "monthly", "yearly"],
            "monthly",
          ),
          field("billing_interval", "Every N periods", "number", "1"),
          field("min_quantity", "Minimum quantity", "number", "1"),
          field("start_date", "Available from", "date", today()),
          field("end_date", "Available until", "date", undefined, false),
          field("trial_days", "Trial days", "number", "0"),
          flag("auto_close", "Close at expiry"),
          flag("closable", "Allow early closure", true),
          flag("pausable", "Allow pause"),
          flag("renewable", "Allow renewal", true),
        ],
      }
    case "Discounts":
      return {
        path: "/discounts",
        admin: true,
        editable: true,
        numbers: ["min_quantity", "usage_limit"],
        arrays: ["product_ids"],
        columns: [
          "name",
          "discount_type",
          "value",
          "scope",
          "used_count",
          "active",
        ],
        fields: [
          field("name", "Name"),
          field("code", "Optional code", "text", undefined, false),
          select("discount_type", "Type", ["percent", "fixed"], "percent"),
          amount("value", "Discount value", "10"),
          select(
            "scope",
            "Applies to",
            ["subscription", "product"],
            "subscription",
          ),
          amount("min_purchase_amount", "Minimum purchase"),
          field("min_quantity", "Minimum quantity", "number", "0"),
          field("start_date", "Starts", "date", today()),
          field("end_date", "Ends", "date", undefined, false),
          field(
            "usage_limit",
            "Maximum invoice uses",
            "number",
            undefined,
            false,
          ),
          {
            key: "product_ids",
            label: "Products (required for product scope)",
            multiple: true,
            options: [],
            value: [],
          },
        ],
      }
    case "Taxes":
      return {
        path: "/taxes",
        admin: true,
        editable: true,
        unpaged: true,
        columns: ["name", "tax_type", "rate", "is_inclusive", "active"],
        fields: [
          field("name", "Name"),
          select("tax_type", "Type", ["percent", "fixed"], "percent"),
          { ...amount("rate", "Rate"), step: "0.001" },
          flag("is_inclusive", "Price includes this tax"),
        ],
      }
    case "Payment terms":
      return {
        path: "/payment-terms",
        admin: true,
        unpaged: true,
        numbers: ["due_days"],
        columns: ["name", "due_days"],
        fields: [
          field("name", "Name"),
          field("due_days", "Days until due", "number", "0"),
        ],
      }
    case "Team":
      return {
        path: "/users",
        admin: true,
        editable: true,
        columns: ["name", "email", "role", "is_active"],
        fields: [
          field("name", "Name"),
          field("email", "Email", "email"),
          field("password", "Temporary password", "password"),
        ],
      }
    case "Quotations":
      return {
        path: "/quotation-templates",
        editable: true,
        numbers: ["plan_id", "validity_days"],
        columns: ["name", "plan_id", "validity_days", "active"],
        fields: [
          field("name", "Name"),
          { key: "plan_id", label: "Plan", required: true, options: [] },
          field("validity_days", "Valid for days", "number", "30"),
          field("notes", "Notes", "textarea", undefined, false),
        ],
      }
  }
}
type Line = {
  product_id: string
  variant_id: string
  quantity: string
  unit_price: string
  description?: string
  tax_ids?: number[]
}
export function LinesEditor({
  products,
  lines,
  setLines,
}: {
  products: Row[]
  lines: Line[]
  setLines: (lines: Line[]) => void
}) {
  return (
    <div className="mt-5 space-y-3">
      <h3 className="font-semibold">Product lines</h3>
      {lines.map((line, index) => {
        const product = products.find((p) => p.id === Number(line.product_id)),
          variants = (product?.variants || []) as Row[]
        const change = (key: keyof Line, value: string) =>
          setLines(
            lines.map((item, i) =>
              i === index
                ? {
                    ...item,
                    [key]: value,
                    ...(key === "product_id" ? { variant_id: "" } : {}),
                  }
                : item,
            ),
          )
        return (
          <div
            key={index}
            className="grid gap-2 rounded-lg border p-3 sm:grid-cols-2"
          >
            <label className="text-sm">
              Product
              <select
                required
                className="mt-1 w-full rounded border p-2"
                value={line.product_id}
                onChange={(e) => change("product_id", e.target.value)}
              >
                <option value="">Select product…</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {text(p, "name")}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Variant
              <select
                className="mt-1 w-full rounded border p-2"
                value={line.variant_id}
                onChange={(e) => change("variant_id", e.target.value)}
              >
                <option value="">Standard product</option>
                {variants.map((v) => (
                  <option key={v.id} value={v.id}>
                    {text(v, "name")}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Quantity
              <input
                aria-label={`Line ${index + 1} quantity`}
                required
                type="number"
                min="1"
                step="1"
                className="mt-1 w-full rounded border p-2"
                value={line.quantity}
                onChange={(e) => change("quantity", e.target.value)}
              />
            </label>
            <label className="text-sm">
              Unit price (blank uses catalog price)
              <input
                type="number"
                min="0"
                step="0.01"
                className="mt-1 w-full rounded border p-2"
                value={line.unit_price}
                onChange={(e) => change("unit_price", e.target.value)}
              />
            </label>
            {lines.length > 1 && (
              <Button
                secondary
                onClick={() => setLines(lines.filter((_, i) => i !== index))}
              >
                Remove line
              </Button>
            )}
          </div>
        )
      })}
      <Button secondary onClick={() => setLines([...lines, emptyLine()])}>
        Add line
      </Button>
      <p className="text-xs text-slate-500">
        Taxes and discounts are calculated by BrightLoop when the invoice is
        generated.
      </p>
    </div>
  )
}
export const emptyLine = (): Line => ({
  product_id: "",
  variant_id: "",
  quantity: "1",
  unit_price: "",
})
export function serializeLines(lines: Line[]) {
  return lines.map((l) => ({
    product_id: Number(l.product_id),
    ...(l.variant_id ? { variant_id: Number(l.variant_id) } : {}),
    quantity: Number(l.quantity),
    ...(l.description !== undefined ? {description: l.description} : {}),
    ...(l.tax_ids !== undefined ? {tax_ids: l.tax_ids} : {}),
    ...(l.unit_price !== "" ? { unit_price: l.unit_price } : {}),
  }))
}
export function ResourcePage({
  name,
  user,
}: {
  name: ResourceName
  user: User
}) {
  const config = configuration(name),
    [revision, setRevision] = useState(0),
    [page, setPage] = useState(1),
    [query, setQuery] = useState(""),
    [selected, setSelected] = useState<Row | null>(null),
    [edit, setEdit] = useState<Row | null | undefined>(undefined)
  const [related, setRelated] = useState<Record<string, Row[]>>({}),
    [relatedError, setRelatedError] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("")
  const url =
    config.path +
    (config.unpaged
      ? ""
      : `?page=${page}&size=20${
          config.search ? `&q=${encodeURIComponent(query)}` : ""
        }`)
  const result = useLoad<Page | Row[]>(url, revision),
    rows = Array.isArray(result.data) ? result.data : result.data?.items || [],
    total = Array.isArray(result.data)
      ? result.data.length
      : result.data?.total || 0
  const canWrite = !config.admin || user.role === "admin"
  const reload = () => {
    setSelected(null)
    setEdit(undefined)
    setRevision((r) => r + 1)
  }
  useEffect(() => {
    if (edit === undefined) return
    let current = true
    setRelatedError("")
    Promise.all([
      name === "Products" ? api<Row[]>("/taxes") : Promise.resolve([]),
      ["Discounts", "Quotations"].includes(name)
        ? options("/products")
        : Promise.resolve([]),
      name === "Quotations" ? options("/plans") : Promise.resolve([]),
    ])
      .then(([taxes, products, plans]) => {
        if (current) setRelated({ taxes, products, plans })
      })
      .catch((e) => {
        if (current) setRelatedError(e.message)
      })
    return () => {
      current = false
    }
  }, [edit, name])
  let fields = config.fields.map((f) =>
    f.key === "tax_ids"
      ? { ...f, options: references(related.taxes || []) }
      : f.key === "product_ids"
        ? { ...f, options: references(related.products || []) }
        : f.key === "plan_id"
          ? { ...f, options: references(related.plans || []) }
          : f,
  )
  if (edit) {
    if (name === "Team")
      fields = [field("name", "Name"), flag("is_active", "Active")]
    if (name === "Plans") fields = fields.filter((f) => f.key !== "code")
    if (name === "Discounts")
      fields = fields.filter((f) => !["discount_type", "scope"].includes(f.key))
    if (name === "Taxes") fields = fields.filter((f) => f.key !== "tax_type")
    if (
      ["Products", "Plans", "Discounts", "Taxes", "Quotations"].includes(name)
    )
      fields = [...fields, flag("active", "Active")]
  }
  const initial: Values = edit
    ? {
        ...edit,
        tax_ids: ((edit.taxes || []) as Row[]).map((t) => String(t.id)),
        product_ids: ((edit.product_ids || []) as number[]).map(String),
      }
    : {}
  async function action(path: string, method: string, body?: unknown) {
    setBusy(true)
    setError("")
    try {
      await api(path, method, body)
      reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div>
            <h1 className="text-3xl font-bold text-navy-900">{name === "Quotations" ? "Quotation templates" : name}</h1>
            {name === "Products" && <p className="mt-2 text-sm text-slate-500">Active recurring products with type Add-on are available for customers to manage on their own subscriptions.</p>}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {name === "Quotations"
              ? "Reusable quotation templates. Create a subscription from a template in Subscriptions."
              : "Live records from your BrightLoop workspace."}
          </p>
        </div>
        {canWrite && (
          <Button onClick={() => setEdit(null)}>
            Add{" "}
            {
              {
                Customers: "customer",
                Products: "product",
                Plans: "plan",
                Discounts: "discount",
                Quotations: "quotation template",
                Taxes: "tax",
                "Payment terms": "payment term",
                Team: "staff member",
              }[name]
            }
          </Button>
        )}
      </div>
      {name === "Plans" && (
        <p className="text-sm text-slate-500">
          Plans define billing schedules and policies. Subscription product
          lines determine invoice amounts.
        </p>
      )}
      <ErrorMessage error={error} />
      <Card>
        {config.search && (
          <input
            aria-label={`Search ${name}`}
            className="mb-4 w-full max-w-md rounded-lg border p-2"
            placeholder={`Search ${name.toLowerCase()}…`}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(1)
            }}
          />
        )}
        <ErrorMessage error={result.error} />
        {result.loading ? (
          <p role="status">Loading…</p>
        ) : (
          <Table
            rows={rows}
            columns={config.columns.map((key) => ({
              key,
              label: key.replaceAll("_", " "),
              render: ["active", "is_active", "is_inclusive"].includes(key)
                ? (row: Row) => String(!!row[key])
                : key === "role"
                  ? (row: Row) => <Badge value={text(row, key)} />
                  : undefined,
            }))}
            select={setSelected}
          />
        )}
        <div className="mt-4 flex items-center justify-between text-sm">
          <span>{total} records</span>
          {!config.unpaged && (
            <div className="flex items-center gap-3">
              <Button
                secondary
                disabled={page === 1 || result.loading}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span>Page {page}</span>
              <Button
                secondary
                disabled={page * 20 >= total || result.loading}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      </Card>
      {selected && (
        <Dialog
          title={String(selected.name || selected.email || name)}
          close={() => setSelected(null)}
        >
          <Details row={selected} />
          {Array.isArray(selected.lines) && (
            <div className="mt-5">
              <h3 className="font-semibold">Template lines</h3>
              <Table
                rows={selected.lines as Row[]}
                columns={[
                  "product_id",
                  "variant_id",
                  "quantity",
                  "unit_price",
                ].map((key) => ({ key, label: key.replaceAll("_", " ") }))}
              />
            </div>
          )}
          {name === "Products" && (
            <Variants product={selected} canWrite={canWrite} changed={reload} />
          )}
          <div className="mt-6 flex gap-2">
            {canWrite && config.editable && (
              <Button
                onClick={() => {
                  setEdit(selected)
                  setSelected(null)
                }}
              >
                Edit
              </Button>
            )}
            {user.role === "admin" &&
              ["Customers", "Products", "Discounts"].includes(name) && (
                <Button
                  secondary
                  disabled={busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Delete this record? Records in use cannot be deleted.",
                      )
                    )
                      void action(`${config.path}/${selected.id}`, "DELETE")
                  }}
                >
                  Delete
                </Button>
              )}
          </div>
        </Dialog>
      )}
      {edit !== undefined && (
        <Dialog
          title={`${edit ? "Edit" : "Add"} ${name}`}
          close={() => setEdit(undefined)}
        >
          <ErrorMessage error={relatedError} />
          <ResourceForm
            key={edit?.id || "new"}
            fields={fields}
            initial={initial}
            products={related.products || []}
            template={name === "Quotations"}
            submit={async (values, lines) => {
              const body = clean(values, config.numbers, config.arrays)
              if (name === "Quotations") body.lines = serializeLines(lines)
              await api(
                `${config.path}${
                  name === "Team" && !edit
                    ? "/staff"
                    : edit
                      ? `/${edit.id}`
                      : ""
                }`,
                edit ? "PATCH" : "POST",
                body,
              )
              reload()
            }}
            cancel={() => setEdit(undefined)}
          />
        </Dialog>
      )}
    </div>
  )
}
function ResourceForm({
  fields,
  initial,
  products,
  template,
  submit,
  cancel,
}: {
  fields: Field[]
  initial: Values
  products: Row[]
  template: boolean
  submit: (values: Values, lines: Line[]) => Promise<void>
  cancel: () => void
}) {
  const [lines, setLines] = useState<Line[]>(() =>
    Array.isArray(initial.lines)
      ? (initial.lines as Row[]).map((l) => ({
          product_id: String(l.product_id),
          variant_id: l.variant_id ? String(l.variant_id) : "",
          quantity: String(l.quantity),
          unit_price: String(l.unit_price),
        }))
      : [emptyLine()],
  )
  return (
    <Form
      fields={fields}
      initial={initial}
      submit={(values) => submit(values, lines)}
      cancel={cancel}
    >
      {template && (
        <LinesEditor products={products} lines={lines} setLines={setLines} />
      )}
    </Form>
  )
}
