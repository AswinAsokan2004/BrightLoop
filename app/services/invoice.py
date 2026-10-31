from __future__ import annotations

from datetime import date
from html import escape

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import OutgoingEmail
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utcnow
from app.models import Invoice
from app.models.enums import InvoiceState
from app.repositories.billing import InvoiceRepository
from app.repositories.discount import DiscountRepository
from app.schemas.common import PageParams


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.invoices = InvoiceRepository(db)
        self.discounts = DiscountRepository(db)

    def get(self, invoice_id: int, customer_id: int | None = None) -> Invoice:
        """customer_id restricts the lookup to that customer's own invoices (portal)."""
        invoice = self.invoices.get_detail(invoice_id, customer_id)
        if invoice is None:
            raise NotFoundError("Invoice not found")
        return invoice

    def list(
        self,
        params: PageParams,
        state: InvoiceState | None = None,
        customer_id: int | None = None,
        subscription_id: int | None = None,
        plan_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        overdue: bool = False,
        outstanding: bool = False,
        q: str | None = None,
    ) -> tuple[list[Invoice], int]:
        return self.invoices.list(
            today=date.today(),
            state=state,
            customer_id=customer_id,
            subscription_id=subscription_id,
            plan_id=plan_id,
            date_from=date_from,
            date_to=date_to,
            overdue=overdue,
            outstanding=outstanding,
            q=q,
            page=params.page,
            size=params.size,
        )

    def confirm(self, invoice_id: int) -> Invoice:
        invoice = self._lock(invoice_id)
        if invoice.state != InvoiceState.draft:
            raise BadRequestError(f"Only draft invoices can be confirmed (this one is {invoice.state})")
        invoice.state = InvoiceState.confirmed
        invoice.confirmed_at = utcnow()
        if invoice.amount_due == 0:  # fully discounted
            invoice.state = InvoiceState.paid
            invoice.paid_at = invoice.confirmed_at
        self.db.commit()
        return self.get(invoice_id)

    def cancel(self, invoice_id: int) -> Invoice:
        invoice = self._lock(invoice_id)
        if invoice.state in (InvoiceState.paid, InvoiceState.cancelled):
            raise BadRequestError(f"A {invoice.state} invoice cannot be cancelled")
        if invoice.amount_paid > 0:
            raise BadRequestError("This invoice has payments recorded; refund them before cancelling")

        # Give the discount uses back so they can apply elsewhere
        for usage in self.discounts.usages_for_invoice(invoice.id):
            self.discounts.release(usage.discount_id)
        self.discounts.delete_usages_for_invoice(invoice.id)

        invoice.state = InvoiceState.cancelled
        invoice.cancelled_at = utcnow()
        invoice.amount_due = 0
        self.db.commit()
        return self.get(invoice_id)

    def send(self, invoice_id: int) -> tuple[Invoice, OutgoingEmail]:
        invoice = self.get(invoice_id)
        if invoice.state not in (InvoiceState.confirmed, InvoiceState.paid):
            raise BadRequestError("Confirm the invoice before sending it")
        invoice.sent_at = utcnow()
        self.db.commit()

        email = OutgoingEmail(
            to=invoice.customer.email,
            subject=f"Invoice {invoice.number} from Brightloop Software",
            body=(
                f"Dear {invoice.customer.name},\n\n"
                f"Invoice {invoice.number} for {invoice.period_start} to {invoice.period_end}.\n"
                f"Total: {invoice.currency} {invoice.total}\n"
                f"Amount due: {invoice.currency} {invoice.amount_due} by {invoice.due_date}\n\n"
                f"View it in your portal: {settings.frontend_url}/portal/invoices/{invoice.id}\n"
            ),
        )
        return invoice, email

    def render_html(self, invoice_id: int, customer_id: int | None = None) -> str:
        """Printable invoice; use the browser's Print / Save as PDF."""
        inv = self.get(invoice_id, customer_id)
        customer = inv.customer
        rows = "".join(
            f"<tr><td>{escape(line.description)}</td><td class=n>{line.quantity}</td>"
            f"<td class=n>{line.unit_price}</td><td class=n>{line.discount_amount}</td>"
            f"<td>{escape(', '.join(f'{t.tax_name}' for t in line.taxes)) or '-'}</td>"
            f"<td class=n>{line.tax_amount}</td><td class=n>{line.total_amount}</td></tr>"
            for line in inv.lines
        )
        address = ", ".join(
            escape(part)
            for part in (customer.address_line1, customer.address_line2, customer.city,
                         customer.state, customer.postal_code, customer.country)
            if part
        )
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Invoice {escape(inv.number)}</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 40px; color: #222; }}
 table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
 th, td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }}
 .n {{ text-align: right; }} .totals td {{ border: 0; }}
 .meta {{ display: flex; justify-content: space-between; }}
</style></head><body>
<h1>Invoice {escape(inv.number)}</h1>
<div class="meta">
 <div><strong>Bill to</strong><br>{escape(customer.company_name or customer.name)}<br>{address}<br>
  {escape(customer.email)}{'<br>Tax ID: ' + escape(customer.tax_id) if customer.tax_id else ''}</div>
 <div>Status: <strong>{inv.state}</strong><br>Invoice date: {inv.invoice_date}<br>Due date: {inv.due_date}<br>
  Period: {inv.period_start} to {inv.period_end}</div>
</div>
<table>
 <tr><th>Description</th><th class=n>Qty</th><th class=n>Unit price</th><th class=n>Discount</th>
  <th>Taxes</th><th class=n>Tax</th><th class=n>Amount</th></tr>
 {rows}
</table>
<table class="totals">
 <tr><td class=n>Subtotal</td><td class=n>{inv.subtotal}</td></tr>
 <tr><td class=n>Discount</td><td class=n>-{inv.discount_total}</td></tr>
 <tr><td class=n>Untaxed</td><td class=n>{inv.untaxed_total}</td></tr>
 <tr><td class=n>Tax</td><td class=n>{inv.tax_total}</td></tr>
 <tr><td class=n><strong>Total ({escape(inv.currency)})</strong></td><td class=n><strong>{inv.total}</strong></td></tr>
 <tr><td class=n>Paid</td><td class=n>{inv.amount_paid}</td></tr>
 <tr><td class=n><strong>Amount due</strong></td><td class=n><strong>{inv.amount_due}</strong></td></tr>
</table>
</body></html>"""

    def _lock(self, invoice_id: int) -> Invoice:
        invoice = self.invoices.lock(invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found")
        return invoice
