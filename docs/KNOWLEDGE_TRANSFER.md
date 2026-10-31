# BrightLoop API: Knowledge Transfer

This document explains **what the backend does, why each API exists, and why the code is split
into tiers the way it is**. Read it before changing anything in `app/`.

Each API is tied back to the requirement in the *Subscription Management System* brief
(Brightloop Software) that made it necessary. If you are about to change an endpoint, find
it here first and check which requirement it serves.

---

## Contents

1. [The problem in one page](#1-the-problem-in-one-page)
2. [Requirements map: brief → module → API](#2-requirements-map-brief--module--api)
3. [The tiers: why routes, services and repositories](#3-the-tiers-why-routes-services-and-repositories)
4. [Cross-cutting rules](#4-cross-cutting-rules)
5. [API reference, with the reason for each endpoint](#5-api-reference-with-the-reason-for-each-endpoint)
6. [Core flows in detail](#6-core-flows-in-detail)
7. [Data model notes](#7-data-model-notes)
8. [Non-functional requirements](#8-non-functional-requirements)
9. [Running, testing and operating](#9-running-testing-and-operating)
10. [Known gaps and next steps](#10-known-gaps-and-next-steps)
11. [Gotchas](#11-gotchas)

---

## 1. The problem in one page

Brightloop Software sells software on subscription. Today it runs on spreadsheets and memory:

| Pain today | What the system does instead | Where in the code |
|---|---|---|
| Subscriptions tracked in a spreadsheet | Subscriptions with a strict lifecycle and history | `services/subscription.py` |
| Renewals remembered by whoever notices | Scheduled billing run, auto-close, explicit renew | `services/billing.py` |
| Invoices typed by hand every month | Invoices generated from subscriptions | `services/billing.py` |
| Payments matched by scrolling bank statements | Payments recorded against invoices, balances tracked | `services/payment.py` |
| Revenue reports built manually each quarter | Live summary and monthly revenue reports | `services/report.py` |

A subscription is **a recurring promise to bill**. The backend has to remember every promise,
turn each one into a correct invoice at the right moment (taxes and discounts applied), match
payments to invoices, and report the resulting revenue.

There are three kinds of user:

| Role | Who | Access |
|---|---|---|
| `admin` | Runs the whole system | Everything. The only role that can create staff, products, plans, taxes and discounts |
| `staff` | Internal team, day-to-day work | Customers, quotations, subscriptions, invoices, payments, billing runs, reports |
| `customer` | Brightloop's clients | Only the portal (`/api/portal/...`), and only their own data |

---

## 2. Requirements map: brief → module → API

Every requirement in the brief, and the APIs that satisfy it.

| # | Requirement (from the brief) | APIs |
|---|---|---|
| R1 | Sign up with email and password | `POST /api/auth/signup` |
| R2 | Each email can belong to only one account | `signup`, `users/staff` (unique email, case-insensitive) |
| R3 | Password: more than 8 characters, uppercase, lowercase, special character | `signup`, `reset-password`, `users/staff` |
| R4 | Forgotten password: reset link to the registered email | `forgot-password`, `reset-password` |
| R5 | Admin controls everything; staff have limited access; customers see only their own data | Role checks on every route; `/api/portal/*` |
| R6 | Only the admin can add staff | `POST /api/users/staff` |
| R7 | Products with name, type, sales price, cost price, notes | `/api/products` |
| R8 | Variants, e.g. the Odoo brand adds 560 to the price | `/api/attributes`, `/api/products/{id}/variants` |
| R9 | Plans: price, billing period (daily/weekly/monthly/yearly), minimum quantity, availability dates | `/api/plans` |
| R10 | Per plan: auto-close at end, closable early, pausable, renewable | `/api/plans` flags, enforced in `/subscriptions/{id}/state` and `/renew` |
| R11 | Quotation templates with a plan, product lines and validity in days | `/api/quotation-templates`, `POST /api/subscriptions/from-template` |
| R12 | Subscription: number, customer, plan, start date, expiry date, payment terms, lines | `/api/subscriptions`, `/api/payment-terms` |
| R13 | Lifecycle Draft → Quotation → Confirmed → Active → Closed, visible to the team | `POST /api/subscriptions/{id}/state`, `state_logs` in responses |
| R14 | Invoices created from subscriptions, not typed by hand | `POST /api/billing/run`, `POST /api/subscriptions/{id}/invoices` |
| R15 | Taxes calculated automatically from admin rules | `/api/taxes`, product tax links, pricing engine |
| R16 | Confirm, cancel, send or print any invoice; Draft → Confirmed → Paid | `/api/invoices/{id}/confirm`, `/cancel`, `/send`, `/print` |
| R17 | Nothing billed twice or skipped | Billing engine (section 6.2) |
| R18 | Only the admin creates discount rules: fixed or percent, minimum purchase or quantity, dates, usage limit | `/api/discounts` |
| R19 | Discounts apply to products or whole subscriptions, appear on the next invoice automatically, stop when expired or used up | Discount engine inside billing |
| R20 | Payments recorded with method, amount, date and note, against an invoice | `POST /api/invoices/{id}/payments` |
| R21 | See which invoices are paid and which are outstanding; chase overdue ones | `GET /api/invoices?outstanding=true` / `?overdue=true`, `GET /api/payments` |
| R22 | One place for active subscriptions, revenue, payments and overdue invoices, with filters and a summary | `/api/reports/summary`, `/api/reports/revenue-by-month` |
| R23 | Customers manage their own subscriptions without emailing anyone | `/api/portal/*` |
| R24 | Every page responds in under two seconds with thousands of subscriptions | Indexes, pagination, SQL aggregates (section 8) |

---

## 3. The tiers: why routes, services and repositories

```
HTTP request
    │
    ▼
┌──────────────┐  app/routes/        "Who is calling, and what did they send?"
│   Route      │  - role check (AdminUser / StaffUser / CustomerUser)
│              │  - request body validated by a Pydantic schema
└──────┬───────┘  - calls ONE service method, shapes the response
       ▼
┌──────────────┐  app/services/      "Is this allowed, and what should happen?"
│   Service    │  - business rules (state machine, plan flags, pricing, billing)
│              │  - owns the transaction: db.commit() / rollback only happen here
└──────┬───────┘  - raises domain errors (BadRequestError, NotFoundError, ...)
       ▼
┌──────────────┐  app/repositories/  "How do I read or write it?"
│  Repository  │  - SQLAlchemy queries, filters, pagination, row locks
│              │  - no business rules, never commits
└──────┬───────┘
       ▼
   PostgreSQL     app/models/ (tables), migrations/ (schema history)
```

### Why split it this way?

| Tier | Requirement it protects | Rule of thumb |
|---|---|---|
| **Routes** | R5 (access control must be impossible to forget) | Every route declares its role in the function signature. If a route has no `AdminUser`/`StaffUser`/`CustomerUser`/`CurrentUser` parameter, it is public; only the auth endpoints and `/health` should be. |
| **Services** | R13, R17, R19 (rules must hold no matter who calls them) | The billing engine is called from an API route **and** a cron script. Because the rules live in the service, both paths behave identically. |
| **Repositories** | R24 (performance) | All SQL is in one place, so query tuning (indexes, `selectinload`, locks) happens without touching business logic. |
| **Schemas** | R3, R7, R18 (input rules) | Validation such as password strength, money precision and `percent ≤ 100` runs before any code touches the database. |
| **Models** | Data integrity | Mirror the Alembic migrations exactly. Constraints (unique email, unique billing period) are the last line of defence. |

### What goes where: quick decisions

| You need to... | Put it in |
|---|---|
| Add a new endpoint | `routes/<module>.py`, keep it to a few lines |
| Check a role | The route signature (`AdminUser`, `StaffUser`, ...) |
| Add a business rule ("plans with X can't do Y") | The service |
| Add a filter or a new query | The repository |
| Validate input shape or range | The schema |
| Add a column or table | A new Alembic migration **and** the model (see section 9) |
| Do pure maths (prices, dates) | `services/pricing.py` / `services/periods.py`, with a unit test |

### Life of a request: recording a payment

1. `POST /api/invoices/12/payments` arrives at `routes/invoices.py::record_payment`.
2. `StaffUser` dependency decodes the JWT and rejects customers with **403**.
3. `PaymentCreate` schema rejects `amount <= 0` or more than 2 decimal places with **422**.
4. `PaymentService.record()` locks the invoice row (`InvoiceRepository.lock`) so two clerks
   can't record against the same invoice at once, checks state and balance, creates the
   `Payment`, updates `amount_paid` / `amount_due`, flips the invoice to `paid` if nothing is
   left, and commits.
5. The route returns the payment, serialised by `PaymentRead`.

---

## 4. Cross-cutting rules

### Authentication (R1–R6)

- **Access token**: JWT, 15 minutes (`ACCESS_TOKEN_MINUTES`), sent as `Authorization: Bearer <token>`.
- **Refresh token**: random opaque string, 7 days. Only its SHA-256 hash is stored
  (`refresh_tokens`). Each refresh token works **once**; using it issues a new pair (rotation).
- **Passwords**: bcrypt. Max 72 characters (a bcrypt limit).
- **Password reset tokens**: random, hashed in `password_reset_tokens`, expire after 30
  minutes, single use. Resetting a password signs the user out everywhere.
- **No account enumeration**: `forgot-password` returns the same message whether or not the
  email exists.
- **Emails are stored lowercase**, which is how "one account per email" stays case-insensitive.

### Authorisation (R5)

Defined in `app/routes/deps.py`:

| Dependency | Allows |
|---|---|
| `CurrentUser` | Any logged-in, active user |
| `AdminUser` | `admin` |
| `StaffUser` | `admin`, `staff` |
| `CustomerUser` / `PortalCustomerId` | `customer` with a linked `customer_id` |

**Data isolation is enforced in the backend, not the UI.** Portal endpoints pass the
logged-in customer's `customer_id` into the service; the repository adds
`WHERE customer_id = :id`. Another customer's record returns **404** (not 403), so the API
doesn't even confirm it exists.

### Errors

Services raise domain errors from `app/core/exceptions.py`; a handler converts them to JSON
`{"detail": "..."}`:

| Error | HTTP | Typical cause |
|---|---|---|
| `BadRequestError` | 400 | Business rule broken (invalid state change, overpayment) |
| `AuthenticationError` | 401 | Missing, bad or expired token; wrong password |
| `PermissionDeniedError` | 403 | Wrong role |
| `NotFoundError` | 404 | Missing record, or another customer's record |
| `ConflictError` / `IntegrityError` | 409 | Duplicate email or SKU; deleting something still in use |
| Pydantic validation | 422 | Request body doesn't match the schema |

### Money (R15, R17)

- Stored as `NUMERIC(12,2)`, handled as Python `Decimal`, **never float**.
- Rounded half-up to the cent (`pricing.money()`).
- JSON responses return money as **strings** (`"9345.60"`) so no precision is lost in
  JavaScript. Frontends should keep them as strings or use a decimal library.

### Pagination

List endpoints return `{"items": [...], "total": n, "page": p, "size": s}`. Query params
`page` (≥1) and `size` (1–100, default 20). Nothing ever loads a whole table.

### Transactions and locking

- One request = one transaction, committed by the service.
- `SELECT ... FOR UPDATE` on invoices (payments, confirm, cancel) and subscriptions (billing).
- The billing run uses `FOR UPDATE SKIP LOCKED`, so parallel runs split the work instead of waiting.
- Document numbers (`SUB/2026/00001`, `INV/2026/00001`) come from `number_sequences` via an
  atomic upsert, gap-free within a year.

### Email

`core/email.py`. When `SMTP_HOST` is empty (development), emails are printed to the server log.
Routes send email as a FastAPI background task so the response isn't slowed down.

---

## 5. API reference, with the reason for each endpoint

Base path `/api`. Interactive docs with request/response examples: `http://localhost:8000/docs`.

### 5.1 Auth: `routes/auth.py` → `services/auth.py`

| Method & path | Who | Why it exists | Key rules |
|---|---|---|---|
| `POST /auth/signup` | Public | R1, R2, R3: "A small business ... creates an account with their email and a password" | Always creates a **customer** user plus a linked `customers` row. Duplicate email → 409. Weak password → 422. |
| `POST /auth/login` | Public | R1, R5 | Returns `access_token`, `refresh_token`, `expires_in`. Wrong credentials → 401 (same message for unknown email and wrong password). Disabled account → 401. |
| `POST /auth/refresh` | Public (needs refresh token) | Keeps short-lived access tokens practical | Rotates: the old refresh token stops working. |
| `POST /auth/logout` | Public (needs refresh token) | Lets a device sign out | Revokes that refresh token. |
| `POST /auth/forgot-password` | Public | R4: "a reset link should arrive at their registered email" | Always answers the same message. Link goes to `FRONTEND_URL/reset-password?token=...`. |
| `POST /auth/reset-password` | Public (needs token) | R4 | Token single-use, 30-minute expiry. New password must pass R3. Revokes all refresh tokens. |
| `GET /auth/me` | Any logged-in user | Frontend needs to know who is logged in and their role | |

### 5.2 Users: `routes/users.py` → `services/user.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `POST /users/staff` | Admin | R6: "Only the admin can add a new member of staff" | Creates role `staff`, records `created_by`. |
| `GET /users` | Admin | Admin manages accounts | Filter `?role=`. |
| `GET /users/{id}` | Admin | | |
| `PATCH /users/{id}` | Admin | Disable a leaver, rename | `is_active=false` also revokes their refresh tokens. Admins can't disable themselves. |

The **first admin** is created with `uv run python -m app.scripts.create_admin`, because
sign-up never creates admins.

### 5.3 Customers and payment terms: `routes/customers.py` → `services/customer.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /customers` | Staff | "A small internal team handles customers day to day" | Search `?q=` across name, company, email. |
| `POST /customers` | Staff | Sales reps add customers who didn't self-register | |
| `GET /customers/{id}` | Staff | | |
| `PATCH /customers/{id}` | Staff | Keep billing details (address, tax ID) current | |
| `DELETE /customers/{id}` | Admin | Clean-up | 409 if the customer has subscriptions, invoices or a login. |
| `GET /payment-terms` | Any logged-in user | R12: subscriptions need payment terms | e.g. Immediate (0), Net 15, Net 30. |
| `POST /payment-terms` | Admin | Add new terms | `due_days` drives the invoice due date. |

### 5.4 Catalog: `routes/catalog.py` → `services/catalog.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /products` | Staff | Browse the catalog when building quotes | Filters `q`, `product_type`, `active`. Includes taxes and variants. |
| `POST /products` | Admin | R7: "The admin adds it with its name, type, sales price, cost price and notes" | `tax_ids` links default taxes (R15). |
| `GET /products/{id}` | Staff | | |
| `PATCH /products/{id}` | Admin | Price changes, deactivation | Changing prices **does not** change existing invoices (snapshots). |
| `DELETE /products/{id}` | Admin | | 409 if used; deactivate instead (`active=false`). |
| `POST /products/{id}/variants` | Admin | R8: "offers it in variants ... choosing the Odoo brand adds 560" | `extra_price` = sum of the chosen attribute values. One value per attribute. Name defaults to `Product (Value)`. |
| `PATCH /variants/{id}` | Admin | Rename, change SKU, deactivate | |
| `GET /attributes` | Staff | | Attributes with their values. |
| `POST /attributes` | Admin | R8: define "Brand" and its values | Can create values in the same call. |
| `POST /attributes/{id}/values` | Admin | Add a value such as "Odoo" (+560) | |
| `PATCH /attribute-values/{id}` | Admin | Change an extra price | Recalculates the cached `extra_price` of every variant using it. |
| `GET /taxes` | Staff | | Filter `active`. |
| `POST /taxes` | Admin | R15: "Taxes are calculated automatically from rules the admin has set" | `percent` or `fixed` (per unit); `is_inclusive` for prices that already include tax. |
| `PATCH /taxes/{id}` | Admin | Rate changes, deactivation | Old invoices keep their snapshot rate. |

**Unit price** = `product.sales_price + variant.extra_price` (e.g. 1200 + 560 = 1760).

### 5.5 Plans and quotation templates: `routes/plans.py` → `services/plan.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /plans` | Staff | Pick a plan when quoting | Filters `active`, `billing_period`. |
| `POST /plans` | Admin | R9, R10: price, period, minimum quantity, dates, and the auto-close / closable / pausable / renewable flags | `billing_interval` lets you express "every 3 months". `trial_days` for free trials. |
| `GET /plans/{id}` | Staff | | |
| `PATCH /plans/{id}` | Admin | | `end_date ≥ start_date`. |
| `GET /quotation-templates` | Staff | R11 | |
| `POST /quotation-templates` | Staff | R11: "start from a quotation template that already has the right plan and product lines" | Line prices default to product + variant price. |
| `GET /quotation-templates/{id}` | Staff | | |
| `PATCH /quotation-templates/{id}` | Staff | | Sending `lines` replaces all lines. |
| `DELETE /quotation-templates/{id}` | Admin | | 409 if subscriptions reference it. |

**Plan flags are enforced, not decorative:**

| Flag | Enforced in |
|---|---|
| `pausable` | `→ paused` is rejected unless true |
| `closable` | Closing an active/paused subscription before its expiry is rejected unless true |
| `renewable` | `POST /subscriptions/{id}/renew` is rejected unless true |
| `auto_close` | The billing run closes these subscriptions once `expiry_date` has passed |
| `min_quantity` | `→ confirmed` is rejected if the lines' total quantity is lower |
| `start_date` / `end_date` / `active` | A plan can't be used for a subscription starting outside its availability |

### 5.6 Subscriptions: `routes/subscriptions.py` → `services/subscription.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /subscriptions` | Staff | R13: "anyone on the team should be able to see where it stands" | Filters `state`, `customer_id`, `plan_id`, `q` (number), `expiring_before`. |
| `POST /subscriptions` | Staff | R12: build a subscription from scratch | Starts in `draft`. Lines default to product/variant price and the product's taxes. Number `SUB/<year>/<n>`. |
| `POST /subscriptions/from-template` | Staff | R11: quote from a template | Starts in `quotation`, valid until today + template `validity_days`. |
| `GET /subscriptions/{id}` | Staff | | Includes lines, taxes and the full `state_logs` history. |
| `PATCH /subscriptions/{id}` | Staff | Negotiate the quote | Only in `draft` or `quotation`. Sending `lines` replaces them. |
| `DELETE /subscriptions/{id}` | Staff | Discard mistakes | Only `draft`. Anything later must be closed, to keep history. |
| `POST /subscriptions/{id}/state` | Staff | R13: move through the lifecycle | See the state machine in section 6.1. Every move is logged with who and why. |
| `POST /subscriptions/{id}/renew` | Staff | R10: "others can be ... renewed" | Plan must be renewable; new expiry must be later. Restarts billing if it had stopped at the old expiry. |
| `POST /subscriptions/{id}/invoices` | Staff | R14: invoice now, without waiting for the billing run | Bills exactly the next period. 409 if already billed. |

`recurring_untaxed` / `recurring_tax` / `recurring_total` on a subscription are a **preview**
using today's discounts. The invoice is re-priced at billing time (discounts may have expired
or been used up by then).

### 5.7 Discounts: `routes/discounts.py` → `services/discount.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /discounts` | Staff | Staff can see which rules exist | Filter `active`. |
| `POST /discounts` | Admin | R18: "Only the admin can create discount rules" | `percent` (≤100) or `fixed`; `scope` = `product` (needs `product_ids`) or `subscription`; `min_purchase_amount`, `min_quantity`, dates, `usage_limit` (empty = unlimited). |
| `GET /discounts/{id}` | Staff | | Shows `used_count`. |
| `PATCH /discounts/{id}` | Admin | Extend, deactivate, change products | |
| `DELETE /discounts/{id}` | Admin | | 409 once used on invoices; deactivate instead. |

There is **no "apply discount" endpoint on purpose**. R19 says the discount should "appear on
the next invoice on its own, without anyone having to remember it". The billing engine
evaluates every valid rule for each invoice (section 6.4).

### 5.8 Billing: `routes/billing.py` → `services/billing.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `POST /billing/run` | Staff | R14, R17: "hundreds of subscriptions are due at once. Nobody should be typing invoices by hand" | Optional `run_date` (default today). Safe to call repeatedly or in parallel. Also closes expired `auto_close` subscriptions. |
| `GET /billing/runs` | Staff | Audit what each run did | Processed count, invoices created, errors. |
| `GET /billing/runs/{id}` | Staff | | `error_log` lists failed subscriptions; one failure doesn't stop the run. |

In production this runs from cron: `uv run python -m app.scripts.run_billing`.

### 5.9 Invoices: `routes/invoices.py` → `services/invoice.py`, `services/payment.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /invoices` | Staff | R21: "see which invoices are paid and which are still outstanding" | Filters `state`, `customer_id`, `subscription_id`, `plan_id`, `date_from`/`date_to`, `q`, **`outstanding=true`**, **`overdue=true`**. Each row has `is_overdue`. |
| `GET /invoices/{id}` | Staff | | Lines with tax snapshots, and payments. |
| `POST /invoices/{id}/confirm` | Staff | R16: Draft → Confirmed | Only from `draft`. A zero-total invoice goes straight to `paid`. |
| `POST /invoices/{id}/cancel` | Staff | R16 | Not if `paid` or any payment recorded. Returns discount uses to their rules. The period stays billed (no automatic re-bill). |
| `POST /invoices/{id}/send` | Staff | R16: "send ... any invoice" | Must be confirmed or paid. Emails the customer; sets `sent_at`. |
| `GET /invoices/{id}/print` | Staff | R16: "print any invoice" | Returns printable HTML; use the browser's Print → Save as PDF. |
| `POST /invoices/{id}/payments` | Staff | R20: "recorded with its method, amount, date and a note, against the right invoice" | Invoice must be `confirmed`. Partial payments allowed; overpayment rejected. Reaching zero due → `paid`. |

**Overdue** = `state = confirmed AND amount_due > 0 AND due_date < today`.
**Due date** = invoice date + payment term `due_days`.

### 5.10 Payments: `routes/payments.py` → `services/payment.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /payments` | Staff | R21, R22: see money coming in | Filters `invoice_id`, `customer_id`, `method`, `date_from`/`date_to`. |

Payments are created through `POST /invoices/{id}/payments` so a payment can never exist
without its invoice.

### 5.11 Reports: `routes/reports.py` → `services/report.py`

| Method & path | Who | Why | Key rules |
|---|---|---|---|
| `GET /reports/summary` | Staff | R22: "How many subscriptions are active? How much revenue came in, and how much is still owed? Which invoices are overdue?" | Filters `date_from`, `date_to`, `customer_id`, `plan_id`. Returns active count, count per state, MRR, ARR, invoiced total, revenue collected, outstanding and overdue (amount + count). |
| `GET /reports/revenue-by-month` | Staff | R22: trend view for charts | Invoiced vs collected per month, same filters. |

Definitions:

| Metric | Meaning |
|---|---|
| **MRR** | Sum of active subscriptions' untaxed recurring amount, normalised to a month (yearly ÷ 12, weekly × 52/12, daily × 365/12, divided by `billing_interval`) |
| **ARR** | MRR × 12 |
| **Invoiced total** | Total of `confirmed` + `paid` invoices dated in the range |
| **Revenue collected** | Completed payments dated in the range |
| **Outstanding** | Confirmed invoices with `amount_due > 0` |
| **Overdue** | Outstanding and `due_date < today` |

The overdue **list** itself is `GET /invoices?overdue=true`.

### 5.12 Customer portal: `routes/portal.py`

R5 and R23: "customers see only their own subscriptions and invoices through a portal" and
"manage their own subscriptions without having to email anyone".

| Method & path | Why | Key rules |
|---|---|---|
| `GET /portal/profile` | Customer sees their billing details | |
| `GET /portal/subscriptions` | See own subscriptions | Filter `state`. |
| `GET /portal/subscriptions/{id}` | | Another customer's → 404. |
| `POST /portal/subscriptions/{id}/state` | Self-service: pause, resume or close | Only `paused`, `active` (resume from paused) and `closed`. Plan flags still apply. Logged against the customer user. |
| `GET /portal/invoices` | See own invoices | Filters `state`, `outstanding`. |
| `GET /portal/invoices/{id}` | | Another customer's → 404. |
| `GET /portal/invoices/{id}/print` | Download/print own invoice | |

### 5.13 Health

| Method & path | Why |
|---|---|
| `GET /health` | Liveness check for load balancers / Docker. No auth. |

---

## 6. Core flows in detail

### 6.1 Subscription state machine (R13, R10)

```
            ┌────────────── back to draft to revise ─────────────┐
            ▼                                                     │
  ┌───────┐   send   ┌───────────┐  accept  ┌───────────┐ start ┌─┴──────┐
  │ draft │ ───────► │ quotation │ ───────► │ confirmed │ ────► │ active │◄──┐
  └───────┘          └─────┬─────┘          └─────┬─────┘       └─┬────┬─┘   │ resume
                           │ reject               │ cancel        │    │     │
                           ▼                      ▼               │    ▼     │
                       ┌────────┐◄────────────────┘    close ◄────┘ ┌────────┐
                       │ closed │◄─────────────────────────────────│ paused │
                       └────────┘              close               └────────┘
```

Allowed transitions live in **one place**, `ALLOWED_TRANSITIONS` in `services/subscription.py`.
Everything else is rejected with 400.

| Transition | Checks | Side effects |
|---|---|---|
| draft → quotation | At least one line | `quotation_valid_until` = today + template validity (or 30 days) |
| quotation → draft | | Clears `quotation_valid_until` |
| quotation → confirmed | Quote not expired; total quantity ≥ plan `min_quantity`; plan available on the start date | |
| confirmed → active | | Sets `trial_end_date` if the plan has trial days; `next_invoice_date` = trial end or start date |
| active → paused | Plan `pausable` | `paused_at` set; billing skips paused subscriptions |
| paused → active | | Resumes at the next scheduled date on or after today: **paused time isn't billed** |
| active/paused → closed | Plan `closable`, unless already past expiry | `closed_at`, `close_reason`; billing stops |
| quotation/confirmed → closed | | Lost or cancelled deal |

Every transition writes a `subscription_state_logs` row (from, to, who, reason).

### 6.2 Billing engine (R14, R17)

`BillingService.run(run_date)`:

```
create billing_runs row (status = running)
for each subscription id WHERE state = active AND next_invoice_date <= run_date:
    lock the subscription row (FOR UPDATE SKIP LOCKED)   ← another worker has it? skip
    while next_invoice_date <= run_date:                 ← catch-up loop: nothing skipped
        if past expiry_date: stop billing (next_invoice_date = NULL)
        period = [next_invoice_date, next scheduled date - 1 day]
        if no invoice exists for (subscription, period_start):
            SAVEPOINT
              price lines, claim discount uses, create invoice + lines + tax snapshots
            on unique violation: roll back the savepoint     ← nothing billed twice
        advance next_invoice_date by one period
    COMMIT (one transaction per subscription; a failure only affects that one)
close active/paused subscriptions on auto_close plans whose expiry has passed
finish billing_runs row with counts and error log
```

**Why it can't double-bill**, three independent layers:

1. The run only picks subscriptions whose `next_invoice_date` is due, and advances it in the
   same transaction as the invoice.
2. Row lock with `SKIP LOCKED`: two simultaneous runs never process the same subscription.
3. Database constraint `UNIQUE (subscription_id, period_start)` on `invoices`: even a bug in
   1 or 2 can't create a duplicate.

Tested: six runs fired at the same moment created each period's invoice exactly once.

**Why it can't skip:** the inner `while` loop. If the server was down for three days (or three
months), the next run creates every missed period's invoice.

**Period dates** (`services/periods.py`) are always counted from a fixed anchor (start date or
trial end), so a subscription starting 31 Jan bills on 28/29 Feb and then **31 Mar**, not 28 Mar.

**Invoice date** = period start. **Due date** = invoice date + payment term days. Invoices
are created as `draft` so staff can review before confirming.

### 6.3 Pricing order (R15)

`services/pricing.py`. It's pure maths with no database access, and is unit-tested. Every
line is priced in this fixed order:

1. `subtotal = quantity × unit_price`
2. minus discounts → `untaxed`
3. taxes on the **discounted** amount
   - `percent`: untaxed × rate / 100
   - `fixed`: rate × quantity
   - `is_inclusive` percent taxes are extracted from the price instead of added
4. `total = untaxed + tax`; invoice totals are sums of line totals

Worked example (the sample data): 5 seats × 1760 = 8800 → 10% volume discount −880 → 7920 →
GST 18% = 1425.60 → **9345.60**.

### 6.4 Discount engine (R18, R19)

At invoice time, for the invoice's `period_start`:

1. Load rules that are `active`, inside their date range, and have uses left.
2. For each rule, find the lines it targets: products in `discount_products` for
   `scope=product`, all lines for `scope=subscription`.
3. Skip the rule if the targeted lines don't meet `min_quantity` or `min_purchase_amount`.
4. Percent: applied per line. Fixed: spread across targeted lines by value, last line takes
   the rounding so it adds up to the cent. Capped at the order value.
5. Stacked rules never take a line below zero.
6. **Claim a use atomically**:
   `UPDATE discounts SET used_count = used_count + 1 WHERE id = ? AND (usage_limit IS NULL OR used_count < usage_limit)`.
   If two invoices race for the last use, only one wins; the other is re-priced without it.
7. Record a `discount_usages` row per discount per invoice. Cancelling the invoice gives the
   use back.

### 6.5 Payments (R20, R21)

- Invoice must be `confirmed` (not draft, cancelled or already paid).
- `amount ≤ amount_due`; partial payments are fine.
- `amount_paid += amount`, `amount_due -= amount`; at zero → `paid` with `paid_at`.
- The invoice row is locked during the update so concurrent payments can't overpay.

---

## 7. Data model notes

The schema came from the DBML design and is created by `migrations/versions/0001_initial_schema.py`.
32 tables in these groups:

| Group | Tables |
|---|---|
| Auth & users | `users`, `password_reset_tokens`, `refresh_tokens` |
| Customers | `customers`, `payment_terms` |
| Catalog | `products`, `product_attributes`, `product_attribute_values`, `product_variants`, `variant_attribute_values`, `taxes`, `product_taxes` |
| Plans | `plans`, `quotation_templates`, `quotation_template_lines` |
| Subscriptions | `subscriptions`, `subscription_lines`, `subscription_line_taxes`, `subscription_state_logs` |
| Discounts | `discounts`, `discount_products`, `discount_usages` |
| Billing | `number_sequences`, `billing_runs`, `invoices`, `invoice_lines`, `invoice_line_taxes`, `credit_notes` |
| Payments | `payments`, `invoice_reminders` |
| Other | `notifications`, `audit_logs` |

Design decisions worth knowing:

- **Snapshots:** `invoice_lines` copy description, unit price and amounts;
  `invoice_line_taxes` copy tax name and rate. Changing the catalog never rewrites history.
- **Cascades:** child rows (lines, line taxes, tokens, join tables) are deleted with their
  parent. Business records (invoices, payments, subscriptions) block deletion while referenced:
  that's why several DELETE endpoints return 409 and say "deactivate instead".
- **Timestamps** are `timestamptz`. `updated_at` is maintained by SQLAlchemy (`onupdate`).
- **Sample data** (`0002_sample_data.py`): Northwind Corp on 5 Odoo-brand CRM seats with a
  10% discount and a part-paid October invoice. Seeded users have placeholder password
  hashes; use `create_admin` to give an account a real password.

---

## 8. Non-functional requirements

### Performance (R24: "under two seconds with thousands of subscriptions")

| Technique | Where |
|---|---|
| Indexes on every hot filter: `subscriptions(state, next_invoice_date)`, `invoices(state, due_date)`, `customer_id`, `invoice_date`, `payment_date`, plus foreign keys | Migration `0001` |
| Server-side pagination on every list | `BaseRepository.paginate` |
| Report numbers computed with SQL `SUM` / `COUNT ... GROUP BY`, never Python loops over rows | `repositories/report.py` |
| No N+1 queries: related rows loaded with `selectinload` | Repositories |
| Billing run processes one subscription per transaction and clears the session between them, so memory stays flat | `BillingService.run` |

Measured on sample data: summary report ≈ 45 ms. To prove the target at scale, seed ~10,000
subscriptions and ~100,000 invoices and time the list and report endpoints (see section 10).

### Security

| Concern | Handling |
|---|---|
| Password storage | bcrypt |
| Token storage | Only SHA-256 hashes of refresh and reset tokens are stored |
| Account enumeration | `forgot-password` answers identically; login error doesn't say which part was wrong |
| Data isolation | Customer scoping in the repository query, 404 for other customers' records |
| Role checks | On every non-public route, declared in the signature |
| Input validation | Pydantic schemas on every body and query param |
| SQL injection | SQLAlchemy parameterised queries only |
| Secrets | `.env` is git-ignored; `JWT_SECRET` must be long and random |

---

## 9. Running, testing and operating

```bash
cp .env.example .env              # set POSTGRES_PASSWORD and JWT_SECRET
uv sync
docker compose up -d
uv run alembic upgrade head       # tables + sample data
uv run python -m app.scripts.create_admin --name "Your Name" --email admin@brightloop.com
uv run fastapi dev app/main.py    # http://localhost:8000/docs
```

| Task | Command |
|---|---|
| Unit tests (pricing, billing periods) | `uv run pytest` |
| Run billing manually | `uv run python -m app.scripts.run_billing [--date 2026-11-01]` |
| Nightly billing (cron) | `0 1 * * *  cd /path/to/BrightLoop && uv run python -m app.scripts.run_billing` |
| Reset DB to clean sample data | `uv run alembic downgrade base && uv run alembic upgrade head` |

### Changing the database schema

1. `uv run alembic revision -m "describe change"` and write `upgrade()` / `downgrade()`.
2. Update the matching model in `app/models/` so it mirrors the migration exactly.
3. `uv run alembic upgrade head`, then test `downgrade -1` and `upgrade head` again.

`migrations/env.py` points `target_metadata` at the models, so `alembic revision --autogenerate`
works. Review its output: it will also suggest column-comment changes, because the models don't
carry the DBML comments.

### Trying the whole flow by hand

In `/docs`: log in as admin → create a product with a tax → add a variant → create a plan →
create a quotation template → `POST /subscriptions/from-template` → move it to `confirmed`, then
`active` → `POST /billing/run` → confirm the invoice → record a payment →
`GET /reports/summary`.

---

## 10. Known gaps and next steps

| Gap | Notes |
|---|---|
| Rate limiting on login / forgot-password | Add middleware (e.g. slowapi) |
| Credit notes and refunds | Table exists (`credit_notes`); no API yet. Today a paid invoice can't be cancelled |
| Audit log | Table exists (`audit_logs`); subscription history is logged, other entities aren't |
| Notifications and dunning reminders | Tables exist (`notifications`, `invoice_reminders`); nothing writes to them yet |
| PDF files | Invoices print as HTML (browser → PDF). Add a PDF library if files are needed |
| Online payments | `payments.gateway` / `gateway_payment_id` are ready for Stripe/Razorpay webhooks |
| Proration on mid-cycle changes | Not implemented |
| Performance proof at scale | Write a seed script for ~10k subscriptions / ~100k invoices and record timings |
| API integration tests | Only the pure maths has pytest tests; the end-to-end flow was verified with a throwaway script |

---

## 11. Gotchas

- **Methods called `list` shadow the built-in.** Modules whose classes define `def list(...)`
  start with `from __future__ import annotations`; otherwise later hints like `-> list[Discount]`
  crash at import. Keep that line when adding such modules.
- **Money comes back as strings** (`"1760.00"`). That's deliberate.
- **Subscription totals are a preview**; the invoice is the source of truth.
- **Billing doesn't run on its own.** Schedule the cron job, or call `POST /billing/run`.
- **Cancelling an invoice doesn't re-bill the period.** The unique constraint keeps that
  period marked as billed.
- **Seeded users can't log in** until you run `create_admin` for them (placeholder hashes).
- **Changing `POSTGRES_PASSWORD` after the container first started** has no effect; run
  `docker compose down -v` to recreate the database.
- **Emails in development** are in the server log (look for "SMTP not configured").
