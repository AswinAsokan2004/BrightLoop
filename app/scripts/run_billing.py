"""Run the billing engine from cron, e.g. every night at 01:00:

    0 1 * * *  cd /path/to/BrightLoop && uv run python -m app.scripts.run_billing
"""

import argparse
from datetime import date

from app.core.database import SessionLocal
from app.services.billing import BillingService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", type=date.fromisoformat, help="Run date (default: today)")
    args = parser.parse_args()

    with SessionLocal() as db:
        run = BillingService(db).run(args.date)
        print(
            f"Billing run {run.id} for {run.run_date}: {run.status}, "
            f"{run.subscriptions_processed} subscriptions, {run.invoices_created} invoices, "
            f"{run.errors_count} errors"
        )
        if run.error_log:
            print(run.error_log)


if __name__ == "__main__":
    main()
