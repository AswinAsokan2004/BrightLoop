import { useState, type FormEvent } from "react"
import { api, login, type User } from "../lib/api"
import { Button, ErrorMessage, FieldInput } from "./ui"
export default function Auth({ signedIn }: { signedIn: (user: User) => void }) {
  const resetToken = new URLSearchParams(location.search).get("token")
  const [mode, setMode] = useState(resetToken ? "reset" : "login")
  const [values, setValues] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("")
  const changeMode = (next: string) => {
    setMode(next)
    setError("")
    setMessage("")
    setValues({})
  }
  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError("")
    setMessage("")
    try {
      if (["signup", "reset"].includes(mode) && new TextEncoder().encode(values.password || "").length > 72) throw new Error("Password must be at most 72 UTF-8 bytes. Use fewer characters.")
      if (mode === "login") signedIn(await login(values.email, values.password))
      else if (mode === "signup") {
        await api("/auth/signup", "POST", values, false)
        signedIn(await login(values.email, values.password))
      } else if (mode === "forgot") {
        const result = await api<{ message: string }>(
          "/auth/forgot-password",
          "POST",
          { email: values.email },
          false,
        )
        setMessage(result.message)
      } else {
        await api(
          "/auth/reset-password",
          "POST",
          { token: resetToken, new_password: values.password },
          false,
        )
        history.replaceState(null, "", "/")
        changeMode("login")
        setMessage("Password updated. Sign in with your new password.")
      }
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="grid min-h-screen place-items-center bg-canvas p-6">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-8 text-2xl font-bold text-navy-900">
          Brightloop<span className="text-teal-700">.</span>
        </div>
        <h1 className="text-xl font-bold">
          {mode === "login"
            ? "Welcome back"
            : mode === "signup"
              ? "Create your customer account"
              : mode === "forgot"
                ? "Reset your password"
                : "Choose a new password"}
        </h1>
        <p className="mb-6 mt-2 text-sm text-slate-500">
          Manage your subscriptions and billing in one place.
        </p>
        <form onSubmit={submit} className="space-y-4">
          {mode === "signup" && (
            <FieldInput
              field={{ key: "name", label: "Name", required: true }}
              value={values.name}
              change={(v) => setValues({ ...values, name: String(v) })}
            />
          )}
          {mode !== "reset" && (
            <FieldInput
              field={{
                key: "email",
                label: "Email",
                type: "email",
                required: true,
              }}
              value={values.email}
              change={(v) => setValues({ ...values, email: String(v) })}
            />
          )}
          {mode !== "forgot" && (
            <FieldInput
              field={{
                key: "password",
                label: "Password",
                type: "password",
                required: true,
                help:
                  mode === "login"
                    ? undefined
                    : "More than 8 characters, uppercase, lowercase and a special character. Maximum 72 UTF-8 bytes.",
              }}
              value={values.password}
              change={(v) => setValues({ ...values, password: String(v) })}
            />
          )}
          <ErrorMessage error={error} />
          {message && (
            <p role="status" className="text-sm text-teal-800">
              {message}
            </p>
          )}
          <Button type="submit" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : mode === "signup"
                  ? "Create account"
                  : mode === "forgot"
                    ? "Send reset link"
                    : "Update password"}
          </Button>
        </form>
        <div className="mt-6 flex flex-wrap gap-4 text-sm text-teal-700">
          {mode !== "login" && (
            <button onClick={() => changeMode("login")}>Back to sign in</button>
          )}
          {mode === "login" && (
            <>
              <button onClick={() => changeMode("signup")}>
                Create customer account
              </button>
              <button onClick={() => changeMode("forgot")}>
                Forgot password?
              </button>
            </>
          )}
        </div>
      </section>
    </main>
  )
}
