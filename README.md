# Expense Calculator Bot 💰

A Telegram bot for tracking expenses with bill scanning (Gemini Vision) and visualization.

## Features

- 📝 **Add Expenses** - Quick expense entry via chat
- 📤 **Bill Scanning** - Upload receipt photos, AI extracts the amount
- 📊 **Reports** - Category breakdowns, daily trends, monthly summaries
- 📜 **History** - View recent expenses
- 🏷️ **Categories** - 10 predefined expense categories

## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL database
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google Gemini API Key (from [AI Studio](https://aistudio.google.com/))

### 2. Installation

```bash
# Install dependencies
pip install -e .

# Or using uv
uv sync
```

### 3. Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/expense_tracker
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Create Database

```sql
CREATE DATABASE expense_tracker;
```

### 5. Run the Bot

```bash
python -m app.main
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message & registration |
| `/add` | Add a new expense manually |
| `/upload` | Upload a bill image |
| `/report` | View expense reports with charts |
| `/history` | View recent expenses |
| `/categories` | View expense categories |
| `/help` | Show help message |

## Tech Stack

- **Backend**: FastAPI + python-telegram-bot
- **Database**: PostgreSQL + SQLAlchemy (async)
- **AI**: Google Gemini Vision (bill scanning)
- **Charts**: Matplotlib

## License

MIT