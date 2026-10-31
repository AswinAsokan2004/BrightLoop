"""Isolated test API adapter. Never deploy this server or use it with real data.

Runs the actual routes/services/repositories against SQLite for workflow tests.
PostgreSQL migrations, locking and production concurrency are outside this adapter's scope.
"""
import os
import tempfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

os.environ.setdefault('POSTGRES_USER', 'test')
os.environ.setdefault('POSTGRES_PASSWORD', 'test')
os.environ.setdefault('POSTGRES_DB', 'test')
os.environ.setdefault('JWT_SECRET', 'isolated-test-secret-never-use-in-production')

from sqlalchemy import Date, DateTime, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.elements import Cast
from sqlalchemy.types import TypeDecorator

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base, Customer, PaymentTerm, Plan, Product, User
from app.models.enums import BillingPeriod, ProductType, UserRole


@compiles(JSONB, 'sqlite')
def compile_jsonb(type_, compiler, **kwargs):
    return 'JSON'


@compiles(Cast, 'sqlite')
def compile_date_cast(element, compiler, **kwargs):
    if isinstance(element.type, Date):
        return 'date(' + compiler.process(element.clause, **kwargs) + ')'
    return compiler.visit_cast(element, **kwargs)


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def create_test_app(database: Path):
    engine = create_engine(f'sqlite:///{database}', connect_args={'check_same_thread': False})

    @event.listens_for(engine, 'connect')
    def sqlite_functions(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.create_function('greatest', -1, max)
        conn.create_function('date_trunc', 2, lambda unit, value: str(value)[:7] + '-01')

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                column.type = UTCDateTime()
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, autoflush=False, expire_on_commit=False)
    with sessions() as db:
        customer = Customer(name='Browser Customer', email='customer@example.com')
        db.add(customer)
        db.flush()
        db.add_all([
            User(name='Integration Admin', email='integration@example.com', password_hash=hash_password('Integration!Pass123'), role=UserRole.admin),
            User(name='Customer Account', email='customer@example.com', password_hash=hash_password('Customer!Pass123'), role=UserRole.customer, customer_id=customer.id),
            User(name='Staff Account', email='staff@example.com', password_hash=hash_password('Staff!Pass123'), role=UserRole.staff),
            PaymentTerm(name='Immediate', due_days=0),
            Product(name='Test CRM', product_type=ProductType.service, sales_price=Decimal('100'), cost_price=Decimal('10')),
            Plan(name='Monthly', code='MONTHLY', price=Decimal('100'), billing_period=BillingPeriod.monthly, start_date=date(2020, 1, 1), pausable=True),
        ])
        db.commit()

    def test_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    return app


if __name__ == '__main__':
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='brightloop-browser-') as directory:
        test_app = create_test_app(Path(directory) / 'test.sqlite')
        test_app.add_api_route('/__test__/health', lambda: {'fixture': 'brightloop-isolated-test-api'})
        uvicorn.run(test_app, host='127.0.0.1', port=8100)
