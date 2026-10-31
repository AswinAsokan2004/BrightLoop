import { useMemo, useState, type ComponentType, type ReactNode } from 'react'
import {
  Bell,
  Boxes,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  ClipboardList,
  CreditCard,
  FileCheck2,
  FileText,
  Gauge,
  LayoutDashboard,
  Menu,
  MoreHorizontal,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ReceiptText,
  Search,
  Settings,
  SlidersHorizontal,
  Landmark,
  RefreshCw,
  Tag,
  TrendingUp,
  Users,
  WalletCards,
  X,
} from 'lucide-react'

type Page =
  | 'Overview'
  | 'Customers'
  | 'Products'
  | 'Plans'
  | 'Subscriptions'
  | 'Quotations'
  | 'Invoices'
  | 'Payments'
  | 'Discounts'
  | 'Reports'
  | 'Settings'
  | 'Customer Portal'

type Icon = ComponentType<{ className?: string; strokeWidth?: number }>

const navigation: { label: Page; icon: Icon }[] = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Customers', icon: Users },
  { label: 'Products', icon: Package },
  { label: 'Plans', icon: ClipboardList },
  { label: 'Subscriptions', icon: CalendarDays },
  { label: 'Quotations', icon: FileCheck2 },
  { label: 'Invoices', icon: ReceiptText },
  { label: 'Payments', icon: CreditCard },
  { label: 'Discounts', icon: Tag },
  { label: 'Reports', icon: TrendingUp },
]

const productsSeed = [
  { id: 1, name: 'Analytics Cloud', description: 'Real-time product analytics suite', type: 'SaaS', prices: 3, revenue: '$32,400', status: 'Active' },
  { id: 2, name: 'Data Connect', description: 'Managed data synchronization', type: 'Add-on', prices: 2, revenue: '$18,240', status: 'Active' },
  { id: 3, name: 'Support Plus', description: 'Priority support and onboarding', type: 'Service', prices: 1, revenue: '$9,850', status: 'Active' },
  { id: 4, name: 'Workspace AI', description: 'AI-powered team assistant', type: 'SaaS', prices: 4, revenue: '$14,120', status: 'Draft' },
]

const subscriptions = [
  { id: 'SUB-1048', customer: 'Luma Labs', plan: 'Scale annual', value: '$14,400', next: 'Dec 12, 2025', status: 'Active' },
  { id: 'SUB-1047', customer: 'Northstar Inc.', plan: 'Growth monthly', value: '$899', next: 'Nov 28, 2025', status: 'Active' },
  { id: 'SUB-1046', customer: 'Acme Studio', plan: 'Starter monthly', value: '$249', next: 'Nov 24, 2025', status: 'Confirmed' },
  { id: 'SUB-1045', customer: 'Sisyphus Corp.', plan: 'Enterprise', value: '$24,000', next: 'Jan 04, 2026', status: 'Quotation' },
  { id: 'SUB-1044', customer: 'Vertex Group', plan: 'Growth monthly', value: '$899', next: '—', status: 'Draft' },
  { id: 'SUB-1043', customer: 'Mercury Labs', plan: 'Scale annual', value: '$12,900', next: '—', status: 'Closed' },
]

const invoices = [
  { id: 'INV-2094', customer: 'Northstar Inc.', date: 'Nov 14, 2025', due: 'Nov 28, 2025', total: '$899.00', status: 'Paid' },
  { id: 'INV-2093', customer: 'Luma Labs', date: 'Nov 12, 2025', due: 'Nov 26, 2025', total: '$1,200.00', status: 'Open' },
  { id: 'INV-2092', customer: 'Vertex Group', date: 'Nov 10, 2025', due: 'Nov 24, 2025', total: '$899.00', status: 'Overdue' },
  { id: 'INV-2091', customer: 'Acme Studio', date: 'Nov 08, 2025', due: 'Nov 22, 2025', total: '$249.00', status: 'Paid' },
  { id: 'INV-2090', customer: 'Mercury Labs', date: 'Nov 05, 2025', due: 'Nov 19, 2025', total: '$1,075.00', status: 'Paid' },
]

const payments = [
  { id: 'PAY-8821', customer: 'Northstar Inc.', invoice: 'INV-2094', method: 'Visa •••• 4242', date: 'Nov 14, 2025', total: '$899.00', status: 'Succeeded' },
  { id: 'PAY-8820', customer: 'Acme Studio', invoice: 'INV-2091', method: 'Mastercard •••• 8291', date: 'Nov 08, 2025', total: '$249.00', status: 'Succeeded' },
  { id: 'PAY-8819', customer: 'Mercury Labs', invoice: 'INV-2090', method: 'ACH transfer', date: 'Nov 07, 2025', total: '$1,075.00', status: 'Succeeded' },
  { id: 'PAY-8818', customer: 'Vertex Group', invoice: 'INV-2092', method: 'Visa •••• 1009', date: 'Nov 05, 2025', total: '$899.00', status: 'Failed' },
]

