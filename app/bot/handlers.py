"""Telegram bot handlers for expense tracking."""

import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from app.database import async_session_maker
from app.services.expense_service import expense_service
from app.services.vision_service import vision_service
from app.services.chart_service import chart_service
from app.schemas.expense import ExpenseCreate
from app.bot.keyboards import (
    build_category_keyboard,
    build_confirm_keyboard,
    build_report_type_keyboard,
    build_month_keyboard,
    build_main_menu_keyboard,
)


# Conversation states
AMOUNT, CATEGORY, DESCRIPTION, CONFIRM = range(4)
UPLOAD_CONFIRM, UPLOAD_CATEGORY = range(4, 6)
REPORT_MONTH, REPORT_TYPE = range(6, 8)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    # Register user in database
    async with async_session_maker() as session:
        await expense_service.get_or_create_user(
            session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        # Seed categories if needed
        await expense_service.seed_categories(session)
    
    welcome_message = f"""
👋 Welcome to **Expense Tracker Bot**, {user.first_name}!

I help you track your expenses easily. Here's what I can do:

📝 **Commands:**
• /add - Add a new expense manually
• /upload - Upload a bill image (I'll extract the amount!)
• /report - View expense reports with charts
• /history - See your recent expenses
• /categories - View expense categories
• /help - Show this help message

💡 **Quick Tip:** Just send me a bill photo anytime, and I'll extract the amount for you!
"""
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await start_command(update, context)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /add command - start expense addition flow."""
    await update.message.reply_text(
        "💰 **Add New Expense**\n\nPlease enter the amount (e.g., 150 or 150.50):",
        parse_mode="Markdown",
    )
    return AMOUNT


async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount input."""
    text = update.message.text.strip()
    
    # Clean the input (remove currency symbols)
    text = text.replace("₹", "").replace("$", "").replace(",", "").strip()
    
    try:
        amount = Decimal(text)
        if amount <= 0:
            raise InvalidOperation("Amount must be positive")
        
        context.user_data["amount"] = amount
        
        # Get categories and show keyboard
        async with async_session_maker() as session:
            categories = await expense_service.get_categories(session)
            keyboard = build_category_keyboard(categories)
        
        await update.message.reply_text(
            f"✅ Amount: **₹{amount:,.2f}**\n\nNow select a category:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return CATEGORY
        
    except (InvalidOperation, ValueError):
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g., 150 or 150.50):"
        )
        return AMOUNT


async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection via callback."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Expense addition cancelled.")
        return ConversationHandler.END
    
    category_id = int(query.data.split("_")[1])
    context.user_data["category_id"] = category_id
    
    # Get category name
    async with async_session_maker() as session:
        category = await expense_service.get_category_by_id(session, category_id)
        context.user_data["category_name"] = f"{category.emoji} {category.name}"
    
    await query.edit_message_text(
        f"✅ Category: **{context.user_data['category_name']}**\n\n"
        "📝 Add a description (optional).\n"
        "Send `/skip` to skip or type your description:",
        parse_mode="Markdown",
    )
    return DESCRIPTION


async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle description input."""
    text = update.message.text.strip()
    
    if text.lower() == "/skip":
        context.user_data["description"] = None
    else:
        context.user_data["description"] = text
    
    # Show confirmation
    amount = context.user_data["amount"]
    category = context.user_data["category_name"]
    description = context.user_data.get("description", "None")
    
    await update.message.reply_text(
        f"📋 **Confirm Expense**\n\n"
        f"💰 Amount: ₹{amount:,.2f}\n"
        f"📁 Category: {category}\n"
        f"📝 Description: {description or 'None'}\n\n"
        "Is this correct?",
        parse_mode="Markdown",
        reply_markup=build_confirm_keyboard(),
    )
    return CONFIRM


async def confirm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle expense confirmation."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Expense addition cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Save expense
    async with async_session_maker() as session:
        user = await expense_service.get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
        )
        
        expense_data = ExpenseCreate(
            amount=context.user_data["amount"],
            category_id=context.user_data["category_id"],
            description=context.user_data.get("description"),
            merchant_name=context.user_data.get("merchant_name"),
        )
        
        expense = await expense_service.create_expense(session, user.id, expense_data)
    
    await query.edit_message_text(
        f"✅ **Expense Saved!**\n\n"
        f"💰 ₹{context.user_data['amount']:,.2f} added to {context.user_data['category_name']}",
        parse_mode="Markdown",
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo upload for bill scanning."""
    await update.message.reply_text("🔍 Analyzing your bill... Please wait.")
    
    # Get photo file
    photo = update.message.photo[-1]  # Highest resolution
    file = await context.bot.get_file(photo.file_id)
    
    # Download image
    image_bytes = await file.download_as_bytearray()
    
    # Extract data using Gemini Vision
    result = await vision_service.extract_from_bill(bytes(image_bytes))
    
    if result.amount:
        context.user_data["amount"] = result.amount
        context.user_data["merchant_name"] = result.merchant_name
        
        message = f"📄 **Bill Analysis**\n\n"
        message += f"💰 Amount Detected: **₹{result.amount:,.2f}**\n"
        if result.merchant_name:
            message += f"🏪 Merchant: {result.merchant_name}\n"
        if result.suggested_category:
            message += f"💡 Suggested Category: {result.suggested_category}\n"
        message += f"📊 Confidence: {result.confidence*100:.0f}%\n\n"
        message += "Is this correct?"
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=build_confirm_keyboard(),
        )
        return UPLOAD_CONFIRM
    else:
        await update.message.reply_text(
            "❌ Could not extract amount from the bill.\n"
            "Please try again with a clearer image or use /add to enter manually.",
        )
        return ConversationHandler.END


