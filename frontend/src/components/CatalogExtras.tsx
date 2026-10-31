import { useState } from "react"
import { api, text, title, type Row } from "../lib/api"
import {
  Button,
  Card,
  clean,
  Dialog,
  ErrorMessage,
  Form,
  Table,
  useLoad,
} from "./ui"
export function Attributes() {
  const [revision, setRevision] = useState(0),
    [form, setForm] = useState<"attribute" | Row | null>(null),
    [editing, setEditing] = useState<Row | null>(null)
  const result = useLoad<Row[]>("/attributes", revision)
  const refresh = () => {
    setRevision((r) => r + 1)
    setForm(null)
    setEditing(null)
  }
  return (
    <div className="space-y-5">
      <div className="flex justify-between">
        <h1 className="text-3xl font-bold text-navy-900">Product attributes</h1>
        <Button onClick={() => setForm("attribute")}>Add attribute</Button>
      </div>
      <ErrorMessage error={result.error} />
      {result.loading ? (
        <p>Loading…</p>
      ) : (
        result.data?.map((attribute) => (
          <Card key={attribute.id}>
            <div className="mb-3 flex justify-between">
              <h2 className="font-bold">{text(attribute, "name")}</h2>
              <Button secondary onClick={() => setForm(attribute)}>
                Add value
              </Button>
            </div>
            <Table
              rows={(attribute.values || []) as Row[]}
              columns={[
                { key: "value", label: "Value" },
                { key: "extra_price", label: "Extra price" },
              ]}
              select={setEditing}
            />
          </Card>
        ))
      )}
      {result.data?.length === 0 && <Card>No attributes yet.</Card>}
      {form && (
        <Dialog
          title={
            form === "attribute"
              ? "Add attribute"
              : `Add value to ${text(form, "name")}`
          }
          close={() => setForm(null)}
        >
          <Form
            fields={
              form === "attribute"
                ? [{ key: "name", label: "Attribute name", required: true }]
                : [
                    { key: "value", label: "Value", required: true },
                    {
                      key: "extra_price",
                      label: "Extra price",
                      type: "number",
                      min: "0",
                      step: "0.01",
                      value: "0.00",
                      required: true,
                    },
                  ]
            }
            submit={async (values) => {
              await api(
                form === "attribute"
                  ? "/attributes"
                  : `/attributes/${form.id}/values`,
                "POST",
                values,
              )
              refresh()
            }}
            cancel={() => setForm(null)}
          />
        </Dialog>
      )}
      {editing && (
        <Dialog title="Edit attribute value" close={() => setEditing(null)}>
          <Form
            initial={editing}
            fields={[
              { key: "value", label: "Value", required: true },
              {
                key: "extra_price",
                label: "Extra price",
                type: "number",
                min: "0",
                step: "0.01",
                required: true,
              },
            ]}
            submit={async (values) => {
              await api(`/attribute-values/${editing.id}`, "PATCH", values)
              refresh()
            }}
            cancel={() => setEditing(null)}
          />
        </Dialog>
      )}
    </div>
  )
}
export function Variants({
  product,
  canWrite,
  changed,
}: {
  product: Row
  canWrite: boolean
  changed: () => void
}) {
  const [edit, setEdit] = useState<Row | null | undefined>(undefined)
  const attributes = useLoad<Row[]>(edit === null ? "/attributes" : null)
  const values = (attributes.data || []).flatMap((a) =>
    ((a.values || []) as Row[]).map((v) => ({
      value: String(v.id),
      label: `${text(a, "name")}: ${text(v, "value")} (+${text(v, "extra_price")})`,
    })),
  )
  return (
    <div className="mt-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold">Variants</h3>
        {canWrite && (
          <Button secondary onClick={() => setEdit(null)}>
            Add variant
          </Button>
        )}
      </div>
      <Table
        rows={(product.variants || []) as Row[]}
        columns={["name", "sku", "unit_price", "active"].map((key) => ({
          key,
          label: title(key),
        }))}
        select={canWrite ? setEdit : undefined}
      />
      {edit !== undefined && (
        <Dialog
          title={edit ? "Edit variant" : "Add variant"}
          close={() => setEdit(undefined)}
        >
          <ErrorMessage error={attributes.error} />
          {attributes.loading ? (
            <p>Loading attributes…</p>
          ) : (
            <Form
              initial={edit || {}}
              fields={[
                { key: "sku", label: "SKU", required: true },
                { key: "name", label: "Variant name", required: !!edit },
                ...(edit
                  ? [{ key: "active", label: "Active", type: "checkbox" }]
                  : [
                      {
                        key: "attribute_value_ids",
                        label: "Attribute values (one per attribute)",
                        multiple: true,
                        options: values,
                        required: true,
                      },
                    ]),
              ]}
              submit={async (form) => {
                await api(
                  edit
                    ? `/variants/${edit.id}`
                    : `/products/${product.id}/variants`,
                  edit ? "PATCH" : "POST",
                  clean(form, [], ["attribute_value_ids"]),
                )
                setEdit(undefined)
                changed()
              }}
              cancel={() => setEdit(undefined)}
            />
          )}
        </Dialog>
      )}
    </div>
  )
}
