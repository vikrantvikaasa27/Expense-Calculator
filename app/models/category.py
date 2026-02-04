"""Category model for expense categories."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.expense import Expense


class Category(Base):
    """Category model for expense categorization."""
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Relationships
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense",
        back_populates="category"
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, emoji={self.emoji})>"


# Default categories to seed
DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "emoji": "🍕", "description": "Restaurants, takeout, coffee"},
    {"name": "Transportation", "emoji": "🚗", "description": "Fuel, uber, public transport"},
    {"name": "Groceries", "emoji": "🛒", "description": "Supermarket, daily essentials"},
    {"name": "Utilities", "emoji": "💡", "description": "Electricity, water, internet"},
    {"name": "Entertainment", "emoji": "🎬", "description": "Movies, games, streaming"},
    {"name": "Healthcare", "emoji": "🏥", "description": "Medicine, doctor visits"},
    {"name": "Shopping", "emoji": "👕", "description": "Clothes, electronics, gadgets"},
    {"name": "Education", "emoji": "📚", "description": "Books, courses, subscriptions"},
    {"name": "Travel", "emoji": "✈️", "description": "Hotels, flights, vacations"},
    {"name": "Others", "emoji": "📦", "description": "Miscellaneous expenses"},
]
