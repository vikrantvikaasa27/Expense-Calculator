"""Pydantic schemas for expense data validation."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    """Category response schema."""
    id: int
    name: str
    emoji: str
    description: str | None = None
    
    class Config:
        from_attributes = True


class ExpenseCreate(BaseModel):
    """Schema for creating a new expense."""
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    category_id: int = Field(..., description="Category ID")
    description: str | None = Field(None, max_length=500)
    merchant_name: str | None = Field(None, max_length=255)
    receipt_image_path: str | None = None


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""
    amount: Decimal | None = Field(None, gt=0)
    category_id: int | None = None
    description: str | None = None
    merchant_name: str | None = None


class ExpenseResponse(BaseModel):
    """Schema for expense response."""
    id: int
    amount: Decimal
    description: str | None
    merchant_name: str | None
    category: CategoryResponse
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategorySummary(BaseModel):
    """Summary of expenses by category."""
    category_name: str
    category_emoji: str
    total_amount: Decimal
    count: int
    percentage: float


class MonthlyReport(BaseModel):
    """Monthly expense report."""
    month: str
    year: int
    total_expenses: Decimal
    expense_count: int
    categories: list[CategorySummary]
    daily_average: Decimal


class BillExtractionResult(BaseModel):
    """Result from Gemini Vision bill extraction."""
    amount: Decimal | None = None
    merchant_name: str | None = None
    suggested_category: str | None = None
    confidence: float = 0.0
    raw_text: str | None = None
