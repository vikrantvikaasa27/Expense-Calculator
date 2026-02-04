"""Inline keyboard builders for Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Sequence

from app.models import Category


def build_category_keyboard(categories: Sequence[Category]) -> InlineKeyboardMarkup:
    """Build inline keyboard for category selection."""
    keyboard = []
    row = []
    
    for i, category in enumerate(categories):
        button = InlineKeyboardButton(
            text=f"{category.emoji} {category.name}",
            callback_data=f"cat_{category.id}"
        )
        row.append(button)
        
        # 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Add remaining buttons
    if row:
        keyboard.append(row)
    
    # Add cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


def build_confirm_keyboard() -> InlineKeyboardMarkup:
    """Build confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_report_type_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for report type selection."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Category Breakdown", callback_data="report_pie"),
            InlineKeyboardButton("📈 Daily Trend", callback_data="report_bar"),
        ],
        [
            InlineKeyboardButton("📋 Summary", callback_data="report_summary"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_month_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for month selection."""
    from datetime import datetime
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    keyboard = []
    row = []
    
    # Show last 6 months
    for i in range(6):
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        
        month_name = datetime(year, month, 1).strftime("%b %Y")
        button = InlineKeyboardButton(
            text=month_name,
            callback_data=f"month_{year}_{month}"
        )
        row.append(button)
        
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Expense", callback_data="menu_add"),
            InlineKeyboardButton("📤 Upload Bill", callback_data="menu_upload"),
        ],
        [
            InlineKeyboardButton("📊 Reports", callback_data="menu_report"),
            InlineKeyboardButton("📜 History", callback_data="menu_history"),
        ],
        [
            InlineKeyboardButton("📁 Categories", callback_data="menu_categories"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
