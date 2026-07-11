import asyncio
import random
import sys
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import delete, select

# Adjust path to import app correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal
from app.modules.organizations.models import Organization
from app.modules.business.models import (
    Project, Resource, ProjectAllocation, Invoice, Transaction,
    ProjectStatus, InvoiceStatus, TransactionType, TransactionCategory
)


async def seed_data():
    print("Starting database seed...")
    async with AsyncSessionLocal() as session:
        # 1. Clean existing data
        print("Cleaning old business tools data...")
        await session.execute(delete(Transaction))
        await session.execute(delete(Invoice))
        await session.execute(delete(ProjectAllocation))
        await session.execute(delete(Resource))
        await session.execute(delete(Project))
        await session.commit()

        # 2. Ensure default Organization exists
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = await session.execute(select(Organization).filter_by(id=org_id))
        org = result.scalar_one_or_none()
        if not org:
            print("Creating default organization...")
            org = Organization(
                id=org_id,
                name="Default Organization",
                slug="default-org"
            )
            session.add(org)
            await session.commit()

        # 3. Create Resources
        print("Creating resources...")
        resources = [
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Alice Developer", role="Software Engineer", cost_rate=Decimal("1500.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Bob Designer", role="UI Designer", cost_rate=Decimal("1200.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Charlie Devops", role="DevOps Engineer", cost_rate=Decimal("1800.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Dave Contractor", role="Contractor Engineer", cost_rate=Decimal("2000.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Eve Sales", role="Sales Executive", cost_rate=Decimal("1000.00")),
        ]
        session.add_all(resources)
        await session.commit()

        # 4. Create Projects
        print("Creating projects...")
        today = date.today()
        projects = [
            Project(
                id=uuid.uuid4(),
                organization_id=org_id,
                name="E-Commerce App",
                description="Core custom shopping application with mobile-first storefront",
                status=ProjectStatus.ACTIVE,
                budget=Decimal("150000.00"),
                start_date=today - timedelta(days=180),
                end_date=today + timedelta(days=180)
            ),
            Project(
                id=uuid.uuid4(),
                organization_id=org_id,
                name="Inventory API Integration",
                description="Backend REST API integrating with supplier databases",
                status=ProjectStatus.COMPLETED,
                budget=Decimal("45000.00"),
                start_date=today - timedelta(days=270),
                end_date=today - timedelta(days=90)
            ),
            Project(
                id=uuid.uuid4(),
                organization_id=org_id,
                name="Mobile App Redesign",
                description="Redesign and transition to React Native for next phase scaling",
                status=ProjectStatus.PLANNING,
                budget=Decimal("85000.00"),
                start_date=today + timedelta(days=30),
                end_date=today + timedelta(days=180)
            ),
        ]
        session.add_all(projects)
        await session.commit()

        # 5. Create Project Allocations
        print("Creating allocations...")
        allocations = [
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[0].id, project_id=projects[0].id,
                allocation_percentage=80, role="Lead Developer"
            ),
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[1].id, project_id=projects[0].id,
                allocation_percentage=40, role="UI Designer"
            ),
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[0].id, project_id=projects[1].id,
                allocation_percentage=20, role="Consulting Developer"
            ),
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[2].id, project_id=projects[1].id,
                allocation_percentage=100, role="Lead DevOps Engineer"
            ),
        ]
        session.add_all(allocations)
        await session.commit()

        # 6. Seed Invoices & Transactions (Semi-Deterministic via random.seed(42))
        print("Seeding invoices and transactions...")
        random.seed(42)

        transactions = []
        invoices = []

        start_date = today - timedelta(days=365)
        
        # Pre-generate some clients and invoices
        clients = ["Acme Corporation", "East Africa Retailers", "Safari Adventures", "Kibo Ventures", "Nile Tech Solutions"]
        
        for idx in range(1, 21):
            issue_date = start_date + timedelta(days=random.randint(10, 340))
            due_date = issue_date + timedelta(days=30)
            inv_amount = Decimal(str(random.randint(50, 250) * 100))
            
            # 80% chance it is paid
            is_paid = random.random() < 0.8
            status = InvoiceStatus.PAID if is_paid else (InvoiceStatus.OVERDUE if due_date < today else InvoiceStatus.UNPAID)
            
            inv = Invoice(
                id=uuid.uuid4(),
                organization_id=org_id,
                invoice_number=f"INV-2025-{idx:03d}",
                amount=inv_amount,
                status=status,
                issue_date=issue_date,
                due_date=due_date,
                client_name=random.choice(clients)
            )
            invoices.append(inv)
            
            # If paid, generate corresponding transaction
            if status == InvoiceStatus.PAID:
                pay_date = issue_date + timedelta(days=random.randint(1, 15))
                t = Transaction(
                    id=uuid.uuid4(),
                    organization_id=org_id,
                    invoice_id=inv.id,
                    amount=inv_amount,
                    type=TransactionType.INCOME,
                    category=TransactionCategory.REVENUE,
                    date=pay_date,
                    description=f"Payment for invoice {inv.invoice_number} by {inv.client_name}"
                )
                transactions.append(t)

        session.add_all(invoices)
        await session.commit()

        # Daily / Time-Series cashflow loop for expenses and miscellaneous income
        current_date = start_date
        while current_date <= today:
            # Monthly Rent
            if current_date.day == 1:
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=Decimal("3000.00"), type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_RENT, date=current_date,
                    description="Monthly Office Space Rent"
                ))

            # Monthly Software Subscriptions
            if current_date.day == 5:
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=Decimal("850.00"), type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_SOFTWARE, date=current_date,
                    description="Internal SaaS Subscription Billing (Slack, GitHub, GSuite)"
                ))

            # Infrastructure (COGS) with small seed-based variation
            if current_date.day == 10:
                infra_cost = Decimal(str(round(1200.00 + random.uniform(-150.0, 350.0), 2)))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=infra_cost, type=TransactionType.EXPENSE,
                    category=TransactionCategory.COGS_INFRASTRUCTURE, date=current_date,
                    description="AWS Cloud Infrastructure Monthly Statement"
                ))

            # Monthly Payroll (OPEX + COGS)
            if current_date.day == 28:
                # OPEX payroll for internal staff
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[0].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[0].name}"
                ))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[1].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[1].name}"
                ))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[2].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[2].name}"
                ))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[4].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[4].name}"
                ))

                # COGS Contractors
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[3].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.COGS_CONTRACTORS, date=current_date,
                    description=f"Contractor billing - {resources[3].name}"
                ))

            # Random daily/weekly business retail income entries
            # Let's say there is a 35% chance of an income receipt on any non-weekend day
            if current_date.weekday() < 5 and random.random() < 0.35:
                retail_amount = Decimal(str(round(random.uniform(150.0, 1500.0), 2)))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=retail_amount, type=TransactionType.INCOME,
                    category=TransactionCategory.REVENUE, date=current_date,
                    description="Daily software subscription / stripe payout revenue"
                ))

            current_date += timedelta(days=1)

        # Batch insert all transactions
        print(f"Batch inserting {len(transactions)} transactions...")
        session.add_all(transactions)
        await session.commit()

        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
