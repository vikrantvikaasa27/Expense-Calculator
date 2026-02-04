"""Expense service for CRUD operations."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, Category, Expense
from app.models.category import DEFAULT_CATEGORIES
from app.schemas.expense import ExpenseCreate, MonthlyReport, CategorySummary


class ExpenseService:
    """Service for expense CRUD operations and reporting."""
    
    async def get_or_create_user(
        self, 
        session: AsyncSession, 
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Get existing user or create new one."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
    
    async def seed_categories(self, session: AsyncSession) -> None:
        """Seed default categories if they don't exist."""
        for cat_data in DEFAULT_CATEGORIES:
            stmt = select(Category).where(Category.name == cat_data["name"])
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                category = Category(**cat_data)
                session.add(category)
        
        await session.commit()
    
    async def get_categories(self, session: AsyncSession) -> Sequence[Category]:
        """Get all categories."""
        stmt = select(Category).order_by(Category.id)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_category_by_id(self, session: AsyncSession, category_id: int) -> Category | None:
        """Get category by ID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_category_by_name(self, session: AsyncSession, name: str) -> Category | None:
        """Get category by name (case-insensitive partial match)."""
        stmt = select(Category).where(Category.name.ilike(f"%{name}%"))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_expense(
        self,
        session: AsyncSession,
        user_id: int,
        expense_data: ExpenseCreate,
    ) -> Expense:
        """Create a new expense."""
        expense = Expense(
            user_id=user_id,
            category_id=expense_data.category_id,
            amount=expense_data.amount,
            description=expense_data.description,
            merchant_name=expense_data.merchant_name,
            receipt_image_path=expense_data.receipt_image_path,
        )
        session.add(expense)
        await session.commit()
        await session.refresh(expense)
        return expense
    
    async def get_user_expenses(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> Sequence[Expense]:
        """Get user's expenses with pagination."""
        stmt = (
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.user_id == user_id)
            .order_by(Expense.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_monthly_expenses(
        self,
        session: AsyncSession,
        user_id: int,
        year: int,
        month: int,
    ) -> Sequence[Expense]:
        """Get expenses for a specific month."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        stmt = (
            select(Expense)
            .options(selectinload(Expense.category))
            .where(
                Expense.user_id == user_id,
                Expense.created_at >= start_date,
                Expense.created_at < end_date,
            )
            .order_by(Expense.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_monthly_report(
        self,
        session: AsyncSession,
        user_id: int,
        year: int,
        month: int,
    ) -> MonthlyReport:
        """Generate monthly expense report."""
        expenses = await self.get_monthly_expenses(session, user_id, year, month)
        
        # Calculate totals by category
        category_totals: dict[int, dict] = {}
        total = Decimal("0")
        
        for expense in expenses:
            total += expense.amount
            cat_id = expense.category_id
            if cat_id not in category_totals:
                category_totals[cat_id] = {
                    "name": expense.category.name,
                    "emoji": expense.category.emoji,
                    "total": Decimal("0"),
                    "count": 0,
                }
            category_totals[cat_id]["total"] += expense.amount
            category_totals[cat_id]["count"] += 1
        
        # Build category summaries
        categories = []
        for cat_data in category_totals.values():
            percentage = float(cat_data["total"] / total * 100) if total > 0 else 0
            categories.append(CategorySummary(
                category_name=cat_data["name"],
                category_emoji=cat_data["emoji"],
                total_amount=cat_data["total"],
                count=cat_data["count"],
                percentage=percentage,
            ))
        
        # Sort by total amount descending
        categories.sort(key=lambda x: x.total_amount, reverse=True)
        
        # Calculate daily average
        days_in_month = (datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)) - datetime(year, month, 1)
        today = datetime.now()
        if year == today.year and month == today.month:
            days_passed = today.day
        else:
            days_passed = days_in_month.days
        
        daily_avg = total / days_passed if days_passed > 0 else Decimal("0")
        
        month_name = datetime(year, month, 1).strftime("%B")
        
        return MonthlyReport(
            month=month_name,
            year=year,
            total_expenses=total,
            expense_count=len(expenses),
            categories=categories,
            daily_average=daily_avg,
        )
    
    async def get_category_totals(
        self,
        session: AsyncSession,
        user_id: int,
        year: int,
        month: int,
    ) -> dict[str, Decimal]:
        """Get expense totals by category for charting."""
        expenses = await self.get_monthly_expenses(session, user_id, year, month)
        
        totals: dict[str, Decimal] = {}
        for expense in expenses:
            key = f"{expense.category.emoji} {expense.category.name}"
            totals[key] = totals.get(key, Decimal("0")) + expense.amount
        
        return totals
    
    async def get_daily_totals(
        self,
        session: AsyncSession,
        user_id: int,
        year: int,
        month: int,
    ) -> dict[str, Decimal]:
        """Get expense totals by day for charting."""
        expenses = await self.get_monthly_expenses(session, user_id, year, month)
        
        totals: dict[str, Decimal] = {}
        for expense in expenses:
            day = expense.created_at.strftime("%d %b")
            totals[day] = totals.get(day, Decimal("0")) + expense.amount
        
        # Sort by date
        return dict(sorted(totals.items()))


# Singleton instance
expense_service = ExpenseService()