async def upload_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation after bill upload."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Bill upload cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Show category selection
    async with async_session_maker() as session:
        categories = await expense_service.get_categories(session)
        keyboard = build_category_keyboard(categories)
    
    await query.edit_message_text(
        f"✅ Amount: **₹{context.user_data['amount']:,.2f}**\n\n"
        "Select a category:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return UPLOAD_CATEGORY


async def upload_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection after bill upload."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Bill upload cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    category_id = int(query.data.split("_")[1])
    
    # Save expense
    async with async_session_maker() as session:
        user = await expense_service.get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
        )
        category = await expense_service.get_category_by_id(session, category_id)
        
        expense_data = ExpenseCreate(
            amount=context.user_data["amount"],
            category_id=category_id,
            merchant_name=context.user_data.get("merchant_name"),
        )
        
        await expense_service.create_expense(session, user.id, expense_data)
    
    await query.edit_message_text(
        f"✅ **Expense Saved!**\n\n"
        f"💰 ₹{context.user_data['amount']:,.2f} added to {category.emoji} {category.name}",
        parse_mode="Markdown",
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /report command."""
    await update.message.reply_text(
        "📊 **Expense Reports**\n\nSelect a month:",
        parse_mode="Markdown",
        reply_markup=build_month_keyboard(),
    )
    return REPORT_MONTH


async def report_month_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle month selection for report."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Report cancelled.")
        return ConversationHandler.END
    
    _, year, month = query.data.split("_")
    context.user_data["report_year"] = int(year)
    context.user_data["report_month"] = int(month)
    
    month_name = datetime(int(year), int(month), 1).strftime("%B %Y")
    
    await query.edit_message_text(
        f"📆 Report for **{month_name}**\n\nSelect report type:",
        parse_mode="Markdown",
        reply_markup=build_report_type_keyboard(),
    )
    return REPORT_TYPE


async def report_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle report type selection and generate report."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Report cancelled.")
        return ConversationHandler.END
    
    year = context.user_data["report_year"]
    month = context.user_data["report_month"]
    report_type = query.data.split("_")[1]
    
    await query.edit_message_text("⏳ Generating report...")
    
    async with async_session_maker() as session:
        user = await expense_service.get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
        )
        
        if report_type == "pie":
            # Category breakdown pie chart
            category_totals = await expense_service.get_category_totals(
                session, user.id, year, month
            )
            
            if not category_totals:
                await query.message.reply_text("📭 No expenses found for this month.")
                return ConversationHandler.END
            
            month_name = datetime(year, month, 1).strftime("%B %Y")
            chart_bytes = chart_service.generate_pie_chart(
                category_totals,
                title=f"Expenses by Category - {month_name}"
            )
            
            await query.message.reply_photo(
                photo=InputFile(io.BytesIO(chart_bytes), filename="category_report.png"),
                caption=f"📊 Category breakdown for {month_name}",
            )
            
        elif report_type == "bar":
            # Daily expense bar chart
            daily_totals = await expense_service.get_daily_totals(
                session, user.id, year, month
            )
            
            if not daily_totals:
                await query.message.reply_text("📭 No expenses found for this month.")
                return ConversationHandler.END
            
            month_name = datetime(year, month, 1).strftime("%B %Y")
            chart_bytes = chart_service.generate_bar_chart(
                daily_totals,
                title=f"Daily Expenses - {month_name}"
            )
            
            await query.message.reply_photo(
                photo=InputFile(io.BytesIO(chart_bytes), filename="daily_report.png"),
                caption=f"📈 Daily expenses for {month_name}",
            )
            
        else:  # summary
            report = await expense_service.get_monthly_report(
                session, user.id, year, month
            )
            
            if report.expense_count == 0:
                await query.message.reply_text("📭 No expenses found for this month.")
                return ConversationHandler.END
            
            message = f"📋 **{report.month} {report.year} Summary**\n\n"
            message += f"💰 Total Spent: **₹{report.total_expenses:,.2f}**\n"
            message += f"📊 Transactions: {report.expense_count}\n"
            message += f"📅 Daily Average: ₹{report.daily_average:,.2f}\n\n"
            message += "**By Category:**\n"
            
            for cat in report.categories[:5]:  # Top 5
                message += f"  {cat.category_emoji} {cat.category_name}: ₹{cat.total_amount:,.2f} ({cat.percentage:.1f}%)\n"
            
            await query.message.reply_text(message, parse_mode="Markdown")
    
    context.user_data.clear()
    return ConversationHandler.END


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history command."""
    async with async_session_maker() as session:
        user = await expense_service.get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
        )
        expenses = await expense_service.get_user_expenses(session, user.id, limit=10)
    
    if not expenses:
        await update.message.reply_text("📭 No expenses found. Use /add to add your first expense!")
        return
    
    message = "📜 **Recent Expenses**\n\n"
    
    for expense in expenses:
        date_str = expense.created_at.strftime("%d %b")
        message += f"{expense.category.emoji} **₹{expense.amount:,.2f}** - {expense.category.name}\n"
        message += f"   📅 {date_str}"
        if expense.description:
            message += f" | {expense.description[:30]}"
        message += "\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /categories command."""
    async with async_session_maker() as session:
        categories = await expense_service.get_categories(session)
    
    message = "📁 **Expense Categories**\n\n"
    
    for cat in categories:
        message += f"{cat.emoji} **{cat.name}**\n   _{cat.description}_\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu callbacks."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split("_")[1]
    
    if action == "add":
        await query.message.reply_text(
            "💰 **Add New Expense**\n\nPlease enter the amount (e.g., 150 or 150.50):",
            parse_mode="Markdown",
        )
        # Note: This won't start the conversation handler properly
        # User should use /add command instead
    elif action == "upload":
        await query.message.reply_text(
            "📤 **Upload Bill**\n\nSend me a photo of your bill/receipt, and I'll extract the amount automatically!",
            parse_mode="Markdown",
        )
    elif action == "report":
        await query.message.reply_text(
            "📊 **Expense Reports**\n\nSelect a month:",
            parse_mode="Markdown",
            reply_markup=build_month_keyboard(),
        )
    elif action == "history":
        # Get history
        async with async_session_maker() as session:
            user = await expense_service.get_or_create_user(
                session,
                telegram_id=update.effective_user.id,
            )
            expenses = await expense_service.get_user_expenses(session, user.id, limit=10)
        
        if not expenses:
            await query.message.reply_text("📭 No expenses found. Use /add to add your first expense!")
        else:
            message = "📜 **Recent Expenses**\n\n"
            for expense in expenses:
                date_str = expense.created_at.strftime("%d %b")
                message += f"{expense.category.emoji} **₹{expense.amount:,.2f}** - {expense.category.name}\n"
                message += f"   📅 {date_str}\n\n"
            await query.message.reply_text(message, parse_mode="Markdown")
    elif action == "categories":
        async with async_session_maker() as session:
            categories = await expense_service.get_categories(session)
        
        message = "📁 **Expense Categories**\n\n"
        for cat in categories:
            message += f"{cat.emoji} **{cat.name}**\n"
        await query.message.reply_text(message, parse_mode="Markdown")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=build_main_menu_keyboard(),
    )
    return ConversationHandler.END


def setup_handlers(application: Application) -> None:
    """Set up all bot handlers."""
    
    # Add expense conversation handler
    add_expense_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            CATEGORY: [CallbackQueryHandler(receive_category)],
            DESCRIPTION: [MessageHandler(filters.TEXT, receive_description)],
            CONFIRM: [CallbackQueryHandler(confirm_expense)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # Photo upload conversation handler
    upload_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.PHOTO, handle_photo),
            CommandHandler("upload", lambda u, c: u.message.reply_text(
                "📤 Send me a photo of your bill/receipt!"
            )),
        ],
        states={
            UPLOAD_CONFIRM: [CallbackQueryHandler(upload_confirm)],
            UPLOAD_CATEGORY: [CallbackQueryHandler(upload_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # Report conversation handler
    report_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report_command)],
        states={
            REPORT_MONTH: [CallbackQueryHandler(report_month_selected)],
            REPORT_TYPE: [CallbackQueryHandler(report_type_selected)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("categories", categories_command))
    application.add_handler(add_expense_handler)
    application.add_handler(upload_handler)
    application.add_handler(report_handler)
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