const customers = [
  { name: 'Luma Labs', contact: 'Maya Chen', email: 'maya@lumalabs.io', subscriptions: 2, value: '$18,400', status: 'Active' },
  { name: 'Northstar Inc.', contact: 'Alex Morgan', email: 'alex@northstar.co', subscriptions: 1, value: '$10,788', status: 'Active' },
  { name: 'Acme Studio', contact: 'Sam Taylor', email: 'sam@acme.studio', subscriptions: 1, value: '$2,988', status: 'Active' },
  { name: 'Vertex Group', contact: 'Jamie Ross', email: 'jamie@vertex.com', subscriptions: 1, value: '$8,091', status: 'At risk' },
]

function Button({ children, variant = 'primary', className = '', onClick, type = 'button' }: { children: ReactNode; variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; className?: string; onClick?: () => void; type?: 'button' | 'submit' }) {
  const variants = {
    primary: 'bg-teal-700 text-white hover:bg-teal-800',
    secondary: 'border border-slate-200 bg-white text-slate-700 hover:bg-canvas',
    ghost: 'text-slate-500 hover:bg-slate-100 hover:text-slate-800',
    danger: 'bg-rose-50 text-rose-700 hover:bg-rose-100',
  }
  return <button type={type} onClick={onClick} className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition ${variants[variant]} ${className}`}>{children}</button>
}

function Input({ value, onChange, placeholder, type = 'text', className = '' }: { value?: string; onChange?: (value: string) => void; placeholder?: string; type?: string; className?: string }) {
  return <input type={type} value={value} onChange={(event) => onChange?.(event.target.value)} placeholder={placeholder} className={`w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy-900 outline-none transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-4 focus:ring-teal-50 ${className}`} />
}

function Select({ children, value, onChange, className = '' }: { children: ReactNode; value?: string; onChange?: (value: string) => void; className?: string }) {
  return <select value={value} onChange={(event) => onChange?.(event.target.value)} className={`rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-teal-600 focus:ring-4 focus:ring-teal-50 ${className}`}>{children}</select>
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-slate-200 bg-white ${className}`}>{children}</div>
}

