import { useEffect, useState, type ComponentType } from "react"
import {
  LayoutDashboard,
  Users,
  Package,
  ClipboardList,
  CalendarDays,
  FileCheck2,
  ReceiptText,
  CreditCard,
  Tag,
  TrendingUp,
  Settings,
  Landmark,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
  RefreshCw,
} from "lucide-react"
import { api, hasSession, logout, type User } from "./lib/api"
import { navigate } from "./lib/navigation"
import Auth from "./components/Auth"
import { Attributes } from "./components/CatalogExtras"
import { Button, Card, ErrorMessage } from "./components/ui"
import { ResourcePage } from "./components/Resources"
import Subscriptions from "./components/Subscriptions"
import Invoices from "./components/Invoices"
import { Billing, Payments, Profile, Reports } from "./components/Reports"
type PageName = "Overview" | "Customers" | "Products" | "Plans" | "Subscriptions" | "Quotations" | "Invoices" | "Payments" | "Discounts" | "Reports" | "Billing" | "Settings" | "Profile"
type Icon = ComponentType<{ className?: string }>
const navigation: { name: PageName; icon: Icon }[] = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Customers", icon: Users },
  { name: "Products", icon: Package },
  { name: "Plans", icon: ClipboardList },
  { name: "Subscriptions", icon: CalendarDays },
  { name: "Quotations", icon: FileCheck2 },
  { name: "Invoices", icon: ReceiptText },
  { name: "Payments", icon: CreditCard },
  { name: "Discounts", icon: Tag },
  { name: "Reports", icon: TrendingUp },
  { name: "Billing", icon: RefreshCw },
  { name: "Settings", icon: Settings },
]
function pageFromLocation(user: User): PageName {
  const segment = location.pathname.replace(/^\/portal/, "").split("/").filter(Boolean)[0] || ""
  if (user.role === "customer") {
    return segment === "subscriptions" ? "Subscriptions" : segment === "invoices" ? "Invoices" : "Profile"
  }
  return navigation.find(item => item.name.toLowerCase() === segment)?.name || "Overview"
}
export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(
      hasSession() && !new URLSearchParams(location.search).has("token"),
    ),
    [error, setError] = useState(""),
    [page, setPage] = useState<PageName>("Overview"),
    [collapsed, setCollapsed] = useState(false),
    [mobile, setMobile] = useState(false)
  useEffect(() => {
    let current = true
    const expired = () => {
      setUser(null)
      setLoading(false)
    }
    window.addEventListener("session-expired", expired)
    if (hasSession() && !new URLSearchParams(location.search).has("token"))
      api<User>("/auth/me")
        .then((u) => {
          if (current) {
            setUser(u)
            setPage(pageFromLocation(u))
          }
        })
        .catch((e) => {
          if (current) setError(e.message)
        })
        .finally(() => {
          if (current) setLoading(false)
        })
    return () => {
      current = false
      window.removeEventListener("session-expired", expired)
    }
  }, [])
  useEffect(() => {
    const back = () => { if (user) setPage(pageFromLocation(user)) }
    window.addEventListener("popstate", back)
    return () => window.removeEventListener("popstate", back)
  }, [user])
  if (loading)
    return (
      <main className="grid min-h-screen place-items-center">
        Restoring your session…
      </main>
    )
  if (!user)
    return (
      <>
        <ErrorMessage error={error} />
        <Auth
          signedIn={(u) => {
            setUser(u)
            setError("")
            setPage(pageFromLocation(u))
          }}
        />
      </>
    )
  const customer = user.role === "customer",
    items = customer
      ? [
          { name: "Profile" as PageName, icon: Users },
          { name: "Subscriptions" as PageName, icon: CalendarDays },
          { name: "Invoices" as PageName, icon: ReceiptText },
        ]
      : navigation
  let content
  if (page === "Subscriptions") content = <Subscriptions user={user} />
  else if (page === "Invoices") content = <Invoices user={user} />
  else if (customer) content = <Profile user={user} />
  else if (page === "Overview" || page === "Reports")
    content = <Reports overview={page === "Overview"} />
  else if (page === "Payments") content = <Payments />
  else if (page === "Billing") content = <Billing />
  else if (page === "Settings") content = <SettingsPage user={user} />
  else if (
    ["Customers", "Products", "Plans", "Quotations", "Discounts"].includes(page)
  )
    content = (
      <ResourcePage
        key={page}
        name={
          page as "Customers" | "Products" | "Plans" | "Quotations" | "Discounts"
        }
        user={user}
      />
    )
  return (
    <div className="min-h-screen bg-canvas text-slate-700">
      {mobile && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
          onClick={() => setMobile(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-200 bg-white transition-all ${
          collapsed ? "w-20" : "w-64"
        } ${mobile ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="flex h-16 items-center gap-3 border-b px-5">
          <Landmark className="shrink-0 text-teal-700" />
          {!collapsed && (
            <span className="text-xl font-bold text-navy-900">Brightloop</span>
          )}
        </div>
        <nav
          aria-label="Main navigation"
          className="flex-1 space-y-1 overflow-auto p-3"
        >
          {items.map(({ name, icon: Icon }) => (
            <button
              key={name}
              title={name}
              aria-label={name === "Quotations" ? "Quotation templates" : name}
              aria-current={page === name ? "page" : undefined}
              onClick={() => {
                setPage(name)
                setMobile(false)
                navigate(name === "Overview" ? "/" : name === "Profile" ? "/portal" : `${customer ? "/portal" : ""}/${name.toLowerCase()}`)
              }}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-semibold ${
                page === name ? "bg-teal-50 text-teal-800" : "hover:bg-slate-50"
              }`}
            >
              <Icon className="size-5 shrink-0" />
              {!collapsed && (name === "Quotations" ? "Quotation templates" : name)}
            </button>
          ))}
        </nav>
        <button
          aria-label="Toggle sidebar"
          className="hidden border-t p-5 lg:block"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
        </button>
      </aside>
      <div className={collapsed ? "lg:pl-20" : "lg:pl-64"}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-white/95 px-5 backdrop-blur">
          <button
            aria-label="Open menu"
            className="lg:hidden"
            onClick={() => setMobile(!mobile)}
          >
            <Menu />
          </button>
          <span className="text-sm text-slate-500">
            {customer ? "Customer portal" : "Subscription workspace"}
          </span>
          <div className="flex items-center gap-4">
            <div className="text-right text-sm">
              <div className="font-semibold">{user.name}</div>
              <div className="text-xs capitalize text-slate-500">
                {user.role}
              </div>
            </div>
            <button
              aria-label="Sign out"
              title="Sign out"
              onClick={() => {
                setUser(null)
                void logout().catch(() => {})
              }}
            >
              <LogOut className="size-5" />
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8">
          {content}
        </main>
      </div>
    </div>
  )
}
function SettingsPage({ user }: { user: User }) {
  const [tab, setTab] =
    useState<"Taxes" | "Payment terms" | "Team" | "Attributes">("Taxes")
  return user.role !== "admin" ? (
    <Card>
      <h1 className="text-xl font-bold">Your account</h1>
      <p className="mt-3">
        {user.name} · {user.email}
      </p>
      <p className="mt-2 text-sm text-slate-500">
        Workspace settings are managed by an administrator.
      </p>
    </Card>
  ) : (
    <div className="space-y-5">
      <div className="flex gap-2">
        {(["Taxes", "Payment terms", "Attributes", "Team"] as const).map(
          (name) => (
            <Button
              key={name}
              secondary={tab !== name}
              onClick={() => setTab(name)}
            >
              {name}
            </Button>
          ),
        )}
      </div>
      {tab === "Attributes" ? (
        <Attributes />
      ) : (
        <ResourcePage key={tab} name={tab} user={user} />
      )}
    </div>
  )
}
