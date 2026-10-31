import { useEffect, useState, type ReactNode, type FormEvent } from "react"
import { X } from "lucide-react"
import { api, title, type Row } from "../lib/api"
export function Button({
  children,
  onClick,
  secondary = false,
  disabled = false,
  type = "button",
}: {
  children: ReactNode
  onClick?: () => void
  secondary?: boolean
  disabled?: boolean
  type?: "button" | "submit"
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
        secondary
          ? "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          : "bg-teal-700 text-white hover:bg-teal-800"
      }`}
    >
      {children}
    </button>
  )
}
export function Card({ children }: { children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      {children}
    </section>
  )
}
export function ErrorMessage({ error }: { error: string }) {
  return error ? (
    <div
      role="alert"
      className="my-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"
    >
      {error}
    </div>
  ) : null
}
export function Badge({ value }: { value: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-1 text-xs font-semibold ${
        ["active", "paid", "completed", "confirmed"].includes(value)
          ? "bg-teal-50 text-teal-800"
          : ["cancelled", "closed", "failed"].includes(value)
            ? "bg-rose-50 text-rose-700"
            : "bg-slate-100 text-slate-600"
      }`}
    >
      {title(value)}
    </span>
  )
}
export function useLoad<T>(url: string | null, revision = 0) {
  const [state, setState] = useState<{
    data: T | null
    loading: boolean
    error: string
  }>({ data: null, loading: true, error: "" })
  useEffect(() => {
    if (!url) {
      setState({ data: null, loading: false, error: "" })
      return
    }
    let current = true
    setState({ data: null, loading: true, error: "" })
    api<T>(url)
      .then((data) => {
        if (current) setState({ data, loading: false, error: "" })
      })
      .catch((error) => {
        if (current)
          setState({ data: null, loading: false, error: error.message })
      })
    return () => {
      current = false
    }
  }, [url, revision])
  return state
}
export type Field = {
  key: string
  label: string
  type?: string
  required?: boolean
  value?: unknown
  options?: { value: string; label: string }[]
  help?: string
  min?: string
  step?: string
  multiple?: boolean
}
export type Values = Record<string, unknown>
const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
export function FieldInput({
  field,
  value,
  change,
}: {
  field: Field
  value: unknown
  change: (value: unknown) => void
}) {
  return (
    <label
      className={`block text-sm ${
        field.type === "textarea" ? "sm:col-span-2" : ""
      }`}
    >
      <span className="mb-1 block font-medium">
        {field.label}
        {field.required ? " *" : ""}
      </span>
      {field.type === "checkbox" ? (
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => change(e.target.checked)}
        />
      ) : field.options ? (
        <select
          aria-label={field.label}
          className={inputClass}
          required={field.required}
          multiple={field.multiple}
          value={field.multiple ? value as string[] || [] : String(value ?? "")}
          onChange={(e) =>
            change(
              field.multiple
                ? Array.from(e.target.selectedOptions, (o) => o.value)
                : e.target.value,
            )
          }
        >
          {!field.multiple && <option value="">Select…</option>}
          {field.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : field.type === "textarea" ? (
        <textarea
          className={inputClass}
          value={String(value ?? "")}
          onChange={(e) => change(e.target.value)}
        />
      ) : (
        <input
          className={inputClass}
          aria-label={field.label}
          type={field.type || "text"}
          required={field.required}
          min={field.min}
          step={field.step}
          value={String(value ?? "")}
          onChange={(e) => change(e.target.value)}
        />
      )}
      {field.help && (
        <span className="mt-1 block text-xs text-slate-500">{field.help}</span>
      )}
    </label>
  )
}
export function Dialog({
  title: heading,
  children,
  close,
}: {
  title: string
  children: ReactNode
  close: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"
      onClick={close}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label={heading}
        className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold text-navy-900">{heading}</h2>
          <button aria-label="Close dialog" onClick={close}>
            <X />
          </button>
        </div>
        {children}
      </section>
    </div>
  )
}
export function Form({
  fields,
  initial = {},
  submit,
  cancel,
  children,
  label = "Save",
}: {
  fields: Field[]
  initial?: Values
  submit: (values: Values) => Promise<void>
  cancel: () => void
  children?: ReactNode
  label?: string
}) {
  const [values, setValues] = useState<Values>(() =>
    Object.fromEntries(
      fields.map((f) => [
        f.key,
        initial[f.key] ??
          f.value ??
          (f.type === "checkbox" ? false : f.multiple ? [] : ""),
      ]),
    ),
  )
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("")
  async function save(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError("")
    try {
      await submit(values)
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <form onSubmit={save}>
      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map((field) => (
          <FieldInput
            key={field.key}
            field={field}
            value={values[field.key]}
            change={(value) => setValues({ ...values, [field.key]: value })}
          />
        ))}
      </div>
      {children}
      <ErrorMessage error={error} />
      <div className="mt-6 flex justify-end gap-2">
        <Button secondary onClick={cancel} disabled={busy}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : label}
        </Button>
      </div>
    </form>
  )
}
export function clean(
  values: Values,
  numbers: string[] = [],
  arrays: string[] = [],
): Values {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => value !== "")
      .map(([key, value]) => [
        key,
        arrays.includes(key)
          ? (value as string[]).map(Number)
          : numbers.includes(key)
            ? Number(value)
            : value,
      ]),
  )
}
export const choices = (values: string[]) =>
  values.map((value) => ({ value, label: title(value) }))
export const references = (rows: Row[]) =>
  rows.map((row) => ({
    value: String(row.id),
    label: String(row.name || row.number || row.id),
  }))
export function Details({ row }: { row: Row }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {Object.entries(row)
        .filter(([, value]) => value !== null && typeof value !== "object")
        .map(([key, value]) => (
          <div key={key}>
            <dt className="text-xs text-slate-500">{title(key)}</dt>
            <dd className="break-words text-sm">
              {typeof value === "boolean"
                ? value
                  ? "Yes"
                  : "No"
                : String(value)}
            </dd>
          </div>
        ))}
    </dl>
  )
}
export function Table({
  rows,
  columns,
  select,
}: {
  rows: Row[]
  columns: { key: string; label: string; render?: (row: Row) => ReactNode }[]
  select?: (row: Row) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs uppercase text-slate-500">
            {columns.map((c) => (
              <th key={c.key} className="whitespace-nowrap p-3">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className={`border-b last:border-0 ${
                select ? "cursor-pointer hover:bg-teal-50" : ""
              }`}
              onClick={() => select?.(row)}
            >
              {columns.map((c) => (
                <td key={c.key} className="p-3">
                  {c.render ? c.render(row) : String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && (
        <p className="p-8 text-center text-slate-500">No records found.</p>
      )}
    </div>
  )
}