function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' }) {
  const colors = {
    success: 'bg-teal-50 text-teal-800 ring-teal-700/15',
    warning: 'bg-amber-50 text-amber-800 ring-amber-700/15',
    danger: 'bg-rose-50 text-rose-800 ring-rose-700/15',
    info: 'bg-slate-100 text-navy-900 ring-slate-400/20',
    neutral: 'bg-slate-100 text-slate-600 ring-slate-500/10',
  }
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${colors[tone]}`}>{children}</span>
}

function statusTone(status: string): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (['Active', 'Paid', 'Succeeded', 'Confirmed'].includes(status)) return 'success'
  if (['Open', 'Quotation'].includes(status)) return 'info'
  if (['Overdue', 'Failed', 'At risk'].includes(status)) return 'danger'
  if (status === 'Draft') return 'warning'
  return 'neutral'
}

function SearchField({ value, onChange, placeholder = 'Search…' }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input value={value} onChange={onChange} placeholder={placeholder} className="pl-9" /></div>
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        {eyebrow && <div className="mb-1 text-xs font-bold uppercase tracking-widest text-teal-700">{eyebrow}</div>}
        <div className="text-2xl font-bold tracking-tight text-navy-900 sm:text-3xl">{title}</div>
        <div className="mt-1.5 text-sm text-slate-500">{description}</div>
      </div>
      {action}
    </div>
  )
}

function Modal({ title, children, onClose, footer }: { title: string; children: ReactNode; onClose: () => void; footer: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/30 p-0 backdrop-blur-sm sm:items-center sm:p-6">
      <Card className="w-full max-w-lg rounded-b-none p-6 shadow-lg sm:rounded-xl">
        <div className="mb-6 flex items-center justify-between">
          <div className="text-lg font-bold text-navy-900">{title}</div>
          <Button variant="ghost" className="size-9 p-0" onClick={onClose}><X className="size-4" /></Button>
        </div>
        {children}
        <div className="mt-6 flex justify-end gap-2">{footer}</div>
      </Card>
    </div>
  )
}

function EmptyIllustration({ icon: Icon }: { icon: Icon }) {
  return <div className="grid size-10 place-items-center rounded-lg border border-slate-200 bg-canvas text-navy-900"><Icon className="size-5" strokeWidth={1.8} /></div>
}

function Overview({ goTo }: { goTo: (page: Page) => void }) {
  const stats = [
    { label: 'Active subscriptions', value: '1,248', change: '+8.4%', icon: CalendarDays, positive: true },
    { label: 'Monthly recurring revenue', value: '$84,320', change: '+12.2%', icon: TrendingUp, positive: true },
    { label: 'Total revenue', value: '$284,680', change: '+9.7%', icon: CircleDollarSign, positive: true },
    { label: 'Outstanding payments', value: '$12,450', change: '18 invoices', icon: WalletCards, positive: false },
    { label: 'Overdue invoices', value: '7', change: '$4,280 due', icon: FileText, positive: false },
  ]
  return (
    <div className="space-y-6">
      <PageHeader title="Good morning, Jordan" description="Here’s what’s happening with Brightloop today." action={<Button onClick={() => goTo('Subscriptions')}><Plus className="size-4" />New subscription</Button>} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {stats.map((stat) => <Card key={stat.label} className="p-5">
          <div className="flex items-start justify-between"><div className="text-sm font-medium text-slate-500">{stat.label}</div><stat.icon className="size-4 text-slate-400" /></div>
          <div className="mt-4 text-2xl font-bold tracking-tight text-navy-900">{stat.value}</div>
          <div className={`mt-2 text-xs font-semibold ${stat.positive ? 'text-teal-700' : 'text-slate-500'}`}>{stat.change} <span className="font-normal text-slate-400">{stat.positive ? 'vs last month' : ''}</span></div>
        </Card>)}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <Card className="p-5 sm:p-6">
          <div className="mb-8 flex items-center justify-between">
            <div><div className="font-bold text-navy-900">Revenue overview</div><div className="mt-1 text-sm text-slate-500">Recurring and one-time revenue</div></div>
            <Select><option>Last 6 months</option><option>This year</option></Select>
          </div>
          <div className="relative h-64">
            <div className="absolute inset-0 flex flex-col justify-between text-xs text-slate-400">
              {['$100k', '$75k', '$50k', '$25k', '$0'].map((label) => <div key={label} className="flex items-center gap-3"><span className="w-10">{label}</span><div className="h-px flex-1 bg-slate-100" /></div>)}
            </div>
            <svg className="absolute inset-x-12 bottom-4 h-56 w-[calc(100%-3rem)] overflow-visible" viewBox="0 0 600 210" preserveAspectRatio="none">
              <path d="M0 175 C70 160,80 145,130 150 S210 110,260 120 S340 80,390 96 S470 42,520 62 S570 30,600 38 L600 210 L0 210 Z" fill="#CCFBF1" fillOpacity=".45" />
              <path d="M0 175 C70 160,80 145,130 150 S210 110,260 120 S340 80,390 96 S470 42,520 62 S570 30,600 38" fill="none" stroke="#0F766E" strokeWidth="2.5" strokeLinecap="round" />
              {[['0','175'],['130','150'],['260','120'],['390','96'],['520','62'],['600','38']].map(([cx,cy]) => <circle key={cx} cx={cx} cy={cy} r="3.5" fill="white" stroke="#0F766E" strokeWidth="2" />)}
            </svg>
          </div>
          <div className="mt-2 flex justify-between pl-14 text-xs text-slate-400"><span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Oct</span><span>Nov</span></div>
        </Card>
        <Card className="p-5 sm:p-6">
          <div className="font-bold text-navy-900">Subscription health</div>
          <div className="mt-1 text-sm text-slate-500">Current portfolio breakdown</div>
          <div className="mx-auto my-7 grid size-40 place-items-center rounded-full bg-[conic-gradient(#0F766E_0_72%,#94A3B8_72%_88%,#E2E8F0_88%)]">
            <div className="grid size-28 place-items-center rounded-full bg-white text-center"><div><div className="text-2xl font-bold text-navy-900">1,248</div><div className="text-xs text-slate-400">Total</div></div></div>
          </div>
          <div className="space-y-3">
            {[['Active','899','bg-teal-700'],['Trial','199','bg-teal-500'],['Paused','150','bg-slate-200']].map(([label,value,color]) => <div key={label} className="flex items-center text-sm"><span className={`mr-2 size-2.5 rounded-full ${color}`} /><span className="text-slate-600">{label}</span><span className="ml-auto font-semibold text-navy-900">{value}</span></div>)}
          </div>
        </Card>
      </div>
      <Card>
        <div className="flex items-center justify-between border-b border-slate-200/70 p-5 sm:px-6"><div><div className="font-bold text-navy-900">Recent transactions</div><div className="mt-1 text-sm text-slate-500">Latest customer payments</div></div><Button variant="ghost" onClick={() => goTo('Payments')}>View all <ChevronRight className="size-4" /></Button></div>
        <div className="overflow-x-auto"><PaymentTable rows={payments.slice(0, 4)} compact /></div>
      </Card>
    </div>
  )
}

function ProductsPage() {
  const [products, setProducts] = useState(productsSeed)
  const [query, setQuery] = useState('')
  const [modal, setModal] = useState(false)
  const [name, setName] = useState('')
  const filtered = products.filter((product) => product.name.toLowerCase().includes(query.toLowerCase()))
  const addProduct = () => {
    if (!name.trim()) return
    setProducts([...products, { id: Date.now(), name, description: 'New subscription product', type: 'SaaS', prices: 1, revenue: '$0', status: 'Draft' }])
    setName('')
    setModal(false)
  }
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Catalog" title="Products" description="Build and manage everything you sell." action={<Button onClick={() => setModal(true)}><Plus className="size-4" />Add product</Button>} />
      <div className="grid gap-4 sm:grid-cols-3">
        {[['4','Total products',Package],['10','Price points',Tag],['$74.6k','Product revenue',TrendingUp]].map(([value,label,Icon]) => <Card key={String(label)} className="flex items-center gap-4 p-5"><EmptyIllustration icon={Icon as Icon} /><div><div className="text-xl font-bold text-navy-900">{String(value)}</div><div className="text-sm text-slate-500">{String(label)}</div></div></Card>)}
      </div>
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200/70 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <SearchField value={query} onChange={setQuery} placeholder="Search products…" />
          <Button variant="secondary"><SlidersHorizontal className="size-4" />Filter</Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-canvas/70"><tr className="border-b border-slate-200/70 text-xs font-semibold uppercase tracking-wider text-slate-500"><th className="px-6 py-3.5">Product</th><th className="px-4 py-3.5">Type</th><th className="px-4 py-3.5">Prices</th><th className="px-4 py-3.5">Revenue</th><th className="px-4 py-3.5">Status</th><th className="px-4 py-3.5"></th></tr></thead>
            <tbody>{filtered.map((product) => <tr key={product.id} className="border-b border-slate-200/70 last:border-0 hover:bg-canvas/60">
              <td className="px-6 py-4"><div className="flex items-center gap-3"><EmptyIllustration icon={Boxes} /><div><div className="font-semibold text-navy-900">{product.name}</div><div className="mt-0.5 text-xs text-slate-500">{product.description}</div></div></div></td>
              <td className="px-4 py-4 text-slate-600">{product.type}</td><td className="px-4 py-4 text-slate-600">{product.prices}</td><td className="px-4 py-4 font-semibold text-navy-900">{product.revenue}</td><td className="px-4 py-4"><Badge tone={statusTone(product.status)}>{product.status}</Badge></td>
              <td className="px-4 py-4"><Button variant="ghost" className="size-8 p-0" onClick={() => setProducts(products.filter((item) => item.id !== product.id))}><MoreHorizontal className="size-4" /></Button></td>
            </tr>)}</tbody>
          </table>
        </div>
      </Card>
      {modal && <Modal title="Add a new product" onClose={() => setModal(false)} footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={addProduct}>Create product</Button></>}>
        <div className="space-y-4"><label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Product name</span><Input value={name} onChange={setName} placeholder="e.g. Analytics Cloud" /></label><label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Product type</span><Select className="w-full"><option>SaaS</option><option>Service</option><option>Add-on</option></Select></label><label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Description</span><Input placeholder="Short product description" /></label></div>
      </Modal>}
    </div>
  )
}

function PlansPage() {
  const [period, setPeriod] = useState('Monthly')
  const plans = [
    { name: 'Starter', product: 'Analytics Cloud', monthly: 249, detail: 'For small teams getting started', features: ['5 team members', '50k events / month', 'Email support'] },
    { name: 'Growth', product: 'Analytics Cloud', monthly: 899, detail: 'For growing product teams', features: ['20 team members', '500k events / month', 'Priority support'], featured: true },
    { name: 'Scale', product: 'Analytics Cloud', monthly: 1200, detail: 'Advanced controls and scale', features: ['Unlimited members', '5m events / month', 'Dedicated success manager'] },
  ]
  const multiplier = period === 'Yearly' ? 10 : period === 'Weekly' ? .25 : period === 'Daily' ? .04 : 1
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Pricing" title="Plans" description="Create flexible pricing and renewal schedules." action={<Button><Plus className="size-4" />Create plan</Button>} />
      <div className="flex overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 sm:w-fit">
        {['Daily','Weekly','Monthly','Yearly'].map((item) => <Button key={item} variant="ghost" onClick={() => setPeriod(item)} className={period === item ? 'bg-teal-50 text-teal-800' : ''}>{item}</Button>)}
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        {plans.map((plan) => <Card key={plan.name} className={`relative overflow-hidden p-6 ${plan.featured ? 'border-teal-600' : ''}`}>
          {plan.featured && <div className="absolute right-5 top-5 text-xs font-semibold text-teal-700">Recommended</div>}
          <div className="text-sm font-semibold text-teal-700">{plan.product}</div><div className="mt-2 text-xl font-bold text-navy-900">{plan.name}</div><div className="mt-1 text-sm text-slate-500">{plan.detail}</div>
          <div className="mt-6 flex items-end gap-1"><span className="text-4xl font-bold tracking-tight text-navy-900">${Math.round(plan.monthly * multiplier).toLocaleString()}</span><span className="pb-1 text-sm text-slate-500">/ {period.toLowerCase().replace('ly','')}</span></div>
          <div className="my-6 h-px bg-slate-100" />
          <div className="space-y-3">{plan.features.map((feature) => <div key={feature} className="flex items-center gap-2 text-sm text-slate-600"><Check className="size-4 text-teal-700" />{feature}</div>)}</div>
          <Button variant="secondary" className="mt-7 w-full">Edit plan</Button>
        </Card>)}
      </div>
      <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
        <EmptyIllustration icon={RefreshCw} /><div className="flex-1"><div className="font-semibold text-navy-900">Renewal settings</div><div className="mt-0.5 text-sm text-slate-500">Subscriptions renew automatically. Failed payments retry 3 times over 7 days.</div></div><Button variant="secondary">Configure</Button>
      </Card>
    </div>
  )
}

function SubscriptionsPage() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All')
  const [modal, setModal] = useState(false)
  const rows = subscriptions.filter((row) => (status === 'All' || row.status === status) && `${row.id} ${row.customer}`.toLowerCase().includes(query.toLowerCase()))
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Billing" title="Subscriptions" description="Manage customer contracts, renewals and lifecycle." action={<Button onClick={() => setModal(true)}><Plus className="size-4" />New subscription</Button>} />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200/70 p-4 sm:flex-row sm:justify-between">
          <SearchField value={query} onChange={setQuery} placeholder="Search ID or customer…" />
          <Select value={status} onChange={setStatus}><option>All</option><option>Draft</option><option>Quotation</option><option>Confirmed</option><option>Active</option><option>Closed</option></Select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-canvas/70"><tr className="border-b border-slate-200/70 text-xs uppercase tracking-wider text-slate-500"><th className="px-6 py-3.5">Subscription</th><th className="px-4 py-3.5">Customer</th><th className="px-4 py-3.5">Plan</th><th className="px-4 py-3.5">Value</th><th className="px-4 py-3.5">Next bill</th><th className="px-4 py-3.5">Status</th><th /></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.id} className="border-b border-slate-200/70 last:border-0 hover:bg-canvas/60"><td className="px-6 py-4 font-semibold text-teal-700">{row.id}</td><td className="px-4 py-4 font-semibold text-navy-900">{row.customer}</td><td className="px-4 py-4 text-slate-600">{row.plan}</td><td className="px-4 py-4 font-semibold text-navy-900">{row.value}</td><td className="px-4 py-4 text-slate-600">{row.next}</td><td className="px-4 py-4"><Badge tone={statusTone(row.status)}>{row.status}</Badge></td><td className="px-4"><Button variant="ghost" className="size-8 p-0"><MoreHorizontal className="size-4" /></Button></td></tr>)}</tbody></table>
        </div>
      </Card>
      {modal && <Modal title="Create subscription" onClose={() => setModal(false)} footer={<><Button variant="secondary" onClick={() => setModal(false)}>Save draft</Button><Button onClick={() => setModal(false)}>Create subscription</Button></>}>
        <div className="grid gap-4 sm:grid-cols-2"><label className="sm:col-span-2"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Customer</span><Select className="w-full"><option>Select a customer</option>{customers.map((item) => <option key={item.name}>{item.name}</option>)}</Select></label><label><span className="mb-1.5 block text-sm font-semibold text-slate-700">Plan</span><Select className="w-full"><option>Starter monthly</option><option>Growth monthly</option><option>Scale annual</option></Select></label><label><span className="mb-1.5 block text-sm font-semibold text-slate-700">Start date</span><Input type="date" /></label><label className="sm:col-span-2"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Product line</span><Input placeholder="Add product or add-on" /></label></div>
      </Modal>}
    </div>
  )
}

function InvoicesPage() {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<(typeof invoices)[number] | null>(null)
  const rows = invoices.filter((item) => `${item.id} ${item.customer}`.toLowerCase().includes(query.toLowerCase()))
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Billing" title="Invoices" description="Track balances, payment status and customer billing." action={<Button><Plus className="size-4" />Create invoice</Button>} />
      <div className="grid gap-4 sm:grid-cols-3">{[['$48,230','Paid this month','text-teal-700'],['$12,450','Outstanding','text-teal-700'],['$4,280','Overdue','text-rose-600']].map(([value,label,color]) => <Card key={label} className="p-5"><div className={`text-2xl font-bold ${color}`}>{value}</div><div className="mt-1 text-sm text-slate-500">{label}</div></Card>)}</div>
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200/70 p-4 sm:flex-row sm:justify-between"><SearchField value={query} onChange={setQuery} placeholder="Search invoices…" /><Button variant="secondary"><SlidersHorizontal className="size-4" />Filter</Button></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-canvas/70"><tr className="border-b border-slate-200/70 text-xs uppercase tracking-wider text-slate-500"><th className="px-6 py-3.5">Invoice</th><th className="px-4 py-3.5">Customer</th><th className="px-4 py-3.5">Issued</th><th className="px-4 py-3.5">Due</th><th className="px-4 py-3.5">Total</th><th className="px-4 py-3.5">Status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} onClick={() => setSelected(row)} className="cursor-pointer border-b border-slate-200/70 last:border-0 hover:bg-canvas"><td className="px-6 py-4 font-semibold text-teal-700">{row.id}</td><td className="px-4 py-4 font-semibold text-navy-900">{row.customer}</td><td className="px-4 py-4 text-slate-600">{row.date}</td><td className="px-4 py-4 text-slate-600">{row.due}</td><td className="px-4 py-4 font-semibold">{row.total}</td><td className="px-4 py-4"><Badge tone={statusTone(row.status)}>{row.status}</Badge></td></tr>)}</tbody></table></div>
      </Card>
      {selected && <Modal title={`Invoice ${selected.id}`} onClose={() => setSelected(null)} footer={<><Button variant="secondary" onClick={() => setSelected(null)}>Close</Button><Button>Download PDF</Button></>}>
        <div className="rounded-xl bg-canvas p-4"><div className="flex justify-between text-sm"><span className="text-slate-500">Billed to</span><span className="font-semibold">{selected.customer}</span></div><div className="my-4 h-px bg-slate-200" /><div className="flex justify-between text-sm"><span className="text-slate-600">Analytics Cloud — Growth</span><span>$832.41</span></div><div className="mt-3 flex justify-between text-sm"><span className="text-slate-500">Tax (8%)</span><span>$66.59</span></div><div className="mt-3 flex justify-between border-t border-slate-200 pt-3 font-bold"><span>Total</span><span>{selected.total}</span></div></div>
      </Modal>}
    </div>
  )
}

function PaymentTable({ rows, compact = false }: { rows: typeof payments; compact?: boolean }) {
  return <table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-canvas/70"><tr className="border-b border-slate-200/70 text-xs uppercase tracking-wider text-slate-500">{!compact && <th className="px-6 py-3.5">Payment</th>}<th className="px-6 py-3.5">Customer</th><th className="px-4 py-3.5">Invoice</th><th className="px-4 py-3.5">Method</th><th className="px-4 py-3.5">Date</th><th className="px-4 py-3.5">Amount</th><th className="px-4 py-3.5">Status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} className="border-b border-slate-200/70 last:border-0 hover:bg-canvas/60">{!compact && <td className="px-6 py-4 font-semibold text-teal-700">{row.id}</td>}<td className="px-6 py-4 font-semibold text-navy-900">{row.customer}</td><td className="px-4 py-4 text-teal-700">{row.invoice}</td><td className="px-4 py-4 text-slate-600">{row.method}</td><td className="px-4 py-4 text-slate-600">{row.date}</td><td className="px-4 py-4 font-semibold">{row.total}</td><td className="px-4 py-4"><Badge tone={statusTone(row.status)}>{row.status}</Badge></td></tr>)}</tbody></table>
}

function PaymentsPage() {
  const [query, setQuery] = useState('')
  const rows = payments.filter((item) => `${item.id} ${item.customer} ${item.invoice}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="space-y-6"><PageHeader eyebrow="Transactions" title="Payments" description="Monitor payment activity and connected methods." action={<Button variant="secondary">Export payments</Button>} /><div className="grid gap-4 sm:grid-cols-3"><Card className="p-5"><div className="text-sm text-slate-500">Net volume</div><div className="mt-2 text-2xl font-bold text-navy-900">$52,890</div><div className="mt-1 text-xs font-semibold text-teal-700">+11.8% this month</div></Card><Card className="p-5"><div className="text-sm text-slate-500">Success rate</div><div className="mt-2 text-2xl font-bold text-navy-900">98.4%</div><div className="mt-1 text-xs text-slate-400">1.6% failed</div></Card><Card className="p-5"><div className="text-sm text-slate-500">Average payment</div><div className="mt-2 text-2xl font-bold text-navy-900">$672</div><div className="mt-1 text-xs text-slate-400">Across all methods</div></Card></div><Card><div className="border-b border-slate-200/70 p-4 sm:px-5"><SearchField value={query} onChange={setQuery} placeholder="Search payments…" /></div><div className="overflow-x-auto"><PaymentTable rows={rows} /></div></Card></div>
}

