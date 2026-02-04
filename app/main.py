"""Main entry point for the Expense Calculator application."""

import asyncio
import logging

from telegram.ext import Application

from app.config import settings
from app.database import init_db, close_db
from app.bot.handlers import setup_handlers


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database after bot starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully!")


async def post_shutdown(application: Application) -> None:
    """Clean up database connection on shutdown."""
    logger.info("Closing database connection...")
    await close_db()
    logger.info("Database connection closed.")


def main() -> None:
    """Start the bot."""
    # Validate settings
    if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_bot_token_here":
        logger.error("❌ TELEGRAM_BOT_TOKEN not configured!")
        logger.error("Please set your bot token in .env file")
        return
    
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        logger.warning("⚠️ GEMINI_API_KEY not configured - bill scanning will not work")
    
    logger.info("🚀 Starting Expense Calculator Bot...")
    
    # Create application
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Set up handlers
    setup_handlers(application)
    
    # Start polling
    logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