function GenericPage({ page }: { page: Page }) {
  const config: Partial<Record<Page, { description: string; icon: Icon }>> = {
    Customers: { description: 'Manage customer profiles, contacts and lifetime value.', icon: Users },
    Quotations: { description: 'Create proposals from templates and convert accepted quotes.', icon: FileCheck2 },
    Discounts: { description: 'Create fixed and percentage promotions for your customers.', icon: Tag },
    Reports: { description: 'Understand revenue, retention and subscription performance.', icon: TrendingUp },
    Settings: { description: 'Configure your workspace, billing rules and team access.', icon: Settings },
  }
  if (page === 'Customers') return <CustomersPage />
  const detail = config[page] ?? config.Reports!
  return <div className="space-y-6"><PageHeader title={page} description={detail.description} action={<Button><Plus className="size-4" />Create new</Button>} /><Card className="p-6"><div className="mb-6 flex items-center gap-3"><EmptyIllustration icon={detail.icon} /><div><div className="font-bold text-navy-900">{page} workspace</div><div className="text-sm text-slate-500">All records are synced with your subscription workflow.</div></div></div><div className="grid gap-3 sm:grid-cols-3">{['Active','Scheduled','Archived'].map((label,index) => <div key={label} className="rounded-xl border border-slate-200/70 bg-canvas p-4"><div className="text-sm text-slate-500">{label}</div><div className="mt-2 text-2xl font-bold text-navy-900">{[24,8,3][index]}</div></div>)}</div></Card></div>
}

function CustomersPage() {
  const [query, setQuery] = useState('')
  const [modal, setModal] = useState(false)
  const rows = customers.filter((item) => `${item.name} ${item.email}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="space-y-6"><PageHeader eyebrow="Relationships" title="Customers" description="Profiles, subscription activity and customer value." action={<Button onClick={() => setModal(true)}><Plus className="size-4" />Add customer</Button>} /><Card><div className="border-b border-slate-200/70 p-4 sm:px-5"><SearchField value={query} onChange={setQuery} placeholder="Search customers…" /></div><div className="overflow-x-auto"><table className="w-full min-w-[740px] text-left text-sm"><thead className="bg-canvas/70"><tr className="border-b border-slate-200/70 text-xs uppercase tracking-wider text-slate-500"><th className="px-6 py-3.5">Customer</th><th className="px-4 py-3.5">Contact</th><th className="px-4 py-3.5">Subscriptions</th><th className="px-4 py-3.5">Annual value</th><th className="px-4 py-3.5">Status</th><th /></tr></thead><tbody>{rows.map((row) => <tr key={row.name} className="border-b border-slate-200/70 last:border-0"><td className="px-6 py-4"><div className="font-semibold text-navy-900">{row.name}</div><div className="text-xs text-slate-500">{row.email}</div></td><td className="px-4 py-4 text-slate-600">{row.contact}</td><td className="px-4 py-4">{row.subscriptions}</td><td className="px-4 py-4 font-semibold">{row.value}</td><td className="px-4 py-4"><Badge tone={statusTone(row.status)}>{row.status}</Badge></td><td><Button variant="ghost" className="size-8 p-0"><MoreHorizontal className="size-4" /></Button></td></tr>)}</tbody></table></div></Card>{modal && <Modal title="Add customer" onClose={() => setModal(false)} footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={() => setModal(false)}>Add customer</Button></>}><div className="space-y-4"><Input placeholder="Company name" /><Input placeholder="Contact name" /><Input type="email" placeholder="Email address" /></div></Modal>}</div>
}

function CustomerPortal({ onExit }: { onExit: () => void }) {
  return <div className="min-h-screen bg-canvas"><div className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6"><Brand /><Button variant="secondary" onClick={onExit}>Back to admin</Button></div></div><main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6"><PageHeader eyebrow="Customer portal" title="Welcome back, Maya" description="Manage your subscriptions, invoices and payment methods." /><div className="grid gap-4 sm:grid-cols-3"><Card className="p-5"><div className="text-sm text-slate-500">Next payment</div><div className="mt-2 text-2xl font-bold text-navy-900">$1,200.00</div><div className="mt-1 text-xs text-slate-400">Due Dec 12, 2025</div></Card><Card className="p-5"><div className="text-sm text-slate-500">Active subscriptions</div><div className="mt-2 text-2xl font-bold text-navy-900">2</div><div className="mt-1 text-xs text-teal-700">All in good standing</div></Card><Card className="p-5"><div className="text-sm text-slate-500">Payment method</div><div className="mt-2 flex items-center gap-2 font-bold"><CreditCard className="size-5 text-teal-700" />Visa •••• 4242</div><div className="mt-1 text-xs text-slate-400">Expires 08/28</div></Card></div><Card className="p-6"><div className="mb-5 font-bold text-navy-900">Your subscriptions</div><div className="space-y-3">{['Analytics Cloud — Scale','Data Connect — Standard'].map((name,index) => <div key={name} className="flex flex-col gap-3 rounded-xl border border-slate-200/70 p-4 sm:flex-row sm:items-center"><EmptyIllustration icon={Package} /><div className="flex-1"><div className="font-semibold">{name}</div><div className="text-sm text-slate-500">Renews {index ? 'monthly' : 'annually'}</div></div><Badge tone="success">Active</Badge><Button variant="secondary">Manage</Button></div>)}</div></Card><Card><div className="border-b border-slate-200/70 p-5 font-bold">Recent invoices</div><div className="overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><tbody>{invoices.slice(0,3).map((invoice) => <tr key={invoice.id} className="border-b border-slate-200/70 last:border-0"><td className="px-6 py-4 font-semibold text-teal-700">{invoice.id}</td><td className="px-4 py-4 text-slate-500">{invoice.date}</td><td className="px-4 py-4 font-semibold">{invoice.total}</td><td className="px-4 py-4"><Badge tone={statusTone(invoice.status)}>{invoice.status}</Badge></td><td className="px-4 py-4"><Button variant="ghost">Download</Button></td></tr>)}</tbody></table></div></Card></main></div>
}

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return <div className="flex items-center gap-2.5"><div className="grid size-9 place-items-center rounded-lg border border-navy-900 bg-navy-900 text-white"><Landmark className="size-[18px]" strokeWidth={1.8} /></div>{!collapsed && <div className="text-lg font-semibold tracking-tight text-navy-900">Brightloop</div>}</div>
}

export default function App() {
  const [page, setPage] = useState<Page>('Overview')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [globalSearch, setGlobalSearch] = useState('')
  const content = useMemo(() => {
    if (page === 'Overview') return <Overview goTo={setPage} />
    if (page === 'Products') return <ProductsPage />
    if (page === 'Plans') return <PlansPage />
    if (page === 'Subscriptions') return <SubscriptionsPage />
    if (page === 'Invoices') return <InvoicesPage />
    if (page === 'Payments') return <PaymentsPage />
    return <GenericPage page={page} />
  }, [page])
  if (page === 'Customer Portal') return <CustomerPortal onExit={() => setPage('Overview')} />
  const navigate = (next: Page) => { setPage(next); setMobileOpen(false) }
  return (
    <div className="min-h-screen bg-canvas text-slate-800">
      {mobileOpen && <div className="fixed inset-0 z-30 bg-slate-950/30 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-200 bg-white transition-all duration-300 ${collapsed ? 'w-20' : 'w-64'} ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="flex h-16 items-center justify-between border-b border-slate-200/70 px-5"><Brand collapsed={collapsed} />{!collapsed && <Button variant="ghost" className="size-8 p-0 lg:hidden" onClick={() => setMobileOpen(false)}><X className="size-4" /></Button>}</div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {navigation.map(({ label, icon: Icon }) => <Button key={label} variant="ghost" onClick={() => navigate(label)} className={`w-full ${collapsed ? 'px-0' : 'justify-start'} ${page === label ? 'bg-teal-50 text-teal-800' : ''}`}><Icon className="size-[18px] shrink-0" strokeWidth={2} />{!collapsed && label}</Button>)}
        </nav>
        <div className="border-t border-slate-200/70 p-3">
          <Button variant="ghost" onClick={() => navigate('Customer Portal')} className={`mb-1 w-full ${collapsed ? 'px-0' : 'justify-start'}`}><Gauge className="size-[18px]" />{!collapsed && 'Customer portal'}</Button>
          <Button variant="ghost" onClick={() => navigate('Settings')} className={`w-full ${collapsed ? 'px-0' : 'justify-start'} ${page === 'Settings' ? 'bg-teal-50 text-teal-800' : ''}`}><Settings className="size-[18px]" />{!collapsed && 'Settings'}</Button>
          <Button variant="ghost" onClick={() => setCollapsed(!collapsed)} className={`mt-2 hidden w-full border-t border-slate-200/70 pt-3 lg:flex ${collapsed ? 'px-0' : 'justify-start'}`}>{collapsed ? <PanelLeftOpen className="size-[18px]" /> : <PanelLeftClose className="size-[18px]" />}{!collapsed && 'Collapse sidebar'}</Button>
        </div>
      </aside>
      <div className={`transition-all duration-300 ${collapsed ? 'lg:pl-20' : 'lg:pl-64'}`}>
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur-xl sm:px-6">
          <Button variant="ghost" className="size-9 p-0 lg:hidden" onClick={() => setMobileOpen(true)}><Menu className="size-5" /></Button>
          <div className="relative hidden w-full max-w-md sm:block"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input value={globalSearch} onChange={setGlobalSearch} placeholder="Search anything…" className="border-transparent bg-slate-100 pl-9 focus:bg-white" /></div>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" className="relative size-9 p-0"><Bell className="size-[18px]" /><span className="absolute right-2 top-2 size-2 rounded-full border-2 border-white bg-teal-500" /></Button>
            <div className="mx-1 hidden h-6 w-px bg-slate-200 sm:block" />
            <Button variant="ghost" className="gap-2 p-1.5 sm:pr-2"><div className="grid size-8 place-items-center rounded-lg bg-navy-900 text-xs font-bold text-white">JD</div><div className="hidden text-left sm:block"><div className="text-xs font-semibold text-slate-800">Jordan Davis</div><div className="text-[11px] font-normal text-slate-400">Administrator</div></div><ChevronDown className="hidden size-3.5 text-slate-400 sm:block" /></Button>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8">{content}</main>
      </div>
    </div>
  )
}
